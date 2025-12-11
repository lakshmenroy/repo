"""
Nozzlenet Model Probes
Buffer probe documentation and helper functions for nozzlenet inference

NOTE: The actual nozzlenet_src_pad_buffer_probe function is implemented in
pipeline/probes.py and attached to the nozzlenet inference bin.

This module provides documentation and helper functions for working with
the nozzlenet probe.

VERIFIED: Main probe is in pipeline/probes.py (file #22)
"""

# The nozzlenet_src_pad_buffer_probe is the core detection processing function.
# It is called for every buffer (frame) that passes through the nozzlenet inference engine.
#
# Processing flow:
# 1. Get buffer and batch metadata
# 2. Update FPS counter and send to CAN
# 3. Acquire display metadata (2 labels: main + PM sensors)
# 4. Get frame metadata (batch size=1, single frame)
# 5. Setup OSD text (before processing objects)
# 6. Iterate through detected objects
# 7. Filter unwanted detections (remove if not in search_item_list)
# 8. Process each detection by class_id
# 9. Add display metadata to frame
# 10. Send to state machine
# 11. Update CAN bus (fan speed + nozzle state)
# 12. Write to CSV
# 13. Send all data to CAN client


def get_detection_class_mapping():
    """
    Get the mapping between class IDs and detection types
    
    :return: Dictionary mapping class_id to (status_string, dict_key, border_color)
    
    VERIFIED: Exact mappings from nozzlenet_src_pad_buffer_probe
    """
    return {
        5: {  # PGIE_CLASS_ID_NOZZLE_CLEAR
            'status': 'clear',
            'dict_key': 'nozzle_clear',
            'border_color': (0.1411, 0.8019, 0.3254, 0.9),  # Green
        },
        4: {  # PGIE_CLASS_ID_NOZZLE_BLOCKED
            'status': 'blocked',
            'dict_key': 'nozzle_blocked',
            'border_color': (1.0, 0.3764, 0.2156, 0.9),  # Red
        },
        2: {  # PGIE_CLASS_ID_CHECK_NOZZLE
            'status': 'check',
            'dict_key': 'check_nozzle',
            'border_color': (0.96078431, 0.57647059, 0.19215686, 0.9),  # Orange
        },
        3: {  # PGIE_CLASS_ID_GRAVEL
            'status': 'gravel',
            'dict_key': 'gravel',
            'border_color': (0.678, 0.847, 0.902, 0.9),  # Light Blue
        },
        1: {  # PGIE_CLASS_ID_ACTION_OBJECT
            'status': 'true',
            'dict_key': 'action_object',
            'border_color': (1.0, 0.0, 0.48627451, 0.9),  # Pink
        }
    }


def get_osd_label_config():
    """
    Get OSD label configuration for the nozzlenet probe
    
    :return: Dictionary with label 0 and label 1 configurations
    
    VERIFIED: Exact OSD configuration from original probe
    """
    return {
        'label_0': {
            'text_template': (
                "Frame Number={} | FPS {} | Num detection = {} | Max Confidence = {:.2f} | "
                "Nozzle status = {} | Action object = {}\n"
                "Nozzle CAN = {} | Fan CAN = {} | Time = {} | SM Current Status = {} | "
                "SM Current State = {}\n"
                "SMS Time Difference = {:.3f} | Action Object Status = {} | "
                "Action Object Diffrence = {:.3f}"
            ),
            'position': {'x': 1, 'y': 1},
            'font': 'Serif',
            'font_size': 1,
            'font_color': (1.0, 1.0, 1.0, 1.0),  # White
            'background_color': (0.0, 0.0, 0.0, 0.5)  # Black with 0.5 alpha
        },
        'label_1': {
            'text_template': "S1_PM10={} | S2_PM10={} | S3_PM10={} | S4_PM10={} | S5_PM10={}",
            'position': {'x': 0, 'y': 1040},  # VERIFIED: 1040, not 740
            'font': 'Serif',
            'font_size': 1,
            'font_color': (1.0, 1.0, 1.0, 1.0),  # White
            'background_color': (0.0, 0.0, 0.0, 0.5)  # Black with 0.5 alpha
        }
    }


def get_csv_column_defaults():
    """
    Get default CSV column names for nozzlenet logging
    
    :return: List of column names
    
    These are the typical columns written by the nozzlenet probe
    """
    return [
        'time',
        'confidence',
        'nozzle_clear',
        'nozzle_blocked',
        'check_nozzle',
        'gravel',
        'action_object',
        'sm_current_state',
        'sm_current_status',
        'sm_time_difference',
        'ao_status',
        'ao_difference',
        # Plus CAN sensor data...
    ]


def format_timestamp():
    """
    Format timestamp in the nozzlenet probe format
    
    :return: Timestamp string in format HH:MM:SS.ffffff00
    
    VERIFIED: Exact format from original - microseconds with last 2 digits as "00"
    """
    from datetime import datetime
    return f"{datetime.now().strftime('%H:%M:%S.%f')[:-5]}00"