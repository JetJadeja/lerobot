#!/usr/bin/env python3

import argparse
import time
from lerobot.common.robot_devices.robots.configs import So100RobotConfig
from lerobot.common.robot_devices.utils import RobotDeviceNotConnectedError, RobotDeviceAlreadyConnectedError

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

def interpret_feetech_status(status_byte):
    """Interprets the Feetech servo status byte into a human-readable string."""
    if status_byte is None:
        return "Status not available"
    
    errors = []
    # Common Feetech Status Bits (may vary slightly by model, check datasheet for STS3215 specifically if issues persist)
    if status_byte & 0x01: errors.append("Overload Error")         # Bit 0
    if status_byte & 0x02: errors.append("Overvoltage Error")      # Bit 1
    if status_byte & 0x04: errors.append("Overtemperature Error") # Bit 2
    # Bit 3 can be Stall or Angle Limit depending on context/model. Let's call it Generic Movement Error.
    if status_byte & 0x08: errors.append("Movement/Angle Limit Error/Stall") # Bit 3 
    if status_byte & 0x10: errors.append("Access Error/Invalid Page") # Bit 4 (Sometimes EEPROM access related or invalid register page)
    if status_byte & 0x20: errors.append("Instruction Error")      # Bit 5
    if status_byte & 0x40: errors.append("Driver Fault")           # Bit 6 (Less common, but some servos have it)
    # Bit 7 is often checksum error or unused

    if not errors and status_byte == 0:
        return "OK (0)"
    elif not errors and status_byte != 0:
        return f"Unknown status or flags: {status_byte} (binary: {status_byte:08b})"
    else:
        return f"Error(s) detected: {', '.join(errors)} (Raw: {status_byte}, Binary: {status_byte:08b})"

def set_motor_target_position(port, brand, model, motor_id, baudrate, target_position):
    """Connects to a specific motor, sets its lock and torque, and moves it to a target position."""
    motor_bus_config_cls, motor_bus_cls, model_baudrate_table, _ = get_motor_bus_cls(brand)

    if model not in model_baudrate_table:
        print(f"Error: Invalid model '{model}' for brand '{brand}'. Supported models: {list(model_baudrate_table.keys())}")
        return

    motor_name = f"motor_interactive_{motor_id}"
    config = motor_bus_config_cls(port=port, motors={motor_name: (motor_id, model)})
    motor_bus = motor_bus_cls(config=config)

    try:
        print(f"\nAttempting to connect to motor ID {motor_id} on port {port}...")
        motor_bus.connect()
        motor_bus.set_bus_baudrate(baudrate)
        print(f"Connected to motor ID {motor_id}. Baudrate set to {baudrate}.")

        if brand == "feetech":
            # --- Read initial critical parameters ---
            print(f"--- Reading initial parameters for motor ID {motor_id} ---")
            try:
                params_to_read = ["Mode", "Lock", "Torque_Enable", "Min_Angle_Limit", "Max_Angle_Limit", "Max_Torque_Limit", "Torque_Limit", "Acceleration"]
                for param_name in params_to_read:
                    val = motor_bus.read(param_name, motor_names=motor_name)[0]
                    print(f"Initial {param_name}: {val}")
                status_val_initial = motor_bus.read("Status", motor_names=motor_name)[0]
                print(f"Initial Status: {interpret_feetech_status(status_val_initial)}")
            except Exception as e:
                print(f"Error reading initial parameters for motor ID {motor_id}: {e}")
            print("----------------------------------------------------")

            try:
                initial_mode = motor_bus.read("Mode", motor_names=motor_name)[0]
                print(f"Motor ID {motor_id} initial 'Mode' status (re-read): {initial_mode} (0 is usually position servo mode)")
                if initial_mode != 0:
                    print(f"Attempting to set motor ID {motor_id} to Mode 0 (position servo mode)...")
                    motor_bus.write("Mode", 0, motor_names=motor_name)
                    time.sleep(0.1)
                    current_mode = motor_bus.read("Mode", motor_names=motor_name)[0]
                    print(f"Motor ID {motor_id} 'Mode' status after setting to 0: {current_mode}")
            except Exception as e:
                print(f"Could not read/write 'Mode' status for motor ID {motor_id}: {e}")

            print(f"Unlocking motor ID {motor_id}...")
            motor_bus.write("Lock", 0, motor_names=motor_name)
            time.sleep(0.1)
            try:
                lock_status = motor_bus.read("Lock", motor_names=motor_name)[0]
                print(f"Motor ID {motor_id} 'Lock' status after setting to 0: {lock_status} (0 means unlocked)")
            except Exception as e:
                print(f"Could not read 'Lock' status for motor ID {motor_id}: {e}")

            print(f"Enabling torque for motor ID {motor_id}...")
            motor_bus.write("Torque_Enable", 1, motor_names=motor_name)
            time.sleep(0.1)
            try:
                torque_status = motor_bus.read("Torque_Enable", motor_names=motor_name)[0]
                print(f"Motor ID {motor_id} 'Torque_Enable' status after setting to 1: {torque_status} (1 means enabled)")
            except Exception as e:
                print(f"Could not read 'Torque_Enable' status for motor ID {motor_id}: {e}")
            
            try:
                status_val = motor_bus.read("Status", motor_names=motor_name)[0]
                print(f"Motor ID {motor_id} status after torque enable sequence: {interpret_feetech_status(status_val)}")
                 # --- Read parameters again after torque enable ---
                print(f"--- Reading parameters for motor ID {motor_id} AFTER torque enable ---")
                for param_name in ["Min_Angle_Limit", "Max_Angle_Limit", "Max_Torque_Limit", "Torque_Limit", "Acceleration"]:
                    val = motor_bus.read(param_name, motor_names=motor_name)[0]
                    print(f"After Torque Enable - {param_name}: {val}")
                print("----------------------------------------------------------")
            except Exception as e:
                print(f"Could not read status/parameters for motor ID {motor_id} after torque enable: {e}")

        current_position = motor_bus.read("Present_Position", motor_names=motor_name)[0]
        print(f"Motor ID {motor_id} current position: {current_position}")

        print(f"Moving motor ID {motor_id} to target position: {target_position}")
        motor_bus.write("Goal_Position", int(target_position), motor_names=motor_name)
        time.sleep(1.5)  # Wait for the motor to move

        final_position = motor_bus.read("Present_Position", motor_names=motor_name)[0]
        print(f"Motor ID {motor_id} final position: {final_position}")

        if brand == "feetech":
            try:
                status_val_after_move = motor_bus.read("Status", motor_names=motor_name)[0]
                print(f"Motor ID {motor_id} status after move attempt: {interpret_feetech_status(status_val_after_move)}")
            except Exception as e:
                print(f"Could not read status for motor ID {motor_id} after move attempt: {e}")

        if abs(final_position - target_position) > 10:
            print(f"WARNING: Motor ID {motor_id} did not reach target position significantly. (Target: {target_position}, Final: {final_position})")

        print(f"Motor ID {motor_id} operation completed.")

    except RobotDeviceAlreadyConnectedError:
        print(f"Error: Motor bus for port {port} already connected.")
    except RobotDeviceNotConnectedError:
        print(f"Error: Motor bus for port {port} not connected when expected.")
    except ConnectionError as e:
        print(f"Connection Error for motor ID {motor_id} on port {port}: {e}")
        print("This could be due to: incorrect baudrate, motor ID not found, loose wiring, or no power to the motor.")
    except OSError as e:
        print(f"OS Error (likely port access) for motor ID {motor_id} on port {port}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred with motor ID {motor_id} on port {port}: {e}")
    finally:
        if motor_bus.is_connected:
            print(f"Disconnecting from motor ID {motor_id} on port {port}.")
            # Optionally, disable torque after operation if desired for safety/manual adjustment
            # if brand == "feetech":
            # motor_bus.write("Torque_Enable", 0, motor_names=motor_name)
            motor_bus.disconnect()
        else:
            print(f"Motor bus for motor ID {motor_id} was not connected or already disconnected.")

def main():
    parser = argparse.ArgumentParser(description="Interactively control follower arm motors.")
    parser.add_argument("--brand", type=str, default="feetech", help="Motor brand (default: feetech)")
    parser.add_argument("--model", type=str, default="sts3215", help="Motor model (default: sts3215)")
    parser.add_argument("--baudrate", type=int, default=1000000, help="Baudrate for communication (default: 1000000)")
    
    args = parser.parse_args()

    try:
        so100_config = So100RobotConfig()
        if "main" not in so100_config.follower_arms:
            print("Error: 'main' follower arm not found in So100RobotConfig. Available follower arms:")
            print(so100_config.follower_arms.keys())
            return
        follower_arm_port = so100_config.follower_arms["main"].port
    except Exception as e:
        print(f"Error loading So100RobotConfig or follower arm port: {e}")
        print("Please ensure your robot configuration is correct.")
        return

    print(f"Using follower arm port: {follower_arm_port}")
    print(f"Motor settings - Brand: {args.brand}, Model: {args.model}, Baudrate: {args.baudrate}")
    print("Enter motor ID and target position when prompted. Type 'quit' for motor ID to exit.")

    while True:
        try:
            motor_id_str = input("\nEnter Motor ID (e.g., 1) or type 'quit' to exit: ")
            if motor_id_str.lower() == 'quit':
                print("Exiting interactive motor control.")
                break
            
            motor_id = int(motor_id_str)
            if not (0 < motor_id < 253): # Typical valid ID range for Feetech/Dynamixel
                print("Invalid motor ID. Please enter a number in the valid range (e.g., 1-252).")
                continue

            target_position_str = input(f"Enter target position for motor ID {motor_id} (e.g., 2048): ")
            target_position = int(target_position_str)
            # You might want to add validation for target_position range if known (e.g., 0-4095 for some motors)

            set_motor_target_position(follower_arm_port, args.brand, args.model, motor_id, args.baudrate, target_position)
        
        except ValueError:
            print("Invalid input. Motor ID and target position must be integers.")
        except KeyboardInterrupt:
            print("\nExiting due to KeyboardInterrupt.")
            break
        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")
            # Decide if you want to break or continue on other errors

    print("Interactive motor control session ended.")

if __name__ == "__main__":
    main() 