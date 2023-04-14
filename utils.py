from pyfirmata import ArduinoMega, util, INPUT, SERVO
from time import sleep

class Params():
    def __init__(self):
        self.iti,self.bool_iti,self.bool_display,self.bool_reward_window,self.reward_vol,self.answer,self.bool_correct,self.time_,self.last_end_time, self.stim_on = \
            3.0,True,False,False,10,'left',False,0.0,0.0, False #initialize task control variables

        self.center_button,self.button_1,self.button_2 = 0,0,0

        self.in_trial = False

        self.stim_contrast,self.stim_orientation,self.stim_spatial_frequency,self.stim_delay,self.button_down_time,self.stim_on_time,self.stim_off_time,self.stim_reaction_time,self.stim_rewarded,self.stim_reward_amount = \
        [],[],[],[],[],[],[],[],[],[]

    def save_params(self):
        pass
        #for p in [self.stim_contrast,self.stim_orientation,self.stim_spatial_frequency,self.stim_delay,self.button_down_time,self.stim_on_time,self.stim_off_time,self.stim_reaction_time,self.stim_rewarded,self.stim_reward_amount]:
            #write p to file



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


