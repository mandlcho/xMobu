# Event Callback Utilities Guide

This guide shows how to use the event callback utilities in `mobu/utils.py` for building tools that respond to scene and file events.

## Why Use Event Callbacks?

**DON'T do this:**
```python
# ❌ BAD: Polling with timer
self.timer = QTimer()
self.timer.timeout.connect(self.check_if_scene_changed)
self.timer.start(500)  # Check every 500ms - wasteful!
```

**DO this instead:**
```python
# ✅ GOOD: Event-driven
from mobu.utils import SceneEventManager

self.event_manager = SceneEventManager()
self.event_manager.register_scene_changes(self.on_scene_changed)
# Only runs when scene actually changes!
```

## SceneEventManager Class

### Basic Usage

```python
from mobu.utils import SceneEventManager

class MyToolDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create event manager
        self.event_manager = SceneEventManager()

        # Register callbacks
        self.setup_events()

    def setup_events(self):
        """Register event callbacks"""
        # File events
        self.event_manager.register_file_events(
            self.on_file_event,
            events=['new', 'open', 'merge']
        )

        # Scene changes
        self.event_manager.register_scene_changes(
            self.on_scene_change
        )

    def on_file_event(self, pCaller, pEvent):
        """Callback for file operations"""
        print("File operation detected!")
        self.refresh_tool()

    def on_scene_change(self, pCaller, pEvent):
        """Callback for scene changes"""
        print("Scene changed!")
        self.update_ui()

    def closeEvent(self, event):
        """IMPORTANT: Cleanup on close"""
        self.event_manager.unregister_all()
        event.accept()
```

### File Events

Register for specific file events:

```python
# All file events (new, open, merge, save)
manager.register_file_events(callback)

# Specific events only
manager.register_file_events(callback, events=['new', 'open'])

# Just merge operations
manager.register_file_events(callback, events=['merge'])
```

Available events:
- `'new'` - File > New completed
- `'open'` - File > Open completed
- `'merge'` - File > Merge or File > Append
- `'save'` - File > Save completed

### Scene Change Events

Responds to object add/delete:

```python
manager.register_scene_changes(callback)
```

Triggers when:
- Objects created
- Objects deleted
- Scene hierarchy changes

### Unregistering Events

**Important:** Always unregister callbacks when your tool closes!

```python
# Unregister all callbacks (recommended)
self.event_manager.unregister_all()

# Unregister specific callback
self.event_manager.unregister_file_events(my_callback)
self.event_manager.unregister_scene_changes(my_callback)

# Unregister all file events but keep scene events
self.event_manager.unregister_file_events()
```

## Quick Helper Functions

For simple tools that only need one callback:

```python
from mobu.utils import register_file_callback, register_scene_callback

# File events
def on_file_changed(pCaller, pEvent):
    print("File changed!")

file_manager = register_file_callback(on_file_changed, events=['new', 'open'])

# Scene events
def on_scene_changed(pCaller, pEvent):
    print("Scene changed!")

scene_manager = register_scene_callback(on_scene_changed)

# Cleanup
file_manager.unregister_all()
scene_manager.unregister_all()
```

## Real-World Examples

### Example 1: Scene Browser Tool

```python
from mobu.utils import SceneEventManager, get_all_models

class SceneBrowserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Setup UI
        self.object_list = QListWidget()

        # Event manager
        self.event_manager = SceneEventManager()
        self.event_manager.register_file_events(self.refresh_list, events=['new', 'open', 'merge'])
        self.event_manager.register_scene_changes(self.refresh_list)

        # Initial population
        self.refresh_list(None, None)

    def refresh_list(self, pCaller, pEvent):
        """Refresh object list"""
        self.object_list.clear()
        for model in get_all_models():
            self.object_list.addItem(model.Name)

    def closeEvent(self, event):
        self.event_manager.unregister_all()
        event.accept()
```

### Example 2: Auto-Save Tool

```python
from mobu.utils import SceneEventManager
import time

class AutoSaveTool:
    def __init__(self):
        self.last_save_time = time.time()
        self.save_interval = 300  # 5 minutes

        self.event_manager = SceneEventManager()
        self.event_manager.register_scene_changes(self.on_scene_changed)

    def on_scene_changed(self, pCaller, pEvent):
        """Auto-save after scene changes"""
        current_time = time.time()
        if current_time - self.last_save_time > self.save_interval:
            self.auto_save()
            self.last_save_time = current_time

    def auto_save(self):
        """Perform auto-save"""
        print("Auto-saving...")
        # Save logic here

    def cleanup(self):
        self.event_manager.unregister_all()
```

### Example 3: Reference Manager

```python
from mobu.utils import SceneEventManager

class ReferenceManager:
    def __init__(self):
        self.references = []

        self.event_manager = SceneEventManager()
        # Only care about file operations
        self.event_manager.register_file_events(
            self.reload_references,
            events=['open', 'merge']
        )

    def reload_references(self, pCaller, pEvent):
        """Reload references when file opens/merges"""
        print("Reloading references...")
        self.references.clear()
        # Reference loading logic

    def shutdown(self):
        self.event_manager.unregister_all()
```

## Best Practices

### ✅ DO

- Always call `unregister_all()` in your cleanup/close method
- Use specific event lists when you don't need all events
- Keep callbacks fast and lightweight
- Store the `SceneEventManager` as an instance variable

### ❌ DON'T

- Don't create multiple `SceneEventManager` instances in one tool
- Don't do heavy processing in callbacks (use signals/deferred execution)
- Don't forget to unregister - causes memory leaks
- Don't poll with timers when events are available

## Callback Signature

All callbacks must follow this signature:

```python
def my_callback(pCaller, pEvent):
    """
    Args:
        pCaller: The object that triggered the event (FBApplication or FBScene)
        pEvent: The event object (FBEvent subclass)
    """
    # Your code here
    pass
```

## Troubleshooting

### Callbacks not firing?

1. Check you called `register_file_events()` or `register_scene_changes()`
2. Verify callback signature matches `callback(pCaller, pEvent)`
3. Make sure you didn't call `unregister_all()` too early

### Memory leaks?

1. Always call `unregister_all()` in your tool's close/cleanup method
2. Store the `SceneEventManager` instance so it doesn't get garbage collected
3. Don't create new managers without cleaning up old ones

### Events firing too often?

Scene.OnChange fires frequently. If you need to throttle:

```python
import time

class MyTool:
    def __init__(self):
        self.last_refresh = 0
        self.event_manager = SceneEventManager()
        self.event_manager.register_scene_changes(self.on_scene_change_throttled)

    def on_scene_change_throttled(self, pCaller, pEvent):
        """Only refresh once per second max"""
        now = time.time()
        if now - self.last_refresh > 1.0:  # 1 second throttle
            self.refresh_ui()
            self.last_refresh = now
```

## Scene Monitor Utility

The Scene Monitor is a higher-level utility that automatically tracks objects and namespaces in your scene and notifies listeners of changes.

### Basic Usage

```python
from mobu.utils.scene_monitor import get_scene_monitor

# Get the global scene monitor instance
monitor = get_scene_monitor()

# Get current scene info
scene_info = monitor.get_scene_info()
print(f"Objects: {scene_info['object_count']}")
print(f"Namespaces: {scene_info['namespaces']}")

# Check for specific namespace
if monitor.has_namespace('Character01'):
    print("Character01 namespace found!")
```

### Listening to Scene Changes

```python
class MyTool:
    def __init__(self):
        from mobu.utils.scene_monitor import get_scene_monitor
        self.monitor = get_scene_monitor()
        self.monitor.add_listener(self.on_scene_changed)

    def on_scene_changed(self, scene_info):
        """Called when scene changes (file open/new/merge)"""
        print(f"Scene changed!")
        print(f"  Objects: {scene_info['object_count']}")
        print(f"  Namespaces: {scene_info['namespaces']}")
        # Update your UI here

    def cleanup(self):
        """IMPORTANT: Remove listener on cleanup"""
        self.monitor.remove_listener(self.on_scene_changed)
```

### Scene Monitor Features

- **Automatic Initialization**: Started when xMobu loads
- **File Event Monitoring**: Scans on file new/open/merge
- **Namespace Detection**: Finds namespaces using `namespace:objectname` pattern
- **Observer Pattern**: Multiple tools can listen to scene changes
- **Scene Info**: Returns object count, namespace list, and has_objects flag

### When to Use Scene Monitor vs SceneEventManager

**Use Scene Monitor when:**
- You need to know what namespaces exist in the scene
- You want automatic object/namespace tracking
- You need high-level scene info without manual scanning

**Use SceneEventManager when:**
- You need fine-grained control over specific events
- You want to respond to save operations
- You need the raw pCaller/pEvent objects
- You're building custom event logic

### Scene Monitor Example: Namespace Dropdown

```python
from mobu.utils.scene_monitor import get_scene_monitor

class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create namespace combo
        self.namespace_combo = QComboBox()

        # Setup scene monitor
        self.monitor = get_scene_monitor()
        self.monitor.add_listener(self.on_scene_changed)

        # Initial population
        self.update_namespace_combo()

    def on_scene_changed(self, scene_info):
        """Update combo when scene changes"""
        self.update_namespace_combo()

    def update_namespace_combo(self):
        """Populate combo with current namespaces"""
        self.namespace_combo.clear()
        namespaces = self.monitor.get_namespaces()
        self.namespace_combo.addItems(namespaces)

    def closeEvent(self, event):
        self.monitor.remove_listener(self.on_scene_changed)
        event.accept()
```

## Summary

**SceneEventManager**: Low-level event callback system
- ✅ Event-driven updates (no polling)
- ✅ Automatic callback tracking
- ✅ Easy cleanup with `unregister_all()`
- ✅ Support for file and scene events
- ✅ Prevents memory leaks

**Scene Monitor**: High-level scene tracking utility
- ✅ Automatic object and namespace detection
- ✅ Global singleton instance
- ✅ Observer pattern with listeners
- ✅ Simple scene info API
- ✅ Auto-initialized on xMobu startup

Use them together for responsive, efficient MotionBuilder development!
