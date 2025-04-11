import numpy as np
import time
import torch
from lerobot.common.robot_devices.robots.configs import So100RobotConfig
from lerobot.common.robot_devices.robots.utils import make_robot_from_config
from PIL import Image


def initialize_robot():
    """Initialize and connect to the SO100 robot."""
    print("Initializing SO100 robot...")
    robot_config = So100RobotConfig(mock=False)
    robot = make_robot_from_config(robot_config)
    
    print("Connecting to SO100 robot...")
    robot.connect()
    print("Successfully connected to SO100 robot")
    
    # Wait for robot to stabilize
    time.sleep(1)
    
    return robot


def process_images(images, camera_name, default_shape=(224, 224, 3)):
    """Process camera images to the required format."""
    processed_image = np.zeros(default_shape, dtype=np.uint8)
    
    if camera_name in images and images[camera_name] is not None:
        img = Image.fromarray(images[camera_name])
        img = img.resize((default_shape[0], default_shape[1]))
        processed_image = np.array(img)
        
    return processed_image


def capture_robot_data(robot, display_function=None):
    """Capture and process data from the robot.
    
    Args:
        robot: The robot instance
        display_function: Optional function to display camera feeds
    
    Returns:
        observation: The observation dictionary for Pi0
    """
    print("Capturing robot data...")
    observation_dict = robot.capture_observation()
    
    # Extract joint positions (comes as a torch tensor)
    joint_positions = observation_dict["observation.state"]
    
    # Separate gripper position (last element) from other joint positions
    gripper_position = joint_positions[-1:].numpy()
    joint_position = joint_positions[:-1].numpy()
    
    # Get camera images if available
    images = {}
    for cam_name in robot.cameras:
        cam_key = f"observation.images.{cam_name}"
        if cam_key in observation_dict:
            images[cam_name] = observation_dict[cam_key].numpy()
    
    # Process camera images - use laptop for exterior and phone for wrist
    exterior_image = process_images(images, "laptop")
    wrist_image = process_images(images, "phone")
    
    # Display camera feeds if a display function is provided
    if display_function:
        image_dict = {
            "exterior_image_1_left": exterior_image,
            "wrist_image_left": wrist_image
        }
        if not display_function(image_dict):
            print("Camera display closed by user")
    
    # Create the observation for the Pi0 model
    observation = {
        # Joint and gripper state
        "observation/joint_position": joint_position,
        "observation/gripper_position": gripper_position,
        
        # Images
        "observation/exterior_image_1_left": exterior_image,
        "observation/wrist_image_left": wrist_image,
        
        # Additional state
        "observation/joint_velocity": np.zeros_like(joint_position),
        "observation/gripper_velocity": np.zeros_like(gripper_position),
        
        # Prompt
        "prompt": "Pick up the duck"
    }
    
    return observation 