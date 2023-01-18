import machine
from machine import Pin, Timer
import ustruct

MIN_BPM = 30
MAX_BPM = 240

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


"""
if self.mode == Mode.BASIC:
    pass
elif self.mode == Mode.SEQUENCER:
    pass
elif self.mode == Mode.ARPEGIATOR:
    pass
"""

class KeyboardConfiguration:
    def __init__(self):
        self.mode = Mode.BASIC
        self.time_div = TimeDiv.ONE_FOURTH
        self.rate = 60
        self.octave_offset = 0
        self.play_mode = PlayMode.STOPPED
        
        # sequencer linked attributes
        self.seq_len = 0
        self.seq_notes = []
        self.current_seq_index = 0
        self.seq_number = 0
        
        self.loading_seq = False
        self.loading_seq_number = 0
        self.last_seq_key_played = -1
        
        # arpegiator linked attributes
        self.hold = False
        self.arp_len = 0
        self.arp_notes = []
        self.current_arp_index = 0
        self.last_arp_key_played = -1
        self.arp_number_note_pressed = 0
        
        self.uart = machine.UART(0,baudrate=31250,tx=Pin(16),rx=Pin(17))        
        self.led = Pin(25,machine.Pin.OUT)
        
        self.play_note_timer = Timer(-1)
        
        self.display()    
        
    def display(self):
        print("*-"*20)
        print("Mode :",modeToStr(self.mode))
        print("TimeDiv :",timeDivToStr(self.time_div))
        print("Rate :",self.rate,"bpm")
        print("First Key : C"+str(self.octave_offset+3))
        print("Play/pause :"+playModeToStr(self.play_mode))
        print("Sequencer len :", self.seq_len)
        print("Sequencer number :", self.seq_number)
        print("Loading sequencer number :", self.loading_seq_number)
        print("Hold : ", self.hold)
        print("*-"*20)

    def timer_callback(self, timer):        
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            if self.play_mode == PlayMode.PLAYING:
                next_index = (self.current_seq_index+1)%self.seq_len
                previous_index = (self.current_seq_index-1)%self.seq_len
                if self.last_seq_key_played != -1:
                    self.note_off(self.last_seq_key_played)
                self.last_seq_key_played = self.seq_notes[self.current_seq_index]
                self.note_on( self.last_seq_key_played)
                self.current_seq_index = next_index          
        elif self.mode == Mode.ARPEGIATOR:
            if self.play_mode == PlayMode.PLAYING:
                
                if self.last_arp_key_played != -1:
                    self.__send_note_off(self.last_arp_key_played)
                if(len(self.arp_notes) != 0):
                    if(self.current_arp_index >len(self.arp_notes) -1):
                        self.current_arp_index = len(self.arp_notes) -1
                    next_index = (self.current_arp_index+1)%len(self.arp_notes)
                    previous_index = (self.current_arp_index-1)%len(self.arp_notes)
                    print(next_index, previous_index)
                    self.last_arp_key_played = self.arp_notes[self.current_arp_index]
                    self.__send_note_on(self.last_arp_key_played)
                    self.current_arp_index = next_index
                
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
        self.__send__all_note_off()
        self.play_mode = PlayMode.STOPPED
        
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            self.load_sequence_file(self.seq_number)
        elif self.mode == Mode.ARPEGIATOR:            
            self.arp_len = 0 # reset arpegiator
            self.arp_notes = []
            self.current_arp_index = 0
            self.arp_number_note_pressed = 0
        
        self.display()
        
    def decr_mode(self):
        self.mode = ((self.mode-1)%3)
        self.__send__all_note_off()
        self.play_mode = PlayMode.STOPPED
        
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            self.load_sequence_file(self.seq_number)
        elif self.mode == Mode.ARPEGIATOR:           
            self.arp_len = 0 # reset arpegiator
            self.arp_notes = []
            self.current_arp_index = 0
            self.arp_number_note_pressed = 0
        
        self.display()
        
    def set_rate_potentiometer(self, pot_value):
        old_rate = self.rate
        new_rate = int((pot_value/65536) * (MAX_BPM-MIN_BPM) + MIN_BPM)
        
        if abs(new_rate- old_rate)>2:
            self.rate = new_rate
            if self.mode == Mode.BASIC:
                pass
            elif self.mode == Mode.SEQUENCER:
                if self.play_mode == PlayMode.PLAYING:
                    self.upadate_timer_frequency()
            elif self.mode == Mode.ARPEGIATOR:
                pass
            self.display()
        
    def note_on(self, note):
        if self.mode == Mode.BASIC:
            self.__send_note_on(note)
        elif self.mode == Mode.SEQUENCER:
            if self.play_mode == PlayMode.RECORDING:
                self.seq_notes.append(note)
                self.seq_len += 1
                self.save_sequence_file(self.seq_number)
                self.display()
            elif self.play_mode == PlayMode.PLAYING:
                self.__send_note_on(note)
        elif self.mode == Mode.ARPEGIATOR:
            self.arp_number_note_pressed += 1
            if self.hold == False:                
                self.arp_notes.append(note)
                print(self.arp_notes)
            else:
                if self.arp_number_note_pressed == 1:
                    self.arp_notes = []
                self.arp_notes.append(note)
                
    def note_off(self, note):
        if self.mode == Mode.BASIC:
            self.__send_note_off(note)
        elif self.mode == Mode.SEQUENCER:
            if self.play_mode == PlayMode.PLAYING:
                self.__send_note_off(note)
        elif self.mode == Mode.ARPEGIATOR:
            self.arp_number_note_pressed -= 1
            if self.hold == False:
                if note in self.arp_notes:
                    self.arp_notes.remove(note)


    def __send_note_on(self, note):
        if note != -1:
            self.uart.write(ustruct.pack("bbb",0x93,note,127))
            self.led.value(1)

    def __send_note_off(self, note):
        if note != -1:
            self.uart.write(ustruct.pack("bbb",0x83,note,0))
            self.led.value(0)
        
    def __send__all_note_off(self):
        self.uart.write(ustruct.pack("bbb",0xb3,123,0))
        self.led.value(0)
        
    def blank_tile_pressed(self):
        print("blank_tile")
        
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            if self.play_mode == PlayMode.RECORDING:
                self.seq_notes.append(-1)
                self.seq_len += 1
                self.display()
        elif self.mode == Mode.ARPEGIATOR:
            pass
        self.display()
        
    def stop_pressed(self):
        self.play_mode = PlayMode.STOPPED
        print("stop")
        self.current_seq_index = 0
        self.play_note_timer.deinit()
        
        if self.mode == Mode.BASIC:
            self.__send__all_note_off()
        elif self.mode == Mode.SEQUENCER:
            if self.last_seq_key_played != -1:
                self.__send_note_off(self.last_seq_key_played)
            self.last_arp_key_played = -1  
        elif self.mode == Mode.ARPEGIATOR:
            if self.last_arp_key_played != -1:
                self.__send_note_off(self.last_arp_key_played)
            self.last_arp_key_played = -1
            
        self.display()
        
    def pauseplay_pressed(self):
        print("pausePlay")
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            if self.play_mode != PlayMode.PLAYING:
                if self.seq_len != 0:
                    self.play_mode = PlayMode.PLAYING
                    self.upadate_timer_frequency()
            else:
                self.play_mode = PlayMode.PAUSING
                if self.last_seq_key_played != -1:
                    self.__send_note_off(self.last_seq_key_played)
                self.last_seq_key_played = -1
                self.play_note_timer.deinit()
        elif self.mode == Mode.ARPEGIATOR:
            if self.play_mode != PlayMode.PLAYING:
                self.play_mode = PlayMode.PLAYING
                self.upadate_timer_frequency()
            else:
                self.play_mode = PlayMode.PAUSING
                if self.last_arp_key_played != -1:
                    self.__send_note_off(self.last_arp_key_played)
                self.last_arp_key_played = -1
                self.play_note_timer.deinit()
       
            
        self.display()
        
    def rec_pressed(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:            
            self.play_mode = PlayMode.RECORDING
            print("rec")
        elif self.mode == Mode.ARPEGIATOR:
            pass
        self.display()
        
    def load_seq_pressed(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            self.loading_seq = True
            self.loading_seq_number = 0
        elif self.mode == Mode.ARPEGIATOR:
            pass
        self.display()
    
    def clear_seq_pressed(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            self.stop_pressed()
            self.seq_len = 0
            self.seq_notes = []
            self.current_seq_index = 0
            self.save_sequence_file(self.seq_number)
        elif self.mode == Mode.ARPEGIATOR:
            pass
        
        self.display()
        
    def digit_pressed(self, digit):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            if self.loading_seq == True:
                self.loading_seq_number = (self.loading_seq_number*10)+digit
                if self.loading_seq_number >63:
                    self.loading_seq_number = 63                    
                self.display()
        elif self.mode == Mode.ARPEGIATOR:
            pass
    
    def sharp_pressed(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            if self.loading_seq == True: # confirm loading
                self.loading_seq = False
                self.seq_number = self.loading_seq_number
                self.load_sequence_file(self.seq_number)
                self.display()
        elif self.mode == Mode.ARPEGIATOR:
            pass
    
    def star_pressed(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            if self.loading_seq == True: # cancel loading
                self.loading_seq = False
                self.loading_seq_number = 0
                self.display()
        elif self.mode == Mode.ARPEGIATOR:
            pass
        
    def hold_pressed(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            pass
        elif self.mode == Mode.ARPEGIATOR:
            self.hold = not self.hold
            self.display()
        
    def load_sequence_file(self, sequence_number):
        #stop timer before loading
        self.play_note_timer.deinit()
        try:
            sequence_file = open("seq_"+str(sequence_number)+".csv", "r")
            output = sequence_file.readline()
            sequence_file.close()
            split_output = output.split(",")
            split_output = [int(x) for x in split_output]
            
            self.seq_len = len(split_output)
            self.seq_notes = split_output
            
            print(self.seq_len)
            print(self.seq_notes)
        except:
            print("couldn't load sequence n°",sequence_number)
            self.seq_len = 0
            self.seq_notes = []
        self.current_seq_index = 0
        if self.seq_len == 0:
            self.stop_pressed()
        else:    
            self.upadate_timer_frequency()
    
    def save_sequence_file(self, sequence_number):
        sequence_file = open("seq_"+str(sequence_number)+".csv", "w")
        line = ""
        for x in self.seq_notes:
            line = line + str(x) + ","
        line = line[:-1]
        sequence_file.write(line)
        sequence_file.close()

