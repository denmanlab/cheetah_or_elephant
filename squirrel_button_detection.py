import glob, time
from numpy import random
from pyfirmata import ArduinoMega, util, INPUT

#set up image and gameplay resources===============================
import pyglet
pyglet.resource.path = ['./models']
pyglet.resource.reindex()
game_window = pyglet.window.Window(800, 600)
grating_image = pyglet.resource.image('grating.jpg')
grating_image.anchor_x = grating_image.width // 2 #center image
sprite = pyglet.sprite.Sprite(grating_image, x = 100, y = 300)
#====================================================================

# set up simple class that does nothing but hold parameter states
class Params():
    def __init__(self):
        self.iti,self.bool_iti,self.bool_display,self.bool_reward_window,self.reward_vol,self.answer,self.bool_correct,self.time_,self.last_end_time, self.stim_on = \
            3.0,True,False,False,10,'left',False,0.0,0.0, False #initialize task control variables

        self.center_button = 0
params = Params()
#====================================================================

# set up global timer for session. simply starts right before the game loop starts and runs up forever. 
# access using `timer.time`
class Timer:
    def __init__(self):
        self.reset()

    def reset(self):
        self.time = 0
        self.running = False
    
    def start(self):
        self.running=True

    def update(self, dt):
        if self.running:
            self.time += dt
timer = Timer()
timer.start()
#====================================================================

# on draw event. this is the main game loop==========================
@game_window.event      
def on_draw():   
    game_window.clear()     # clear the window

    params.center_button = joystick.button_state(53)
    # print(params.center_button)

    #check to see if we are in an ITI. if we are at the end of it, start a trial
    # if timer.time > params.last_end_time + params.iti:
    #     if params.bool_iti:
    if params.center_button:
        if not params.stim_on:#start drawing
            print('start')
            start_trial()
        else: #keep drawing
            sprite.scale = 0.2
            sprite.draw()
    else:
        if params.stim_on: end_trial()   #check to see if the button is still down
    #     params.bool_iti=False
    # else: params.bool_iti=True


     
    


def start_trial():
    print('new trial')
    trial_start = timer.time
    #randomize #TODO: implement distribution here
    if random.random() > 0.5: params.answer = 'left'
    else:                     params.answer = 'right'

    if params.answer == 'left': 
        sprite.rotation = 0
        sprite.x = 200
        sprite.y = 200
    else:                       
        sprite.rotation = 90
        sprite.x = 400
        sprite.y = 300

    params.stim_on=True

def end_trial():
    #log trial info
    print(timer.time)
    print(params.last_end_time + params.iti)
    # print(params.answer + '   '+answered)
    params.last_end_time = timer.time
    params.stim_on=False

#TODO: replace with joystick
#TODO: replace joystick answers (but not trial starts) with doors or nosepokes under each image
@game_window.event 
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.A:
        end_trial('left')
    if symbol == pyglet.window.key.L:
        end_trial('right')

def on_key_release(symbol, modifiers):
    pass
#====================================================================

#set up joystick=====================================================
class InputController():
    def __init__(self,board_string,horizontal=0,vertical=1,digital_channels=[53,51]):
        self.board =  ArduinoMega(board_string)
        self.horizontal_channel = horizontal
        self.vertical_channel = vertical
        self.digital_channels = digital_channels

        self.author_name = 'Daniel J Denman'

    def init(self):
        it = util.Iterator(self.board)
        it.start()
        self.board.analog[self.horizontal_channel].enable_reporting()#horizontal
        self.board.analog[self.vertical_channel].enable_reporting()#vertical

        for channel in self.digital_channels:
            self.board.digital[channel].mode=INPUT
    
    def start_analog(self):
        #make an infinite loop
        print('ready to listen to joystick')
        while True:
            pass
            h = self.board.analog[0].read()
            v = self.board.analog[1].read()
            if h == None or v==None :pass
            else:
                if h < 0.4: #went left
                    self.left()
                if h > 0.6: #went right
                    self.right()
                if v < 0.4: #went up
                    self.up()
                if v > 0.6: #went down
                    self.down()

    def button_state(self,channel):
        return self.board.digital[channel].read()
        #     print('down')
        # if self.board.digital[channel].read():
        #     print('up')

    def left(self):
        print('left')
    def right(self):
        print('right')
    def up(self):
        print('up')
    def down(self):
        print('down')
#====================================================================
# start the joystick listening
board_port = glob.glob('/dev/cu.usbmodem*')[0]
joystick=InputController(board_port)
joystick.init()

#start the game loop
# pyglet.clock.schedule_interval(timer.update, 1/60.0)
pyglet.clock.schedule(timer.update)
pyglet.app.run()
    
