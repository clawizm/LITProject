import PySimpleGUI as sg
import threading
import socket

import cv2
import mediapipe as mp


# Initialize MediaPipe Hands.
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=True, max_num_hands=2, min_detection_confidence=0.5)

# Load your original image.
image = cv2.imread('path_to_your_image.jpg')

# Coordinates of the detected object. Replace these with your actual coordinates.
x_min, x_max, y_min, y_max = 100, 300, 100, 300  # Example coordinates

# Crop the image to the ROI.
cropped_image = image[y_min:y_max, x_min:x_max]

# Convert the cropped image to RGB (required by MediaPipe).
cropped_image_rgb = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB)

# Process the cropped image.
results = hands.process(cropped_image_rgb)

# Draw hand landmarks on the cropped image.
if results.multi_hand_landmarks:
    for hand_landmarks in results.multi_hand_landmarks:
        mp.solutions.drawing_utils.draw_landmarks(
            cropped_image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

# Display the results.
cv2.imshow('Hand Detection on Cropped Image', cropped_image)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Release resources.
hands.close()
