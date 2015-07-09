import random
from pubsub import pub

def play_card_factory (num, game_state, owner):
    return all_play_cards[num](num, game_state, owner)

class PlayCard ():
    target_required = None
    target_active_required = None
    def __init__ (self, num, game_state, owner):
        self.game_state = game_state
        self.owner = owner
        self.num = num
        self.cost = all_card_data[num]['cost']
        self.creature_strength = all_card_data[num]['creature_strength']
        self.name = all_card_data[num]['name']
        #self.is_silenced = false 
        self.card_type = all_card_data[num]['card_type']

    def play (self, X=0):
        self.owner = self.game_state.on_trait
        if self.cost == 'X':
            cost = X
        else:
            cost = self.cost
        if self.owner.cur_mana < cost:
            print "No mana: %d for %d" % (self.owner.cur_mana, cost)
            return False
        pub.sendMessage(str(self.game_state.gameid1)+'.play_event', card=self)
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
        local_dict = all_card_data[self.num].copy()
        local_dict['creature_strength'] = self.creature_strength
        if self in self.owner.creatures or self in self.owner.items:
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
    target_required = "opp_creatures"
    def get_target_list (self):
        return self.owner.opponent.creatures
    def play (self, target):
        if target and SorceryCard.play (self):
            target.destroy ()
            return True
        return False
            
class Doomsday (SorceryCard):
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
    target_required = "opp_items"
    def get_target_list (self):
        return self.owner.opponent.items
    def play (self, target):
        if target and SorceryCard.play (self):
            target.destroy ()
            return True
        return False

class Fasten (SorceryCard):
    target_required = "hand"
    def get_target_list (self):
        return self.owner.hand
    def play (self, target):
        if target.cost + self.cost <= self.owner.cur_mana:
            if target.play ():
                SorceryCard.play (self)
                self.game_state.log ("You play "+self.name+" on "+target.name+"<br>",
                    "Opponent plays "+self.name+" on "+target.name+"<br>")

        return False

class WisdomCrown (ItemCard):
    def play (self):
        if ItemCard.play (self):
            pub.subscribe (self.on_play, str(self.game_state.gameid1)+'.play_event')
            return True
        return False
    def on_play (self, card):
        if self.game_state.on_trait == self.owner and card.card_type == 'sorcery':
            self.owner.draw ()
            
class ManaWell (ItemCard):
    def play (self):
        if ItemCard.play (self):
            pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
            return True
        return False
    def on_end_turn (self):
        if self.owner == self.game_state.on_trait:
            self.owner.cur_mana = min (self.owner.cur_mana + 1, self.owner.max_mana)

class DrainingScepter (ItemCard):
    def activate (self):
        if not self.is_activable():
            return False
        self.owner.cur_mana -= 2
        self.owner.health += 1
        self.owner.opponent.health -= 1
        return False
    def is_activable (self):
        return self.owner.cur_mana > 1 

class GreenWarden (CreatureCard):
    def play (self):
        if CreatureCard.play (self):
            pub.subscribe (self.on_play, str(self.game_state.gameid1)+'.play_event')
            return True
        return False
    def on_play (self, card):
        if self.game_state.on_trait == self.owner and card.card_type == 'creature':
            self.owner.health += 2

class KingBrandt (CreatureCard):
    target_active_required = "creatures"
    def __init__ (self, *args, **kwargs):
        CreatureCard.__init__(self, *args, **kwargs)
        self.boosted_cards = []
        pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
    def get_target_active_list (self):
        return self.owner.creatures
    def is_activable (self):
        return self.owner.cur_mana > 0 and len(self.boosted_cards) < 3
    def on_end_turn (self):
        for c in self.boosted_cards :
            c.creature_strength -= 1
        self.boosted_cards = []
    def activate (self, target):
        if not self.is_activable():
            return False
        self.boosted_cards += [target]
        target.creature_strength += 1
        self.owner.cur_mana -= 1

class Abomination (CreatureCard):
    def play (self):
        if CreatureCard.play (self):
            pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
            return True
        return False
    def on_end_turn (self):
        if self in self.owner.graveyard:
            pub.unsubscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
            for i in range (4):
                self.owner.creatures.append (CreatureCard (15, self.game_state, self.owner)) 


class AngelOfFury (CreatureCard):
    def __init__ (self, *args, **kwargs):
        CreatureCard.__init__(self, *args, **kwargs)
        self.boosted = False
        pub.subscribe (self.on_attack, str(self.game_state.gameid1)+'.attack_event')
        pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
    def on_attack (self, attackers):
        if self in attackers :
            self.creature_strength += 2
            self.boosted = True
    def on_end_turn (self):
        if self.boosted :
            self.creature_strength -= 2

class ChromeBerserker (CreatureCard):
    def play (self):
        if CreatureCard.play (self):
            self.boosted = False
            return True
        return False
    def is_activable (self):
        return not self.boosted
    def activate (self):
        if not self.boosted:
            self.creature_strength += 3
            self.boosted = True
            pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
    def on_end_turn (self):
        pub.unsubscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
        self.destroy ()


class Shadow (CreatureCard):
    def play (self):
        if CreatureCard.play (self):
            for c in self.owner.creatures :
                if c.num == self.num and c != self:
                    c.creature_strength += 1
                    self.creature_strength += 1
            return True
        return False

all_play_cards = [
    Blast, 
    Doomsday, 
    Torment,
    Shatter, 
    Fasten,
    WisdomCrown,
    ManaWell, 
    DrainingScepter, 
    KingBrandt,
    CreatureCard,
    Abomination,
    GreenWarden,
    AngelOfFury,
    ChromeBerserker,
    Shadow,
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
    card_data_factory(4, "Blast", "sorcery","Destroy target creature."),
    card_data_factory(6, "Doomsday", "sorcery", "Destroy all creatures and items."),
    card_data_factory(5, "Torment", "sorcery", "Your opponent randomly discards three cards."),
    card_data_factory(2, "Shatter", "sorcery", "Destroy target item"),
    card_data_factory(2, "Fasten", "sorcery", "Play target card for its cost and take an additional turn."),
    card_data_factory(3, "Wisdom crown", "item", "Each time you play a sorcery, draw a card."),
    card_data_factory(3, "Mana well", "item", "Gain 1 mana at the end of your turn."),
    card_data_factory(2, "Draining scepter", "item", "Pay 2 mana: Your opponent looses 1 life and you gain 1 life.") ]

all_creature_data = [
    card_data_factory(2, "King Brandt", "creature", "Pay 1 mana: Target creature gains +1 strength until the end of turn. Maximum 3 activations per turn.", 2),
    card_data_factory(3, "Mercenary", "creature", "--", 3),
    card_data_factory(4, "Abomination", "creature", "Spawns 4 crawlers when destroyed.", 3),
    card_data_factory(1, "Green Warden", "creature", "Gain 2 life every time a creature is played.", 1),
    card_data_factory(5, "Angel of fury", "creature", "Gains +2 strength when attacking", 4),
    card_data_factory(2, "Chrome berserker", "creature", "Activate to gain +3 strength; if you do, destroy it at the end of turn.", 2),
    card_data_factory(2, "Shadow", "creature", "Gains +1 strength for each other shadow you control", 2),
    card_data_factory(0, "Crawler", "creature", "--", 1)
]


all_card_data = all_spell_data + all_creature_data
