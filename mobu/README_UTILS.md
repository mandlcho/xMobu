# MotionBuilder Utilities

This module provides reusable utility functions for common MotionBuilder operations.

## API Reference

Official MotionBuilder Python SDK Documentation:
https://download.autodesk.com/us/motionbuilder/sdk-documentation/PythonSDK/namespacepyfbsdk.html

## Available Utilities

### Selection Utilities

```python
from mobu.utils import (
    get_selection,
    get_selection_as_list,
    get_selection_names,
    get_first_selected,
    get_last_selected,
    get_selection_count,
    is_selected,
    validate_selection
)

# Get selection in order they were selected
models = get_selection_as_list(sort_by_order=True)

# Get just the names
names = get_selection_names(sort_by_order=True)

# Get first and last selected
first = get_first_selected()  # First selected object
last = get_last_selected()    # Last selected object

# Count
count = get_selection_count()

# Check if model is selected
if is_selected(my_model):
    print("Selected!")

# Validate selection
if validate_selection(min_count=2, max_count=10):
    # Process selection...
    pass
```

### Object Finding Utilities

```python
from mobu.utils import (
    find_model_by_name,
    find_models_by_pattern,
    get_all_models,
    get_children
)

# Find exact model
root = find_model_by_name("Root")
root_nocase = find_model_by_name("root", case_sensitive=False)

# Find with wildcards
controls = find_models_by_pattern("*_ctrl")
chars = find_models_by_pattern("Character*")

# Get all models
all_models = get_all_models()

# Get children
direct_children = get_children(root, recursive=False)
all_descendants = get_children(root, recursive=True)
```

### Scene Utilities

```python
from mobu.utils import get_scene, get_system

# Get scene
scene = get_scene()
for comp in scene.Components:
    print(comp.Name)

# Get system
system = get_system()
print(f"Version: {system.Version}")
```

## Selection Order

The key feature is `sort_by_order` which preserves the order objects were selected:

```python
# User selects: Cube, Sphere, Cylinder (in that order)
ordered = get_selection_as_list(sort_by_order=True)
# Returns: [Cube, Sphere, Cylinder]

unordered = get_selection_as_list(sort_by_order=False)
# Returns: Objects in scene hierarchy order
```

This is useful for tools that care about selection order, like:
- Parent/child constraint creation
- Sequential operations
- UI display ordering

## Testing

Run the test script in MotionBuilder:

```python
execfile(r"C:\Users\elementa\projects\xMobu\test_selection_utils.py")
```

Or in the Python Editor:
1. Select some objects
2. Run `test_selection_utils.py`
3. Check output for results

## Usage in Tools

Tools should use these utilities instead of calling pyfbsdk directly:

### Before:
```python
from pyfbsdk import FBModelList, FBGetSelectedModels

selected = FBModelList()
FBGetSelectedModels(selected)
for model in selected:
    print(model.Name)
```

### After:
```python
from mobu.utils import get_selection_as_list

selected = get_selection_as_list()
for model in selected:
    print(model.Name)
```

## Event Callback Utilities

### SceneEventManager Class

Simplifies registering and unregistering MotionBuilder event callbacks:

```python
from mobu.utils import SceneEventManager

class MyTool:
    def __init__(self):
        # Create event manager
        self.event_manager = SceneEventManager()

        # Register file events (new, open, merge, save)
        self.event_manager.register_file_events(
            self.on_file_changed,
            events=['new', 'open', 'merge']  # Optional: specify which events
        )

        # Register scene changes (object add/delete)
        self.event_manager.register_scene_changes(self.on_scene_changed)

    def on_file_changed(self, pCaller, pEvent):
        """Called when file operations complete"""
        print("File changed!")
        self.refresh_my_data()

    def on_scene_changed(self, pCaller, pEvent):
        """Called when scene changes (objects added/deleted)"""
        print("Scene changed!")
        self.update_my_list()

    def closeEvent(self, event):
        """Cleanup - IMPORTANT!"""
        self.event_manager.unregister_all()
```

### Quick Helper Functions

For simple cases:

```python
from mobu.utils import register_file_callback, register_scene_callback

# Register file callbacks
def on_file_event(pCaller, pEvent):
    print("File event!")

manager1 = register_file_callback(on_file_event, events=['new', 'open'])

# Register scene callbacks
def on_scene_event(pCaller, pEvent):
    print("Scene changed!")

manager2 = register_scene_callback(on_scene_event)

# Cleanup later
manager1.unregister_all()
manager2.unregister_all()
```

### Available File Events

- `'new'` - File > New completed (`OnFileNewCompleted`)
- `'open'` - File > Open completed (`OnFileOpenCompleted`)
- `'merge'` - File > Merge/Append (`OnFileMerge`)
- `'save'` - File > Save completed (`OnFileSaveCompleted`)

### Scene Events

- `register_scene_changes()` - Object add/delete (`Scene.OnChange`)

### Why Use SceneEventManager?

✅ **Automatic cleanup** - Tracks all registered callbacks
✅ **No memory leaks** - `unregister_all()` removes everything
✅ **Simpler API** - No need to manage FBApplication/FBSystem instances
✅ **Reusable** - Same pattern across all tools
✅ **Type hints** - Better IDE support

## Qt Widget Utilities

### refresh_list_widget()

Standard pattern for refreshing Qt list widgets with MotionBuilder models. Handles widget re-finding, clearing, populating, and forcing UI updates.

```python
from mobu.utils import refresh_list_widget, get_all_models
from pyfbsdk import FBCamera

class MyDialog(QDialog):
    def update_scene_objects(self):
        # Get and filter models
        all_models = get_all_models()
        models = [m for m in all_models if not isinstance(m, FBCamera)]
        models.sort(key=lambda x: x.Name)

        # Store for later use
        self.all_models = models

        # Refresh the list widget
        success = refresh_list_widget(
            parent_widget=self,
            list_widget_name="objectsList",
            models=models,
            selected_objects=self.selected_objects,  # Optional: auto-cleanup
            tool_name="My Tool"
        )

        if not success:
            print("Failed to refresh list")
```

**Features:**
- Re-finds widget each time (handles widget lifecycle safely)
- Clears and repopulates the list
- Forces Qt updates (`update()`, `repaint()`)
- Forces MotionBuilder UI update (`UpdateAllWidgets()`)
- Auto-cleans up `selected_objects` list (removes deleted models)
- Returns `True` on success, `False` if widget not found
- Handles both PySide2 and PySide gracefully

**Use Cases:**
- Scene object lists in Qt dialogs
- Auto-refreshing lists when scene changes
- List widgets that need to stay in sync with scene

**Why Use This?**

✅ **Reliable** - Re-finds widget each time, avoiding stale references
✅ **Consistent** - Same pattern across all tools
✅ **Complete** - Handles all refresh aspects (clear, populate, force updates)
✅ **Safe** - Proper error handling and logging
✅ **Efficient** - Cleans up deleted objects automatically

## Benefits

- **Cleaner code**: Less boilerplate
- **Consistent**: Same patterns across all tools
- **Pythonic**: Returns Python lists, not FBModelList
- **Event-driven**: Proper callbacks instead of polling
- **Documented**: Docstrings with examples
- **Type hints**: Better IDE support
- **Tested**: Centralized testing
