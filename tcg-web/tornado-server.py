import tornado.ioloop
import tornado.web
from tornado import websocket
import json
import random
from game import *

GLOBALS={
    'waiting' : None,
    'games' : {},
}

class GamePageHandler(tornado.web.RequestHandler):
    def get(self):
        page = open ("sse.html")
        self.write(page.read())

class IndexPageHandler(tornado.web.RequestHandler):
    def get(self):
        page = open ("index.html")
        self.write(page.read())

class RulesPageHandler(tornado.web.RequestHandler):
    def get(self):
        page = open ("rules.html")
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
                r1 = random.randint (0,2**30)
                r2 = random.randint (0,2**30)
                if r1 != r2 and r1 not in GLOBALS['games'] and r2 not in GLOBALS['games']:
                    game = Game (GLOBALS['waiting'], self, r1, r2)
                    GLOBALS['games'][r1] = game
                    GLOBALS['games'][r2] = game
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
        else:
            game.send_status ()
    def comnand (self, game):
        return True

class PlayHandler(GameCommandHandler):
    def command(self, game):
        if game.on_block : 
            return False
        handnum = int(self.get_argument('handnum'))
        card = game.on_trait.hand[handnum]
        if not card.target_required:
            if card.play ():
                game.log ("You play "+card.name+"<br>","Opponent plays "+card.name+"<br>")
                return True
            return False
        target_string = self.get_argument('target', default="[]")
        if target_string == "[]":
            game.get_target = card.target_required
            game.pending_card = card
        return False

class GrowManaHandler(GameCommandHandler):
    def command(self, game):
        if game.on_block : 
            return False
        game.on_trait.grow_mana ()
        game.log ("You grow mana<br>", "Opponent grows mana<br>")
        return True

class DrawHandler(GameCommandHandler):
    def command(self, game):
        if game.on_block : 
            return False
        game.on_trait.draw ()
        game.log ("You draw<br>", "Opponent draws<br>")
        return True

class AttackHandler(GameCommandHandler):
    def command(self, game):
        if game.on_block : 
            return False
        attackers = json.loads (self.get_argument('checkboxes'))
        if attackers == []:
            return False
        game.attack_phase (attackers)
        return False

class SelectHandler(GameCommandHandler):
    def command (self, game):
        target_string = self.get_argument('checkboxes')
        target_bools = json.loads (target_string)
        for i in range (len (target_bools)):
            if target_bools[i] and game.pending_card:
                game.get_target = None
                target_card = game.pending_card.get_target_list ()[i]
                if game.pending_card.play (target_card):
                    game.log ("You play "+game.pending_card.name+" on "+target_card.name+"<br>",
                        "Opponent plays "+game.pending_card.name+" on "+target_card.name+"<br>")
                    return True
                return False
            elif target_bools[i] and game.pending_active: 
                game.get_target = None
                target_card = game.pending_active.get_target_active_list ()[i]
                if game.pending_active.activate (target_card):
                    game.log ("You activate "+game.pending_card.name+" on "+target_card.name+"<br>",
                        "Opponent activates "+game.pending_card.name+" on "+target_card.name+"<br>")
                    return True
                return False


class BlockHandler(GameCommandHandler):
    def command(self, game):
        if game.get_killed:
            return False
        blockers = json.loads (self.get_argument('checkboxes'))
        game.block_phase (blockers)
        return False

class KillHandler(GameCommandHandler):
    def command(self, game):
        killed = json.loads (self.get_argument('checkboxes'))
        return game.kill_phase (killed)

class ActivateItemHandler(GameCommandHandler):
    def command(self, game):
        iid = int(self.get_argument('iid'))
        card = game.on_trait.items[iid]
        if not card.target_active_required:
            if card.activate () :
                game.log ("You activate "+card.name+"<br>", "Opponent activates "+card.name+"<br>")
                return True
            return False
        target_string = self.get_argument('target', default="[]")
        if target_string == "[]":
            game.get_target = card.target_active_required
            game.pending_active = card
            game.send_status ()

class ActivateCreatureHandler(GameCommandHandler):
    def command(self, game):
        cid = int(self.get_argument('cid'))
        card = game.on_trait.creatures[cid]
        if not card.target_active_required:
            if card.activate () :
                game.log ("You activate "+card.name+"<br>", "Opponent activates "+card.name+"<br>")
                return True
            return False
        target_string = self.get_argument('target', default="[]")
        if target_string == "[]":
            game.get_target = card.target_active_required
            game.pending_active = card
            game.send_status ()

application = tornado.web.Application([
    (r"/", IndexPageHandler),
    (r"/index.html", IndexPageHandler),
    (r"/game", GamePageHandler),
    (r"/rules", RulesPageHandler),
    (r"/sse.js", JsHandler),
    (r"/socket", ClientSocket),
    (r"/play", PlayHandler),
    (r"/grow_mana", GrowManaHandler),
    (r"/draw", DrawHandler),
    (r"/attack", AttackHandler),
    (r"/select", SelectHandler),
    (r"/block", BlockHandler),
    (r"/kill", KillHandler),
    (r"/activate_item", ActivateItemHandler),
    (r"/activate_creature", ActivateCreatureHandler)
], debug=True)

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
