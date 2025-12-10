"""
GStreamer Pipeline Builder
Constructs the complete inference pipeline
"""
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

from .elements import make_element
from .bins import create_inference_bin, create_multi_argus_camera_bin, create_udpsinkbin
from .linking import get_static_pad


def on_message(bus, message, loop, app_context):
    """
    GStreamer bus message callback
    
    :param bus: GStreamer bus
    :param message: Message from bus
    :param loop: GLib main loop
    :param app_context: Application context
    """
    logger = app_context.get_value('app_context_v2').logger
    mtype = message.type
    
    if mtype == Gst.MessageType.EOS:
        logger.info('End-of-stream')
        loop.quit()
    
    elif mtype == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        logger.error(f'Error: {err}, Debug: {debug}')
        loop.quit()
    
    elif mtype == Gst.MessageType.WARNING:
        warn, debug = message.parse_warning()
        logger.warning(f'Warning: {warn}')
    
    elif mtype == Gst.MessageType.STATE_CHANGED:
        if message.src == app_context.get_value('pipeline'):
            old_state, new_state, pending = message.parse_state_changed()
            logger.debug(f'Pipeline state: {old_state.value_nick} -> {new_state.value_nick}')
    
    return True


def build_pipeline(app_context):
    """
    Build the complete GStreamer pipeline
    
    Pipeline structure:
    multi_argus_camera_bin -> inference_bin -> tiler -> nvdsosd -> udp_sink_bin
    
    :param app_context: Application context with configuration
    :return: GStreamer pipeline or None
    """
    logger = app_context.get_value('app_context_v2').logger
    init_config = app_context.get_value('init_config')
    cameras = init_config.get('cameras', [])
    
    logger.info('Building GStreamer pipeline...')
    
    # Create pipeline
    pipeline = Gst.Pipeline()
    if not pipeline:
        logger.error('Failed to create pipeline')
        return None
    
    # Display configuration
    display_width = init_config.get('display_width', 1920)
    display_height = init_config.get('display_height', 1080)
    tiler_rows = 2
    tiler_columns = 2
    
    # Create multi-camera source bin
    logger.debug('Creating multi-camera source bin...')
    if create_multi_argus_camera_bin(cameras, app_context) != 0:
        logger.error('Failed to create multi-camera source bin')
        return None
    
    multi_argus_camera_bin = app_context.get_value('multi_argus_camera_bin')
    
    # Create inference bin
    logger.debug('Creating inference bin...')
    if create_inference_bin(app_context) != 0:
        logger.error('Failed to create inference bin')
        return None
    
    inference_bin = app_context.get_value('bucher_inference_bin')
    
    # Create UDP sink bin
    logger.debug('Creating UDP sink bin...')
    if create_udpsinkbin(app_context) != 0:
        logger.error('Failed to create UDP sink bin')
        return None
    
    udp_sink_bin = app_context.get_value('udp_sink_bin')
    
    # Create tiler for multi-stream display
    tiler = make_element('nvmultistreamtiler', 'display-tiler')
    if not tiler:
        logger.error('Failed to create tiler')
        return None
    
    tiler.set_property('rows', tiler_rows)
    tiler.set_property('columns', tiler_columns)
    tiler.set_property('width', display_width)
    tiler.set_property('height', display_height)
    
    # Create video converter
    nvvidconv = make_element('nvvideoconvert', 'converter')
    if not nvvidconv:
        logger.error('Failed to create video converter')
        return None
    
    # Create OSD for overlays
    nvosd = make_element('nvdsosd', 'onscreendisplay')
    if not nvosd:
        logger.error('Failed to create OSD')
        return None
    
    # Create queue for RTSP sink
    rtsp_sink_queue = make_element('queue', 'rtsp_sink_queue')
    if not rtsp_sink_queue:
        logger.error('Failed to create RTSP queue')
        return None
    
    rtsp_sink_queue.set_property('max-size-buffers', 30)
    rtsp_sink_queue.set_property('leaky', 2)
    rtsp_sink_queue.set_property('flush-on-eos', True)
    
    # Add all elements to pipeline
    logger.debug('Adding elements to pipeline...')
    pipeline.add(multi_argus_camera_bin)
    pipeline.add(inference_bin)
    pipeline.add(tiler)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(rtsp_sink_queue)
    pipeline.add(udp_sink_bin)
    
    # Link elements
    logger.debug('Linking pipeline elements...')
    if not multi_argus_camera_bin.link(inference_bin):
        logger.error('Failed to link camera bin to inference bin')
        return None
    
    if not inference_bin.link(tiler):
        logger.error('Failed to link inference bin to tiler')
        return None
    
    if not tiler.link(nvvidconv):
        logger.error('Failed to link tiler to video converter')
        return None
    
    if not nvvidconv.link(nvosd):
        logger.error('Failed to link video converter to OSD')
        return None
    
    if not nvosd.link(rtsp_sink_queue):
        logger.error('Failed to link OSD to RTSP queue')
        return None
    
    if not rtsp_sink_queue.link(udp_sink_bin):
        logger.error('Failed to link RTSP queue to UDP sink')
        return None
    
    logger.info('Pipeline built successfully')
    return pipeline