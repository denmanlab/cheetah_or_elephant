#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 22 14:33:52 2020

@latest author: elizabethstubblefield
"""


## Beth updated 7.6.20 to include updating/saving frame rates (dT)
## Also updated 8.4.20 the sleep time after key press so rxn times aren't skewed high (ll.750ish)... 
## mean(rxn times) seemed to approx. the sleep time & so will max frame rate; EAS removed sleep time
## l. 287 now calls folder w/ same #images at ea. %(easier) from git dir/models/all_same_ea/*.tif'
## l. 291 no longer hard-coded for selecting easy images for the first 4 trials

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.interval.MetaInterval import Sequence
from direct.interval.LerpInterval import LerpFunc
from direct.interval.FunctionInterval import Func
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import Mat4, WindowProperties, CardMaker, NodePath, TextureStage, MovieTexture, MovieVideo
from panda3d.core import KeyboardButton
from direct.gui.OnscreenText import OnscreenText

import sys, glob, time, datetime, os, getopt, subprocess
from math import pi, sin, cos
from numpy.random import randint, exponential
from numpy import arange, concatenate
import numpy as np
RANDOM_SEED = randint(10000)
np.random.seed(RANDOM_SEED)
from pyglet.window import key
from PIL import Image
from scipy import ndimage

try:
    from toolbox.toolbox.IO.nidaq import DigitalInput, DigitalOutput, AnalogInput, AnalogOutput

    have_nidaq = True
except:  # Exception, e:
    print("could not import iodaq.")
    have_nidaq = False

# sys.path.append('C:\github\syringe_pump')
try:
    from syringe_pump.stepper import Stepper
    import time

    s = Stepper(mode='arduino', port='COM3', syringe='3mL')
except:
    print('no reward hardware found')

MOUSE_ID = 'test'
REWARD_VOLUME = 10  # in µL
REWARD_WINDOW = 2.0  # in seconds

#make sure we have the most recent user list
subprocess.call('osf -p cy643 -u denmanlab@gmail.com fetch -f -U .user_ids.npy',shell=True)

#load (or make) the an anonymized used id for this repo
try:
    extant_user_ids = np.load('.user_ids.npy').astype(int)
    if os.path.isfile('.user_id.npy'):
        MOUSE_ID = 'user'+str(np.load('.user_ids.npy')[0])
    else:
        extant_user_ids = np.append(extant_user_ids,int(len(extant_user_ids)))
        np.save('.user_id.npy',np.array([extant_user_ids[-1]]))  
        np.save('.user_ids.npy',np.array(extant_user_ids)).astype(int)
        MOUSE_ID = 'user'+str(extant_user_ids[-1])
except: 
    MOUSE_ID = np.random.randint(0,100)
# getopt.getopt(args, options, [long_options])

# try:
#     opts, args = getopt.getopt(argv,"hi:o:",["mouse_id=","reward_volume="])
# except getopt.GetoptError:
#     print('test.py -i <inputfile> -o <outputfile>')
#     sys.exit(2)
# for opt, arg in opts:
#     if opt == '-h':
#         print('test.py -i <inputfile> -o <outputfile>')
#         sys.exit()
#     elif opt in ("-id", "--mouse_id"):
#         MOUSE_ID = arg
#     elif opt in ("-v", "--reward_volume"):
#         REWARD_VOLUME = arg


# this is used to change whether the mouse's running and licking control the rewards.
# if TRUE, then the stimulus automatically advances to the next stop zone, waits, plays the stimulus, and delivers a reward.
# AUTO_MODE=False
AUTO_MODE = False
AUTO_REWARD = False

# Global variables for the tunnel dimensions and speed of travel
TUNNEL_SEGMENT_LENGTH = 50
TUNNEL_TIME = 2  # Amount of time for one segment to travel the


# distance of TUNNEL_SEGMENT_LENGTH

class MouseTunnel(ShowBase):
    def __init__(self):
        # Initialize the ShowBase class from which we inherit, which will
        # create a window and set up everything we need for rendering into it.
        ShowBase.__init__(self)
        self.stimtype = 'random image'

        # session_start
        self.session_start_time = datetime.datetime.now()

        # self.accept("escape", sys.exit, [0])#don't let the user do this, because then the data isn't saved.
        self.accept('q', self.close)
        self.accept('Q', self.close)

        self.upArrowIsPressed = base.mouseWatcherNode.isButtonDown(KeyboardButton.up())
        self.downArrowIsPressed = base.mouseWatcherNode.isButtonDown(KeyboardButton.down())
        self.rightArrowIsPressed = base.mouseWatcherNode.isButtonDown(KeyboardButton.right())
        self.leftArrowIsPressed = base.mouseWatcherNode.isButtonDown(KeyboardButton.left())

        self.AUTO_REWARD = AUTO_REWARD
        # disable mouse control so that we can place the camera
        base.disableMouse()
        camera.setPosHpr(0, 0, 10, 0, -90, 0)
        mat = Mat4(camera.getMat())
        mat.invertInPlace()
        base.mouseInterfaceNode.setMat(mat)
        # base.enableMouse()

        props = WindowProperties()
        # props.setOrigin(0, 0)
        props.setFullscreen(True)
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)
        base.win.requestProperties(props)
        base.setBackgroundColor(0, 0, 0)  # set the background color to black

        print('FULSCREEN:')
        print(props.getFullscreen())
        print('=============')
        # set up the textures
        # we now get buffer thats going to hold the texture of our new scene
        altBuffer = self.win.makeTextureBuffer("hello", 1524, 1024)
        # altBuffer.getDisplayRegion(0).setDimensions(0.5,0.9,0.5,0.8)
        # altBuffer = base.win.makeDisplayRegion()
        # altBuffer.makeDisplayRegion(0,1,0,1)

        # now we have to setup a new scene graph to make this scene
        self.dr2 = base.win.makeDisplayRegion(0, 0.001, 0, 0.001)#make this really,really small so it's not seeable by the subject

        altRender = NodePath("new render")
        # this takes care of setting up ther camera properly
        self.altCam = self.makeCamera(altBuffer)
        self.dr2.setCamera(self.altCam)
        self.altCam.reparentTo(altRender)
        self.altCam.setPos(0, -10, 0)

        self.bufferViewer.setPosition("lrcorner")
        # self.bufferViewer.position = (-.1,-.4,-.1,-.4)
        self.bufferViewer.setCardSize(1.0, 0.0)
        print(self.bufferViewer.position)

        self.imagesTexture = MovieTexture("image_sequence")
        # success = self.imagesTexture.read("models/natural_images.avi")
        # success = self.imagesTexture.read("models/movie_5hz.mpg")
        self.imagesTexture.setPlayRate(1.0)
        self.imagesTexture.setLoopCount(10)
        # self.imageTexture =loader.loadTexture("models/NaturalImages/BSDs_8143.tiff")
        # self.imagesTexture.reparentTo(altRender)

        self.fixationPoint = OnscreenImage(image='models/fixationpoint.jpg', pos=(0, 0,0),scale=0.01)

        cm = CardMaker("stimwindow")
        cm.setFrame(-4, 4, -3, 3)
        # cm.setUvRange(self.imagesTexture)
        self.card = NodePath(cm.generate())
        self.card.reparentTo(altRender)
        if self.stimtype == 'image_sequence':
            self.card.setTexture(self.imagesTexture, 1)

        # add the score display
        self.scoreLabel = OnscreenText(text='Current Score:', pos=(-1, 0.9), scale=0.1, fg=(0.8, 0.8, 0.8, 1))
        self.scoreText = OnscreenText(text=str(0), pos=(-1, 0.76), scale=0.18, fg=(0, 1, 0, 1),
                                      shadow=(0.1, 1, 0.1, 0.5))
        self.feebackScoreText = OnscreenText(text='+ ' + str(0), pos=(-0.5, 0.5), scale=0.3, fg=(0, 1, 0, 1),
                                             shadow=(0.1, 1, 0.1, 0.5))
        self.feebackScoreText.setX(3.)

        # self.imagesTexture.play()

        # self.bufferViewer.setPosition("lrcorner")
        # self.bufferViewer.setCardSize(1.0, 0.0)
        self.accept("v", self.bufferViewer.toggleEnable)
        self.accept("V", self.bufferViewer.toggleEnable)

        # Load the tunnel
        self.initTunnel()

        # initialize some things
        # for the tunnel construction:
        self.boundary_to_add_next_segment = -1 * TUNNEL_SEGMENT_LENGTH
        self.current_number_of_segments = 8
        # task flow booleans
        self.in_waiting_period = False
        self.stim_started = False
        self.looking_for_a_cue_zone = True
        self.in_reward_window = False
        self.show_stimulus = False
        # for task control
        self.interval = 0
        self.time_waiting_in_cue_zone = 0
        self.wait_time = 1.83
        self.stim_duration = 0  # in seconds
        
       
        self.distribution_type = np.random.uniform#
#        self.distribution_type_inputs = [0.05,1.5] #can be anytong should match 
        self.distribution_type_inputs = [0.016,0.4] #change the min & max stim duration times

        self.max_stim_duration = 1.0  # in seconds
        self.stim_elapsed = 0.0  # in seconds
        self.last_position = base.camera.getZ()
        self.position_on_track = base.camera.getZ()
        # for reward control
        self.reward_window = REWARD_WINDOW  # in seconds
        self.reward_elapsed = 0.0
        
#        self.new_dt = list()
        
        # self.reward_volume = 0.008 # in mL. this is for the hardcoded 0.1 seconds of reward time
        self.reward_volume = int(REWARD_VOLUME)  # in uL, for the stepper motor
        self.reward_time = 0.1  # in sec, based on volume. hard coded right now but should be modified by the (1) calibration and (2) optionally by the main loop for dynamic reward scheduling
        # self.lick_buffer = []
        self.current_score = 0
        self.score = 0
        self.feedback_score_startime = -2

        # INITIALIZE NIDAQ
        self.nidevice = 'Dev2'
        self.encodervinchannel = 1
        self.encodervsigchannel = 0
        self.invertdo = False
        self.diport = 1
        self.lickline = 1
        self.doport = 0
        self.rewardline = 0
        self.rewardlines = [0]
        self.encoder_position_diff = 0
        if have_nidaq:
            self._setupDAQ()
            self.do.WriteBit(1, 1)
            self.do.WriteBit(3,
                             1)  # set reward high, because the logic is flipped somehow. possibly by haphazard wiring of the circuit (12/24/2018 djd)
            self.previous_encoder_position = self.ai.data[0][self.encodervsigchannel]
        else:
            self.previous_encoder_position = 0
        self.encoder_gain = 3

        # INITIALIZE LICK SENSOR
        self._lickSensorSetup()

        # INITIALIZE  output data
        self.lickData = []
        self.x = []
        self.t = []
        self.trialData = []
        self.reactionTimeData = []
        self.rewardData = []
        self.rightKeyData = []
        self.leftKeyData = []
        self.imageData = []
        self.imageTimeData = []
        self.scoreData = []
        self.trialDurationData = []
        self.new_dt = []

        # INITIALIZE KEY SENSOR, for backup inputs and other user controls
        self.keys = key.KeyStateHandler()
        self.accept('r', self._give_reward, [self.reward_volume])
        self.accept('l', self._toggle_reward)

        # initialize the image list and populate what images you want included


#        self.img_list = glob.glob('models/2AFC_IMAGES_HUMAN/*.tif')
#        self.img_list = glob.glob('models/2AFC_IMAGES_HUMAN2/*.tif')  
#        self.img_list = glob.glob('/Users/elizabethstubblefield/Desktop/cheetah_or_elephant/composite_images/masks/all_same_num_ea/*.tif')  #Newest images
        self.img_list = glob.glob('models/all_same_ea/*.tif')  #Newest images

        #No longer hard-coded:
        self.original_indices = [0,0]  #this was manually counted... first number must was the index of the first easy img; was [43, -18]
        for ndx, name in enumerate(self.img_list):
            if 'Cheetah255' in name:
                self.original_indices[0] = ndx
            elif 'elephant0' in name:
                self.original_indices[1] = ndx

        # print(self.img_list)
        
#        self.original_indices = [43,-18] #manually counted, grump  #Problematic w/out at least 43 images in the folder        

        self.imageTextures =[loader.loadTexture(img) for img in self.img_list]
        self.img_id = None  # this variable used so we know which stimulus is being presented
        self.img_mask = None #this tells us what the image mask being presented is

        # self._setupEyetracking()
        # self._startEyetracking()

        if AUTO_MODE:
            self.gameTask = taskMgr.add(self.autoLoop2, "autoLoop2")
            self.rewardTask = taskMgr.add(self.rewardControl, "reward")
            self.cue_zone = concatenate((self.cue_zone, arange( \
                self.current_number_of_segments * -TUNNEL_SEGMENT_LENGTH-50, \
                self.current_number_of_segments * -TUNNEL_SEGMENT_LENGTH - TUNNEL_SEGMENT_LENGTH - 100, \
                -1)))
            self.auto_position_on_track = 0
            self.auto_restart = False
            self.auto_running = True
            self.contTunnel()
        else:
            # Now we create the task. taskMgr is the task manager that actually
            # calls the function each frame. The add method creates a new task.
            # The first argument is the function to be called, and the second
            # argument is the name for the task.  It returns a task object which
            # is passed to the function each frame.
            self.gameTask = taskMgr.add(self.gameLoop, "gameLoop")
            # self.stimulusTask = taskMgr.add(self.stimulusControl, "stimulus")
            self.lickTask = taskMgr.add(self.lickControl, "lick")
            self.rewardTask = taskMgr.add(self.rewardControl, "reward")
            self.keyTask = taskMgr.add(self.keyControl, "Key press")

    # Code to initialize the tunnel
    def initTunnel(self):
        self.tunnel = [None] * 8

        for x in range(8):
            # Load a copy of the tunnel
            self.tunnel[x] = loader.loadModel('models/tunnel')
            # The front segment needs to be attached to render
            if x == 0:
                self.tunnel[x].reparentTo(render)
            # The rest of the segments parent to the previous one, so that by moving
            # the front segement, the entire tunnel is moved
            else:
                self.tunnel[x].reparentTo(self.tunnel[x - 1])
                # We have to offset each segment by its length so that they stack onto
            # each other. Otherwise, they would all occupy the same space.
            self.tunnel[x].setPos(0, 0, -TUNNEL_SEGMENT_LENGTH)
            # Now we have a tunnel consisting of 4 repeating segments with a
            # hierarchy like this:
            # render<-tunnel[0]<-tunnel[1]<-tunnel[2]<-tunnel[3]

        self.tunnel[0] = loader.loadModel('models/grating')
        self.tunnel[0].reparentTo(render)
        self.cue_zone = arange(0, TUNNEL_SEGMENT_LENGTH, -1)-280

    # This function is called to snap the front of the tunnel to the back
    # to simulate traveling through it
    def contTunnel(self):
        self.auto_position_on_track -= 50
        position_on_track = self.auto_position_on_track
        print(str(int(position_on_track)) + '   ' + str(self.cue_zone))
        if int(position_on_track) in np.array(self.cue_zone):  # check for cue zone
            if not self.auto_restart:
                print('STOP!')
                self.tunnelMove.pause()
                self.auto_presentation = True
                # self.current_number_of_segments +=1
            else:
                self.auto_restart = True
                self.tunnelMove.resume()

        else:
            self.in_waiting_period = False
            self.auto_presentation = False

            # base.setBackgroundColor([1,0 , 0])
            if self.looking_for_a_cue_zone == False:
                self.looking_for_a_cue_zone = True
            if self.stim_started == True:
                self.stop_a_presentation()

                # This line uses slices to take the front of the list and put it on the
            # back. For more information on slices check the Python manual
            self.tunnel = self.tunnel[1:] + self.tunnel[0:1]

            # Set the front segment (which was at TUNNEL_SEGMENT_LENGTH) to 0, which
            # is where the previous segment started
            self.tunnel[0].setZ(0)
            # Reparent the front to render to preserve the hierarchy outlined above
            self.tunnel[0].reparentTo(render)
            # Set the scale to be apropriate (since attributes like scale are
            # inherited, the rest of the segments have a scale of 1)
            self.tunnel[0].setScale(.155, .155, .305)
            # Set the new back to the values that the rest of the segments have
            self.tunnel[3].reparentTo(self.tunnel[2])
            self.tunnel[3].setZ(-TUNNEL_SEGMENT_LENGTH)
            self.tunnel[3].setScale(1)

            # Set up the tunnel to move one segment and then call contTunnel again
            # to make the tunnel move infinitely
            self.tunnelMove = Sequence(
                LerpFunc(self.tunnel[0].setZ,
                         duration=TUNNEL_TIME,
                         fromData=0,
                         toData=TUNNEL_SEGMENT_LENGTH * .305),
                Func(self.contTunnel)
            )
            self.tunnelMove.start()
    
    def get_trial_duration(self):
        return self.distribution_type(*self.distribution_type_inputs)

    def start_a_presentation(self):

        self.save_data()
        self.stim_duration = self.get_trial_duration()
        self.fixationPoint.destroy()
#        import pickle
#        with open('objs.pkl', 'wb') as f:  # Python 3: open(..., 'wb')
#            pickle.dump([self.stim_duration,self.distribution_type_inputs], f)
#            print('variables saved!!!')

        self.in_reward_window = True
        print("start")
        if have_nidaq:
            self.do.WriteBit(2, 1)
        # self.bufferViewer.toggleEnable()

        self.lick_buffer = []
        self.trialData.extend([globalClock.getFrameTime()])
        self.reactionTimeData.extend([-1])

        if self.stimtype == 'random image':

            if len(self.trialData) < 4:
                i=self.original_indices[int(np.round(np.random.random()))]   #commented out due to <43 images [see l. 290ish]
                self.stim_duration = 2.0
            else:                                                            #commented out due to <43 images
                i = randint(len(self.imageTextures))
                
            self.card.setTexture(self.imageTextures[i],0)
            self.dr2.setDimensions(0.25, 0.75, 0.25, 0.75)  # floats (left, right, bottom, top)
            self.img_id = self.img_list[i] #this assigns the current presented image to self.image_id
            print(self.img_id)
            self.imageData.extend(self.img_id)                    
        
        if self.stimtype == 'image_sequence':
            self.imagesTexture.setTime(0.)
            self.dr2.setDimensions(0.4, 0.8, 0.4, 0.70)  # floats (left, right, bottom, top)
            self.imagesTexture.play()
        self.imageTimeData.extend([globalClock.getFrameTime()])
        self.imageData.extend(self.img_id)
  
    def check_arrows(self):
        # this function will report which arrow was pressed. right = 1, left = 2, no press = 0
        if self.rightArrowIsPressed:
            #print('check arrows RIGHT')
            return 1
            # time.sleep(2)
        elif self.leftArrowIsPressed:
            #print('check arrows LEFT')
            return 2
            # time.sleep(2)
        else:
            return 0

    def stop_a_presentation(self):
        if self.stim_started == True:
            if self.stim_elapsed > self.stim_duration:
                self.trialDurationData.append(self.stim_duration)
            else: self.trialDurationData.append(self.stim_duration)
            self.dr2.setDimensions(0, 0.001, 0, 0.001)#make this really,really small so it's not seeable by the subject
            # self.bufferViewer.toggleEnable()
            self.stim_started = False
            self.stim_elapsed = 0.
            self.stim_duration = 0.
            self.stim_off_time = globalClock.getFrameTime()
            if have_nidaq:
                self.do.WriteBit(2, 0)
            # if globalClock.getFrameTime() > self.feedback_score_startime + 1.5:  # arbitrary wait to make sure this isn't after a correct trial
            #     self.feebackScoreText.setText('+' + str(0))
            #     self.feebackScoreText.setFg((1, 0, 0, 1))
            #     self.feebackScoreText.setX(.5)
            #     self.feedback_score_startime = globalClock.getFrameTime()
            self.scoreData.append(self.current_score)
            self.fixationPoint = OnscreenImage(image='models/fixationpoint.jpg', pos=(0, 0,0),scale=0.01)

            
    #   def keySensorSetup(self):


    def show_the_score(self):
            self.feebackScoreText.setText('+' + str(self.score))
            if self.score == 0:
                self.feebackScoreText.setFg((1, 0, 0, 1))
            else:
                self.feebackScoreText.setFg((0, 1, 0, 1))
            self.feebackScoreText.setX(.5)
            self.feedback_score_startime = globalClock.getFrameTime()
    # sets up the task to listen for user input from the keys

    def _lickSensorSetup(self):

        """ Attempts to set up lick sensor NI task. """
        ##TODO: Make lick sensor object if necessary. Let user select port and line.
        if have_nidaq:
            if self.di:
                self.lickSensor = self.di  # just use DI for now
                licktest = []
                for i in range(30):
                    licktest.append(self.rightArrowIsPressed.Read()[self.lickline])
                    time.sleep(0.01)
                licktest = np.array(licktest, dtype=np.uint8)
                if len(licktest[np.where(licktest > 0)]) > 25:
                    self.lickSensor = None
                    self.lickData = [np.zeros(len(self.rewardlines))]
                    print("Lick sensor failed startup test.")
                else:
                    print('lick sensor setup succeeded.')
                self.keycontrol = True
            else:
                print("Could not initialize lick sensor.  Ensure that NIDAQ is connected properly.")
                self.keycontrol = True
                self.lickSensor = None
                self.lickData = [np.zeros(len(self.rewardlines))]
                self.keys = key.KeyStateHandler()
                # self.window.winHandle.push_handlers(self.keys)
        else:
            print("Could not initialize lick sensor.  Ensure that NIDAQ is connected properly.")
            self.keycontrol = True
            self.lickSensor = None
            self.lickData = [np.zeros(len(self.rewardlines))]
            self.keys = key.KeyStateHandler()

    def reactiontime_to_score(self):
        rt = globalClock.getFrameTime() - self.trialData[-1]
        self.reactionTimeData[-1] = rt
        score = 100. / rt  # scale the reaction time, with faster producing more points
        return int(score / 20.)

    # def _read_licks(self): # not yet implemented; should be replaces with check to beam break
    def _give_reward(self, volume):
        print("reward!")
        self.rewardData.extend([globalClock.getFrameTime()])

        # for humans
        self.score = self.reactiontime_to_score()
        self.current_score += self.score
        self.show_the_score()
        self.scoreText.setText(str(self.current_score))
        

        # for mice
        if have_nidaq:
            self.do.WriteBit(3, 0)
            time.sleep(self.reward_time)
            self.do.WriteBit(3, 1)  # put a TTL on a line to indicate that a reward was given
            s.dispense(volume)  # pass # not yet implemented

    def _toggle_reward(self):
        if self.AUTO_REWARD:
            self.AUTO_REWARD = False
            print('switched to lick sensing for reward.')
        else:
            self.AUTO_REWARD = True
            print('switched to automatic rewards after stimuli.')

    def autoLoop2(self, task):
        dt = globalClock.getDt()
        current_time = globalClock.getFrameTime()

        self.x.extend([self.auto_position_on_track])
        self.t.extend([globalClock.getFrameTime()])

        if self.auto_presentation:
            self.auto_running = False
            if self.in_waiting_period:
                self.time_waited += dt
            else:
                self.time_waited = 0
                self.in_waiting_period = True
            if self.time_waited > self.wait_time:  # if in cue zone,see if we have been ther for long enough
                # start a trial
                self.start_position = self.auto_position_on_track
                self.start_time = current_time
                if not self.stim_started:
                    self.start_a_presentation()
                    # print(self.stim_duration)
                    self.stim_started = True
                    self.show_stimulus = True
                else:
                    self.stim_elapsed += dt
                    if self.stim_elapsed > self.stim_duration:
                        self.show_stimulus = False
                        self.in_reward_window = True
                        self.stop_a_presentation()
                        self.auto_restart = False
                        # print(self.current_number_of_segments)
                        self.current_number_of_segments += 9
                        # redefine the cue zone as the next one
                        self.cue_zone = arange(self.current_number_of_segments * -TUNNEL_SEGMENT_LENGTH,
                                               self.current_number_of_segments * -TUNNEL_SEGMENT_LENGTH - TUNNEL_SEGMENT_LENGTH - 280,
                                               -1)
                        # extend cue zone, keeping old ones
                        # self.cue_zone = concatenate((self.cue_zone,arange(self.current_number_of_segments*-TUNNEL_SEGMENT_LENGTH-40,
                        #                             self.current_number_of_segments*-TUNNEL_SEGMENT_LENGTH-TUNNEL_SEGMENT_LENGTH-40,
                        #                             -1)))
                        self.contTunnel()
                        self.time_waited = 0
                        self.looking_for_a_cue_zone = False
                # base.setBackgroundColor([0, 0, 1])
            else:
                pass  # base.setBackgroundColor([0, 1, 0])
        else:
            self.auto_running = True
        return Task.cont  # Since every return is Task.cont, the task will

    def gameLoop(self, task):
        # get the time elapsed since the next frame.
        dt = globalClock.getDt()
        self.new_dt.append(dt)                  #Store the append here for dt
        
        current_time = globalClock.getFrameTime()    #This is for the key press
        if current_time > self.feedback_score_startime + 1.5:
            self.feebackScoreText.setX(3.)
        # get the camera position.
        position_on_track = base.camera.getZ()

        # get the encoder position from NIDAQ Analog Inputs channel 2
        if have_nidaq:
            encoder_position = self.ai.data[0][self.encodervsigchannel]  # zeroth sample in buffer [0], from ai2 [2]
            # convert to track coordinates
            encoder_position_diff = (encoder_position - self.previous_encoder_position)
            if encoder_position_diff > 4.5: encoder_position_diff -= 5.
            if encoder_position_diff < -4.5: encoder_position_diff += 5.
            self.encoder_position_diff = encoder_position_diff * self.encoder_gain
            self.previous_encoder_position = encoder_position
        else:
            self.read_keys()
            if self.upArrowIsPressed:
                self.encoder_position_diff = -1 * self.encoder_gain
            if self.downArrowIsPressed:
                self.encoder_position_diff = 1 * self.encoder_gain
            if not self.downArrowIsPressed:
                if not self.upArrowIsPressed:
                    self.encoder_position_diff = 0
        position_on_track = base.camera.getZ() + self.encoder_position_diff
        # reset the camera position
        self.camera.setPos(base.camera.getX(), base.camera.getY(), position_on_track)

        self.x.extend([position_on_track])
        self.t.extend([globalClock.getFrameTime()])

        # first check if the mouse moved on the last frame.
        if abs(self.last_position - position_on_track) < 1.5:  # the mouse didn't move more than 0.5 units on the track
            self.moved = False
            if int(position_on_track) in self.cue_zone:  # check for cue zone
                if self.looking_for_a_cue_zone:  # make sure we transitioning from the tunnel to a cue zone
                    # increment how long we've been waiting in the cue zone.
                    if self.in_waiting_period:
                        self.time_waited += dt
                    else:
                        self.time_waited = 0
                        self.in_waiting_period = True
                    if self.time_waited > self.wait_time:  # if in cue zone,see if we have been ther for long enough
                        # start a trial
                        self.start_position = position_on_track
                        self.start_time = current_time
                        if not self.stim_started:
                            self.start_a_presentation()
                            print(self.stim_duration)
                            self.stim_started = True
                            self.show_stimulus = True
                        else:
                            self.stim_elapsed += dt
                            if self.stim_elapsed > self.stim_duration:
                                self.show_stimulus = False
                                self.stop_a_presentation()
                                self.time_waited = 0
                                self.looking_for_a_cue_zone = False
                        # base.setBackgroundColor([0, 0, 1])
                    else:
                        pass  # base.setBackgroundColor([0, 1, 0])
            else:
                self.in_waiting_period = False
                # base.setBackgroundColor([1,0 , 0])
                if self.looking_for_a_cue_zone == False:
                    self.looking_for_a_cue_zone = True
                if self.stim_started == True:
                    self.stop_a_presentation()
        else:  # the mouse did move
            self.moved = True
            if self.stim_started == True:  # check if it moved during a presenation
                self.stop_a_presentation()
                self.time_waited = 0
                self.looking_for_a_cue_zone = False
                self.show_stimulus = False

        # if we need to add another segment, do so
        if position_on_track < self.boundary_to_add_next_segment:
            self.tunnel.extend([None])
            x = self.current_number_of_segments
            if x % 8 == 0:
                self.tunnel[x] = loader.loadModel('models/grating')
                self.cue_zone = concatenate((self.cue_zone, arange( \
                    self.current_number_of_segments * -TUNNEL_SEGMENT_LENGTH - 50, \
                    self.current_number_of_segments * -TUNNEL_SEGMENT_LENGTH - TUNNEL_SEGMENT_LENGTH - 100, \
                    -1)))
            else:
                self.tunnel[x] = loader.loadModel('models/tunnel')
            self.tunnel[x].setPos(0, 0, -TUNNEL_SEGMENT_LENGTH)
            self.tunnel[x].reparentTo(self.tunnel[x - 1])
            # increment
            self.boundary_to_add_next_segment -= TUNNEL_SEGMENT_LENGTH
            self.current_number_of_segments += 1
        else:
            pass  # print('current:'+str(position_on_track) +'      next boundary:' + str(self.boundary_to_add_next_segment))

        self.last_position = position_on_track

        # lick_times = self.
        # self._read_licks()
        return Task.cont  # Since every return is Task.cont, the task will
        # continue indefinitely, under control of the mouse (animal)

    def stimulusControl(self, task):
        if self.show_stimulus and not self.bufferViewer.isEnabled():
            # self.bufferViewer.toggleEnable()
            self.dr2.setDimensions(0.5, 0.9, 0.5, 0.8)
        if not self.show_stimulus and self.bufferViewer.isEnabled():
            # self.bufferViewer.toggleEnable()
            self.dr2.setDimensions(0, 0.1, 0, 0.1)
        return Task.cont

    def lickControl(self, task):
        """ Checks to see if a lick is occurring. """
        ##TODO: Let user select line for lick sensing.
        if self.lickSensor:
            if self.lickSensor.Read()[self.lickline]:
                self.lickData.extend([globalClock.getFrameTime()])
                print('lick happened at: ' + str(self.lickData[-1]))
        elif self.keycontrol == True:  # NO NI BOARD.  KEY INPUT?
            if self.keys[key.SPACE]:
                data = [globalClock.getFrameTime()]
            elif self.keys[key.NUM_1]:
                # print(self.lickData)
                # elif self.keys[key.NUM_3]:
                #     data = [0,1]
                # else:
                #     data = [0,0]
                self.lickData.extend(data)
        return Task.cont

    def keyControl(self, task):
        # listen to and record when the arrows are pressed
        self.read_keys()
        if self.rightArrowIsPressed:
            self.rightKeyData.extend([globalClock.getFrameTime()])
            print('right arrow at: ' + str(self.rightKeyData[-1]))
#            time.sleep(.2)  #EAS changed this only allows for one keystroke to be recorded every 0.5s
        elif self.leftArrowIsPressed:
            self.leftKeyData.extend([globalClock.getFrameTime()])
            print('left arrow at: ' + str(self.leftKeyData[-1]))
#            time.sleep(.2)  #EAS changed this only allows for one keystroke to be recorded every 0.5s
        return Task.cont

    def rewardControl(self, task):
        # print(self.in_reward_window)
        if self.in_reward_window == True:
            if self.reward_elapsed < self.reward_window:
            
                self.reward_elapsed += globalClock.getDt()
#                self.new_reward_elapsed.append(self.reward_elapsed)
                
#                import pickle
#                with open('objs.pkl', 'wb') as f:  # Python 3: open(..., 'wb')
#                    pickle.dump([self.stim_duration,self.distribution_type_inputs, self.new_rew_control], f)
#                    print('variables saved!!!')

                self.check_arrows()
                if not self.AUTO_REWARD:
                    if self.check_arrows() == 1:  # if check arrows returns a 1 the right arrow was pressed during stimulus presentation
                        # note reaction time

                        if self.img_id.find("Elephant") != -1: #if the current image file contains the string in () the value is not -1
                            self._give_reward(self.reward_volume)
                            print('correct: image was mostly elephant')
                            self.in_reward_window = False;
                            self.reward_elapsed = 0.  # reset
                        else:
                            print(self.img_mask)
                            print('image was not mostly elephant!')
                            self.in_reward_window = False
                            self.reward_elapsed = 0.  # reset
                            self.score=0
                            self.show_the_score()
                    if self.check_arrows() == 2:  # if check arrows returns a 2 the left arrow was pressed during stimulus presentation
                        if self.img_id.find("Cheetah") != -1: #if the current image file contains the string in () the value is not -1
                            self._give_reward(self.reward_volume)
                            print('correct: image was mostly cheetah')
                            self.in_reward_window = False;
                            self.reward_elapsed = 0.  # reset
                        else:
                            print(self.img_mask)
                            print('image was not mostly cheetah!')
                            self.in_reward_window = False
                            self.reward_elapsed = 0.  # reset
                            self.score=0
                            self.show_the_score()
                    # else:
                        # self.in_reward_window = False
                        # self.reward_elapsed = 0.  # reset
                else:
                    self._give_reward(self.reward_volume)
                    self.in_reward_window = False;
                    
#                    import pickle
#                    with open('objs.pkl', 'wb') as f:  # Python 3: open(..., 'wb')
#                        pickle.dump([self.stim_duration,self.distribution_type_inputs, self.rew_control], f)
#                        print('variables saved!!!')

                    self.reward_elapsed = 0.  # reset
                    # self.reward_elapsed=0.
                    # base.setBackgroundColor([1, 1, 0])

            # if self.keys[key.NUM_1]:
            #     print('reward!')
            else:
                self.score=0
                self.show_the_score()
                self.in_reward_window = False
                self.reward_elapsed = 0.
        else:
            pass#print('not listening for reward'+str(globalClock.getFrameTime()))
        return Task.cont

    def _setupEyetracking(self):
        """ sets up eye tracking"""
        try:
            eyetrackerip = "DESKTOP-EE5KKDO"
            eyetrackerport = 10000
            trackeyepos = False
            from aibs.Eyetracking.EyetrackerClient import Client
            self.eyetracker = Client(outgoing_ip=eyetrackerip,
                                     outgoing_port=eyetrackerport,
                                     output_filename=str(datetime.datetime.now()).replace(':', '').replace('.',
                                                                                                           '').replace(
                                         ' ', '-'))
            self.eyetracker.setup()
            # eyedatalog = []
            # if trackeyepos:
            #     eyeinitpos = None
        except:
            print("Could not initialize eyetracker:")
            self.eyetracker = None

    def _startEyetracking(self):
        if self.eyetracker:
            self.eyetracker.recordStart()

    def _setupDAQ(self):
        """ Sets up some digital IO for sync and tiggering. """
        print('SETTING UP DAQ')
        try:
            if self.invertdo:
                istate = 'low'
            else:
                istate = 'high'
            self.do = DigitalOutput(self.nidevice, self.doport,
                                    initial_state='low')
            self.do.StartTask()
        except:  # Exception, e:
            print("Error starting DigitalOutput task:")
            self.do = None
        try:
            self.di = DigitalInput(self.nidevice, self.diport)
            self.di.StartTask()
        except:  # Exception, e:
            print("Error starting DigitalInput task:")
            self.di = None
        # try:
        # set up 8 channels, only use 2 though for now
        self.ai = AnalogInput(self.nidevice, range(8), buffer_size=25, terminal_config='RSE',
                              clock_speed=6000.0, voltage_range=[-5.0, 5.0])
        self.ai.StartTask()
        # except:# Exception, e:
        # print("Error starting AnalogInput task:")
        # self.ai = None
        try:
            self.ao = AnalogOutput(self.nidevice, channels=[0, 1], terminal_config='RSE',
                                   voltage_range=[0.0, 5.0])
            self.ao.StartTask()
        except:  # Exception, e:
            print("Error starting AnalogOutput task:")
            self.ao = None

    def read_keys(self):
        self.upArrowIsPressed = base.mouseWatcherNode.isButtonDown(KeyboardButton.up())
        self.downArrowIsPressed = base.mouseWatcherNode.isButtonDown(KeyboardButton.down())
        self.rightArrowIsPressed = base.mouseWatcherNode.isButtonDown(KeyboardButton.right())
        self.leftArrowIsPressed = base.mouseWatcherNode.isButtonDown(KeyboardButton.left())

    def save_data(self):
        if not os.path.isdir(os.path.join(os.getcwd(), 'data')):
            os.mkdir(os.path.join(os.getcwd(), 'data'))
        save_path = os.path.join(os.getcwd(), 'data', str(MOUSE_ID) + '_' + \
                                 str(self.session_start_time.year) + '_' + \
                                 str(self.session_start_time.month) + '_' + \
                                 str(self.session_start_time.day) + '-' + \
                                 str(self.session_start_time.hour) + '_' + \
                                 str(self.session_start_time.minute) + '_' + \
                                 str(self.session_start_time.second))
        if not os.path.isdir(save_path):
            os.mkdir(save_path)

        print("saving data to " + save_path)
        np.save(os.path.join(save_path, 'licks.npy'), self.lickData)
        np.save(os.path.join(save_path, 'x.npy'), self.x)
        np.save(os.path.join(save_path, 't.npy'), self.t)
        np.save(os.path.join(save_path, 'trialData.npy'), self.trialData)
        np.save(os.path.join(save_path, 'rewardData.npy'), self.rewardData)
        np.save(os.path.join(save_path, 'rtData.npy'), self.reactionTimeData)
        np.save(os.path.join(save_path, 'rightKeyData.npy'), self.rightKeyData)
        np.save(os.path.join(save_path, 'leftKeyData.npy'), self.leftKeyData)
        np.save(os.path.join(save_path, 'imageData.npy'), self.imageData)
        np.save(os.path.join(save_path, 'imageTimeData.npy'), self.imageTimeData)
        np.save(os.path.join(save_path, 'scoreData.npy'), self.scoreData)
        np.save(os.path.join(save_path, 'trialDurationData.npy'), self.trialDurationData)
        np.save(os.path.join(save_path, 'dT.npy'), self.new_dt)

    def close(self):
        self.save_data()

        print('rewardData:')
        print(np.shape(self.rewardData))
        try:
            #push anonymized data to Denman Lab Open Science Framework project for human psychophysics
            subprocess.call('osf -p 7xruh -u denmanlab@gmail.com upload -r '+save_path+' data/'+os.path.basename(save_path),shell=True)     #commented these lines out to test if saving to osf is the hangup; it's not
        except:pass

        sys.exit(0)

app = MouseTunnel()
app.run()