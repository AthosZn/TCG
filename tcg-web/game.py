from gameshared import *
import random
import json
from pubsub import pub

class PlayerState ():
    """Represent gameplay variables of a player: stats, deck and cards"""
    def __init__ (self, game_state):
        self.health = 20
        self.cur_mana = 2
        self.max_mana = 2
        self.creatures = []
        self.items = []
        self.graveyard = []
        self.hand = [play_card_factory (random.randint (0, len (all_card_data)-1), 
            game_state, self) for i in range (5)]
        self.deck = [play_card_factory (random.randint (0, len (all_card_data)-1), 
            game_state, self) for i in range (55)]

    def draw (self):
        self.hand.append (self.deck.pop ())

    def discard (self, hand_index):
        card = self.hand[hand_index]
        self.graveyard.append (card)
        self.hand.remove (card)

    def grow_mana (self):
        self.max_mana = min (self.max_mana + 1, 10)
        self.cur_mana = self.max_mana

    def visible_state (self, from_self):
        if from_self :
            vis_state = {
            'creatures' : [ c.get_card_data() for c in self.creatures ],
            'items' : [ c.get_card_data() for c in self.items ],
            'hand' : [ c.get_card_data() for c in self.hand ], 
            'graveyard' : [ c.get_card_data() for c in self.graveyard ],
            'health' : self.health,
            'cur_mana' : self.cur_mana,
            'max_mana' : self.max_mana
            }
        else :
            vis_state = {
            'opp_creatures' : [ c.get_card_data() for c in self.creatures ],
            'opp_items' : [ c.get_card_data() for c in self.items ],
            'opp_hand' : len ( self.hand ), 
            'opp_graveyard' : [ c.get_card_data() for c in self.graveyard ],
            'opp_health' : self.health,
            'opp_cur_mana' : self.cur_mana,
            'opp_max_mana' : self.max_mana
            }
        return vis_state

class Game ():
    """Regroup players and their respective connections and variables 
    representing the turn state"""
    def __init__ (self, connection1, connection2, gameid1, gameid2):
        self.gameid1 = gameid1
        self.gameid2 = gameid2
        self.player1 = PlayerState (self)
        self.player2 = PlayerState (self)
        self.player1.opponent = self.player2
        self.player2.opponent = self.player1
        self.connection1 = connection1
        self.connection2 = connection2
        self.on_trait = self.player1
        self.attackers = None
        self.blockers = None
        self.on_block = None
        self.get_killed = None
        self.get_target = None
        self.pending_card = None
        self.pending_active = None
        self.send_status ()

    def dump_state (self,player_from):
        if player_from == self.player1:
            gameid = self.gameid1
        else:
            gameid = self.gameid2
        tempdict = { "self_state": player_from.visible_state(True),
                     "opp_state": player_from.opponent.visible_state(False),
                     "on_trait": self.on_trait==player_from,
                     "attackers": self.attackers or [],
                     "blockers": self.blockers or [],
                     "get_killed": self.get_killed,
                     "gid": gameid,
                     "get_target": self.get_target
                }
        return json.dumps(tempdict)

    def send_status (self):
        self.connection1.write_message(self.dump_state(self.player1))
        self.connection2.write_message(self.dump_state(self.player2))

    def log (self, msg_on_trait, msg_other):
        if self.on_trait == self.player1:
            self.connection1.write_message(json.dumps({"log": msg_on_trait}))
            self.connection2.write_message(json.dumps({"log": msg_other}))
        else:
            self.connection2.write_message(json.dumps({"log": msg_on_trait}))
            self.connection1.write_message(json.dumps({"log": msg_other}))


    def end_turn (self):
        self.attackers = None
        self.blockers = None
        self.on_block = None
        self.get_killed = None
        self.get_target = None
        self.pending_card = None
        self.pending_active = None
        pub.sendMessage (str(self.gameid1)+'.end_turn_event')
        if self.on_trait == self.player1:
            self.on_trait = self.player2
        else:
            self.on_trait = self.player1
        self.log ("--- Your turn ---<br>", "--- Opponent's turn ---<br>")
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
        pub.sendMessage (str(self.gameid1)+'.attack_event', attackers=attacker_cards)
        attacker_names = ', '.join([c.name for c in attacker_cards])
        self.log ("You attack with "+attacker_names+"</br>", 
                "You are attacked by "+attacker_names+"</br>")
        if self.on_block.creatures == []:
            self.attackers = attackers
            self.block_phase ([])
            return
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
        if a_strength > b_strength:
            damage = a_strength - b_strength
            self.on_block.health -= damage
            pub.sendMessage (str(self.gameid1)+'.combat_damage_event', damage)
            self.log ("You dealt %d damage</br>" % damage, 
                    "You suffered %d damage</br>"% damage)
        if blocker_cards == []:
            self.end_turn ()
            return
        blocker_names = ', '.join([c.name for c in blocker_cards])
        self.log ("You are blocked by "+blocker_names+"</br>", 
                "You block with "+blocker_names+"</br>")
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
                for c in killed_cards :
                    c.destroy ()
                for c in blocker_cards :
                    c.destroy ()
                return True
        return False
