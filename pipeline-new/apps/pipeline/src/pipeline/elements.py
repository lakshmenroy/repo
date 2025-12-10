"""
GStreamer Element Creation
Utilities for creating pipeline elements with unique naming
"""
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

# Global counter for element naming
_element_counter = {}


def make_element(element_name, specific_name=None):
    """
    Create a GStreamer element with unique naming
    
    :param element_name: GStreamer element type (e.g., 'nvstreammux', 'queue')
    :param specific_name: Optional custom name (string or int)
    :return: GStreamer element or None
    """
    element = Gst.ElementFactory.make(element_name, element_name)
    if not element:
        sys.stderr.write(f'Unable to create {element_name}\n')
        return None
    
    if specific_name:
        if isinstance(specific_name, str):
            element.set_property('name', f'{specific_name}')
        elif isinstance(specific_name, int):
            element.set_property('name', f'{element_name}_{specific_name}')
        else:
            sys.stderr.write('specific_name should be a string or an integer\n')
            return None
    else:
        # Auto-increment counter for unique naming
        if element_name not in _element_counter:
            _element_counter[element_name] = 0
        _element_counter[element_name] += 1
        element.set_property('name', f'{element_name}_{_element_counter[element_name]}')
    
    return element