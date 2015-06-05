#!/usr/bin/env python

#Import Modules
import os, pygame
from pygame.locals import *
from pygame.compat import geterror
import json 
import sys

#Twisted
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor

#custom module containing card database
from gameshared import *


class PlayerState ():
    def __init__ (self):
        self.hand = []
        self.graveyard = []
        self.grave_top = None
        self.creatures = []
        self.enchants = []

self_state = PlayerState ()
opp_state = PlayerState ()
CONNECTIONS = []

def set_conn (conn):
    CONNECTIONS.append(conn)

class EchoClient(LineReceiver):

    def connectionMade(self):
        set_conn (self)

    def lineReceived(self, line):
        if "[OK]" in line :
            set_conn (self)
            return
        obj = json.loads (line)
        print "receive:", obj

        if obj["from_self"] :
            self_state.hand = self._up_list (obj["hand"], self_state.hand)
            player = self_state
        else :
            for card in opp_state.hand :
                card.erase ()
            opp_state.hand = [
                    SimpleSprite ("Carte_dos_mini.png", 1000, 5 + 41 * i)
                    for i in range(obj["hand"]) 
                    ]
            player = opp_state
        player.creatures = self._up_list (obj["creatures"], player.creatures)
        player.enchants = self._up_list (obj["enchants"], player.enchants)
        player.graveyard = self._up_list (obj["graveyard"], player.graveyard) 
    def _up_list (self, data, card_list):
        for card in card_list :
            card.erase()
        card_list = [ card_factory (index) for index in data ]
        return card_list


class EchoClientFactory(ClientFactory):
    protocol = EchoClient

    def clientConnectionFailed(self, connector, reason):
        print 'connection failed:', reason.getErrorMessage()
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        print 'connection lost:', reason.getErrorMessage()
        #reactor.stop()


from itertools import chain

 
def truncline(text, font, maxwidth):
    real=len(text)       
    stext=text           
    l=font.size(text)[0]
    cut=0
    a=0                  
    done=1
    old = None
    while l > maxwidth:
        a=a+1
        n=text.rsplit(None, a)[0]
        if stext == n:
            cut += 1
            stext= n[:-cut]
        else:
            stext = n
        l=font.size(stext)[0]
        real=len(stext)               
        done=0                        
    return real, done, stext             
        
def wrapline(text, font, maxwidth): 
    done=0                      
    wrapped=[]                  
                               
    while not done:             
        nl, done, stext=truncline(text, font, maxwidth) 
        wrapped.append(stext.strip())                  
        text=text[nl:]                                 
    return wrapped
 
 
def wrap_multi_line(text, font, maxwidth):
    """ returns text taking new lines into account.
    """
    lines = chain(*(wrapline(line, font, maxwidth) for line in text.splitlines()))
    return list(lines)


if not pygame.font: print ('Warning, fonts disabled')
if not pygame.mixer: print ('Warning, sound disabled')


main_dir = os.path.split(os.path.abspath(__file__))[0]
data_dir = os.path.join(main_dir, 'data')

#functions to create our resources
def load_image(name, colorkey=None):
    fullname = os.path.join(data_dir, name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error:
        print ('Cannot load image:', fullname)
        raise SystemExit(str(geterror()))
    return image, image.get_rect()

def load_sound(name):
    class NoneSound:
        def play(self): pass
    if not pygame.mixer or not pygame.mixer.get_init():
        return NoneSound()
    fullname = os.path.join(data_dir, name)
    try:
        sound = pygame.mixer.Sound(fullname)
    except pygame.error:
        print ('Cannot load sound: %s' % fullname)
        raise SystemExit(str(geterror()))
    return sound

#    whiff_sound = load_sound('whiff.wav')
#    whiff_sound.play() 

#        pos = pygame.mouse.get_pos()
#        self.rect.midtop = pos
#            self.rect.move_ip(5, 10)

#            hitbox = self.rect.inflate(-5, -5)
#            return hitbox.colliderect(target.rect)

#        newpos = self.rect.move((self.move, 0))
#            self.image = pygame.transform.flip(self.image, 1, 0)

        #center = self.rect.center
            #rotate = pygame.transform.rotate
            #self.image = rotate(self.original, self.dizzy)
        #self.rect = self.image.get_rect(center=center)


background, bg_rect = load_image("bg.jpg")

pygame.init()
ALL_SPRITES = pygame.sprite.OrderedUpdates(())

#classes for our game objects

class SimpleSprite (pygame.sprite.Sprite):
    """ Simple sprites refreshed every frame """
    def __init__(self, image_name, x=0, y=0, flipped=False):
        pygame.sprite.Sprite.__init__(self) #call Sprite initializer
        self.image, self.rect = load_image(image_name)
        ALL_SPRITES.add (self)
        self.rect.x, self.rect.y = x, y

    def erase (self):
        ALL_SPRITES.remove (self)

class TextSprite (pygame.sprite.Sprite):
    """ Text sprites, can be re-used through set_text """
    def __init__ (self, text, size, color, x=0, y=0):
        pygame.sprite.Sprite.__init__(self) #call Sprite initializer
        self.font = pygame.font.SysFont("Verdana", size)
        self.color = color
        self.image = self.font.render(text, True, color)
        (w, h) = self.font.size (text)
        self.rect = pygame.Rect (x, y, w, h)
        ALL_SPRITES.add (self)

    def set_text (self, text):
        self.image = self.font.render (text, True, self.color)
        (w, h) = self.font.size (text)

    def erase (self):
        ALL_SPRITES.remove (self)

class DescriptionText ():
    def __init__(self):
        """ This class handles the description of card abilities when 
        hoovering a card with the mouse """
        self.sprites = [TextSprite ("", 15, (0,0,0))
                for i in range(6)] 
        for i in range(6):
            self.sprites[i].rect = pygame.Rect (30, 450 + 20 * i, 200, 120)

    def update (self, text):
        word_list = wrap_multi_line(text, self.sprites[0].font, 200)
        word_list = word_list[:6]
        for i in range (6) :
            if i < len (word_list):
                self.sprites[i].set_text (word_list[i]) 
            else:
                self.sprites[i].set_text ("") 
DESC_TEXT = DescriptionText ()

class Card (SimpleSprite):
    """Handles card data and behavior"""
    def __init__(self, sprite_name, card_index):
        SimpleSprite.__init__(self, sprite_name)
        self.data = all_cards [card_index] 

        self.text_sprite = TextSprite (self.data.name, 9, (0,0,0))
        self.cost_sprite = TextSprite (self.data.cost, 12, (0,0,0))

        #screen = pygame.display.get_surface()
        #self.area = screen.get_rect()

    def update(self):
        """Callback, called every update"""
        if self.rect.collidepoint(pygame.mouse.get_pos()):
            DESC_TEXT.update ( self.data.desc_text )

    def play (self):
        CONNECTIONS[0].sendLine ("[\"play\", %d]" % self_state.hand.index(self))
        #self_state.hand.remove (self)

    def go_to (self, x, y):
        self.rect.x = x
        self.rect.y = y

        text_w, text_h = self.text_sprite.font.size (str(self.data.cost))
        self.cost_sprite.rect = self.rect.move(20-text_w/2,20-text_h/2)

        text_w, text_h = self.text_sprite.font.size (self.data.name)
        self.text_sprite.rect = self.rect.move(34,21-text_h/2)

    def erase(self):
        SimpleSprite.erase(self)
        self.text_sprite.erase ()
        self.cost_sprite.erase ()

class Creature (Card):
    def __init__ (self, card_index):
        Card.__init__ (self, "Carte_face_creat.png", card_index)
        self.strength_sprite = TextSprite (str (self.data.creature_strength), 12, (0,0,0))

    def go_to (self, x, y):
        Card.go_to (self, x, y)
        text_w, text_h = self.text_sprite.font.size (str (self.data.creature_strength))
        self.strength_sprite.rect = self.rect.move (113-text_w/2,20-text_h/2)

    def erase(self):
        Card.erase(self)
        self.strength_sprite.erase()

class Enchant (Card):
    def __init__ (self, card_index):
        Card.__init__ (self, "Carte_face.png", card_index)

class Sorcery (Card):
    def __init__ (self, card_index):
        Card.__init__ (self, "Carte_face.png", card_index)

    def play (self):
        Card.play (self)

def card_factory (card_index):
    if all_cards [card_index].creature_strength :
        return Creature (card_index)
    if all_cards [card_index].is_enchant :
        return Enchant (card_index)
    return Sorcery (card_index)

class Gauge(SimpleSprite):
    """Handles health points and behavior"""
    def __init__(self, bg, initial_amount, x=0, y=0):
        SimpleSprite.__init__(self, bg, x, y)
        self.max_amount = initial_amount 
        self.current_amount = initial_amount 
        self.text_sprite = TextSprite ("%d/%d" % 
                (self.current_amount, self.max_amount), 15, (0,0,0))
        self.text_sprite.rect.center = self.rect.center

    def _text_up(self):
        text = str("%d/%d" % 
                (self.current_amount, self.max_amount))
        self.text_sprite.set_text (text)
        self.text_sprite.rect.center = self.rect.center


    def update (self):
        self._text_up()
        self.text_sprite.update()


class UI_Sprites ():
    def __init__ (self):
        self.mana = Gauge ("Mana.png",2, 220, 595)
        self.opp_mana = Gauge ("Mana.png",2, 220, 145)

        self.health = Gauge ("Health.png",20, 150, 595)
        self.opp_health = Gauge ("Health.png",20, 150, 145)

        self.deck = SimpleSprite ("Carte_dos.png", 5, 580)
        self.opp_deck = SimpleSprite ("Carte_dos.png", 5, 5)

        self.hand_border = SimpleSprite ("Main.png", 995, 570)
        self.opp_hand_border = SimpleSprite ("Main.png", 995, 5)

def game_loop (UI):
    reactor.callLater(1./60, game_loop, UI)
    for i in range (min (5, len (self_state.hand))):
        card = self_state.hand[i]
        card.go_to (1000, 575 + 41 * i)
    for i in range (5, max (5, len (self_state.hand))):
        card = self_state.hand[i]
        card.go_to (1135, 370 + 41 * i)
    for card in self_state.creatures:
        card.go_to (500, 575 + 41 * self_state.creatures.index(card))
    for card in self_state.enchants:
        card.go_to (700, 575 + 41 * self_state.enchants.index(card))
    for card in self_state.graveyard:
        card.go_to (140, 655) # Stack the cards. 
                              # TODO: only draw top card would perform better
        
    # Same as above with different positions
    for card in opp_state.creatures:
        card.go_to (500, 10 + 41 * opp_state.creatures.index(card))
    for card in opp_state.enchants:
        card.go_to (700, 10 + 41 * opp_state.enchants.index(card))
    for card in opp_state.graveyard:
        card.go_to (140, 10) 
        
    ALL_SPRITES.update()
    #Draw Everything
    screen.blit(background, (0, 0))
    ALL_SPRITES.draw(screen)
    pygame.display.flip()
    #Handle Input Events
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            reactor.stop()
        elif event.type == KEYDOWN and event.key == K_ESCAPE:
            pygame.quit()
            reactor.stop()
        elif event.type == MOUSEBUTTONDOWN:
            for card in self_state.hand :
                toprect = card.rect.copy ()
                toprect.h = 41
                if toprect.collidepoint(pygame.mouse.get_pos()):
                    card.play ()
            rect = UI.deck.rect
            if rect.collidepoint(pygame.mouse.get_pos()):
                CONNECTIONS[0].sendLine("[\"draw\"]")
        elif event.type == MOUSEBUTTONUP:
            pass

screen = pygame.display.set_mode((1280, 800))

def main():
    """this function is called when the program starts.
       it initializes everything it needs, then runs in
       a loop until the function returns."""
#Initialize Everything
    pygame.display.set_caption('Card Game')
    #pygame.mouse.set_visible(0)

#Create The Backgound

#Put Text On The Background, Centered

#Display The Background
    screen.blit(background, (0, 0))
    pygame.display.flip()

#Prepare Game Objects
    #clock = pygame.time.Clock()
    factory = EchoClientFactory()
    reactor.connectTCP('localhost', 8000, factory)
    UI = UI_Sprites ()
    game_loop (UI)
    reactor.run ()

#Game Over


#this calls the 'main' function when this script is executed
if __name__ == '__main__':
    main()
