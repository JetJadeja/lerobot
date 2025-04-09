#!/usr/bin/env python3

import argparse
import time
import sys
from typing import List, Dict, Tuple

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

def scan_motors_on_port(port, brand, model, baudrate=1000000):
    """Scan for motors on a specific port and return their IDs and positions."""
    motor_bus_config_cls, motor_bus_cls, model_baudrate_table, series_baudrate_table = get_motor_bus_cls(brand)
    
    # Check if the provided model is supported
    if model not in model_baudrate_table:
        raise ValueError(
            f"Invalid model '{model}' for brand '{brand}'. Supported models: {list(model_baudrate_table.keys())}"
        )
    
    # Setup motor names, indices, and models - we'll use a placeholder since we're scanning
    motor_name = "scanner"
    motor_index_arbitrary = 1  # Just a placeholder ID
    
    config = motor_bus_config_cls(port=port, motors={motor_name: (motor_index_arbitrary, model)})
    
    # Initialize the MotorBus
    motor_bus = motor_bus_cls(config=config)
    
    # Store results
    results = []
    
    try:
        # Connect to the motor bus
        motor_bus.connect()
        print(f"Connected to port: {port}")
        
        # Scan for motors using different baudrates
        all_baudrates = set(series_baudrate_table.values())
        found_motors = False
        
        for baudrate_val in all_baudrates:
            motor_bus.set_bus_baudrate(baudrate_val)
            present_ids = motor_bus.find_motor_indices(list(range(1, 10)))
            
            if present_ids:
                found_motors = True
                print(f"Found {len(present_ids)} motors at baudrate {baudrate_val}")
                
                # We found motors at this baudrate, now get their positions
                for motor_id in present_ids:
                    try:
                        # Configure the motor bus to communicate with this specific ID
                        motor_bus_config_cls, motor_bus_cls, _, _ = get_motor_bus_cls(brand)
                        config = motor_bus_config_cls(port=port, motors={f"motor_{motor_id}": (motor_id, model)})
                        specific_motor_bus = motor_bus_cls(config=config)
                        specific_motor_bus.connect()
                        specific_motor_bus.set_bus_baudrate(baudrate_val)
                        
                        # Read position
                        position = specific_motor_bus.read("Present_Position")
                        
                        # For Feetech motors, also read offset
                        offset = None
                        if brand == "feetech":
                            try:
                                offset = specific_motor_bus.read("Offset")
                            except Exception:
                                offset = "Unknown"
                        
                        # Store the results
                        results.append({
                            "port": port,
                            "id": motor_id,
                            "position": position,
                            "offset": offset,
                            "baudrate": baudrate_val
                        })
                        
                        specific_motor_bus.disconnect()
                    except Exception as e:
                        print(f"Error reading motor ID {motor_id}: {e}")
        
        if not found_motors:
            print(f"No motors found on port {port}")
            
    except Exception as e:
        print(f"Error scanning port {port}: {e}")
    
    finally:
        # Always disconnect
        try:
            motor_bus.disconnect()
        except:
            pass
    
    return results

def scan_all_motors(ports, brand, model, baudrate=1000000):
    """Scan all specified ports for motors and print out their information."""
    all_results = []
    
    for port in ports:
        print(f"\n=== Scanning port: {port} ===")
        results = scan_motors_on_port(port, brand, model, baudrate)
        all_results.extend(results)
    
    # Print summary
    if all_results:
        print("\n===== Motor Connection Summary =====")
        print("{:<40} {:<5} {:<15} {:<10}".format("Port", "ID", "Position", "Offset"))
        print("-" * 75)
        
        for result in all_results:
            print("{:<40} {:<5} {:<15} {:<10}".format(
                result["port"], 
                result["id"], 
                str(result["position"]), 
                str(result["offset"]) if result["offset"] is not None else "N/A"
            ))
    else:
        print("\nNo motors found on any of the specified ports.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan for motors and verify their connections")
    parser.add_argument("--ports", type=str, nargs="+", required=True, 
                        help="List of ports to scan (e.g. /dev/tty.usbmodem*)")
    parser.add_argument("--brand", type=str, required=True, 
                        help="Motor brand (e.g. dynamixel, feetech)")
    parser.add_argument("--model", type=str, required=True, 
                        help="Motor model (e.g. xl330-m077, sts3215)")
    parser.add_argument("--baudrate", type=int, default=1000000, 
                        help="Baudrate for communication (default: 1000000)")
    
    args = parser.parse_args()
    
    scan_all_motors(args.ports, args.brand, args.model, args.baudrate)