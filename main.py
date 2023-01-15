import machine
from machine import Pin
import utime
import ustruct

uart = machine.UART(0,baudrate=31250,tx=Pin(16),rx=Pin(17))


led = Pin(25,machine.Pin.OUT)
    
boot_exit_button = Pin(26, Pin.IN, Pin.PULL_UP)

COL_NUMBER = 8
ROW_NUMBER = 8


# 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15
# F E D C B A 9 8 7 6 5  4  3  2  1  0

# col = 1  2  3  4  B C D E
#       14 13 12 11 4 3 2 1

# line = 0  5  6 7 8 9 A F
#        15 10 9 8 7 6 5 0

col_list=[15, 10, 9, 8, 7, 6, 5, 0]
row_list=[14, 13, 12, 11, 4, 3, 2, 1]

for x in range(0,ROW_NUMBER):
    row_list[x]=Pin(row_list[x], Pin.OUT)
    row_list[x].value(1)


for x in range(0,COL_NUMBER):
    col_list[x] = Pin(col_list[x], Pin.IN, Pin.PULL_UP)

key_map= [
    ["up","t","g",".","b","guide","Fnct","Connexion Fin"],
    ["correction","e","d","Esc","c","z","s","x"],
    ["annulation","r","f",",","v","a","q","w"],
    ["down","y","h","'","n","Sommaire","Ctrl","Espace"],
    ["shift",";","*","Suite","0","u","j","#"],
    ["left","-","7","Retour","8","i","k","9"],
    ["right",":","4","Envoi","5","o","l","6"],
    ["enter","?","1","Répétition","2","p","m","3"]
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

octaveOffset = 0

def KeypadRead(cols,rows):
    global key_state
    global key_state_old
    
    key_state = [[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]]
        
    for r in range(0, ROW_NUMBER):
        rows[r].value(0)
        utime.sleep(0.01)
        for c in range(0,COL_NUMBER):
            if cols[c].value() == 0:
                key_state[r][c] = 1

            if(key_state[r][c] != key_state_old[r][c]):
                key=key_map[r][c]
                note=note_map[r][c]
                if key_state[r][c] == 0:                          
                    if(note != 0):
                        noteOff(note+octaveOffset*12)
                    else:
                        customKeyOff(key)
                else:                
                    if(note != 0):
                        noteOn(note+octaveOffset*12)
                    else:                        
                        customKeyOn(key)
        
        rows[r].value(1)
        
    for x in range(0, COL_NUMBER):
        for y in range(0, ROW_NUMBER):
            key_state_old[x][y] = key_state[x][y]

    
print("--- Ready to get user inputs ---")

def noteOn(note):
    uart.write(ustruct.pack("bbb",0x93,note,127))
    led.value(1)

def noteOff(note):
    uart.write(ustruct.pack("bbb",0x83,note,0))
    led.value(0)
    
def customKeyOn(key):
    global octaveOffset
    print("You pressed: "+key)
    if key == "right":
        octaveOffset += 1
        if octaveOffset > -3 + 9: #main key is 3 so -3 then limit key +9
            octaveOffset = -3 + 9
            print("capping octave offset to key +9")
    elif key == "left":
        octaveOffset -= 1
        if octaveOffset < -1 -3: #main key is 3 so -3 then limit key -1
            octaveOffset = -1 -3
            print("capping octave offset to key -1")
    
def customKeyOff(key):
    print("You released: "+key)  

if boot_exit_button.value() == 1:
    while True:
        key=KeypadRead(col_list, row_list)
else:
    print("Exit button pressed at boot, quit program")