

class CardData ():
    def __init__ (self, cost, name, desc_text, creature_strength=None, is_enchant=False):
        self.cost = cost
        self.name = name
        self.desc_text = desc_text
        self.creature_strength = creature_strength
        self.is_enchant = is_enchant

all_cards = [
CardData("3", "Refreshing winds", "Each time you play a sorcery, draw a card.", None , True),
CardData("2", "King Brandt", "Pay 2 mana: Target creature gains +1 strength until the end of turn.", 2),
CardData("3", "Mercenary", "During a creature untap phase, you must pay 1 mana to untap the mercenary or leave it tapped.", 3),
CardData("X", "Blast", "Destroy target creature of strength X or less."),
CardData("1", "Blue Warden", "If a creature you control is destroyed by a spell or an ability, draw a card.", 1),
CardData("1", "Green Warden", "Gain 2 life every time a creature is played.", 1),
CardData("3", "Resilience", "At the end of your turn, if you have less than 10 life, gain 1 life.", None , True)
]
    
