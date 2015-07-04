import random
from pubsub import pub

def play_card_factory (num, game_state, owner):
    return all_play_cards[num](num, game_state, owner)

class PlayCard ():
    def __init__ (self, num, game_state, owner):
        self.game_state = game_state
        self.owner = owner
        self.num = num
        self.cost = all_card_data[num]['cost']
        self.creature_strength = all_card_data[num]['creature_strength']
        #self.is_silenced = false 
        self.card_type = all_card_data[num]['card_type']

    def play (self, X=0):
        self.owner = self.game_state.on_trait
        if self.cost == 'X':
            cost = X
        else:
            cost = int(self.cost)
        if self.owner.cur_mana < cost:
            return False
        pub.sendMessage('play_event', card=self)
        self.owner.cur_mana -= cost 
        self.owner.hand.remove (self)
        return True
    def activate (self):
        pass
    def is_activable (self):
        return False
    def destroy (self):
        pass 
    def get_card_data (self):
        local_dict = all_card_data[self.num]
        local_dict['creature_strength'] = self.creature_strength
        local_dict['is_activable'] = self.is_activable ()
        return local_dict

class ItemCard (PlayCard):
    def play (self, X=0):
        ret = PlayCard.play (self, X)
        if ret:
            self.owner.items.append (self)
        return ret
    def destroy (self):
        self.owner.items.remove (self)
        self.owner.graveyard.append (self)

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
    def destroy (self):
        self.owner.creatures.remove (self)
        self.owner.graveyard.append (self)

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
            if self.owner == self.game_state.player1:
                opp = self.game_state.player2
            else:
                opp = self.game_state.player1
            if len(opp.hand) < 4:
                opp.graveyard += opp.hand
                opp.hand = []
                return True
            for i in range(3):
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
    def play (self):
        if ItemCard.play (self):
            pub.subscribe (self.on_play, 'play_event')
            return True
        return False
    def on_play (self, card):
        if self.game_state.on_trait == self.owner and card.card_type == 'sorcery':
            self.owner.draw ()

class DrainingScepter (ItemCard):
    def activate (self):
        if not self.is_activable():
            return
        self.owner.cur_mana -= 2
        self.owner.health += 1
        if self.owner == self.game_state.player1:
            self.game_state.player2.health -= 1
        else:
            self.game_state.player1.health -= 1
    def is_activable (self):
        return self.owner.cur_mana > 1

class GreenWarden (CreatureCard):
    def play (self):
        if CreatureCard.play (self):
            pub.subscribe (self.on_play, 'play_event')
            return True
        return False
    def on_play (self, card):
        if self.game_state.on_trait == self.owner and card.card_type == 'creature':
            self.owner.health += 2

class AngelOfFury (CreatureCard):
    def __init__ (self, *args, **kwargs):
        CreatureCard.__init__(self, *args, **kwargs)
        self.boosted = False
        pub.subscribe (self.on_attack, 'attack_event')
        pub.subscribe (self.on_end_turn, 'end_turn_event')
    def on_attack (self, attackers):
        if self in attackers :
            self.creature_strength += 2
            self.boosted = True
    def on_end_turn (self):
        if self.boosted :
            self.creature_strength -= 2

all_play_cards = [
    Blast, 
    DoomsDay, 
    Torment,
    Shatter, 
    WisdomCrown,
    ItemCard, 
    DrainingScepter, 
    CreatureCard,
    CreatureCard,
    CreatureCard,
    GreenWarden,
    AngelOfFury,
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

all_spell_data = [
    card_data_factory("X", "Blast", "sorcery","Destroy target creature of strength X or less."),
    card_data_factory("6", "Doom's Day", "sorcery", "Destroy all creatures and items."),
    card_data_factory("4", "Torment", "sorcery", "Your opponent randomly discards three cards."),
    card_data_factory("2", "Shatter", "sorcery", "Destroy target item"),
    card_data_factory("3", "Wisdom crown", "item", "Each time you play a sorcery, draw a card."),
    card_data_factory("3", "Soothing robe", "item", "At the end of your turn, if you have less than 10 life, gain 1 life."),
    card_data_factory("2", "Draining scepter", "item", "Pay 2 mana: Your opponent looses 1 life and you gain 1 life.") ]

all_creature_data = [
    card_data_factory("2", "King Brandt", "creature", "Pay 2 mana: Target creature gains +1 strength until the end of turn.", 2),
    card_data_factory("3", "Mercenary", "creature", "--", 3),
    card_data_factory("1", "Blue Warden", "creature", "If an other creature you control is destroyed by a spell or an ability, draw a card.", 1),
    card_data_factory("1", "Green Warden", "creature", "Gain 2 life every time a creature is played.", 1),
    card_data_factory("5", "Angel of fury", "creature", "Gains +2 strength when attacking", 4),
    card_data_factory("2", "Elven archers", "creature", "When fighting grouped with a creature, gains +2 strength.", 1),
    card_data_factory("3", "Shadow", "creature", "--", 1)
]

all_card_data = all_spell_data #+ all_creature_data
