"""
Camera Source Creation
Creates GStreamer source elements for cameras
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
    :param camera_config: Camera configuration dict
    :param app_context: Application context
    :return: GStreamer source element or None
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
    
    # Configure camera parameters
    source.set_property('sensor-id', int(sensor_id))
    source.set_property('sensor-mode', camera_config.get('sensor-mode', 3))
    source.set_property('gainrange', camera_config.get('gainrange', '1.0 8.0'))
    source.set_property('exposuretimerange', camera_config.get('exposuretimerange', '20000 336980000'))
    source.set_property('ispdigitalgainrange', camera_config.get('ispdigitalgainrange', '1 256'))
    
    return source


def make_bucher_ds_filesrc(file_path, codec, app_context=None):
    """
    Create a filesrc bin for testing with video files
    
    :param file_path: Path to video file
    :param codec: Codec type ('h264' or 'h265')
    :param app_context: Application context
    :return: GStreamer bin or None
    """
    if app_context:
        logger = app_context.get_value('app_context_v2').logger
    else:
        logger = None
    
    # Create bin
    file_name = os.path.basename(file_path)
    filesrc_name = file_name.replace('.', '_')
    
    bucher_ds_filesrc_bin = Gst.Bin.new(f'bucher_ds_filesrc_bin_{filesrc_name}')
    if not bucher_ds_filesrc_bin:
        sys.stderr.write('Failed to create filesrc bin\n')
        return None
    
    bucher_ds_filesrc_bin.set_property('message-forward', True)
    
    if logger:
        logger.debug(f'Creating filesrc bin for: {file_path}')
    
    # Create elements
    filesrc = make_element('filesrc', f'filesrc_{filesrc_name}')
    if not filesrc:
        return None
    filesrc.set_property('location', str(file_path))
    
    demuxer = make_element('qtdemux', f'qtdemux_{filesrc_name}')
    if not demuxer:
        return None
    
    source_queue = make_element('queue', f'source_queue_{filesrc_name}')
    if not source_queue:
        return None
    
    # Select parser based on codec
    if codec == 'h264':
        parser = make_element('h264parse', f'h264parse_{filesrc_name}')
    elif codec == 'h265':
        parser = make_element('h265parse', f'h265parse_{filesrc_name}')
    else:
        sys.stderr.write(f'Unsupported codec: {codec}\n')
        return None
    
    if not parser:
        return None
    
    decoder = make_element('nvv4l2decoder', f'nvv4l2decoder_{filesrc_name}')
    if not decoder:
        return None
    
    converter = make_element('nvvideoconvert', f'videoconvert_{filesrc_name}')
    if not converter:
        return None
    
    sink_queue = make_element('queue', f'sink_queue_{filesrc_name}')
    if not sink_queue:
        return None
    
    # Add elements to bin
    Gst.Bin.add(bucher_ds_filesrc_bin, filesrc)
    Gst.Bin.add(bucher_ds_filesrc_bin, demuxer)
    Gst.Bin.add(bucher_ds_filesrc_bin, source_queue)
    Gst.Bin.add(bucher_ds_filesrc_bin, parser)
    Gst.Bin.add(bucher_ds_filesrc_bin, decoder)
    Gst.Bin.add(bucher_ds_filesrc_bin, converter)
    Gst.Bin.add(bucher_ds_filesrc_bin, sink_queue)
    
    # Link elements
    filesrc.link(demuxer)
    
    # Connect demuxer pad-added signal
    source_queue_sinkpad = get_static_pad(source_queue, 'sink')
    demuxer.connect('pad-added', lambda ctx, pad: demuxer_pad_added(ctx, pad, source_queue_sinkpad))
    
    source_queue.link(parser)
    parser.link(decoder)
    decoder.link(converter)
    converter.link(sink_queue)
    
    # Add ghost pad
    bin_srcpad = bucher_ds_filesrc_bin.add_pad(
        Gst.GhostPad.new('src', sink_queue.get_static_pad('src'))
    )
    
    if not bin_srcpad:
        sys.stderr.write('Failed to add ghost pad to filesrc bin\n')
        return None
    
    return bucher_ds_filesrc_bin