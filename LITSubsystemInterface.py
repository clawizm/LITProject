import typing
import threading
import pickle
import socket
from utils import find_missing_numbers_as_ranges_tuples, is_overlap, LEDData
from ObjectDetectionModel import ObjectDetectionModel
import itertools

class LITSubsystemData():
    """A data structure used to store information relevant between the GUI, ObjectDetectionModel used for performing Object Detection on the camera specified, and the potential server the user 
    would like data sent to for addressing the LED subsystems."""
    manual_status: bool = False
    auto_status: bool = False
    manual_led_data_list = []
    turn_off_leds_data_list: list[LEDData] = []
    manual_brightness: float = 0

    def __init__(self, camera_idx: int, object_detection_model: typing.Union[ObjectDetectionModel, None] = None, number_of_leds: int = 256,
                 number_of_sections: int = 8, host: str = None, port: int = None) -> None:
        """
        Parameters:
        - camera_idx (int): The USB ID number for the camera of this Subsystem. This is how the device is identified by the OS.
        - object_detection_model (typing.Union[ObjectDetectionModel, None]): The detection model used to perform inference on the camera_idx.
        - number_of_leds (int): The number of LEDs of the LED Subsystem.
        - number_of_sections (int): When specifying how the lights would like to be sectionalzied when attempting to illuminate an object, this value is used to divide the LED Subsystem
                                    into an equal number of sections equal to number_of_sections. The larger this number the smalled the column illuminated when an object is detected.
        - host (str): The Server IP Address where information will be sent, involving LEDs to Illumuniate.     
        - port (int): The specific port you would like to create your connectiom to the server with. 
        """
        self.camera_idx = camera_idx
        self.object_detection_model = object_detection_model
        self.number_of_leds = number_of_leds
        self.number_of_sections = number_of_sections
        self.host = host
        self.port = port
        self.attempt_to_create_client_conn()

    def attempt_to_create_client_conn(self):
        """Called in the constructor, used to create a connection to the server if provided a host and port. This connection is unique to each instance, as well as the lock creatred when connecting.
        This connection and thread lock is also passed to the object detection model if provide in the constructor. If the server and port are not present, the client_conn and send_lock
        attributes are set to False."""

        if self.host and self.port:
            try:
                self.send_lock = threading.Lock()
                self.client_conn = socket.socket()
                self.client_conn.connect((self.host,self.port))
                if self.object_detection_model:
                    self.object_detection_model.set_client_conn(self.client_conn)
                    self.object_detection_model.set_thread_lock(self.send_lock)
                return
            except:
                pass
        self.client_conn = False
        self.send_lock = False
        return

    def send_data_for_led_addressing(self):
        """Sends data to the respective LED subsystem associated with the instance of this ObjectDetectionModel using a socket connection. This is used to update the state of LEDs throughout the subsystem."""
        all_on_leds = []
        



        data = [, current_led_list_of_dicts, missing_ranges]
        pickle_data = pickle.dumps(data)
        if thread_lock:
            with thread_lock:
                client_conn.send(pickle_data)
        else:
            client_conn.send(pickle_data)        
        return
    

    