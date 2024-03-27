import math
# import asyncio
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






sensor_width_mm = 6.17  # Sensor width in mm
focal_length_mm = 3.14  # Focal length in mm

# Calculate FOV in radians
FOV_radians = 2 * math.atan(sensor_width_mm / (2 * focal_length_mm))

# Convert FOV to degrees
FOV_degrees = math.degrees(FOV_radians)

FOV_degrees

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
    


