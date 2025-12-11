"""
GStreamer Element Creation
Factory functions for creating pipeline elements with unique naming

VERIFIED: Exact functionality from original pipeline_w_logging.py
"""
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst


def make_element(element_name, specific_name=None):
    """
    Create a GStreamer element with unique naming
    Essential for pipeline construction - prevents naming conflicts
    
    :param element_name: GStreamer element type (e.g., 'nvstreammux', 'queue')
    :param specific_name: Optional custom name (string or int for indexing)
    :return: GStreamer element or None
    
    VERIFIED: Exact logic from original
    """
    element = Gst.ElementFactory.make(element_name, element_name)
    if not element:
        sys.stderr.write(f' Unable to create {element_name}\n')
        return None
    
    if specific_name:
        if isinstance(specific_name, str):
            element.set_property('name', f'{specific_name}')
            return element
        if isinstance(specific_name, int):
            element.set_property('name', f'{element_name}_{specific_name}')
            return element
        sys.stderr.write('specific_name should be a string or an integer\n')
        return None
    
    return element