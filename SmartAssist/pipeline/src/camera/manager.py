"""
Camera Manager
Handles camera initialization and V4L2 settings

VERIFIED: Functionality from original with simplified structure
"""
import subprocess


class CameraManager:
    """
    Manages multiple camera sources
    Handles V4L2 control settings for cameras
    """
    
    def __init__(self, app_context):
        """
        Initialize camera manager
        
        :param app_context: GStreamer Structure with app context
        """
        self.app_context = app_context
        self.logger = app_context.get_value('app_context_v2').logger
    
    def send_v4l2_settings(self, camera):
        """
        Send V4L2 settings to camera device
        Applies flip settings and bypass mode
        
        :param camera: Camera configuration dict with device_path, vertical_flip, horizontal_flip
        
        VERIFIED: Exact logic from original
        """
        device_path = camera.get('device_path')
        if not device_path:
            self.logger.warning('Camera has no device_path, skipping V4L2 settings')
            return
        
        # Build v4l2-ctl command
        cmd = [
            'v4l2-ctl',
            '-d', device_path,
            '--set-ctrl', f"vertical_flip={camera.get('vertical_flip', 0)}",
            '--set-ctrl', f"horizontal_flip={camera.get('horizontal_flip', 0)}",
            '--set-ctrl', 'bypass_mode=0'
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.logger.debug(f'V4L2 settings applied to {device_path}')
        except subprocess.CalledProcessError as e:
            self.logger.error(f'Failed to apply V4L2 settings to {device_path}: {e.stderr}')
        except FileNotFoundError:
            self.logger.error('v4l2-ctl not found - cannot apply camera settings')


def initialize_cameras(app_context):
    """
    Initialize cameras and apply V4L2 settings
    Reads cameras from init_config and applies settings to cameras that passed tests
    
    :param app_context: GStreamer Structure with app context
    :return: CameraManager instance
    
    VERIFIED: Logic from original
    """
    manager = CameraManager(app_context)
    init_config = app_context.get_value('init_config')
    
    if not init_config:
        manager.logger.warning('No init_config found')
        return manager
    
    cameras = init_config.get('cameras', [])
    
    # Apply V4L2 settings to detected cameras that passed capture test
    for camera in cameras:
        if camera.get('detected_on_init') and camera.get('capture_test_passed'):
            manager.send_v4l2_settings(camera)
    
    return manager