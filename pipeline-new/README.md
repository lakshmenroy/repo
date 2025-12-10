truck-ai-stack/
├── apps/
│   ├── pipeline/                          # Main inference pipeline
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                    # Entry point (clean, ~200 lines)
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── context.py             # AppContext, shared state
│   │   │   │   ├── config.py              # Configuration loading
│   │   │   │   └── constants.py           # Detection categories, enums
│   │   │   ├── gstreamer/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── pipeline_builder.py    # Build main pipeline
│   │   │   │   ├── elements.py            # Element creation helpers
│   │   │   │   ├── bins/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── inference_bin.py   # Nozzlenet inference bin
│   │   │   │   │   ├── csi_bin.py         # CSI probe bin
│   │   │   │   │   ├── source_bin.py      # Multi-camera source bin
│   │   │   │   │   └── output_bin.py      # File/network output bin
│   │   │   │   ├── pads/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── linking.py         # Pad linking utilities
│   │   │   │   └── probes/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── nozzlenet_probe.py # Nozzlenet detection probe
│   │   │   │       ├── csi_probe.py       # CSI computation probe
│   │   │   │       └── monitor_probe.py   # Buffer monitoring probe
│   │   │   ├── camera/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── manager.py             # CameraManager class
│   │   │   │   ├── source.py              # Camera source creation
│   │   │   │   └── v4l2.py                # v4l2-ctl wrapper
│   │   │   ├── can/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py              # CanClient (refactored)
│   │   │   │   ├── server.py              # CanServer (refactored)
│   │   │   │   └── state_machine.py       # SmartStateMachine (refactored)
│   │   │   ├── logging/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── csv_logger.py          # CSV logging logic
│   │   │   │   └── video_logger.py        # Video recording logic
│   │   │   ├── monitoring/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── threads.py             # Background monitoring threads
│   │   │   │   └── overlay.py             # OSD overlay updates
│   │   │   └── utils/
│   │   │       ├── __init__.py
│   │   │       ├── systemd.py             # Systemd integration
│   │   │       ├── paths.py               # Path resolution
│   │   │       └── helpers.py             # General utilities
│   │   ├── config/
│   │   │   ├── pipeline_config.yaml       # Main pipeline config
│   │   │   ├── camera_config.json         # Camera configuration
│   │   │   ├── logging_config.yaml        # Logging settings
│   │   │   └── deepstream/
│   │   │       ├── preprocess.txt         # Preprocessing config
│   │   │       ├── inference.txt          # Inference config
│   │   │       ├── tracker.yml            # Tracker config
│   │   │       ├── metamux.txt            # Metamux config
│   │   │       └── nms.txt                # NMS config
│   │   ├── systemd/
│   │   │   └── bucher-smart-sweeper.service
│   │   ├── scripts/
│   │   │   └── debug_pipeline.py          # Pipeline debugging tool
│   │   ├── tests/
│   │   │   ├── test_pipeline_builder.py
│   │   │   ├── test_inference_bin.py
│   │   │   └── test_can_client.py
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   └── services/                          # System services
│       ├── camera-init/
│       │   ├── src/
│       │   │   ├── __init__.py
│       │   │   └── main.py                # Camera init script (refactored)
│       │   ├── config/
│       │   │   └── camera_config.json
│       │   ├── systemd/
│       │   │   └── bucher-camera-init.service
│       │   └── README.md
│       ├── can-init/
│       │   ├── systemd/
│       │   │   ├── bucher-can-init-250k.service
│       │   │   └── bucher-can-deinit.service
│       │   └── README.md
│       ├── heartbeat/
│       │   ├── src/
│       │   │   ├── check-services.sh
│       │   │   ├── check-camera-service.sh
│       │   │   └── syslogic-heartbeat.sh
│       │   ├── systemd/
│       │   │   ├── bucher-syslogic-heartbeat.service
│       │   │   └── bucher-syslogic-heartbeat.timer
│       │   └── README.md
│       └── serial-number/
│           ├── src/
│           │   └── set_serial_number.py
│           ├── systemd/
│           │   └── bucher-collect-jcm-serial-number.service
│           └── README.md
│
├── models/                                # Model repository
│   ├── csi/                               # CSI models (MOVED OUT OF PIPELINE)
│   │   ├── v1.0.0/
│   │   │   ├── road_segmentation.onnx
│   │   │   ├── garbage_segmentation.onnx
│   │   │   ├── metadata.yaml
│   │   │   ├── labels.txt
│   │   │   └── README.md
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── csi_computation.py         # CSI computation logic
│   │       ├── csi_utils.py               # CSI utilities
│   │       ├── filtering.py               # Mask creation
│   │       ├── probes/
│   │       │   ├── __init__.py
│   │       │   └── csi_buffer_probe.py
│   │       └── config/
│   │           └── csi_config.yaml
│   ├── nozzlenet/
│   │   └── v2.5.4/
│   │       ├── model.plan
│   │       ├── metadata.yaml
│   │       ├── labels.txt
│   │       └── README.md
│   └── resnet/
│       └── v2.5.4/
│           ├── model.onnx
│           ├── metadata.yaml
│           └── README.md
│
├── ota-uploader/                          # OTA uploader (runs on truck)
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                        # Uploader main
│   │   ├── log_uploader.py                # CSV upload logic
│   │   ├── video_uploader.py              # Video upload logic
│   │   └── utils.py
│   ├── config/
│   │   └── uploader_config.json.example
│   ├── systemd/
│   │   └── smartassist-uploader.service
│   ├── requirements.txt
│   └── README.md
│
├── scripts/                               # Development/deployment scripts
│   ├── validate-deployment.sh
│   ├── bump-versions.py
│   └── post-training-push.sh
│
├── .github/
│   └── workflows/
│       ├── test-pipeline.yml
│       ├── validate-models.yml
│       └── release.yml
│
├── manifest.yaml                          # Version manifest
├── .gitignore
├── .gitattributes                         # Git LFS config
└── README.md
