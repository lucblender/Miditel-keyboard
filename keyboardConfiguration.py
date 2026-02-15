import machine
from machine import Pin, Timer
import ustruct
from random import randrange
import json

MIN_BPM = 30
MAX_BPM = 240

LEN_INDEX = -1

POT_MAX_VALUE = 42000
POT_MIN_VALUE = 24000
POT_INTERVAL_VALUE = POT_MAX_VALUE-POT_MIN_VALUE

# Lookup tables for O(1) performance instead of if-elif chains
# Indexed by TimeDiv enum values
TIME_DIV_TO_SPLIT = (24, 16, 12, 8, 6, 4, 3, 2)
TIME_DIV_TO_STR = ("1/4", "1/4T", "1/8", "1/8T",
                   "1/16", "1/16T", "1/32", "1/32T")
MODE_TO_STR = ("Basic", "Arpeg", "Sequ", "Multi\nsequencer")
ARP_MODE_TO_STR = ("Up", "Down", "Inclusive", "Exclusive",
                   "Random", "Press Order", "Up x2", "Down x2")
PLAY_MODE_TO_STR = ("⏵", "⏸", "⏺", "⏹")


def enum(**enums: int):
    return type('Enum', (), enums)


Mode = enum(BASIC=0, ARPEGIATOR=1, SEQUENCER=2, MULTISEQUENCER=3)

TimeDiv = enum(ONE_FOURTH=0,
               ONE_FOURTH_T=1,
               ONE_EIGHTH=2,
               ONE_EIGHTH_T=3,
               ONE_SIXTEENTH=4,
               ONE_SIXTEENTH_T=5,
               ONE_THIRTYSECOND=6,
               ONE_THIRTYSECOND_T=7)


PlayMode = enum(PLAYING=0,
                PAUSING=1,
                RECORDING=2,
                STOPPED=3)

ArpMode = enum(UP=0,
               DWN=1,
               INC=2,
               EXC=3,
               RAND=4,
               ORDER=5,
               UPX2=6,
               DWNX2=7,
               )


def modeToStr(local_mode):
    return MODE_TO_STR[local_mode]


def timeDivToStr(local_time_div):
    return TIME_DIV_TO_STR[local_time_div]


def timeDivToTimeSplit(local_time_div):
    return TIME_DIV_TO_SPLIT[local_time_div]


def arpModeToStr(local_arp_mode):
    return ARP_MODE_TO_STR[local_arp_mode]


def sort_notes_for_arp_mode(local_arp_mode, arp_notes):
    to_return = []
    cpy_arp_notes = list(arp_notes)

    if local_arp_mode == ArpMode.UP:
        cpy_arp_notes.sort()
        to_return = cpy_arp_notes
    elif local_arp_mode == ArpMode.DWN:
        cpy_arp_notes.sort()
        cpy_arp_notes.reverse()
        to_return = cpy_arp_notes
    elif local_arp_mode == ArpMode.INC:
        cpy_arp_notes.sort()
        rev_cpy_arp_notes = list(cpy_arp_notes)
        rev_cpy_arp_notes.reverse()
        to_return = cpy_arp_notes+rev_cpy_arp_notes
    elif local_arp_mode == ArpMode.EXC:
        cpy_arp_notes.sort()
        rev_cpy_arp_notes = list(cpy_arp_notes)
        rev_cpy_arp_notes.reverse()
        to_return = cpy_arp_notes+rev_cpy_arp_notes[1:-1]
    # in random, the index of the note played will be random, the array doesn't change
    elif local_arp_mode == ArpMode.RAND:
        to_return = cpy_arp_notes
    elif local_arp_mode == ArpMode.ORDER:
        to_return = cpy_arp_notes
    elif local_arp_mode == ArpMode.UPX2:
        cpy_arp_notes.sort()
        for x in cpy_arp_notes:
            to_return.append(x)
            to_return.append(x)
    elif local_arp_mode == ArpMode.DWNX2:
        cpy_arp_notes.sort()
        cpy_arp_notes.reverse()
        for x in cpy_arp_notes:
            to_return.append(x)
            to_return.append(x)
    return to_return


def playModeToStr(local_play_mode):
    return PLAY_MODE_TO_STR[local_play_mode]


def midi_to_key(note_num):
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (note_num // 12) - 1
    key = notes[note_num % 12] + str(octave)
    return key


def append_error(error):
    print("*-"*20)
    print("Error caught")
    print(error)
    print("*-"*20)
    error_file = open("error.txt", "a")
    error_file.write(str(error))
    error_file.write("\n")
    error_file.close()


def decomp(n):
    L = dict()
    k = 2
    while n != 1:
        exp = 0
        while n % k == 0:
            n = n // k
            exp += 1
        if exp != 0:
            L[k] = exp
        k = k + 1
    return L


def _ppcm(a, b):
    Da = decomp(a)
    Db = decomp(b)
    p = 1
    for facteur, exposant in Da.items():
        if facteur in Db:
            exp = max(exposant, Db[facteur])
        else:
            exp = exposant
        p *= facteur**exp
    for facteur, exposant in Db.items():
        if facteur not in Da:
            p *= facteur**exposant
    return p


def ppcm(L):
    while len(L) > 1:
        a = L[-1]
        L.pop()
        b = L[-1]
        L.pop()
        L.append(_ppcm(a, b))
    return L[0]


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
        self.rate = 60
        self.mod = 0
        self.pitch_bend = 0x2000
        self.pitch_bend_counter = 0

        self.octave_offset = 0
        self.play_mode = PlayMode.STOPPED

        self.rate_led = None

        self.time_div = TimeDiv.ONE_FOURTH
        self.change_time_div = False
        self.load_time_div = TimeDiv.ONE_FOURTH

        # flag to tell if a midi resume or midi play needs to be sent befor a midi tick
        self.request_midi_resume = False
        self.request_midi_playing = False

        self.midi_change_channel = False
        self.midi_change_channel_channel = 0
        self.midi_channel = 1

        # sequencer linked attributes
        # TODO
        self.seq_len = 0
        self.seq_notes = {}
        self.current_seq_index = 0
        self.seq_number = 0
        self.seq_current_rec_notes = []
        self.seq_played_notes = []

        self.loading_seq = False
        self.loading_seq_number = 0
        self.last_seq_key_played = -1
        # true = transpose, false = keyboardplay
        self.transpose_keyboardplay_mode = True
        self.transpose_key = 60  # 60 = C4

        # arpegiator linked attributes
        self.arp_mode = ArpMode.ORDER
        self.hold = False
        self.arp_len = 0
        self.arp_notes = []
        self.current_arp_index = 0
        self.last_arp_key_played = -1
        self.arp_number_note_pressed = 0

        # multi sequencer attributes

        self.multi_sequence_index = [-1]*16
        self.last_multi_seq_key_played = [-1]*16
        self.multi_seq_played_notes = [[] for i in range(0, 16)]
        self.multi_sequence_notes = [{LEN_INDEX: 0}]*16
        self.multi_sequence_highlighted = 0
        self.multi_sequence_global_index = 0
        self.multi_sequence_global_index_tst = 0
        self.multi_sequence_index_boundary = 0
        self.multi_sequence_time_div = [TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH,
                                        TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH,
                                        TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH,
                                        TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH, TimeDiv.ONE_FOURTH]
        self.loading_multi_seq = False
        self.loading_multi_seq_number = -1
        self.keyboard_play_index = -1

        # gate lenght attributes
        self.changing_gate_length = False

        # Performance optimization caches
        self._gate_offset_cache = {}
        self._multi_time_div_cache = [None] * 16
        self._cached_arp_notes = None
        self._cached_arp_mode = None
        self._cached_arp_result = None

        # Multi-sequencer specific optimizations
        self._active_channels_mask = 0  # Bitmask of active channels
        self._active_channels_list = []  # Pre-computed list of active channel indices
        self._channel_timing_cache = {}  # Pre-computed timing values per channel
        self._channel_sequence_indices = [
            0] * 16  # Per-channel sequence indices
        self._midi_message_queue = []  # MIDI message batching queue
        self.MAX_BATCH_SIZE = 6  # Maximum MIDI messages to batch

        self.uart = machine.UART(0, baudrate=31250, tx=Pin(16), rx=Pin(17))
        self.led = Pin(25, machine.Pin.OUT)

        self.play_note_timer = Timer(-1)
        self.update_timer_frequency()
        self.play_note_timer_tenth_counter = 0
        self.player_note_timer_gate_pertenth = 5
        self._update_gate_cache()
        self._update_active_channels()  # Initialize active channels
        if self._active_channels_list:
            self._update_channel_timing_cache()  # Initialize timing cache
        self.oled_display = None
        self.display()

    def set_led(self, led):
        self.rate_led = led
        self.rate_led.off()

    def set_display(self, oled_display):
        self.oled_display = oled_display

    def display(self):
        if self.oled_display != None:
            self.oled_display.need_screen_refresh()

    def _update_gate_cache(self):
        """Pre-calculate all gate timing offsets for performance"""
        self._gate_offset_cache.clear()

        # Cache for all time divisions (0-7) and gate lengths (1-9)
        for t_div_enum in range(8):  # TimeDiv enum values 0-7
            t_div = TIME_DIV_TO_SPLIT[t_div_enum]
            for gate_tenth in range(1, 10):  # Gate lengths 1-9
                gate_offset = int(((10-gate_tenth)/10) * (240*(t_div/24)))
                key = (t_div, gate_tenth)
                self._gate_offset_cache[key] = gate_offset

    def _get_gate_offset(self, t_div, gate_length):
        """Get cached gate offset - O(1) lookup"""
        return self._gate_offset_cache.get((t_div, gate_length), 0)

    def _get_multi_time_split(self, channel):
        """Cached multi-sequencer time division lookup"""
        if self._multi_time_div_cache[channel] is None:
            self._multi_time_div_cache[channel] = TIME_DIV_TO_SPLIT[self.multi_sequence_time_div[channel]]
        return self._multi_time_div_cache[channel]

    def _invalidate_multi_cache(self, channel=None):
        """Invalidate multi-sequencer cache when time divisions change"""
        if channel is None:
            self._multi_time_div_cache = [None] * 16
        else:
            self._multi_time_div_cache[channel] = None

    def _update_active_channels(self):
        """Update bitmask and list of channels with sequences"""
        self._active_channels_mask = 0
        self._active_channels_list.clear()

        for i in range(16):
            if (len(self.multi_sequence_notes[i]) > 1 and
                    self.multi_sequence_notes[i][LEN_INDEX] > 0):
                self._active_channels_mask |= (1 << i)
                self._active_channels_list.append(i)

    def _update_channel_timing_cache(self):
        """Pre-compute timing values for all active channels"""
        self._channel_timing_cache.clear()
        per_tenth = self.player_note_timer_gate_pertenth

        for channel in self._active_channels_list:
            t_div = self._get_multi_time_split(channel)
            gate_offset = self._get_gate_offset(t_div, per_tenth)

            self._channel_timing_cache[channel] = {
                't_div': t_div,
                't_div_x10': t_div * 10,
                'gate_offset': gate_offset,
                'seq_len': self.multi_sequence_notes[channel][LEN_INDEX]
            }

    def _process_channel_note_on(self, channel, _counter=None):
        """Process note-on for a specific channel"""
        cache = self._channel_timing_cache[channel]
        if cache['seq_len'] == 0:
            return

        seq_index = int((self.multi_sequence_global_index_tst /
                        cache['t_div']) % cache['seq_len'])

        if seq_index in self.multi_sequence_notes[channel]:
            note_data = self.multi_sequence_notes[channel][seq_index]
            note_to_play = [note_data[0], min(note_data[1], cache['seq_len'])]

            self._queue_midi_message(0x90 + channel, note_to_play[0], 127)
            self.multi_seq_played_notes[channel].append(note_to_play)

    def _process_channel_note_off(self, channel):
        """Process note-off for a specific channel using efficient list iteration"""
        if not self.multi_seq_played_notes[channel]:
            return

        # Use reverse iteration to avoid index shifting during removal
        for i in range(len(self.multi_seq_played_notes[channel]) - 1, -1, -1):
            note = self.multi_seq_played_notes[channel][i]
            note[1] -= 1
            if note[1] <= 0:
                self._queue_midi_message(0x80 + channel, note[0], 0)
                self.multi_seq_played_notes[channel].pop(
                    i)  # More efficient than remove()

    def _queue_midi_message(self, status, data1, data2):
        """Queue MIDI message for batch sending"""
        self._midi_message_queue.append((status, data1, data2))

        if len(self._midi_message_queue) >= self.MAX_BATCH_SIZE:
            self._flush_midi_queue()

    def _flush_midi_queue(self):
        """Send all queued MIDI messages in one UART write"""
        if not self._midi_message_queue:
            return

        # Create one large buffer for all messages
        total_size = len(self._midi_message_queue) * 3
        batch_buffer = bytearray(total_size)

        for i, (status, data1, data2) in enumerate(self._midi_message_queue):
            offset = i * 3
            batch_buffer[offset] = status
            batch_buffer[offset + 1] = data1
            batch_buffer[offset + 2] = data2

        self.uart.write(batch_buffer)
        self._midi_message_queue.clear()

    def _on_sequence_loaded(self, channel):
        """Called when a sequence is loaded to a channel"""
        self._update_active_channels()
        if self._active_channels_list:
            self._update_channel_timing_cache()

    def timer_callback(self, timer):
        try:
            if self.mode == Mode.BASIC:
                pass
            elif self.mode == Mode.SEQUENCER:
                if self.play_mode == PlayMode.PLAYING:
                    # set variable to compute ton and toff to make it more readable
                    counter = self.play_note_timer_tenth_counter
                    t_div = TIME_DIV_TO_SPLIT[self.time_div]
                    per_tenth = self.player_note_timer_gate_pertenth
                    gate_offset = self._get_gate_offset(t_div, per_tenth)

                    if (counter % (t_div*10)) == 0:
                        if self.current_seq_index in self.seq_notes:
                            note_to_play = self.seq_notes[self.current_seq_index].copy(
                            )
                            note_to_play[0] = note_to_play[0] + \
                                (self.transpose_key-60)
                            # in the case we deleted too many note and a note is longer than the sequence:
                            if note_to_play[1] > self.seq_len:
                                note_to_play[1] = self.seq_len
                            self.__send_note_on(note_to_play[0])
                            self.seq_played_notes.append(note_to_play.copy())
                        self.current_seq_index = (
                            self.current_seq_index+1) % self.seq_len
                    elif (counter + gate_offset) % (t_div*10) == 0:

                        notes_to_remove = []
                        for seq_played_note in self.seq_played_notes:
                            seq_played_note[1] = seq_played_note[1] - 1
                            if seq_played_note[1] <= 0:
                                self.__send_note_off(seq_played_note[0])
                                notes_to_remove.append(seq_played_note)

                        for note_to_remove in notes_to_remove:
                            self.seq_played_notes.remove(note_to_remove)
            elif self.mode == Mode.ARPEGIATOR:
                # set variable to compute ton and toff to make it more readable
                counter = self.play_note_timer_tenth_counter
                t_div = TIME_DIV_TO_SPLIT[self.time_div]
                per_tenth = self.player_note_timer_gate_pertenth
                gate_offset = self._get_gate_offset(t_div, per_tenth)

                if self.play_mode == PlayMode.PLAYING:
                    if (counter % (t_div*10)) == 0:
                        if (len(self.arp_notes) != 0):
                            # Cache arp note sorting to avoid recalculation
                            if (self._cached_arp_notes != self.arp_notes or
                                    self._cached_arp_mode != self.arp_mode):
                                self._cached_arp_notes = self.arp_notes.copy()
                                self._cached_arp_mode = self.arp_mode
                                self._cached_arp_result = sort_notes_for_arp_mode(
                                    self.arp_mode, self.arp_notes)

                            arp_notes_mode = self._cached_arp_result

                            if (self.current_arp_index > len(arp_notes_mode) - 1):
                                self.current_arp_index = len(
                                    arp_notes_mode) - 1
                            if self.arp_mode == ArpMode.RAND:
                                self.last_arp_key_played = arp_notes_mode[randrange(
                                    0, len(arp_notes_mode))]
                            else:
                                self.last_arp_key_played = arp_notes_mode[self.current_arp_index]
                            self.__send_note_on(self.last_arp_key_played)
                            self.current_arp_index = (
                                self.current_arp_index+1) % len(arp_notes_mode)
                    elif (counter + gate_offset) % (t_div*10) == 0:
                        if self.last_arp_key_played != -1:
                            self.__send_note_off(self.last_arp_key_played)
            elif self.mode == Mode.MULTISEQUENCER:

                if self.play_mode == PlayMode.PLAYING:
                    counter = self.play_note_timer_tenth_counter

                    # Only process active channels with sequences
                    for channel in self._active_channels_list:
                        cache = self._channel_timing_cache[channel]
                        t_div_x10 = cache['t_div_x10']
                        gate_offset = cache['gate_offset']

                        # Note ON timing - optimized with cached values
                        if (counter % t_div_x10) == 0:
                            self._process_channel_note_on(channel)

                        # Note OFF timing - optimized with cached values
                        if (counter + gate_offset) % t_div_x10 == 0:
                            self._process_channel_note_off(channel)

                    # Global index increment (only every 10th callback)
                    if (counter % 10) == 0:
                        self.multi_sequence_global_index_tst += 1

                    # Flush any remaining MIDI messages at end of callback
                    self._flush_midi_queue()

            if self.request_midi_resume == True and self.play_note_timer_tenth_counter % 240 == 0:
                self.request_midi_resume = False
                self.__send_midi_continue()
            elif self.request_midi_playing == True and self.play_note_timer_tenth_counter % 240 == 0:
                self.request_midi_playing = False
                self.__send_midi_start()

            if self.play_note_timer_tenth_counter % 10 == 0:
                self.__send_midi_clock()

            if self.play_note_timer_tenth_counter % 240 == 0:
                if self.rate_led != None:
                    self.rate_led.on()

            if (self.play_note_timer_tenth_counter+20) % 120 == 0:
                if self.rate_led != None:
                    self.rate_led.off()

            self.play_note_timer_tenth_counter = (
                self.play_note_timer_tenth_counter+1) % 480
        except Exception as e:
            self.deinit_timer()
            append_error(e)

    def update_timer_frequency(self):
        period = (((60/self.rate)*1000)/240)
        freq = 1/period
        # self.play_note_timer.deinit()
        # self.play_note_timer.init(period=int(((60/self.rate)*1000)/240), mode=Timer.PERIODIC, callback=self.timer_callback)
        self.play_note_timer.init(
            freq=freq*1000, mode=Timer.PERIODIC, callback=self.timer_callback)

    def deinit_timer(self):
        self.play_note_timer.deinit()

    def incr_octave_offset(self):
        self.octave_offset += 1
        if self.octave_offset > -4 + 9:  # main key is 4 so -4 then limit key +9
            self.octave_offset = -4 + 9
            print("capping octave offset to key +9")
        self.display()

    def decr_octave_offset(self):
        self.octave_offset -= 1
        if self.octave_offset < -1 - 4:  # main key is 4 so -4 then limit key -1
            self.octave_offset = -1 - 4
            print("capping octave offset to key -1")
        self.display()

    def incr_mode(self):
        self.play_mode = PlayMode.STOPPED
        self.mode = ((self.mode+1) % 4)
        if self.last_seq_key_played != -1:
            self.__send_note_off(self.last_seq_key_played)
        self.__send_all_note_off()

        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            self.seq_notes = self.load_sequence_file(self.seq_number)
        elif self.mode == Mode.ARPEGIATOR:
            self.arp_len = 0  # reset arpegiator
            self.arp_notes = []
            self.current_arp_index = 0
            self.arp_number_note_pressed = 0

        self.display()

    def decr_mode(self):
        self.play_mode = PlayMode.STOPPED
        self.mode = ((self.mode-1) % 4)
        if self.last_seq_key_played != -1:
            self.__send_note_off(self.last_seq_key_played)
        self.__send_all_note_off()

        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            self.seq_notes = self.load_sequence_file(self.seq_number)
        elif self.mode == Mode.ARPEGIATOR:
            self.arp_len = 0  # reset arpegiator
            self.arp_notes = []
            self.current_arp_index = 0
            self.arp_number_note_pressed = 0

        self.display()

    def incr_arp_mode_undo_seq(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            if self.play_mode == PlayMode.RECORDING:
                if len(self.seq_notes) > 0:

                    self.seq_len -= 1
                    self.seq_notes[LEN_INDEX] = self.seq_len

                    if self.seq_len in self.seq_notes:
                        self.seq_notes.pop(self.seq_len)

                    self.save_sequence_file(self.seq_number)
                    self.display()
        elif self.mode == Mode.ARPEGIATOR:
            self.arp_mode = (self.arp_mode+1) % 8
            self.display()

    def decr_arp_mode_kbp_transpose(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            self.transpose_keyboardplay_mode = not self.transpose_keyboardplay_mode
            self.display()
        elif self.mode == Mode.ARPEGIATOR:
            self.arp_mode = (self.arp_mode-1) % 8
            self.display()
        elif self.mode == Mode.MULTISEQUENCER:
            if self.keyboard_play_index == self.multi_sequence_highlighted:
                self.keyboard_play_index = -1
            else:
                self.keyboard_play_index = self.multi_sequence_highlighted
            self.display()

    def set_rate_potentiometer(self, pot_value):
        old_rate = self.rate
        new_rate = ((pot_value/65536) * (MAX_BPM-MIN_BPM) + MIN_BPM)

        if abs(new_rate - old_rate) > 0.7:
            self.rate = int(new_rate)
            if old_rate != self.rate:  # only refresh if rate really changed
                self.update_timer_frequency()
                self.display()

    # hex --> from 0 to 0x3fff, 0x2000 is the center, divided range by two on my setup
    def set_pitch_potentiometer(self, pot_value):
        # dec --> from 0 to 16383,  8192

        old_pitch_bend = self.pitch_bend

        new_pitch_bend = (
            ((((pot_value-POT_MIN_VALUE)/POT_INTERVAL_VALUE)) * (0x3fff/2))+0x2000/2)

        if abs(new_pitch_bend - old_pitch_bend) > 100:
            self.pitch_bend = new_pitch_bend
            self.__send_pitch_wheel(int(self.pitch_bend))
            self.pitch_bend_counter = 0
        else:
            if self.pitch_bend_counter != -1:
                self.pitch_bend_counter += 1
                if self.pitch_bend_counter > 500:
                    self.pitch_bend_counter = -1
                    self.__send_pitch_wheel(0x2000)

    def set_mod_potentiometer(self, pot_value):  # mod from 0 to 127
        old_mod = self.mod
        new_mod = (((pot_value-POT_MIN_VALUE)/POT_INTERVAL_VALUE) * 127)

        if abs(new_mod - old_mod) > 3:
            self.mod = new_mod
            self.__send_mod_wheel(int(self.mod))

    def note_on(self, note):
        if self.mode == Mode.BASIC:
            self.__send_note_on(note)
        elif self.mode == Mode.SEQUENCER:
            if self.play_mode == PlayMode.RECORDING:  # TODO
                self.seq_current_rec_notes.append([note, 0])
                self.__send_note_on(note)
                self.display()
            elif self.play_mode == PlayMode.PLAYING:
                if self.transpose_keyboardplay_mode == True:
                    self.transpose_key = note
                    self.display()
                else:
                    self.__send_note_on(note)
            elif self.play_mode == PlayMode.STOPPED:
                self.__send_note_on(note)
        elif self.mode == Mode.ARPEGIATOR:

            if self.play_mode == PlayMode.STOPPED:
                self.__send_note_on(note)
            else:
                self.arp_number_note_pressed += 1
                if self.hold == False:
                    self.arp_notes.append(note)
                else:
                    if self.arp_number_note_pressed == 1:
                        self.arp_notes = []
                    self.arp_notes.append(note)
        elif self.mode == Mode.MULTISEQUENCER:

            if self.keyboard_play_index != -1:
                # +1 since midi channel start to 1
                self.__send_note_midi_on(note, self.keyboard_play_index+1)

    def note_off(self, note):
        if self.mode == Mode.BASIC:
            self.__send_note_off(note)
        elif self.mode == Mode.SEQUENCER:
            if self.play_mode == PlayMode.PLAYING:
                self.__send_note_off(note)
            elif self.play_mode == PlayMode.STOPPED:
                self.__send_note_off(note)

            elif self.play_mode == PlayMode.RECORDING:  # TODO
                # incr all note lenght
                self.__send_note_off(note)

                self.seq_len += 1
                self.seq_notes[LEN_INDEX] = self.seq_len
                for seq_current_rec_notes in self.seq_current_rec_notes:
                    seq_current_rec_notes[1] = seq_current_rec_notes[1] + 1

                note_to_remove = []
                # find note that were in rec_notes to remove
                for seq_current_rec_notes in self.seq_current_rec_notes:
                    if note in seq_current_rec_notes:
                        note_to_remove = seq_current_rec_notes
                        break

                if note_to_remove != []:
                    self.seq_notes[self.seq_len -
                                   note_to_remove[1]] = note_to_remove
                    self.seq_current_rec_notes.remove(note_to_remove)
                self.save_sequence_file(self.seq_number)
                self.display()

        elif self.mode == Mode.ARPEGIATOR:
            if self.play_mode == PlayMode.STOPPED:
                self.__send_note_off(note)
            else:
                self.arp_number_note_pressed -= 1
                if self.hold == False:
                    if note in self.arp_notes:
                        self.arp_notes.remove(note)
        elif self.mode == Mode.MULTISEQUENCER:
            if self.keyboard_play_index != -1:
                # +1 since midi channel start to 1
                self.__send_note_midi_off(note, self.keyboard_play_index+1)

    def __send_note_on(self, note):
        self.__send_note_midi_on(note, self.midi_channel)

    def __send_note_off(self, note):
        self.__send_note_midi_off(note, self.midi_channel)

    # note on midi channel when doing uart.write:
    # midi channel usually goes from 1 to 16 (in the whole code and display)
    # but when sent it goes from 0 to 15, that's why when using
    # uart.write(....) there is always midi_channel - 1
    def __send_note_midi_on(self, note, midi_channel):
        if note != -1:
            # print("__send_note_midi_on", note, midi_channel)
            self.uart.write(ustruct.pack(
                "bbb", 0x90+(midi_channel-1), note, 127))
            self.led.value(1)

    def __send_note_midi_off(self, note, midi_channel):
        if note != -1:
            # print("__send_note_midi_off", note, midi_channel)
            self.uart.write(ustruct.pack(
                "bbb", 0x80+(midi_channel-1), note, 0))
            self.led.value(0)

    def __send_all_note_off(self):
        self.__send_all_note_midi_off(self.midi_channel-1)

    def __send_all_note_midi_off(self, midi_channel):
        self.uart.write(ustruct.pack("bbb", 0xb0+(midi_channel-1), 123, 0))
        self.led.value(0)

    def __send_mod_wheel(self, mod_wheel_value):
        if mod_wheel_value > 127:
            mod_wheel_value = 127
        elif mod_wheel_value < 0:
            mod_wheel_value = 0
        self.uart.write(ustruct.pack(
            "bbb", 0xb0+(self.midi_channel-1), 1, mod_wheel_value))

    def __send_pitch_wheel(self, pitch_wheel_value):
        if pitch_wheel_value > 0x3fff:
            pitch_wheel_value = 0x3fff
        elif pitch_wheel_value < 0:
            pitch_wheel_value = 0
        lsb = pitch_wheel_value & 0x7F
        msb = (pitch_wheel_value >> 7) & 0x7F

        self.uart.write(ustruct.pack(
            "bbb", 0xe0+(self.midi_channel-1), lsb, msb))

    def __send_midi_clock(self):
        self.uart.write(ustruct.pack("b", 0xf8))

    def __send_midi_start(self):
        self.uart.write(ustruct.pack("b", 0xfa))

    def __send_midi_continue(self):
        self.uart.write(ustruct.pack("b", 0xfb))

    def __send_midi_stop(self):
        self.uart.write(ustruct.pack("b", 0xfc))

    def blank_tile_pressed(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            if self.play_mode == PlayMode.RECORDING:  # TODO
                self.seq_len += 1
                self.seq_notes[LEN_INDEX] = self.seq_len

                # incr all note lenght
                for seq_current_rec_notes in self.seq_current_rec_notes:
                    seq_current_rec_notes[1] = seq_current_rec_notes[1] + 1

                self.save_sequence_file(self.seq_number)
                self.display()
        elif self.mode == Mode.ARPEGIATOR:
            pass
        self.display()

    def stop_pressed(self):
        self.play_mode = PlayMode.STOPPED
        self.current_seq_index = 0

        if self.mode == Mode.BASIC:
            self.__send_midi_stop()
            self.__send_all_note_off()
        elif self.mode == Mode.SEQUENCER:  # TODO
            self.__send_midi_stop()
            for seq_played_note in self.seq_played_notes:
                self.__send_note_off(seq_played_note[0])
            self.seq_played_notes = []
            self.__send_all_note_off()
            self.last_arp_key_played = -1

        elif self.mode == Mode.ARPEGIATOR:
            self.__send_midi_stop()
            if self.last_arp_key_played != -1:
                self.__send_note_off(self.last_arp_key_played)
            self.last_arp_key_played = -1
        elif self.mode == Mode.MULTISEQUENCER:
            self.multi_sequence_global_index = 0
            self.multi_sequence_global_index_tst = 0
            for i in range(0, 16):
                if len(self.multi_seq_played_notes[i]) != 0:
                    for seq_played_note in self.multi_seq_played_notes[i]:
                        self.__send_note_midi_off(seq_played_note[0], i+1)
                    self.multi_seq_played_notes[i] = []
            for i in range(0, 16):
                # i+1 cause midi channel start on 1
                self.__send_all_note_midi_off(i+1)
        self.display()

    def pauseplay_pressed(self):
        self.play_note_timer_tenth_counter = 0
        if self.mode == Mode.BASIC:
            if self.play_mode != PlayMode.PLAYING:
                if self.play_mode == PlayMode.PAUSING:
                    self.request_midi_resume = True
                else:
                    self.request_midi_playing = True
                self.play_mode = PlayMode.PLAYING
            else:
                self.__send_midi_stop()
                self.play_mode = PlayMode.PAUSING
                if self.last_arp_key_played != -1:
                    self.__send_note_off(self.last_arp_key_played)
        elif self.mode == Mode.SEQUENCER:  # TODO
            if self.play_mode != PlayMode.PLAYING:
                if self.seq_len != 0:
                    if self.play_mode == PlayMode.PAUSING:
                        self.request_midi_resume = True
                    else:
                        self.request_midi_playing = True
                    self.play_mode = PlayMode.PLAYING
            else:
                self.__send_midi_stop()
                self.play_mode = PlayMode.PAUSING
                for seq_played_note in self.seq_played_notes:
                    self.__send_note_off(seq_played_note[0])
                self.seq_played_notes = []
                self.__send_all_note_off()
                self.last_seq_key_played = -1
        elif self.mode == Mode.ARPEGIATOR:
            if self.play_mode != PlayMode.PLAYING:
                if self.play_mode == PlayMode.PAUSING:
                    self.request_midi_resume = True
                else:
                    self.request_midi_playing = True
                self.play_mode = PlayMode.PLAYING
            else:
                self.__send_midi_stop()
                self.play_mode = PlayMode.PAUSING
                if self.last_arp_key_played != -1:
                    self.__send_note_off(self.last_arp_key_played)
                self.last_arp_key_played = -1
        elif self.mode == Mode.MULTISEQUENCER:
            if self.multi_sequence_index_boundary != 0:
                if self.play_mode != PlayMode.PLAYING:
                    if self.play_mode == PlayMode.PAUSING:
                        self.request_midi_resume = True
                    else:
                        self.request_midi_playing = True
                    self.play_mode = PlayMode.PLAYING
                else:
                    self.__send_midi_stop()
                    self.play_mode = PlayMode.PAUSING
                    for i in range(0, 16):
                        if len(self.multi_seq_played_notes[i]) != 0:
                            for seq_played_note in self.multi_seq_played_notes[i]:
                                self.__send_note_midi_off(
                                    seq_played_note[0], i+1)
                            self.multi_seq_played_notes[i] = []
                    for i in range(0, 16):
                        # i+1 cause midi channel start on 1
                        self.__send_all_note_midi_off(i+1)
        self.display()

    def rec_pressed(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            # TODO remove the last next note off from the begging of the sequence to put it later in next step
            if self.play_mode != PlayMode.RECORDING:
                for seq_played_note in self.seq_played_notes:
                    self.__send_note_off(seq_played_note[0])
                self.seq_played_notes = []
                self.__send_all_note_off()
            self.play_mode = PlayMode.RECORDING
        elif self.mode == Mode.ARPEGIATOR:
            pass
        self.display()

    def change_time_div_pressed(self):
        self.change_time_div = not self.change_time_div
        if self.change_time_div == True:
            self.midi_change_channel = False
            self.loading_seq = False
            self.changing_gate_length = False

        if self.mode == Mode.MULTISEQUENCER:
            self.load_time_div = self.multi_sequence_time_div[self.multi_sequence_highlighted]
        else:
            self.load_time_div = self.time_div
        self.display()

    def load_seq_pressed(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            self.loading_seq = not self.loading_seq
            if self.loading_seq == True:
                self.midi_change_channel = False
                self.change_time_div = False
                self.changing_gate_length = False
                self.loading_multi_seq = False
            self.loading_seq_number = 0
        elif self.mode == Mode.ARPEGIATOR:
            pass
        elif self.mode == Mode.MULTISEQUENCER:
            self.loading_multi_seq = not self.loading_multi_seq
            if self.loading_multi_seq == True:
                self.midi_change_channel = False
                self.change_time_div = False
                self.changing_gate_length = False
                self.loading_seq = False
            self.loading_multi_seq_number = -1
        self.display()

    def midi_channel_gate_length_pressed(self):
        if self.mode == Mode.BASIC:
            self.midi_change_channel = not self.midi_change_channel
            if self.midi_change_channel == True:
                self.change_time_div = False
                self.loading_seq = False
                self.changing_gate_length = False
                self.loading_multi_seq = False
            self.midi_change_channel_channel = 0
        elif self.mode == Mode.SEQUENCER or self.mode == Mode.ARPEGIATOR or self.mode == Mode.MULTISEQUENCER:
            self.changing_gate_length = not self.changing_gate_length
            if self.changing_gate_length == True:
                self.midi_change_channel = False
                self.change_time_div = False
                self.loading_seq = False
                self.loading_multi_seq = False
        self.display()

    def digit_pressed(self, digit):
        if self.mode == Mode.BASIC:
            if self.midi_change_channel == True:
                self.midi_change_channel_channel = (
                    self.midi_change_channel_channel*10)+digit
                if self.midi_change_channel_channel > 16:
                    self.midi_change_channel_channel = 16
                self.display()
        elif self.mode == Mode.SEQUENCER:
            if self.loading_seq == True:
                self.loading_seq_number = (self.loading_seq_number*10)+digit
                if self.loading_seq_number > 99:
                    self.loading_seq_number = 99
                self.display()
        elif self.mode == Mode.ARPEGIATOR:
            pass
        elif self.mode == Mode.MULTISEQUENCER:
            if self.loading_multi_seq == True:
                if self.loading_multi_seq_number == -1:
                    self.loading_multi_seq_number = 0
                self.loading_multi_seq_number = (
                    self.loading_multi_seq_number*10)+digit
                if self.loading_multi_seq_number > 99:
                    self.loading_multi_seq_number = 99
            else:
                if self.change_time_div == False:
                    if digit == 2:  # up
                        self.multi_sequence_highlighted = (
                            self.multi_sequence_highlighted+8) % 16
                    elif digit == 6:  # right
                        self.multi_sequence_highlighted = (
                            self.multi_sequence_highlighted+1) % 16
                    elif digit == 4:  # left
                        self.multi_sequence_highlighted = (
                            self.multi_sequence_highlighted-1) % 16
                    elif digit == 8:  # down
                        self.multi_sequence_highlighted = (
                            self.multi_sequence_highlighted-8) % 16

            self.display()

        if self.mode == Mode.SEQUENCER or self.mode == Mode.ARPEGIATOR or self.mode == Mode.MULTISEQUENCER:
            if self.changing_gate_length == True:
                if digit != 0:
                    self.player_note_timer_gate_pertenth = digit
                    self._update_gate_cache()  # Refresh cache when gate length changes
                    if self.mode == Mode.MULTISEQUENCER and self._active_channels_list:
                        self._update_channel_timing_cache()  # Update multi-sequencer timing cache
                self.display()

        if self.change_time_div == True:  # works in any mode
            if digit != 0 and digit != 9:
                # works with digit from 1 to 8 and the enum start to 0 so remove 1
                self.load_time_div = (digit-1)
            self.display()

    def sharp_pressed(self):  # sharp = ok
        if self.mode == Mode.BASIC:
            if self.midi_change_channel == True:
                self.midi_change_channel = False
                if self.midi_change_channel_channel != 0:
                    self.midi_channel = self.midi_change_channel_channel
                self.display()
        elif self.mode == Mode.SEQUENCER:
            if self.loading_seq == True:  # confirm loading
                self.loading_seq = False
                self.seq_number = self.loading_seq_number
                self.seq_notes = self.load_sequence_file(self.seq_number)
                self.display()
        elif self.mode == Mode.ARPEGIATOR:
            pass
        elif self.mode == Mode.MULTISEQUENCER:
            if self.loading_multi_seq == True:
                self.loading_multi_seq = False
                if self.loading_multi_seq_number == -1:
                    self.multi_sequence_notes[self.multi_sequence_highlighted] = {
                        LEN_INDEX: 0}
                    self.multi_sequence_index[self.multi_sequence_highlighted] = -1
                else:
                    self.multi_sequence_notes[self.multi_sequence_highlighted] = self.load_sequence_file(
                        self.loading_multi_seq_number, False)
                    self.multi_sequence_index[self.multi_sequence_highlighted] = self.loading_multi_seq_number

                # Update active channels and timing cache after loading
                self._on_sequence_loaded(self.multi_sequence_highlighted)

                ppcm_index_list = []
                index = 0
                for sequence_notes in self.multi_sequence_notes:
                    if sequence_notes[LEN_INDEX] > 1:
                        ppcm_index_list.append(
                            sequence_notes[LEN_INDEX]*timeDivToTimeSplit(self.multi_sequence_time_div[index]))
                    index = index + 1

                if len(ppcm_index_list) == 0:
                    self.multi_sequence_index_boundary = 0
                else:
                    self.multi_sequence_index_boundary = ppcm(ppcm_index_list)

                self.loading_multi_seq_number = -1
                self.display()

        if self.mode == Mode.SEQUENCER or self.mode == Mode.ARPEGIATOR or self.mode == Mode.MULTISEQUENCER:
            if self.changing_gate_length == True:
                self.changing_gate_length = False
                self.display()

        if self.change_time_div == True:  # works in any mode
            if self.mode == Mode.MULTISEQUENCER:
                self.multi_sequence_time_div[self.multi_sequence_highlighted] = self.load_time_div
                # Invalidate cache for changed channel
                self._invalidate_multi_cache(self.multi_sequence_highlighted)
                # Update timing cache for the changed channel
                if self._active_channels_list:
                    self._update_channel_timing_cache()
            else:
                self.time_div = self.load_time_div
            self.change_time_div = False
            self.display()

    def star_pressed(self):  # star = cancel
        if self.mode == Mode.BASIC:
            if self.midi_change_channel == True:
                self.midi_change_channel = False
                self.midi_change_channel_channel = 0
                self.display()
        elif self.mode == Mode.SEQUENCER:
            if self.loading_seq == True:  # cancel loading
                self.loading_seq = False
                self.loading_seq_number = 0
                self.display()
        elif self.mode == Mode.ARPEGIATOR:
            pass
        elif self.mode == Mode.MULTISEQUENCER:
            if self.loading_multi_seq == True:
                self.loading_multi_seq = False
                self.loading_multi_seq_number = -1
                self.display()

        if self.mode == Mode.SEQUENCER or self.mode == Mode.ARPEGIATOR:
            if self.changing_gate_length == True:
                self.changing_gate_length = False
                self.display()

        if self.change_time_div == True:  # works in any mode
            self.change_time_div = False
            self.display()

    def clear_seq_hold_pressed(self):
        if self.mode == Mode.BASIC:
            pass
        elif self.mode == Mode.SEQUENCER:
            self.stop_pressed()
            self.seq_len = 0
            self.seq_notes = {}
            self.current_seq_index = 0
            self.seq_notes[LEN_INDEX] = self.seq_len
            self.save_sequence_file(self.seq_number)
            self.display()
        elif self.mode == Mode.ARPEGIATOR:
            self.hold = not self.hold
            if self.hold == False:
                self.arp_len = 0  # reset arpegiator
                self.arp_notes = []
                self.current_arp_index = 0
                self.arp_number_note_pressed = 0
            self.display()

    def load_sequence_file(self, sequence_number, stop=True):
        # stop timer before loading
        to_return_seq_notes = {LEN_INDEX: 0}
        try:
            self.play_note_timer.deinit()
            sequence_file = open("seq_"+str(sequence_number)+".csv", "r")
            output = sequence_file.readline()
            sequence_file.close()
            self.update_timer_frequency()

            to_return_seq_notes = json.loads(output)
            self.seq_len = to_return_seq_notes[LEN_INDEX]

        except Exception as e:
            print("couldn't load sequence n°", sequence_number)
            self.seq_len = 0
            to_return_seq_notes = {LEN_INDEX: 0}
        self.current_seq_index = 0
        if self.seq_len == 0 and stop == True:
            self.stop_pressed()
        return to_return_seq_notes

    def save_sequence_file(self, sequence_number):
        self.play_note_timer.deinit()
        sequence_file = open("seq_"+str(sequence_number)+".csv", "w")
        line = str(self.seq_notes)
        sequence_file.write(line)
        sequence_file.close()
        self.update_timer_frequency()
