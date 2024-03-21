import typing
import itertools

class ManualLEDData:
    manual_led_tuple_list: list[tuple[int, int]] = []
    slider_led_tuple: tuple[int, int] = None
    full_manual_list: list[tuple[int, int]]
    def __init__(self, brightness: float = 0.00):
        self.brightness = brightness
        return
    
    def add_led_range(self, led_range: tuple[int, int]):
        self.manual_led_tuple_list.append(led_range)
        return
        
    def remove_led_range(self, led_range: tuple[int, int]):
        self.manual_led_tuple_list.remove(led_range)
        return
    
    def set_slider_led_range(self, led_range: tuple[int, int]):
        self.slider_led_tuple = led_range
        return
    
    def generate_full_manual_led_list(self)->list[tuple[int, int]]:
        if self.slider_led_tuple:
            return list(itertools.chain.from_iterable([self.manual_led_tuple_list, [self.slider_led_tuple]]))
        return self.manual_led_tuple_list

class AutoLEDData:
    def __init__(self, led_range: tuple[int, int], brightness: float):
        self.led_range = led_range
        self.brightness = brightness    
    
    
class SystemLEDData:
    turn_off_leds: ManualLEDData = ManualLEDData()
    def __init__(self, manual_led_data: typing.Union[ManualLEDData, None], auto_led_data_list: typing.Union[list[AutoLEDData], None]):
        if manual_led_data:
            self.manual_led_data = manual_led_data
        else:
            self.manual_led_data = ManualLEDData()
        if auto_led_data_list:
            self.auto_led_data_list = auto_led_data_list    
        else:
            self.auto_led_data_list = []
        return
    
    def update_led_data_for_sending(self, auto_status: bool, manual_status: bool):
        if auto_status and manual_status:
            self.full_manual_list = self.manual_led_data.generate_full_manual_led_list()
            # full_led_list = list(itertools.chain.from_iterable([full_manual_list, [auto_led.led_range for auto_led in self.auto_led_data_list]]))
            missing_leds = find_missing_numbers_as_ranges_tuples(self.full_manual_list)
            self.turn_off_leds.manual_led_tuple_list = missing_leds
            self.auto_led_data_list = remove_overlapping_ranges_between_auto_led_and_manual_leds(missing_leds, self.auto_led_data_list)
        elif manual_status:
            self.full_manual_list = self.manual_led_data.generate_full_manual_led_list()
            missing_leds = find_missing_numbers_as_ranges_tuples(self.full_manual_list)
            self.turn_off_leds.manual_led_tuple_list = missing_leds
        else:
            full_auto_list = [auto_led.led_range for auto_led in self.auto_led_data_list]
            missing_leds = find_missing_numbers_as_ranges_tuples(full_auto_list)
            self.turn_off_leds.manual_led_tuple_list = missing_leds
        return
    


def is_overlap(range1, range2):
    """Check if range1 overlaps with range2."""
    if (range1[0] < range2[1]) and (range1[1] > range2[0]):
        return True
    return False

def find_missing_numbers_as_ranges_tuples(ranges) -> list[tuple]:
    # Initialize a set with all numbers from 0 to 256
    all_numbers = set(range(257))
    
    # Remove the numbers present in the given ranges
    for start, end in ranges:
        all_numbers -= set(range(start, end + 1))
    
    # Convert the set to a sorted list
    missing_numbers_sorted = sorted(list(all_numbers))
    
    # Group the consecutive numbers into ranges
    missing_ranges = []
    if missing_numbers_sorted:
        # Initialize the first range with the first missing number
        range_start = missing_numbers_sorted[0]
        range_end = missing_numbers_sorted[0]
        
        for number in missing_numbers_sorted[1:]:
            if number == range_end + 1:
                # Extend the current range
                range_end = number
            else:
                # Finish the current range and start a new one
                missing_ranges.append((range_start, range_end))
                range_start = number
                range_end = number
        
        # Add the last range
        missing_ranges.append((range_start, range_end))
    
    return missing_ranges
    
def remove_overlapping_ranges_between_auto_led_and_manual_leds(manual_led_tuple_list: list[tuple[int, int]], auto_led_data_list: list[AutoLEDData]):
    if not auto_led_data_list or not manual_led_tuple_list:
        return None
    # auto_leds_to_remove = []
    for led_range in manual_led_tuple_list:
        for auto_led in auto_led_data_list:
            if is_overlap(auto_led.led_range, led_range):
                auto_led.led_range = adjust_overlap(auto_led.led_range, led_range)
    


    # # Remove the ranges marked for removal
    # for led in set(auto_leds_to_remove):
    #     auto_led_data_list.remove(led)
    return auto_led_data_list

def adjust_overlap(range1, range2):
    """
    Adjusts range1 to ensure there's no overlap with range2.
    :param range1: First range tuple.
    :param range2: Second range tuple.
    :return: Adjusted range1 tuple.
    """
    start1, end1 = range1
    start2, end2 = range2

    # Check if range1 completely overlaps range2 or vice versa
    if start1 >= start2 and end1 <= end2:
        return (start1, start1)  # Or any logic to handle complete overlap
    elif start2 >= start1 and end2 <= end1:
        return (start1, end2)  # Split range1 around range2

    # Partial overlap cases
    if start1 < start2 < end1 <= end2:
        return (start1, start2)  # Adjust end of range1 to start of range2
    elif start2 <= start1 < end2 < end1:
        return (end2, end1)  # Adjust start of range1 to end of range2

    # No overlap
    return range1

###WHAT IF I GOT MISSING REGIONS OF MANUAL REGION, AND THAT BECOMES ONLY REGIONS AUTO DATA CAN POPULATE. IT COULD BE AN ATTRIBUTE STORED AND ONLY CHANGED ON THE UPDATE OF MANUAL DATA.


if __name__ == '__main__':
    manual_led_data = ManualLEDData()
    manual_led_data.add_led_range((0, 32))
    manual_led_data.add_led_range((32, 64))
    manual_led_data.add_led_range((224, 256))
    manual_led_data.set_slider_led_range((70, 255))
    auto_led_data_one = AutoLEDData((64, 96), .56)
    auto_led_data_two = AutoLEDData((0, 32), .51)
    auto_led_list = [auto_led_data_one, auto_led_data_two]
    system_led_data = SystemLEDData(manual_led_data, auto_led_list)
    print(f'System Led Data is: {[print(auto_led.led_range, auto_led.brightness) for auto_led in system_led_data.auto_led_data_list]}\n')
    system_led_data.update_led_data_for_sending(auto_status=True, manual_status=True)
    print(f"Updated LED Data is:")
    [print(auto_led.led_range, auto_led.brightness) for auto_led in system_led_data.auto_led_data_list if isinstance(auto_led, AutoLEDData)]
    print(f"System Manual Data is: {manual_led_data.manual_led_tuple_list}")








