import cv2
import numpy as np


def display_camera_feeds(images, wait_key=1000):
    """Display camera feeds using OpenCV.
    
    Args:
        images: Dictionary with camera images (exterior, wrist)
        wait_key: Time to wait for key press in milliseconds (default: 1 second)
    
    Returns:
        True if user wants to continue, False to exit
    """
    # Check if there are images to display
    if not images:
        print("No camera feeds available to display")
        return True
    
    # Create a combined display
    if "exterior_image_1_left" in images and "wrist_image_left" in images:
        # Create a horizontal stack of both images
        display_img = np.hstack((images["exterior_image_1_left"], images["wrist_image_left"]))
        
        # Add labels to identify each camera
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(display_img, "Exterior Camera", (10, 30), font, 1, (0, 255, 0), 2)
        cv2.putText(display_img, "Wrist Camera", (display_img.shape[1]//2 + 10, 30), font, 1, (0, 255, 0), 2)
        
        # Display the combined image
        cv2.imshow("Robot Camera Feeds", display_img)
    else:
        # Display whichever image is available
        if "exterior_image_1_left" in images:
            cv2.imshow("Exterior Camera", images["exterior_image_1_left"])
        if "wrist_image_left" in images:
            cv2.imshow("Wrist Camera", images["wrist_image_left"])
    
    print("Press any key in the camera window to continue, or 'q' to exit")
    # Wait for key press, exit if 'q' is pressed
    key = cv2.waitKey(wait_key)
    if key == ord('q'):
        cv2.destroyAllWindows()
        return False
    
    return True


def cleanup_display():
    """Clean up and close all OpenCV windows."""
    cv2.destroyAllWindows() 