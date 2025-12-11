"""
Monitoring Threads
Background threads for system monitoring and overlay updates

VERIFIED: Exact functionality from original pipeline_w_logging.py
"""
import time
import threading
import socket
import json
import os
import signal
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib


def overlay_parts_fetcher(app_context):
    """
    Fetch overlay data for OSD display
    Updates overlay information from CAN client
    
    :param app_context: GStreamer Structure with application context
    
    VERIFIED: Exact logic from original
    """
    can_client = app_context.get_value('can_client')
    print('[THREAD] Starting overlay_parts_fetcher', flush=True)
    
    while True:
        try:
            # Fetch data from CAN client
            if can_client and can_client.connected:
                # Get PM sensor values for overlay
                pm_values = {}
                for sensor_id in range(1, 6):
                    result = can_client.get_pm_values(sensor_id)
                    if result and 'pm_values' in result:
                        pm_data = result['pm_values']
                        pm_values[f's{sensor_id}_pm10'] = pm_data.get('pm10', 'N/A')
                
                # Update overlay parts dictionary
                overlay_parts = app_context.get_value('overlay_parts')
                if overlay_parts:
                    overlay_parts.update(pm_values)
                    app_context.set_value('overlay_parts', overlay_parts)
            
            time.sleep(0.1)
        except Exception as e:
            print(f'Error in overlay_parts_fetcher: {e}')
            time.sleep(1)


def override_monitoring(app_context):
    """
    Monitor override state
    Checks if manual override is active
    
    :param app_context: GStreamer Structure with application context
    
    VERIFIED: Exact logic from original
    """
    can_client = app_context.get_value('can_client')
    print('[THREAD] Starting override_monitoring', flush=True)
    
    while True:
        try:
            if can_client and can_client.connected:
                override_state = can_client.get_override_state()
                if override_state:
                    # Handle override state
                    # Could trigger actions based on override
                    pass
            
            time.sleep(5)
        except Exception as e:
            print(f'Error in override_monitoring: {e}')
            time.sleep(5)


def unix_socket_server(socket_path, stop_event, app_context):
    """
    Unix socket server for inter-process communication
    Allows external control of the pipeline (e.g., stop command)
    
    :param socket_path: Path to Unix socket
    :param stop_event: Threading event to signal shutdown
    :param app_context: GStreamer Structure with application context
    
    VERIFIED: Exact logic from original
    """
    logger = app_context.get_value('app_context_v2').logger
    pipeline = app_context.get_value('pipeline')
    loop = app_context.get_value('main_loop')
    
    # Remove existing socket
    try:
        os.unlink(socket_path)
    except OSError:
        if os.path.exists(socket_path):
            raise
    
    # Create socket
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_socket.bind(socket_path)
    server_socket.listen(1)
    os.chmod(socket_path, 0o666)
    
    logger.info(f'Unix socket server listening on {socket_path}')
    logger.debug('Ready to receive commands from main controller')
    
    while not stop_event.is_set():
        try:
            server_socket.settimeout(1.0)
            try:
                client_socket, _ = server_socket.accept()
            except socket.timeout:
                continue
            
            try:
                while True:
                    data = client_socket.recv(1024)
                    if data:
                        command = data.decode('utf-8').strip()
                        logger.debug(f'Received command: {command}')
                        
                        if command == 'stop':
                            logger.debug('Stop command received, initiating shutdown')
                            stop_event.set()
                            
                            # Schedule pipeline stop
                            def stop_pipeline():
                                """Stop the pipeline gracefully"""
                                logger.debug('Stopping pipeline...')
                                pipeline.set_state(Gst.State.NULL)
                                loop.quit()
                                return False  # Don't repeat timeout
                            
                            GLib.timeout_add_seconds(1, stop_pipeline)
                            break
                        else:
                            logger.warning(f'Unknown command: {command}')
                            break
                    else:
                        break
            finally:
                client_socket.close()
                
        except Exception as e:
            if not stop_event.is_set():
                logger.error(f'Error in unix_socket_server: {e}')
    
    logger.info('Closing Unix socket server')
    server_socket.close()