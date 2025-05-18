import numpy as np
import time
import torch
from lerobot.common.robot_devices.robots.configs import So100RobotConfig
from lerobot.common.robot_devices.robots.utils import make_robot_from_config
from PIL import Image


# Define normalization parameters - must match denormalization in motor_control.py
JOINT_POSITION_RANGES = {
    "min": np.array([-1.0, -1.0, -200.0, -200.0, -10.0]),
    "max": np.array([1.0, 200.0, 10.0, 10.0, 10.0])
}

GRIPPER_POSITION_RANGES = {
    "min": np.array([0.0]),
    "max": np.array([50.0])
}


def normalize_joint_position(joint_position):
    """Normalize joint positions to the range [-1, 1]."""
    min_vals = JOINT_POSITION_RANGES["min"]
    max_vals = JOINT_POSITION_RANGES["max"]
    
    # Clip values to the defined ranges
    clipped = np.clip(joint_position, min_vals, max_vals)
    
    # Apply min-max normalization to [-1, 1]
    normalized = 2.0 * (clipped - min_vals) / (max_vals - min_vals) - 1.0
    
    return normalized


def normalize_gripper_position(gripper_position):
    """Normalize gripper position to the range [-1, 1]."""
    min_val = GRIPPER_POSITION_RANGES["min"][0]
    max_val = GRIPPER_POSITION_RANGES["max"][0]
    
    # Clip value to the defined range
    clipped = np.clip(gripper_position[0], min_val, max_val)
    
    # Apply min-max normalization to [-1, 1]
    normalized = 2.0 * (clipped - min_val) / (max_val - min_val) - 1.0
    
    return np.array([normalized])


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


def capture_robot_data(robot, display_function=None, prompt="Pick up the duck"):
    """Capture and process data from the robot.
    
    Args:
        robot: The robot instance
        display_function: Optional function to display camera feeds
        prompt: Text prompt for the Pi0 model
    
    Returns:
        observation: The observation dictionary for Pi0
    """
    print(f"Capturing robot data with prompt: '{prompt}'")
    observation_dict = robot.capture_observation()

    print("Our observation dict", observation_dict["observation.state"])
    
    # Extract joint positions (comes as a torch tensor)
    joint_positions = observation_dict["observation.state"]
    
    # Separate gripper position (last element) from other joint positions
    gripper_position = joint_positions[-1:].numpy()
    joint_position = joint_positions[:-1].numpy()
    
    # Print raw values before normalization
    print("Our joint position", joint_position, "\nOur gripper position", gripper_position)
    
    # Normalize joint and gripper positions
    normalized_joint_position = normalize_joint_position(joint_position)
    normalized_gripper_position = normalize_gripper_position(gripper_position)
    
    print("Normalized joint position", normalized_joint_position, 
          "\nNormalized gripper position", normalized_gripper_position)
    
    # Get camera images if available
    images = {}
    for cam_name in robot.cameras:
        cam_key = f"observation.images.{cam_name}"
        if cam_key in observation_dict:
            images[cam_name] = observation_dict[cam_key].numpy()
    
    # Process camera images - use laptop for exterior and phone for wrist
    wrist_image = process_images(images, "laptop")
    exterior_image = process_images(images, "phone")
    
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
        # Joint and gripper state (normalized)
        "observation/joint_position": normalized_joint_position,
        "observation/gripper_position": normalized_gripper_position,
        
        # Images
        "observation/exterior_image_1_left": exterior_image,
        "observation/wrist_image_left": wrist_image,
        
        # Additional state
        "observation/joint_velocity": np.zeros_like(normalized_joint_position),
        "observation/gripper_velocity": np.zeros_like(normalized_gripper_position),
        
        # Prompt
        "prompt": prompt
    }
    
    return observation 