#!/usr/bin/env python3

import argparse
import time

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

def read_motor_position(port, brand, model, motor_id, baudrate=1000000):
    """Connect to a motor and read its current position."""
    # Get the appropriate classes for the motor brand
    motor_bus_config_cls, motor_bus_cls, model_baudrate_table, series_baudrate_table = get_motor_bus_cls(brand)

    # Check if the provided model is supported
    if model not in model_baudrate_table:
        raise ValueError(
            f"Invalid model '{model}' for brand '{brand}'. Supported models: {list(model_baudrate_table.keys())}"
        )

    # Setup motor configuration
    motor_name = "position_reader"
    config = motor_bus_config_cls(port=port, motors={motor_name: (motor_id, model)})

    # Initialize the motor bus
    motor_bus = motor_bus_cls(config=config)
    
    try:
        # Connect to the motor bus
        motor_bus.connect()
        print(f"Connected to {brand} {model} motor (ID: {motor_id}) on port {port}")
        print("Press Ctrl+C to stop reading")
        
        # Set the baudrate
        motor_bus.set_bus_baudrate(baudrate)
        
        while True:
            try:
                # Read the current position
                position = motor_bus.read("Present_Position")
                print(f"Current Position: {position}", end='\r')
                
                # For Feetech motors, also read the offset value
                if brand == "feetech":
                    offset = motor_bus.read("Offset")
                    adjusted_position = position - offset
                    print(f"Current Position: {position}, Offset: {offset}, Adjusted: {adjusted_position}", end='\r')
                
                # Small delay to prevent overwhelming the motor
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                print("\nStopping position reading...")
                break
            except Exception as e:
                print(f"\nError occurred while reading motor position: {e}")
                break
        
    except Exception as e:
        print(f"Error occurred while reading motor position: {e}")
    
    finally:
        # Always disconnect from the motor bus
        motor_bus.disconnect()
        print("Disconnected from motor bus.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read the current position of a motor/servo")
    parser.add_argument("--port", type=str, required=True, help="Motors bus port (e.g. /dev/ttyUSB0)")
    parser.add_argument("--brand", type=str, required=True, help="Motor brand (e.g. dynamixel, feetech)")
    parser.add_argument("--model", type=str, required=True, help="Motor model (e.g. xl330-m077, sts3215)")
    parser.add_argument("--id", type=int, required=True, help="ID of the motor to read (e.g. 1, 2, 3)")
    parser.add_argument("--baudrate", type=int, default=1000000, help="Baudrate for communication (default: 1000000)")
    
    args = parser.parse_args()
    
    read_motor_position(args.port, args.brand, args.model, args.id, args.baudrate)