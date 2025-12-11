"""
Camera Source Creation
Creates GStreamer source elements for cameras

VERIFIED: Exact functionality from original pipeline_w_logging.py
"""
import sys
import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

from ..pipeline.elements import make_element
from ..pipeline.linking import get_static_pad
from ..utils.helpers import demuxer_pad_added


def make_argus_camera_source(sensor_id, camera_config=None, app_context=None):
    """
    Create an nvarguscamerasrc element for CSI camera
    
    :param sensor_id: Camera sensor ID (0-7)
    :param camera_config: Camera configuration dict (optional)
    :param app_context: Application context (optional)
    :return: GStreamer source element or None
    
    VERIFIED: Exact logic from original
    """
    if app_context:
        logger = app_context.get_value('app_context_v2').logger
    else:
        logger = None
    
    camera_config = camera_config or {}
    
    source = make_element('nvarguscamerasrc', f'nvarguscamerasrc_{sensor_id}')
    if not source:
        sys.stderr.write(f'Unable to create argus camera source for sensor {sensor_id}\n')
        return None
    
    if logger:
        logger.debug(f'Setting nvarguscamerasrc parameters for sensor {sensor_id}')
    
    # Configure camera parameters (exact defaults from original)
    source.set_property('sensor-id', int(sensor_id))
    source.set_property('sensor-mode', camera_config.get('sensor-mode', 3))
    source.set_property('gainrange', camera_config.get('gainrange', '1.0 8.0'))
    source.set_property('exposuretimerange', camera_config.get('exposuretimerange', '20000 336980000'))
    source.set_property('ispdigitalgainrange', camera_config.get('ispdigitalgainrange', '1 256'))
    
    return source


def make_bucher_ds_filesrc(file_path, codec, app_context=None):
    """
    Create a filesrc bin for testing with video files
    Handles H.264 and H.265 encoded files
    
    :param file_path: Path to video file
    :param codec: Codec type ('h264' or 'h265')
    :param app_context: Application context (optional)
    :return: GStreamer bin or None
    
    VERIFIED: Exact logic from original
    """
    if app_context:
        logger = app_context.get_value('app_context_v2').logger
    else:
        logger = None
    
    # Create bin name from file path
    file_name = os.path.basename(file_path)
    filesrc_name = file_name.replace('.', '_')
    
    if logger:
        logger.debug(f'Creating bucher_ds_filesrc_bin for file: {file_path}')
    
    # Create bin
    bucher_ds_filesrc_bin = Gst.Bin.new(f'bucher_ds_filesrc_bin_{filesrc_name}')
    if not bucher_ds_filesrc_bin:
        if logger:
            logger.error('Failed to create bucher_ds_filesrc_bin')
        return None
    
    bucher_ds_filesrc_bin.set_property('message-forward', True)
    bucher_ds_filesrc_bin.set_property('name', f'bucher_ds_filesrc_bin_{filesrc_name}')
    
    # File source
    filesrc = make_element('filesrc', f'filesrc_{filesrc_name}')
    if not filesrc:
        return None
    filesrc.set_property('location', str(file_path))
    Gst.Bin.add(bucher_ds_filesrc_bin, filesrc)
    
    # Demuxer (for .mov/.mp4 files)
    demuxer = make_element('qtdemux', f'qtdemux_{filesrc_name}')
    if not demuxer:
        return None
    Gst.Bin.add(bucher_ds_filesrc_bin, demuxer)
    filesrc.link(demuxer)
    
    # Queue after demuxer
    source_queue = make_element('queue', f'source_queue_{filesrc_name}')
    if not source_queue:
        return None
    Gst.Bin.add(bucher_ds_filesrc_bin, source_queue)
    
    # Connect demuxer dynamic pad to queue
    source_queue_sinkpad = get_static_pad(source_queue, 'sink')
    demuxer.connect('pad-added', lambda context, pad: demuxer_pad_added(context, pad, source_queue_sinkpad))
    
    # Parser (H.264 or H.265)
    if codec == 'h264':
        parser = make_element('h264parse', f'h264parse_{filesrc_name}')
    elif codec == 'h265':
        parser = make_element('h265parse', f'h265parse_{filesrc_name}')
    else:
        if logger:
            logger.error(f'Unsupported codec: {codec}')
        return None
    
    if not parser:
        return None
    Gst.Bin.add(bucher_ds_filesrc_bin, parser)
    source_queue.link(parser)
    
    # Decoder
    decoder = make_element('nvv4l2decoder', f'nvv4l2decoder_{filesrc_name}')
    if not decoder:
        return None
    Gst.Bin.add(bucher_ds_filesrc_bin, decoder)
    parser.link(decoder)
    
    # Video converter
    converter_rotate = make_element('nvvideoconvert', f'videoconvert_{filesrc_name}_1')
    if not converter_rotate:
        return None
    Gst.Bin.add(bucher_ds_filesrc_bin, converter_rotate)
    decoder.link(converter_rotate)
    
    # Output queue
    sink_queue = make_element('queue', f'sink_queue_{filesrc_name}')
    if not sink_queue:
        return None
    Gst.Bin.add(bucher_ds_filesrc_bin, sink_queue)
    converter_rotate.link(sink_queue)
    
    # Add ghost pad for bin output
    binsrcpad = bucher_ds_filesrc_bin.add_pad(Gst.GhostPad.new('src', sink_queue.get_static_pad('src')))
    if not binsrcpad:
        if logger:
            logger.error('Failed to add ghost src pad to bucher_ds_filesrc_bin')
        return None
    
    return bucher_ds_filesrc_bin