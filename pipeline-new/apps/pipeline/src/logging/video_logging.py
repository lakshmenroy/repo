"""
Video Logger
Records inference videos to disk
"""
from pathlib import Path

class VideoLogger:
    def __init__(self, app_context):
        self.app_context = app_context
        self.output_dir = Path("/mnt/syslogic_sd_card/upload/video")
        
    def start_recording(self):
        """
        Start video recording
        """
        # Extract video recording logic
        pass