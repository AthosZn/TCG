import tornado.ioloop
import tornado.web
from gameshared import *
import random
import json
from tornado import websocket

GLOBALS={
    'waiting' : None,
    'games' : [],
}


class PlayerState ():
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
        #TODO: dictionariser recursivement
        vis_state = self.__dict__.copy()
        vis_state['creatures'] = [ all_card_data[c.num] for c in self.creatures ]
        vis_state['hand'] = [ all_card_data[c.num] for c in self.hand ]
        vis_state['graveyard'] = [ all_card_data[c.num] for c in self.graveyard ]
        vis_state['items'] = [ all_card_data[c.num] for c in self.items ]
        
        vis_state["from_self"] = from_self
        if not from_self:
            # Deleting what shouldnt be visible
            vis_state["hand"] = len (vis_state["hand"]) 
        del vis_state["deck"]
        return json.dumps(vis_state)

class Game ():
    def __init__ (self, connection1, connection2):
        self.player1 = PlayerState (self)
        self.player2 = PlayerState (self)
        self.connection1 = connection1
        self.connection2 = connection2
        self.on_trait = self.player2
        self.gameid = len(GLOBALS['games'])
        self.end_turn ()

    def end_turn (self):
        page = open("play_form.html")
        self.connection1.write_message(self.player1.visible_state(True)) # + self.player2.visible_state())
        self.connection2.write_message(self.player2.visible_state(True)) # + self.player1.visible_state())
        if self.on_trait == self.player1:
            self.on_trait = self.player2
            #self.connection2.write_message(page.read())
        else:
            self.on_trait = self.player1
            #self.connection1.write_message(page.read())

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        page = open ("sse.html")
        self.write(page.read())

class ClientSocket(websocket.WebSocketHandler):
    def open(self):
        if GLOBALS['waiting']:
            GLOBALS['games'].append (Game (GLOBALS['waiting'], self))
            GLOBALS['waiting'] = None
            print "Game launched"
        else:
            GLOBALS['waiting'] = self
            self.write_message("Waiting for opponent...")
            print "Player waiting"

    def on_close(self):
        if GLOBALS['waiting'] == self:
            GLOBALS['waiting'] = None
        else:
            dc = False
            for game in GLOBALS['games']:
                if game.connection1 == self :
                    GLOBALS['waiting'] = game.connection2
                    dc = True
                elif game.connection2 == self :
                    GLOBALS['waiting'] = game.connection1
                    dc = True
                if dc:
                    gameindex = GLOBALS['games'].index (game)
                    GLOBALS['games'].remove(game)
                    GLOBALS['waiting'].write_message("Disconnected. Waiting for opponent...")
                    break
        print "WebSocket closed"

class PlayHandler(tornado.web.RequestHandler):
    def post(self, *args, **kwargs):
        gameid = int(self.get_argument('gameid'))
        action = self.get_argument('action')
        handnum = int(self.get_argument('handnum'))
        game = GLOBALS['games'][gameid]
        if action == "play":
            card = game.on_trait.hand[handnum]
            if card.play ():
                game.end_turn ()
            else:
                print "No mana"
        elif action == "grow_mana":
            game.on_trait.grow_mana ()
            game.end_turn ()
        elif action == "draw":
            game.on_trait.draw ()
            game.end_turn ()


application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/socket", ClientSocket),
    (r"/play", PlayHandler),
], debug=True)

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
