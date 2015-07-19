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
        self.card_type = all_card_data[num]['card_type']
        self.counter = None

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
        local_dict['counter'] = self.counter
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

class Recycle (SorceryCard):
    def play (self):
        if SorceryCard.play (self):
            card_count = len (self.owner.hand) + 1
            self.owner.graveyard += self.owner.hand 
            self.owner.hand = [] 
            for i in range (card_count):
                self.owner.draw ()
            return True
        return False


class Assassinate (SorceryCard):
    target_required = "opp_creatures"
    def get_target_list (self):
        return self.owner.opponent.creatures
    def play (self, target):
        if target and SorceryCard.play (self):
            target.destroy ()
            return True
        return False

class Unsummon (SorceryCard):
    target_required = "opp_creatures"
    def get_target_list (self):
        return self.owner.opponent.creatures
    def play (self, target):
        if target and SorceryCard.play (self):
            target.owner.creatures.remove(target)
            target.owner.hand += [target]
            return True
        return False

class Blast (SorceryCard):
    def play (self):
        if SorceryCard.play (self):
            for c in self.owner.opponent.creatures:
                if c.creature_strength <= 1:
                    target.destroy ()
            return True
        return False
            
class Doomsday (SorceryCard):
    def play (self):
        if SorceryCard.play (self):
            for card in self.owner.items + self.owner.creatures + \
                    self.owner.opponent.items + self.owner.opponent.creatures:
                card.destroy ()
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

class Hasten (SorceryCard):
    target_required = "hand"
    def get_target_list (self):
        return self.owner.hand
    def play (self, target):
        if target.cost + self.cost > self.owner.cur_mana:
            return False
        SorceryCard.play (self)
        self.game_state.log ("You play "+self.name+" on "+target.name+"<br>",
            "Opponent plays "+self.name+" on "+target.name+"<br>")
        if not target.target_required :
                target.play ()
                return False
        self.game_state.get_target = target.target_required
        self.game_state.send_status ()
        self.owner.extra_turn = True
        return False
    
class Recall (SorceryCard):
    target_required = "graveyard"
    def get_target_list (self):
        return self.owner.graveyard
    def play (self, target):
        if SorceryCard.play (self):
            self.owner.hand += [target]
            self.owner.graveyard.remove(target)
            return True
        return False

class MagicSpells (SorceryCard):
    def play (self):
        if SorceryCard.play (self):
            for i in range (3):
                self.owner.draw ()
            return True
        return False

class WisdomCrown (ItemCard):
    def play (self):
        if ItemCard.play (self):
            pub.subscribe (self.on_play, str(self.game_state.gameid1)+'.play_event')
            return True
        return False
    def on_play (self, card):
        if not self in self.owner.items:
            pub.unsubscribe (self.on_play, str(self.game_state.gameid1)+'.play_event')
            return
        if card.card_type == 'sorcery':
            self.owner.draw ()

class SilenceOrb (ItemCard):
    def play (self):
        if ItemCard.play (self):
            pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
            self.counter = 3
            self.owner.opponent.silencers += [self]
            return True
        return False
    def on_end_turn (self):
        self.counter -= 1
        if self.counter <= 0 :
            self.destroy ()
    def destroy (self):
       pub.unsubscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
       self.counter = 3
       self.owner.opponent.silencers.remove (self)


            
class ManaWell (ItemCard):
    def play (self):
        if ItemCard.play (self):
            pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
            return True
        return False
    def on_end_turn (self):
        if not self in self.owner.items:
            pub.unsubscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
            return
        if self.owner == self.game_state.on_trait:
            self.owner.cur_mana = min (self.owner.cur_mana + 1, self.owner.max_mana)

class DrainingScepter (ItemCard):
    def activate (self):
        if not self.is_activable():
            return False
        self.owner.cur_mana -= 2 
        self.owner.health += 2
        self.owner.opponent.health -= 2
        return False
    def is_activable (self):
        return self.owner.cur_mana > 1 

class PlateMail (ItemCard):
    def play (self):
        if ItemCard.play(self):
            self.owner.armor += 2
            return True
        return False
    def destroy (self):
        self.owner.armor -= 2
        return ItemCard.destroy (self)

class DarkAltar(CreatureCard):
    target_active_required = "creatures"
    def get_target_active_list (self):
        return self.owner.creatures
    def is_activable (self):
        return bool(self.owner.creatures)
    def activate (self, target):
        if not self.is_activable():
            return False
        target.destroy ()
        if target not in self.owner.graveyard ():
            return False
        self.owner.health += target.creature_strength
        self.owner.cur_mana = min (self.owner.max_mana, self.owner.cur_mana + target.creature_strength)
        self.owner.draw ()
        return True

class LongSword (ItemCard):
    def play (self):
        if ItemCard.play(self):
            self.owner.bonus_attack += 2
            return True
        return False
    def destroy (self):
        self.owner.bonus_attack -= 2
        return ItemCard.destroy (self)

class Hatchetry (ItemCard):
    def play (self):
        if ItemCard.play(self):
            pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'end_turn_event')
            return True
        return False
    def on_end_turn (self):
        if self not in self.owner.items:
            pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'end_turn_event')
            return 
        self.owner.creatures.append (CreatureCard (len(all_play_cards)-1, self.game_state, self.owner)) 

class GreenWarden (CreatureCard):
    def play (self):
        if CreatureCard.play (self):
            pub.subscribe (self.on_play, str(self.game_state.gameid1)+'.play_event')
            return True
        return False
    def on_play (self, card):
        if self not in self.owner.creatures:
            pub.unsubscribe (self.on_play, str(self.game_state.gameid1)+'.play_event')
            return 
        if card.card_type == 'creature':
            self.owner.health += 2


class KingBrandt (CreatureCard):
    target_active_required = "creatures"
    def __init__ (self, *args, **kwargs):
        CreatureCard.__init__(self, *args, **kwargs)
        self.boosted_cards = []
        self.counter = 3
        pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
    def get_target_active_list (self):
        return self.owner.creatures
    def is_activable (self):
        return self.owner.cur_mana > 0 and len(self.boosted_cards) < 3
    def on_end_turn (self):
        for c in self.boosted_cards :
            c.creature_strength -= 1
        self.boosted_cards = []
        self.counter = 3
    def activate (self, target):
        if not self.is_activable():
            return False
        self.boosted_cards += [target]
        self.counter -= 1
        target.creature_strength += 1
        self.owner.cur_mana -= 1

class Smith (CreatureCard):
    target_active_required = "creatures"
    def __init__ (self, *args, **kwargs):
        CreatureCard.__init__(self, *args, **kwargs)
        self.boosted_cards = []
        self.counter = 2
    def get_target_active_list (self):
        return self.owner.creatures
    def is_activable (self):
        return self.counter > 0
    def activate (self, target):
        if not self.is_activable():
            return False
        target.creature_strength += 1
        self.counter -= 1

class Warlord (CreatureCard):
    def play (self):
        if CreatureCard.play (self):
            pub.subscribe (self.on_play, str(self.game_state.gameid1)+'.play_event')
            self.creature_strength += len (self.owner.items)
            return True
        return False
    def on_play (self, card):
        if self not in self.owner.creatures:
            pub.unsubscribe (self.on_play, str(self.game_state.gameid1)+'.play_event')
            return 
        if card.card_type == 'item' and card.owner == self.owner:
            self.creature_strength += 1

class Immortal (CreatureCard):
    def destroy (self):
        if self.creature_strength <= 0:
            CreatureCard.destroy (self)

class FireElemental (CreatureCard):
    def play (self):
        if CreatureCard.play (self):
            pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
            return True
        return False
    def on_end_turn (self):
        if not self.owner == self.game_state.on_trait:
            return
        self.creature_strength -= 1
        if self.creature_strength <= 0:
            self.destroy ()
    def destroy (self):
        pub.unsubscribe (self.on_play, str(self.game_state.gameid1)+'.play_event')
        self.creature_strength = 6
        CreatureCard.destroy (self)



class Sorceress (CreatureCard):
    target_active_required = "opp_creatures"
    def __init__ (self, *args, **kwargs):
        CreatureCard.__init__ (self,*args, **kwargs)
        self.counter = 0
    def get_target_active_list (self):
        return self.owner.opponent.creatures
    def is_activable (self):
        return self.counter >= 2
    def play (self):
        if CreatureCard.play (self):
            pub.subscribe (self.on_end_turn, str(self.game_state.gameid1)+'.end_turn_event')
            return True
        return False
    def activate (self, target):
        if not self.is_activable():
            return False
        target.creature_strength -= 1
        if target.creature_strength <= 0:
            target.sacrifice ()
        self.counter -= 2
    def on_end_turn (self):
        if self not in self.owner.creatures:
            pub.unsubscribe (self.on_play, str(self.game_state.gameid1)+'.play_event')
            return 
        if self.owner == self.game_state.on_trait :
            self.counter += 1


class Abomination (CreatureCard):
    def destroy (self):
        for i in range (4):
            self.owner.creatures.append (CreatureCard (len(all_play_cards)-1, self.game_state, self.owner)) 
        CreatureCard.destroy (self)

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
            self.boosted = False

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
    Recycle,
    Assassinate,
    Blast, 
    Unsummon,
    Doomsday, 
    Torment,
    Shatter, 
    Hasten,
    Recall,
    MagicSpells,
    WisdomCrown,
    SilenceOrb,
    ManaWell, 
    DrainingScepter, 
    PlateMail,
    DarkAltar,
    LongSword,
    Hatchetry,
    KingBrandt,
    Smith,
    Immortal,
    FireElemental,
    Sorceress,
    Warlord,
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
    card_data_factory(2, "Recycle", "sorcery","Discard your hand then draw as many cards than before casting Recycle."),
    card_data_factory(4, "Assassinate", "sorcery","Destroy target creature."),
    card_data_factory(4, "Blast", "sorcery","Destroy all opponent creatures of strength 1."),
    card_data_factory(1, "Unsummon", "sorcery","Return target opponent creature in his hand"),

    card_data_factory(6, "Doomsday", "sorcery", "Destroy all creatures and items."),
    card_data_factory(5, "Torment", "sorcery", "Your opponent randomly discards three cards."),
    card_data_factory(2, "Shatter", "sorcery", "Destroy target item"),
    card_data_factory(1, "Hasten", "sorcery", "Play target card for its cost and take an additional turn."),
    card_data_factory(2, "Recall", "sorcery", "Put target card from your graveyard into your hand."),
    card_data_factory(4, "Magic spells", "sorcery", "Draw three cards."),
    card_data_factory(3, "Wisdom crown", "item", "Each time a sorcery is played, draw a card."),
    card_data_factory(3, "Silence orb", "item", "Each time a sorcery is played, draw a card."),
    card_data_factory(2, "Mana well", "item", "Gain 1 mana at the end of your turn."),
    card_data_factory(4, "Draining scepter", "item", "Pay 2 mana: Your opponent looses 2 HP and you gain 2 HP."),
    card_data_factory(3, "Plate mail", "item", "You recieve 2 less damage from each attack."), 
    card_data_factory(3, "Dark altar", "item", "Sacrifice a creature: gain health and mana equal to its strength, and draw a card."),
    card_data_factory(4, "Long sword", "item", "All your attacks recieve a +2 bonus to their attack score."),
    card_data_factory(5, "Hatchetry", "item", "Spawns a crawler at the end of each of your turn.") ]

all_creature_data = [
    card_data_factory(2, "King Brandt", "creature", "Pay 1 mana: Target creature gains +1 strength until the end of turn. Maximum 3 activations per turn.", 2),
    card_data_factory(3, "Smith", "creature", "Remove a counter: Target  creature gains +1 strength.", 1),
    card_data_factory(6, "Immortal", "creature", "Cannot be destroyed.", 3),
    card_data_factory(4, "Fire elemental", "creature", "Looses 1 strength at the end of your turn.", 6),

    card_data_factory(3, "Sorceress", "creature", "Remove two counters: target creature looses 1 strength.Add a counter at the end of your turn.", 1),
    card_data_factory(3, "Warlord", "creature", "Gains +1 strength for every item you control.", 2),
    card_data_factory(4, "Abomination", "creature", "Spawns 4 crawlers when destroyed.", 3),
    card_data_factory(1, "Green Warden", "creature", "Gain 2 life every time a creature is played.", 1),
    card_data_factory(5, "Angel of fury", "creature", "Gains +2 strength when attacking", 4),
    card_data_factory(2, "Chrome berserker", "creature", "Activate to gain +3 strength; if you do, destroy it at the end of turn.", 2),
    card_data_factory(2, "Shadow", "creature", "Gains +1 strength for each other shadow you control", 2),
    card_data_factory(0, "Crawler", "creature", "", 1)
]


all_card_data = all_spell_data + all_creature_data
#for i in range(len(all_card_data)):
#    print all_card_data[i]['name'], all_play_cards[i].__name__
