"""
Camera Manager
Handles camera initialization and management
"""
import subprocess
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

from ..pipeline.elements import make_element
from ..pipeline.linking import link_static_srcpad_pad_to_request_sinkpad, get_static_pad
from .source import make_argus_camera_source, make_bucher_ds_filesrc


class CameraManager:
    """
    Manages multiple camera sources
    """
    def __init__(self, app_context):
        self.app_context = app_context
        self.logger = app_context.get_value('app_context_v2').logger
        self.cameras = []
        self.muxer_padmap = {}
    
    def send_v4l2_settings(self, camera):
        """
        Send V4L2 settings to camera
        
        :param camera: Camera configuration dict
        """
        device_path = camera.get('device_path')
        if not device_path:
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
            subprocess.run(cmd, check=True, capture_output=True)
            self.logger.debug(f'V4L2 settings applied to {device_path}')
        except subprocess.CalledProcessError as e:
            self.logger.error(f'Failed to apply V4L2 settings: {e.stderr.decode()}')


def initialize_cameras(app_context):
    """
    Initialize cameras and return camera manager
    
    :param app_context: Application context
    :return: CameraManager instance
    """
    manager = CameraManager(app_context)
    init_config = app_context.get_value('init_config')
    cameras = init_config.get('cameras', [])
    
    # Apply V4L2 settings to detected cameras
    for camera in cameras:
        if camera.get('detected_on_init') and camera.get('capture_test_passed'):
            manager.send_v4l2_settings(camera)
    
    return manager


def create_multi_argus_camera_bin(cameras, app_context):
    """
    Create a bin containing multiple camera sources
    
    :param cameras: List of camera configurations
    :param app_context: Application context
    :return: 0 on success, 1 on failure
    """
    logger = app_context.get_value('app_context_v2').logger
    
    # Count cameras that passed capture test
    num_cameras = len([c for c in cameras if c.get('capture_test_passed')])
    logger.info(f'Initializing {num_cameras} cameras')
    
    if num_cameras == 0:
        logger.error('No cameras available')
        return 1
    
    # Create bin
    multi_nvargus_bin = Gst.Bin.new('multi_nvargus_bin')
    multi_nvargus_bin.set_property('message-forward', True)
    
    # Create stream muxer
    streammux = make_element('nvstreammux', 'multi_nvargus_streammux')
    streammux.set_property('batch-size', num_cameras)
    streammux.set_property('live-source', 1)
    streammux.set_property('batched-push-timeout', 4000000)
    streammux.set_property('enable-padding', 1)
    streammux.set_property('width', 960)
    streammux.set_property('height', 540)
    
    Gst.Bin.add(multi_nvargus_bin, streammux)
    
    # Get source overrides
    camera_settings_overrides = app_context.get_value('camera_settings_overrides', {})
    
    # Track muxer pad mapping
    muxer_pad_index = 0
    muxer_padmap = {}
    
    # Create source for each camera
    for i, camera in enumerate(cameras):
        if not camera.get('capture_test_passed'):
            logger.debug(f"Skipping camera {camera['name']} (failed capture test)")
            continue
        
        camera_name = camera['name']
        device_path = camera['device_path']
        sensor_id = int(device_path.split('/dev/video')[-1])
        
        logger.debug(f"Creating source for camera {camera_name} (sensor {sensor_id})")
        
        # Create camera bin
        camera_bin = Gst.Bin.new(f"{camera_name}_camera_bin")
        camera_bin.set_property('message-forward', True)
        
        # Check for override (file source for testing)
        override = camera_settings_overrides.get(camera_name, {}).get('override', False)
        
        if override:
            # Use file source
            file_path = camera_settings_overrides[camera_name]['file_path']
            codec = camera_settings_overrides[camera_name].get('codec', 'h264')
            logger.info(f"Using file source for {camera_name}: {file_path}")
            camera_source = make_bucher_ds_filesrc(file_path, codec, app_context)
        else:
            # Use argus camera source
            camera_config = {
                'gainrange': camera['gainrange'],
                'exposuretimerange': camera['exposuretimerange'],
                'ispdigitalgainrange': camera['ispdigitalgainrange'],
                'sensor-mode': camera['sensor_mode']
            }
            camera_source = make_argus_camera_source(sensor_id, camera_config, app_context)
        
        if not camera_source:
            logger.error(f"Failed to create source for camera {camera_name}")
            continue
        
        # Create converter
        converter = make_element('nvvideoconvert', f'converter_{camera_name}')
        converter.set_property('flip-method', camera.get('converter_flip_method', 0))
        
        # Create caps filter
        caps_filter = make_element('capsfilter', f'capsfilter_{camera_name}')
        caps_filter.set_property('caps', Gst.Caps.from_string('video/x-raw(memory:NVMM), format=NV12'))
        
        # Add to camera bin
        Gst.Bin.add(camera_bin, camera_source)
        Gst.Bin.add(camera_bin, converter)
        Gst.Bin.add(camera_bin, caps_filter)
        
        # Link
        camera_source.link(converter)
        converter.link(caps_filter)
        
        # Add ghost pad
        camera_bin.add_pad(Gst.GhostPad.new('src', get_static_pad(caps_filter, 'src')))
        
        # Add camera bin to main bin
        Gst.Bin.add(multi_nvargus_bin, camera_bin)
        
        # Link to streammux
        link_static_srcpad_pad_to_request_sinkpad(camera_bin, streammux, sink_pad_index=muxer_pad_index)
        
        # Store mapping
        muxer_padmap[muxer_pad_index] = i
        muxer_pad_index += 1
    
    # Add ghost pad for output
    multi_nvargus_bin.add_pad(Gst.GhostPad.new('src', get_static_pad(streammux, 'src')))
    
    # Store in context
    app_context.set_value('multi_argus_camera_bin', multi_nvargus_bin)
    app_context.set_value('muxer_padmap', muxer_padmap)
    
    logger.info(f'Multi-camera bin created with {muxer_pad_index} sources')
    return 0