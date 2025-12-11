"""
Pipeline Module
GStreamer pipeline construction and management
"""
from .elements import make_element
from .linking import (
    get_static_pad,
    get_request_pad,
    link_static_srcpad_pad_to_request_sinkpad,
    link_request_srcpad_to_static_sinkpad
)

__all__ = [
    'make_element',
    'get_static_pad',
    'get_request_pad',
    'link_static_srcpad_pad_to_request_sinkpad',
    'link_request_srcpad_to_static_sinkpad'
]