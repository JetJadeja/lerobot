#!/usr/bin/env python3

import argparse
import time
import sys
from typing import List, Tuple

def get_motor_bus_cls(brand: str) -> tuple:
    """Get the appropriate motor bus class and configuration based on the brand."""
    if brand == "feetech":
        from lerobot.common.robot_devices.motors.configs import FeetechMotorsBusConfig
        from lerobot.common.robot_devices.motors.feetech import (
            FeetechMotorsBus,
        )
        return FeetechMotorsBusConfig, FeetechMotorsBus
    else:
        raise ValueError(f"Currently we only support feetech motors for this test.")

def progressive_motor_test(port: str, brand: str, model: str, motor_ids: List[int], baudrate: int=1000000):
    """Progressively test communication with an increasing number of motors."""
    motor_bus_config_cls, motor_bus_cls = get_motor_bus_cls(brand)
    
    print(f"Starting progressive motor testing on port {port}")
    print(f"Will test {len(motor_ids)} motors with IDs: {motor_ids}")
    
    # Create a dictionary of motor configurations
    all_motors = {}
    for i, motor_id in enumerate(motor_ids):
        motor_name = f"motor_{i+1}"
        all_motors[motor_name] = (motor_id, model)
    
    # Test with increasing number of motors
    for num_motors in range(1, len(motor_ids) + 1):
        test_motors = {}
        motor_names = []
        
        # Select the first num_motors motors
        for i in range(num_motors):
            motor_name = f"motor_{i+1}"
            test_motors[motor_name] = all_motors[motor_name]
            motor_names.append(motor_name)
        
        print(f"\n{'='*60}")
        print(f"Testing with {num_motors} motor(s): {[test_motors[name][0] for name in motor_names]}")
        print(f"{'='*60}")
        
        # Configure and connect to the motors
        config = motor_bus_config_cls(port=port, motors=test_motors)
        motor_bus = motor_bus_cls(config=config)
        
        try:
            # Connect to the motor bus
            print("Connecting to motor bus...")
            motor_bus.connect()
            motor_bus.set_bus_baudrate(baudrate)
            print("Successfully connected!")
            
            # Try to read positions multiple times
            for attempt in range(1, 6):
                try:
                    print(f"\nAttempt {attempt} to read positions:")
                    start_time = time.time()
                    positions = motor_bus.read("Present_Position", motor_names)
                    elapsed = time.time() - start_time
                    
                    print(f"SUCCESS: Read completed in {elapsed:.4f} seconds")
                    print(f"Positions: {positions}")
                    time.sleep(0.5)  # Short delay between reads
                    
                except Exception as e:
                    print(f"ERROR: Failed to read positions on attempt {attempt}")
                    print(f"Error details: {e}")
                    # Continue with the next attempt rather than breaking
            
            # Try to write positions
            try:
                print("\nAttempting to write positions (just current positions)...")
                start_time = time.time()
                motor_bus.write("Goal_Position", positions, motor_names)
                elapsed = time.time() - start_time
                print(f"SUCCESS: Write completed in {elapsed:.4f} seconds")
            except Exception as e:
                print(f"ERROR: Failed to write positions")
                print(f"Error details: {e}")
            
            # Brief pause before disconnecting
            time.sleep(1)
            
        except Exception as e:
            print(f"ERROR: Failed during setup with {num_motors} motors")
            print(f"Error details: {e}")
        
        finally:
            # Always disconnect from the motor bus
            try:
                motor_bus.disconnect()
                print(f"Disconnected from motor bus with {num_motors} motors")
            except Exception as e:
                print(f"Error during disconnect: {e}")
            
            # Give a bit more time between tests
            time.sleep(2)
    
    print("\nProgressive motor testing complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Progressively test communication with multiple motors")
    parser.add_argument("--port", type=str, required=True, help="Motors bus port (e.g. /dev/tty.usbmodem58FA1026741)")
    parser.add_argument("--brand", type=str, default="feetech", help="Motor brand (default: feetech)")
    parser.add_argument("--model", type=str, default="sts3215", help="Motor model (default: sts3215)")
    parser.add_argument("--baudrate", type=int, default=1000000, help="Baudrate for communication (default: 1000000)")
    parser.add_argument("--ids", type=int, nargs="+", default=[1, 2, 3, 4, 5, 6], 
                        help="IDs of motors to test (default: 1 2 3 4 5 6)")
    
    args = parser.parse_args()
    
    # Run the progressive test
    try:
        progressive_motor_test(args.port, args.brand, args.model, args.ids, args.baudrate)
    except KeyboardInterrupt:
        print("\nTest interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error in main program: {e}")
        sys.exit(1)