#!/usr/bin/env python3
"""
SmartAssist Serial Number Collection Script
Reads vehicle serial number from CAN bus and saves to config

This script:
1. Listens to CAN bus for serial number message (0x205)
2. Decodes serial number from DBC
3. Updates logging_config.yaml with serial number
4. Runs at boot before main pipeline

Based on: bucher-05-collect-jcm-serial-number-service.d/set_serial_number.py
Location: tools/set_serial_number.py
"""
import os
import sys
import can
import cantools
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline', 'src'))

from utils.paths import get_dbc_path, get_config_path


def read_serial_number_from_can(dbc_path, timeout=30):
    """
    Read serial number from CAN bus
    
    Listens for message 0x205 containing equipment number
    
    Args:
        dbc_path: Path to DBC file
        timeout: Timeout in seconds
    
    Returns:
        Serial number string (e.g., 'SN217841') or None
    """
    print(f'Loading DBC file: {dbc_path}')
    
    try:
        db = cantools.database.load_file(dbc_path)
    except Exception as e:
        print(f'Failed to load DBC: {e}')
        return None
    
    print('Initializing CAN bus (can0)...')
    
    try:
        bus = can.interface.Bus(
            channel='can0',
            interface='socketcan',
            bitrate=250000,
            can_filters=[
                {'can_id': 0x205, 'can_mask': 0xFFF, 'extended': False}
            ]
        )
    except Exception as e:
        print(f'Failed to initialize CAN bus: {e}')
        return None
    
    print(f'Listening for serial number message (timeout={timeout}s)...')
    
    start_time = can.util.get_time()
    
    while True:
        # Check timeout
        if can.util.get_time() - start_time > timeout:
            print('Timeout waiting for serial number')
            bus.shutdown()
            return None
        
        try:
            msg = bus.recv(timeout=1.0)
            
            if msg and msg.arbitration_id == 0x205:
                # Decode message
                decoded = db.decode_message(msg.arbitration_id, msg.data)
                
                # Extract serial number components
                eq_high = decoded.get('EQ_number_high_order', 0)
                eq_mid = decoded.get('EQ_number_mid_order', 0)
                eq_low = decoded.get('EQ_number_low_order', 0)
                
                # Combine to form serial number
                serial_number = eq_high * 65536 + eq_mid * 256 + eq_low
                serial_str = f'SN{serial_number}'
                
                print(f'Serial number received: {serial_str}')
                bus.shutdown()
                return serial_str
        
        except Exception as e:
            # Ignore decoding errors for non-matching messages
            pass
    
    bus.shutdown()
    return None


def update_config_with_serial(config_path, serial_number):
    """
    Update logging_config.yaml with serial number
    
    Args:
        config_path: Path to logging_config.yaml
        serial_number: Serial number string
    
    Returns:
        True if successful
    """
    print(f'Updating config: {config_path}')
    
    try:
        # Read existing config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update serial number
        if 'vehicle_info' in config and len(config['vehicle_info']) > 0:
            config['vehicle_info'][0]['serial_number'] = serial_number
        else:
            config['vehicle_info'] = [{'serial_number': serial_number}]
        
        # Write back
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        print(f'Config updated successfully: {serial_number}')
        return True
    
    except Exception as e:
        print(f'Failed to update config: {e}')
        return False


def main():
    """
    Main entry point
    """
    print('=' * 60)
    print('SmartAssist Serial Number Collection')
    print('=' * 60)
    
    # Get paths
    try:
        dbc_path = get_dbc_path('TMS_V1_45_20251110.dbc')
        config_path = get_config_path('logging_config.yaml')
    except Exception as e:
        print(f'Failed to resolve paths: {e}')
        return 1
    
    # Check if serial number already set
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        existing_serial = config.get('vehicle_info', [{}])[0].get('serial_number')
        
        if existing_serial and existing_serial != 'UNKNOWN':
            print(f'Serial number already set: {existing_serial}')
            print('Skipping CAN read')
            return 0
    except Exception as e:
        print(f'Could not read existing config: {e}')
    
    # Read from CAN
    serial_number = read_serial_number_from_can(dbc_path, timeout=30)
    
    if not serial_number:
        print('Failed to read serial number from CAN')
        return 1
    
    # Update config
    if not update_config_with_serial(config_path, serial_number):
        return 1
    
    print('\n✓ Serial number collection successful')
    return 0


if __name__ == '__main__':
    sys.exit(main())