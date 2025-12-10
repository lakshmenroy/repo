"""
Detection Categories for NozzleNet
Enum mapping for object detection class IDs
"""
from enum import Enum


class DETECTION_CATEGORIES(Enum):
    """Object detection class IDs for nozzlenet model"""
    PGIE_CLASS_ID_BACKGROUND = 0
    PGIE_CLASS_ID_ACTION_OBJECT = 1
    PGIE_CLASS_ID_EMPTY = 2
    PGIE_CLASS_ID_CHECK_NOZZLE = 2  # Same as EMPTY
    PGIE_CLASS_ID_GRAVEL = 3
    PGIE_CLASS_ID_NOZZLE_BLOCKED = 4
    PGIE_CLASS_ID_NOZZLE_CLEAR = 5