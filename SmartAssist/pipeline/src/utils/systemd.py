"""
Systemd Integration
Handles systemd notifications and service management

VERIFIED: Exact functionality from original pipeline_w_logging.py
"""
import os
import socket
import glob
import json
from datetime import datetime


def notify_systemd(msg='READY=1', app_context=None):
    """
    Notifies the systemd service manager
    Prevents duplicate notifications
    
    :param msg: Message to send (e.g., 'READY=1', 'STATUS=...', 'STOPPING=1')
    :param app_context: GStreamer Structure with app context (optional)
    
    VERIFIED: Exact logic from original
    """
    if app_context:
        # Get logger and mode from app context
        logger = app_context.get_value('app_context_v2').logger
        mode = app_context.get_value('SSWP_RUN_MODE')
        
        # Only notify if running as systemd service
        if mode != 'SYSTEMD_NOTIFY_SERVICE':
            logger.debug(f'Mode is not SYSTEMD_NOTIFY_SERVICE, skipping notification to systemd: {msg}')
            return
        
        # Prevent duplicate notifications
        last_notification = app_context.get_value('last_notificationsent_to_systemd')
        if last_notification != msg:
            logger.debug(f'Sending notification to systemd: {msg}')
            systemd_notifier(msg)
            app_context.set_value('last_notificationsent_to_systemd', msg)
        else:
            logger.debug(f'Duplicate notification to systemd: {msg}, skipping...')
    else:
        # No app context - just send notification
        systemd_notifier(msg)


def systemd_notifier(msg='READY=1'):
    """
    Send notification to systemd via NOTIFY_SOCKET
    Low-level systemd communication
    
    :param msg: Notification message (default: 'READY=1')
    
    VERIFIED: Exact logic from original
    """
    if 'NOTIFY_SOCKET' in os.environ:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
                address = os.environ['NOTIFY_SOCKET']
                # Handle abstract socket (starts with '@')
                if address[0] == '@':
                    address = '\x00' + address[1:]
                sock.sendto(msg.encode('utf-8'), address)
        except Exception as e:
            # Silently fail - systemd not available
            pass


def load_latest_init_status(base_filename, app_context=None):
    """
    Load the latest initialization status from a file matching a pattern in /tmp
    Used to load camera initialization results from bucher-d3-camera-init service
    
    :param base_filename: Base filename pattern to search for
                         (e.g., 'bucher-d3-camera-init')
    :param app_context: GStreamer Structure with app context (optional)
    :return: 0 on success, -1 on failure
    
    VERIFIED: Exact logic from original
    """
    # Get logger if app context available
    if app_context:
        logger = app_context.get_value('app_context_v2').logger
    else:
        logger = None
    
    # Search for files matching pattern
    pattern = f'/tmp/{base_filename}_*.json'
    if logger:
        logger.debug(f'Searching for files matching pattern {pattern}')
    
    files = glob.glob(pattern)
    if not files:
        if logger:
            logger.error(f'No files found for pattern {base_filename}. This is a fatal error.')
        else:
            print(f'ERROR: No files found for pattern {pattern}')
        return -1
    
    def extract_datetime(filename):
        """Extract datetime from filename timestamp"""
        timestamp_str = filename.split('_')[-1].rstrip('.json')
        return datetime.strptime(timestamp_str, '%Y%m%d%H%M')
    
    # Find the latest file
    latest_file = max(files, key=lambda x: extract_datetime(x))
    if logger:
        logger.debug(f'Latest file found: {latest_file}')
    else:
        print(f'Loading init status from: {latest_file}')
    
    # Load and store in app context
    try:
        with open(latest_file, 'r') as f:
            content = json.load(f)
            if app_context:
                app_context.set_value('init_config', content)
            return 0
    except Exception as e:
        if logger:
            logger.error(f'Error loading init status file: {e}')
        else:
            print(f'ERROR: Failed to load {latest_file}: {e}')
        return -1