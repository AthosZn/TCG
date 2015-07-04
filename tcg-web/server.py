import tornado.ioloop
import tornado.web
from gameshared import *
import random
import json
from tornado import websocket
from pubsub import pub

GLOBALS={
    'waiting' : None,
    'games' : {},
}

class PlayerState ():
    """Represent gameplay variables of a player: stats, deck and cards"""
    def __init__ (self, game_state):
        self.health = 20
        self.cur_mana = 2
        self.max_mana = 2
        self.hand = [play_card_factory (random.randint (0, len (all_card_data)-1), 
            game_state, self) for i in range (5)]
        self.deck = [play_card_factory (random.randint (0, len (all_card_data)-1), 
            game_state, self) for i in range (55)]
        self.creatures = []
        self.items = []
        self.graveyard = []

    def draw (self):
        self.hand.append (self.deck.pop ())

    def discard (self, hand_index):
        card = self.hand[hand_index]
        self.graveyard.append (card)
        self.hand.remove (card)

    def kill (self, creature_index):
        card = self.creatures[creature_index]
        self.graveyard.append (card)
        self.creatures.remove (card)

    def grow_mana (self):
        self.max_mana = min (self.max_mana + 1, 10)
        self.cur_mana = self.max_mana

    def visible_state (self, from_self=False):
        vis_state = self.__dict__.copy()
        vis_state['creatures'] = [ c.get_card_data() for c in self.creatures ]
        vis_state['hand'] = [ c.get_card_data() for c in self.hand ]
        vis_state['graveyard'] = [ c.get_card_data() for c in self.graveyard ]
        vis_state['items'] = [ c.get_card_data() for c in self.items ]
        
        if not from_self:
            # Deleting what shouldnt be visible
            vis_state["hand"] = len (vis_state["hand"]) 
        del vis_state["deck"]
        return vis_state

class Game ():
    """Regroup players and their respective connections and variables 
    representing the turn state"""
    def __init__ (self, connection1, connection2, gameid):
        self.player1 = PlayerState (self)
        self.player2 = PlayerState (self)
        self.connection1 = connection1
        self.connection2 = connection2
        self.on_trait = self.player2
        self.gameid = gameid
        self.end_turn ()

    def dump_state (self,player_from):
        if player_from == self.player1:
            player_opp = self.player2
        else :
            player_opp = self.player1 
        tempdict = { "pstate":  player_from.visible_state(True),
                     "oppstate": player_opp.visible_state(),
                     "on_trait": self.on_trait==player_from,
                     "attackers": self.attackers or [],
                     "blockers": self.blockers or [],
                     "get_killed": self.get_killed,
                     "gid": self.gameid
                }
        return json.dumps(tempdict)

    def send_status (self):
        self.connection1.write_message(self.dump_state(self.player1))
        self.connection2.write_message(self.dump_state(self.player2))

    def require_target (self, card_type):
        if self.on_trait == self.player1 :
            self.connection1.write_message ("{require_target:"+card_type+"}")
        else:
            self.connection2.write_message ("{require_target:"+card_type+"}")

    def end_turn (self):
        self.attackers = None
        self.blockers = None
        self.on_block = None
        self.get_killed = None
        pub.sendMessage ('end_turn_event')
        if self.on_trait == self.player1:
            self.on_trait = self.player2
        else:
            self.on_trait = self.player1
        self.send_status ()

    def attack_phase (self, attackers):
        if self.on_trait == self.player1:
            self.on_block = self.player2
        else:
            self.on_block = self.player1

        attacker_cards = []
        for i in range(len(self.on_trait.creatures)):
            if attackers[i]:
                attacker_cards += [self.on_trait.creatures [i]]
        pub.sendMessage ('attack_event', attackers=attacker_cards)
           
        if self.on_block.creatures == []:
            for c in attacker_cards :
                self.on_block.health -= c.creature_strength
            self.on_block = None
            self.end_turn()
            return
        self.attackers = attackers
        self.send_status ()

    def block_phase (self, blockers):
        self.blockers = blockers
        blocker_cards = []
        for i in range(len(self.on_block.creatures)):
            if blockers[i]:
                blocker_cards += [self.on_block.creatures [i]]
        attacker_cards = []
        for i in range(len(self.on_trait.creatures)):
            if self.attackers[i]:
                attacker_cards += [self.on_trait.creatures [i]]

        a_strength = 0
        b_strength = 0
        for c in blocker_cards :
            b_strength += c.creature_strength
        for c in attacker_cards :
            a_strength += c.creature_strength
        if a_strength > b_strength :
            self.get_killed = "attacking"
            self.send_status ()
        elif b_strength > a_strength :
            self.get_killed = "blocking"
            self.send_status ()
        else:
            for c in blocker_cards :
                c.destroy ()
            for c in attacker_cards :
                c.destroy ()
            self.end_turn ()

    def kill_phase (self, killed):
        blocker_cards = []
        for i in range(len(self.on_block.creatures)):
            if self.blockers[i]:
                blocker_cards += [self.on_block.creatures [i]]
        attacker_cards = []
        for i in range(len(self.on_trait.creatures)):
            if self.attackers[i]:
                attacker_cards += [self.on_trait.creatures [i]]

        a_strength = 0  #Calculate attacking strength
        for c in attacker_cards :
            a_strength += c.creature_strength 

        if self.get_killed == "blocking" :
            strength_delta = self.on_block.creatures[0].creature_strength 
                           #Calculate the part the weakest defensive 
                           #creature can tank without dying
            killed_cards = []
            for i in range(len(killed)):
                if killed[i]:
                    if self.on_block.creatures[i] not in blocker_cards :
                        return False # Trying to sacrifice non blocking
                    killed_cards += [self.on_block.creatures[i]] #Get sacrificed cards
                else :
                    strength = self.on_block.creatures[i].creature_strength
                    strength_delta = min (strength, strength - 1)
            b_strength = 0 #Calculate sacrificed strength
            for c in killed_cards :
                b_strength += c.creature_strength
            if a_strength - b_strength <= strength_delta:
                for c in killed_cards :
                    c.destroy ()
                for c in attacker_cards :
                    c.destroy ()
                return True

        elif self.get_killed == "attacking":
        #Same as above without strength delta and some reversed variables
            b_strength = 0
            for c in blocker_cards :
                b_strength += c.creature_strength
            killed_cards = []
            for i in range(len(killed)):
                if killed[i]:
                    if self.on_trait.creatures[i] not in attacker_cards :
                        return False # Trying to kill non attacking
                    killed_cards += [self.on_trait.creatures[i]] 
            killed_strength = 0 #Calculate killed strength
            for c in killed_cards :
                killed_strength += c.creature_strength
            if killed_strength <= b_strength :
                self.on_block.health -= a_strength - b_strength
                for c in killed_cards :
                    c.destroy ()
                for c in blocker_cards :
                    c.destroy ()
                return True
        return False

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        page = open ("sse.html")
        self.write(page.read())

class JsHandler(tornado.web.RequestHandler):
    def get(self):
        page = open ("sse.js")
        self.write(page.read())

class ClientSocket(websocket.WebSocketHandler):
    def open(self):
        if GLOBALS['waiting']:
            inserted = False
            while not inserted:
                r = random.randint (0,2**30)
                if r not in GLOBALS['games']:
                    GLOBALS['games'][r] = Game (GLOBALS['waiting'], self, r)
                    inserted = True
            GLOBALS['waiting'] = None
            print "Game launched"
        else:
            GLOBALS['waiting'] = self
            #self.write_message("Waiting for opponent...")
            print "Player waiting"

    def on_close(self):
        if GLOBALS['waiting'] == self:
            GLOBALS['waiting'] = None
        else:
            dc = False
            for key in GLOBALS['games']:
                game = GLOBALS['games'][key]
                if game.connection1 == self :
                    GLOBALS['waiting'] = game.connection2
                    dc = True
                elif game.connection2 == self :
                    GLOBALS['waiting'] = game.connection1
                    dc = True
                if dc:
                    for key in GLOBALS['games']:
                        if GLOBALS['games'][key] == game:
                            del GLOBALS['games'][key]
                            break
                    #GLOBALS['waiting'].write_message("Disconnected. Waiting for opponent...")
                    break
        print "WebSocket closed"

class GameCommandHandler (tornado.web.RequestHandler):
    def post(self, *args, **kwargs):
        gameid = int(self.get_argument('gameid'))
        game = GLOBALS['games'][gameid]
        if self.command (game):
            game.end_turn ()
    def comnand (self, game):
        return True

class PlayHandler(GameCommandHandler):
    def command(self, game):
        if game.on_block : 
            return False
        handnum = int(self.get_argument('handnum'))
        card = game.on_trait.hand[handnum]
        return card.play ()

class GrowManaHandler(GameCommandHandler):
    def command(self, game):
        if game.on_block : 
            return False
        game.on_trait.grow_mana ()
        return True

class DrawHandler(GameCommandHandler):
    def command(self, game):
        if game.on_block : 
            return False
        game.on_trait.draw ()
        return True

class AttackHandler(GameCommandHandler):
    def command(self, game):
        if game.on_block : 
            return False
        attackers = json.loads (self.get_argument('creatures'))
        if attackers == []:
            return False
        game.attack_phase (attackers)
        return False

class BlockHandler(GameCommandHandler):
    def command(self, game):
        if game.get_killed:
            return False
        blockers = json.loads (self.get_argument('creatures'))
        game.block_phase (blockers)
        return False

class KillHandler(GameCommandHandler):
    def command(self, game):
        killed = json.loads (self.get_argument('creatures'))
        return game.kill_phase (killed)

class ActivateItemHandler(GameCommandHandler):
    def command(self, game):
        iid = int(self.get_argument('iid'))
        game.on_trait.items[iid].activate ()
        game.send_status ()
        return False

class ActivateCreatureHandler(GameCommandHandler):
    def command(self, game):
        cid = int(self.get_argument('cid'))
        game.on_trait.creatures[cid].activate ()
        game.send_status ()
        return False

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/sse.js", JsHandler),
    (r"/socket", ClientSocket),
    (r"/play", PlayHandler),
    (r"/grow_mana", GrowManaHandler),
    (r"/draw", DrawHandler),
    (r"/attack", AttackHandler),
    (r"/block", BlockHandler),
    (r"/kill", KillHandler),
    (r"/activate_item", ActivateItemHandler),
    (r"/activate_creature", ActivateCreatureHandler)
], debug=True)

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
