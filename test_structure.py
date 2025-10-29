#!/usr/bin/env python3
"""
Test script to verify project structure without dependencies
"""
import os
import sys
from pathlib import Path

def test_project_structure():
    """Test that all required files and directories exist"""
    
    project_root = Path(__file__).parent
    
    print("Testing Trainer-Charlie Project Structure")
    print("=" * 50)
    
    # Test directories
    required_dirs = [
        "data_collection",
        "thesis_generation", 
        "orchestration",
        "utils",
        "scripts",
        "storage/distilled_theses",
        "storage/distilled_theses/backups",
        "storage/checkpoints",
        "storage/data"
    ]
    
    print("\nChecking directories:")
    dirs_ok = True
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} - MISSING")
            dirs_ok = False
    
    # Test key files
    required_files = [
        "main.py",
        "pyproject.toml",
        ".env.example",
        "README.md",
        "__init__.py",
        "data_collection/__init__.py",
        "data_collection/database_manager.py",
        "data_collection/data_processor.py",
        "data_collection/eodhd_client.py",
        "data_collection/fred_client.py",
        "data_collection/feature_engineering.py",
        "data_collection/data_orchestrator.py",
        "thesis_generation/__init__.py",
        "thesis_generation/data_deduplicator.py",
        "thesis_generation/prompt_builder.py",
        "thesis_generation/llm_client.py",
        "thesis_generation/xml_thesis_generator.py",
        "orchestration/__init__.py",
        "orchestration/config_manager.py",
        "orchestration/market_calendar.py",
        "orchestration/checkpoint_manager.py",
        "orchestration/main_pipeline.py",
        "utils/__init__.py",
        "utils/logger.py",
        "utils/xml_validator.py",
        "scripts/init_db.sh",
        "scripts/run_pipeline.sh",
        "scripts/verify_setup.sh",
        "scripts/setup.sh"
    ]
    
    print("\nChecking files:")
    files_ok = True
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} - MISSING")
            files_ok = False
    
    # Test imports (without external dependencies)
    print("\nTesting Python imports:")
    sys.path.insert(0, str(project_root))
    
    try:
        # Test that modules can be found
        import data_collection
        print("  ✓ data_collection module")
        
        import thesis_generation
        print("  ✓ thesis_generation module")
        
        import orchestration
        print("  ✓ orchestration module")
        
        import utils
        print("  ✓ utils module")
        
        imports_ok = True
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        imports_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    if dirs_ok and files_ok and imports_ok:
        print("✓ All structure tests passed!")
        print("\nNext step: Run ./scripts/setup.sh to install dependencies")
        return True
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = test_project_structure()
    sys.exit(0 if success else 1)