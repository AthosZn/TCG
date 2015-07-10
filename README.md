# Twisted Card Game

TCG is a collectible card game over network. Two players confront in a duel in
which they can play a variety of cards with special abilities. First player at
zero health looses. 

The game is forked in two sub-projects which are both early developpement. One
branch uses pygame as a display and twisted as a backend, the other, more 
advanced, uses websockets and web (HTML + javascript) display.

You can read the rules and play the game at http://195.154.45.210

For any question, contact arthurhavlicek@gmail.com

## Installing and playing

### Pygame version

Pygame version depends on **pygame** version 1.9 or greater, **twisted** version
14 and is a project written for **python 2.7**.
To launch a game, run a server.py with python, then connect both clients 
(cards.py) to it. The IPs are hard coded in the .py scripts, you can modify 
them if you intend to use this on a non-localhost way.

### Web version

Pygame version depends on **tornado** version 4.2 and is a project written for 
**python 2.7**. It also uses HTML5, javascript and AJAX, and is playable with 
any up-to-date web browser. 
To launch a game, run the server with python, then connect with a web browser
to its url. This url is hardcoded in the server.py and sse.js, modify them if
you need a non-localhost setting.

## Game rules

See http://195.154.45.210/rules
