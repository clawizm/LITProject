#I need to add a detailed description of this file for sharing with the world aka GitHub
import PySimpleGUI as sg
import typing
from LITGuiEventHandler import LITGuiEventHandler
import ObjectDetectionModel
from ObjectDetectionModel import ObjectDetectionModel
import threading
import socket
# used to prevent popup froms occur while debugging and poential errors that are inevitable but caught with try and excepts from also creating annoying popups
sg.set_options(suppress_raise_key_errors=True, suppress_error_popups=True, suppress_key_guessing=True)


class LITSubsystemData():
    """A data structure used to store information relevant between the GUI, ObjectDetectionModel used for performing Object Detection on the camera specified, and the potential server the user 
    would like data sent to for addressing the LED subsystems."""

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

class LITGUI(LITGuiEventHandler):
    """Abstract GUI Class used to create a GUI that displays live camera feed for N number of cameras, with each camera camera in the GUI having its own section to turn off and on
    Object Detection, if the user provides a ObjectDetectionModel for each Subsystem passed. Allows for the manual control of LED subsystems associated with each Subsystem represented by their 
    unique cameras. Can be scalled to as many Cameras and Subsystems the user would like to run.
    
    Attributes:
    
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

    led_tuples_dict_of_list: dict[str, list[tuple[int, int]]] = {}
    object_detection_model_dict: dict[str, typing.Union[ObjectDetectionModel, None]] = {}
    lit_subystem_conn_dict: dict[str, typing.Union[socket.socket, bool]] = {}
    lit_subystem_thread_lock_dict: dict[str, typing.Union[threading.Lock, bool]] = {}

    def __init__(self, lit_subsystem_data: typing.Union[LITSubsystemData, list[LITSubsystemData]]):
        """Creates a GUI displaying Camera Feeds for each LITSubsystemData instance passed.
        
        Parameters:
        - lit_subsystem_data (typing.Union[LITSubsystemData, list[LITSubsystemData]]): Will create a seperate section in the GUI for each subsystem passed, whether in a list of Length N, or 
        if a single instance of LITSubsystemData is passed."""

        if isinstance(lit_subsystem_data, LITSubsystemData):
            final_layout = self.create_gui_from_camera_instance(lit_subsystem_data)
            self.window = sg.Window('Test', final_layout)

        elif isinstance(lit_subsystem_data, list):
            final_layout = self.create_gui_from_cameras_list(lit_subsystem_data)
            self.window = sg.Window('Test', final_layout)
        
        self.set_lit_subsystems_windows(lit_subsystem_data)
        return

    def set_lit_subsystems_windows(self, lit_subsystem_data: typing.Union[LITSubsystemData, list[LITSubsystemData], None, list[None]]):
        """Sets the window where each object detection model will pass data to, which will be the window created by an instance of this class.
        
        - lit_subsystem_data (typing.Union[LITSubsystemData, list[LITSubsystemData], None, list[None]]): An instance of the LITSubsystemData class, or a list containing either all LITSubsystemData 
        instances, or some LITSubsystemData instances and some Nonetype instances."""

        if isinstance(lit_subsystem_data, LITSubsystemData):
            lit_subsystem_data.object_detection_model.set_window(self.window)
        elif isinstance(lit_subsystem_data, list):
            for subsystem in lit_subsystem_data:
                if isinstance(subsystem.object_detection_model, ObjectDetectionModel):
                    subsystem.object_detection_model.set_window(self.window)
        return
    
    def create_led_tuple_range_list(self)->list[tuple[int, int]]:
        """Returns a list of tuples containing the start and stopping point of LED ranges based on the number of LEDs of the subsystem specified divided by the number of sections the user would 
        like the subsystem divided into."""

        led_tuples_list = []
        leds_ranges = round(self.number_of_leds/self.num_of_sections)
        i = 0
        while i < self.number_of_leds:
            led_tuples_list.append((i, i+leds_ranges))
            i += leds_ranges
        return led_tuples_list
    

    def add_object_detection_model_to_gui(self, object_detection_model: typing.Union[ObjectDetectionModel, None]):
        """Sets the image window where video feed will be passed from the object detection model to the GUI window. Also adds the key value pair of the camera_idx and the object model instance to the 
        object detection model dictionary
        
        Parameters:
        - object_detection_model (typing.Union[ObjectDetectionModel, None]): an instance of the ObjectDetectionModel, or a NoneType instance.
        """
        if isinstance(object_detection_model, ObjectDetectionModel):
            object_detection_model.set_image_window(f'-CAMERA_{self.camera_idx}_FEED-')
        self.object_detection_model_dict[f'CAMERA_{self.camera_idx}'] = object_detection_model
        return

    def create_camera_frame(self, lit_subsystem_data: LITSubsystemData):
        """Creates a frame for a LITSubsystemData instance passed. This Frame contains all of the User Interface relevant to the provided LITSubsystem.
        
        Parameters:
        - lit_subsystem_data (LITSubsystemData): An instance of the LITSubsystemData class."""

        self.camera_idx = lit_subsystem_data.camera_idx
        self.number_of_leds = lit_subsystem_data.number_of_leds
        self.num_of_sections = lit_subsystem_data.number_of_sections
        self.lit_subystem_conn_dict[f'CAMERA_{self.camera_idx}'] = lit_subsystem_data.client_conn
        self.lit_subystem_thread_lock_dict[f'CAMERA_{self.camera_idx}'] = lit_subsystem_data.send_lock
        self.add_object_detection_model_to_gui(lit_subsystem_data.object_detection_model)
        led_tuples_list = self.create_led_tuple_range_list()
        self.led_tuples_dict_of_list[f"CAMERA_{self.camera_idx}"] =led_tuples_list
        leds_range_option_with_frame = self.create_control_led_range_frame()
        slider_led_range_option_with_frame = self.create_led_slider_range_frame()
        slider_brightness_range_option_with_frame = self.create_brightness_slider_range_frame()
        control_buttons_row = self.create_enable_controls_row()
        image_preview_section = self.create_image_preview_section()
        layout = [control_buttons_row, [leds_range_option_with_frame], [slider_led_range_option_with_frame], [slider_brightness_range_option_with_frame]]
        controller_options_section_layout = self.create_controller_options_section_wrapped_in_frame(layout)

        final_layout = self.create_final_subsystem_section_layout_wrapped_in_frame(image_preview_section, controller_options_section_layout)
        return final_layout

    def create_image_preview_section(self):
        """Creates the image element for the current Subsystem Frame being created. This is video feed will be displayed."""
        if self.camera_idx == 0:
            camera_preview = [sg.Image(filename=r'Jason.png', key=f'-CAMERA_{self.camera_idx}_FEED-', size=(720, 480))] 
        else:
            camera_preview = [sg.Image(filename=r'Lebron.png', key=f'-CAMERA_{self.camera_idx}_FEED-', size=(720, 480))]

        return camera_preview

    def create_enable_controls_row(self)->list[sg.Checkbox]:
        """Creates the main controls row, which contains the checkboxes for enabling manual control of the LED subsystem, Autonomous Mode, and showing the camera feed."""
        control_buttons_row = [sg.Checkbox(f"Manually Control LIT Subsystem {self.camera_idx}", size=(23,1), key=f'-CAMERA_{self.camera_idx}_MANUALSTATUS-', enable_events=True), 
                                sg.Checkbox(f"Autonomous Mode", size=(13,1), key=f'-CAMERA_{self.camera_idx}_AUTONOMOUSMODE-', enable_events=True), 
                                sg.Checkbox(f"Show Camera Feed", size=(15,1), key=f'-CAMERA_{self.camera_idx}_SHOWFEED-', enable_events=True, disabled=True)]
        
        return control_buttons_row

    def create_control_led_range_frame(self)->sg.Frame:
        """Creates the Frame containing checkboxes for manually controlling sections of the LED Subsystem with checkboxes which each refer to a specific section."""
        leds_range_option_inside_frame = [[sg.Checkbox(f"({led_range[0]}, {led_range[1]})",  size=((len(str(led_range[0]))+1+len(str(led_range[1]))),1),\
                                                        key=f'-CAMERA_{self.camera_idx}_LEDRANGE_{led_range[0]}_{led_range[1]}-', enable_events=True, disabled=True) \
                                                            for led_range in self.led_tuples_dict_of_list[f'CAMERA_{self.camera_idx}']]]
        leds_range_option_with_frame = sg.Frame('Manually Control LED Ranges', leds_range_option_inside_frame)

        return leds_range_option_with_frame

    def create_led_slider_range_frame(self)->sg.Frame:
        """Creates the Frame containing checkboxes and a slider for manually controlling consecutive leds in the LED Subsystem."""
        slider_led_range_option_inside_frame = [[sg.Checkbox(f'Adjust LEDs Left To Right', size=(23,1), key=f'-CAMERA_{self.camera_idx}_SLIDER_LEFT_TO_RIGHT-', enable_events=True, default=True, disabled=True),
                                                 sg.Checkbox(f'Adjust LEDs Right To Left', size=(23,1), key=f'-CAMERA_{self.camera_idx}_SLIDER_RIGHT_TO_LEFT-', enable_events=True, disabled=True)],
                                                [sg.Slider((0,self.number_of_leds), 0,1, orientation='h', size=(20,15), key=f'-CAMERA_{self.camera_idx}_LEDSLIDER-',\
                                                            enable_events=True, expand_x=True, disabled=True)]]
        slider_led_range_option_with_frame = sg.Frame('Adjust LEDs Consecutively', slider_led_range_option_inside_frame, expand_x=True)
        
        return slider_led_range_option_with_frame

    def create_brightness_slider_range_frame(self)->sg.Frame:
        """Creates the Frame containing the brightness slider used to set the brightness of manual controled LEDs."""
        slider_brightness_range_option_inside_frame = [[sg.Slider((0, 100), 0, 1, orientation='h', size=(20,15), key=f'-CAMERA_{self.camera_idx}_BRIGHTNESSSLIDER-', \
                                                                   enable_events=True, expand_x=True, disabled=True)]]
        slider_brightness_range_option_with_frame = sg.Frame('Adjust Brightness of LEDs (in Percentages)', slider_brightness_range_option_inside_frame, expand_x=True)
        
        return slider_brightness_range_option_with_frame

    def create_controller_options_section_wrapped_in_frame(self, layout_list: list)->sg.Frame:
        """Creates a Frame around the Current Subsystem Control Settings being created in the GUI. Used to seperate Subsystem Control Settings from the Camera feed."""
        return sg.Frame(f'Camera {self.camera_idx} Subsystem Controller', layout_list)

    def create_final_subsystem_section_layout_wrapped_in_frame(self, image_preview_section, controller_options_section_layout)->sg.Frame:
        """Creates a Frame around the Current Subsystem Panel being created. Used to seperate Subsystems from one another in the GUI."""
        final_layout = [image_preview_section, [controller_options_section_layout]]
        return sg.Frame(f'Camera {self.camera_idx} Subsystem', final_layout)

    def create_gui_from_cameras_list(self, lit_subsystem_data: list[LITSubsystemData])->list[list[sg.Frame]]:
        """Creates all of the Subsystem Frames which are displayed in the Gui. This is passed to the sg.Window class to create the final GUI."""
        return [[self.create_camera_frame(subsystem_data) for subsystem_data in lit_subsystem_data]]

    def create_gui_from_camera_instance(self, lit_subsystem_data: LITSubsystemData)->list[list[sg.Frame]]:
        """Creates a LITSubsystem Frame which is displayed in the GUI. Called when user provides only one LITSubsystem data instance to the constructor."""
        return [[self.create_camera_frame(lit_subsystem_data)]]

    

if __name__ == '__main__':
    obj_detector_one = ObjectDetectionModel(r'C:\Users\brand\OneDrive\Documents\SeniorDesign\ModelFiles\detect.tflite', False, 0, 
                                        r'C:\Users\brand\OneDrive\Documents\SeniorDesign\ModelFiles\labelmap.txt')
    # obj_detector_two = ObjectDetectionModel(r'/home/clawizm/Desktop/LITProject/tflite1/Sample_TFLite_model/detect.tflite', False, 2, 
    #                                     r'/home/clawizm/Desktop/LITProject/tflite1/Sample_TFLite_model/labelmap.txt')
    subsystem_one = LITSubsystemData(0, obj_detector_one, host='192.168.0.220', port=5000)
    subsystem_two = LITSubsystemData(1, obj_detector_one, host='192.168.0.220', port=5001)

    subsystem_list = [subsystem_one, subsystem_two]
    lit_gui = LITGUI(subsystem_list)
    lit_gui.start_event_loop()
