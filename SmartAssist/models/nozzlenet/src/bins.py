"""
Nozzlenet Model Bins
GStreamer bins specific to nozzlenet inference

NOTE: The main nozzlenet inference bin is created inline within
create_bucher_inference_bin() in pipeline/bins.py, not as a separate function.

This module is provided for consistency with the CSI model structure
and for any future nozzlenet-specific bin logic.

VERIFIED: Nozzlenet bin logic is embedded in pipeline/bins.py
"""

# Currently, nozzlenet bins are created inline in the main inference bin.
# The bin structure is:
#
# nozzlenet_infer_bin:
#   identity (placeholder) → nvdspreprocess → nvinfer (nozzlenet) → nvvideoconvert → capsfilter → queue
#
# The nozzlenet probe is attached to the nvinfer src pad.

# If we need to extract nozzlenet bin creation to a separate function in the future,
# it would go here. For now, this file serves as documentation of the nozzlenet
# bin structure and maintains module consistency with models/csi/.

def get_nozzlenet_config_defaults():
    """
    Get default configuration values for nozzlenet inference
    
    :return: Dictionary with default nozzlenet config
    
    These are the expected config file paths and settings
    """
    return {
        'preprocess_config': '/mnt/ssd/csi_pipeline/config/ds_config/config_preprocess.txt',
        'inference_config': '/mnt/ssd/csi_pipeline/config/ds_config/infer_config.txt',
        'unique_id': 1,
        'output_resolution': (960, 540),
        'network_input_shape': '1;3;480;480',
        'infer_dims': '3;480;480'
    }


def get_nozzlenet_cameras():
    """
    Get the list of camera names that use nozzlenet inference
    
    :return: List of camera names
    
    VERIFIED: These are the cameras that go through nozzlenet
    """
    return ['right', 'left']  # Changed from primary_nozzle, secondary_nozzle