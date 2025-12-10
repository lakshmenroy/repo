#!/usr/bin/env python3
"""
SmartAssist Pipeline Application
Main entry point for AI inference pipeline

Author: Ganindu Nanayakkara
Modified for monorepo structure
"""
import sys
import os
import signal
import threading
import yaml
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

# Global loop
loop = None


def signal_handler(sig, frame):
    """
    Handle SIGINT (Ctrl+C) and SIGTERM signals
    Gracefully shutdown pipeline
    """
    global loop
    logger = app_context.get_value('app_context_v2').logger
    
    ctrl_c_count = app_context.get_value('ctrl_c_count')
    if ctrl_c_count is None:
        ctrl_c_count = [0]
        app_context.set_value('ctrl_c_count', ctrl_c_count)
    
    ctrl_c_count[0] += 1
    
    if ctrl_c_count[0] == 1:
        logger.info('SIGINT/SIGTERM received. Stopping pipeline gracefully...')
        notify_systemd('STOPPING=1', app_context)
        
        pipeline = app_context.get_value('pipeline')
        if pipeline:
            pipeline.send_event(Gst.Event.new_eos())
        
        if loop:
            GLib.timeout_add_seconds(5, lambda: loop.quit())
    
    elif ctrl_c_count[0] >= 2:
        logger.warning('Second signal received. Forcing exit.')
        notify_systemd('STOPPING=1', app_context)
        
        pipeline = app_context.get_value('pipeline')
        if pipeline and pipeline.set_state(Gst.State.NULL) == Gst.StateChangeReturn.FAILURE:
            logger.error('Failed to stop pipeline. Attempting to kill process.')
            os.kill(app_context.get_int('main_process_id').value, signal.SIGKILL)
        else:
            logger.info('Pipeline stopped successfully.')
            if loop:
                loop.quit()


def bus_call(bus, message, loop):
    """
    GStreamer bus message handler
    """
    logger = app_context.get_value('app_context_v2').logger
    mtype = message.type
    
    if mtype == Gst.MessageType.EOS:
        logger.info('End-of-stream received')
        loop.quit()
    
    elif mtype == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        logger.error(f'Error: {err}, Debug: {debug}')
        loop.quit()
    
    elif mtype == Gst.MessageType.WARNING:
        warn, debug = message.parse_warning()
        logger.warning(f'Warning: {warn}, Debug: {debug}')
    
    elif mtype == Gst.MessageType.STATE_CHANGED:
        old_state, new_state, pending = message.parse_state_changed()
        if message.src == app_context.get_value('pipeline'):
            logger.debug(f'Pipeline state changed: {old_state.value_nick} -> {new_state.value_nick}')
    
    return True


def initialize_application_context():
    """
    Initialize application context and load configurations
    """
    notify_systemd('STATUS=Initializing application context', app_context)
    
    # Determine run mode
    run_mode = os.environ.get('SSWP_RUN_MODE', 'STANDALONE')
    app_context.set_value('SSWP_RUN_MODE', run_mode)
    app_context.set_value('main_process_id', os.getpid())
    
    # Load camera configuration
    camera_config_path = '/mnt/ssd/csi_pipeline/config/bucher_camera_on_boot_config.json'
    config = Config(camera_config_path)
    actx = AppContext(config)
    actx.initialise_logging()
    actx.logger.info(f'Starting pipeline. PID: {os.getpid()}')
    app_context.set_value('app_context_v2', actx)
    
    # Load pipeline configuration
    pipeline_config_path = '/mnt/ssd/csi_pipeline/config/nozzlenet_config.yaml'
    with open(pipeline_config_path, 'r') as f:
        pipeline_config = yaml.safe_load(f)
    
    if pipeline_config is None:
        actx.logger.error('Failed to load pipeline config. Fatal error.')
        notify_systemd('STATUS=ERROR', app_context)
        sys.exit(1)
    
    # Extract DeepStream config paths
    config_paths_dict = {}
    ds_configs = pipeline_config.get('ds_configs', {})
    for config_type, configs in ds_configs.items():
        config_paths_dict[config_type] = configs
        actx.logger.debug(f'Config[{config_type}] = {configs}')
    
    # Verify essential configs exist
    essential_configs = ['preprocess', 'inference', 'metamux', 'tracker']
    for config_type in essential_configs:
        if config_type not in config_paths_dict:
            actx.logger.error(f'Missing essential config: {config_type}')
            notify_systemd('STATUS=ERROR', app_context)
            sys.exit(1)
        
        config_path = config_paths_dict[config_type]['path']
        if not os.path.isfile(config_path):
            actx.logger.error(f'Config file not found: {config_path}')
            notify_systemd('STATUS=ERROR', app_context)
            sys.exit(1)
    
    app_context.set_value('config_paths', config_paths_dict)
    
    # Load camera initialization status
    if load_latest_init_status('bucher_ai_camera_status_on_bucher-d3-camera-init_service_run', app_context) != 0:
        actx.logger.error('Failed to load camera init status')
        notify_systemd('STATUS=ERROR', app_context)
        sys.exit(1)
    
    # Initialize logging config
    log_config = Configuration()
    serial_number = log_config.get_serial_number()
    log_duration = log_config.get_log_duration()
    camera_columns = log_config.get_camera_columns()
    csi_columns = log_config.get_csi_columns()
    
    # Initialize CAN client and state machine
    can_client = CanClient(client_name='pipeline_w_logging.py')
    state_machine = SmartStateMachine()
    
    # Initialize FPS counters
    nn_fps_counter = GETFPS(0)
    front_csi_fps_counter = GETFPS(0)
    rear_csi_fps_counter = GETFPS(0)
    
    # Store in context
    app_context.set_value('can_client', can_client)
    app_context.set_value('state_machine', state_machine)
    app_context.set_value('serial_number', serial_number)
    app_context.set_value('log_duration', log_duration)
    app_context.set_value('camera_columns', camera_columns)
    app_context.set_value('csi_columns', csi_columns)
    app_context.set_value('nn_fps_counter', nn_fps_counter)
    app_context.set_value('front_csi_fps_counter', front_csi_fps_counter)
    app_context.set_value('rear_csi_fps_counter', rear_csi_fps_counter)
    app_context.set_value('shutdown_initiated_by_user_process', False)
    app_context.set_value('last_notificationsent_to_systemd', '')
    
    # Overlay parts for OSD
    overlay_parts = {
        'sm_nozzle_state': 0, 'sm_fan_speed': 0, 'sm_current_status': 'N/A',
        'sm_current_state': 'N/A', 'sm_time_difference': 0, 'sm_ao_status': 'N/A',
        'sm_ao_difference': 0, 's1_pm10': 'N/A', 's2_pm10': 'N/A', 's3_pm10': 'N/A',
        's4_pm10': 'N/A', 's5_pm10': 'N/A'
    }
    app_context.set_value('overlay_parts', overlay_parts)
    
    return actx


def main():
    """
    Main application entry point
    """
    global loop
    
    # Initialize context
    actx = initialize_application_context()
    logger = actx.logger
    
    notify_systemd('STATUS=Creating pipeline', app_context)
    
    # Import pipeline builder (deferred to avoid circular imports)
    from pipeline.builder import build_pipeline
    
    # Build GStreamer pipeline
    pipeline = build_pipeline(app_context)
    if not pipeline:
        logger.error('Failed to create pipeline')
        notify_systemd('STATUS=ERROR', app_context)
        return -1
    
    app_context.set_value('pipeline', pipeline)
    
    # Setup bus watch
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    loop = GLib.MainLoop()
    bus.connect('message', bus_call, loop)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start background threads
    stop_event = threading.Event()
    monitoring_thread = threading.Thread(target=override_monitoring, args=(app_context,), daemon=True)
    overlay_thread = threading.Thread(target=overlay_parts_fetcher, args=(app_context,), daemon=True)
    
    monitoring_thread.start()
    overlay_thread.start()
    
    # Start Unix socket server if in systemd mode
    if app_context.get_value('SSWP_RUN_MODE') == 'SYSTEMD_NOTIFY_SERVICE':
        socket_path = '/tmp/smart_sweeper_pipeline_comms_socket'
        server_thread = threading.Thread(
            target=unix_socket_server,
            args=(socket_path, stop_event, app_context),
            daemon=True
        )
        server_thread.start()
        app_context.set_value('server_thread', server_thread)
        app_context.set_value('stop_event', stop_event)
    
    # Connect to CAN server
    can_client = app_context.get_value('can_client')
    if can_client.connect():
        logger.info('CAN client connected. Starting logging.')
        can_client.start_logging()
    else:
        logger.warning('Failed to connect to CAN bus. Continuing without CAN.')
    
    # Start pipeline
    notify_systemd('STATUS=Starting pipeline', app_context)
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        logger.error('Unable to set pipeline to PLAYING state')
        return -1
    
    notify_systemd('READY=1', app_context)
    notify_systemd('STATUS=Pipeline running', app_context)
    logger.info('Pipeline started successfully')
    
    # Run main loop
    try:
        loop.run()
    except KeyboardInterrupt:
        logger.info('Interrupted by user')
    except Exception as e:
        logger.error(f'Error in main loop: {e}', exc_info=True)
    
    # Cleanup
    logger.info('Stopping pipeline...')
    notify_systemd('STOPPING=1', app_context)
    
    if pipeline:
        pipeline.set_state(Gst.State.NULL)
    
    if can_client:
        can_client.disconnect()
    
    if app_context.get_value('SSWP_RUN_MODE') == 'SYSTEMD_NOTIFY_SERVICE':
        stop_event.set()
        server_thread = app_context.get_value('server_thread')
        if server_thread:
            server_thread.join(timeout=2)
    
    logger.info('Application terminated')
    return 0


if __name__ == '__main__':
    sys.exit(main())