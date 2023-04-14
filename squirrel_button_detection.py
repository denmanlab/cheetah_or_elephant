import glob, time
from numpy import random
from utils import Params, Timer#, InputController
from pyfirmata import ArduinoMega, util, INPUT, SERVO
from time import sleep

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
params = Params()

print(params.center_button)
# set up global timer for session. simply starts right before the game loop starts and runs up forever. 
# access using `timer.time`
timer = Timer()
timer.start()



#set up joystick, button, and/or reward servo control==============================================
class InputController():
    def __init__(self,board_string,horizontal=0,vertical=1,digital_channels=[53,51,49,47,45,43],food_reward_pin=9):
        self.board =  ArduinoMega(board_string)
        self.horizontal_channel = horizontal
        self.vertical_channel = vertical
        self.digital_channels = digital_channels
        self.food_reward_pin = food_reward_pin
        self.author_name = 'Daniel J Denman'

    def init(self):
        it = util.Iterator(self.board)
        it.start()
        self.board.analog[self.horizontal_channel].enable_reporting()#horizontal
        self.board.analog[self.vertical_channel].enable_reporting()#vertical

        for channel in self.digital_channels:
            self.board.digital[channel].mode=INPUT

        #set up servo motor ouput
        # set up pin D9 as Servo Output
        self.reward_food_pin = self.board.digital[self.food_reward_pin]
        self.reward_food_pin.mode = SERVO
  

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

    def move_servo(self,a):
        self.reward_food_pin.write(a)
        sleep(1.015)

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
# try:
board_port = glob.glob('/dev/cu.usbmodem*')[0]
joystick=InputController(board_port)
joystick.init()
joystick.move_servo(270) #initialize closed to be sure
# except:pass # no arduino connected

#start the game loop
# pyglet.clock.schedule_interval(timer.update, 1/60.0)
pyglet.clock.schedule(timer.update)
pyglet.app.run()
    






#====================================================================

# on draw event. this is the main game loop==========================
@game_window.event      
def on_draw():   
    game_window.clear()     # clear the window

    try:
        params.center_button = joystick.button_state(53)
        params.button_1 = joystick.button_state(49)
        params.button_2 = joystick.button_state(45)
    except:pass
    print(params.center_button)
    print(params.button_1)
    print(params.button_2)

    #check to see if we are in an ITI. if we are at the end of it, start a trial
    # if timer.time > params.last_end_time + params.iti:
    #     if params.bool_iti:
    if params.center_button: # if center button is pressed down
        if not params.in_trial:#start drawing if stimulus is not already on
            params.button_down_time.append(timer.time)
            setup_trial()
        else: #keep drawing if stimulus is already on
            if timer.time - params.button_down_time[-1] < params.stim_delay[-1]: #check to see if our random delay has elapsed before we start drawing
                pass
            else:
                if not params.stim_on:
                    start_trial()
                else:
                    sprite.scale = 0.2
                    sprite.draw()
    else:
        if params.stim_on: end_trial()   #check to see if the button is still down, if not stop drawing
    #     params.bool_iti=False
    # else: params.bool_iti=True

def setup_trial():
    if random.random() > 0.5: params.answer = 'left'
    else:                     params.answer = 'right'

    if params.answer == 'left': 
        sprite.rotation = 0
        params.stim_orientation.append(0)
    else:                       
        sprite.rotation = 90
        params.stim_orientation.append(90)

    #TODO: implement distribution here
    # as it is, random flat distro to 5 seconds
    params.stim_delay.append(random.random() * 5)

    contrasts = [0,0.05,0.1,0.2,0.4,0.8,1.0]
    contrast = contrasts[random.randint(7)]
    params.stim_contrast.append(contrast)
    sprite.color = (int(255*contrast),int(255*contrast),int(255*contrast))

    sprite.x = 300
    sprite.y=300

    params.in_trial=True

def start_trial():
    print('start vis stim of new trial')
    trial_start = timer.time
    params.stim_on_time.append(trial_start)

    params.stim_on=True

def end_trial():
    #log trial info
    # print(timer.time)
    # print(params.last_end_time + params.iti)
    # print(params.answer + '   '+answered)
    params.last_end_time = timer.time
    params.stim_off_time.append(params.last_end_time) #store trial end in params
    

    reaction_time= params.last_end_time - params.stim_on_time[-1]
    params.stim_reaction_time.append(reaction_time)  #store reaction time in params
    
    check_reaction_time(reaction_time)

    params.save_params() #record the last trial on disk
    params.stim_on=False #update boolean so we have the option to try again
    params.in_trial=False

def check_reaction_time(reaction_time):
    print(reaction_time)
    if reaction_time < 1.0:
        joystick.move_servo(90)
        joystick.move_servo(270)
        params.stim_rewarded.append(True)
        params.stim_reward_amount.append(180)
    else:
        params.stim_rewarded.append(False)
        params.stim_reward_amount.append(0)

        #optionally add timeout here. 

#backup keyboard version for testing if harware not connected
@game_window.event 
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.A:
        print('A')
        params.center_button = True

    if symbol == pyglet.window.key.R:
        print('R')
        joystick.move_servo(90)

    if symbol == pyglet.window.key.T:
        print('T')
        joystick.move_servo(270)

def on_key_release(symbol, modifiers):
    if symbol == pyglet.window.key.A:
        params.center_button = False
#====================================================================


