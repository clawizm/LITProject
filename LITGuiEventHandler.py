import PySimpleGUI as sg
import cv2
import numpy as np
import typing
import ObjectDetectionModel
from ObjectDetectionModel import ObjectDetectionModel
import threading
import time
import socket
import pickle


class LITGuiEventHandler:
    """A class handing events with the LITGUI class. The seperation of two allows for this class to be overwritten or manually implemented by other developers to handle their own events in the
    GUI.
    
    Attributes:
    - window (sg.Window): The window attribute of the LITGUI instance. 
    
    - led_tuples_dict_of_list (dict[list[tuple[int, int]]]): A dictionary where the key is the camera_idx of the current Subsystem being referenced, such as 'CAMERA_0'. The values stores
    are a list of tuples containing two integers, where the integers are the start and stop values of ranges of the LEDSubsystem. These ranges are unqiue to each checkbox in the 'Manually Control LED Ranges Section'.
    
    - object_detection_model_dict (dict[str, typing.Union[ObjectDetectionModel, None]]): A dictonary where each key is a camera plus its index, such as 'CAMERA_0'.
    Each Camera in the GUI has the option of being part of a subsystem, bus is not required. 
    This dict will store each Camera passed to the GUI, and store whether that camera is used for performing Object Detection or is just used to view video from a webcam.

    - lit_subsystem_conn_dict (dict[str, typing.Union[socket.socket, bool]]): A dictonary where each key is a camera plus its index, such as 'CAMERA_0'. If the camera is part of a subsystem which 
    is sending data over a socket connection for address LED in the Subsystem, then the value stored will be an instance of a socket connection, but if there is no connection the value will be False.

    - lit_subystem_thread_lock_dict (dict[str, typing.Union[threading.Lock, bool]]): A dictonary where each key is a camera plus its index, such as 'CAMERA_0'. If there is a server connection for this
    camera subsystem, we use an instance of the threading.Lock class for sending data, so that each unqiue connection for cameras in the GUI have the ability to send data autonomously through their respective
    object detection models, and manually through user input in the GUI. This prevents any race conditions from occuring when sending data.
    """

    window: sg.Window
    led_tuples_dict_of_list: dict[list[tuple[int, int]]]
    object_detection_model_dict: dict[str, ObjectDetectionModel]
    lit_subystem_conn_dict: dict[str, socket.socket] = {}
    lit_subystem_thread_lock_dict: dict[str, threading.Lock] = {}

    def set_camera_of_event(self):
        """Used to find the camera index for the panel in which the event spawned from. This value is used to apply the setting changed to the correct Subsystem.
        Value is set to the event_camera Attribute."""
        self.event_camera = self.event.split('_')[1]
        return 

    def on_autonomous_mode_event(self):
        """Handles an event in which the user has pressed the _AUTONOMOUSMODE checkbox in one of the Subsystems displayed on the GUI. This will either stop or start detection in the current subsystem based on the 
        value of the checkbox. It will also alter the status of the show feed checkbox."""
        if self.lit_subystem_conn_dict[f'CAMERA_{self.event_camera}']:
            self.send_auto_status_data_with_lock(self.values[f'-CAMERA_{self.event_camera}_AUTONOMOUSMODE-'], self.lit_subystem_conn_dict[f'CAMERA_{self.event_camera}'], self.lit_subystem_thread_lock_dict[f'CAMERA_{self.event_camera}'])

        if self.values[f'-CAMERA_{self.event_camera}_AUTONOMOUSMODE-']:            
            if self.object_detection_model_dict[f'CAMERA_{self.event_camera}']:
                self.object_detection_model_dict[f'CAMERA_{self.event_camera}'].start_detection()
            self.window[f'-CAMERA_{self.event_camera}_SHOWFEED-'].update(True, disabled=False)
        else:
            if self.object_detection_model_dict[f'CAMERA_{self.event_camera}']:
                self.object_detection_model_dict[f'CAMERA_{self.event_camera}'].stop_detection()
            self.window[f'-CAMERA_{self.event_camera}_FEED-'].update(filename=r'Jason.png', size=(720, 480))
            self.window[f'-CAMERA_{self.event_camera}_SHOWFEED-'].update(False, disabled=True)
        return
    
    def on_show_camera_feed_event(self):
        """Handes an event in which the user has pressed the SHOWFEED checkbox in one of the Subsystems displayed on the GUI. Depending on the state of the checkbox, the videostream from the camera will either
        be passed to the GUI, or will no longer displayed. By disabling feed the performance of the System increases."""

        if self.values[f'-CAMERA_{self.event_camera}_SHOWFEED-'] and self.object_detection_model_dict[f'CAMERA_{self.event_camera}']:
            self.object_detection_model_dict[f'CAMERA_{self.event_camera}'].set_window(self.window)
        else:
            self.object_detection_model_dict[f'CAMERA_{self.event_camera}'].set_window(None)
            time.sleep(2)
            self.window[f'-CAMERA_{self.event_camera}_FEED-'].update(filename=r'Lebron.png', size=(720, 480))
        return
    
    def on_manual_control_event(self):
        """Handles an event in which the user has altered the state of one of the MANUALSTATUS checkboxes displayed on the GUI inside one of the Subsystem Frames. If there is a connection to a server, this event will send 
        relevant manual control data to the server and update LEDs accordingly."""

        manual_status = self.values[f'-CAMERA_{self.event_camera}_MANUALSTATUS-']
        if manual_status:
            self.enable_all_manual_options_of_subsystem()
        else:
            self.disable_all_manual_options_of_subsystem()

        if self.lit_subystem_conn_dict[f'CAMERA_{self.event_camera}']:
            client_conn = self.lit_subystem_conn_dict[f'CAMERA_{self.event_camera}']
            thread_lock = self.lit_subystem_thread_lock_dict[f'CAMERA_{self.event_camera}']
            self.send_manual_status_data_with_lock(manual_status, client_conn, thread_lock)
        return
    
    def on_manually_control_led_range_event(self):  
        """Handles an event in which the user has altered the state of one of the LED range checkboxes displayed on the GUI inside one of the Subsystem Frames. If there is a connection to a server, this event will
        update the state of the LED range selected by the user in the physical LED Subsystem."""  
        if self.lit_subystem_conn_dict[f'CAMERA_{self.event_camera}']:
            led_range = self.get_led_range_from_event()
            status = self.get_value_of_element_from_event()        
            client_conn = self.lit_subystem_conn_dict[f'CAMERA_{self.event_camera}']
            thread_lock = self.lit_subystem_thread_lock_dict[f'CAMERA_{self.event_camera}']
            self.send_manual_led_range_data_with_lock(led_range, status, client_conn, thread_lock)
        return 

    def on_manually_control_led_range_slider_event(self):
        """Handles an event in which the user has altered the value of a led range slider in one of the LED range sliders displayed on the GUI inside of the Subsystem Frames. If there is a connection to a server,
        this event will update the state of the LED slider range specified by the user in the physical LED Subsystem."""
        if self.lit_subystem_conn_dict[f'CAMERA_{self.event_camera}']:
            if self.values[f'-CAMERA_{self.event_camera}_SLIDER_LEFT_TO_RIGHT-']:
                led_range = (0, round(self.values[f'-CAMERA_{self.event_camera}_LEDSLIDER-']))
            elif self.values[f'-CAMERA_{self.event_camera}_SLIDER_RIGHT_TO_LEFT-']:
                led_range = (round(self.values[f'-CAMERA_{self.event_camera}_LEDSLIDER-']), 255)
            else:
                led_range = False
            if led_range == (0, 0):
                led_range = False
            client_conn = self.lit_subystem_conn_dict[f'CAMERA_{self.event_camera}']
            thread_lock = self.lit_subystem_thread_lock_dict[f'CAMERA_{self.event_camera}']
            self.send_manual_led_slider_data_with_lock(led_range, client_conn, thread_lock)

    def on_manually_control_led_brightness_slider_event(self):
        """Handles an event in which the user has altered the value of a led brightness slider in one of the LED brightness sliders displayed on the GUI inside of the Subsystem Frames. 
        If there is a connection to a server, this event will update the state of the LED slider brightness specified by the user in the physical LED Subsystem."""
        if self.lit_subystem_conn_dict[f'CAMERA_{self.event_camera}']:
            brightness = self.values[f'-CAMERA_{self.event_camera}_BRIGHTNESSSLIDER-']
            client_conn = self.lit_subystem_conn_dict[f'CAMERA_{self.event_camera}']
            thread_lock = self.lit_subystem_thread_lock_dict[f'CAMERA_{self.event_camera}']
            self.send_manual_led_brighntess_data_with_lock(brightness, client_conn, thread_lock)

            
    def disable_all_manual_options_of_subsystem(self):
        """Disable all manual options of the subsystem panel where this event originated."""
        self.disable_all_led_range_checkboxs()
        self.disable_adjust_leds_left_to_right()
        self.disable_adjust_brightness_of_leds()
        self.disable_left_to_right_checkbox()
        self.disable_right_to_left_checkbox()
        return

    def enable_all_manual_options_of_subsystem(self):
        """Enables all manual options of the subsystem panel where this event originated."""
        self.enable_all_led_range_checkboxs()
        self.enable_adjust_leds_left_to_right()
        self.enable_adjust_brightness_of_leds()
        self.enable_left_to_right_checkbox()
        self.enable_right_to_left_checkbox()
        return
    
    
    def enable_all_led_range_checkboxs(self):
        """Iterates over all of the LED Range checkboxes in a panel and enables them for user interaction."""
        for led_tuple in self.led_tuples_dict_of_list[f'CAMERA_{self.event_camera}']:
            self.window[f'-CAMERA_{self.event_camera}_LEDRANGE_{led_tuple[0]}_{led_tuple[1]}-'].update(disabled=False)
        return
    
    def enable_adjust_leds_left_to_right(self):
        """Enables the led slider of the current panel where this event orginiated."""
        self.window[f'-CAMERA_{self.event_camera}_LEDSLIDER-'].update(disabled=False)
        return

    def enable_adjust_brightness_of_leds(self):
        """Enables the led brightness slider of the current panel where this event orginiated."""
        self.window[f'-CAMERA_{self.event_camera}_BRIGHTNESSSLIDER-'].update(disabled=False)
        return
    
    def enable_right_to_left_checkbox(self):
        """Enables the checkbox for using the led slider in left to right mode. This change is applied to the current panel where this event orginiated."""
        self.window[f'-CAMERA_{self.event_camera}_SLIDER_LEFT_TO_RIGHT-'].update(disabled=False)
        return
    
    def enable_left_to_right_checkbox(self):
        """Enables the checkbox for using the led slider in right to left mode. This change is applied to the current panel where this event orginiated."""
        self.window[f'-CAMERA_{self.event_camera}_SLIDER_RIGHT_TO_LEFT-'].update(disabled=False)
        return
    
    def disable_all_led_range_checkboxs(self):
        """Iterates over all of the LED Range checkboxes in a panel and enables them for user interaction."""
        for led_range in self.led_tuples_dict_of_list[f'CAMERA_{self.event_camera}']:
            self.window[f'-CAMERA_{self.event_camera}_LEDRANGE_{led_range[0]}_{led_range[1]}-'].update(disabled=True)
        return
    
    def disable_adjust_leds_left_to_right(self):
        """Disables the led slider of the current panel where this event orginiated."""
        self.window[f'-CAMERA_{self.event_camera}_LEDSLIDER-'].update(disabled=True)
        return

    def disable_adjust_brightness_of_leds(self):
        """Disables the led brightness slider of the current panel where this event orginiated."""
        self.window[f'-CAMERA_{self.event_camera}_BRIGHTNESSSLIDER-'].update(disabled=True)
        return
    
    def disable_right_to_left_checkbox(self):
        """Enables the checkbox for using the led slider in right to left mode. This change is applied to the current panel where this event orginiated."""
        self.window[f'-CAMERA_{self.event_camera}_SLIDER_RIGHT_TO_LEFT-'].update(disabled=True)
        return
    
    def disable_left_to_right_checkbox(self):
        """Enables the checkbox for using the led slider in left to right mode. This change is applied to the current panel where this event orginiated."""
        self.window[f'-CAMERA_{self.event_camera}_SLIDER_LEFT_TO_RIGHT-'].update(disabled=True)
        return
    
    def turn_right_to_left_status_to_false(self):
        """Sets the status of the checkbox for using the led slider in right to left mode to False. This change is applied to the current panel where this event orginiated."""
        self.window[f'-CAMERA_{self.event_camera}_SLIDER_RIGHT_TO_LEFT-'].update(False)
        return

    def turn_left_to_right_status_to_false(self):
        """Sets the status of the checkbox for using the led slider in left to right mode to False. This change is applied to the current panel where this event orginiated."""
        self.window[f'-CAMERA_{self.event_camera}_SLIDER_LEFT_TO_RIGHT-'].update(False)
        return

    def get_led_range_from_event(self)->tuple:
        """Returns the tuple of ints from a checkbox event in the Adjust LED range subframe. Used to parse the str displayed to the user and only return the int values."""
        return tuple(int(x) for x in self.event.replace('-','').split('_')[3:])

    def get_value_of_element_from_event(self)->bool:
        """Returns the value of the element where an event spawns."""
        return self.values[self.event]
        
    def send_manual_led_range_data_with_lock(self, led_range: tuple[int, int], checkbox_status: bool, client_conn: socket.socket, send_lock: threading.Lock)->None:
        """Sends data over a socket connection relevant to the update of the status of an LED Range checkbox. Sends a list where the first index is a string 'MANUAL' used to specify this was a manual update of LEDs, LED_RANGE_APPEND or LED_RANGE_REMOVE, where these strings 
        correspond to True and False respectively, and finally the tuple containing the two integers releveant to the LED Range updated.
        
        Parameters:
        - led_range (tuple[int, int]): The LED range values sent over a server to update LED status. index 0 should always be smaller than index 1.
        - checkbox_status (bool): The status the checkbox corresponding to the LED range to be updated. This status corresponds directly to if the user would like to turn LEDs on or off.
        - client_conn (socket.socket): The socket connection used to pass data.
        - send_lock (threading.Lock): A thread lock that should be shared by all threads that are used to send data over the instance of the client_conn passed to this method."""

        if checkbox_status:
            data = ['MANUAL', 'LED_RANGE_APPEND', led_range]
        else:
            data = ['MANUAL', 'LED_RANGE_REMOVE', led_range]

        pickle_data = pickle.dumps(data)
        if send_lock:
            with send_lock:
                client_conn.send(pickle_data)
        else:
            client_conn.send(pickle_data)        
        return

    def send_manual_led_slider_data_with_lock(self, led_range: tuple[int, int], client_conn: socket.socket, send_lock: threading.Lock)->None:
        """Sends data over a socket connection relevant to the update of the status of the LED slider range in a panel. Sends a list where the first index is a string 'MANUAL' used to specify this was a manual update of LEDs, LED_SLIDER_RANGE used to specify this update
        is spawned from a LED slider event, and finally the tuple containing the two integers relevant to the LED range updated.
        
        Parameters:
        - led_range (tuple[int, int]): The LED range values sent over a server to update LED status. index 0 should always be smaller than index 1.
        - client_conn (socket.socket): The socket connection used to pass data.
        - send_lock (threading.Lock): A thread lock that should be shared by all threads that are used to send data over the instance of the client_conn passed to this method."""

        data = ['MANUAL', 'LED_SLIDER_RANGE', led_range]
        pickle_data = pickle.dumps(data)
        if send_lock:
            with send_lock:
                client_conn.send(pickle_data)
        else:
            client_conn.send(pickle_data)        
        return
    
    def send_manual_led_brighntess_data_with_lock(self, brightness: float, client_conn: socket.socket, send_lock: threading.Lock)->None:
        """Sends data over a socket connection relevant to the update of the status of the manually controlled LEDs brightness in a panel. Sends a list where the first index is a string 'MANUAL' used to specify this was a manual update of LEDs, 
        BRIGHTNESS used to specify this update is spawned from a brightness slider event, and finally the float value of the brightness specified.
        
        Parameters:
        - brightness (float): The brightness to set manually control LEDs to.
        - client_conn (socket.socket): The socket connection used to pass data.
        - send_lock (threading.Lock): A thread lock that should be shared by all threads that are used to send data over the instance of the client_conn passed to this method."""

        data = ['MANUAL', 'BRIGHTNESS', brightness]
        pickle_data = pickle.dumps(data)
        if send_lock:
            with send_lock:
                client_conn.send(pickle_data)
        else:
            client_conn.send(pickle_data)        
        return

    def send_manual_status_data_with_lock(self, manual_status: bool, client_conn: socket.socket, send_lock: threading.Lock)->None:
        """Sends data over a socket connection relevant to the update of the status of the manually controlled LEDs in a panel. Sends a list where the first index is a string 'MANUAL' used to specify this was a manual update of LEDs, 
        MANUAL_STATUS used to specify this update is spawned from a manual status update event, and finally the boolean value of the manual status specified.
        
        Parameters:
        - manual_status (bool): Enable or Disable Manual Control of LEDs.
        - client_conn (socket.socket): The socket connection used to pass data.
        - send_lock (threading.Lock): A thread lock that should be shared by all threads that are used to send data over the instance of the client_conn passed to this method."""

        data = ['MANUAL', 'MANUAL_STAUS', manual_status]
        pickle_data = pickle.dumps(data)
        if send_lock:
            with send_lock:
                client_conn.send(pickle_data)
        else:
            client_conn.send(pickle_data)        
        return        
    
    def send_auto_status_data_with_lock(self, auto_status: bool, client_conn: socket.socket, send_lock: threading.Lock)->None:
        """Sends data over a socket connection relevant to the update of the status of the manually controlled LEDs in a panel. Sends a list where the first index is a string 'UPDATE_AUTO_STATUS' used to specify this the starting or stoping of Auto Object Detection, 
        and the boolean value of the auto status specified.
        
        Parameters:
        - auto_status (bool): Enable or Disable Manual Control of LEDs.
        - client_conn (socket.socket): The socket connection used to pass data.
        - send_lock (threading.Lock): A thread lock that should be shared by all threads that are used to send data over the instance of the client_conn passed to this method."""

        data = ['UPDATE_AUTO_STATUS', auto_status]
        pickle_data = pickle.dumps(data)
        if send_lock:
            with send_lock:
                client_conn.send(pickle_data)
        else:
            client_conn.send(pickle_data)        
        return        
    
    def start_event_loop(self):
        """Creates a loop that runs endlessly while the GUI is running, handles all events the occur in the GUI."""
        while True:             
            self.event, self.values = self.window.Read()
            if self.event is None:
                break
            self.set_camera_of_event()
            if 'SHOWFEED' in self.event:
                self.on_show_camera_feed_event()
            elif 'MANUALSTATUS' in self.event:
                self.on_manual_control_event()
            elif 'AUTONOMOUSMODE' in self.event:
                self.on_autonomous_mode_event()
            elif '_LEDRANGE_' in self.event:
                self.on_manually_control_led_range_event()
            elif '_LEDSLIDER-' in self.event:
                self.on_manually_control_led_range_slider_event()
            elif '_SLIDER_LEFT_TO_RIGHT' in self.event:
                self.turn_right_to_left_status_to_false()
                self.on_manually_control_led_range_slider_event()
            elif '_SLIDER_RIGHT_TO_LEFT' in self.event:
                self.turn_left_to_right_status_to_false()
                self.on_manually_control_led_range_slider_event()
            elif '_BRIGHTNESSSLIDER' in self.event:
                self.on_manually_control_led_brightness_slider_event()
        return
    
