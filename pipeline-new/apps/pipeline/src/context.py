"""
Application Context
Global state management using GStreamer Structure
"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import threading

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst


class GETFPS:
    """
    FPS Counter for monitoring stream performance
    Thread-safe FPS tracking
    """
    
    def __init__(self, stream_id):
        """
        Initialize FPS counter
        
        :param stream_id: Unique identifier for this stream
        """
        self.stream_id = stream_id
        self.start_time = datetime.now()
        self.frame_count = 0
        self.fps = 0.0
        self.lock = threading.Lock()
    
    def update_fps(self):
        """
        Update frame count and calculate FPS
        Call this on every frame
        """
        with self.lock:
            self.frame_count += 1
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            if elapsed > 0:
                self.fps = self.frame_count / elapsed
            
            # Reset every 30 seconds to avoid overflow
            if elapsed > 30:
                self.start_time = datetime.now()
                self.frame_count = 0
    
    def get_fps(self):
        """
        Get current FPS value
        
        :return: Current FPS as float
        """
        with self.lock:
            return round(self.fps, 2)
    
    def print_data(self):
        """Print FPS data to console"""
        print(f"Stream {self.stream_id}: {self.get_fps()} FPS")


class PERF_DATA:
    """
    Performance data tracker for multiple streams
    """
    
    def __init__(self, num_streams=1):
        """
        Initialize performance tracker
        
        :param num_streams: Number of streams to track
        """
        self.num_streams = num_streams
        self.fps_counters = {i: GETFPS(i) for i in range(num_streams)}
    
    def update_fps(self, stream_id):
        """Update FPS for specific stream"""
        if stream_id in self.fps_counters:
            self.fps_counters[stream_id].update_fps()
    
    def get_fps(self, stream_id):
        """Get FPS for specific stream"""
        if stream_id in self.fps_counters:
            return self.fps_counters[stream_id].get_fps()
        return 0.0
    
    def print_all(self):
        """Print FPS for all streams"""
        for counter in self.fps_counters.values():
            counter.print_data()


class Config:
    """
    Configuration from JSON file
    Used for camera and logging configuration
    """
    
    def __init__(self, config_path=None):
        """
        Load configuration from JSON file
        
        :param config_path: Path to config JSON file
        """
        if config_path is None:
            # Default to monorepo structure
            current_file = Path(__file__).resolve()
            pipeline_root = current_file.parents[1]  # apps/pipeline/
            config_path = pipeline_root / "config" / "bucher_camera_on_boot_config.json"
        
        self.config_path = Path(config_path)
        
        if not self.config_path.exists():
            # Try alternative path
            config_path = "/mnt/ssd/csi_pipeline/config/bucher_camera_on_boot_config.json"
            if os.path.exists(config_path):
                self.config_path = Path(config_path)
            else:
                raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(self.config_path, 'r') as f:
            self._config = json.load(f)
        
        # Extract common config values
        self.log_level = self._config.get('log_level', 'INFO')
        self.need_long_format_logs = self._config.get('need_long_format_logs', False)
        self.status_json_path = self._config.get('status_json_path')
        self.export_status_json = self._config.get('export_status_json', False)
    
    def get(self, key, default=None):
        """Get config value by key"""
        return self._config.get(key, default)


class AppContext:
    """
    Application context manager
    Stores runtime state and configuration
    """
    
    def __init__(self, config):
        """
        Initialize application context
        
        :param config: Config object with settings
        """
        self.pipeline_state = Gst.State.NULL
        self.active_sinks = []
        self.active_sources = []
        self.metadata = {}
        self.logger = None
        self._state = config
        self._main_process_pid = None
    
    def initialise_logging(self):
        """
        Initialize logging with configured level and format
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