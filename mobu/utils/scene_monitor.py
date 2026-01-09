"""
Scene Monitor
Monitors scene for objects, namespaces, and file events
"""

from pyfbsdk import FBApplication, FBSystem
from core.logger import logger


class SceneMonitor:
    """Monitor scene for objects, namespaces, and file events"""

    def __init__(self):
        self.app = FBApplication()
        self.callbacks_registered = False
        self.scene_objects = []
        self.namespaces = set()
        self.has_objects = False
        self.listeners = []  # List of callback functions to notify on scene change

    def register_callbacks(self):
        """Register file event callbacks"""
        if self.callbacks_registered:
            return

        try:
            # Register file events
            self.app.OnFileNewCompleted.Add(self.on_file_new)
            self.app.OnFileOpenCompleted.Add(self.on_file_open)
            self.app.OnFileMerge.Add(self.on_file_merge)

            self.callbacks_registered = True
            logger.info("Scene monitor callbacks registered")
            print("[Scene Monitor] File event callbacks registered")

            # Do initial scan
            self.scan_scene()

        except Exception as e:
            logger.error(f"Failed to register scene monitor callbacks: {str(e)}")
            print(f"[Scene Monitor] ERROR: Failed to register callbacks: {str(e)}")

    def unregister_callbacks(self):
        """Unregister file event callbacks"""
        if not self.callbacks_registered:
            return

        try:
            self.app.OnFileNewCompleted.Remove(self.on_file_new)
            self.app.OnFileOpenCompleted.Remove(self.on_file_open)
            self.app.OnFileMerge.Remove(self.on_file_merge)

            self.callbacks_registered = False
            logger.info("Scene monitor callbacks unregistered")
            print("[Scene Monitor] File event callbacks unregistered")

        except Exception as e:
            logger.error(f"Failed to unregister scene monitor callbacks: {str(e)}")
            print(f"[Scene Monitor] ERROR: Failed to unregister callbacks: {str(e)}")

    def add_listener(self, callback):
        """
        Add a listener callback to be notified when scene changes

        Args:
            callback: Function to call with signature: callback(scene_info)
                      scene_info is a dict with keys: has_objects, namespaces, object_count
        """
        if callback not in self.listeners:
            self.listeners.append(callback)
            print(f"[Scene Monitor] Added listener: {callback.__name__}")

    def remove_listener(self, callback):
        """Remove a listener callback"""
        if callback in self.listeners:
            self.listeners.remove(callback)
            print(f"[Scene Monitor] Removed listener: {callback.__name__}")

    def notify_listeners(self):
        """Notify all listeners of scene changes"""
        scene_info = {
            'has_objects': self.has_objects,
            'namespaces': list(self.namespaces),
            'object_count': len(self.scene_objects)
        }

        for listener in self.listeners:
            try:
                listener(scene_info)
            except Exception as e:
                print(f"[Scene Monitor] ERROR: Listener {listener.__name__} failed: {str(e)}")

    def on_file_new(self, control, event):
        """Called when a new file is created"""
        print("[Scene Monitor] File New event detected")
        self.scan_scene()

    def on_file_open(self, control, event):
        """Called when a file is opened"""
        print("[Scene Monitor] File Open event detected")
        self.scan_scene()

    def on_file_merge(self, control, event):
        """Called when files are merged"""
        print("[Scene Monitor] File Merge event detected")
        self.scan_scene()

    def scan_scene(self):
        """Scan the scene for objects and namespaces"""
        print("[Scene Monitor] Scanning scene...")

        try:
            system = FBSystem()
            scene = system.Scene

            # Reset tracking
            self.scene_objects = []
            self.namespaces = set()

            # Get all models in scene
            for comp in scene.Components:
                # Skip cameras and lights for now - focus on models
                if hasattr(comp, 'Name'):
                    name = comp.Name

                    # Add to objects list
                    self.scene_objects.append(comp)

                    # Check for namespace (format: namespace:objectname)
                    if ':' in name:
                        namespace = name.split(':')[0]
                        self.namespaces.add(namespace)

            self.has_objects = len(self.scene_objects) > 0

            # Log results
            print(f"[Scene Monitor] Found {len(self.scene_objects)} objects in scene")
            if self.namespaces:
                print(f"[Scene Monitor] Found namespaces: {sorted(self.namespaces)}")
            else:
                print("[Scene Monitor] No namespaces detected")

            # Notify listeners
            self.notify_listeners()

        except Exception as e:
            logger.error(f"Scene scan failed: {str(e)}")
            print(f"[Scene Monitor] ERROR: Scene scan failed: {str(e)}")
            import traceback
            traceback.print_exc()

    def get_scene_info(self):
        """
        Get current scene information

        Returns:
            dict with keys: has_objects, namespaces, object_count
        """
        return {
            'has_objects': self.has_objects,
            'namespaces': list(self.namespaces),
            'object_count': len(self.scene_objects)
        }

    def get_namespaces(self):
        """Get list of detected namespaces"""
        return sorted(self.namespaces)

    def has_namespace(self, namespace):
        """Check if a specific namespace exists"""
        return namespace in self.namespaces


# Global instance
_scene_monitor = None


def get_scene_monitor():
    """Get or create the global scene monitor instance"""
    global _scene_monitor
    if _scene_monitor is None:
        _scene_monitor = SceneMonitor()
        _scene_monitor.register_callbacks()
    return _scene_monitor
