#!/usr/bin/env python3

import argparse
import time
from lerobot.common.robot_devices.robots.configs import So100RobotConfig

def get_motor_bus_cls(brand: str) -> tuple:
    """Get the appropriate motor bus class and configuration based on the brand."""
    if brand == "feetech":
        from lerobot.common.robot_devices.motors.configs import FeetechMotorsBusConfig
        from lerobot.common.robot_devices.motors.feetech import (
            MODEL_BAUDRATE_TABLE,
            SCS_SERIES_BAUDRATE_TABLE,
            FeetechMotorsBus,
        )

        return FeetechMotorsBusConfig, FeetechMotorsBus, MODEL_BAUDRATE_TABLE, SCS_SERIES_BAUDRATE_TABLE

    elif brand == "dynamixel":
        from lerobot.common.robot_devices.motors.configs import DynamixelMotorsBusConfig
        from lerobot.common.robot_devices.motors.dynamixel import (
            MODEL_BAUDRATE_TABLE,
            X_SERIES_BAUDRATE_TABLE,
            DynamixelMotorsBus,
        )

        return DynamixelMotorsBusConfig, DynamixelMotorsBus, MODEL_BAUDRATE_TABLE, X_SERIES_BAUDRATE_TABLE

    else:
        raise ValueError(
            f"Currently we do not support this motor brand: {brand}. We currently support feetech and dynamixel motors."
        )

def read_motor_position(port1, port2, brand, model, baudrate=1000000):
    """Connect to motors on two ports and read their current positions."""
    # Get the appropriate classes for the motor brand
    motor_bus_config_cls, motor_bus_cls, model_baudrate_table, series_baudrate_table = get_motor_bus_cls(brand)

    # Check if the provided model is supported
    if model not in model_baudrate_table:
        raise ValueError(
            f"Invalid model '{model}' for brand '{brand}'. Supported models: {list(model_baudrate_table.keys())}"
        )
    
    print(f"Reading positions for {brand} {model} motors on both arms")
    print("Press Ctrl+C at any time to stop")
    
    try:
        # Iterate through motor IDs 1-6
        for motor_id in range(1, 7):
            print(f"\n--- Reading Motor ID {motor_id} on both arms ---")
            
            leader_position = None
            leader_offset = None
            follower_position = None
            follower_offset = None
            
            # Read leader arm motor
            try:
                motor_name = f"motor_{motor_id}"
                config = motor_bus_config_cls(port=port1, motors={motor_name: (motor_id, model)})
                leader_bus = motor_bus_cls(config=config)
                leader_bus.connect()
                leader_bus.set_bus_baudrate(baudrate)
                
                leader_position = leader_bus.read("Present_Position")
                if brand == "feetech":
                    try:
                        leader_offset = leader_bus.read("Offset")
                    except:
                        pass
                leader_bus.disconnect()
            except Exception as e:
                print(f"Leader arm motor {motor_id} error: {e}")
            
            # Read follower arm motor
            try:
                motor_name = f"motor_{motor_id}"
                config = motor_bus_config_cls(port=port2, motors={motor_name: (motor_id, model)})
                follower_bus = motor_bus_cls(config=config)
                follower_bus.connect()
                follower_bus.set_bus_baudrate(baudrate)
                
                follower_position = follower_bus.read("Present_Position")
                if brand == "feetech":
                    try:
                        follower_offset = follower_bus.read("Offset")
                    except:
                        pass
                follower_bus.disconnect()
            except Exception as e:
                print(f"Follower arm motor {motor_id} error: {e}")
            
            # Print results and calculate differences
            print(f"Motor ID {motor_id}:")
            
            # Print position information
            if leader_position is not None and follower_position is not None:
                position_diff = follower_position - leader_position
                print(f"  Position: Leader={leader_position}, Follower={follower_position}, Difference={position_diff}")
            elif leader_position is not None:
                print(f"  Position: Leader={leader_position}, Follower=N/A")
            elif follower_position is not None:
                print(f"  Position: Leader=N/A, Follower={follower_position}")
            
            # Print offset and adjusted information for Feetech motors
            if brand == "feetech":
                if leader_offset is not None and follower_offset is not None:
                    offset_diff = follower_offset - leader_offset
                    print(f"  Offset: Leader={leader_offset}, Follower={follower_offset}, Difference={offset_diff}")
                elif leader_offset is not None:
                    print(f"  Offset: Leader={leader_offset}, Follower=N/A")
                elif follower_offset is not None:
                    print(f"  Offset: Leader=N/A, Follower={follower_offset}")
                
                # Calculate adjusted positions if available
                if leader_position is not None and leader_offset is not None:
                    leader_adjusted = leader_position - leader_offset
                    print(f"  Adjusted Position (Leader): {leader_adjusted}")
                
                if follower_position is not None and follower_offset is not None:
                    follower_adjusted = follower_position - follower_offset
                    print(f"  Adjusted Position (Follower): {follower_adjusted}")
                
                # Print difference in adjusted positions if both available
                if (leader_position is not None and leader_offset is not None and 
                    follower_position is not None and follower_offset is not None):
                    adjusted_diff = follower_adjusted - leader_adjusted
                    print(f"  Adjusted Position Difference: {adjusted_diff}")
    
    except KeyboardInterrupt:
        print("\nOperation canceled by user.")
    
    print("Completed reading all motor positions.")

if __name__ == "__main__":
    # Create an instance of So100RobotConfig
    so100_config = So100RobotConfig()
    
    leader_arm = so100_config.leader_arms["main"].port
    follower_arm = so100_config.follower_arms["main"].port

    print(f"Leader arm port: {leader_arm}")
    print(f"Follower arm port: {follower_arm}")
    
    read_motor_position(leader_arm, follower_arm, "feetech", "sts3215", 1000000)