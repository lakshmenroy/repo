"""
Helper Utilities
Miscellaneous utility functions
"""
import configparser
import os


def modify_deepstream_config_files(input_file, output_file, section, key, value, app_context=None):
    """
    Modify DeepStream config files (INI format)
    
    :param input_file: Path to input config file
    :param output_file: Path to output config file
    :param section: Config section name
    :param key: Config key to modify
    :param value: New value
    :param app_context: Application context for logging
    """
    if app_context:
        logger = app_context.get_value('app_context_v2').logger
        logger.debug(f'Modifying {input_file}: [{section}] {key} = {value}')
    
    config = configparser.ConfigParser()
    config.read(input_file)
    
    if not config.has_section(section):
        config.add_section(section)
    
    config.set(section, key, str(value))
    
    with open(output_file, 'w') as f:
        config.write(f)


def demuxer_pad_added(context, pad, target_sinkpad):
    """
    Callback for dynamic pad linking when demuxer creates new pads
    
    :param context: Demuxer element
    :param pad: New pad that was added
    :param target_sinkpad: Target sink pad to link to
    """
    string = pad.query_caps(None).to_string()
    if string.startswith('video/x-h265'):
        print('Linking demuxer src pad to source queue sink pad (h265)')
        pad.link(target_sinkpad)
    elif string.startswith('video/x-h264'):
        print('Linking demuxer src pad to source queue sink pad (h264)')
        pad.link(target_sinkpad)
    else:
        print(f'Error: video/x-h264 stream not found, string: {string}')