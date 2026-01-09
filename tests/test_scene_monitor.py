"""
Test script for Scene Monitor
Run this in MotionBuilder's Script Editor to test scene monitoring
"""

from mobu.utils.scene_monitor import get_scene_monitor

def test_scene_monitor():
    """Test the scene monitor functionality"""
    print("\n" + "="*60)
    print("Testing Scene Monitor")
    print("="*60)

    # Get the scene monitor instance
    monitor = get_scene_monitor()

    # Get current scene info
    scene_info = monitor.get_scene_info()
    print(f"\nCurrent Scene Info:")
    print(f"  Has Objects: {scene_info['has_objects']}")
    print(f"  Object Count: {scene_info['object_count']}")
    print(f"  Namespaces: {scene_info['namespaces']}")

    # Test listener callback
    def on_scene_changed(info):
        print(f"\n[Listener Callback] Scene changed!")
        print(f"  Has Objects: {info['has_objects']}")
        print(f"  Object Count: {info['object_count']}")
        print(f"  Namespaces: {info['namespaces']}")

    # Add listener
    monitor.add_listener(on_scene_changed)
    print("\n[Test] Listener registered")

    # Trigger a manual scan
    print("\n[Test] Triggering manual scene scan...")
    monitor.scan_scene()

    # Test namespace detection
    if monitor.namespaces:
        print(f"\n[Test] Detected namespaces: {monitor.get_namespaces()}")
        for ns in monitor.namespaces:
            print(f"  - Has namespace '{ns}': {monitor.has_namespace(ns)}")
    else:
        print("\n[Test] No namespaces detected in current scene")

    print("\n" + "="*60)
    print("Test completed. Now try:")
    print("  1. File > New to test OnFileNewCompleted")
    print("  2. File > Open to test OnFileOpenCompleted")
    print("  3. File > Merge to test OnFileMerge")
    print("Watch console for '[Scene Monitor]' messages")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_scene_monitor()
