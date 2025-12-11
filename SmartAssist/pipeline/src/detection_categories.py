"""
Detection Categories for NozzleNet Model
Enum mapping for object detection class IDs

VERIFIED: Exact copy from original pipeline_w_logging.py
"""
from enum import Enum


class DETECTION_CATEGORIES(Enum):
    """
    Object detection class IDs for nozzlenet model
    These map to the output classes from the neural network
    """
    PGIE_CLASS_ID_BACKGROUND = 0
    PGIE_CLASS_ID_ACTION_OBJECT = 1
    PGIE_CLASS_ID_EMPTY = 2
    PGIE_CLASS_ID_CHECK_NOZZLE = 2  # Same as EMPTY
    PGIE_CLASS_ID_GRAVEL = 3
    PGIE_CLASS_ID_NOZZLE_BLOCKED = 4
    PGIE_CLASS_ID_NOZZLE_CLEAR = 5