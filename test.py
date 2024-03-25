import math
x = 6
y = 6
print()
def distance_to_brightness_complex(distance, minDist=0.01, maxDist=5.0, linear_slope=0.25, exponential_base=2):
    if distance <= minDist:
        return 0  # Assuming you want very little brightness at close proximity.
    elif distance >= maxDist:
        return 100  # Maximum brightness at the max distance or beyond.
    
    # Define the threshold as halfway through the max distance.
    threshold = maxDist / 2
    
    if distance <= threshold:
        # Linear increase with a customizable slope from minDist to threshold.
        # Brightness increases linearly based on the distance and slope.
        linear_brightness = (distance - minDist) / (threshold - minDist) * linear_slope * 100
        # Ensuring that the linear phase does not exceed the intended maximum at the threshold.
        return min(linear_brightness, linear_slope * 100)
    else:
        # Exponential increase from the end of the linear phase to 100% from threshold to maxDist.
        # Normalize distance to range [0,1] for exponential calculation.
        normalized_dist = (distance - threshold) / (maxDist - threshold)
        # Calculate exponential increase with a base that can be adjusted.
        exponential_brightness = 100 * linear_slope + (100 * (1 - linear_slope) * (normalized_dist ** exponential_base))
        return exponential_brightness

# Example usage:
# distance = 3  # Example distance in meters
# brightness_percentage = distance_to_brightness_complex(distance, linear_slope=0.2)
# print(f"Brightness: {brightness_percentage}%")

focal_pixel = (720 * 0.5) / math.tan(47 * 0.5)

print(focal_pixel)
import cv2
cv2.Came