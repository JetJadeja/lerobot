import time

# Import modules from our own files
from robot_interface import initialize_robot, capture_robot_data
from camera_utils import display_camera_feeds, cleanup_display
from pi0_client import create_pi0_client, send_to_pi0
from motor_control import apply_robot_action


def main():
    """Main function to run the robot-Pi0 integration."""
    # Connect to Pi0 model
    client = create_pi0_client(host="localhost", port=9000)
    
    robot = None
    try:
        # Initialize robot
        robot = initialize_robot()
        
        # Capture robot data with camera display enabled
        observation = capture_robot_data(robot, display_function=display_camera_feeds)
        
        # Send to Pi0 model
        response = send_to_pi0(client, observation)
        
        # Apply action to robot (executes full trajectory)
        apply_robot_action(robot, response, hz=20)
        
    finally:
        # Close any open windows
        cleanup_display()
        
        # Ensure robot is disconnected properly
        if robot and robot.is_connected:
            print("Disconnecting from SO100 robot...")
            robot.disconnect()
            print("Robot disconnected")


def trajectory_mode(num_trajectories=1):
    """Run a specified number of trajectories with user confirmation between each.
    
    Args:
        num_trajectories: Number of trajectories to execute, -1 for infinite
    """
    client = create_pi0_client(host="localhost", port=9000)
    
    robot = None
    try:
        # Initialize robot
        robot = initialize_robot()
        
        trajectory_count = 0
        
        while num_trajectories == -1 or trajectory_count < num_trajectories:
            # Capture robot data with camera display enabled
            observation = capture_robot_data(robot, display_function=display_camera_feeds)
            
            # Send to Pi0 model
            response = send_to_pi0(client, observation)
            
            # Apply full trajectory to robot
            apply_robot_action(robot, response, hz=20)
            
            trajectory_count += 1
            
            # If we're not at the limit, ask for confirmation to continue
            if num_trajectories == -1 or trajectory_count < num_trajectories:
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


def continuous_control_mode(hz=5):
    """Run in continuous mode to control the robot using Pi0 model.
    
    Gets a new trajectory after each full trajectory execution.
    
    Args:
        hz: Frequency (Hz) for checking if we should get a new trajectory
    """
    client = create_pi0_client(host="localhost", port=9000)
    
    robot = None
    try:
        # Initialize robot
        robot = initialize_robot()
        
        print("Starting continuous control mode. Press Ctrl+C to exit.")
        
        while True:
            trajectory_start = time.time()
            
            # Capture robot data
            observation = capture_robot_data(robot, display_function=display_camera_feeds)
            
            # Send to Pi0 and apply full trajectory
            response = send_to_pi0(client, observation)
            apply_robot_action(robot, response, hz=20)
            
            # Calculate time to wait before next trajectory (to maintain desired frequency)
            elapsed = time.time() - trajectory_start
            cycle_time = 1.0 / hz  # Time per cycle in seconds
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


def continuous_camera_mode():
    """Run in continuous mode to display camera feeds in real-time without Pi0 control."""
    robot = None
    try:
        # Initialize robot
        robot = initialize_robot()
        
        print("Starting continuous camera display mode. Press 'q' in camera window or Ctrl+C to exit.")
        while True:
            # Capture and display robot data without Pi0 inference
            capture_robot_data(robot, display_function=display_camera_feeds)
            
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
    # Choose mode:
    # 'single'     - Execute one trajectory and stop
    # 'trajectory' - Execute specified number of trajectories with user confirmation
    # 'continuous' - Continuously execute trajectories with fixed timing
    # 'camera'     - Just display camera feeds without Pi0 control
    
    mode = 'single'
    
    if mode == 'trajectory':
        # Execute 3 trajectories with user confirmation between each
        # Set to -1 for unlimited trajectories
        trajectory_mode(num_trajectories=3)
    elif mode == 'continuous':
        # Continuously execute trajectories at 0.2Hz (one every 5 seconds)
        continuous_control_mode(hz=0.2)
    elif mode == 'camera':
        continuous_camera_mode()
    else:
        # Default: Execute one trajectory and stop
        main()
