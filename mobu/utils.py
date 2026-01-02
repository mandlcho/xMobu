"""
MotionBuilder Utility Functions

This module provides common utility functions for working with MotionBuilder's pyfbsdk API.

API Reference:
https://download.autodesk.com/us/motionbuilder/sdk-documentation/PythonSDK/namespacepyfbsdk.html
"""

from typing import List, Optional, Callable
from pyfbsdk import (
    FBModel, FBModelList, FBGetSelectedModels, FBSystem, FBApplication
)
from core.logger import logger


# =============================================================================
# Selection Utilities
# =============================================================================

def get_selection(sort_by_order=False):
    """
    Get currently selected models in the scene.

    Args:
        sort_by_order (bool): If True, returns models sorted by selection order
                             (first selected model comes first in the list)

    Returns:
        FBModelList: List of selected models

    Example:
        >>> selection = get_selection(sort_by_order=True)
        >>> for model in selection:
        ...     print(model.Name)
    """
    selected = FBModelList()
    FBGetSelectedModels(selected, None, True, sort_by_order)
    return selected


def get_selection_as_list(sort_by_order=False):
    """
    Get currently selected models as a Python list.

    Args:
        sort_by_order (bool): If True, returns models sorted by selection order

    Returns:
        List[FBModel]: Python list of selected models

    Example:
        >>> models = get_selection_as_list(sort_by_order=True)
        >>> first_selected = models[0] if models else None
    """
    selected = get_selection(sort_by_order=sort_by_order)
    return [model for model in selected]


def get_selection_names(sort_by_order=False):
    """
    Get names of currently selected models.

    Args:
        sort_by_order (bool): If True, returns names sorted by selection order

    Returns:
        List[str]: List of model names

    Example:
        >>> names = get_selection_names(sort_by_order=True)
        >>> print(f"Selected: {', '.join(names)}")
    """
    selected = get_selection_as_list(sort_by_order=sort_by_order)
    return [model.Name for model in selected]


def get_first_selected():
    """
    Get the first selected model (by selection order).

    Returns:
        FBModel or None: The first selected model, or None if nothing selected

    Example:
        >>> first = get_first_selected()
        >>> if first:
        ...     print(f"First selected: {first.Name}")
    """
    models = get_selection_as_list(sort_by_order=True)
    return models[0] if models else None


def get_last_selected():
    """
    Get the last selected model (by selection order).

    Returns:
        FBModel or None: The last selected model, or None if nothing selected

    Example:
        >>> last = get_last_selected()
        >>> if last:
        ...     print(f"Last selected: {last.Name}")
    """
    models = get_selection_as_list(sort_by_order=True)
    return models[-1] if models else None


def get_selection_count():
    """
    Get the count of currently selected models.

    Returns:
        int: Number of selected models

    Example:
        >>> count = get_selection_count()
        >>> print(f"Selected {count} objects")
    """
    selected = get_selection()
    return len(selected)


def is_selected(model):
    """
    Check if a specific model is currently selected.

    Args:
        model (FBModel): The model to check

    Returns:
        bool: True if the model is selected

    Example:
        >>> model = find_model_by_name("MyObject")
        >>> if is_selected(model):
        ...     print(f"{model.Name} is selected")
    """
    if not model:
        return False
    return model.Selected


# =============================================================================
# Object Finding Utilities
# =============================================================================

def find_model_by_name(name, case_sensitive=True):
    """
    Find a model by its exact name.

    Args:
        name (str): The name of the model to find
        case_sensitive (bool): Whether the search should be case-sensitive

    Returns:
        FBModel or None: The found model, or None if not found

    Example:
        >>> model = find_model_by_name("Root")
        >>> if model:
        ...     print(f"Found: {model.LongName}")
    """
    scene = FBSystem().Scene

    for comp in scene.Components:
        if isinstance(comp, FBModel):
            if case_sensitive:
                if comp.Name == name:
                    return comp
            else:
                if comp.Name.lower() == name.lower():
                    return comp

    return None


def find_models_by_pattern(pattern):
    """
    Find models matching a wildcard pattern.

    Args:
        pattern (str): Wildcard pattern (e.g., "*_ctrl", "Char*", "?oot")
                      * matches any characters
                      ? matches single character

    Returns:
        List[FBModel]: List of models matching the pattern

    Example:
        >>> controls = find_models_by_pattern("*_ctrl")
        >>> for ctrl in controls:
        ...     print(ctrl.Name)
    """
    import fnmatch

    scene = FBSystem().Scene
    matching_models = []

    for comp in scene.Components:
        if isinstance(comp, FBModel):
            # Match against both Name and LongName for flexibility
            if fnmatch.fnmatch(comp.Name, pattern) or fnmatch.fnmatch(comp.LongName, pattern):
                matching_models.append(comp)

    return matching_models


def get_all_models(include_children=True):
    """
    Get all models in the scene.

    Args:
        include_children (bool): If True, recursively includes all children.
                                If False, only returns top-level models.

    Returns:
        List[FBModel]: List of all scene models

    Example:
        >>> all_models = get_all_models()
        >>> print(f"Scene has {len(all_models)} models")
        >>>
        >>> # Only top-level models
        >>> top_level = get_all_models(include_children=False)
    """
    scene = FBSystem().Scene
    models = []

    # Get all components that are models
    for comp in scene.Components:
        if isinstance(comp, FBModel):
            models.append(comp)

    return models


def get_children(model, recursive=False):
    """
    Get children of a model.

    Args:
        model (FBModel): Parent model
        recursive (bool): If True, get all descendants; if False, only direct children

    Returns:
        List[FBModel]: List of child models

    Example:
        >>> root = find_model_by_name("Root")
        >>> children = get_children(root, recursive=False)
        >>> all_descendants = get_children(root, recursive=True)
    """
    if not model:
        return []

    if not recursive:
        return [model.Children[i] for i in range(len(model.Children))]

    # Recursive collection
    children = []

    def collect_children(parent):
        for i in range(len(parent.Children)):
            child = parent.Children[i]
            children.append(child)
            collect_children(child)

    collect_children(model)
    return children


# =============================================================================
# Scene Utilities
# =============================================================================

def get_scene():
    """
    Get the current scene object.

    Returns:
        FBScene: The current scene

    Example:
        >>> scene = get_scene()
        >>> print(f"Scene has {len(scene.Components)} components")
    """
    return FBSystem().Scene


def get_system():
    """
    Get the MotionBuilder system object.

    Returns:
        FBSystem: The system object

    Example:
        >>> system = get_system()
        >>> print(f"MotionBuilder version: {system.Version}")
    """
    return FBSystem()


# =============================================================================
# Validation Utilities
# =============================================================================

def validate_selection(min_count=1, max_count=None, object_type=None, raise_error=False):
    """
    Validate the current selection against criteria.

    Args:
        min_count (int): Minimum number of objects required
        max_count (int, optional): Maximum number of objects allowed
        object_type (type, optional): Required type (e.g., FBModelSkeleton)
        raise_error (bool): If True, raises ValueError on validation failure

    Returns:
        bool: True if selection is valid

    Raises:
        ValueError: If raise_error is True and validation fails

    Example:
        >>> if validate_selection(min_count=2, max_count=10):
        ...     print("Valid selection")
        >>>
        >>> # With error raising
        >>> try:
        ...     validate_selection(min_count=1, raise_error=True)
        ...     process_selection()
        ... except ValueError as e:
        ...     print(f"Selection error: {e}")
    """
    selection = get_selection_as_list()
    count = len(selection)

    # Check minimum count
    if count < min_count:
        msg = f"Please select at least {min_count} object(s). Currently selected: {count}"
        if raise_error:
            raise ValueError(msg)
        logger.warning(msg)
        return False

    # Check maximum count
    if max_count is not None and count > max_count:
        msg = f"Please select at most {max_count} object(s). Currently selected: {count}"
        if raise_error:
            raise ValueError(msg)
        logger.warning(msg)
        return False

    # Check object type
    if object_type is not None:
        for model in selection:
            if not isinstance(model, object_type):
                msg = f"Object '{model.Name}' is not of required type {object_type.__name__}"
                if raise_error:
                    raise ValueError(msg)
                logger.warning(msg)
                return False

    return True


# =============================================================================
# Event Callback Utilities
# =============================================================================

class SceneEventManager:
    """
    Manager for MotionBuilder scene and file event callbacks.

    Simplifies registering and unregistering event callbacks for tools that need
    to respond to scene changes, file operations, etc.

    Example:
        >>> class MyTool:
        ...     def __init__(self):
        ...         self.event_manager = SceneEventManager()
        ...         self.event_manager.register_file_events(self.on_file_changed)
        ...         self.event_manager.register_scene_changes(self.on_scene_changed)
        ...
        ...     def on_file_changed(self, pCaller, pEvent):
        ...         print("File changed!")
        ...
        ...     def on_scene_changed(self, pCaller, pEvent):
        ...         print("Scene changed!")
        ...
        ...     def cleanup(self):
        ...         self.event_manager.unregister_all()
    """

    def __init__(self):
        """Initialize the event manager"""
        self.app = FBApplication()
        self.scene = FBSystem().Scene
        self._registered_callbacks = {
            'file_new': [],
            'file_open': [],
            'file_merge': [],
            'file_save': [],
            'scene_change': []
        }

    def register_file_events(self, callback: Callable, events: List[str] = None):
        """
        Register a callback for file events.

        Args:
            callback: Function with signature callback(pCaller, pEvent)
            events: List of events to register for. Options:
                    - 'new': File > New completed
                    - 'open': File > Open completed
                    - 'merge': File > Merge/Append
                    - 'save': File > Save completed
                    If None, registers for all file events

        Example:
            >>> manager = SceneEventManager()
            >>> manager.register_file_events(my_callback, events=['new', 'open'])
        """
        if events is None:
            events = ['new', 'open', 'merge', 'save']

        for event in events:
            if event == 'new':
                self.app.OnFileNewCompleted.Add(callback)
                self._registered_callbacks['file_new'].append(callback)
            elif event == 'open':
                self.app.OnFileOpenCompleted.Add(callback)
                self._registered_callbacks['file_open'].append(callback)
            elif event == 'merge':
                self.app.OnFileMerge.Add(callback)
                self._registered_callbacks['file_merge'].append(callback)
            elif event == 'save':
                self.app.OnFileSaveCompleted.Add(callback)
                self._registered_callbacks['file_save'].append(callback)

        logger.info(f"Registered file event callbacks: {events}")

    def register_scene_changes(self, callback: Callable):
        """
        Register a callback for scene change events (object add/delete).

        Args:
            callback: Function with signature callback(pCaller, pEvent)

        Example:
            >>> manager = SceneEventManager()
            >>> manager.register_scene_changes(my_scene_callback)
        """
        print(f"[SceneEventManager] Registering scene change callback: {callback.__name__}")
        self.scene.OnChange.Add(callback)
        self._registered_callbacks['scene_change'].append(callback)
        print(f"[SceneEventManager] Scene change callback registered successfully")
        logger.info("Registered scene change callback")

    def unregister_file_events(self, callback: Callable = None):
        """
        Unregister file event callbacks.

        Args:
            callback: Specific callback to unregister. If None, unregisters all.
        """
        if callback is None:
            # Unregister all file callbacks
            for cb in self._registered_callbacks['file_new']:
                self.app.OnFileNewCompleted.Remove(cb)
            for cb in self._registered_callbacks['file_open']:
                self.app.OnFileOpenCompleted.Remove(cb)
            for cb in self._registered_callbacks['file_merge']:
                self.app.OnFileMerge.Remove(cb)
            for cb in self._registered_callbacks['file_save']:
                self.app.OnFileSaveCompleted.Remove(cb)

            self._registered_callbacks['file_new'].clear()
            self._registered_callbacks['file_open'].clear()
            self._registered_callbacks['file_merge'].clear()
            self._registered_callbacks['file_save'].clear()
        else:
            # Unregister specific callback
            if callback in self._registered_callbacks['file_new']:
                self.app.OnFileNewCompleted.Remove(callback)
                self._registered_callbacks['file_new'].remove(callback)
            if callback in self._registered_callbacks['file_open']:
                self.app.OnFileOpenCompleted.Remove(callback)
                self._registered_callbacks['file_open'].remove(callback)
            if callback in self._registered_callbacks['file_merge']:
                self.app.OnFileMerge.Remove(callback)
                self._registered_callbacks['file_merge'].remove(callback)
            if callback in self._registered_callbacks['file_save']:
                self.app.OnFileSaveCompleted.Remove(callback)
                self._registered_callbacks['file_save'].remove(callback)

    def unregister_scene_changes(self, callback: Callable = None):
        """
        Unregister scene change callbacks.

        Args:
            callback: Specific callback to unregister. If None, unregisters all.
        """
        if callback is None:
            for cb in self._registered_callbacks['scene_change']:
                self.scene.OnChange.Remove(cb)
            self._registered_callbacks['scene_change'].clear()
        else:
            if callback in self._registered_callbacks['scene_change']:
                self.scene.OnChange.Remove(callback)
                self._registered_callbacks['scene_change'].remove(callback)

    def unregister_all(self):
        """
        Unregister all callbacks.

        Call this in your tool's cleanup/close method to prevent memory leaks.

        Example:
            >>> def closeEvent(self, event):
            ...     self.event_manager.unregister_all()
        """
        print("[SceneEventManager] Unregistering all callbacks...")
        self.unregister_file_events()
        self.unregister_scene_changes()
        print("[SceneEventManager] All callbacks unregistered")
        logger.info("Unregistered all event callbacks")


def register_file_callback(callback: Callable, events: List[str] = None) -> SceneEventManager:
    """
    Quick helper to register file event callbacks.

    Args:
        callback: Function with signature callback(pCaller, pEvent)
        events: List of events ('new', 'open', 'merge', 'save'). If None, all events.

    Returns:
        SceneEventManager: Manager instance (store this to unregister later)

    Example:
        >>> def on_file_changed(pCaller, pEvent):
        ...     print("File changed!")
        >>>
        >>> manager = register_file_callback(on_file_changed, events=['new', 'open'])
        >>> # Later, cleanup:
        >>> manager.unregister_all()
    """
    manager = SceneEventManager()
    manager.register_file_events(callback, events)
    return manager


def register_scene_callback(callback: Callable) -> SceneEventManager:
    """
    Quick helper to register scene change callbacks.

    Args:
        callback: Function with signature callback(pCaller, pEvent)

    Returns:
        SceneEventManager: Manager instance (store this to unregister later)

    Example:
        >>> def on_scene_changed(pCaller, pEvent):
        ...     print("Scene changed!")
        >>>
        >>> manager = register_scene_callback(on_scene_changed)
        >>> # Later, cleanup:
        >>> manager.unregister_all()
    """
    manager = SceneEventManager()
    manager.register_scene_changes(callback)
    return manager


# =============================================================================
# Qt Widget Utilities
# =============================================================================

def refresh_list_widget(
    parent_widget,
    list_widget_name: str,
    models: List[FBModel],
    selected_objects: Optional[List[FBModel]] = None,
    tool_name: str = "Tool"
):
    """
    Refresh a Qt list widget with MotionBuilder models.

    This is the standard pattern for updating scene object lists in Qt dialogs.
    Re-finds the widget, clears it, populates with model names, and forces UI updates.

    Args:
        parent_widget: Qt dialog/widget containing the list widget (usually self)
        list_widget_name: Object name of the QListWidget to refresh
        models: List of FBModel objects to display
        selected_objects: Optional list to clean up (removes deleted models)
        tool_name: Name of the tool (for logging)

    Returns:
        bool: True if refresh succeeded, False if widget not found

    Example:
        >>> # In your Qt dialog class:
        >>> def update_scene_objects(self):
        ...     all_models = get_all_models()
        ...     # Filter cameras
        ...     from pyfbsdk import FBCamera
        ...     models = [m for m in all_models if not isinstance(m, FBCamera)]
        ...     models.sort(key=lambda x: x.Name)
        ...
        ...     refresh_list_widget(
        ...         parent_widget=self,
        ...         list_widget_name="objectsList",
        ...         models=models,
        ...         selected_objects=self.selected_objects,
        ...         tool_name="My Tool"
        ...     )

    Notes:
        - Re-finds the widget each time for reliability (handles widget lifecycle)
        - Clears and repopulates the entire list
        - Forces Qt widget updates (update, repaint)
        - Forces MotionBuilder UI update (UpdateAllWidgets)
        - Cleans up selected_objects list if provided
        - Returns False if widget can't be found (safe to ignore)
    """
    try:
        # Import Qt here to avoid requiring it at module level
        try:
            from PySide2 import QtWidgets
        except ImportError:
            from PySide import QtGui as QtWidgets
    except ImportError:
        logger.error(f"[{tool_name}] Qt not available for refresh_list_widget")
        return False

    # Re-find the widget each time to ensure we have a valid reference
    list_widget = parent_widget.findChild(QtWidgets.QListWidget, list_widget_name)

    if not list_widget:
        logger.warning(f"[{tool_name}] Could not find list widget '{list_widget_name}'")
        return False

    try:
        # Clear the list
        list_widget.clear()

        # Populate the list widget
        for model in models:
            list_widget.addItem(model.Name)

        logger.debug(f"[{tool_name}] List updated with {len(models)} objects")

        # Force Qt widget updates
        list_widget.update()
        list_widget.repaint()

        # Force MotionBuilder UI update
        FBApplication().UpdateAllWidgets()

        # Clean up selected_objects list if provided - remove any deleted objects
        if selected_objects is not None:
            # Remove objects that are no longer in the models list
            removed = []
            for i in range(len(selected_objects) - 1, -1, -1):
                if selected_objects[i] not in models:
                    removed.append(selected_objects[i])
                    del selected_objects[i]

            if removed:
                logger.debug(f"[{tool_name}] Cleaned up {len(removed)} deleted objects from selection")

        return True

    except RuntimeError as e:
        logger.error(f"[{tool_name}] RuntimeError during list refresh: {e}")
        return False
    except Exception as e:
        logger.error(f"[{tool_name}] Error refreshing list widget: {e}")
        import traceback
        traceback.print_exc()
        return False
