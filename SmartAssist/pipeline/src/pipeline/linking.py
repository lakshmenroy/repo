"""
GStreamer Pad Linking Utilities
Functions for connecting pads between elements

VERIFIED: Exact functionality from original pipeline_w_logging.py
"""
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst


def get_static_pad(element, pad_name):
    """
    Get a static pad from an element
    
    :param element: GStreamer element
    :param pad_name: Name of the pad (e.g., 'sink', 'src')
    :return: GstPad or None
    
    VERIFIED: Exact logic from original
    """
    pad = element.get_static_pad(pad_name)
    if not pad:
        sys.stderr.write(f'Unable to get the {pad_name} pad of {element.get_name()}\n')
    return pad


def get_request_pad(element, pad_name):
    """
    Get a request pad from an element
    
    :param element: GStreamer element
    :param pad_name: Name pattern for the request pad (e.g., 'sink_%u', 'sink_0')
    :return: GstPad or None
    
    VERIFIED: Exact logic from original
    """
    pad = element.get_request_pad(pad_name)
    if not pad:
        sys.stderr.write(f'Unable to get the {pad_name} pad of {element.get_name()}\n')
    return pad


def link_static_srcpad_pad_to_request_sinkpad(src, sink, sink_pad_index=None):
    """
    Link a static source pad to a request sink pad
    Used for connecting elements where sink needs a request pad (like nvstreammux)
    
    :param src: Source element (has static src pad)
    :param sink: Sink element (needs request sink pad)
    :param sink_pad_index: Index for the request pad (int or string, optional)
    
    VERIFIED: Exact logic from original
    """
    request_pad_index = 0
    src_pad_name = 'src'
    
    if sink_pad_index is None:
        sink_pad_index = f'sink_{request_pad_index}'
    elif isinstance(sink_pad_index, int):
        sink_pad_index = f'sink_{sink_pad_index}'
    else:
        # Already a string, use as-is
        sys.stderr.write('warning: sink pad name is not an integer, using provided name\n')
    
    src_pad = get_static_pad(src, src_pad_name)
    sink_pad = get_request_pad(sink, sink_pad_index)
    
    if src_pad and sink_pad:
        ret = src_pad.link(sink_pad)
        if ret != Gst.PadLinkReturn.OK:
            sys.stderr.write(
                f'error: pad link error, src: {src.get_name()} pad: {src_pad_name}, '
                f'sink: {sink.get_name()} pad: {sink_pad_index}\n'
            )
    else:
        sys.stderr.write(
            f'error: pad link error, src: {src.get_name()} pad: {src_pad_name}, '
            f'sink: {sink.get_name()} pad: {sink_pad_index}\n'
        )


def link_request_srcpad_to_static_sinkpad(src, sink, src_pad_index=None, sink_pad_index=None):
    """
    Link a request source pad to a static sink pad
    Used for connecting demuxers/tees to regular elements
    
    :param src: Source element (needs request src pad)
    :param sink: Sink element (has static sink pad)
    :param src_pad_index: Index for the source request pad (optional)
    :param sink_pad_index: Index for the sink static pad (optional)
    
    VERIFIED: Exact logic from original
    """
    request_pad_index = 0
    
    if src_pad_index is None:
        src_pad_index = 'src_%u'
    elif isinstance(src_pad_index, int):
        src_pad_index = f'src_%u' % src_pad_index
    
    if sink_pad_index is None:
        sink_pad_index = 'sink'
    elif isinstance(sink_pad_index, int):
        sink_pad_index = f'sink_%u' % sink_pad_index
    
    try:
        src_pad = get_request_pad(src, src_pad_index)
        sink_pad = get_static_pad(sink, sink_pad_index)
        
        if src_pad and sink_pad:
            ret = src_pad.link(sink_pad)
            if ret != Gst.PadLinkReturn.OK:
                sys.stderr.write(
                    f'error: pad link error, src: {src.get_name()} pad: {src_pad_index}, '
                    f'sink: {sink.get_name()} pad: {sink_pad_index}\n'
                )
        else:
            sys.stderr.write(
                f'error: pad link error, src: {src.get_name()} pad: {src_pad_index}, '
                f'sink: {sink.get_name()} pad: {sink_pad_index}\n'
            )
    except Exception as e:
        sys.stderr.write(f'error: {e}\n')
        sys.stderr.write(
            f'error: pad link error, src: {src.get_name()} pad: {src_pad_index}, '
            f'sink: {sink.get_name()} pad: {sink_pad_index}\n'
        )
        raise e