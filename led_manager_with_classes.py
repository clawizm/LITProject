import time
import board
import neopixel
import pickle
import typing

class LEDPanels:
    manual_mode_status: bool
    manual_brightness: float
    manual_led_ranges: list[tuple]
    manual_led_with_sliders: tuple 
    
    def __init__(self, board_pin, num_of_leds: int = 800, brightness: float = 1):
        self.board_pixels = neopixel.NeoPixel(board_pin, num_of_leds, brightness=brightness)
        return


    def turn_off_led_ranges(self ,turn_off_tuple_list: list[tuple]):
        for turn_off_range in turn_off_tuple_list:
            if self.manual_mode_status:
                if self.range_is_in_manual_mode_section(turn_off_range):
                    continue
            first_led = turn_off_range[0] 
            last_led = turn_off_range[-1] + 1

            first_led_mid_panel = 512 - last_led 
            last_led_mid_panel = 512 - first_led

            first_led_last_panel = first_led + 511
            last_led_last_panel = last_led + 512

            self.board_pixels[first_led: last_led] = [(0,0,0)] * (last_led-first_led)

            self.board_pixels[first_led_mid_panel: last_led_mid_panel] = [(0,0,0)] * (last_led_mid_panel-first_led_mid_panel)

            self.board_pixels[first_led_last_panel: last_led_last_panel] = [(0,0,0)] * (last_led_last_panel-first_led_last_panel)
        return


    def update_leds(self, objs_detect_stats_list_of_dicts: list[dict]):
        for led_dict in objs_detect_stats_list_of_dicts:
            if not led_dict:
                continue
            if self.manual_mode_status:
                if self.range_is_in_manual_mode_section(led_dict['led_tuple']):
                    continue
            self.update_current_auto_detect_led_tuple_ranges(led_dict)
        return

    def turn_on_manual_range(self, manual_led_tuple: tuple[int, int]):
        if not manual_led_tuple:
            return
        leds_tuple_mid_panel = (512-manual_led_tuple[1], 512-manual_led_tuple[0])
        leds_tuple_top_panel = (manual_led_tuple[0]+512, manual_led_tuple[1]+512)
        
        self.board_pixels[manual_led_tuple[0]:manual_led_tuple[1]] = [(0,0,round(255*self.manual_brightness))] * (manual_led_tuple[1]-manual_led_tuple[0])

        self.board_pixels[leds_tuple_mid_panel[0]:leds_tuple_mid_panel[1]] = [(0,0,round(255*self.manual_brightness))] * (leds_tuple_mid_panel[1]-leds_tuple_mid_panel[0])

        self.board_pixels[leds_tuple_top_panel[0]:leds_tuple_top_panel[1]] = [(0,0,round(255*self.manual_brightness))] * (leds_tuple_top_panel[1]-leds_tuple_top_panel[0])
        return
    
    def update_current_auto_detect_led_tuple_ranges(self, led_dict: dict[float, tuple[int, int]]):
        brightness = float(led_dict['brightness'])
        leds_tuple = led_dict['led_tuple']
        leds_tuple_mid_panel = (512-leds_tuple[1], 512-leds_tuple[0])
        leds_tuple_top_panel = (leds_tuple[0]+512, leds_tuple[1]+512)
        
        self.board_pixels[leds_tuple[0]:leds_tuple[1]] = [(0,0,round(255*brightness))] * (leds_tuple[1]-leds_tuple[0])

        self.board_pixels[leds_tuple_mid_panel[0]:leds_tuple_mid_panel[1]] = [(0,0,round(255*brightness))] * (leds_tuple_mid_panel[1]-leds_tuple_mid_panel[0])

        self.board_pixels[leds_tuple_top_panel[0]:leds_tuple_top_panel[1]] = [(0,0,round(255*brightness))] * (leds_tuple_top_panel[1]-leds_tuple_top_panel[0])
        return
    
    def manual_brightness_adjust_of_manual_ranges(self):
        if self.manual_led_ranges:
            for led_tuple in self.manual_led_ranges:
                self.turn_on_manual_range(led_tuple)

        elif self.manual_led_with_sliders:
            self.turn_on_manual_range(self.manual_led_with_sliders)
        return

    def update_leds_from_data_packets(self, data: list[any]):
        try:
            detect_obj = pickle.loads(data)
        except:
            pass
        try:
            if detect_obj[0] == 'auto':
                if detect_obj[1]:
                    self.update_leds(detect_obj[0])
                if detect_obj[2]:
                    self.turn_off_led_ranges(detect_obj[1])
            else:
                self.handle_manual_mode_event(detect_obj)
        except:
            pass

    def range_is_in_manual_mode_section(self, turn_off_range: tuple[int, int])->bool:
        if self.manual_led_ranges and self.manual_led_with_sliders:
            if any(is_overlap(turn_off_range, led_range) for led_range in self.manual_led_ranges) or is_overlap(turn_off_range, self.manual_led_with_sliders):
                return True
            return False
        elif self.manual_led_ranges:
            if any(is_overlap(turn_off_range, led_range) for led_range in self.manual_led_ranges):
                return True
            return False
        elif self.manual_led_with_sliders:
            if is_overlap(turn_off_range, self.manual_led_with_sliders):
                return True
            return False
        return False
    
    def handle_manual_mode_event(self, detect_obj: list[str, str, typing.Union[tuple, float]]):
        if detect_obj[1] == 'MANUAL_STAUS':
            self.manual_mode_status = detect_obj[2]
        elif detect_obj[1] == 'LED_RANGE_APPEND':
            self.manual_led_ranges.append(detect_obj[2])
            self.turn_on_manual_range(detect_obj[2])
        elif detect_obj[1] == 'LED_RANGE_REMOVE':
            self.manual_led_ranges.remove(detect_obj[2])
            #this may need a turn off manual range function that turns off the LEDS immedadlity 
            # self.turn_off_manual_range(detect_obj[2])
        elif detect_obj[1] == 'BRIGHTNESS':
            self.manual_brightness = detect_obj[2]
            self.manual_brightness_adjust_of_manual_ranges()
        elif detect_obj[1] == 'LED_SLIDER_RANGE':
            #verify data is in a proper tuple
            self.manual_led_with_sliders = detect_obj[2]
            if self.manual_led_with_sliders:
                self.turn_on_manual_range(detect_obj[2])
        
    
def is_overlap(range1, range2):
    """Check if range1 overlaps with range2."""
    return range1[0] <= range2[1] and range1[1] >= range2[0]