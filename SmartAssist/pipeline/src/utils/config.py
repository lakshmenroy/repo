"""
Configuration Management
Loads and provides access to logging_config.yaml settings

VERIFIED: Exact functionality from original pipeline with smart path detection
"""
import yaml
import subprocess
from .paths import get_config_path


class Configuration:
    """
    Configuration manager for pipeline settings
    Loads logging_config.yaml and provides access to all settings
    
    VERIFIED: All methods match original utils.py Configuration class
    """
    
    def __init__(self, config_file=None):
        """
        Initialize configuration from YAML file
        
        :param config_file: Path to logging_config.yaml (auto-detected if None)
        """
        if config_file is None:
            # Use smart path detection
            try:
                config_file = get_config_path("logging_config.yaml")
            except:
                # Fallback to old hardcoded path
                config_file = '/mnt/ssd/csi_pipeline/config/logging_config.yaml'
        
        with open(config_file, 'r') as file:
            self.config = yaml.safe_load(file)
    
    def get(self, key):
        """
        Get top-level config key
        
        :param key: Config key name
        :return: Config value
        """
        return self.config.get(key)
    
    def get_camera_columns(self):
        """
        Get camera signal column names for CSV logging
        
        :return: List of camera signal column names
        """
        return self.get('signal_settings').get('camera_signals')
    
    def get_can_signals(self):
        """
        Get CAN signal column names
        
        :return: List of CAN signal column names
        """
        return self.get('signal_settings').get('can_signals')
    
    def get_columns(self):
        """
        Get all CAN signal columns
        
        :return: List of CAN signal column names
        """
        signal_settings = self.get('signal_settings')
        can_signals = signal_settings.get('can_signals')
        return can_signals
    
    def get_directory(self):
        """
        Get logging directory path
        
        :return: Directory path for CSV/video output
        """
        return self.get('logging_settings')[2].get('logged_data_dir')
    
    def get_log_duration(self):
        """
        Get maximum log duration in seconds
        Files rotate after this duration
        
        :return: Log duration in seconds (e.g., 1200 = 20 minutes)
        """
        return self.get('logging_settings')[1].get('max_log_duration')
    
    def get_pm_columns(self):
        """
        Get particulate matter sensor column names
        
        :return: List of PM sensor column names
        """
        return self.get('signal_settings').get('pm_signals')
    
    def get_serial_number(self):
        """
        Get vehicle serial number
        
        :return: Serial number string (e.g., 'SN217841')
        """
        return self.get('vehicle_info')[0].get('serial_number')
    
    def get_csi_columns(self):
        """
        Get CSI (Clean Street Index) column names
        
        :return: List of CSI column names
        """
        return self.get('signal_settings').get('csi_signals')
    
    def get_camera_id(self, camera_name):
        """
        Get camera ID from camera name
        
        :param camera_name: Camera name ('front', 'back', 'left_nozzle', 'right_nozzle')
        :return: Camera ID string (e.g., '43-0021') or None
        """
        camera_info = self.get('camera_info')
        for camera in camera_info:
            if camera_name in camera:
                return camera[f'{camera_name}'][0]['id']
        return None
    
    def get_video_device(self, camera_id):
        """
        Get /dev/video* device path for camera with given ID
        Uses v4l2-ctl to query available video devices
        
        :param camera_id: Camera ID string (e.g., '43-0021')
        :return: Video device path (e.g., '/dev/video0') or None
        """
        # Run the v4l2-ctl --list-devices command
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                              capture_output=True, text=True)
        
        # Split the output into lines
        lines = result.stdout.splitlines()
        for i, line in enumerate(lines):
            if camera_id in line:
                # Device path is on next line
                return lines[i + 1].strip()
        
        # Camera ID not found
        return None