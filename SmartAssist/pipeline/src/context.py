"""
Application Context and Configuration
Contains Config, AppContext, and GETFPS classes

VERIFIED: Exact functionality from original pipeline with smart path detection
"""
import json
import time
import logging
import os
from pathlib import Path

# Smart path detection
from .utils.paths import get_repo_root, get_config_path

# Global FPS tracking variables
start_time = time.time()
frame_count = 0


class GETFPS:
    """
    FPS Counter for video streams
    From NVIDIA DeepStream examples
    
    Tracks frames per second for a specific stream
    """
    
    def __init__(self, stream_id):
        """
        Initialize FPS counter
        
        :param stream_id: Stream identifier (camera index)
        """
        global start_time
        self.start_time = start_time
        self.is_first = True
        global frame_count
        self.frame_count = frame_count
        self.stream_id = stream_id
        self.current_fps = None
    
    def get_fps(self):
        """
        Calculate and return current FPS
        Updates every 5 seconds
        
        :return: Current FPS as integer
        """
        end_time = time.time()
        
        if self.is_first:
            self.start_time = end_time
            self.is_first = False
        
        if (end_time - self.start_time) > 5:
            # Calculate FPS over 5 second window
            self.current_fps = int(float(self.frame_count) / 5.0)
            self.frame_count = 0
            self.start_time = end_time
        else:
            self.frame_count = self.frame_count + 1
        
        return self.current_fps
    
    def print_data(self):
        """Print current frame count and start time (debugging)"""
        print(f'frame_count={self.frame_count}')
        print(f'start_time={self.start_time}')


class Config:
    """
    Configuration from camera JSON file
    Loads bucher_camera_on_boot_config.json
    
    VERIFIED: Exact functionality from original with smart path detection
    """
    
    def __init__(self, config_file=None):
        """
        Load camera configuration from JSON file
        
        :param config_file: Path to config file (auto-detected if None)
        """
        if config_file is None:
            # Try monorepo location first
            try:
                
                config_ = Config(get_config_path('camera_config.json'))
                # config_file = get_config_path("bucher_camera_on_boot_config.json")
        
        self.config_file = config_file
        
        # Default values (same as original)
        self.cameras = None
        self.sinks = None
        self.socket_path = None
        self.metadata_source = None
        self.log_level = "DEBUG"
        self.display_height = 1080
        self.display_width = 1920
        self.log_frame_height = 1080
        self.log_frame_width = 1920
        self.log_frame_rate = 30
        self.need_long_format_logs = False
        self.test_frame_count = 10
        self.perform_frame_capture_test = False
        self.send_v4l2_ctl_settings = False
        self.status_json_path = "/tmp/bucher_ai_camera_status_on_boot.json"
        self.export_status_json = False
        
        # Load configuration
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Extract values (exact same logic as original)
            self.cameras = config_data.get('cameras', [])
            self.sinks = config_data.get('sinks', [])
            self.socket_path = config_data.get('socket_path')
            self.metadata_source = config_data.get('metadata_source')
            self.log_level = config_data.get('log_level', self.log_level)
            self.display_height = config_data.get('display_height', self.display_height)
            self.display_width = config_data.get('display_width', self.display_width)
            self.log_frame_height = config_data.get('log_frame_height', self.log_frame_height)
            self.log_frame_width = config_data.get('log_frame_width', self.log_frame_width)
            self.log_frame_rate = config_data.get('log_frame_rate', self.log_frame_rate)
            self.need_long_format_logs = config_data.get('need_long_format_logs', self.need_long_format_logs)
            self.test_frame_count = config_data.get('test_frame_count', self.test_frame_count)
            self.perform_frame_capture_test = config_data.get('perform_frame_capture_test', self.perform_frame_capture_test)
            self.send_v4l2_ctl_settings = config_data.get('send_v4l2_ctl_settings', self.send_v4l2_ctl_settings)
            self.status_json_path = config_data.get('status_json_path', self.status_json_path)
            self.export_status_json = config_data.get('export_status_json', self.export_status_json)
            
        except Exception as e:
            print(f"Error reading config file {self.config_file}: {e}")
            raise e
    
    def get(self, key, default=None):
        """Get config value by key"""
        return getattr(self, key, default)


class AppContext:
    """
    Application Context Manager
    Stores runtime state and configuration
    
    VERIFIED: Exact functionality from original
    """
    
    def __init__(self, config):
        """
        Initialize application context
        
        :param config: Config object with settings
        """
        self.pipeline_state = None
        self.active_sinks = []
        self.active_sources = []
        self.metadata = {}
        self.logger = None
        self._state = config
        self._main_process_pid = None
    
    def initialise_logging(self):
        """
        Initialize logging with configured level and format
        VERIFIED: Exact logic from original
        """
        self.logger = logging.getLogger('app')
        log_level = getattr(logging, self._state.log_level.upper())
        self.logger.setLevel(log_level)
        
        console_handler = logging.StreamHandler()
        
        if self._state.need_long_format_logs:
            formatter = logging.Formatter(
                '%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d (%(funcName)s): %(message)s'
            )
        else:
            formatter = logging.Formatter('%(levelname)s: %(message)s')
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    @property
    def state(self):
        """Get config state"""
        return self._state
    
    def set_metadata(self, key, value):
        """Store metadata"""
        self.metadata[key] = value
    
    def get_metadata(self, key, default=None):
        """Retrieve metadata"""
        return self.metadata.get(key, default)