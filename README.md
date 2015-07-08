# Twisted Card Game

TCG is a collectible card game over network. Two players confront in a duel in
which they can play a variety of cards with special abilities. First player at
zero health looses. Full rules available below.

The game is forked in two sub-projects which are both early developpement. One
branch uses pygame as a display and twisted as a backend, the other, more 
advanced, uses websockets and web (HTML + javascript) display.

For any question, contact arthurhavlicek@gmail.com

## Installing and playing

### Pygame version

Pygame version depends on *pygame* version 1.9 or greater, *twisted* version 14
and is a project written for *python 2.7*.
To launch a game, run a server.py with python, then connect both clients 
(cards.py) to it. The IPs are hard coded in the .py scripts, you can modify 
them if you intend to use this on a non-localhost way.

### Web version

Pygame version depends on *tornado* version 4.2 and is a project written for 
*python 2.7*. It also uses HTML5, javascript and AJAX, and is playable with any
up-to-date web browser. 
To launch a game, run the server with python, then connect with a web browser
to its url. This url is hardcoded in the server.py and sse.js, modify them if
you need a non-localhost setting.

## Game rules

TCG is a card game, where cards can hold a few properties. They have a unique
and distinguishing name, a cost, and a type. Each card require its cost to be
payed in mana to apply its special effects. There is three types of cards in 
TCG:
* Sorceries. They do their special effect when played, then are discarded.
* Items. They can apply a passive effect while they remain in play, or apply an 
active effect when activated.
* Creatures. They can combat on the battlefield and damage your opponent, and
may have extra abilities.

The game is played turn by turn. On his turn, the player can either:
* Play a card from his hand
* Draw a card from his deck
* Launch an attack with his creatures, if he have any
* Increase his mana. If he does so, his maximum mana is increased by one up to a
maximum of ten, and his current mana is refilled to this new maximum. 

All these actions end his turn. He can also activate an item or a creature he
controls; this does not end his turn unless stated otherwise.

### Combat

Creatures have an extra statistic the other cards doesn't have, which is their
strength. Creature strength represent the ability to combat and affect the
damage they can inflict to players, to other creatures, and the damage they can
block from attacks.

An attack phase is a sightly more complex phase than other TCG turns. It 
follows these steps :
* Attacker declares which creatures he is willing to attack with. We will call
attack strength the total of strength of these creatures.
* Blocker declares which creatures he is willing to block with. Similarly, we
will call blocker strength the total of strength of blockers.
* The blocker looses health equivalent to attack strength - blocker strength.
* The blocker chooses which attackers he wants to kill. Their total strength
must not exceed his block strength.
* He also declares which blockers he wants to sacrifice. As long as the attack
strength is superior to the strength of one of his creature, he must choose a
creature to sacrifice and remove its strength from attack strength. Example:
blocker has three creatures of respective strength 3, 1, and 1, and blocks
an attack of strength 4 with them. He sacrifices the two weakest creatures, the
remaining attack strength is 2, so his creature of strength 3 can survive.


