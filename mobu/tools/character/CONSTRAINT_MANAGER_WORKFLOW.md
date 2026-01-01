# Constraint Manager - New Workflow

## Overview

The Constraint Manager now uses a scene browser approach instead of automatic selection tracking.

## New Features

### 1. Objects in Scene List
- Shows **all objects** in the scene (sorted alphabetically)
- Click on any object to select it in the viewport
- **Auto-updates** when scene changes (new objects, deletions, file open/new/merge)
- Manual refresh available via "Refresh List" button

### 2. Click-to-Select
Click on any object in the list to select it in the viewport:

- **Single Click** - Select only that object (clears previous selection)
- **Ctrl+Click** - Add/remove object from selection (toggle)
- **Selection Order** - The order you click objects is preserved

### 3. Selection Order Tracking
The tool remembers the **exact order** you selected objects:
```
Click: Cube → Sphere → Cylinder
Selection Order: [Cube, Sphere, Cylinder]
```

This is important for constraint workflows where order matters.

### 4. Clear Selection Button
New "Clear Selection" button beside "Set as Source(s)":
- Clears all selected objects in the viewport
- Resets the internal selection order tracking

## Workflow Example

### Creating a Parent/Child Constraint

1. Open Constraint Manager
2. Click on source object (e.g., "Root") in the list
3. Click "Set as Source(s)"
4. Ctrl+Click on target objects in order (e.g., "Arm_L", "Arm_R")
5. Choose "Parent/Child" constraint type
6. Click "Create Constraint"

### Multi-Object Selection

1. Click first object (selects only that one)
2. Ctrl+Click second object (adds to selection)
3. Ctrl+Click third object (adds to selection)
4. Ctrl+Click second object again (removes from selection)

## UI Changes

### Updated Labels
- ~~"Selected Objects:"~~ → **"Objects in Scene:"**
- ~~"Refresh Selection"~~ → **"Refresh List"**

### New Button
- **"Clear Selection"** - Clears all selections

## Technical Details

### Selection Tracking
```python
self.selected_objects = []  # Tracks selection ORDER
```

The `selected_objects` list maintains the exact order you clicked objects, which is preserved when creating constraints.

### Keyboard Modifiers
- **No modifier**: Single selection (clears others)
- **Ctrl**: Multi-selection (add/remove)

### Event-Based Auto-Refresh
The list **automatically updates** using MotionBuilder event callbacks when:
- ✅ New objects are created → `Scene.OnChange` event
- ✅ Objects are deleted → `Scene.OnChange` event
- ✅ File is opened → `OnFileOpenCompleted` event
- ✅ New file is created → `OnFileNewCompleted` event
- ✅ Scene is merged → `OnFileMerge` event

**No polling!** Uses proper event callbacks instead of timer-based checking.

Manual refresh via "Refresh List" button is also available.

**Smart Selection Cleanup**: If you have objects selected and they get deleted from the scene, they're automatically removed from your selection list.

**Event Cleanup**: All event callbacks are properly unregistered when the dialog closes (no memory leaks).

## Benefits

✅ **Event-driven** auto-refresh (no polling, better performance)
✅ See all scene objects at once (easier to find)
✅ Click to select (faster workflow)
✅ Selection order preserved (important for constraints)
✅ Ctrl+Click for multi-selection (standard UI pattern)
✅ Smart cleanup (removes deleted objects from selection)
✅ Works with File Open/New/Merge automatically
✅ Proper callback cleanup (no memory leaks)

## Technical Implementation

Uses MotionBuilder's native event system:
- `FBApplication.OnFileNewCompleted` - File > New
- `FBApplication.OnFileOpenCompleted` - File > Open
- `FBApplication.OnFileMerge` - File > Merge
- `FBSystem.Scene.OnChange` - Object add/delete

All callbacks are registered on dialog open and unregistered on close.
