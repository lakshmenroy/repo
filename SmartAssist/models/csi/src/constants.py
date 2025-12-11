"""
CSI (Clean Street Index) Constants
Unique IDs and configuration values for CSI computation

VERIFIED: Exact values from original pipeline/csi/
"""

# Unique IDs for DeepStream inference engines - VERIFIED
ROAD_UNIQUE_ID = 2      # Road segmentation model unique ID
GARBAGE_UNIQUE_ID = 3   # Garbage segmentation model unique ID

# CSI class IDs - VERIFIED from csi_config.yaml
ROAD_CLASS_IDS = [0, 1]         # Background, Road
GARBAGE_CLASS_IDS = [0, 1, 2]   # Background, Foliage, Waste

# CSI computation defaults - can be overridden by config
DEFAULT_N_BINS = 48
DEFAULT_LINSP_START = 0.7
DEFAULT_LINSP_STOP = 1.0
DEFAULT_PERCENTAGE_DIRTY_ROAD = 0.5
DEFAULT_GARBAGE_TYPE_COEFFS = [0.6, 0.7]  # [foliage_coeff, waste_coeff]
DEFAULT_SMOOTH = 2.0e-22
DEFAULT_CLIP_CSI = False

# Discrete CSI levels for front/rear cameras
# Front: 21 levels (0.0 to 1.0)
# Rear: 5 levels (0.0 to 1.0)
FRONT_CSI_LEVELS = 21
REAR_CSI_LEVELS = 5