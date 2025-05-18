import numpy as np
import time

# Define denormalization parameters for action outputs - must match normalization in robot_interface.py
# Assuming the first 5 values correspond to joint positions
JOINT_ACTION_RANGES = {
    "min": np.array([-1.0, -1.0, -200.0, -200.0, -10.0]),
    "max": np.array([1.0, 200.0, 10.0, 10.0, 10.0])
}

# Assuming the 7th value (index 6) is the gripper control
GRIPPER_ACTION_RANGES = {
    "min": np.array([0.0]),
    "max": np.array([50.0])
}


def denormalize_joint_actions(normalized_actions):
    """Denormalize joint actions from [-1, 1] to robot's range."""
    min_vals = JOINT_ACTION_RANGES["min"]
    max_vals = JOINT_ACTION_RANGES["max"]
    
    # Convert from [-1, 1] to actual range
    denormalized = 0.5 * (normalized_actions + 1.0) * (max_vals - min_vals) + min_vals
    
    return denormalized


def denormalize_gripper_action(normalized_action):
    """Denormalize gripper action from [-1, 1] to robot's range."""
    min_val = GRIPPER_ACTION_RANGES["min"][0]
    max_val = GRIPPER_ACTION_RANGES["max"][0]
    
    # Convert from [-1, 1] to actual range
    denormalized = 0.5 * (normalized_action + 1.0) * (max_val - min_val) + min_val
    
    return denormalized


def map_pi0_to_so100_actions(pi0_action):
    """Map Pi0 actions to SO100 robot joint space.
    
    Args:
        pi0_action: Raw action from Pi0 model
        
    Returns:
        numpy.ndarray: 6-dimensional action vector for SO100 robot
    """
    # Print the raw normalized action from Pi0
    print(f"Raw normalized action from Pi0: {pi0_action}")
    
    # Extract the normalized joint actions (first 5 dimensions)
    normalized_arm_joints = pi0_action[:5]
    
    # Extract the normalized gripper control 
    normalized_gripper = pi0_action[6] if len(pi0_action) > 6 else pi0_action[5]
    
    # Denormalize values to the robot's actual range
    denormalized_arm_joints = denormalize_joint_actions(normalized_arm_joints)
    denormalized_gripper = denormalize_gripper_action(normalized_gripper)
    
    # Print the denormalized values
    print(f"Denormalized arm joints: {denormalized_arm_joints}")
    print(f"Denormalized gripper: {denormalized_gripper}")
    
    # Combine into a 6-dimensional vector
    mapped_action = np.zeros(6)
    mapped_action[:5] = denormalized_arm_joints
    mapped_action[5] = denormalized_gripper
    
    return mapped_action


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
    
    # Use the improved mapping function instead of simple truncation
    print(f"Raw action values: {action_step}")
    positions_array = map_pi0_to_so100_actions(action_step)
    print(f"Mapped to SO100: {positions_array}")
    
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