"""
Helper Utilities
Miscellaneous utility functions for pipeline operations

VERIFIED: Exact functionality from original pipeline_w_logging.py
"""
import configparser
import os


def modify_deepstream_config_files(input_file, output_file, section, key, value, app_context=None):
    """
    Modify DeepStream config files (INI format)
    Used to update paths and parameters in DeepStream config files at runtime
    
    :param input_file: Path to input config file
    :param output_file: Path to output config file (can be same as input)
    :param section: Config section name (e.g., 'property', 'group-0')
    :param key: Config key to modify (e.g., 'model-engine-file')
    :param value: New value to set
    :param app_context: Application context for logging
    
    VERIFIED: Exact logic from original
    """
    if app_context:
        logger = app_context.get_value('app_context_v2').logger
        logger.debug(f'Modifying {input_file}: [{section}] {key} = {value}')
    
    # Read existing config
    config = configparser.ConfigParser()
    config.read(input_file)
    
    # Add section if doesn't exist
    if not config.has_section(section):
        config.add_section(section)
    
    # Set value
    config.set(section, key, str(value))
    
    # Write modified config
    with open(output_file, 'w') as f:
        config.write(f)


def demuxer_pad_added(context, pad, target_sinkpad):
    """
    Callback for dynamic pad linking when demuxer creates new pads
    Used for filesrc bin to handle video stream detection
    
    :param context: Demuxer element (qtdemux)
    :param pad: New pad that was added
    :param target_sinkpad: Target sink pad to link to (queue sink pad)
    
    VERIFIED: Exact logic from original
    """
    # Query pad capabilities
    string = pad.query_caps(None).to_string()
    
    # Link based on codec type
    if string.startswith('video/x-h265'):
        print('Linking demuxer src pad to source queue sink pad (h265)')
        pad.link(target_sinkpad)
    elif string.startswith('video/x-h264'):
        print('Linking demuxer src pad to source queue sink pad (h264)')
        pad.link(target_sinkpad)
    else:
        print(f'Error: video/x-h264 stream not found, string: {string}')