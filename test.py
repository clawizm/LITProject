import math
import asyncio
# import winrt.windows.devices.enumeration as windows_devices


# CAMERA_NAME = "Dino-Lite Premier"

# async def get_camera_info():
#     return await windows_devices.DeviceInformation.find_all_async(4)

# connected_cameras = asyncio.run(get_camera_info())
# names = [camera.name for camera in connected_cameras]

# if CAMERA_NAME not in names:
#     print("Camera not found")
# else:
#     camera_index = names.index(CAMERA_NAME)
#     print(camera_index)






# import cv2

# index = 0
# arr = []
# while True:
#     cap = cv2.VideoCapture(index)
#     try:
#         if cap.getBackendName()=="MSMF":
#             arr.append(index)
#     except:
#         break
#     cap.release()
#     index += 1

# print(arr)

def brightness_based_on_distance(distance, minDist=0.01, maxDist=5.0, linear_slope=0.25, exponential_base=2):
    """Distance is in meters, so please provide meters"""
    if distance <= minDist:
        return 0  # Assuming you want very little brightness at close proximity.
    elif distance >= maxDist:
        return 1  # Maximum brightness at the max distance or beyond.
    
    # Define the threshold as halfway through the max distance.
    threshold = maxDist / 2
    
    if distance <= threshold:
        # Linear increase with a customizable slope from minDist to threshold.
        # Brightness increases linearly based on the distance and slope.
        linear_brightness = (distance - minDist) / (threshold - minDist) * linear_slope * 100
        # Ensuring that the linear phase does not exceed the intended maximum at the threshold.
        return (min(linear_brightness, linear_slope * 100) / 100)
    else:
        # Exponential increase from the end of the linear phase to 100% from threshold to maxDist.
        # Normalize distance to range [0,1] for exponential calculation.
        normalized_dist = (distance - threshold) / (maxDist - threshold)
        # Calculate exponential increase with a base that can be adjusted.
        exponential_brightness = 100 * linear_slope + (100 * (1 - linear_slope) * (normalized_dist ** exponential_base))
        return (exponential_brightness / 100)
    

print()
import pandas as pd

def order_scores(scores: pd.DataFrame) -> pd.DataFrame:
    scores.sort_values(by='score', ascending=False, inplace=True, )
    scores.set_index('score', inplace=True)
