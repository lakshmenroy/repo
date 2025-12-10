#!/usr/bin/env python3
"""
Structure Verification Script
Verifies that all refactored files exist with correct structure
"""
import sys
from pathlib import Path

def verify_structure():
    """Verify the refactored pipeline structure"""
    
    # Get pipeline root
    script_dir = Path(__file__).resolve().parent
    pipeline_root = script_dir
    
    print("=" * 70)
    print("VERIFYING REFACTORED PIPELINE STRUCTURE")
    print("=" * 70)
    print(f"\nPipeline Root: {pipeline_root}\n")
    
    # Define expected structure
    expected_files = [
        # Source files
        "src/__init__.py",
        "src/main.py",
        "src/detection_categories.py",
        "src/context.py",
        
        # Pipeline module
        "src/pipeline/__init__.py",
        "src/pipeline/probes.py",
        
        # CSI module
        "src/csi/__init__.py",
        "src/csi/constants.py",
        "src/csi/computation.py",
        "src/csi/probes.py",
        
        # Utils module
        "src/utils/__init__.py",
        "src/utils/config.py",
        
        # Config files
        "config/logging_config.yaml",
        "config/csi_config.yaml",
    ]
    
    # Check each file
    missing_files = []
    present_files = []
    
    for file_path in expected_files:
        full_path = pipeline_root / file_path
        if full_path.exists():
            present_files.append(file_path)
            print(f"✓ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"✗ {file_path} (MISSING)")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Present: {len(present_files)}/{len(expected_files)}")
    print(f"Missing: {len(missing_files)}/{len(expected_files)}")
    
    if missing_files:
        print("\nMISSING FILES:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        print("\n❌ Verification FAILED")
        return False
    else:
        print("\n✅ Verification PASSED - All files present!")
        return True

if __name__ == "__main__":
    success = verify_structure()
    sys.exit(0 if success else 1)