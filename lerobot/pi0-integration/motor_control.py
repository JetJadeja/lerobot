import numpy as np
import time


def apply_single_action(robot, action_step, num_motors=None):
    """Apply a single action step to the robot.
    
    Args:
        robot: The robot instance
        action_step: A single action step (array of motor positions)
        num_motors: Optional number of motors (detected if None)
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Get the number of motors if not provided
    if num_motors is None:
        for name in robot.follower_arms:
            num_motors = len(robot.follower_arms[name].motors)
            break  # Just check the first arm
    
    if num_motors == 0:
        print("No motors found in follower arm")
        return False
    
    # If the action has more values than motors, truncate to the right size
    if len(action_step) > num_motors:
        print(f"Truncating action from {len(action_step)} to {num_motors} values")
        positions = action_step[:num_motors]
    else:
        positions = action_step
    
    # Convert to numpy array
    positions_array = np.array(positions)
    
    # Send to each follower arm
    for name in robot.follower_arms:
        try:
            # Write positions for each motor individually
            for motor_name, motor_value in zip(robot.follower_arms[name].motors.keys(), positions_array):
                robot.follower_arms[name].write("Goal_Position", motor_value, motor_name)
            return True
        except Exception as e:
            print(f"Error setting motor positions: {e}")
            return False


def apply_trajectory(robot, actions_array, hz=20):
    """Execute a full trajectory at a fixed control frequency.
    
    Args:
        robot: The robot instance
        actions_array: Array of action steps from Pi0
        hz: Control frequency in Hz (default: 20)
    """
    if len(actions_array) == 0:
        print("Empty actions array received")
        return
    
    print(f"Executing trajectory with {len(actions_array)} steps at {hz}Hz")
    
    # Get the number of motors in the follower arm
    num_motors = 0
    for name in robot.follower_arms:
        num_motors = len(robot.follower_arms[name].motors)
        print(f"Follower arm '{name}' has {num_motors} motors")
        break  # Just check the first arm
    
    # Calculate time per step in seconds
    step_duration = 1.0 / hz
    
    # Execute each action step in sequence at the specified frequency
    for i, action_step in enumerate(actions_array):
        step_start_time = time.time()
        
        print(f"Executing step {i+1}/{len(actions_array)}")
        
        # Apply this action step
        success = apply_single_action(robot, action_step, num_motors)
        
        # Calculate how long to wait to maintain desired frequency
        elapsed = time.time() - step_start_time
        sleep_time = max(0, step_duration - elapsed)
        
        if sleep_time > 0:
            time.sleep(sleep_time)
            actual_hz = 1.0 / (elapsed + sleep_time)
        else:
            actual_hz = 1.0 / elapsed if elapsed > 0 else float('inf')
        
        print(f"Step executed at {actual_hz:.1f}Hz (target: {hz}Hz)")
        
        # Check if we should continue
        if not success:
            print("Stopping trajectory execution due to error")
            break


def apply_robot_action(robot, action, hz=20):
    """Apply the action received from Pi0 to the follower arm.
    
    Args:
        robot: The robot instance
        action: Response from Pi0 model containing actions
        hz: Control frequency in Hz (default: 20)
    """
    if 'actions' not in action:
        print("No actions found in Pi0 response")
        return
    
    actions_array = action['actions']
    
    if len(actions_array) == 0:
        print("Empty actions array received")
        return
    
    print(f"Received {len(actions_array)} action steps from Pi0 model")
    print(f"Action shape: {actions_array.shape}")
    
    # Execute the full trajectory at the specified control frequency
    apply_trajectory(robot, actions_array, hz=hz) 