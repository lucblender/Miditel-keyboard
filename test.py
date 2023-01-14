import machine
from machine import Pin
import utime
import ustruct

uart = machine.UART(0,baudrate=31250,tx=Pin(16),rx=Pin(17))

COL_NUMBER = 8
ROW_NUMBER = 8


# 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15
# F E D C B A 9 8 7 6 5  4  3  2  1  0

# col = 1  2  3  4  B C D E
#       14 13 12 11 4 3 2 1

# line = 0  5  6 7 8 9 A F
#        15 10 9 8 7 6 5 0

col_list=[14, 13, 12, 11, 4, 3, 2, 1]
row_list=[15, 10, 9, 8, 7, 6, 5, 0]

for x in range(0,ROW_NUMBER):
    row_list[x]=Pin(row_list[x], Pin.OUT)
    row_list[x].value(1)


for x in range(0,COL_NUMBER):
    col_list[x] = Pin(col_list[x], Pin.IN, Pin.PULL_UP)

key_map=[["up","correction","annulation","down","shift","left","right","enter"],\
        ["t","e","r","y",";","-",":","?"],\
        ["g","d","f","h","*","7","4","1"],\
        [".","Esc",",","'","Suite","Retour","Envoi","Répétition"],\
        ["b","c","v","n","0","8","5","2"],\
        ["guide","z","a","Sommaire","u","i","o","p"],\
        ["Fnct","s","q","Ctrl","j","k","l","m"],\
        ["Connexion Fin","x","w","Espace","#","9","6","3"]]

note_map=[[0,0,0,0,54,0,0,0],\
        [65,59,62,68,66,69,72,75],\
        [67, 61, 64, 70,0,0,0,0],\
        [60,54,57,63,0,0,0,0],\
        [69, 63, 66, 72,0,0,0,0],\
        [0,56, 53,0,71, 74, 77, 80],\
        [0,58,55,52,73,76,79,82],\
        [0,60, 57,0,0,0,0,0]]

key_state = [[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]]
key_state_old = [[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]]

octaveOffset = 0

def KeypadRead(cols,rows):
    global key_state
    global key_state_old
    
    key_state = [[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]]
        
    for r in range(0, ROW_NUMBER):
        rows[r].value(0)
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

def noteOff(note):
    uart.write(ustruct.pack("bbb",0x83,note,0))
    
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

while True:
    key=KeypadRead(col_list, row_list)
    #if key != None:
   #   print("You pressed: "+key)
    #  utime.sleep(0.3)
