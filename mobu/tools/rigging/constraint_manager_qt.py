"""
Constraint Manager Tool (Qt Designer version)
Create and manage constraints easily in MotionBuilder
"""

from pathlib import Path
import json

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
    FBMessageBox, FBModelList, FBGetSelectedModels,
    FBSystem, FBConstraintManager
)
from core.logger import logger

TOOL_NAME = "Constraint Manager"

# Global reference to prevent garbage collection
_constraint_manager_dialog = None


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

    if _constraint_manager_dialog is not None:
        print("[Constraint Manager Qt] Bringing existing dialog to front")
        _constraint_manager_dialog.show()
        _constraint_manager_dialog.raise_()
        _constraint_manager_dialog.activateWindow()
        return

    print("[Constraint Manager Qt] Creating new dialog")
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
        self.selected_objects = []
        self.constraint_sources = []
        self.constraint_weight = 100.0
        self.preset_path = self._get_preset_path()

        # Load the UI file
        ui_path = Path(__file__).parent / "constraint_manager.ui"
        self.load_ui(str(ui_path))

    def _get_preset_path(self):
        """Get the path to the presets directory"""
        root = Path(__file__).parent.parent.parent.parent
        preset_dir = root / "presets" / "constraints"
        preset_dir.mkdir(parents=True, exist_ok=True)
        return preset_dir

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
            ui_widget = loader.load(file, self)
            file.close()

            if ui_widget:
                print(f"[Constraint Manager Qt] UI widget loaded")

                # Create layout and add the loaded widget
                layout = QtWidgets.QVBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(ui_widget)
                self.setLayout(layout)

                # Store references to UI elements using findChild
                self.selectionList = ui_widget.findChild(QtWidgets.QListWidget, "selectionList")
                self.refreshButton = ui_widget.findChild(QtWidgets.QPushButton, "refreshButton")
                self.setSourceButton = ui_widget.findChild(QtWidgets.QPushButton, "setSourceButton")

                self.constraintTypeCombo = ui_widget.findChild(QtWidgets.QComboBox, "constraintTypeCombo")
                self.weightSlider = ui_widget.findChild(QtWidgets.QSlider, "weightSlider")
                self.weightValueLabel = ui_widget.findChild(QtWidgets.QLabel, "weightValueLabel")
                self.createConstraintButton = ui_widget.findChild(QtWidgets.QPushButton, "createConstraintButton")
                self.snapButton = ui_widget.findChild(QtWidgets.QPushButton, "snapButton")

                self.templateNameEdit = ui_widget.findChild(QtWidgets.QLineEdit, "templateNameEdit")
                self.saveTemplateButton = ui_widget.findChild(QtWidgets.QPushButton, "saveTemplateButton")
                self.loadTemplateButton = ui_widget.findChild(QtWidgets.QPushButton, "loadTemplateButton")
                self.deleteTemplateButton = ui_widget.findChild(QtWidgets.QPushButton, "deleteTemplateButton")

                # Connect signals
                self.connect_signals()
                # Refresh selection
                self.refresh_selection()

                print("[Constraint Manager Qt] UI loaded successfully")
            else:
                print("[Constraint Manager Qt] Failed to load UI widget")

        except Exception as e:
            print(f"[Constraint Manager Qt] Error loading UI: {str(e)}")
            logger.error(f"Failed to load UI file: {str(e)}")
            import traceback
            traceback.print_exc()

    def closeEvent(self, event):
        """Handle dialog close event"""
        global _constraint_manager_dialog
        _constraint_manager_dialog = None
        event.accept()

    def connect_signals(self):
        """Connect UI signals to slots"""
        if not self.selectionList:
            print("[Constraint Manager Qt] WARNING: Widgets not found")
            return

        # Selection
        self.refreshButton.clicked.connect(self.on_refresh_selection)
        self.setSourceButton.clicked.connect(self.on_set_sources)

        # Constraint creation
        self.weightSlider.valueChanged.connect(self.on_weight_changed)
        self.createConstraintButton.clicked.connect(self.on_create_constraint)
        self.snapButton.clicked.connect(self.on_snap_constraints)

        # Templates
        self.saveTemplateButton.clicked.connect(self.on_save_template)
        self.loadTemplateButton.clicked.connect(self.on_load_template)
        self.deleteTemplateButton.clicked.connect(self.on_delete_template)

        print("[Constraint Manager Qt] Signals connected")

    def refresh_selection(self):
        """Refresh the selected objects list"""
        self.selected_objects = []
        self.selectionList.clear()

        # Get selected models
        selected = FBModelList()
        FBGetSelectedModels(selected)

        for model in selected:
            self.selected_objects.append(model)
            self.selectionList.addItem(model.Name)

        print(f"[Constraint Manager Qt] Selected {len(self.selected_objects)} objects")

    def on_refresh_selection(self):
        """Refresh button callback"""
        self.refresh_selection()

    def on_set_sources(self):
        """Set selected objects as constraint sources"""
        if not self.selected_objects:
            QMessageBox.warning(self, "No Selection", "Please select objects first")
            return

        self.constraint_sources = self.selected_objects[:]
        names = [obj.Name for obj in self.constraint_sources]

        QMessageBox.information(
            self,
            "Sources Set",
            f"Set {len(self.constraint_sources)} source(s):\n" + "\n".join(names)
        )
        print(f"[Constraint Manager Qt] Set {len(self.constraint_sources)} sources")

    def on_weight_changed(self, value):
        """Update weight label when slider changes"""
        self.constraint_weight = float(value)
        self.weightValueLabel.setText(f"{value}%")

    def on_create_constraint(self):
        """Create constraint based on selected type"""
        if not self._validate_constraint_setup():
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
            return

        if mb_type == "Relation":
            self._create_relation_constraint()
            return

        try:
            for target in self.selected_objects:
                constraint = FBConstraintManager().TypeCreateConstraint(mb_type)
                if constraint:
                    constraint.Name = f"{constraint_type}_{target.Name}"
                    constraint.ReferenceAdd(0, target)

                    for source in self.constraint_sources:
                        constraint.ReferenceAdd(1, source)

                    constraint.Weight = self.constraint_weight
                    constraint.Active = True
                    constraint.Snap()

                    print(f"[Constraint Manager Qt] Created {constraint_type} for {target.Name}")

            QMessageBox.information(
                self,
                "Success",
                f"Created {len(self.selected_objects)} {constraint_type} constraint(s)"
            )

        except Exception as e:
            logger.error(f"Failed to create constraint: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create constraint:\n{str(e)}")

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
        """Validate that we have source and target objects"""
        if not self.constraint_sources:
            QMessageBox.warning(
                self,
                "No Sources",
                "Please set source object(s) first:\n"
                "1. Select source object(s)\n"
                "2. Click 'Set as Source(s)'\n"
                "3. Select target object(s)\n"
                "4. Create constraint"
            )
            return False

        if not self.selected_objects:
            QMessageBox.warning(
                self,
                "No Targets",
                "Please select target object(s) to constrain"
            )
            return False

        return True

    def on_save_template(self):
        """Save current constraint setup as a template"""
        template_name = self.templateNameEdit.text() or "ConstraintSetup"

        if not self.selected_objects:
            QMessageBox.warning(self, "No Selection", "Please select objects with constraints to save")
            return

        try:
            template_data = {
                "name": template_name,
                "version": "1.0",
                "constraints": []
            }

            for model in self.selected_objects:
                for constraint in FBSystem().Scene.Constraints:
                    is_constrained = False
                    for i in range(constraint.ReferenceGroupGetCount(0)):
                        if constraint.ReferenceGet(0, i) == model:
                            is_constrained = True
                            break

                    if is_constrained:
                        constraint_info = {
                            "type": constraint.ClassName().replace("FB", "").replace("Constraint", ""),
                            "name": constraint.Name,
                            "weight": constraint.Weight,
                            "active": constraint.Active
                        }
                        template_data["constraints"].append(constraint_info)

            if not template_data["constraints"]:
                QMessageBox.warning(self, "No Constraints", "No constraints found on selected objects")
                return

            # Save to file
            template_file = self.preset_path / f"{template_name}.json"
            with open(template_file, 'w') as f:
                json.dump(template_data, f, indent=2)

            QMessageBox.information(
                self,
                "Template Saved",
                f"Saved {len(template_data['constraints'])} constraint(s) to:\n{template_file}"
            )
            print(f"[Constraint Manager Qt] Saved template: {template_file}")

        except Exception as e:
            logger.error(f"Failed to save template: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save template:\n{str(e)}")

    def on_load_template(self):
        """Load and show template info"""
        template_name = self.templateNameEdit.text() or "ConstraintSetup"
        template_file = self.preset_path / f"{template_name}.json"

        if not template_file.exists():
            QMessageBox.warning(
                self,
                "Template Not Found",
                f"Template '{template_name}' not found in:\n{self.preset_path}"
            )
            return

        try:
            with open(template_file, 'r') as f:
                template_data = json.load(f)

            info = f"Template: {template_data.get('name', 'Unknown')}\n"
            info += f"Constraints: {len(template_data.get('constraints', []))}\n\n"

            for c in template_data.get('constraints', []):
                info += f"- {c.get('type')} ({c.get('weight', 100)}%)\n"

            info += "\nNote: This shows template info.\n"
            info += "Create constraints manually using the buttons above."

            QMessageBox.information(self, "Template Info", info)

        except Exception as e:
            logger.error(f"Failed to load template: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load template:\n{str(e)}")

    def on_delete_template(self):
        """Delete a constraint template"""
        template_name = self.templateNameEdit.text() or "ConstraintSetup"
        template_file = self.preset_path / f"{template_name}.json"

        if not template_file.exists():
            QMessageBox.warning(self, "Template Not Found", f"Template '{template_name}' not found")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete template '{template_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                template_file.unlink()
                QMessageBox.information(self, "Deleted", f"Template '{template_name}' deleted")
                print(f"[Constraint Manager Qt] Deleted template: {template_file}")

            except Exception as e:
                logger.error(f"Failed to delete template: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to delete template:\n{str(e)}")
