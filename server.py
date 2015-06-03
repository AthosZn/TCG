import json

from twisted.internet import reactor, protocol, endpoints
from twisted.protocols import basic

from gameshared import *

class Card ():
    def __init__ (self, card_id):
        self.card_id = card_id
        self.name = "King Brandt"
        self.creature = True

class PlayerState ():
    def __init__ (self):
        self.health = 20
        self.cur_mana = 2
        self.max_mana = 2
        self.hand = [0,1,2,3,3] 
        self.deck = [4] * 50 
        self.creatures = []
        self.enchants = []
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

    def play (self, hand_index):
        card = self.hand[hand_index]
        data = all_cards [card]
        if data.creature_strength:
            self.creatures.append (card)
        elif data.is_enchant:
            self.enchants.append (card)
        else:
            self.graveyard.append (card)
        self.hand.remove (card)

    def visible_state (self, from_self=False):
        vis_state = self.__dict__.copy()
        vis_state["from_self"] = from_self
        if not from_self:
            # Deleting what shouldnt be visible
            vis_state["hand"] = len (vis_state["hand"]) 
        del vis_state["deck"]
        return json.dumps(vis_state)

class PubProtocol(basic.LineReceiver):
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        self.sendLine ("[OK]")
        self.factory.clients.add (self)
        self.state = PlayerState ()
        self.player_actions = { 
                "play" : self.state.play,
                "draw" : self.state.draw,
                "discard" : self.state.discard,
                "kill" : self.state.kill
                }
        self._send_update ()

    def connectionLost(self, reason):
        self.factory.clients.remove(self)

    def _send_update (self):
        self.sendLine (self.state.visible_state (True))
        for c in self.factory.clients:
            if c != self:
                c.sendLine(self.state.visible_state())

    def lineReceived(self, line):
        obj = json.loads (line)
        func = self.player_actions[obj[0]]
        func (*obj[1:])
        self._send_update ()

class PubFactory(protocol.Factory):
    def __init__(self):
        self.clients = set()

    def buildProtocol(self, addr):
        return PubProtocol(self)

endpoints.serverFromString(reactor, "tcp:8000").listen(PubFactory())
reactor.run()

