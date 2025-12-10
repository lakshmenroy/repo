"""
GStreamer Bin Creation
Complex bins for inference, CSI, and output
"""
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import sys

from .elements import make_element
from .linking import (
    link_request_srcpad_to_static_sinkpad,
    link_static_srcpad_pad_to_request_sinkpad,
    get_static_pad,
    get_request_pad
)
from .probes import buffer_monitor_probe


def create_udpsinkbin(app_context):
    """
    Create UDP sink bin for RTSP streaming
    
    :param app_context: Application context
    :return: 0 on success, 1 on failure
    """
    logger = app_context.get_value('app_context_v2').logger
    logger.debug('Creating UDP sink bin...')
    
    udpsinkbin = Gst.Bin.new('udp_sink_bin')
    udpsinkbin.set_property('message-forward', True)
    
    # Create encoder
    encoder = make_element('nvv4l2h265enc', 'h265_encoder')
    encoder.set_property('bitrate', 8000000)
    encoder.set_property('preset-level', 1)
    encoder.set_property('insert-sps-pps', 1)
    encoder.set_property('iframeinterval', 30)
    
    # Create RTP payloader
    rtppay = make_element('rtph265pay', 'rtp_payloader')
    rtppay.set_property('config-interval', 1)
    rtppay.set_property('pt', 96)
    
    # Create UDP sink
    udpsink = make_element('udpsink', 'udp_sink')
    udpsink.set_property('host', '127.0.0.1')
    udpsink.set_property('port', 5400)
    udpsink.set_property('sync', 0)
    udpsink.set_property('async', 0)
    
    # Add elements to bin
    Gst.Bin.add(udpsinkbin, encoder)
    Gst.Bin.add(udpsinkbin, rtppay)
    Gst.Bin.add(udpsinkbin, udpsink)
    
    # Link elements
    encoder.link(rtppay)
    rtppay.link(udpsink)
    
    # Add ghost pad
    udpsinkbin.add_pad(Gst.GhostPad.new('sink', get_static_pad(encoder, 'sink')))
    
    app_context.set_value('udp_sink_bin', udpsinkbin)
    logger.debug('UDP sink bin created')
    return 0


def create_csiprobebin(app_context, flip_method):
    """
    Create CSI probe bin for Clean Street Index computation
    
    Pipeline: nvstreammux -> road_nvinfer -> garbage_nvinfer -> nvsegvisual -> convert
    
    :param app_context: Application context
    :param flip_method: Video flip method
    :return: GStreamer bin or None
    """
    logger = app_context.get_value('app_context_v2').logger
    logger.debug('Creating CSI probe bin...')
    
    csi_probe_bin = Gst.Bin.new('csi_probe_bin')
    csi_probe_bin.set_property('message-forward', True)
    
    # Create muxers for road and garbage inference
    nvstreammux_road_pgie = make_element('nvstreammux', 'nvstreammux_road_pgie')
    nvstreammux_garbage_pgie = make_element('nvstreammux', 'nvstreammux_garbage_pgie')
    
    # Create queues
    queue_pre_road_pgie = make_element('queue', 'queue_pre_road_pgie')
    queue_pre_garbage_pgie = make_element('queue', 'queue_pre_garbage_pgie')
    queue_post_garbage_pgie = make_element('queue', 'queue_post_garbage_pgie')
    
    # Create inference engines
    road_nvinfer_engine = make_element('nvinfer', 'road_nvinfer_engine')
    garbage_nvinfer_engine = make_element('nvinfer', 'garbage_nvinfer_engine')
    
    # Create segmentation visualizer
    segvisual = make_element('nvsegvisual', 'segvisual')
    
    # Create video rate control
    videorate_out_csi = make_element('videorate', 'videorate_out_csi')
    
    # Create converter and caps filter
    rgba_to_nv12_convert = make_element('nvvideoconvert', 'rgba_to_nv12_convert')
    rgba_to_nv12_capsfilter = make_element('capsfilter', 'rgba_to_nv12_capsfilter')
    output_queue = make_element('queue', 'csi_output_queue')
    
    # Configure elements
    videorate_out_csi.set_property("skip-to-first", True)
    
    segvisual.set_property('alpha', 0)
    segvisual.set_property('original-background', True)
    segvisual.set_property('width', 608)
    segvisual.set_property('height', 416)
    
    # Configure road muxer
    nvstreammux_road_pgie.set_property('width', 1920)
    nvstreammux_road_pgie.set_property('height', 1080)
    nvstreammux_road_pgie.set_property('batch-size', 2)
    nvstreammux_road_pgie.set_property('live-source', 1)
    nvstreammux_road_pgie.set_property('batched-push-timeout', 33000000)
    
    # Configure garbage muxer
    nvstreammux_garbage_pgie.set_property('width', 1920)
    nvstreammux_garbage_pgie.set_property('height', 1080)
    nvstreammux_garbage_pgie.set_property('batch-size', 2)
    nvstreammux_garbage_pgie.set_property('live-source', 1)
    nvstreammux_garbage_pgie.set_property('batched-push-timeout', 33000000)
    
    # Configure inference engines
    road_nvinfer_engine.set_property('config-file-path', '/mnt/ssd/csi_pipeline/config/ds_config/road_config.txt')
    garbage_nvinfer_engine.set_property('config-file-path', '/mnt/ssd/csi_pipeline/config/ds_config/garbage_config.txt')
    
    # Configure caps filter
    rgba_to_nv12_capsfilter.set_property('caps', Gst.Caps.from_string('video/x-raw(memory:NVMM), format=NV12'))
    
    # Add all elements to bin
    elements = [
        nvstreammux_road_pgie, queue_pre_road_pgie, road_nvinfer_engine,
        nvstreammux_garbage_pgie, queue_pre_garbage_pgie, garbage_nvinfer_engine,
        segvisual, queue_post_garbage_pgie, rgba_to_nv12_convert,
        rgba_to_nv12_capsfilter, output_queue
    ]
    
    for element in elements:
        if not element:
            logger.error(f'Failed to create element in CSI bin')
            return None
        Gst.Bin.add(csi_probe_bin, element)
    
    # Add ghost pads for input
    csi_probe_bin.add_pad(Gst.GhostPad.new('sink_0', get_request_pad(nvstreammux_road_pgie, 'sink_0')))
    csi_probe_bin.add_pad(Gst.GhostPad.new('sink_1', get_request_pad(nvstreammux_road_pgie, 'sink_1')))
    
    # Link elements
    nvstreammux_road_pgie.link(queue_pre_road_pgie)
    queue_pre_road_pgie.link(road_nvinfer_engine)
    
    # Link road output to garbage muxer
    link_static_srcpad_pad_to_request_sinkpad(road_nvinfer_engine, nvstreammux_garbage_pgie, sink_pad_index=0)
    
    nvstreammux_garbage_pgie.link(queue_pre_garbage_pgie)
    queue_pre_garbage_pgie.link(garbage_nvinfer_engine)
    garbage_nvinfer_engine.link(segvisual)
    segvisual.link(queue_post_garbage_pgie)
    queue_post_garbage_pgie.link(rgba_to_nv12_convert)
    rgba_to_nv12_convert.link(rgba_to_nv12_capsfilter)
    rgba_to_nv12_capsfilter.link(output_queue)
    
    # Add CSI computation probe
    try:
        from ..csi.probes import compute_csi_buffer_probe
        queue_post_garbage_pgie_pad = get_static_pad(queue_post_garbage_pgie, 'src')
        queue_post_garbage_pgie_pad.add_probe(Gst.PadProbeType.BUFFER, compute_csi_buffer_probe, 0)
        logger.debug('CSI computation probe attached')
    except ImportError:
        logger.warning('CSI module not available, skipping CSI probe')
    
    # Add ghost pad for output
    csi_probe_bin.add_pad(Gst.GhostPad.new('src_0', get_static_pad(output_queue, 'src')))
    
    logger.debug('CSI probe bin created')
    return csi_probe_bin


def create_inference_bin(app_context):
    """
    Create the main inference bin
    Contains nozzlenet inference and CSI computation paths
    
    :param app_context: Application context
    :return: 0 on success, 1 on failure
    """
    logger = app_context.get_value('app_context_v2').logger
    logger.debug('Creating inference bin...')
    
    # Get configuration
    config_paths_dict = app_context.get_value('config_paths')
    cameras = app_context.get_value('init_config')['cameras']
    num_sources = len([camera for camera in cameras if camera.get('capture_test_passed') == True])
    
    app_context.set_value('num_sources', num_sources)
    logger.debug(f'Number of active sources: {num_sources}')
    
    # Create parent inference bin
    inference_bin = Gst.Bin.new('bucher_inference_bin')
    if not inference_bin:
        logger.error('Failed to create inference bin')
        return 1
    
    inference_bin.set_property('message-forward', True)
    
    # Create tee for splitting input stream
    inference_bin_tee = make_element('tee', 'inference_bin_tee')
    Gst.Bin.add(inference_bin, inference_bin_tee)
    inference_bin.add_pad(Gst.GhostPad.new('sink', get_static_pad(inference_bin_tee, 'sink')))
    
    # Create metamux for combining metadata streams
    metamux = make_element('nvdsmetamux', 'inference_bin_metamux')
    metamux_config_file = config_paths_dict.get('metamux', {}).get('path')
    if metamux_config_file:
        metamux.set_property('config-file', metamux_config_file)
    
    # Create videomux for combining video streams
    videomux = make_element('nvstreammux', 'videomux')
    videomux.set_property('batch-size', num_sources)
    videomux.set_property('live-source', 1)
    videomux.set_property('batched-push-timeout', 33000000)
    videomux.set_property('width', 960)
    videomux.set_property('height', 540)
    
    Gst.Bin.add(inference_bin, videomux)
    Gst.Bin.add(inference_bin, metamux)
    
    # Add ghost pad for output
    inference_bin.add_pad(Gst.GhostPad.new('src', get_static_pad(metamux, 'src')))
    
    # Create stream demuxer
    queue_to_stream_demuxer = make_element('queue', 'queue_to_streamdemuxer')
    stream_demuxer = make_element('nvstreamdemux', 'inference_stream_demuxer')
    
    Gst.Bin.add(inference_bin, queue_to_stream_demuxer)
    Gst.Bin.add(inference_bin, stream_demuxer)
    
    # Link tee to demuxer
    link_request_srcpad_to_static_sinkpad(inference_bin_tee, queue_to_stream_demuxer, src_pad_index=2)
    queue_to_stream_demuxer.link(stream_demuxer)
    
    # Create CSI merger for front/rear cameras
    csi_merger = make_element('nvstreammux', 'csi_merger')
    csi_merger.set_property('batch-size', 2)
    csi_merger.set_property('live-source', 1)
    csi_merger.set_property('batched-push-timeout', 100000000)
    csi_merger.set_property('width', 960)
    csi_merger.set_property('height', 540)
    csi_merger.set_property('sync-inputs', True)
    Gst.Bin.add(inference_bin, csi_merger)
    
    # Get padmap and camera categorization
    padmap = app_context.get_value('muxer_padmap')
    num_nozzlet_sources = 0
    num_csi_sources = 0
    
    nozzlenet_cameras = ['right', 'left', 'primary_nozzle', 'secondary_nozzle']
    csi_cameras = ['front', 'rear']
    
    # Build per-camera branches
    for muxer_pad_index, camera_index in padmap.items():
        muxer_pad_index = int(muxer_pad_index)
        camera_index = int(camera_index)
        camera = cameras[camera_index]
        camera_name = camera['name']
        camera_position = camera['position']
        do_inference = camera.get('do_infer', False)
        
        logger.debug(f'Setting up camera: {camera_name} (position: {camera_position}, pad: {muxer_pad_index})')
        
        if camera_position in nozzlenet_cameras:
            num_nozzlet_sources += 1
        if camera_position in csi_cameras:
            num_csi_sources += 1
        
        # Create per-camera elements
        queue_to_streammux = make_element('queue', f'queue_{camera_name}_to_streammux')
        queue_post_streammux = make_element('queue', f'queue_{camera_name}_post_streammux')
        tee = make_element('tee', f'tee_{camera_name}')
        
        Gst.Bin.add(inference_bin, queue_to_streammux)
        Gst.Bin.add(inference_bin, queue_post_streammux)
        Gst.Bin.add(inference_bin, tee)
        
        # Create inference queue if needed
        if do_inference:
            queue_to_inference = make_element('queue', f'queue_{camera_name}_to_inference')
            Gst.Bin.add(inference_bin, queue_to_inference)
            link_request_srcpad_to_static_sinkpad(tee, queue_to_inference, src_pad_index=0)
        
        # Create selective streammux
        selective_streammux = make_element('nvstreammux', f'selective_streammux_{camera_name}')
        selective_streammux.set_property('batch-size', 1)
        selective_streammux.set_property('live-source', 1)
        selective_streammux.set_property('batched-push-timeout', 4000000)
        selective_streammux.set_property('width', 960)
        selective_streammux.set_property('height', 540)
        Gst.Bin.add(inference_bin, selective_streammux)
        
        # Link demuxer to this camera's path
        link_request_srcpad_to_static_sinkpad(stream_demuxer, queue_to_streammux, src_pad_index=muxer_pad_index)
        link_static_srcpad_pad_to_request_sinkpad(queue_to_streammux, selective_streammux, sink_pad_index=muxer_pad_index)
        selective_streammux.link(queue_post_streammux)
        queue_post_streammux.link(tee)
        
        # Branch for nozzlenet cameras
        if camera_position in nozzlenet_cameras:
            queue_to_videomux = make_element('queue', f'queue_{camera_name}_to_videomux')
            Gst.Bin.add(inference_bin, queue_to_videomux)
            link_request_srcpad_to_static_sinkpad(tee, queue_to_videomux, src_pad_index=1)
            link_static_srcpad_pad_to_request_sinkpad(queue_to_videomux, videomux, sink_pad_index=muxer_pad_index)
        
        # Branch for CSI cameras
        if camera_position in csi_cameras:
            if do_inference:
                queue_to_inference.set_property('max-size-buffers', 1)
                queue_to_inference.set_property('leaky', 1)
                queue_to_inference.set_property('flush-on-eos', True)
                link_static_srcpad_pad_to_request_sinkpad(queue_to_inference, csi_merger, sink_pad_index=muxer_pad_index)
    
    logger.debug(f'Nozzle cameras: {num_nozzlet_sources}, CSI cameras: {num_csi_sources}')
    
    # Create nozzlenet inference bin if needed
    if num_nozzlet_sources > 0:
        logger.debug('Creating nozzlenet inference bin...')
        
        nozzlenet_infer_bin = Gst.Bin.new('BUCHER-nozzlenet-infer-bin')
        nozzlenet_infer_bin.set_property('message-forward', True)
        
        # Create elements
        pgie = make_element('nvinfer', 'nozzlenet-infer')
        nozzlenet_infer_placeholder = make_element('identity', 'nozzlenet_infer_placeholder')
        preprocess = make_element('nvdspreprocess', 'nozzlenet_preprocess')
        nvvideo_conv_readjuster = make_element('nvvideoconvert', 'resize-back-to-fit-display')
        caps_filter_readjuster = make_element('capsfilter', 'capsfilter')
        queue_nozzlenet_post_infer = make_element('queue', 'queue_nozzlenet_post_infer')
        
        elements = [pgie, nozzlenet_infer_placeholder, preprocess, nvvideo_conv_readjuster, 
                   caps_filter_readjuster, queue_nozzlenet_post_infer]
        
        # Get config paths
        preprocess_config_file = config_paths_dict.get('preprocess', {}).get('path')
        infer_config_file = config_paths_dict.get('inference', {}).get('path')
        
        # Configure elements
        if preprocess_config_file:
            preprocess.set_property('config-file', preprocess_config_file)
        if infer_config_file:
            pgie.set_property('config-file-path', infer_config_file)
        
        pgie.set_property('unique-id', 1)
        caps_filter_readjuster.set_property('caps', Gst.Caps.from_string('video/x-raw(memory:NVMM), width=960, height=540'))
        queue_nozzlenet_post_infer.set_property('leaky', 'downstream')
        
        # Add elements to bin
        Gst.Bin.add(inference_bin, nozzlenet_infer_bin)
        for element in elements:
            try:
                Gst.Bin.add(nozzlenet_infer_bin, element)
            except Exception as e:
                logger.error(f"Error adding element {element.get_name()} to nozzlenet_infer_bin: {e}")
        
        # Link elements
        nozzlenet_infer_placeholder.link(preprocess)
        preprocess.link(pgie)
        pgie.link(nvvideo_conv_readjuster)
        nvvideo_conv_readjuster.link(caps_filter_readjuster)
        caps_filter_readjuster.link(queue_nozzlenet_post_infer)
        
        # Add ghost pad
        nozzlenet_infer_bin.add_pad(Gst.GhostPad.new('src', get_static_pad(queue_nozzlenet_post_infer, 'src')))
        
        # Add nozzlenet probe
        from .probes import nozzlenet_src_pad_buffer_probe
        tracker_src_pad = get_static_pad(pgie, 'src')
        tracker_src_pad.add_probe(Gst.PadProbeType.BUFFER, lambda pad, info, u_data: nozzlenet_src_pad_buffer_probe(pad, info, u_data), 0)
        
        # Link to primary nozzle camera
        primary_inference_queue = inference_bin.get_by_name(f'queue_primary_nozzle_to_inference')
        if primary_inference_queue:
            primary_inference_queue.link(nozzlenet_infer_placeholder)
        else:
            logger.warning('Primary nozzle inference queue not found')
    
    # Create CSI probe bin if needed
    if num_csi_sources > 0:
        logger.debug('Creating CSI probe bin...')
        
        flip_method = cameras[0].get('converter_flip_method', 0)
        csi_probe_bin = create_csiprobebin(app_context, flip_method)
        
        if csi_probe_bin:
            # Create demuxer and rate control
            csi_demuxer = make_element('nvstreamdemux', 'csi_demuxer')
            csi_front_videorate_queue = make_element('queue', 'csi_front_videorate_queue')
            csi_rear_videorate_queue = make_element('queue', 'csi_rear_videorate_queue')
            csi_front_videomux_queue = make_element('queue', 'csi_front_videomux_queue')
            csi_rear_videomux_queue = make_element('queue', 'csi_rear_videomux_queue')
            csi_front_videorate = make_element('videorate', 'csi_front_videorate')
            csi_rear_videorate = make_element('videorate', 'csi_rear_videorate')
            
            # Configure queues
            for queue in [csi_front_videomux_queue, csi_rear_videomux_queue]:
                queue.set_property('max-size-buffers', 2)
                queue.set_property('leaky', 2)
                queue.set_property('flush-on-eos', True)
            
            for queue in [csi_front_videorate_queue, csi_rear_videorate_queue]:
                queue.set_property('max-size-buffers', 2)
                queue.set_property('leaky', 2)
                queue.set_property('flush-on-eos', True)
            
            csi_front_videorate.set_property('skip-to-first', True)
            csi_rear_videorate.set_property('skip-to-first', True)
            
            # Add to bin
            Gst.Bin.add(inference_bin, csi_probe_bin)
            Gst.Bin.add(inference_bin, csi_demuxer)
            for elem in [csi_front_videorate_queue, csi_rear_videorate_queue,
                        csi_front_videomux_queue, csi_rear_videomux_queue,
                        csi_front_videorate, csi_rear_videorate]:
                Gst.Bin.add(inference_bin, elem)
            
            # Link CSI path
            csi_merger.link(csi_probe_bin)
            csi_bin_srcpad = csi_probe_bin.get_static_pad('src_0')
            csi_demuxer_sinkpad = csi_demuxer.get_static_pad('sink')
            csi_bin_srcpad.link(csi_demuxer_sinkpad)
            
            link_request_srcpad_to_static_sinkpad(csi_demuxer, csi_front_videorate_queue, src_pad_index=0)
            link_request_srcpad_to_static_sinkpad(csi_demuxer, csi_rear_videorate_queue, src_pad_index=2)
            
            csi_front_videorate_queue.link(csi_front_videorate)
            csi_rear_videorate_queue.link(csi_rear_videorate)
            csi_front_videorate.link(csi_front_videomux_queue)
            csi_rear_videorate.link(csi_rear_videomux_queue)
            
            link_static_srcpad_pad_to_request_sinkpad(csi_front_videomux_queue, videomux, sink_pad_index=0)
            link_static_srcpad_pad_to_request_sinkpad(csi_rear_videomux_queue, videomux, sink_pad_index=2)
    
    # Connect videomux and nozzlenet to metamux
    link_static_srcpad_pad_to_request_sinkpad(videomux, metamux, sink_pad_index=0)
    if num_nozzlet_sources > 0:
        link_static_srcpad_pad_to_request_sinkpad(nozzlenet_infer_bin, metamux, sink_pad_index=1)
    
    app_context.set_value('bucher_inference_bin', inference_bin)
    logger.info('Inference bin created successfully')
    return 0