import time
import argparse

# Import modules from our own files
from robot_interface import initialize_robot, capture_robot_data
from camera_utils import display_camera_feeds, cleanup_display
from pi0_client import create_pi0_client, send_to_pi0
from motor_control import apply_robot_action

# Import OpenCV and NumPy
import cv2
import numpy as np

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='SO100 Robot Control with Pi0 Model')
    
    # Mode selection
    parser.add_argument('--mode', type=str, default='single',
                        choices=['single', 'trajectory', 'continuous', 'camera'],
                        help='Operation mode (default: single)')
    
    # Parameters for trajectory mode
    parser.add_argument('--num-trajectories', type=int, default=3,
                        help='Number of trajectories to execute in trajectory mode (default: 3, -1 for infinite)')
    
    # Parameters for continuous mode
    parser.add_argument('--hz', type=float, default=0.2,
                        help='Frequency in Hz for continuous mode trajectory requests (default: 0.2)')
    
    # Control frequency for trajectory execution
    parser.add_argument('--control-hz', type=float, default=20,
                        help='Control frequency in Hz for trajectory execution (default: 20)')
    
    # Server connection
    parser.add_argument('--host', type=str, default='localhost',
                        help='Pi0 server host (default: localhost)')
    parser.add_argument('--port', type=int, default=9000,
                        help='Pi0 server port (default: 9000)')
    
    # Prompt for Pi0 model
    parser.add_argument('--prompt', type=str, default='Pick up the duck',
                        help='Prompt for the Pi0 model (default: "Pick up the duck")')
    
    return parser.parse_args()

# Run a single trajectory
def single_trajectory_mode(args):
    """Main function to run the robot-Pi0 integration."""
    # Connect to Pi0 model
    client = create_pi0_client(host=args.host, port=args.port)
    
    robot = None
    try:
        # Initialize robot
        robot = initialize_robot()
        
        # Capture robot data with camera display enabled
        observation = capture_robot_data(robot, display_function=display_camera_feeds, prompt=args.prompt)
        
        # Send to Pi0 model
        response = send_to_pi0(client, observation)
        
        # Apply action to robot (executes full trajectory)
        apply_robot_action(robot, response, hz=args.control_hz)
        
    finally:
        # Close any open windows
        cleanup_display()
        
        # Ensure robot is disconnected properly
        if robot and robot.is_connected:
            print("Disconnecting from SO100 robot...")
            robot.disconnect()
            print("Robot disconnected")


# Run a specified number of trajectories with user confirmation between each
def trajectory_mode(args):
    """Run a specified number of trajectories with user confirmation between each."""
    client = create_pi0_client(host=args.host, port=args.port)
    
    robot = None
    try:
        # Initialize robot
        robot = initialize_robot()
        
        trajectory_count = 0
        
        while args.num_trajectories == -1 or trajectory_count < args.num_trajectories:
            # Capture robot data with camera display enabled
            observation = capture_robot_data(robot, display_function=display_camera_feeds, prompt=args.prompt)
            
            # Send to Pi0 model
            response = send_to_pi0(client, observation)
            
            # Apply full trajectory to robot
            apply_robot_action(robot, response, hz=args.control_hz)
            
            trajectory_count += 1
            
            # If we're not at the limit, ask for confirmation to continue
            if args.num_trajectories == -1 or trajectory_count < args.num_trajectories:
                choice = input("\nExecute another trajectory? (y/n): ")
                if choice.lower() != 'y':
                    break
        
    finally:
        # Close any open windows
        cleanup_display()
        
        # Ensure robot is disconnected properly
        if robot and robot.is_connected:
            print("Disconnecting from SO100 robot...")
            robot.disconnect()
            print("Robot disconnected")


# Run in continuous mode to control the robot using Pi0 model
def continuous_control_mode(args):
    """Run in continuous mode to control the robot using Pi0 model."""
    client = create_pi0_client(host=args.host, port=args.port)
    
    robot = None
    try:
        # Initialize robot
        robot = initialize_robot()
        
        print(f"Starting continuous control mode at {args.hz}Hz. Press Ctrl+C to exit.")
        
        while True:
            trajectory_start = time.time()
            
            # Capture robot data
            observation = capture_robot_data(robot, display_function=display_camera_feeds, prompt=args.prompt)
            
            # Send to Pi0 and apply full trajectory
            response = send_to_pi0(client, observation)
            apply_robot_action(robot, response, hz=args.control_hz)
            
            # Calculate time to wait before next trajectory (to maintain desired frequency)
            elapsed = time.time() - trajectory_start
            cycle_time = 1.0 / args.hz  # Time per cycle in seconds
            sleep_time = max(0, cycle_time - elapsed)
            
            if sleep_time > 0:
                print(f"Waiting {sleep_time:.2f}s before next trajectory...")
                time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("Continuous control mode interrupted by user")
    finally:
        # Close any open windows
        cleanup_display()
        
        # Ensure robot is disconnected properly
        if robot and robot.is_connected:
            print("Disconnecting from SO100 robot...")
            robot.disconnect()
            print("Robot disconnected")


# Camera test mode to display all available cameras with IDs
def camera_test_mode(args):
    """Display all available cameras with their names and IDs."""

    robot = None
    try:
        # Initialize robot
        robot = initialize_robot()
        print("Accessing all available cameras...")
        
        # Keep displaying camera feeds until user quits
        while True:
            # Capture observation to get camera images
            observation_dict = robot.capture_observation()
            
            # Get all camera images
            images = {}
            camera_ids = {}
            
            # Get camera ID mapping
            for i, cam_name in enumerate(robot.cameras):
                camera_ids[cam_name] = i
                cam_key = f"observation.images.{cam_name}"
                if cam_key in observation_dict:
                    images[cam_name] = observation_dict[cam_key].numpy()
            
            if not images:
                print("No camera feeds available")
                break
                
            # Process and display each camera feed
            displays = []
            for cam_name, cam_id in camera_ids.items():
                if cam_name in images and images[cam_name] is not None:
                    # Ensure image is in correct format
                    img = images[cam_name]
                    if img.ndim == 2:  # Convert grayscale to RGB if needed
                        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                    
                    # Add caption with name and ID
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    caption = f"Camera: {cam_name} (ID: {cam_id})"
                    cv2.putText(img, caption, (10, 30), font, 0.7, (0, 255, 0), 2)
                    
                    # Add to list of displays
                    displays.append(img)
            
            if displays:
                # Arrange images in a grid
                if len(displays) == 1:
                    combined = displays[0]
                elif len(displays) == 2:
                    combined = np.hstack(displays)
                else:
                    # Create a more complex grid for multiple cameras
                    rows = []
                    row = []
                    for i, img in enumerate(displays):
                        row.append(img)
                        if (i + 1) % 2 == 0 or i == len(displays) - 1:
                            # Create a row with uniform size images
                            for j in range(len(row)):
                                if row[j].shape != row[0].shape:
                                    row[j] = cv2.resize(row[j], (row[0].shape[1], row[0].shape[0]))
                            rows.append(np.hstack(row))
                            row = []
                    combined = np.vstack(rows)
                
                # Show the combined image
                cv2.imshow("All Camera Feeds", combined)
                
                # Wait for key press, exit if 'q' is pressed
                key = cv2.waitKey(1000)
                if key == ord('q'):
                    break
            else:
                print("No valid camera images to display")
                break
    
    finally:
        # Clean up
        cleanup_display()
        
        # Ensure robot is disconnected properly
        if robot and robot.is_connected:
            print("Disconnecting from SO100 robot...")
            robot.disconnect()
            print("Robot disconnected")


if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_args()
    
    print(f"Running in {args.mode} mode with prompt: '{args.prompt}'")
    
    # Run the appropriate mode based on the command-line argument
    if args.mode == 'trajectory':
        trajectory_mode(args)
    elif args.mode == 'continuous':
        continuous_control_mode(args)
    elif args.mode == 'camera':
        camera_test_mode(args)
    elif args.mode == 'single':
        single_trajectory_mode(args)
