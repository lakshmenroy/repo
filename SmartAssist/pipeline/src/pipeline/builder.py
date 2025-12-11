"""
GStreamer Pipeline Builder
Constructs the complete inference pipeline

VERIFIED: Exact functionality from original pipeline_w_logging.py
This file builds the main pipeline topology
"""
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
import sys

from .elements import make_element
from .bins import create_bucher_inference_bin, create_udpsinkbin
from ..camera.manager import create_multi_argus_camera_bin


def bus_call(bus, message, loop):
    """
    GStreamer bus message callback
    
    Handles pipeline messages like EOS, errors, warnings
    
    :param bus: GStreamer bus
    :param message: Message from bus
    :param loop: GLib main loop
    :return: True to continue receiving messages
    
    VERIFIED: Exact from original
    """
    # Get app_context from global scope (set by main.py)
    import __main__
    if hasattr(__main__, 'app_context'):
        app_context = __main__.app_context
        logger = app_context.get_value('app_context_v2').logger
    else:
        logger = None
    
    mtype = message.type
    
    if mtype == Gst.MessageType.EOS:
        if logger:
            logger.info('End-of-stream received')
        loop.quit()
    
    elif mtype == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        if logger:
            logger.error(f'Error from {message.src.get_name()}: {err.message}')
            logger.error(f'Debug info: {debug}')
        else:
            sys.stderr.write(f'Error: {err.message}\n')
        loop.quit()
    
    elif mtype == Gst.MessageType.WARNING:
        warn, debug = message.parse_warning()
        if logger:
            logger.warning(f'Warning from {message.src.get_name()}: {warn.message}')
        else:
            sys.stderr.write(f'Warning: {warn.message}\n')
    
    elif mtype == Gst.MessageType.STATE_CHANGED:
        if message.src.get_name() == 'pipeline0':
            old_state, new_state, pending = message.parse_state_changed()
            if logger:
                logger.debug(f'Pipeline state: {old_state.value_nick} -> {new_state.value_nick}')
    
    elif mtype == Gst.MessageType.LATENCY:
        if logger:
            logger.debug('Redistributing latency...')
        # Get pipeline from message source
        pipeline = message.src
        if isinstance(pipeline, Gst.Pipeline):
            pipeline.recalculate_latency()
    
    return True


def build_pipeline(app_context):
    """
    Build the complete GStreamer pipeline
    
    Pipeline topology:
    multi_argus_camera_bin -> inference_bin -> nvvidconv -> tiler -> nvosd -> rtsp_sink_queue -> udp_sink_bin
    
    Note: Order is nvvidconv THEN tiler (not tiler then nvvidconv)
    This matches the exact original pipeline topology
    
    :param app_context: Application context with configuration
    :return: 0 on success, non-zero on failure
    
    VERIFIED: Exact topology and linking order from original
    """
    logger = app_context.get_value('app_context_v2').logger
    logger.info('Building GStreamer pipeline...')
    
    # Get configuration
    init_config = app_context.get_value('init_config')
    cameras = init_config.get('cameras', [])
    
    # Display configuration
    display_width = init_config.get('display_width', 1920)
    display_height = init_config.get('display_height', 1080)
    tiler_rows = 2
    tiler_columns = 2
    
    # Create main pipeline
    logger.debug('Creating GST pipeline...')
    pipeline = Gst.Pipeline()
    if not pipeline:
        logger.error('Failed to create pipeline')
        return -1
    
    # ========== CREATE BINS ==========
    
    # Create multi-camera source bin
    logger.debug('Adding multi_argus_camera_bin to the pipeline...')
    multi_src_bin_ok = create_multi_argus_camera_bin(cameras, app_context)
    if multi_src_bin_ok != 0:
        logger.error('Failed to create multi source bin')
        return -1
    multi_argus_camera_bin = app_context.get_value('multi_argus_camera_bin')
    
    # Create inference bin (contains nozzlenet + CSI + HR output)
    logger.debug('Adding bucher_inference_bin to the pipeline...')
    inference_bin_ok = create_bucher_inference_bin(app_context)
    if inference_bin_ok != 0:
        logger.error('Failed to create bucher inference bin')
        return -1
    inference_bin = app_context.get_value('bucher_inference_bin')
    
    # Create UDP sink bin (RTSP streaming)
    logger.debug('Adding udp_sink_bin to the pipeline...')
    udp_sink_bin = create_udpsinkbin(app_context)
    if not udp_sink_bin:
        logger.error('Failed to create UDP sink bin')
        return -1
    
    # ========== CREATE DISPLAY ELEMENTS ==========
    
    # Create video converter (BEFORE tiler - CRITICAL order!)
    nvvidconv = make_element('nvvideoconvert', 'converter')
    if not nvvidconv:
        logger.error('Failed to create video converter')
        return -1
    
    # Create tiler for multi-stream display
    tiler = make_element('nvmultistreamtiler', 'display-tiler')
    if not tiler:
        logger.error('Failed to create tiler')
        return -1
    
    # Configure tiler
    tiler.set_property('rows', tiler_rows)
    tiler.set_property('columns', tiler_columns)
    tiler.set_property('width', display_width)
    tiler.set_property('height', display_height)
    
    # Create OSD for on-screen display
    nvosd = make_element('nvdsosd', 'onscreendisplay')
    if not nvosd:
        logger.error('Failed to create OSD')
        return -1
    
    # Create queue before UDP sink
    rtsp_sink_queue = make_element('queue', 'rtsp_sink_queue')
    if not rtsp_sink_queue:
        logger.error('Failed to create RTSP queue')
        return -1
    
    # Configure queue
    rtsp_sink_queue.set_property('max-size-buffers', 30)
    rtsp_sink_queue.set_property('leaky', 2)
    rtsp_sink_queue.set_property('flush-on-eos', True)
    
    # ========== ADD ELEMENTS TO PIPELINE ==========
    
    logger.debug('Adding elements to the pipeline...')
    pipeline.add(multi_argus_camera_bin)
    pipeline.add(inference_bin)
    pipeline.add(nvvidconv)
    pipeline.add(tiler)
    pipeline.add(nvosd)
    pipeline.add(rtsp_sink_queue)
    pipeline.add(udp_sink_bin)
    
    # ========== LINK ELEMENTS ==========
    
    logger.debug('Linking elements in the pipeline...')
    
    # CRITICAL: Exact linking order from original
    # cameras -> inference -> nvvidconv -> tiler -> osd -> queue -> udp
    if not multi_argus_camera_bin.link(inference_bin):
        logger.error('Failed to link camera bin to inference bin')
        return -1
    
    if not inference_bin.link(nvvidconv):
        logger.error('Failed to link inference bin to video converter')
        return -1
    
    if not nvvidconv.link(tiler):
        logger.error('Failed to link video converter to tiler')
        return -1
    
    if not tiler.link(nvosd):
        logger.error('Failed to link tiler to OSD')
        return -1
    
    if not nvosd.link(rtsp_sink_queue):
        logger.error('Failed to link OSD to RTSP queue')
        return -1
    
    if not rtsp_sink_queue.link(udp_sink_bin):
        logger.error('Failed to link RTSP queue to UDP sink')
        return -1
    
    # ========== SETUP BUS AND MAIN LOOP ==========
    
    logger.debug('Setting pipeline and main loop in app context...')
    app_context.set_value('pipeline', pipeline)
    
    # Get bus and add signal watch
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    
    # Create main loop
    loop = GObject.MainLoop()
    app_context.set_value('main_loop', loop)
    
    # Connect bus callback
    bus.connect('message', bus_call, loop)
    
    logger.info('Pipeline built successfully')
    return 0