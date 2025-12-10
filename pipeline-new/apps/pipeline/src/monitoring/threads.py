"""
Monitoring Threads
Background threads for system monitoring and overlay updates
"""
import time
import threading
import socket
import json
import os
import signal


def overlay_parts_fetcher(app_context):
    """
    Fetch overlay data for OSD display
    Updates overlay information from CAN client
    
    :param app_context: Application context
    """
    can_client = app_context.get_value('can_client')
    print('[THREAD] Starting overlay_parts_fetcher', flush=True)
    
    while True:
        try:
            # Fetch data from CAN client
            if can_client and can_client.connected:
                # Get PM sensor values
                pm_values = {}
                for sensor_id in range(1, 6):
                    result = can_client.get_pm_values(sensor_id)
                    if result:
                        pm_values[f's{sensor_id}_pm10'] = result.get('pm10', 'N/A')
                
                # Update overlay parts
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
    
    :param app_context: Application context
    """
    can_client = app_context.get_value('can_client')
    print('[THREAD] Starting override_monitoring', flush=True)
    
    while True:
        try:
            if can_client and can_client.connected:
                override_state = can_client.get_override_state()
                if override_state:
                    # Handle override state
                    pass
            
            time.sleep(5)
        except Exception as e:
            print(f'Error in override_monitoring: {e}')
            time.sleep(5)


def unix_socket_server(socket_path, stop_event, app_context):
    """
    Unix socket server for inter-process communication
    Allows external control of the pipeline
    
    :param socket_path: Path to Unix socket
    :param stop_event: Threading event to signal shutdown
    :param app_context: Application context
    """
    logger = app_context.get_value('app_context_v2').logger
    
    # Remove existing socket
    if os.path.exists(socket_path):
        os.unlink(socket_path)
    
    # Create socket
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_socket.bind(socket_path)
    server_socket.listen(1)
    os.chmod(socket_path, 0o666)
    
    logger.info(f'Unix socket server listening on {socket_path}')
    
    while not stop_event.is_set():
        try:
            server_socket.settimeout(1.0)
            try:
                client_socket, _ = server_socket.accept()
            except socket.timeout:
                continue
            
            logger.debug('Client connected to Unix socket')
            
            # Handle client commands
            data = client_socket.recv(1024)
            if data:
                try:
                    command = json.loads(data.decode('utf-8'))
                    logger.debug(f'Received command: {command}')
                    
                    if command.get('action') == 'stop':
                        logger.info('Stop command received via Unix socket')
                        app_context.set_value('shutdown_initiated_by_user_process', True)
                        
                        # Send SIGINT to main process
                        main_pid = app_context.get_int('main_process_id').value
                        os.kill(main_pid, signal.SIGINT)
                        
                        response = {'status': 'success', 'message': 'Stop signal sent'}
                    else:
                        response = {'status': 'error', 'message': 'Unknown command'}
                    
                    client_socket.send(json.dumps(response).encode('utf-8'))
                except json.JSONDecodeError:
                    logger.error('Invalid JSON received')
            
            client_socket.close()
            
        except Exception as e:
            logger.error(f'Error in Unix socket server: {e}')
    
    server_socket.close()
    os.unlink(socket_path)
    logger.info('Unix socket server stopped')