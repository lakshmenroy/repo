"""
GStreamer Buffer Probes
Callbacks for processing buffer metadata and inference results
VERIFIED against pipeline_w_logging.py
"""
import sys
import os
import time
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
from datetime import datetime

try:
    import pyds
except ImportError:
    print("Warning: pyds not available. Some features will be disabled.")
    pyds = None

from ..detection_categories import DETECTION_CATEGORIES


# Global state for CSV logging (matches original)
_last_update_time = None
_file_index = 0


def buffer_monitor_probe(pad, info, u_data):
    """
    Monitor buffer flow and update camera status
    VERIFIED against pipeline_w_logging.py
    
    :param pad: GStreamer pad
    :param info: Probe info
    :param u_data: Tuple of (camera_name, app_context)
    :return: Gst.PadProbeReturn.OK
    """
    camera_name, app_context = u_data
    buffer = info.get_buffer()
    
    if buffer:
        can_client = app_context.get_value('can_client')
        if can_client and can_client.connected:
            can_client.update_camera_status(camera=camera_name)
    
    return Gst.PadProbeReturn.OK


def _write_to_csv(prediction_dict, app_context):
    """
    Write prediction data to CSV file with time-based rotation
    VERIFIED against deepstream_functions_sm.py write_to_file()
    
    :param prediction_dict: Dictionary of prediction data
    :param app_context: Application context (Gst.Structure)
    """
    global _last_update_time, _file_index
    
    serial_number = app_context.get_value('serial_number')
    log_duration = app_context.get_value('log_duration')
    log_directory = app_context.get_value('log_directory')
    file_start_time = app_context.get_value('file_start_time')
    columns = app_context.get_value('camera_columns')
    
    # Initialize last update time
    if _last_update_time is None:
        _last_update_time = time.time()
    
    # Check if we need to rotate to a new file
    current_time = time.time()
    if current_time - _last_update_time >= log_duration:
        _file_index += 1
        _last_update_time = current_time
    
    # Generate filename - VERIFIED format from original
    file_name = f'{log_directory}{serial_number}_CAMERA_{file_start_time}_{_file_index}.csv'
    
    # Write header if file doesn't exist
    if not os.path.exists(file_name):
        with open(file_name, 'w') as f:
            f.write(','.join(columns))  # No newline after header
    
    # Append data row
    with open(file_name, 'a') as f:
        row = ','.join(str(prediction_dict.get(col, 0.0)) for col in columns)
        f.write('\n' + row)  # Newline BEFORE row


def nozzlenet_src_pad_buffer_probe(pad, info, u_data):
    """
    Process nozzlenet inference results
    VERIFIED against pipeline_w_logging.py (production version)
    
    :param pad: GStreamer pad
    :param info: Probe info containing buffer
    :param u_data: app_context (Gst.Structure)
    :return: Gst.PadProbeReturn.OK
    """
    if not pyds:
        return Gst.PadProbeReturn.OK
    
    app_context = u_data
    
    # Get all required objects from app_context
    logger = app_context.get_value('app_context_v2').logger
    can_client = app_context.get_value('can_client')
    state_machine = app_context.get_value('state_machine')
    columns = app_context.get_value('camera_columns')
    search_item_list = app_context.get_value('search_item_list')
    overlay_parts = app_context.get_value('overlay_parts')
    
    # Initialize prediction dictionary
    prediction_dict = dict.fromkeys(columns, 0.0)
    
    frame_number = 0
    nozzle_status_string = None
    action_object_string = None
    highest_confidence = 0.0
    deleted = 1
    timenow = datetime.now()
    
    # Get buffer
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        sys.stderr.write('unable to get pgie src pad buffer\n')
        return Gst.PadProbeReturn.OK
    
    # Update FPS counter
    nn_fps_counter = app_context.get_value('nn_fps_counter')
    nn_fps_counter.update_fps()
    fps_count = nn_fps_counter.get_fps()
    
    if fps_count and can_client and can_client.connected:
        try:
            can_client.update_fps('nn', int(fps_count))
        except Exception as e:
            logger.debug(f'FPS update error: {e}')
    
    # Get batch metadata
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    
    # Acquire display metadata for OSD
    display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
    
    # Get frame metadata
    l_frame = batch_meta.frame_meta_list
    frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
    ndetections = frame_meta.num_obj_meta
    l_obj = frame_meta.obj_meta_list
    frame_number = frame_meta.frame_num
    
    # Setup display metadata for OSD (TWO labels) - VERIFIED
    display_meta.num_labels = 2
    py_nvosd_text_params = display_meta.text_params[0]
    py_nvosd_pm_params = display_meta.text_params[1]
    
    # Build OSD text BEFORE processing objects (to match original flow)
    py_nvosd_text_params.display_text = 'Frame Number={} | FPS {} | Num detection =  {} | Max Confidence = {:.2f} | Nozzle status = {} | Action object = {}\n Nozzle CAN = {} | Fan CAN = {} | Time = {} | SM Current Status = {} | SM Current State = {}\n SMS Time Difference = {:.3f} | Action Object Status = {} | Action Object Diffrence = {:.3f}'.format(
        frame_number, 
        fps_count, 
        ndetections, 
        highest_confidence, 
        nozzle_status_string, 
        action_object_string, 
        overlay_parts.get('sm_nozzle_state', 'N/A'), 
        overlay_parts.get('sm_fan_speed', 'N/A'), 
        timenow, 
        overlay_parts.get('sm_current_status', 'N/A'), 
        overlay_parts.get('sm_current_state', 'N/A'), 
        overlay_parts.get('sm_time_difference', 'N/A'), 
        overlay_parts.get('sm_ao_status', 'N/A'), 
        overlay_parts.get('sm_ao_difference', 'N/A')
    )
    
    # OSD text positioning and styling - VERIFIED VALUES
    py_nvosd_text_params.x_offset = 1
    py_nvosd_text_params.y_offset = 1
    py_nvosd_text_params.font_params.font_name = 'Serif'
    py_nvosd_text_params.font_params.font_size = 1
    py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)
    py_nvosd_text_params.set_bg_clr = 1
    py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 0.5)  # VERIFIED: 0.5 NOT 0.75
    
    # PM sensor OSD text
    py_nvosd_pm_params.display_text = f"S1_PM10={overlay_parts.get('s1_pm10', 0)} | S2_PM10={overlay_parts.get('s2_pm10', 'N/A')} | S3_PM10={overlay_parts.get('s3_pm10', 'N/A')} | S4_PM10={overlay_parts.get('s4_pm10', 'N/A')} | S5_PM10={overlay_parts.get('s5_pm10', 'N/A')}"
    py_nvosd_pm_params.x_offset = 0
    py_nvosd_pm_params.y_offset = 1040  # VERIFIED: 1040 NOT 740
    py_nvosd_pm_params.font_params.font_name = 'Serif'
    py_nvosd_pm_params.font_params.font_size = 1
    py_nvosd_pm_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)
    py_nvosd_pm_params.set_bg_clr = 1
    py_nvosd_pm_params.text_bg_clr.set(0.0, 0.0, 0.0, 0.5)
    
    # Iterate through detected objects
    while l_obj is not None:
        try:
            obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
        except StopIteration:
            pass
        
        try:
            l_obj = l_obj.next
        except StopIteration:
            pass
        
        # Remove objects not in search list - VERIFIED logic
        if obj_meta.class_id not in search_item_list:
            print('class id = ', obj_meta.class_id)
            print('search item list = ', search_item_list)
            pyds.nvds_remove_obj_meta_from_frame(frame_meta, obj_meta)
            print(f'class = {obj_meta.class_id} object deleted , total deleted = {deleted}')
            deleted += 1
        else:
            # Process detection based on class ID - VERIFIED values
            if obj_meta.class_id == DETECTION_CATEGORIES.PGIE_CLASS_ID_NOZZLE_CLEAR.value:
                nozzle_status_string = 'clear'
                obj_meta.rect_params.border_color.set(0.1411, 0.8019, 0.3254, 0.9)
                prediction_dict['nozzle_clear'] = 1.0
            
            elif obj_meta.class_id == DETECTION_CATEGORIES.PGIE_CLASS_ID_NOZZLE_BLOCKED.value:
                nozzle_status_string = 'blocked'
                obj_meta.rect_params.border_color.set(1.0, 0.3764, 0.2156, 0.9)
                prediction_dict['nozzle_blocked'] = 1.0
            
            elif obj_meta.class_id == DETECTION_CATEGORIES.PGIE_CLASS_ID_CHECK_NOZZLE.value:
                nozzle_status_string = 'check'
                obj_meta.rect_params.border_color.set(0.96078431, 0.57647059, 0.19215686, 0.9)
                prediction_dict['check_nozzle'] = 1.0
            
            elif obj_meta.class_id == DETECTION_CATEGORIES.PGIE_CLASS_ID_GRAVEL.value:
                nozzle_status_string = 'gravel'
                obj_meta.rect_params.border_color.set(0.678, 0.847, 0.902, 0.9)
                prediction_dict['gravel'] = 1.0
            
            elif obj_meta.class_id == DETECTION_CATEGORIES.PGIE_CLASS_ID_ACTION_OBJECT.value:
                action_object_string = 'true'
                obj_meta.rect_params.border_color.set(1.0, 0.0, 0.48627451, 0.9)
                prediction_dict['action_object'] = 1.0
            
            # Set border width
            obj_meta.rect_params.border_width = 5
            
            # Track highest confidence
            if obj_meta.confidence > highest_confidence:
                highest_confidence = obj_meta.confidence
                prediction_dict['confidence'] = highest_confidence
    
    pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)
    
    # Add timestamp - VERIFIED format
    prediction_dict['time'] = f"{datetime.now().strftime('%H:%M:%S.%f')[:-5]}00"
    
    # Write to CSV
    try:
        _write_to_csv(prediction_dict, app_context)
    except Exception as e:
        logger.error(f'CSV write error: {e}')
    
    # Send all data to CAN client
    for key, value in prediction_dict.items():
        if can_client and can_client.connected:
            try:
                can_client.send_data(key=key, value=value)
            except Exception as e:
                logger.debug(f'CAN send error for {key}: {e}')
    
    return Gst.PadProbeReturn.OK