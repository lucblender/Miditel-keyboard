from machine import Pin,SPI
import framebuf
import time
from keyboardConfiguration import *
import arial8
import arial10
import arial35
import arial_50
import courier20
import font10
import font6
import freesans20
import writer
from random import randrange

DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

def pict_to_fbuff(path,x,y):
    with open(path, 'rb') as f:
        f.readline() # Magic number
        f.readline() # Creator comment
        f.readline() # Dimensions
        data = bytearray(f.read())
    return framebuf.FrameBuffer(data, x, y, framebuf.MONO_HLSB)


class OLED_1inch3(framebuf.FrameBuffer):
    def __init__(self, keyboard_config):
        self.width = 128
        self.height = 64
        
        self.screensaver_active = False
        self.screesaver_pixels = [[0]*2]*20
        
        self.cs = Pin(CS,Pin.OUT)
        self.rst = Pin(RST,Pin.OUT)
        
        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1,2000_000)
        self.spi = SPI(1,20000_000,polarity=0, phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=None)
        self.dc = Pin(DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HMSB)
        self.init_display()
        
        self.white =   0xffff
        self.black =   0x0000
        
        self.keyboard_config = keyboard_config
        
        self.font_writer_arial8 = writer.Writer(self, arial8)
        self.font_writer_arial10 = writer.Writer(self, arial10)
        self.font_writer_arial35 = writer.Writer(self, arial35)
        self.font_writer_arial_50 = writer.Writer(self, arial_50)
        self.font_writer_courier20 = writer.Writer(self, courier20)
        self.font_writer_font10 = writer.Writer(self, font10)
        self.font_writer_font6 = writer.Writer(self, font6)
        self.font_writer_freesans20 = writer.Writer(self, freesans20)
        
        self.fbuf_play = pict_to_fbuff('play.pbm', 9, 9)   
        self.fbuf_pause = pict_to_fbuff('pause.pbm', 9, 9)
        self.fbuf_rec = pict_to_fbuff('rec.pbm', 9, 9)
        self.fbuf_stop = pict_to_fbuff('stop.pbm', 9, 9)
        
        self.fbufs_play_mode = [self.fbuf_play, self.fbuf_pause, self.fbuf_rec, self.fbuf_stop]
        
        
        self.fbuf_arp_up = pict_to_fbuff('arp_mode/up.pbm', 16, 16)
        self.fbuf_arp_dwn = pict_to_fbuff('arp_mode/dwn.pbm', 16, 16)
        self.fbuf_arp_inc = pict_to_fbuff('arp_mode/inc.pbm', 16, 16)
        self.fbuf_arp_exc = pict_to_fbuff('arp_mode/exc.pbm', 16, 16)
        self.fbuf_arp_rand = pict_to_fbuff('arp_mode/rand.pbm', 16, 16)
        self.fbuf_arp_order = pict_to_fbuff('arp_mode/order.pbm', 16, 16)
        self.fbuf_arp_upx2 = pict_to_fbuff('arp_mode/upx2.pbm', 16, 16)
        self.fbuf_arp_dwnx2 = pict_to_fbuff('arp_mode/dwnx2.pbm', 16, 16)
        
        self.fbufs_arp_modes = [self.fbuf_arp_up, self.fbuf_arp_dwn, self.fbuf_arp_inc, self.fbuf_arp_exc, self.fbuf_arp_rand, self.fbuf_arp_order, self.fbuf_arp_upx2, self.fbuf_arp_dwnx2]
        
                
        self.fbuf_inv_arp_up = pict_to_fbuff('arp_mode/inv_up.pbm', 16, 16)
        self.fbuf_inv_arp_dwn = pict_to_fbuff('arp_mode/inv_dwn.pbm', 16, 16)
        self.fbuf_inv_arp_inc = pict_to_fbuff('arp_mode/inv_inc.pbm', 16, 16)
        self.fbuf_inv_arp_exc = pict_to_fbuff('arp_mode/inv_exc.pbm', 16, 16)
        self.fbuf_inv_arp_rand = pict_to_fbuff('arp_mode/inv_rand.pbm', 16, 16)
        self.fbuf_inv_arp_order = pict_to_fbuff('arp_mode/inv_order.pbm', 16, 16)
        self.fbuf_inv_arp_upx2 = pict_to_fbuff('arp_mode/inv_upx2.pbm', 16, 16)
        self.fbuf_inv_arp_dwnx2 = pict_to_fbuff('arp_mode/inv_dwnx2.pbm', 16, 16)
        
        self.fbufs_inv_arp_modes = [self.fbuf_inv_arp_up, self.fbuf_inv_arp_dwn, self.fbuf_inv_arp_inc, self.fbuf_inv_arp_exc, self.fbuf_inv_arp_rand, self.fbuf_inv_arp_order, self.fbuf_inv_arp_upx2, self.fbuf_inv_arp_dwnx2]
    
    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        """Initialize dispaly"""  
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)
        
        self.write_cmd(0xAE)#turn off OLED display

        self.write_cmd(0x00)   #set lower column address
        self.write_cmd(0x10)   #set higher column address 

        self.write_cmd(0xB0)   #set page address 
      
        self.write_cmd(0xdc)    #et display start line 
        self.write_cmd(0x00) 
        self.write_cmd(0x81)    #contract control 
        self.write_cmd(0x6f)    #128
        self.write_cmd(0x21)    # Set Memory addressing mode (0x20/0x21) #
    
        self.write_cmd(0xa0)    #set segment remap 
        self.write_cmd(0xc0)    #Com scan direction
        self.write_cmd(0xa4)   #Disable Entire Display On (0xA4/0xA5) 

        self.write_cmd(0xa6)    #normal / reverse
        self.write_cmd(0xa8)    #multiplex ratio 
        self.write_cmd(0x3f)    #duty = 1/64
  
        self.write_cmd(0xd3)    #set display offset 
        self.write_cmd(0x60)

        self.write_cmd(0xd5)    #set osc division 
        self.write_cmd(0x41)
    
        self.write_cmd(0xd9)    #set pre-charge period
        self.write_cmd(0x22)   

        self.write_cmd(0xdb)    #set vcomh 
        self.write_cmd(0x35)  
    
        self.write_cmd(0xad)    #set charge pump enable 
        self.write_cmd(0x8a)    #Set DC-DC enable (a=0:disable; a=1:enable)
        self.write_cmd(0XAF)
        
    def show(self):
        self.write_cmd(0xb0)
        for page in range(0,64):
            self.column = 63 - page              
            self.write_cmd(0x00 + (self.column & 0x0f))
            self.write_cmd(0x10 + (self.column >> 4))
            for num in range(0,16):
                self.write_data(self.buffer[page*16+num])
    
    def is_screensaver(self):
        return self.screensaver_active
        
    def set_screensaver_mode(self):
        self.screensaver_active = True
        for i in range(0,len(self.screesaver_pixels)):
            self.screesaver_pixels[i] = [randrange(0,128), randrange(0,64)]
        self.fill(self.black)        
        
        for pix in self.screesaver_pixels:
            self.rect(pix[0],pix[1],1,1,self.white)
            
        self.show()
        
    def reset_screensaver_mode(self): 
        self.screensaver_active = False
        self.display()
        
    def update_screensaver(self):
        
        for i in range(0,len(self.screesaver_pixels)):
            self.screesaver_pixels[i][1] += 1
            if self.screesaver_pixels[i][1] > 63:                
                self.screesaver_pixels[i] = [randrange(0,128), 0]
        self.fill(self.black)        
        
        for pix in self.screesaver_pixels:
            self.rect(pix[0],pix[1],1,1,self.white)
            
        self.show()
        
        
    def display_helixbyte(self):
        with open('lxb64x64.pbm', 'rb') as f:
            f.readline() # Magic number
            f.readline() # Creator comment
            f.readline() # Dimensions
            data = bytearray(f.read())
        lxb_fbuf = framebuf.FrameBuffer(data, 64, 64, framebuf.MONO_HLSB)

        self.blit(lxb_fbuf, 32, 0)
        self.show()
        
    def display_programming_mode(self):     
        self.fill(self.black)#smallest
        self.font_writer_arial10.text("Programming mode",0,0)
        self.show()
        time.sleep(1)
        
    def display_demo(self):     
        self.fill(self.black)#smallest
        self.font_writer_arial10.text("Hey",0,0)
        self.text("hey", 0, 64-8)
        self.show()
        time.sleep(1)
        
        self.fill(self.black)#middle
        self.font_writer_font6.text("Hey",0,0)
        self.text("hey", 0, 64-8)
        self.show()
        time.sleep(1)
        
        self.fill(self.black)#bigger balder
        self.font_writer_font10.text("Hey",0,0)
        self.text("hey", 0, 64-8)
        self.show()
        time.sleep(1)
                     
    def display(self):
        if self.screensaver_active == False:
            #self.display_demo()
            
            self.fill(self.black)
            
            if self.keyboard_config.mode == Mode.MULTISEQUENCER:
                self.font_writer_arial10.text("Multi-seq",17,4)
            else:
                self.font_writer_font10.text(modeToStr(self.keyboard_config.mode),17,1)
            bpm_txt = str(self.keyboard_config.rate)+"bpm"
            self.font_writer_arial10.text(bpm_txt,(128-(7*len(bpm_txt))),3)
            
            self.rect(0,0,15,15,self.white)
            correct_play_mode_buff = self.fbufs_play_mode[self.keyboard_config.play_mode]
            self.blit(correct_play_mode_buff, 3, 3)
            
            print("Play/pause :"+playModeToStr(self.keyboard_config.play_mode))

            self.line(0,15,128,15,self.white)
            
            if self.keyboard_config.mode == Mode.SEQUENCER:                           
                #todo
                self.line(84,15,84,50,self.white)
                self.line(84,40,127,40,self.white)
                if self.keyboard_config.transpose_keyboardplay_mode == True:
                    self.fill_rect(86,17,40,10,self.white)
                    self.font_writer_arial10.text("transpo.",87,17,True)
                    self.font_writer_arial10.text("kb play",87,29)

                else:
                    self.fill_rect(86,29,40,10,self.white)
                    self.font_writer_arial10.text("transpo.",87,17)
                    self.font_writer_arial10.text("kb play",87,29,True)
                self.font_writer_arial10.text("key:"+midi_to_key(self.keyboard_config.transpose_key),87,41)
                # true = transpose, false = keyboardplay
                #self.transpose_key = 60 # 60 = C4 
                
            
            if self.keyboard_config.mode == Mode.SEQUENCER or self.keyboard_config.mode == Mode.ARPEGIATOR or self.keyboard_config.mode == Mode.MULTISEQUENCER:
                  #gate lenght picto
                start_line = 62
                gate_up = 3
                gate_low = 13            
                gate_lenght = self.keyboard_config.player_note_timer_gate_pertenth
                gate_off = 10 - gate_lenght
                
                if self.keyboard_config.changing_gate_length:
                    self.fill_rect(start_line-1,0,23,15,self.white)
                    self.line(start_line,gate_low,start_line+2,gate_low,self.black)
                    self.line(start_line+2,gate_low,start_line+2,gate_up,self.black)
                    self.line(start_line+2,gate_up,start_line+2*gate_lenght,gate_up,self.black)
                    self.line(start_line+2*gate_lenght,gate_up,start_line+2*gate_lenght,gate_low,self.black)
                    self.line(start_line+2*gate_lenght,13,start_line+2*gate_lenght+2*(gate_off),13,self.black)

                else:
                    self.line(start_line,gate_low,start_line+2,gate_low,self.white)
                    self.line(start_line+2,gate_low,start_line+2,gate_up,self.white)
                    self.line(start_line+2,gate_up,start_line+2*gate_lenght,gate_up,self.white)
                    self.line(start_line+2*gate_lenght,gate_up,start_line+2*gate_lenght,gate_low,self.white)
                    self.line(start_line+2*gate_lenght,13,start_line+2*gate_lenght+2*(gate_off),13,self.white)
                
                # bottom block key and Tdiv
                self.fill_rect(0,50,128,64,self.white)
                key_str = "Key:C"+str(self.keyboard_config.octave_offset+4)
                self.font_writer_arial10.text(key_str,2, 53, True)
                #TODO
                time_div_x = 39
                time_div_y = 51
                if self.keyboard_config.change_time_div == True:
                    self.fill_rect(time_div_x,time_div_y,76,12,self.black)
                    time_div_str = "TimeDiv : "+timeDivToStr(self.keyboard_config.load_time_div)
                    self.font_writer_arial10.text(time_div_str,time_div_x+2, time_div_y+2)
                else:    
                    time_div_str = "TimeDiv : "+timeDivToStr(self.keyboard_config.time_div)
                    self.font_writer_arial10.text(time_div_str,time_div_x+2, time_div_y+2,True)
                
            
        
                
        if self.keyboard_config.mode == Mode.BASIC:
            key_str = "Key : C"+str(self.keyboard_config.octave_offset+4)
            self.font_writer_font6.text(key_str,5, 22)
            
            time_div_x = 3
            time_div_y = 42
            if self.keyboard_config.change_time_div == True:
                self.fill_rect(time_div_x,time_div_y,101,16,self.white)
                time_div_str = "TimeDiv : "+timeDivToStr(self.keyboard_config.load_time_div)
                self.font_writer_font6.text(time_div_str,time_div_x+2, time_div_y+2,True)
            else:    
                time_div_str = "TimeDiv : "+timeDivToStr(self.keyboard_config.time_div)
                self.font_writer_font6.text(time_div_str,time_div_x+2, time_div_y+2,False)
            
            midi_ch_x = 96
            midi_ch_y = 16
            if self.keyboard_config.midi_change_channel == True:
                self.rect(midi_ch_x,midi_ch_y,31,12,self.white)
                midi_channel_txt = 'Ch {:02d}'.format(self.keyboard_config.midi_change_channel_channel).replace("0","_")
                self.font_writer_arial10.text(midi_channel_txt,midi_ch_x+2,midi_ch_y+2)
                self.rect(midi_ch_x,midi_ch_y,31,12,self.white)
            else:
                self.fill_rect(midi_ch_x,midi_ch_y,31,12,self.white)
                midi_channel_txt = 'Ch {:02d}'.format(self.keyboard_config.midi_channel)
                self.font_writer_arial10.text(midi_channel_txt,midi_ch_x+2,midi_ch_y+2,True)


        
        elif self.keyboard_config.mode == Mode.SEQUENCER:
            seq_n_x = 3
            seq_n_y = 17
            if self.keyboard_config.loading_seq:
                seq_number_str = 'Seq n  {:02d}'.format(self.keyboard_config.loading_seq_number).replace("0","_")
                self.fill_rect(seq_n_x,seq_n_y,66,16,self.white)
                self.font_writer_font6.text(seq_number_str,seq_n_x+2,seq_n_y+2,True)
                self.font_writer_arial10.text("o",seq_n_x+38,seq_n_y,True)
            else:
                seq_number_str = 'Seq n  {:02d}'.format(self.keyboard_config.seq_number)
                self.font_writer_font6.text(seq_number_str,seq_n_x+2,seq_n_y+2)
                self.font_writer_arial10.text("o",seq_n_x+38,seq_n_y)
                
            self.font_writer_font6.text("{:03d} steps".format(self.keyboard_config.seq_len),seq_n_x+2, seq_n_y+18)
 
                
        elif self.keyboard_config.mode == Mode.ARPEGIATOR:
            
            for i in range(0,8):
                if self.keyboard_config.arp_mode == i:
                    self.fill_rect(0+i*16, 34,16,16,self.white)
                    self.blit(self.fbufs_inv_arp_modes[i],0+i*16, 34)
                else:    
                    self.blit(self.fbufs_arp_modes[i],0+i*16, 34)
                    self.rect(0+i*16, 34,16,16,self.white)
            
            if self.keyboard_config.hold:
                time_div_str = "H"
                self.rect(114,51,12,12,self.black)
                self.text(time_div_str,116,53,self.black)
            else:   
                time_div_str = "H"
                self.fill_rect(114,51,12,12,self.black)
                self.text(time_div_str,116,53,self.white)
                
        elif self.keyboard_config.mode == Mode.MULTISEQUENCER:
            
        # self.multi_sequence_index
        # self.multi_sequence_highlighted
        # self.loading_multi_seq
        # self.loading_multi_seq_number
            
            for y in range(0,2):
                for x in range(0,8):
                    index = 8*y + x
                    if index == self.keyboard_config.multi_sequence_highlighted:                        
                        self.fill_rect(0+x*16, 17+16*y,16,16,self.white)
                        self.rect(0+x*16, 17+16*y,16,16,self.black)
                        if self.keyboard_config.loading_multi_seq == True:
                            if self.keyboard_config.loading_multi_seq_number == -1:
                                index_str = "__"
                            elif self.keyboard_config.loading_multi_seq_number == 0:
                                index_str = "_0"
                            else:
                                index_str = '{:02d}'.format(self.keyboard_config.loading_multi_seq_number).replace("0", "_")
                            self.font_writer_arial8.text(index_str,4+x*16, 23+16*y,True)
                        else:
                            if self.keyboard_config.multi_sequence_index[index] == -1:
                                index_str = '{:02d}'.format(index+1)
                                self.font_writer_arial8.text(index_str,2+x*16, 19+16*y,True)
                            else:
                                index_str = '{:02d}'.format(self.keyboard_config.multi_sequence_index[index])
                                self.font_writer_arial10.text(index_str,2+x*16, 21+16*y,True)
                    else:                        
                        self.rect(0+x*16, 17+16*y,16,16,self.white)
                        
                        if self.keyboard_config.multi_sequence_index[index] == -1:
                            index_str = '{:02d}'.format(index+1)
                            self.font_writer_arial8.text(index_str,2+x*16, 19+16*y)
                        else:
                            index_str = '{:02d}'.format(self.keyboard_config.multi_sequence_index[index])
                            self.font_writer_arial10.text(index_str,2+x*16, 21+16*y)
        
        self.show()    
            
            
        
        print("*-"*20)
        print("Mode :",modeToStr(self.keyboard_config.mode))#ok
        print("TimeDiv :",timeDivToStr(self.keyboard_config.time_div))#ok
        print("Rate :",self.keyboard_config.rate,"bpm")#ok
        print("First Key : C"+str(self.keyboard_config.octave_offset+4))#ok
        print("Play/pause :"+playModeToStr(self.keyboard_config.play_mode))#ok
        print("Sequencer len :", self.keyboard_config.seq_len)
        print("Sequencer number :", self.keyboard_config.seq_number)
        print("Loading sequencer number :", self.keyboard_config.loading_seq_number)
        print("Hold : ", self.keyboard_config.hold)#ok
        print("Gate  : ", self.keyboard_config.player_note_timer_gate_pertenth*10,"%")#ok
        print("Midi channel : ",self.keyboard_config.midi_channel)
        print("Arp Mode : ", arpModeToStr(self.keyboard_config.arp_mode))
        print("*-"*20)
          
if __name__=='__main__':
    keyboard_config = KeyboardConfiguration()
    OLED_tst = OLED_1inch3(keyboard_config)
    keyboard_config.set_display(OLED_tst)
    
    OLED_tst.display_helixbyte()
    time.sleep(0.5)
    OLED_tst.display()


    """
    OLED.fill(0x0000) 
    OLED.show()
    OLED.rect(0,0,128,64,OLED.white)
    time.sleep(0.5)
    OLED.show()
    OLED.rect(10,22,20,20,OLED.white)
    time.sleep(0.5)
    OLED.show()
    OLED.fill_rect(40,22,20,20,OLED.white)
    time.sleep(0.5)
    OLED.show()
    OLED.rect(70,22,20,20,OLED.white)
    time.sleep(0.5)
    OLED.show()
    OLED.fill_rect(100,22,20,20,OLED.white)
    time.sleep(0.5)
    OLED.show()
    time.sleep(1)
    
    OLED.fill(0x0000)
    OLED.line(0,0,5,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,20,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,35,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,65,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,95,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,125,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,125,41,OLED.white)
    OLED.show()
    time.sleep(0.1)
    OLED.line(0,0,125,21,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,125,3,OLED.white)
    OLED.show()
    time.sleep(0.01)
    
    OLED.line(127,1,125,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,110,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,95,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,65,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,35,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,1,64,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,1,44,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,1,24,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,1,3,OLED.white)
    OLED.show()
    time.sleep(1)
    OLED.fill(0x0000) 
    OLED.text("128 x 64 Pixels",1,10,OLED.white)
    OLED.text("Pico-OLED-1.3",1,27,OLED.white)
    OLED.text("SH1107",1,44,OLED.white)  
    OLED.show()
    
    time.sleep(1)
    OLED.fill(0x0000) 
    keyA = Pin(15,Pin.IN,Pin.PULL_UP)
    keyB = Pin(17,Pin.IN,Pin.PULL_UP)
    while(1):
        if keyA.value() == 0:
            OLED.fill_rect(0,0,128,20,OLED.white)
            print("A")
        else :
            OLED.fill_rect(0,0,128,20,OLED.black)
            
            
        if(keyB.value() == 0):
            OLED.fill_rect(0,44,128,20,OLED.white)
            print("B")
        else :
            OLED.fill_rect(0,44,128,20,OLED.black)
        OLED.fill_rect(0,22,128,20,OLED.white)
        OLED.text("press the button",0,28,OLED.black)
            
        OLED.show()
    
    
    time.sleep(1)
    OLED.fill(0xFFFF)
"""




