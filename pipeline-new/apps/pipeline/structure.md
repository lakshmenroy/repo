# Pipeline Structure Overview

This document explains the organization of the pipeline application.

## Directory Structure
```
apps/pipeline/
├── src/                           # Source code
│   ├── __init__.py
│   ├── main.py                   # Entry point (~200 lines)
│   ├── detection_categories.py   # Detection class enum
│   ├── context.py                # AppContext, Config, GETFPS
│   │
│   ├── pipeline/                 # GStreamer pipeline construction
│   │   ├── __init__.py
│   │   ├── builder.py           # Pipeline builder
│   │   ├── elements.py          # Element creation
│   │   ├── bins.py              # Complex bins (inference, CSI, UDP)
│   │   ├── probes.py            # Buffer probes & callbacks
│   │   └── linking.py           # Pad linking utilities
│   │
│   ├── camera/                   # Camera management
│   │   ├── __init__.py
│   │   ├── manager.py           # Camera initialization
│   │   └── source.py            # Source element creation
│   │
│   ├── can/                      # CAN bus communication
│   │   ├── __init__.py
│   │   ├── client.py            # CAN client
│   │   ├── server.py            # CAN server (separate process)
│   │   └── state_machine.py     # Nozzle control state machine
│   │
│   ├── csi/                      # Clean Street Index
│   │   ├── __init__.py
│   │   └── probes.py            # CSI computation probes
│   │
│   ├── monitoring/               # Background threads
│   │   ├── __init__.py
│   │   └── threads.py           # Overlay, monitoring, socket server
│   │
│   └── utils/                    # Utilities
│       ├── __init__.py
│       ├── systemd.py           # Systemd notifications
│       ├── config.py            # YAML config loader
│       └── helpers.py           # Helper functions
│
├── config/                       # Configuration files
│   ├── pipeline_config.yaml     # Main pipeline config
│   ├── camera_config.json       # Camera initialization
│   ├── logging_config.yaml      # Logging settings
│   ├── csi_config.yaml          # CSI parameters
│   └── deepstream/              # DeepStream configs
│       ├── config_preprocess.txt
│       ├── infer_config.txt
│       ├── config_metamux.txt
│       ├── tracker_config.yml
│       ├── road_config.txt
│       └── garbage_config.txt
│
├── systemd/                      # Systemd service files
│   └── bucher-smart-sweeper.service
│
├── tests/                        # Unit tests
│   ├── __init__.py
│   └── test_pipeline.py
│
├── requirements.txt              # Python dependencies
├── .gitignore
├── README.md                     # User documentation
├── DEPLOYMENT.md                 # Deployment guide
└── STRUCTURE.md                  # This file
```

## Module Responsibilities

### `main.py`
- Application entry point
- Signal handling (SIGINT, SIGTERM)
- GStreamer bus callbacks
- Context initialization
- Main loop management

### `pipeline/`
**builder.py**: Constructs complete pipeline
- Links camera bin → inference bin → tiler → OSD → sink
- Bus message handling

**elements.py**: Element creation with auto-naming
- Wraps `Gst.ElementFactory.make()`
- Maintains global counter for unique names

**bins.py**: Complex bin creation
- `create_inference_bin()`: Main inference pipeline
- `create_csiprobebin()`: CSI computation bin
- `create_udpsinkbin()`: RTSP/UDP streaming
- `create_multi_argus_camera_bin()`: Multi-camera source

**probes.py**: Buffer probes
- `nozzlenet_src_pad_buffer_probe()`: Processes nozzlenet detections
- `buffer_monitor_probe()`: Monitors camera activity

**linking.py**: Pad linking utilities
- `link_static_srcpad_pad_to_request_sinkpad()`
- `link_request_srcpad_to_static_sinkpad()`
- `get_static_pad()`, `get_request_pad()`

### `camera/`
**manager.py**: Camera initialization
- `CameraManager`: Manages multiple cameras
- `initialize_cameras()`: Sets up cameras with V4L2 settings
- `create_multi_argus_camera_bin()`: Creates source bin

**source.py**: Source element creation
- `make_argus_camera_source()`: Creates nvarguscamerasrc
- `make_bucher_ds_filesrc()`: Creates filesrc for testing

### `can/`
**client.py**: CAN client (runs in pipeline process)
- Connects to CAN server via Unix socket
- Sends nozzle state, FPS, detections
- Receives PM sensor data

**server.py**: CAN server (separate process, not in this app)
- Manages CAN bus communication
- Handles multiple clients
- Sends CAN messages to vehicle

**state_machine.py**: Nozzle control logic
- Tracks nozzle state (clear/blocked/check/gravel)
- Calculates fan speed
- Maintains state history

### `csi/`
**probes.py**: CSI computation
- Processes road/garbage segmentation
- Computes Clean Street Index
- Logs CSI values

### `monitoring/`
**threads.py**: Background threads
- `overlay_parts_fetcher()`: Updates OSD data
- `override_monitoring()`: Checks manual override
- `unix_socket_server()`: IPC for pipeline control

### `utils/`
**systemd.py**: Systemd integration
- `notify_systemd()`: Sends status to systemd
- `load_latest_init_status()`: Loads camera init results

**config.py**: Configuration loading
- `Configuration`: Loads logging_config.yaml
- Provides getters for columns, paths, settings

**helpers.py**: Utility functions
- `modify_deepstream_config_files()`: Updates INI configs
- `demuxer_pad_added()`: Dynamic pad callback

### `context.py`
**Config**: Loads camera_config.json
**AppContext**: Manages application state
**GETFPS**: FPS counter utility

## Data Flow
```
Cameras (nvarguscamerasrc)
    ↓
Multi-camera bin (nvstreammux)
    ↓
Inference bin
    ├→ Nozzlenet path (primary/secondary nozzle)
    │   ├→ nvdspreprocess
    │   ├→ nvinfer (nozzlenet)
    │   └→ Probe: nozzlenet_src_pad_buffer_probe
    │       └→ Updates state machine
    │       └→ Sends CAN data
    │
    └→ CSI path (front/rear)
        ├→ nvstreammux
        ├→ nvinfer (road segmentation)
        ├→ nvinfer (garbage segmentation)
        ├→ nvsegvisual
        └→ Probe: compute_csi_buffer_probe
            └→ Logs CSI values
    ↓
nvdsmetamux (combines metadata)
    ↓
Tiler (nvmultistreamtiler)
    ↓
OSD (nvdsosd)
    ↓
Encoder (nvv4l2h265enc)
    ↓
UDP sink (RTSP streaming)
```

## Configuration Flow
```
main.py
    ├→ Loads camera_config.json (Config)
    ├→ Loads pipeline_config.yaml
    ├→ Loads logging_config.yaml (Configuration)
    └→ Initializes AppContext
        └→ Stored in GStreamer Structure
            └→ Passed to all components
```

## Key Design Patterns

1. **GStreamer Structure for Context**: Uses `Gst.Structure` as global context
2. **Modular Bins**: Complex functionality in separate bins
3. **Probes for Processing**: Buffer probes for inference results
4. **IPC via Unix Sockets**: CAN communication via sockets
5. **Background Threads**: Monitoring, overlay, control server
6. **Systemd Integration**: Type=notify service with watchdog

## File Size Guidelines

- Entry point (`main.py`): ~200 lines
- Module files: 200-400 lines each
- Bin creation (`bins.py`): ~600 lines (most complex)
- Total source: ~3000 lines (was 5000+ monolithic)

## Testing

Run tests:
```bash
cd apps/pipeline
pytest tests/ -v
```

## Dependencies

See `requirements.txt` for Python packages.

Key dependencies:
- GStreamer 1.0
- DeepStream SDK 6.2
- PyGObject
- python-can
- PyYAML