import random

def play_card_factory (num, game_state, owner):
    return all_play_cards[num](num, game_state, owner)

class PlayCard ():
    def __init__ (self, num, game_state, owner):
        self.game_state = game_state
        self.owner = owner
        self.num = num
    def play (self, X=0):
        self.owner = self.game_state.on_trait
        if all_card_data[self.num]['cost'] == "X":
            cost = X
        else:
            cost = int (all_card_data[self.num]['cost'])
        if self.owner.cur_mana < cost:
            return False
        for c in self.game_state.player1.creatures :
            c.on_play (self)
        for c in self.game_state.player2.creatures :
            c.on_play (self)
        for c in self.game_state.player1.items :
            c.on_play (self)
        for c in self.game_state.player2.items :
            c.on_play (self)
        self.owner.cur_mana -= cost 
        self.owner.hand.remove (self)
        return True
    def on_play (self, card):
        pass
    def activate (self):
        pass

class ItemCard (PlayCard):
    def play (self, X=0):
        ret = PlayCard.play (self, X)
        if ret:
            self.owner.items.append (self)
        return ret

class SorceryCard (PlayCard):
    def play (self, X=0):
        ret = PlayCard.play (self, X)
        if ret:
            self.owner.graveyard.append (self)
        return ret

class CreatureCard (PlayCard):
    def play (self, X=0):
        ret = PlayCard.play (self, X)
        if ret:
            self.owner.creatures.append (self)
        return ret


class Blast (SorceryCard):
    def play (self, target = None, X=0):
        #target = get_target (lambda f (target) : return target.creature_strength )
        if target and PlayCard.play (self, X):
            return True
            #target.destroy ()
        return False
            
class DoomsDay (SorceryCard):
    def play (self):
        if SorceryCard.play (self):
            self.game_state.player1.graveyard += self.game_state.player1.creatures
            self.game_state.player1.graveyard += self.game_state.player1.items
            self.game_state.player1.creatures = []
            self.game_state.player1.items = []
            self.game_state.player2.graveyard += self.game_state.player2.creatures
            self.game_state.player2.graveyard += self.game_state.player2.items
            self.game_state.player2.creatures = []
            self.game_state.player2.items = []
            return True
        return False

class Torment (SorceryCard):
    def play (self):
        if SorceryCard.play (self):
            if self == self.game_state.player1:
                opp = self.game_state.player2
            else:
                opp = self.game_state.player1
            for i in range(2):
                ind = random.randint (0, len(opp.hand)-1)
                opp.graveyard.append (opp.hand[ind])
                del opp.hand[ind]
            return True
        return False
    

class Shatter (SorceryCard):
    def play (self, target = None):
        #target = get_target
        if target and SorceryCard.play (self):
            return True
        return False

class WisdomCrown (ItemCard):
    def on_play (self, card):
        if self.game_state.on_trait == self.owner and all_cards_data[card.num]['card_type'] == 'sorcery':
            self.owner.draw ()

class GreenWarden (CreatureCard):
    def on_play (self, card):
        if self.game_state.on_trait == self.owner and all_cards_data[card.num]['card_type'] == 'creature':
            self.owner.health += 2

all_play_cards = [
    Blast, 
    DoomsDay, 
    Torment,
    SorceryCard,
    Shatter, 
    WisdomCrown,
    ItemCard, 
    ItemCard, 
    CreatureCard,
    CreatureCard,
    CreatureCard,
    GreenWarden,
    CreatureCard,
    CreatureCard,
    CreatureCard
    ]
    
def card_data_factory (cost, name, card_type, desc_text, creature_strength=None):
    return {
        "cost" : cost,
        "name" : name,
        "card_type" : card_type,
        "desc_text" : desc_text,
        "creature_strength" : creature_strength }

all_card_data = [
    card_data_factory("X", "Blast", "sorcery","Destroy target creature of strength X or less."),
    card_data_factory("6", "Doom's Day", "sorcery", "Destroy all creatures and items."),
    card_data_factory("4", "Torment", "sorcery", "Your randomly discards two cards."),
    card_data_factory("2", "Shatter", "sorcery", "Destroy target item"),
    card_data_factory("3", "Wisdom crown", "item", "Each time you play a sorcery, draw a card."),
    card_data_factory("3", "Soothing robe", "item", "At the end of your turn, if you have less than 10 life, gain 1 life."),
    card_data_factory("3", "Draining scepter", "item", "Pay 2 mana: Your opponent looses 1 life and you gain 1 life."),
    card_data_factory("2", "King Brandt", "creature", "Pay 2 mana: Target creature gains +1 strength until the end of turn.", 2),
    card_data_factory("3", "Mercenary", "creature", "", 3),
    card_data_factory("1", "Blue Warden", "creature", "If a creature you control is destroyed by a spell or an ability, draw a card.", 1),
    card_data_factory("1", "Green Warden", "creature", "Gain 2 life every time a creature is played.", 1),
    card_data_factory("1", "Gray Warden", "creature", "Cancels all opponent items effects as long as alive.", 1),
    card_data_factory("2", "Elven archers", "creature", "When fighting grouped with a creature, gains +2 strength.", 1),
    card_data_factory("3", "Shadow", "creature", "Cannot be blocked.", 1)
]
