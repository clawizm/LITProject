import cv2
import mediapipe as mp
import time

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Function to classify the gesture based on hand landmarks
def classify_gesture(hand_landmarks):
    # Implement your gesture classification logic here
    # For simplicity, let's pretend we have a gesture classification function
    # This should return a string that uniquely identifies the gesture
    pass

cap = cv2.VideoCapture(0)
prev_gesture = None
gesture_start_time = None  # Time when the current gesture was first detected

while cap.isOpened():
    success, image = cap.read()
    if not success:
        continue

    image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
    image.flags.writeable = False
    results = hands.process(image)

    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            current_gesture = classify_gesture(hand_landmarks)

            if current_gesture != prev_gesture:
                if prev_gesture is not None and gesture_start_time is not None:
                    # Calculate the duration for which the previous gesture was maintained
                    duration = time.time() - gesture_start_time
                    print(f"Gesture '{prev_gesture}' was maintained for {duration} seconds.")

                # Update the gesture start time and the previous gesture
                gesture_start_time = time.time()
                prev_gesture = current_gesture
            # Optionally draw the hand landmarks
            mp.solutions.drawing_utils.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
    else:
        # If no hand is detected, reset the gesture and timer
        prev_gesture = None
        gesture_start_time = None

    cv2.imshow('Hand Gesture Detection', image)
    if cv2.waitKey(5) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()