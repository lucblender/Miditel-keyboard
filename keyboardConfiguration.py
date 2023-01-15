import machine
from machine import Pin, Timer
import ustruct

def enum(**enums: int):
    return type('Enum', (), enums)

Mode = enum(BASIC=0, ARPEGIATOR=1, SEQUENCER=2)
TimeDiv = enum(ONE_FOURTH=0,
            ONE_EIGHTH=1,
            ONE_SIXTEENTH=2,
            ONE_THIRTYSECOND=3,
            ONE_FOURTH_T=4,
            ONE_EIGHTH_T=5,
            ONE_SIXTEENTH_T=6,
            ONE_THIRTYSECOND_T=7)


PlayMode = enum(PLAYING = 0,
                PAUSING = 1,
                RECORDING = 2,
                STOPPED = 3)

def modeToStr(local_mode):
    if local_mode == Mode.BASIC:
        return "basic"
    elif local_mode == Mode.ARPEGIATOR:
        return "arpegiator"
    elif local_mode == Mode.SEQUENCER:
        return "sequencer"
    
def timeDivToStr(local_time_div):
    if local_time_div == TimeDiv.ONE_FOURTH:
        return "1/4"
    elif local_time_div == TimeDiv.ONE_EIGHTH:
        return "1/8"
    elif local_time_div == TimeDiv.ONE_SIXTEENTH:
        return "1/16"
    elif local_time_div == TimeDiv.ONE_THIRTYSECOND:
        return "1/32"
    elif local_time_div == TimeDiv.ONE_FOURTH_T:
        return "1/4T"
    elif local_time_div == TimeDiv.ONE_EIGHTH_T:
        return "1/8T"
    elif local_time_div == TimeDiv.ONE_SIXTEENTH_T:
        return "1/16T"
    elif local_time_div == TimeDiv.ONE_THIRTYSECOND_T:
        return "1/32T"
    
def playModeToStr(local_play_mode):
    if local_play_mode == PlayMode.PLAYING:
        return "⏵"
    elif local_play_mode == PlayMode.PAUSING:
        return "⏸"
    elif local_play_mode == PlayMode.RECORDING:
        return "⏺"
    elif local_play_mode == PlayMode.STOPPED:
        return "⏹"

class KeyboardConfiguration:
    def __init__(self):
        self.mode = Mode.BASIC
        self.time_div = TimeDiv.ONE_FOURTH
        self.rate = 60
        self.octave_offset = 0
        self.play_mode = PlayMode.STOPPED
        
        self.uart = machine.UART(0,baudrate=31250,tx=Pin(16),rx=Pin(17))        
        self.led = Pin(25,machine.Pin.OUT)
        
        self.play_note_timer = Timer(-1)
        self.upadate_timer_frequency()
        
        self.display()    
        
    def display(self):
        print("*-"*20)
        print("Mode :",modeToStr(self.mode))
        print("TimeDiv :",timeDivToStr(self.time_div))
        print("Rate :",self.rate,"bpm")
        print("First Key : C"+str(self.octave_offset+3))
        print("Play/pause :"+playModeToStr(self.play_mode))
        print("*-"*20)

    def timer_callback(self, timer):
        print("ping")
        
    def upadate_timer_frequency(self):
        self.play_note_timer.init(period=int((60/self.rate)*1000), mode=Timer.PERIODIC, callback=self.timer_callback)
        
    def incr_octave_offset(self):
        self.octave_offset += 1
        if self.octave_offset > -3 + 9: #main key is 3 so -3 then limit key +9
            self.octave_offset = -3 + 9
            print("capping octave offset to key +9")
        self.display()
        
    def decr_octave_offset(self):
        self.octave_offset -= 1
        if self.octave_offset < -1 -3: #main key is 3 so -3 then limit key -1
            self.octave_offset = -1 -3
            print("capping octave offset to key -1")
        self.display()
        
    def incr_mode(self):
        self.mode = ((self.mode+1)%3)
        self.display()
        
    def decr_mode(self):
        self.mode = ((self.mode-1)%3)
        self.display()
        
    def note_on(self, note):
        self.uart.write(ustruct.pack("bbb",0x93,note,127))
        self.led.value(1)

    def note_off(self, note):
        self.uart.write(ustruct.pack("bbb",0x83,note,0))
        self.led.value(0)
        
    def blank_tile_pressed(self):
        print("blank_tile")
        self.display()
        
    def stop_pressed(self):
        self.play_mode = PlayMode.STOPPED
        print("stop")
        self.display()
        
    def pauseplay_pressed(self):
        print("pausePlay")
        
        if self.play_mode != PlayMode.PLAYING:
            self.play_mode = PlayMode.PLAYING
        else:
            self.play_mode = PlayMode.PAUSING
            
        self.display()
        
    def rec_pressed(self):
        self.play_mode = PlayMode.RECORDING
        print("rec")
        self.display()
        
    def load_seq_pressed(self):
        print("load_seq")
        self.display()