"""
MotionBuilder startup script for xMobu
This script is automatically executed when MotionBuilder starts
"""

import sys
from pathlib import Path

# Add xMobu root to Python path
XMOBU_ROOT = Path(__file__).parent.parent
if str(XMOBU_ROOT) not in sys.path:
    sys.path.insert(0, str(XMOBU_ROOT))

from core.logger import logger
from core.config import config
from mobu.menu_builder import MenuBuilder


def initialize():
    """
    Initialize xMobu for MotionBuilder
    Called automatically on MotionBuilder startup
    """
    print("[xMobu] ========================================")
    print("[xMobu] Starting xMobu initialization...")
    print(f"[xMobu] Version: 1.0.0")
    print(f"[xMobu] Root directory: {XMOBU_ROOT}")
    print("[xMobu] ========================================")

    try:
        # Check MotionBuilder version
        print("[xMobu] Checking MotionBuilder version...")
        from core.utils import get_mobu_version
        mobu_version = get_mobu_version()

        if mobu_version:
            print(f"[xMobu] MotionBuilder version detected: {mobu_version}")

            if mobu_version < 2020:
                print("[xMobu] WARNING: This version is older than 2020")
                print("[xMobu] WARNING: Some features may not work correctly")
                logger.warning(
                    f"MotionBuilder {mobu_version} detected. "
                    "xMobu is designed for MotionBuilder 2020+. "
                    "Some features may not work correctly."
                )
            else:
                print("[xMobu] Version check passed")
        else:
            print("[xMobu] WARNING: Could not determine MotionBuilder version")

        # Load configuration
        print("[xMobu] Loading configuration...")
        menu_name = config.get('mobu.menu_name', 'xMobu')
        categories = config.get('mobu.tool_categories', [])
        print(f"[xMobu] Menu name: {menu_name}")
        print(f"[xMobu] Enabled categories: {len([c for c in categories if c.get('enabled', True)])}")

        # Build the menu system
        print("[xMobu] Building menu system...")
        menu_builder = MenuBuilder()
        menu_builder.build_menu()

        # Initialize Scene Monitor
        print("[xMobu] Initializing scene monitor...")
        from mobu.utils.scene_monitor import get_scene_monitor
        scene_monitor = get_scene_monitor()
        print("[xMobu] Scene monitor initialized and monitoring file events")

        print("[xMobu] ========================================")
        print("[xMobu] Initialization completed successfully!")
        print(f"[xMobu] Look for '{menu_name}' menu in the menu bar")
        print("[xMobu] ========================================")

        logger.info("xMobu initialized successfully!")

    except ImportError as e:
        print("[xMobu ERROR] ========================================")
        print(f"[xMobu ERROR] Import failed: {str(e)}")
        print("[xMobu ERROR] ========================================")
        print("[xMobu ERROR] Possible causes:")
        print("[xMobu ERROR] - Missing xMobu files")
        print("[xMobu ERROR] - Incorrect Python path")
        print("[xMobu ERROR] - Corrupted installation")
        print("[xMobu ERROR] ========================================")
        logger.error(f"Failed to initialize xMobu: {str(e)}")
        import traceback
        traceback.print_exc()

    except Exception as e:
        print("[xMobu ERROR] ========================================")
        print(f"[xMobu ERROR] Initialization failed: {str(e)}")
        print("[xMobu ERROR] ========================================")
        logger.error(f"Failed to initialize xMobu: {str(e)}")
        import traceback
        traceback.print_exc()


# Auto-initialize when this module is imported
if __name__ != "__main__":
    initialize()
