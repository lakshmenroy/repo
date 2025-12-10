"""
Systemd Integration
Handles systemd notifications and service management
"""
import os
import socket
import glob
import json
from datetime import datetime


def notify_systemd(msg='READY=1', app_context=None):
    """
    Notifies the systemd service manager
    
    :param msg: Message to send (e.g., 'READY=1', 'STATUS=...', 'STOPPING=1')
    :param app_context: Application context (optional)
    """
    if app_context:
        logger = app_context.get_value('app_context_v2').logger
        mode = app_context.get_value('SSWP_RUN_MODE')
        if mode != 'SYSTEMD_NOTIFY_SERVICE':
            logger.debug(f'Mode is not SYSTEMD_NOTIFY_SERVICE, skipping: {msg}')
            return
        
        last_notification = app_context.get_value('last_notificationsent_to_systemd')
        if last_notification != msg:
            logger.debug(f'Sending notification to systemd: {msg}')
            systemd_notifier(msg)
            app_context.set_value('last_notificationsent_to_systemd', msg)
        else:
            logger.debug(f'Duplicate notification to systemd: {msg}, skipping')
    else:
        systemd_notifier(msg)


def systemd_notifier(msg='READY=1'):
    """
    Send notification to systemd via NOTIFY_SOCKET
    
    :param msg: Notification message (default: 'READY=1')
    """
    if 'NOTIFY_SOCKET' in os.environ:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
                address = os.environ['NOTIFY_SOCKET']
                if address[0] == '@':
                    address = '\x00' + address[1:]
                sock.sendto(msg.encode('utf-8'), address)
        except Exception as e:
            print(f'Error notifying systemd: {e}')


def load_latest_init_status(base_filename, app_context=None):
    """
    Load the latest initial status from a file matching a pattern in /tmp
    
    :param base_filename: Base filename pattern to search for
    :param app_context: Application context
    :return: 0 on success, -1 on failure
    """
    if app_context:
        logger = app_context.get_value('app_context_v2').logger
    else:
        logger = None
    
    pattern = f'/tmp/{base_filename}_*.json'
    if logger:
        logger.debug(f'Searching for files matching pattern {pattern}')
    
    files = glob.glob(pattern)
    if not files:
        if logger:
            logger.error(f'No files found for pattern {base_filename}. Fatal error.')
        return -1

    def extract_datetime(filename):
        timestamp_str = filename.split('_')[-1].rstrip('.json')
        return datetime.strptime(timestamp_str, '%Y%m%d%H%M')
    
    latest_file = max(files, key=lambda x: extract_datetime(x))
    if logger:
        logger.debug(f'Latest file found: {latest_file}')
    
    with open(latest_file, 'r') as f:
        content = json.load(f)
        if app_context:
            app_context.set_value('init_config', content)
        return 0