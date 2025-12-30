# Qt Tool Window Standards

## Overview
All Qt-based tool windows in xMobu must follow these standards to ensure proper integration with MotionBuilder.

## Required Implementation Pattern

### 1. Parent Window Detection
Every Qt tool must include this helper function:

```python
def get_mobu_main_window():
    """Get MotionBuilder's main window to use as parent"""
    try:
        app = QApplication.instance()
        if app:
            # Try to find MotionBuilder main window
            for widget in app.topLevelWidgets():
                if widget.objectName() == "MotionBuilder" or "MotionBuilder" in widget.windowTitle():
                    print(f"[Tool Name] Found parent window: {widget.windowTitle()}")
                    return widget
            # Fallback: return first top-level widget
            widgets = app.topLevelWidgets()
            if widgets:
                print(f"[Tool Name] Using first top-level widget as parent: {widgets[0].windowTitle()}")
                return widgets[0]
        return None
    except Exception as e:
        print(f"[Tool Name] Error finding parent: {str(e)}")
        return None
```

### 2. Singleton Pattern
Use a global reference to prevent garbage collection and ensure only one instance:

```python
# Global reference to prevent garbage collection
_tool_dialog = None

def execute(control, event):
    """Execute the Tool"""
    global _tool_dialog

    if _tool_dialog is not None:
        print("[Tool Name] Bringing existing dialog to front")
        _tool_dialog.show()
        _tool_dialog.raise_()
        _tool_dialog.activateWindow()
        return

    print("[Tool Name] Creating new dialog")
    parent = get_mobu_main_window()
    _tool_dialog = ToolDialog(parent)
    _tool_dialog.show()
```

### 3. Dialog Class Setup
Proper QDialog initialization with correct window flags:

```python
class ToolDialog(QDialog):
    """Tool dialog using Qt Designer UI"""

    def __init__(self, parent=None):
        super(ToolDialog, self).__init__(parent)
        # Set window flags - don't use Qt.Window to allow proper parenting
        if parent:
            self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
            print(f"[Tool Name] Dialog created with parent: {parent.windowTitle()}")
        else:
            self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
            print("[Tool Name] WARNING: No parent found, creating as standalone window")

        # Load UI and initialize
        ui_path = Path(__file__).parent / "tool_name.ui"
        self.load_ui(str(ui_path))

    def closeEvent(self, event):
        """Handle dialog close event"""
        global _tool_dialog
        _tool_dialog = None
        event.accept()
```

## Critical Rules

### ✅ DO:
- Always pass parent window to QDialog constructor
- Use `Qt.Dialog` flag when parent exists
- Implement singleton pattern with global reference
- Clear global reference in `closeEvent`
- Add debug print statements for parent detection
- Use Qt Designer (.ui files) for UI layout

### ❌ DON'T:
- Don't use `Qt.Window` flag when parent exists (breaks parenting)
- Don't create multiple instances of the same tool
- Don't forget to implement `closeEvent` to clear global reference
- Don't skip parent window detection

## Example Files
Reference implementations:
- `mobu/tools/pipeline/settings_qt.py`
- `mobu/tools/rigging/constraint_manager_qt.py`

## Why This Matters
Proper parenting ensures:
- Tool windows stay attached to MotionBuilder
- Windows don't appear as separate taskbar items
- Tools are properly destroyed when MotionBuilder closes
- Consistent user experience across all tools
