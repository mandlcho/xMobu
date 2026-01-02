"""
Constraint Manager Tool (Qt Designer version)
Create and manage constraints easily in MotionBuilder
"""

from pathlib import Path

try:
    from PySide2 import QtWidgets, QtCore, QtUiTools
    from PySide2.QtWidgets import QDialog, QMessageBox, QApplication
    from PySide2.QtCore import QFile, Qt
except ImportError:
    try:
        from PySide import QtGui as QtWidgets
        from PySide import QtCore, QtUiTools
        from PySide.QtGui import QDialog, QMessageBox, QApplication
        from PySide.QtCore import QFile, Qt
    except ImportError:
        print("[Constraint Manager Qt] ERROR: Neither PySide2 nor PySide found")
        QtWidgets = None

from pyfbsdk import (
    FBMessageBox, FBSystem, FBConstraintManager, FBApplication
)
from core.logger import logger
from mobu.utils import get_all_models, SceneEventManager

TOOL_NAME = "Constraint Manager"

# Global reference to prevent garbage collection
_constraint_manager_dialog = None
_q_application_instance = None # Global reference to the QApplication instance


def get_mobu_main_window():
    """Get MotionBuilder's main window to use as parent"""
    try:
        app = QApplication.instance()
        if app:
            # Try to find MotionBuilder main window
            for widget in app.topLevelWidgets():
                if widget.objectName() == "MotionBuilder" or "MotionBuilder" in widget.windowTitle():
                    print(f"[Constraint Manager Qt] Found parent window: {widget.windowTitle()}")
                    return widget
            # Fallback: return first top-level widget
            widgets = app.topLevelWidgets()
            if widgets:
                print(f"[Constraint Manager Qt] Using first top-level widget as parent: {widgets[0].windowTitle()}")
                return widgets[0]
        return None
    except Exception as e:
        print(f"[Constraint Manager Qt] Error finding parent: {str(e)}")
        return None


def execute(control, event):
    """Execute the Constraint Manager tool"""
    global _constraint_manager_dialog
    global _q_application_instance  # Ensure QApplication instance is kept alive

    if _constraint_manager_dialog is not None:
        print("[Constraint Manager Qt] Bringing existing dialog to front")
        _constraint_manager_dialog.show()
        _constraint_manager_dialog.raise_()
        _constraint_manager_dialog.activateWindow()
        return

    print("[Constraint Manager Qt] Creating new dialog")

    # Store QApplication instance globally to prevent premature garbage collection
    _q_application_instance = QApplication.instance()

    parent = get_mobu_main_window()
    _constraint_manager_dialog = ConstraintManagerDialog(parent)
    _constraint_manager_dialog.show()


class ConstraintManagerDialog(QDialog):
    """Constraint Manager dialog using Qt Designer UI"""

    def __init__(self, parent=None):
        super(ConstraintManagerDialog, self).__init__(parent)
        # Set window flags - don't use Qt.Window to allow proper parenting
        if parent:
            self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
            print(f"[Constraint Manager Qt] Dialog created with parent: {parent.windowTitle()}")
        else:
            self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
            print("[Constraint Manager Qt] WARNING: No parent found, creating as standalone window")
        self.all_scene_objects = []  # All objects in scene
        self.selected_objects = []    # Objects selected through the list (tracks order)
        self.constraint_parents = []  # Parent objects for constraint
        self.constraint_children = []  # Child objects for constraint
        self._is_closing = False      # Flag to prevent callback execution during close

        # Load the UI file
        ui_path = Path(__file__).parent / "constraint_manager.ui"
        self.load_ui(str(ui_path))

        # Setup event-based auto-refresh using utility
        self.event_manager = SceneEventManager()
        self.event_manager.register_file_events(self.on_file_event, events=['new', 'open', 'merge'])
        self.event_manager.register_scene_changes(self.on_scene_change)

    def load_ui(self, ui_file):
        """Load UI from .ui file"""
        try:
            # Set window properties
            self.setWindowTitle("Constraint Manager")
            self.resize(500, 450)
            self.setMinimumSize(500, 450)
            self.setMaximumSize(700, 600)

            loader = QtUiTools.QUiLoader()
            file = QFile(ui_file)

            if not file.exists():
                print(f"[Constraint Manager Qt] UI file not found: {ui_file}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"UI file not found:\n{ui_file}"
                )
                return

            file.open(QFile.ReadOnly)
            print(f"[Constraint Manager Qt] Loading UI from: {ui_file}")
            # Load with `self` as parent and store a reference
            self.ui_widget = loader.load(file, self)
            file.close()

            if self.ui_widget:
                print(f"[Constraint Manager Qt] UI widget loaded")

                # The loaded widget is now a child of the dialog.
                # We add it to a layout to make it fill the dialog.
                self.main_layout = QtWidgets.QVBoxLayout(self)
                self.main_layout.setContentsMargins(0, 0, 0, 0)
                self.main_layout.addWidget(self.ui_widget)

                # Store references to UI elements using findChild on `self`.
                self.selectionList = self.findChild(QtWidgets.QListWidget, "selectionList")
                self.refreshButton = self.findChild(QtWidgets.QPushButton, "refreshButton")
                self.setParentButton = self.findChild(QtWidgets.QPushButton, "setParentButton")
                self.setChildButton = self.findChild(QtWidgets.QPushButton, "setChildButton")
                self.clearSelectionButton = self.findChild(QtWidgets.QPushButton, "clearSelectionButton")

                self.constraintTypeCombo = self.findChild(QtWidgets.QComboBox, "constraintTypeCombo")
                self.activeCheckbox = self.findChild(QtWidgets.QCheckBox, "activeCheckbox")
                self.snapButton = self.findChild(QtWidgets.QPushButton, "snapButton")

                # Debug: Print widget references
                print(f"[Constraint Manager Qt] selectionList: {self.selectionList}")
                print(f"[Constraint Manager Qt] refreshButton: {self.refreshButton}")

                # Verify widgets are valid right after creation
                try:
                    test_count = self.selectionList.count()
                    print(f"[Constraint Manager Qt] Widget validation at creation: SUCCESS (count={test_count})")
                except (RuntimeError, AttributeError) as e:
                    print(f"[Constraint Manager Qt] Widget validation at creation: FAILED - {e}")

                # Connect signals
                self.connect_signals()

                print("[Constraint Manager Qt] UI loaded successfully")
            else:
                print("[Constraint Manager Qt] Failed to load UI widget")

        except Exception as e:
            print(f"[Constraint Manager Qt] Error loading UI: {str(e)}")
            logger.error(f"Failed to load UI file: {str(e)}")
            import traceback
            traceback.print_exc()

        # Populate scene objects AFTER UI is fully loaded
        self.update_list_widget()

    def closeEvent(self, event):
        """Handle dialog close event"""
        global _constraint_manager_dialog
        global _q_application_instance

        # Set closing flag FIRST to prevent callbacks
        self._is_closing = True

        # Unregister event callbacks using utility
        if hasattr(self, 'event_manager'):
            self.event_manager.unregister_all()

        _constraint_manager_dialog = None
        _q_application_instance = None # Clear global QApplication reference
        event.accept()

    def connect_signals(self):
        """Connect UI signals to slots"""
        if not self.selectionList:
            print("[Constraint Manager Qt] WARNING: Widgets not found")
            return

        # List widget - click to select object in viewport
        self.selectionList.itemClicked.connect(self.on_list_item_clicked)

        # Selection buttons
        if self.refreshButton:
            # Use lambda to ensure clean call without Qt's bool parameter
            self.refreshButton.clicked.connect(self.on_refresh_clicked)
            print("[Constraint Manager Qt] Refresh button signal connected")
        else:
            print("[Constraint Manager Qt] WARNING: Refresh button not found!")

        if self.setParentButton:
            self.setParentButton.clicked.connect(self.on_set_parent)
        else:
            print("[Constraint Manager Qt] WARNING: Set parent button not found!")

        if self.setChildButton:
            self.setChildButton.clicked.connect(self.on_set_child)
        else:
            print("[Constraint Manager Qt] WARNING: Set child button not found!")

        if self.clearSelectionButton:
            self.clearSelectionButton.clicked.connect(self.on_clear_selection)
        else:
            print("[Constraint Manager Qt] WARNING: Clear selection button not found!")

        # Constraint controls - Active checkbox triggers constraint creation
        if self.activeCheckbox:
            self.activeCheckbox.stateChanged.connect(self.on_active_changed)

        if self.snapButton:
            self.snapButton.clicked.connect(self.on_snap_constraints)

        print("[Constraint Manager Qt] Signals connected")

    def on_file_event(self, pCaller, pEvent):
        """Callback for file operations (new/open/merge)"""
        if self._is_closing:
            return

        print(f"[Constraint Manager Qt] File event detected, refreshing scene list")
        self.update_list_widget()
        # Clear selections on file operations
        self.selected_objects = []
        self.constraint_parents = []
        self.constraint_children = []

    def on_scene_change(self, pCaller, pEvent):
        """Callback for scene changes (object add/delete)"""
        from pyfbsdk import FBSceneChangeType

        if self._is_closing:
            return

        # Filter events - only refresh on relevant changes
        relevant_events = [
            FBSceneChangeType.kFBSceneChangeAddChild,
            FBSceneChangeType.kFBSceneChangeRemoveChild,
            FBSceneChangeType.kFBSceneChangeDestroy,
            FBSceneChangeType.kFBSceneChangeRenamed,
            FBSceneChangeType.kFBSceneChangeAttach,
            FBSceneChangeType.kFBSceneChangeDetach
        ]

        if pEvent.Type not in relevant_events:
            return

        print(f"[Constraint Manager Qt] Scene change detected, refreshing list")
        self.update_list_widget()

        # Clean up selected_objects list - remove any deleted objects
        self.selected_objects = [obj for obj in self.selected_objects
                                if obj in self.all_scene_objects]

    def update_list_widget(self):
        """
        Dedicated function to update the list widget with current scene objects.
        Handles clearing, repopulating, and forcing UI refresh.
        """
        print("[Constraint Manager Qt] update_list_widget() called")

        # DEBUG: Re-find the widget each time to ensure we have a valid reference
        selection_list = self.findChild(QtWidgets.QListWidget, "selectionList")

        if not selection_list:
            print("[Constraint Manager Qt] FATAL: Could not find 'selectionList' in UI on refresh.")
            return

        try:
            # Clear the list
            selection_list.clear()

            # Get all models from the scene
            self.all_scene_objects = get_all_models()

            # Sort by name for easier finding
            self.all_scene_objects.sort(key=lambda x: x.Name)

            # Populate the list widget
            for model in self.all_scene_objects:
                selection_list.addItem(model.Name)

            print(f"[Constraint Manager Qt] List updated with {len(self.all_scene_objects)} objects")

            # Force Qt widget updates
            selection_list.update()
            selection_list.repaint()

            # Force MotionBuilder UI update
            FBApplication().UpdateAllWidgets()

            print(f"[Constraint Manager Qt] UI refresh complete")

        except RuntimeError as e:
            print(f"[Constraint Manager Qt] RuntimeError during update: {e}")
            return
        except Exception as e:
            print(f"[Constraint Manager Qt] ERROR in update_list_widget: {e}")
            import traceback
            traceback.print_exc()
            return

    def on_refresh_clicked(self):
        """Handle refresh button click"""
        print("[Constraint Manager Qt] ===== REFRESH BUTTON CLICKED =====")
        self.update_list_widget()
        print("[Constraint Manager Qt] ===== REFRESH COMPLETE =====")

    def populate_scene_objects(self, silent=False):
        """Populate list with all objects in the scene (legacy method - calls update_list_widget)"""
        if not silent:
            print(f"[Constraint Manager Qt] populate_scene_objects called (redirecting to update_list_widget)")
        self.update_list_widget()

    def on_list_item_clicked(self, item):
        """Handle clicking on list item - select object in viewport"""
        # Get the model name from the clicked item
        model_name = item.text()

        # Find the corresponding model
        model = None
        for obj in self.all_scene_objects:
            if obj.Name == model_name:
                model = obj
                break

        if not model:
            print(f"[Constraint Manager Qt] WARNING: Model '{model_name}' not found")
            return

        # Check if Ctrl or Shift is pressed for multi-selection
        modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.ControlModifier:
            # Ctrl: Toggle selection (add/remove from selection)
            if model in self.selected_objects:
                self.selected_objects.remove(model)
                model.Selected = False
                print(f"[Constraint Manager Qt] Removed from selection: {model.Name}")
            else:
                self.selected_objects.append(model)
                model.Selected = True
                print(f"[Constraint Manager Qt] Added to selection: {model.Name}")
        else:
            # No modifier: Clear selection and select only this object
            # Clear all selections first
            for obj in self.selected_objects:
                obj.Selected = False

            self.selected_objects = [model]
            model.Selected = True
            print(f"[Constraint Manager Qt] Selected: {model.Name}")

        print(f"[Constraint Manager Qt] Selection order: {[obj.Name for obj in self.selected_objects]}")

    def on_clear_selection(self):
        """Clear all selections in viewport"""
        for obj in self.selected_objects:
            obj.Selected = False

        self.selected_objects = []
        print("[Constraint Manager Qt] Cleared all selections")

    def on_set_parent(self):
        """Set selected objects as constraint parents"""
        if not self.selected_objects:
            QMessageBox.warning(self, "No Selection", "Please select objects first")
            return

        self.constraint_parents = self.selected_objects[:]
        names = [obj.Name for obj in self.constraint_parents]

        QMessageBox.information(
            self,
            "Parent Set",
            f"Set {len(self.constraint_parents)} parent(s):\n" + "\n".join(names)
        )
        print(f"[Constraint Manager Qt] Set {len(self.constraint_parents)} parents")

    def on_set_child(self):
        """Set selected objects as constraint children"""
        if not self.selected_objects:
            QMessageBox.warning(self, "No Selection", "Please select objects first")
            return

        self.constraint_children = self.selected_objects[:]
        names = [obj.Name for obj in self.constraint_children]

        QMessageBox.information(
            self,
            "Child Set",
            f"Set {len(self.constraint_children)} child(ren):\n" + "\n".join(names)
        )
        print(f"[Constraint Manager Qt] Set {len(self.constraint_children)} children")

    def on_active_changed(self, state):
        """Toggle constraint active state or create new constraint"""
        is_active = (state == 2)  # Qt.Checked = 2

        if not self._validate_constraint_setup():
            # Reset checkbox if validation fails
            self.activeCheckbox.setChecked(False)
            return

        constraint_type = self.constraintTypeCombo.currentText()

        # Map UI names to MB constraint types
        constraint_map = {
            "Parent/Child": "Parent/Child",
            "Position": "Position",
            "Rotation": "Rotation",
            "Aim": "Aim",
            "Relation": "Relation"
        }

        mb_type = constraint_map.get(constraint_type)
        if not mb_type:
            QMessageBox.warning(self, "Error", f"Unknown constraint type: {constraint_type}")
            self.activeCheckbox.setChecked(False)
            return

        if mb_type == "Relation":
            self._create_relation_constraint()
            return

        try:
            # Use children if set, otherwise fall back to selected objects
            targets = self.constraint_children if self.constraint_children else self.selected_objects

            for target in targets:
                constraint = FBConstraintManager().TypeCreateConstraint(mb_type)
                if constraint:
                    constraint.Name = f"{constraint_type}_{target.Name}"
                    constraint.ReferenceAdd(0, target)

                    for parent in self.constraint_parents:
                        constraint.ReferenceAdd(1, parent)

                    constraint.Weight = 100.0
                    constraint.Active = is_active
                    if is_active:
                        constraint.Snap()

                    print(f"[Constraint Manager Qt] Created {constraint_type} for {target.Name} (Active={is_active})")

            QMessageBox.information(
                self,
                "Success",
                f"Created {len(targets)} {constraint_type} constraint(s)"
            )

        except Exception as e:
            logger.error(f"Failed to create constraint: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create constraint:\n{str(e)}")
            self.activeCheckbox.setChecked(False)

    def _create_relation_constraint(self):
        """Create relation constraint"""
        QMessageBox.information(
            self,
            "Relation Constraint",
            "Relation constraints require custom setup.\n\n"
            "This will create a basic relation constraint.\n"
            "Use the Relations Editor to customize the expression."
        )

        try:
            constraint = FBConstraintManager().TypeCreateConstraint("Relation")
            if constraint:
                constraint.Name = "Relation_Custom"
                constraint.Active = True

                QMessageBox.information(
                    self,
                    "Success",
                    f"Created relation constraint: {constraint.Name}\n\n"
                    "Use the Relations Editor (Window > Relations) to set up expressions."
                )
                print(f"[Constraint Manager Qt] Created relation constraint")

        except Exception as e:
            logger.error(f"Failed to create relation constraint: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create constraint:\n{str(e)}")

    def on_snap_constraints(self):
        """Snap all active constraints on selected objects"""
        if not self.selected_objects:
            QMessageBox.warning(self, "No Selection", "Please select constrained objects")
            return

        try:
            snapped_count = 0
            for model in self.selected_objects:
                for constraint in FBSystem().Scene.Constraints:
                    if constraint.Active:
                        for i in range(constraint.ReferenceGroupGetCount(0)):
                            if constraint.ReferenceGet(0, i) == model:
                                constraint.Snap()
                                snapped_count += 1
                                break

            if snapped_count > 0:
                QMessageBox.information(self, "Success", f"Snapped {snapped_count} constraint(s)")
            else:
                QMessageBox.information(self, "Info", "No active constraints found on selected objects")

        except Exception as e:
            logger.error(f"Failed to snap constraints: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to snap constraints:\n{str(e)}")

    def _validate_constraint_setup(self):
        """Validate that we have parent and child objects"""
        if not self.constraint_parents:
            QMessageBox.warning(
                self,
                "No Parent",
                "Please set parent object(s) first:\n"
                "1. Select parent object(s)\n"
                "2. Click 'Set as Parent'\n"
                "3. Select child object(s)\n"
                "4. Click 'Set as Child'\n"
                "5. Check 'Active' to create constraint"
            )
            return False

        # Use children if set, otherwise check selected objects
        targets = self.constraint_children if self.constraint_children else self.selected_objects

        if not targets:
            QMessageBox.warning(
                self,
                "No Child",
                "Please select child object(s):\n"
                "1. Select child object(s)\n"
                "2. Click 'Set as Child'"
            )
            return False

        return True
