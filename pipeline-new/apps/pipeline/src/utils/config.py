"""
Configuration Management
Load and access configuration from YAML files
"""
import yaml
import subprocess
from pathlib import Path


class Configuration:
    """
    Configuration manager for pipeline settings
    Loads logging_config.yaml and provides access to all settings
    """
    
    def __init__(self, config_file=None):
        """
        Initialize configuration
        
        :param config_file: Path to logging_config.yaml (optional)
                           If None, uses default location relative to monorepo root
        """
        if config_file is None:
            # Default to monorepo structure
            current_file = Path(__file__).resolve()
            pipeline_root = current_file.parents[2]  # apps/pipeline/
            config_file = pipeline_root / "config" / "logging_config.yaml"
        
        self.config_file = Path(config_file)
        
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        with open(self.config_file, 'r') as file:
            self.config = yaml.safe_load(file)
    
    def get(self, key):
        """Get top-level config key"""
        return self.config.get(key)
    
    def get_camera_columns(self):
        """Get camera signal column names for CSV logging"""
        return self.get('signal_settings').get('camera_signals')
    
    def get_can_signals(self):
        """Get CAN signal column names"""
        return self.get('signal_settings').get('can_signals')
    
    def get_columns(self):
        """Get all CAN signal columns"""
        signal_settings = self.get('signal_settings')
        can_signals = signal_settings.get('can_signals')
        return can_signals
    
    def get_directory(self):
        """Get logging directory path"""
        return self.get('logging_settings')[2].get('logged_data_dir')
    
    def get_log_duration(self):
        """Get maximum log duration in seconds"""
        return self.get('logging_settings')[1].get('max_log_duration')
    
    def get_pm_columns(self):
        """Get particulate matter sensor column names"""
        return self.get('signal_settings').get('pm_signals')
    
    def get_serial_number(self):
        """Get vehicle serial number"""
        return self.get('vehicle_info')[0].get('serial_number')
    
    def get_csi_columns(self):
        """Get CSI (Clean Street Index) column names"""
        return self.get('signal_settings').get('csi_signals')
    
    def get_camera_id(self, camera_name):
        """
        Get camera ID by name
        
        :param camera_name: Name of camera (e.g., 'front', 'back', 'right_nozzle')
        :return: Camera ID string or None
        """
        camera_info = self.get('camera_info')
        for camera in camera_info:
            if camera_name in camera:
                return camera[f'{camera_name}'][0]['id']
        return None
    
    def get_video_device(self, camera_id):
        """
        Get /dev/video* path for camera with given ID
        
        :param camera_id: Camera device tree node ID
        :return: Path to /dev/video* or None
        """
        try:
            result = subprocess.run(
                ['v4l2-ctl', '--list-devices'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            
            lines = result.stdout.splitlines()
            for i, line in enumerate(lines):
                if camera_id in line:
                    # Next line contains /dev/video* path
                    if i + 1 < len(lines):
                        return lines[i + 1].strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return None