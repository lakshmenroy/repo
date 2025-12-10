#!/usr/bin/env python3
"""
SmartAssist Pipeline Application
Main entry point for AI inference pipeline

VERIFIED against pipeline_w_logging.py
Maintains exact initialization order from original
"""
import sys
import os
import signal
import threading
import time
from datetime import datetime
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from detection_categories import DETECTION_CATEGORIES
from context import Config, AppContext, GETFPS
from can.client import CanClient
from can.state_machine import SmartStateMachine
from utils.systemd import notify_systemd, load_latest_init_status
from utils.config import Configuration
from monitoring.threads import overlay_parts_fetcher, override_monitoring, unix_socket_server

# Initialize GStreamer
Gst.init(None)

# Global application context (GStreamer Structure for sharing state)
app_context = Gst.Structure.new_empty('app_context')


def bus_call(bus, message, loop):
    """
    GStreamer bus message callback
    VERIFIED against pipeline_w_logging.py on_message()
    
    :param bus: GStreamer bus
    :param message: Message from bus
    :param loop: GLib main loop
    :return: True to keep callback active
    """
    logger = app_context.get_value('app_context_v2').logger
    mtype = message.type
    
    if mtype == Gst.MessageType.EOS:
        logger.info('End-of-stream reached')
        loop.quit()
    
    elif mtype == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        logger.warning(f'Warning: {err}: {debug}')
    
    elif mtype == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        logger.error(f'Error: {err}: {debug}')
        print(err)
        
        # Check for camera timeout error
        if 'NvArgusCameraSrc: TIMEOUT' in str(err):
            logger.error('nvarguscamerasrc: Timeout error detected')
            # TODO: Implement camera replacement logic if needed
        
        notify_systemd('STOPPING=1', app_context)
        loop.quit()
    
    elif mtype == Gst.MessageType.STATE_CHANGED:
        if message.src == app_context.get_value('pipeline'):
            old_state, new_state, pending = message.parse_state_changed()
            logger.debug(f'Pipeline state: {old_state.value_nick} -> {new_state.value_nick}')
    
    return True


if __name__ == '__main__':
    # STEP 1: Set process ID and run mode (EXACT ORDER from old pipeline)
    app_context.set_value('main_process_id', os.getpid())
    app_context.set_value('SSWP_RUN_MODE', 'STANDALONE')
    if os.environ.get('SSWP_RUN_MODE') == 'SYSTEMD_NOTIFY_SERVICE':
        app_context.set_value('SSWP_RUN_MODE', 'SYSTEMD_NOTIFY_SERVICE')
    
    notify_systemd('STATUS=Initializing...', app_context)
    
    # STEP 2: Load camera initialization status
    if load_latest_init_status('bucher-d3-camera-init', app_context) != 0:
        print('ERROR: Failed to load camera initialization status')
        sys.exit(-1)
    
    # STEP 3: Initialize Configuration (logging_config.yaml)
    try:
        config = Configuration()  # Auto-detects monorepo paths
    except Exception as e:
        print(f'ERROR: Failed to load configuration: {e}')
        sys.exit(-1)
    
    # STEP 4: Load bucher camera config (bucher_camera_on_boot_config.json)
    try:
        bucher_config = Config()  # Loads camera_config.json
    except Exception as e:
        print(f'ERROR: Failed to load bucher config: {e}')
        sys.exit(-1)
    
    # STEP 5: Initialize AppContext (app_context_v2)
    app_context_v2 = AppContext(bucher_config)
    app_context_v2.initialise_logging()
    app_context.set_value('app_context_v2', app_context_v2)
    logger = app_context_v2.logger
    
    logger.info('=' * 70)
    logger.info('SmartAssist Pipeline Starting')
    logger.info('=' * 70)
    
    # STEP 6: Initialize CAN client and state machine
    logger.debug('Initializing CAN client and state machine...')
    can_client = CanClient()
    state_machine = SmartStateMachine()
    
    # STEP 7: Get configuration values (EXACT ORDER)
    serial_number = config.get_serial_number()
    log_duration = config.get_log_duration()
    log_directory = config.get_directory()
    columns = config.get_camera_columns()
    csi_columns = config.get_csi_columns()
    pm_columns = config.get_pm_columns()
    can_columns = config.get_can_signals()
    
    # STEP 8: Set up file start time and probe IDs
    file_start_time = datetime.now().strftime('%Y_%m_%d_%H%M')
    probe_ids = []
    
    # STEP 9: Define search item list (EXACT VALUES from old)
    search_item_list = [
        DETECTION_CATEGORIES.PGIE_CLASS_ID_ACTION_OBJECT.value,
        DETECTION_CATEGORIES.PGIE_CLASS_ID_CHECK_NOZZLE.value,
        DETECTION_CATEGORIES.PGIE_CLASS_ID_NOZZLE_BLOCKED.value,
        DETECTION_CATEGORIES.PGIE_CLASS_ID_NOZZLE_CLEAR.value,
        DETECTION_CATEGORIES.PGIE_CLASS_ID_GRAVEL.value
    ]
    
    # STEP 10: Set full path and socket path (EXACT VALUES)
    full_path_and_filename = __file__
    socket_path = '/tmp/bucher-deepstream-python-logger.sock'
    
    # STEP 11: Create FPS counters (EXACT ORDER)
    nn_fps_counter = GETFPS(0)
    rear_csi_fps_counter = GETFPS(0)
    front_csi_fps_counter = GETFPS(0)
    
    # STEP 12: Create overlay_parts dictionary (EXACT KEYS and VALUES)
    overlay_parts = {
        'sm_nozzle_state': 0,
        'sm_fan_speed': 0,
        'sm_current_status': 'N/A',
        'sm_current_state': 'N/A',
        'sm_time_difference': 0,
        'sm_ao_status': 'N/A',
        'sm_ao_difference': 0,
        's1_pm10': 'N/A',
        's2_pm10': 'N/A',
        's3_pm10': 'N/A',
        's4_pm10': 'N/A',
        's5_pm10': 'N/A'
    }
    
    # STEP 13: Create threading objects (EXACT ORDER)
    stop_event = threading.Event()
    monitoring_thread = threading.Thread(target=override_monitoring, args=(app_context,), daemon=True)
    overlay_thread = threading.Thread(target=overlay_parts_fetcher, args=(app_context,), daemon=True)
    server_thread = threading.Thread(
        target=unix_socket_server,
        args=('/tmp/smart_sweeper_pipeline_comms_socket', stop_event, app_context)
    )
    
    # STEP 14: Store ALL runtime variables in app context (EXACT ORDER from old)
    app_context.set_value('shutdown_initiated_by_user_process', False)
    app_context.set_value('pid_path', '/tmp/bucher-deepstream-python-logger.pid')
    app_context.set_value('last_notificationsent_to_systemd', '')
    app_context.set_value('enhanced_logging', False)
    app_context.set_value('can_client', can_client)
    app_context.set_value('state_machine', state_machine)
    app_context.set_value('serial_number', serial_number)
    app_context.set_value('log_duration', log_duration)
    app_context.set_value('camera_columns', columns)
    app_context.set_value('csi_columns', csi_columns)
    app_context.set_value('log_directory', log_directory)
    app_context.set_value('file_start_time', file_start_time)
    app_context.set_value('probe_ids', probe_ids)
    app_context.set_value('search_item_list', search_item_list)
    app_context.set_value('full_path_and_filename', full_path_and_filename)
    app_context.set_value('socket_path', socket_path)
    app_context.set_value('nn_fps_counter', nn_fps_counter)
    app_context.set_value('rear_csi_fps_counter', rear_csi_fps_counter)
    app_context.set_value('front_csi_fps_counter', front_csi_fps_counter)
    app_context.set_value('overlay_parts', overlay_parts)
    app_context.set_value('monitoring_thread', monitoring_thread)
    app_context.set_value('overlay_thread', overlay_thread)
    app_context.set_value('server_thread', server_thread)
    app_context.set_value('stop_event', stop_event)
    
    # Check for systemd service file (EXACT CHECK from old)
    if os.path.isfile('/etc/systemd/system/bucher-smart-sweeper.service'):
        logger.debug('Service file found at /etc/systemd/system/bucher-smart-sweeper.service')
    
    # STEP 15: Build GStreamer pipeline
    logger.debug('Building GStreamer pipeline...')
    notify_systemd('STATUS=Building pipeline', app_context)
    
    # Import here to avoid circular imports
    from pipeline.builder import build_pipeline
    
    pipeline = build_pipeline(app_context)
    if not pipeline:
        logger.error('Failed to create pipeline')
        notify_systemd('STATUS=ERROR', app_context)
        sys.exit(-1)
    
    app_context.set_value('pipeline', pipeline)
    logger.debug('Pipeline built successfully')
    
    # STEP 16: Set up bus callback (EXACT ORDER)
    logger.debug('Setting up bus watch...')
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    loop = GLib.MainLoop()
    app_context.set_value('main_loop', loop)
    bus.connect('message', bus_call, loop)
    
    ctrl_c_count = [0]
    
    # STEP 17: Define signal handler (EXACT BEHAVIOR from old)
    def signal_handler(sig, frame):
        logger.debug('############### CTRL+C pressed ##########################')
        pipeline = app_context.get_value('pipeline')
        ctrl_c_count[0] += 1
        
        if ctrl_c_count[0] == 1:
            # First CTRL+C: Graceful shutdown
            can_client = app_context.get_value('can_client')
            can_client.stop_logging()
            can_client.disconnect()
            mt = app_context.get_value('monitoring_thread')
            mt.join(timeout=0.1)
            
            # Generate DOT file
            timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
            logger.debug(f"dot file path -> {os.environ.get('GST_DEBUG_DUMP_DOT_DIR', '/tmp')}/python_ROI_{timestamp}.dot")
            Gst.debug_bin_to_dot_file(pipeline, Gst.DebugGraphDetails.ALL, f'python_{timestamp}')
            logger.debug(f"Creating symlink to latest dot file")
            os.system(f"/usr/bin/ln -sf {os.environ.get('GST_DEBUG_DUMP_DOT_DIR', '/tmp')}/python_ROI_{timestamp}.dot {os.environ.get('SCRIPT_EXECUTION_DIR', '/tmp')}/python_nozzlenet_latest.dot")
            
            time.sleep(1)
            app_context.set_value('shutdown_initiated_by_user_process', True)
            logger.debug('Sending EOS event to the pipeline')
            
            # Send EOS to streammux
            streammux = pipeline.get_by_name('multi_nvargus_streammux')
            replaced_pads = app_context.get_value('replacement_pads')
            if replaced_pads:
                for pad in replaced_pads:
                    sink_pad = streammux.get_static_pad(f'{pad}')
                    sink_pad.send_event(Gst.Event.new_eos())
            
            pipeline.send_event(Gst.Event.new_eos())
            Gst.debug_bin_to_dot_file(pipeline, Gst.DebugGraphDetails.ALL, f'python_post_EOS_{timestamp}')
        
        elif ctrl_c_count[0] >= 2:
            # Second CTRL+C: Force exit
            logger.debug('CTRL+C pressed at least twice. Forcing exit.')
            notify_systemd('STOPPING=1', app_context)
            if pipeline.set_state(Gst.State.NULL) == Gst.StateChangeReturn.FAILURE:
                logger.debug('Failed to stop the pipeline, attempting to kill the process.')
                os.kill(app_context.get_int('main_process_id').value, signal.SIGKILL)
            else:
                logger.debug('Pipeline stopped successfully on second CTRL+C press!')
                loop.quit()
        else:
            ctrl_c_count[0] = 2
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # STEP 18: Set pipeline to PLAYING (EXACT ORDER and notifications)
    notify_systemd('STATUS=Setting pipeline to PLAYING state', app_context)
    pipeline.set_state(Gst.State.PLAYING)
    
    # STEP 19: Start monitoring threads (EXACT ORDER)
    monitoring_thread.start()
    overlay_thread.start()
    
    # STEP 20: Notify systemd ready
    notify_systemd('STATUS=Ready to Roll...', app_context)
    notify_systemd('READY=1', app_context)
    notify_systemd('STATUS=ROLLING', app_context)
    
    # STEP 21: Connect CAN client (EXACT ORDER)
    can_client.connect()
    if can_client.connected:
        print('CAN client connected, starting logging...')
        can_client.start_logging()
    else:
        print('Failed to connect to CAN bus, continuing without CAN logging...')
    
    # STEP 22: Start unix socket server if in systemd mode (EXACT CHECK)
    if app_context.get_value('SSWP_RUN_MODE') == 'SYSTEMD_NOTIFY_SERVICE':
        logger.debug('Setting up the custom unix signal handler to capture stop signals')
        server_thread.start()
    
    # STEP 23: Run main loop
    try:
        loop.run()
    except Exception as err:
        print(f'Error: {err}')
    
    # STEP 24: Cleanup (EXACT ORDER)
    logger.debug('Cleanup')
    notify_systemd('STATUS=Stopping...', app_context)
    notify_systemd('STOPPING=1', app_context)
    
    if pipeline and pipeline.get_state(Gst.CLOCK_TIME_NONE)[1] != Gst.State.NULL:
        pipeline.set_state(Gst.State.NULL)
    
    logger.debug(f"App context: shutdown initiated by user process = {app_context.get_boolean('shutdown_initiated_by_user_process').value}")
    logger.debug(f"App context: process_id = {app_context.get_int('main_process_id').value}")
    logger.debug(f"App context: pid_path = {app_context.get_string('pid_path')}")
    
    app_context.free()
    
    if app_context.get_value('SSWP_RUN_MODE') == 'SYSTEMD_NOTIFY_SERVICE':
        server_thread.join()
    
    logger.info('Application terminated')