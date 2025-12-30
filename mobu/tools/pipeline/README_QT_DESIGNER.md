# Using Qt Designer with xMobu Settings

This guide explains how to use Qt Designer to modify the Settings UI.

## Overview

The Settings tool now has two versions:
- **Settings...** - Original version using pyfbsdk UI elements
- **Settings (Qt)...** - Qt Designer version using `settings.ui`

## Files

- `settings.ui` - Qt Designer UI file (edit this in Qt Designer)
- `settings_qt.py` - Python code that loads the .ui file
- `settings.py` - Original FBTool version (for reference)

## Editing the UI

### 1. Install Qt Designer

Qt Designer is included with:
- **PyQt5**: `pip install pyqt5-tools` (includes designer.exe)
- **PySide2**: Part of the Qt installation
- **Standalone**: Download from Qt website

### 2. Open the UI File

```bash
# Windows (if installed via pyqt5-tools)
designer.exe settings.ui

# Or just double-click settings.ui if Qt Designer is associated
```

### 3. Edit the UI

The UI is structured as:
- **QTabWidget** with two tabs:
  - **Perforce** tab - P4 connection settings
  - **Export** tab - Export path settings
- **Buttons** at the bottom - Save, Reset, Apply and Close

#### Widget Names (Important!)

These widget names are referenced in `settings_qt.py`. Don't rename them:

**Perforce Tab:**
- `p4ServerEdit` - QLineEdit for server
- `p4UserEdit` - QLineEdit for user
- `p4WorkspaceList` - QListWidget for workspaces
- `testP4Button` - QPushButton for testing connection
- `p4StatusLabel` - QLabel for status messages

**Export Tab:**
- `fbxPathEdit` - QLineEdit for FBX path
- `browseFbxButton` - QPushButton for browse dialog

**Buttons:**
- `saveButton` - Save settings
- `resetButton` - Reset to defaults
- `applyCloseButton` - Apply and close

### 4. Save and Test

1. Save the .ui file in Qt Designer
2. In MotionBuilder, go to `xMobu > Reload xMobu`
3. Test with `xMobu > Settings (Qt)...`

## Adding New UI Elements

If you add new widgets in Qt Designer:

1. **Add the widget** with a meaningful name
2. **Update `settings_qt.py`**:
   - Add signal connections in `connect_signals()`
   - Add load/save logic in `load_settings()` / `on_save_settings()`
   - Add handler methods as needed

Example:
```python
# In connect_signals()
self.ui.myNewButton.clicked.connect(self.on_my_new_button)

# Add handler
def on_my_new_button(self):
    print("Button clicked!")
```

## Troubleshooting

### UI File Not Found
- Check that `settings.ui` is in the same directory as `settings_qt.py`
- Check the console output for the full path being searched

### Widgets Not Found
- Make sure widget names in Qt Designer match the names used in `settings_qt.py`
- Use `findChild()` to debug: `widget = self.ui.findChild(QLineEdit, "p4ServerEdit")`

### PySide2 Not Found
- MotionBuilder 2020+ uses PySide2
- Older versions may use PySide
- The code auto-detects and falls back

## Qt Designer Tips

### Layout Management
- Use layouts (QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout)
- Right-click → Layout to apply layouts
- Use spacers to control spacing

### Property Editor
- Set `placeholderText` on QLineEdit for hints
- Set `toolTip` for hover help text
- Set `objectName` to meaningful names (used in code)

### Preview
- Use `Form > Preview` (Ctrl+R) to test the UI
- This shows how it will look in the application

## Benefits of Qt Designer

✅ **Visual editing** - Drag and drop UI design
✅ **Faster iteration** - No code changes for layout adjustments
✅ **Better layouts** - Qt's layout system handles resizing
✅ **Separation of concerns** - UI design separate from logic
✅ **Reusability** - .ui files can be used across projects

## Migrating Back to FBTool

If you prefer the FBTool version:
- The original `settings.py` is still available
- Use `xMobu > Settings...` (without Qt)
- Both versions save to the same config file
