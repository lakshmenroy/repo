# SmartAssist Pipeline Application

Main AI inference pipeline for garbage detection, nozzle monitoring, and Clean Street Index (CSI) computation.

## Overview

The pipeline application runs on Syslogic hardware with NVIDIA Jetson Orin processors, processing video from 4 CSI cameras:
- **Front camera**: Road view for CSI computation
- **Rear camera**: Road view for CSI computation  
- **Primary nozzle camera**: Left nozzle monitoring
- **Secondary nozzle camera**: Right nozzle monitoring

## Architecture
```
src/
├── main.py                    # Entry point
├── detection_categories.py    # Detection class definitions
├── context.py                 # Application context & state
├── pipeline/                  # GStreamer pipeline modules
│   ├── builder.py            # Pipeline construction
│   ├── elements.py           # Element creation
│   ├── bins.py               # Complex bin creation
│   ├── probes.py             # Buffer probes & callbacks
│   └── linking.py            # Pad linking utilities
├── camera/                    # Camera management
│   ├── manager.py            # Camera initialization
│   └── source.py             # Source element creation
├── can/                       # CAN bus communication
│   ├── client.py             # CAN client
│   ├── server.py             # CAN server
│   └── state_machine.py      # Nozzle control state machine
├── csi/                       # Clean Street Index
│   ├── computation.py        # CSI calculation
│   └── probes.py             # CSI buffer probes
├── logging/                   # CSV/Video logging
│   ├── csv_logger.py         # CSV data logging
│   └── video_logger.py       # Video recording
├── monitoring/                # Background threads
│   └── threads.py            # System monitoring
└── utils/                     # Utilities
    ├── systemd.py            # Systemd notifications
    ├── config.py             # Configuration loading
    └── helpers.py            # Helper functions
```

## Running

### Standalone Mode
```bash
cd /opt/smartassist/apps/pipeline/src
python3 main.py
```

### Via Systemd Service
```bash
sudo systemctl start bucher-smart-sweeper.service
sudo journalctl -u bucher-smart-sweeper -f
```

## Configuration

**Main Pipeline Config**: `config/pipeline_config.yaml`  
- Model paths
- Inference settings
- Pipeline parameters

**Camera Config**: `config/camera_config.json`  
- Camera initialization
- Sensor settings
- V4L2 parameters

**Logging Config**: `config/logging_config.yaml`  
- CSV column definitions
- Log duration
- Output directories
- CAN signal mapping

**DeepStream Configs**: `config/deepstream/`  
- `preprocess.txt` - Preprocessing settings
- `inference.txt` - Nozzlenet inference config
- `metamux.txt` - Metadata multiplexing
- `tracker.yml` - Object tracking

**CSI Config**: `config/csi_config.yaml`  
- Road/garbage model parameters
- Discrete CSI levels
- Filtering masks

## Models

Models are loaded from paths defined in the root `manifest.yaml`:

- **Nozzlenet**: `../../models/nozzlenet/{version}/`
- **Road Segmentation**: `../../models/resnet/{version}/`
- **Garbage Segmentation**: `../../models/resnet/{version}/`

Current production versions are specified in `config/pipeline_config.yaml`.

## Output

### CSV Logs
Location: `/mnt/syslogic_sd_card/upload/csv/`  
Format: `{DATA_TYPE}_{VEHICLE_TYPE}_{VEHICLE_ID}_{TIMESTAMP}.csv`

Columns: time, confidence, nozzle_clear, nozzle_blocked, check_nozzle, gravel, action_object, sm_current_state, + CAN signals

### Inference Videos
Location: `/mnt/syslogic_sd_card/upload/video/`  
Format: 20-minute H.265 chunks with splitmuxsink
Filename: `VIDEO_LOW_MANUAL_{VEHICLE_TYPE}_{VEHICLE_ID}_{TIMESTAMP}.mp4`

## GStreamer Pipeline
```
nvarguscamerasrc (x4) 
→ nvstreammux 
→ nvdspreprocess 
→ nvinfer (nozzlenet) 
→ nvstreamdemux
→ [CSI Path]: nvstreammux → nvinfer (road) → nvinfer (garbage) → nvsegvisual
→ [Video Path]: nvstreammux → nvmultistreamtiler → nvdsosd → splitmuxsink
```

## CAN Bus Integration

The pipeline communicates with the CAN server via Unix socket (`/tmp/can_server.sock`):

- Sends nozzle state updates (clear/blocked/check/gravel)
- Sends fan speed requests
- Receives PM sensor data for OSD overlay
- Monitors system health (FPS, camera status)

## Dependencies

- GStreamer 1.0 with DeepStream SDK 6.2
- NVIDIA Jetson Linux (L4T)
- Python 3.8+
- PyGObject, numpy, opencv-python
- python-can, cantools

See `requirements.txt` for complete list.

## Testing
```bash
cd apps/pipeline
pytest tests/ -v
```

## Troubleshooting

**Pipeline won't start:**
- Check camera initialization: `sudo systemctl status bucher-d3-camera-init`
- Verify models exist at configured paths
- Check argus daemon: `sudo systemctl status nvargus-daemon`

**No CAN communication:**
- Verify CAN server is running: `ps aux | grep can_server`
- Check socket exists: `ls -l /tmp/can_server.sock`

**Low FPS:**
- Check GPU usage: `tegrastats`
- Verify model engine files are compiled for correct GPU
- Check for thermal throttling

## See Also

- [Models Documentation](../../models/README.md)
- [OTA Uploader](../../ota-uploader/README.md)
- [Services Documentation](../services/README.md)