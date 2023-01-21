import machine
from machine import Pin
import utime
import time

from keyboardConfiguration import KeyboardConfiguration
from OLED_SPI import OLED_1inch3
    
boot_exit_button = Pin(26, Pin.IN, Pin.PULL_UP)
rate_potentiometer = machine.ADC(28)

COL_NUMBER = 8
ROW_NUMBER = 8

MAX_DELAY_BEFORE_SCREENSAVER_S = 300
last_key_update = time.time()


# 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15
# F E D C B A 9 8 7 6 5  4  3  2  1  0

# line = 1  2  3  4  B C D E
#        14 13 12 11 4 3 2 1

# col =  0  5  6 7 8 9 A F
#        15 10 9 8 7 6 5 0


# 8 9  10 11 12
#22 21 20 19 18 
col_list=[15, 20, 21, 22, 7, 6, 5, 0]
row_list=[14, 13, 18, 19, 4, 3, 2, 1]

for x in range(0,ROW_NUMBER):
    row_list[x]=Pin(row_list[x], Pin.OUT)
    row_list[x].value(1)


for x in range(0,COL_NUMBER):
    col_list[x] = Pin(col_list[x], Pin.IN, Pin.PULL_UP)

key_map= [
    ["up","t","g",".","b","guide","Fnct","connexion fin"],
    ["correction","e","d","Esc","c","z","s","x"],
    ["annulation","r","f",",","v","a","q","w"],
    ["down","y","h","'","n","sommaire","Ctrl","Espace"],
    ["shift",";","*","suite","0","u","j","#"],
    ["left","-","7","retour","8","i","k","9"],
    ["right",":","4","envoi","5","o","l","6"],
    ["enter","?","1","répétition","2","p","m","3"]
]

note_map= [
    [0 ,65,67,60,69,0 ,0 ,0 ],
    [0 ,59,61,54,63,56,58,60],
    [0 ,62,64,57,66,53,55,57],
    [0 ,68,70,63,72,0 ,52,0 ],
    [54,66,0 ,0 ,0 ,71,73,0 ],
    [0 ,69,0 ,0 ,0 ,74,76,0 ],
    [0 ,72,0 ,0 ,0 ,77,79,0 ],
    [0 ,75,0 ,0 ,0 ,80,82,0 ]
]

key_state = [[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]]
key_state_old = [[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]]

keyboard_config = KeyboardConfiguration()
OLED = OLED_1inch3(keyboard_config)
keyboard_config.set_display(OLED)


def KeypadRead(cols,rows):
    global key_state
    global key_state_old
    global last_key_update
    global OLED
    
    key_state = [[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]]
        
    for r in range(0, ROW_NUMBER):
        rows[r].value(0)
        for c in range(0,COL_NUMBER):
            if cols[c].value() == 0:
                key_state[r][c] = 1

            if(key_state[r][c] != key_state_old[r][c]):
                last_key_update = time.time()
                if OLED.is_screensaver() == True:
                    OLED.reset_screensaver_mode()
                key=key_map[r][c]
                note=note_map[r][c]
                if key_state[r][c] == 0:                          
                    if(note != 0):
                        keyboard_config.note_off(note+keyboard_config.octave_offset*12)
                    else:
                        customKeyOff(key)
                else:                
                    if(note != 0):
                        keyboard_config.note_on(note+keyboard_config.octave_offset*12)
                    else:                        
                        customKeyOn(key)
        
        rows[r].value(1)
        
    for x in range(0, COL_NUMBER):
        for y in range(0, ROW_NUMBER):
            key_state_old[x][y] = key_state[x][y]

    
print("--- Ready to get user inputs ---")
    
def customKeyOn(key):
    global octaveOffset
    print("You pressed: "+key)
    if key == "right":
        keyboard_config.incr_octave_offset()
    elif key == "left":
        keyboard_config.decr_octave_offset()
    if key == "up":
        keyboard_config.incr_mode()
    elif key == "down":
        keyboard_config.decr_mode()
    elif key == "guide":
        keyboard_config.rec_pressed()
    elif key == "correction":
        keyboard_config.stop_pressed()
    elif key == "suite":
        keyboard_config.pauseplay_pressed()
    elif key == "envoi":
        keyboard_config.load_seq_pressed()
    elif key == "enter":
        keyboard_config.blank_tile_pressed()
    elif key == "sommaire":
        keyboard_config.midi_channel_gate_length_pressed()
    elif key == "#":
        keyboard_config.sharp_pressed()
    elif key == "*":
        keyboard_config.star_pressed()
    elif key == "annulation":
        keyboard_config.clear_seq_hold_pressed()
    elif key == "retour":
        keyboard_config.decr_arp_mode_kbp_transpose()
    elif key == "répétition":
        keyboard_config.incr_arp_mode()
    elif key == "connexion fin":
        keyboard_config.change_time_div_pressed()
    elif key.isdigit():
        keyboard_config.digit_pressed(int(key))
        
def customKeyOff(key):
    print("You released: "+key)  

if boot_exit_button.value() == 1:
    
    OLED.display_helixbyte()
    time.sleep(0.5)
    keyboard_config.display()
    index = 0
    while True:
        if time.time() - last_key_update > MAX_DELAY_BEFORE_SCREENSAVER_S and OLED.is_screensaver() == False:
            OLED.set_screensaver_mode()
        if OLED.is_screensaver() == True:           
            index+=1
            if index%16== True:
                OLED.update_screensaver()
                index = 0
        key=KeypadRead(col_list, row_list)
        keyboard_config.set_rate_potentiometer(rate_potentiometer.read_u16())
else:
    OLED.display_helixbyte()
    time.sleep(0.5)
    OLED.display_programming_mode()
    print("Exit button pressed at boot, quit program")