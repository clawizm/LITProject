import time
import board
import neopixel
import pickle
import typing
import utils

class LEDPanels:
    """Used to interface with an LED system. Allows for cascading of NeoPixel Panels of the same size, where sections of the LEDs can be directly altered with APIs."""



    def __init__(self, board_pin: board, num_of_leds: int = 800, brightness: float = 1):
        """Using a board pin, this initializes the current class and an instance of the NeoPixel class."""
        self.board_pixels = neopixel.NeoPixel(board_pin, num_of_leds, brightness=brightness)
        return


    def auto_turn_off_led_ranges(self, turn_off_tuple_list: list[tuple]):
        """Turn off all ranges in the provided turn_off_tuple_list, this will ignore leds that are currently set to be turned on manually if the manual mode is enabled.
        This will update the LEDs in the same column amongst all of the panels.
        
        Parameters:
        - turn_off_tuple_list (list[tuple]): A list of tuples containing the start and stop values of the range of LEDs to turn off."""

        if isinstance(turn_off_tuple_list, tuple):
            turn_off_tuple_list = [turn_off_tuple_list]
        
        for turn_off_range in turn_off_tuple_list:
            first_led = turn_off_range[0] 
            last_led = turn_off_range[-1] 

            first_led_mid_panel = 512 - last_led 
            last_led_mid_panel = 512 - first_led

            first_led_last_panel = first_led + 511
            last_led_last_panel = last_led + 512

            self.board_pixels[first_led: last_led] = [(0,0,0)] * (last_led-first_led)

            self.board_pixels[first_led_mid_panel: last_led_mid_panel] = [(0,0,0)] * (last_led_mid_panel-first_led_mid_panel)

            self.board_pixels[first_led_last_panel: last_led_last_panel] = [(0,0,0)] * (last_led_last_panel-first_led_last_panel)
        return
    
    def turn_on_leds(self, leds_tuple: typing.Union[tuple[int, int], None], brightness: float)->None:
        if not leds_tuple:
            return
        leds_tuple_mid_panel = (512-leds_tuple[1], 512-leds_tuple[0])
        leds_tuple_top_panel = (leds_tuple[0]+512, leds_tuple[1]+512)
        
        self.board_pixels[leds_tuple[0]:leds_tuple[1]] = [(0,0,round(255*brightness))] * (leds_tuple[1]-leds_tuple[0])

        self.board_pixels[leds_tuple_mid_panel[0]:leds_tuple_mid_panel[1]] = [(0,0,round(255*brightness))] * (leds_tuple_mid_panel[1]-leds_tuple_mid_panel[0])

        self.board_pixels[leds_tuple_top_panel[0]:leds_tuple_top_panel[1]] = [(0,0,round(255*brightness))] * (leds_tuple_top_panel[1]-leds_tuple_top_panel[0])

        return

    def update_leds_from_data_packets(self, data: list):
        """Used to update LEDs from a server connection, first the data is assumed to be pickled and therefore must be unpickled. This handles packets received from the ObjectDetectionModel or the LITGui Modules.
        
        Parameters:
        - data: UPDATE"""

        try:
            loaded_data = pickle.loads(data)
        except:
            loaded_data = data
        if loaded_data[0] == 0:
            for led_range in loaded_data[1]:
                self.turn_on_leds(led_range, loaded_data[2])
            self.auto_turn_off_led_ranges(loaded_data[3])
        ####THIS MAY NEED ERROR HANDLING FOR AUTO DATA
        elif loaded_data[0] == 1:
            for led_tuple in loaded_data[1]:
                self.turn_on_leds(led_tuple[0], led_tuple[1])
            self.auto_turn_off_led_ranges(loaded_data[2])
        return


