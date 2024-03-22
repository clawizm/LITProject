import typing

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
        return (start1, start2), (end2, end1)  # Split range1 around range2

    # Partial overlap cases
    if start1 < start2 < end1 <= end2:
        return (start1, start2)  # Adjust end of range1 to start of range2
    elif start2 <= start1 < end2 < end1:
        return (end2, end1)  # Adjust start of range1 to end of range2

    # No overlap
    return range1

# Example usage
def create_fov_tuple_range_list(hfov: int, num_of_sections)->list[float]:
    max_positive_fov = round(hfov / 2)
    max_negative_fov = -1 * max_positive_fov
    lst = [max_negative_fov + x * (max_positive_fov - max_negative_fov) / num_of_sections for x in range(num_of_sections + 1)]
    lst.sort(reverse=True)
    return lst

def create_led_tuple_range_list(number_of_leds: int, num_of_sections: int)->list[tuple[int, int]]:
    """Returns a list of tuples containing the start and stopping point of LED ranges based on the number of LEDs of the subsystem specified divided by the number of sections the user would 
    like the subsystem divided into."""

    led_tuples_list = []
    leds_ranges = round(number_of_leds/num_of_sections)
    i = 0
    while i < number_of_leds:
        led_tuples_list.append((i, i+leds_ranges))
        i += leds_ranges
    return led_tuples_list

def brightness_based_on_distance(distance: int)->float:
    """Returns a brightness percetange based from 0.00 to 1.00:

    Parameters:
    - distance (int): (in cm) The distance the human is away from the camera"""
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

def determine_leds_range_for_angle(angle_x: typing.Union[float, int], led_sections: list[tuple[int, int]], hfov_range_list: list[float])->tuple:
    """Returns the LEDs to turn on based on the angle of the object provided.
    
    Parameters:
    angle_x (float): The angle of the object detected respective to the camera of the subsystem."""
    i = 0
    while i < len(hfov_range_list)-1:
        if angle_x <= hfov_range_list[i] and angle_x >= hfov_range_list[i+1]:
            return led_sections[i]
        i+=1
    return None


class ContainedClass:
    def __init__(self, name):
        self.name = name
        self.container = None

    def link_to_container(self, container):
        self.container = container

    def call_container_method(self):
        if self.container:
            self.container.container_method()
        else:
            print("No container linked.")

class ContainerClass:
    def __init__(self, name, contained_instance):
        self.name = name
        self.contained = contained_instance
        # Link the contained instance back to this container
        self.contained.link_to_container(self)

    def container_method(self):
        print(f"Container method called from {self.name}")

import cv2
import mediapipe as mp
import tensorflow as tf
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as viz_utils

# Load the TensorFlow model.
PATH_TO_SAVED_MODEL = "YOUR_MODEL_PATH/saved_model"
PATH_TO_LABELS = "YOUR_MODEL_PATH/mscoco_label_map.pbtxt"

detect_fn = tf.saved_model.load(PATH_TO_SAVED_MODEL)
category_index = label_map_util.create_category_index_from_labelmap(PATH_TO_LABELS, use_display_name=True)

# Initialize MediaPipe Hands.
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5)

# Function to run object detection.
def detect_objects(image):
    input_tensor = tf.convert_to_tensor(image)
    input_tensor = input_tensor[tf.newaxis, ...]
    detections = detect_fn(input_tensor)
    return detections

# Open webcam.
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Ignoring empty camera frame.")
        continue

    # Convert the BGR image to RGB.
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False

    # Detect objects in the image.
    detections = detect_objects(image)

    # Draw detection results.
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    viz_utils.visualize_boxes_and_labels_on_image_array(
        image,
        detections['detection_boxes'][0].numpy(),
        (detections['detection_classes'][0].numpy() + 1).astype(int),
        detections['detection_scores'][0].numpy(),
        category_index,
        use_normalized_coordinates=True,
        max_boxes_to_draw=200,
        min_score_thresh=.30,
        agnostic_mode=False)

    # Detect hands and draw hand landmarks for each detected person (for simplicity, this assumes each detection with high confidence is a person).
    for i in range(detections['detection_boxes'].shape[1]):
        if detections['detection_classes'][0][i] == 1 and detections['detection_scores'][0][i] >= 0.5:  # Class 1: Person
            box = detections['detection_boxes'][0][i].numpy()
            im_height, im_width, _ = image.shape
            (ymin, xmin, ymax, xmax) = (box[0] * im_height, box[1] * im_width, box[2] * im_height, box[3] * im_width)
            # Process each person's area with MediaPipe Hands.
            person_img = image[int(ymin):int(ymax), int(xmin):int(xmax)]
            results = hands.process(cv2.cvtColor(person_img, cv2.COLOR_BGR2RGB))
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp.solutions.drawing_utils.draw_landmarks(person_img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    # Display the resulting frame.
    cv2.imshow('MediaPipe Hands', image)
    if cv2.waitKey(5) & 0xFF == 27:  # Press 'ESC' to exit.
        break

cap.release()
cv2.destroyAllWindows()


# # Example Usage
# contained = ContainedClass("Contained Object")
# container = ContainerClass("Container Object", contained)

# # Call a method on the container from the contained object
# contained.call_container_method()




if __name__ == '__main__':
    x = [[]] * 5

    print(x)