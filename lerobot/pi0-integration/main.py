import time
import argparse

# Import modules from our own files
from robot_interface import initialize_robot, capture_robot_data
from camera_utils import display_camera_feeds, cleanup_display
from pi0_client import create_pi0_client, send_to_pi0
from motor_control import apply_robot_action


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


def main(args):
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


def continuous_camera_mode(args):
    """Run in continuous mode to display camera feeds in real-time without Pi0 control."""
    robot = None
    try:
        # Initialize robot
        robot = initialize_robot()
        
        print("Starting continuous camera display mode. Press 'q' in camera window or Ctrl+C to exit.")
        while True:
            # Capture and display robot data without Pi0 inference
            capture_robot_data(robot, display_function=display_camera_feeds, prompt=args.prompt)
            
            # Short delay to control frame rate
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("Continuous camera mode interrupted by user")
    finally:
        # Close any open windows
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
        continuous_camera_mode(args)
    else:
        # Default: Execute one trajectory and stop
        main(args)
