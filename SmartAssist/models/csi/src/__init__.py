"""
CSI (Clean Street Index) Module
Clean Street Index computation from road and garbage segmentation

This module provides:
- CSI computation algorithms (compute_csi, get_discrete_csi)
- Filtering mask creation (create_filtering_masks)
- Weight matrix generation (get_weight_matrix_linspace)
- Buffer probe for DeepStream integration (compute_csi_buffer_probe)
- CSI probe bin creation (create_csiprobebin)
"""
from .constants import (
    ROAD_UNIQUE_ID,
    GARBAGE_UNIQUE_ID,
    ROAD_CLASS_IDS,
    GARBAGE_CLASS_IDS,
    DEFAULT_N_BINS,
    DEFAULT_LINSP_START,
    DEFAULT_LINSP_STOP,
    DEFAULT_PERCENTAGE_DIRTY_ROAD,
    DEFAULT_GARBAGE_TYPE_COEFFS,
    DEFAULT_SMOOTH,
    DEFAULT_CLIP_CSI,
    FRONT_CSI_LEVELS,
    REAR_CSI_LEVELS
)

from .computation import (
    compute_csi,
    create_filtering_masks,
    get_discrete_csi,
    get_weight_matrix_linspace,
    find_xmin_xmax
)

from .probes import (
    compute_csi_buffer_probe,
    display_masks
)

from .bins import (
    create_csiprobebin
)

__all__ = [
    # Constants
    'ROAD_UNIQUE_ID',
    'GARBAGE_UNIQUE_ID',
    'ROAD_CLASS_IDS',
    'GARBAGE_CLASS_IDS',
    'DEFAULT_N_BINS',
    'DEFAULT_LINSP_START',
    'DEFAULT_LINSP_STOP',
    'DEFAULT_PERCENTAGE_DIRTY_ROAD',
    'DEFAULT_GARBAGE_TYPE_COEFFS',
    'DEFAULT_SMOOTH',
    'DEFAULT_CLIP_CSI',
    'FRONT_CSI_LEVELS',
    'REAR_CSI_LEVELS',
    
    # Computation functions
    'compute_csi',
    'create_filtering_masks',
    'get_discrete_csi',
    'get_weight_matrix_linspace',
    'find_xmin_xmax',
    
    # Buffer probes
    'compute_csi_buffer_probe',
    'display_masks',
    
    # Bin creation
    'create_csiprobebin',
]