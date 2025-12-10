# Deployment Guide

## Prerequisites

### Hardware
- Syslogic A4GX with NVIDIA Jetson Orin NX
- 4x GMSL2 cameras (D3 cameras from Allied Vision)
- CAN interface connected

### Software
- JetPack 6.2.1 (L4T 35.x)
- DeepStream SDK 6.2+
- Python 3.8+
- GStreamer 1.20+

## Installation

### 1. Install System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install DeepStream
cd /opt/nvidia/deepstream/deepstream
sudo ./install.sh

# Install Python dependencies
sudo apt install python3-pip python3-gi python3-dev python3-gst-1.0
sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-good
sudo apt install gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
sudo apt install libgstrtspserver-1.0-dev

# Install build tools
sudo apt install build-essential cmake pkg-config
```

### 2. Install Python Packages
```bash
cd /opt/smartassist/apps/pipeline
pip3 install -r requirements.txt --break-system-packages
```

### 3. Install DeepStream Python Bindings
```bash
cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/bindings
python3 setup.py install --user
```

### 4. Deploy Configuration Files
```bash
# Copy configs to system location
sudo mkdir -p /mnt/ssd/csi_pipeline/config
sudo cp -r config/* /mnt/ssd/csi_pipeline/config/

# Update paths in config files if needed
sudo nano /mnt/ssd/csi_pipeline/config/pipeline_config.yaml
```

### 5. Deploy Models

Models should be deployed via the monorepo model system. Ensure:
- Nozzlenet model at `/mnt/ssd/model_repository/nozzlenet-v2/{version}/`
- Road segmentation model at `/mnt/ssd/csi_pipeline/models/road_segmentation/`
- Garbage segmentation model at `/mnt/ssd/csi_pipeline/models/garbage_segmentation/`

### 6. Install Systemd Service
```bash
# Copy service file
sudo cp systemd/bucher-smart-sweeper.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable bucher-smart-sweeper.service
```

## Starting the Pipeline

### Manual Start (for testing)
```bash
cd /opt/smartassist/apps/pipeline/src
python3 main.py
```

### Via Systemd
```bash
# Start service
sudo systemctl start bucher-smart-sweeper

# Check status
sudo systemctl status bucher-smart-sweeper

# View logs
sudo journalctl -u bucher-smart-sweeper -f
```

## Verification

### 1. Check Camera Initialization
```bash
sudo systemctl status bucher-d3-camera-init
ls /dev/video*  # Should show video0-video7
```

### 2. Check Pipeline Status
```bash
# View pipeline logs
sudo journalctl -u bucher-smart-sweeper -n 100

# Check CAN communication
ls -l /tmp/can_server.sock

# Check output files
ls -lh /mnt/syslogic_sd_card/upload/csv/
ls -lh /mnt/syslogic_sd_card/upload/video/
```

### 3. Monitor Performance
```bash
# GPU stats
tegrastats

# Check FPS
sudo journalctl -u bucher-smart-sweeper | grep "fps"
```

## Troubleshooting

### Pipeline won't start
```bash
# Check argus daemon
sudo systemctl status nvargus-daemon
sudo systemctl restart nvargus-daemon

# Check camera service
sudo systemctl status bucher-d3-camera-init

# Check model files exist
ls -l /mnt/ssd/model_repository/nozzlenet-v2/V253/
```

### No video output
```bash
# Check if splitmuxsink is writing
ls -lh /mnt/syslogic_sd_card/upload/video/

# Check disk space
df -h /mnt/syslogic_sd_card/
```

### CAN bus not working
```bash
# Check CAN server
ps aux | grep can_server

# Check socket
ls -l /tmp/can_server.sock

# Check CAN interface
ip link show can0
```

### Low FPS

- Check thermal throttling: `cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq`
- Verify GPU clock: `sudo jetson_clocks --show`
- Set max performance: `sudo jetson_clocks`

## Updates

To update the pipeline:
```bash
# Stop service
sudo systemctl stop bucher-smart-sweeper

# Pull latest code
cd /opt/smartassist
git pull

# Update configs if needed
sudo cp -r apps/pipeline/config/* /mnt/ssd/csi_pipeline/config/

# Restart service
sudo systemctl start bucher-smart-sweeper
```

## Logs

- **Systemd logs**: `sudo journalctl -u bucher-smart-sweeper -f`
- **Pipeline logs**: `/var/log/syslog`
- **CSV logs**: `/mnt/syslogic_sd_card/upload/csv/`
- **Videos**: `/mnt/syslogic_sd_card/upload/video/`

## Configuration Locations

- **Camera config**: `/mnt/ssd/csi_pipeline/config/camera_config.json`
- **Pipeline config**: `/mnt/ssd/csi_pipeline/config/pipeline_config.yaml`
- **Logging config**: `/mnt/ssd/csi_pipeline/config/logging_config.yaml`
- **DeepStream configs**: `/mnt/ssd/csi_pipeline/config/deepstream/`