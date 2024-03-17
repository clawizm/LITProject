import threading
from threading import Thread
import cv2
from queue import Queue
import numpy as np
import time
import pickle
import socket
import PySimpleGUI as sg    
from tensorflow.lite.python.interpreter import Interpreter 

try:
    from tflite_runtime.interpreter import Interpreter
    from tflite_runtime.interpreter import load_delegate
except:
    pass

    
import typing
from multiprocessing import Process, Queue

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

def send_data_for_led_addressing(client_conn: socket.socket, curr_led_tuple_list: list[tuple], current_led_list_of_dicts: list[dict], thread_lock: socket.socket = None):
    if not curr_led_tuple_list:
        missing_ranges = (0,255)
    else:
        missing_ranges = find_missing_numbers_as_ranges_tuples(curr_led_tuple_list)
    data = ['auto', current_led_list_of_dicts, missing_ranges]
    pickle_data = pickle.dumps(data)
    if thread_lock:
        with thread_lock:
            client_conn.send(pickle_data)
    else:
        client_conn.send(pickle_data)        
    return

def brightness_based_on_distance(distance: int)->float:
    """Returns a brightness percetange based from 0.00 to 1.00:
    distance (int): (in cm) The distance the human is away from the camera"""
    if distance < 50:
        return .01
    elif distance < 100:
        return .05
    elif distance < 150:
        return .1
    elif distance < 200:
        return .2
    elif distance < 250:
        return .3
    elif distance < 300:
        return .5
    elif distance < 350:
        return .7
    else:
        return 1.00

def determine_leds_range_for_angle(angle_x: float)->tuple:
    if angle_x <= 39 and angle_x > 28.25:
        return 0, 32
    elif angle_x <= 28.25 and angle_x > 19.75:
        return 32, 64
    elif angle_x <= 19.75 and angle_x > 10.00:
        return 64, 96
    elif angle_x <= 10.00 and angle_x > 0:
        return 96, 128
    elif angle_x >= -9.75 and angle_x < 0:
        return 128, 160
    elif angle_x >= -19.5 and angle_x < -9.75:
        return 192, 224
    elif angle_x >= -29.25 and angle_x < -19.5:
        return 224, 256
    else:
        None
    
def estimate_distance(found_width, focal_length, known_width):
    # Estimate the distance based on the size of the detected face
    distance = ((known_width * focal_length) / found_width) * 2.54
    return distance

def calculate_horz_angle(obj_center_x, frame_width, hfov):
    relative_position = obj_center_x / frame_width - 0.5
    angle = hfov * relative_position
    return angle

def calculate_vert_angle(obj_center_y, frame_width, vfov):
    relative_position = obj_center_y / frame_width - 0.5
    angle = vfov * relative_position
    return angle

class DetectObj:
    """Used to store the distance, horizontal, and vertical angles of a object detected in the current frame"""
    def __init__(self, objs_detected_list_dict: list[dict], leds_to_turn_off_list: list[tuple]):
        self.objs_detected_list_dict = objs_detected_list_dict
        self.leds_to_turn_off_list = leds_to_turn_off_list
        
class VideoStream:
    focal_length = 1080.1875
    hfov = 78
    vfov = 49
    """Camera object that controls video streaming"""
    def __init__(self, camera_index: int, resolution: tuple[int, int] =(640,480), framerate: int = 30):
        """Creates an Object for that interfaces with the selected camera and stores data from the live feed in real time.
        Data is stored and the dropped as feed is updated.
        
        Parameters:
        - camera_index (int): The file path to a TensorFlow Lite model.
        - resolution (tuple[int, int]): A flag for creating a model that uses an edgeTPU to perfrom computations.
        - framerate (int): The framerate to display the camera feed at."""

        # Initialize the Camera and the camera image stream
        self.stream = cv2.VideoCapture(camera_index)
        ret = self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        ret = self.stream.set(3,resolution[0])
        ret = self.stream.set(4,resolution[1])
        self.video_width = resolution[0]
        self.video_heigth = resolution[1]
        # Read first frame from the stream
        (self.grabbed, self.frame) = self.stream.read()
        

	# Variable to control when the camera is stopped
        self.stopped = False

    def start(self):
        """Start the thread that reads frames from the video stream"""
        self.stopped = False
        Thread(target=self.update,args=()).start()
        return self

    def update(self):
        """Keep looping indefinitely until the thread is stopped"""
        while True:
            # If the camera is stopped, stop the thread
            if self.stopped:
                # Close camera resources
                self.stream.release()
                return

            # Otherwise, grab the next frame from the stream
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        """Return the most recent frame"""
        return self.frame

    def stop(self):
        """Indicate that the camera and thread should be stopped"""
        self.stopped = True


class ObjectDetectionModel:
    input_mean: float = 127.5
    input_std: float = 127.5
    frame_rate_calc: int = 1
    ref_person_width: int = 20 #inches

    def __init__(self, model_path: str, use_edge_tpu: bool, camera_index: int, label_path: str, 
                 min_conf_threshold: float= 0.5,window: typing.Union[sg.Window, None]=None, image_window_name: typing.Union[str, None]=None, 
                 client_conn: socket.socket = None, thread_lock: threading.Lock = None) -> None:
        """Creates an Object for performing object detection on a camera feed. Uses either an EdgeTPU or CPU to perform computations.
        
        Parameters:
        - model_path: (str): The file path to a TensorFlow Lite model.
        - use_edge_tpu (bool): A flag for creating a model that uses an edgeTPU to perfrom computations.
        - camera_index (int): The device ID of the camera the user would like to use for this object detection model.
        - label_path (str): The path of the labels used for object detection labeling.
        - min_conf_threshold (float): The confidence interval used to identify object."""
        # self.gui_window = window
        self.gui_window = window
        self.image_window_name = image_window_name
        self.min_conf_threshold = min_conf_threshold
        self.camera_index = camera_index
        self.client_conn = client_conn
        self.thread_lock = thread_lock
        self.freq = cv2.getTickFrequency()
        self.set_interpreter(use_edge_tpu, model_path)
        self.set_labels_from_label_path(label_path)
        self.set_input_details()
        self.set_boxes_clases_and_scores_idxs()
        self.detection_thread = None
        self.detection_active = threading.Event()

    def set_client_conn(self, client_conn: socket.socket):
        self.client_conn = client_conn
        return 
    
    def set_thread_lock(self, thread_lock: threading.Lock):
        self.thread_lock = thread_lock
        return
    
    def set_window(self, window: typing.Union[sg.Window, None]):
        self.gui_window = window
        return

    def set_image_window(self, image_window: typing.Union[str, None]):
        self.image_window_name = image_window
        return
    

    def start_detection(self):
        if self.detection_thread is None or not self.detection_thread.is_alive():
            self.detection_active.set()  # Signal that detection should be active
            self.video_stream = VideoStream(self.camera_index)  # Recreate VideoStream to ensure it's fresh
            self.detection_thread = threading.Thread(target=self.main_detection_loop, daemon=True)
            self.detection_thread.start()
        return
    
    def stop_detection(self):
        self.detection_active.clear()  # Signal that detection should stop
        if self.video_stream:
            self.video_stream.stop() 
        time.sleep(3)
        return
    

    def main_detection_loop(self):
        self.video_stream.start()
        while self.detection_active.is_set():
            try:
                self.t1 = cv2.getTickCount()
                self.perform_detection_on_current_frame()
                boxes, classes, scores = self.get_boxes_classes_and_scores_from_current_frame()
                self.loop_over_all_objects_detected(boxes, classes, scores)
            except:
                pass
        self.video_stream.stop()
        return

    def loop_over_all_objects_detected(self, boxes, classes, scores):
        if self.video_stream.stopped:
            return
        current_led_list_of_dicts = []
        curr_led_tuple_list = []
        for i in range(len(scores)):
            if ((scores[i] > self.min_conf_threshold) and (scores[i] <= 1.0)):      

                curr_led_dict = {}
                self.get_and_set_current_box_vertices(boxes[i])
                self.draw_rectangle_around_current_box()
                self.set_label_on_obj_in_frame(classes[i], scores[i])
                self.set_mid_point_current_obj()
                self.set_width_of_current_obj()
                distance = estimate_distance(self.current_obj_width, self.video_stream.focal_length, self.ref_person_width)
                angle_x = calculate_horz_angle(self.current_obj_mid_point_x, self.video_stream.video_width, self.video_stream.hfov)
                angle_y = calculate_vert_angle(self.current_obj_mid_point_y, self.video_stream.video_heigth, self.video_stream.hfov)
                brightness = brightness_based_on_distance(distance)
                led_tuple = determine_leds_range_for_angle(angle_x)

                curr_led_dict = {'brightness': brightness,
                                    'led_tuple': led_tuple}
                current_led_list_of_dicts.append(curr_led_dict)
                curr_led_tuple_list.append(led_tuple)


        try:
            if curr_led_tuple_list:
                send_data_for_led_addressing(self.client_conn, curr_led_tuple_list, current_led_list_of_dicts)
        except:
            pass

        cv2.putText(self.frame,'FPS: {0:.2f}'.format(self.frame_rate_calc),(30,50),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,0),2,cv2.LINE_AA)

        if self.gui_window:
            try:
                image_bytes = cv2.imencode('.png', self.frame)[1].tobytes()
                self.gui_window[self.image_window_name].update(data=image_bytes)
            except:
                pass
        else:
            print(distance)

        t2 = cv2.getTickCount()
        time1 = (t2-self.t1)/self.freq
        self.frame_rate_calc= 1/time1
        if cv2.waitKey(1) == ord('q'):
            self.video_stream.stop()
        return
        
    
    def set_label_on_obj_in_frame(self, class_idx, score):
        object_name = self.labels[int(class_idx)] # Look up object name from "labels" array using class index
        label = '%s: %d%%' % (object_name, int(score*100)) # Example: 'person: 72%'
        labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2) # Get font size
        label_ymin = max(self.ymin, labelSize[1] + 10) # Make sure not to draw label too close to top of window
        cv2.rectangle(self.frame, (self.xmin, label_ymin-labelSize[1]-10), (self.xmin+labelSize[0], label_ymin+baseLine-10), (255, 255, 255), cv2.FILLED) # Draw white box to put label text in             
        cv2.putText(self.frame, label, (self.xmin, label_ymin-7), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2) # Draw label text
        return 
    
    def set_width_of_current_obj(self):
        self.current_obj_width = self.xmax - self.xmin
        return 
    
    def set_mid_point_current_obj(self):
        self.current_obj_mid_point_x = self.xmin + (.5 * (self.xmax - self.xmin))
        self.current_obj_mid_point_y = self.ymin + (.5 * (self.ymax - self.ymin))

    def get_and_set_current_box_vertices(self, boxes):
        self.ymin = int(max(1,(boxes[0] * self.video_stream.video_heigth)))
        self.xmin = int(max(1,(boxes[1] * self.video_stream.video_width)))
        self.ymax = int(min(self.video_stream.video_heigth,(boxes[2] * self.video_stream.video_heigth)))
        self.xmax = int(min(self.video_stream.video_width,(boxes[3] * self.video_stream.video_width)))
        return
    
    def draw_rectangle_around_current_box(self):
        cv2.rectangle(self.frame, (self.xmin,self.ymin), (self.xmax,self.ymax), (10, 255, 0), 2)
        return
    
    def obj_is_person(self, obj):
        if obj == 'person':
            return True
        return False


    def perform_detection_on_current_frame(self):
        if self.video_stream.stopped:
            return
        frame1 = self.video_stream.read()
        self.frame = frame1.copy()
        frame_rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (self.width, self.height))
        input_data = np.expand_dims(frame_resized, axis=0)   
        if self.floating_model:
            input_data = (np.float32(input_data) - self.input_mean) / self.input_std
        self.interpreter.set_tensor(self.input_details[0]['index'],input_data)
        self.interpreter.invoke()
    
    def get_boxes_classes_and_scores_from_current_frame(self):
        if self.video_stream.stopped:
            return
        boxes = self.interpreter.get_tensor(self.output_details[self.boxes_idx]['index'])[0] # Bounding box coordinates of detected objects
        classes = self.interpreter.get_tensor(self.output_details[self.classes_idx]['index'])[0] # Class index of detected objects
        scores = self.interpreter.get_tensor(self.output_details[self.scores_idx]['index'])[0] # Confidence of detected objects
        return boxes, classes, scores
    def set_interpreter(self, use_edge_tpu: bool, model_path: str)->None:
        if use_edge_tpu:
            interpreter = self.load_edge_tpu_model(model_path)
        else:
            interpreter = self.load_cpu_model(model_path)
        self.interpreter = interpreter
        self.interpreter.allocate_tensors()
        return
    
    def set_labels_from_label_path(self, label_path: str)->None:
        with open(label_path, 'r') as f:
            self.labels = [line.strip() for line in f.readlines()]  
        if self.labels[0] == '???':
            del(self.labels[0])
        return
    
    def set_boxes_clases_and_scores_idxs(self)->None:
        if ('StatefulPartitionedCall' in self.outname): # This is a TF2 model
            self.boxes_idx, self.classes_idx, self.scores_idx = 1, 3, 0
        else: # This is a TF1 model
            self.boxes_idx, self.classes_idx, self.scores_idx = 0, 1, 2
        return
    
    def set_input_details(self)->None:
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.height = self.input_details[0]['shape'][1]
        self.width = self.input_details[0]['shape'][2]
        self.floating_model = (self.input_details[0]['dtype'] == np.float32)
        self.outname = self.output_details[0]['name']


    def load_edge_tpu_model(self, model_path: str)->None:
        """
        Loads a TensorFlow Lite model and creates an interpreter optimized for Edge TPU.

        Parameters:
        - model_path (str): The file path to the TensorFlow Lite model compiled for Edge TPU.

        Returns:
        A TensorFlow Lite Interpreter instance optimized for Edge TPU.
        """
        # Load the TensorFlow Lite model with Edge TPU support.
        interpreter = Interpreter(
            model_path=model_path,
            experimental_delegates=[load_delegate('libedgetpu.so.1')]
        )        
        return interpreter

    def load_cpu_model(self, model_path: str):
        """
        Loads a TensorFlow Lite model and creates an interpreter using the CPU.
        
        Paramters:
        - model_path: The file path to the Tensorflow Lite model compiled for CPU.
        
        Returns:
        A TensorFlow Lite Interpreter instance optimized for CPU use."""

        tf_interpreter = Interpreter(model_path=model_path)
        return tf_interpreter
    
    @property
    def interpreter(self):
        return self._interpreter

    @interpreter.setter
    def interpreter(self, interpreter)->None:
        # if isinstance(interpreter, Interpreter):
        self._interpreter = interpreter


    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, labels: list[str])->None:
        if isinstance(labels, list):
            self._labels = labels


    @property
    def input_details(self):
        return self._input_details

    @input_details.setter
    def input_details(self, input_details)->None:
        # if isinstance(input_details):
            self._input_details = input_details
    

    @property
    def output_details(self):
        return self._output_details

    @output_details.setter
    def output_details(self, output_details)->None:
        # if isinstance(input_details):
            self._output_details = output_details


    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, height)->None:
        # if isinstance(input_details):
            self._height = height


    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width)->None:
        # if isinstance(input_details):
            self._width = width


    @property
    def floating_model(self)->bool:
        return self._floating_model

    @floating_model.setter
    def floating_model(self, floating_model)->None:
        # if isinstance(input_details):
            self._floating_model = floating_model


    @property
    def outname(self):
        return self._outname
    
    @outname.setter
    def outname(self, outname)->None:
        # if isinstance(input_details):
            self._outname = outname



if __name__ == '__main__':
    host = '192.168.1.2'
    port = 5000
    model_path = r'/home/clawizm/Desktop/LITProject/tflite1/Sample_TFLite_model/edgetpu.tflite'
    label_path = r'/home/clawizm/Desktop/LITProject/tflite1/Sample_TFLite_model/labelmap.txt'
    first_model = ObjectDetectionModel(host, port, model_path, False, -1, label_path)
    port = 5001
    second_model = ObjectDetectionModel(host, port, model_path, False, -1, label_path)
    processes = []
    for camera_id in [0,1]:  # Adjust camera IDs as needed
        port = 5000 + camera_id  # Example: camera 0 uses port 5000, camera 1 uses port 5001
        p = Process(target=ObjectDetectionModel.start_detection)
        p.start()
        processes.append(p)

    # Wait for all processes to complete
    for p in processes:
        p.join()