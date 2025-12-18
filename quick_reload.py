"""
Quick Reload Script for xMobu Development
Run this in MotionBuilder's Python Console for fast iteration

Usage in Python Console:
    exec(open(r'C:\Users\elementa\projects\xMobu\quick_reload.py').read())

Or shorter alias:
    reload_xmobu()  (after first run)
"""

import importlib
import sys


def reload_xmobu():
    """Reload all xMobu modules without restarting MotionBuilder"""
    print("\n" + "="*50)
    print("QUICK RELOAD - xMobu Development")
    print("="*50)

    try:
        # Reload core modules
        print("→ Reloading core modules...")
        import core.logger
        import core.config
        import core.utils
        importlib.reload(core.logger)
        importlib.reload(core.config)
        importlib.reload(core.utils)
        print("  ✓ Core modules reloaded")

        # Reload tool modules
        print("→ Reloading tool modules...")
        tool_modules = []

        # Animation tools
        try:
            import mobu.tools.animation.keyframe_tools
            tool_modules.append(mobu.tools.animation.keyframe_tools)
        except ImportError:
            pass

        # Rigging tools
        try:
            import mobu.tools.rigging.constraint_helper
            tool_modules.append(mobu.tools.rigging.constraint_helper)
        except ImportError:
            pass

        # Pipeline tools
        try:
            import mobu.tools.pipeline.scene_manager
            tool_modules.append(mobu.tools.pipeline.scene_manager)
        except ImportError:
            pass

        # Unreal tools
        try:
            import mobu.tools.unreal.content_browser
            tool_modules.append(mobu.tools.unreal.content_browser)
        except ImportError:
            pass

        for module in tool_modules:
            importlib.reload(module)

        print(f"  ✓ {len(tool_modules)} tool module(s) reloaded")

        # Reload menu builder (but don't rebuild menu - MotionBuilder can't delete menus)
        print("→ Reloading menu builder...")
        import mobu.menu_builder
        import mobu.startup
        importlib.reload(mobu.menu_builder)
        importlib.reload(mobu.startup)
        print("  ✓ Menu builder reloaded")

        print("="*50)
        print("✓ RELOAD COMPLETE - Tool changes applied!")
        print("="*50)
        print("NOTE: Menu structure changes require MotionBuilder restart")
        print("NOTE: Tool code changes are active - test your tools!")
        print("="*50 + "\n")

        return True

    except Exception as e:
        print("\n" + "="*50)
        print("✗ RELOAD FAILED")
        print("="*50)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*50 + "\n")
        return False


# Run immediately if executed
if __name__ == "__main__":
    reload_xmobu()
else:
    # Make function available globally
    print("\n[xMobu Quick Reload] Function registered!")
    print("Usage: reload_xmobu()")
    reload_xmobu()
