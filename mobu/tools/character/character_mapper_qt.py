"""
Character Mapper Tool (Qt Designer version)
Visual character mapping with preset save/load functionality and drag-and-drop support
"""

from pathlib import Path
import json
import shutil

try:
    from PySide2 import QtWidgets, QtCore, QtUiTools, QtGui
    from PySide2.QtWidgets import QDialog, QMessageBox, QApplication, QListWidget, QListWidgetItem, QFileDialog
    from PySide2.QtCore import QFile, Qt
    from PySide2.QtGui import QDrag
except ImportError:
    try:
        from PySide import QtGui as QtWidgets
        from PySide import QtCore, QtUiTools, QtGui
        from PySide.QtGui import QDialog, QMessageBox, QApplication, QListWidget, QListWidgetItem, QFileDialog, QDrag
        from PySide.QtCore import QFile, Qt
    except ImportError:
        print("[Character Mapper Qt] ERROR: Neither PySide2 nor PySide found")
        QtWidgets = None

from pyfbsdk import (
    FBMessageBox, FBSystem, FBCharacter, FBBodyNodeId
)
from core.logger import logger
from mobu.utils import get_all_models, SceneEventManager

TOOL_NAME = "Character Mapper"

# Global reference to prevent garbage collection
_character_mapper_dialog = None


# Character bone slots in logical order
CHARACTER_SLOTS = [
    # Reference
    ("Reference", "Reference"),

    # Hips and Spine
    ("Hips", "Hips"),
    ("Spine", "Spine"),
    ("Spine1", "Spine1"),
    ("Spine2", "Spine2"),
    ("Spine3", "Spine3"),
    ("Spine4", "Spine4"),
    ("Spine5", "Spine5"),
    ("Spine6", "Spine6"),
    ("Spine7", "Spine7"),
    ("Spine8", "Spine8"),
    ("Spine9", "Spine9"),

    # Neck and Head
    ("Neck", "Neck"),
    ("Head", "Head"),

    # Left Arm
    ("LeftShoulder", "LeftShoulder"),
    ("LeftArm", "LeftArm"),
    ("LeftForeArm", "LeftForeArm"),
    ("LeftHand", "LeftHand"),

    # Right Arm
    ("RightShoulder", "RightShoulder"),
    ("RightArm", "RightArm"),
    ("RightForeArm", "RightForeArm"),
    ("RightHand", "RightHand"),

    # Left Leg
    ("LeftUpLeg", "LeftUpLeg"),
    ("LeftLeg", "LeftLeg"),
    ("LeftFoot", "LeftFoot"),

    # Right Leg
    ("RightUpLeg", "RightUpLeg"),
    ("RightLeg", "RightLeg"),
    ("RightFoot", "RightFoot"),
]


def get_mobu_main_window():
    """Get MotionBuilder's main window to use as parent"""
    try:
        app = QApplication.instance()
        if app:
            # Try to find MotionBuilder main window
            for widget in app.topLevelWidgets():
                if widget.objectName() == "MotionBuilder" or "MotionBuilder" in widget.windowTitle():
                    print(f"[Character Mapper Qt] Found parent window: {widget.windowTitle()}")
                    return widget
            # Fallback: return first top-level widget
            widgets = app.topLevelWidgets()
            if widgets:
                print(f"[Character Mapper Qt] Using first top-level widget as parent: {widgets[0].windowTitle()}")
                return widgets[0]
        return None
    except Exception as e:
        print(f"[Character Mapper Qt] Error finding parent: {str(e)}")
        return None


def execute(control, event):
    """Execute the Character Mapper tool"""
    global _character_mapper_dialog

    if _character_mapper_dialog is not None:
        print("[Character Mapper Qt] Bringing existing dialog to front")
        _character_mapper_dialog.show()
        _character_mapper_dialog.raise_()
        _character_mapper_dialog.activateWindow()
        return

    print("[Character Mapper Qt] Creating new dialog")
    parent = get_mobu_main_window()
    _character_mapper_dialog = CharacterMapperDialog(parent)
    _character_mapper_dialog.show()


class DraggableListWidget(QListWidget):
    """Custom QListWidget that supports dragging items"""

    def __init__(self, parent=None):
        super(DraggableListWidget, self).__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.SingleSelection)

    def startDrag(self, supportedActions):
        """Start a drag operation"""
        item = self.currentItem()
        if not item:
            return

        # Create drag
        drag = QDrag(self)
        mime_data = QtCore.QMimeData()

        # Store the item text
        mime_data.setText(item.text())
        drag.setMimeData(mime_data)

        # Execute drag
        drag.exec_(Qt.CopyAction)


class DroppableListWidget(QListWidget):
    """Custom QListWidget that accepts drops"""

    def __init__(self, parent=None):
        super(DroppableListWidget, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        self.parent_dialog = None  # Will be set by dialog

    def dragEnterEvent(self, event):
        """Handle drag enter"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle drop"""
        if event.mimeData().hasText():
            # Get the item that was dropped on
            pos = event.pos()
            item = self.itemAt(pos)

            if item:
                # Get the dropped text (model name)
                dropped_model_name = event.mimeData().text()

                # Notify parent dialog about the drop
                if self.parent_dialog:
                    self.parent_dialog.on_bone_dropped(item, dropped_model_name)

                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()


class CharacterMapperDialog(QDialog):
    """Character Mapper dialog using Qt Designer UI with drag-and-drop support"""

    def __init__(self, parent=None):
        super(CharacterMapperDialog, self).__init__(parent)

        # Set window flags
        if parent:
            self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
            print(f"[Character Mapper Qt] Dialog created with parent: {parent.windowTitle()}")
        else:
            self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
            print("[Character Mapper Qt] WARNING: No parent found, creating as standalone window")

        self.character = None
        self.bone_mappings = {}  # slot_name -> model
        self.all_models = []  # Store all scene models
        self.filtered_models = []  # Store filtered models
        self.preset_path = self._get_preset_path()
        self._is_closing = False

        # Load the UI file
        ui_path = Path(__file__).parent / "character_mapper.ui"
        self.load_ui(str(ui_path))

        # Setup event-based auto-refresh
        self.event_manager = SceneEventManager()
        self.event_manager.register_file_events(self.on_file_event, events=['new', 'open', 'merge'])
        self.event_manager.register_scene_changes(self.on_scene_change)

    def _get_preset_path(self):
        """Get the path to the presets directory"""
        root = Path(__file__).parent.parent.parent.parent
        preset_dir = root / "presets" / "characters"
        preset_dir.mkdir(parents=True, exist_ok=True)
        return preset_dir

    def load_ui(self, ui_file):
        """Load UI from .ui file and replace list widgets with custom ones"""
        try:
            # Set window properties
            self.setWindowTitle("Character Mapper")
            self.resize(800, 600)
            self.setMinimumSize(800, 600)

            loader = QtUiTools.QUiLoader()
            file = QFile(ui_file)

            if not file.exists():
                print(f"[Character Mapper Qt] UI file not found: {ui_file}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"UI file not found:\n{ui_file}"
                )
                return

            file.open(QFile.ReadOnly)
            print(f"[Character Mapper Qt] Loading UI from: {ui_file}")
            ui_widget = loader.load(file, self)
            file.close()

            if ui_widget:
                print(f"[Character Mapper Qt] UI widget loaded")

                # Add to layout
                self.main_layout = QtWidgets.QVBoxLayout(self)
                self.main_layout.setContentsMargins(0, 0, 0, 0)
                self.main_layout.addWidget(ui_widget)

                # Find the original list widgets
                original_mapping_list = self.findChild(QtWidgets.QListWidget, "mappingList")
                original_objects_list = self.findChild(QtWidgets.QListWidget, "objectsList")

                # Replace with custom drag-and-drop widgets
                if original_mapping_list:
                    parent_widget = original_mapping_list.parent()
                    layout = parent_widget.layout()

                    # Find index in layout
                    for i in range(layout.count()):
                        if layout.itemAt(i).widget() == original_mapping_list:
                            # Remove original
                            layout.removeWidget(original_mapping_list)
                            original_mapping_list.setParent(None)
                            original_mapping_list.deleteLater()

                            # Add custom droppable widget
                            self.mappingList = DroppableListWidget(parent_widget)
                            self.mappingList.setObjectName("mappingList")
                            self.mappingList.setAlternatingRowColors(True)
                            self.mappingList.parent_dialog = self
                            layout.insertWidget(i, self.mappingList)
                            break

                if original_objects_list:
                    parent_widget = original_objects_list.parent()
                    layout = parent_widget.layout()

                    # Find index in layout
                    for i in range(layout.count()):
                        if layout.itemAt(i).widget() == original_objects_list:
                            # Remove original
                            layout.removeWidget(original_objects_list)
                            original_objects_list.setParent(None)
                            original_objects_list.deleteLater()

                            # Add custom draggable widget
                            self.objectsList = DraggableListWidget(parent_widget)
                            self.objectsList.setObjectName("objectsList")
                            self.objectsList.setAlternatingRowColors(True)
                            layout.insertWidget(i, self.objectsList)
                            break

                # Find other UI elements
                self.searchEdit = self.findChild(QtWidgets.QLineEdit, "searchEdit")
                self.refreshButton = self.findChild(QtWidgets.QPushButton, "refreshButton")
                self.createCharacterButton = self.findChild(QtWidgets.QPushButton, "createCharacterButton")
                self.clearMappingButton = self.findChild(QtWidgets.QPushButton, "clearMappingButton")
                self.presetNameEdit = self.findChild(QtWidgets.QLineEdit, "presetNameEdit")
                self.savePresetButton = self.findChild(QtWidgets.QPushButton, "savePresetButton")
                self.loadPresetButton = self.findChild(QtWidgets.QPushButton, "loadPresetButton")
                self.exportPresetButton = self.findChild(QtWidgets.QPushButton, "exportPresetButton")
                self.importPresetButton = self.findChild(QtWidgets.QPushButton, "importPresetButton")

                # Populate mapping list with character slots
                for slot_name, _ in CHARACTER_SLOTS:
                    self.mappingList.addItem(f"{slot_name}: <None>")
                    self.bone_mappings[slot_name] = None

                # Connect signals
                self.connect_signals()

                # Load scene objects
                self.update_scene_objects()

                print("[Character Mapper Qt] UI loaded successfully")
            else:
                print("[Character Mapper Qt] Failed to load UI widget")

        except Exception as e:
            print(f"[Character Mapper Qt] Error loading UI: {str(e)}")
            logger.error(f"Failed to load UI file: {str(e)}")
            import traceback
            traceback.print_exc()

    def connect_signals(self):
        """Connect UI signals to slots"""
        if self.searchEdit:
            self.searchEdit.textChanged.connect(self.on_search_changed)

        if self.refreshButton:
            self.refreshButton.clicked.connect(self.on_refresh_clicked)

        if self.createCharacterButton:
            self.createCharacterButton.clicked.connect(self.on_create_character)

        if self.clearMappingButton:
            self.clearMappingButton.clicked.connect(self.on_clear_mapping)

        if self.savePresetButton:
            self.savePresetButton.clicked.connect(self.on_save_preset)

        if self.loadPresetButton:
            self.loadPresetButton.clicked.connect(self.on_load_preset)

        if self.exportPresetButton:
            self.exportPresetButton.clicked.connect(self.on_export_preset)

        if self.importPresetButton:
            self.importPresetButton.clicked.connect(self.on_import_preset)

        print("[Character Mapper Qt] Signals connected")

    def closeEvent(self, event):
        """Handle dialog close event"""
        global _character_mapper_dialog

        self._is_closing = True

        # Unregister event callbacks
        if hasattr(self, 'event_manager'):
            self.event_manager.unregister_all()

        _character_mapper_dialog = None
        event.accept()

    def on_file_event(self, pCaller, pEvent):
        """Callback for file operations"""
        if self._is_closing:
            return

        print(f"[Character Mapper Qt] File event detected, refreshing scene list")
        self.update_scene_objects()
        # Clear mappings on file operations
        self.on_clear_mapping()

    def on_scene_change(self, pCaller, pEvent):
        """Callback for scene changes"""
        from pyfbsdk import FBSceneChangeType

        if self._is_closing:
            return

        # Filter events - only refresh on relevant changes
        relevant_events = [
            FBSceneChangeType.kFBSceneChangeAddChild,
            FBSceneChangeType.kFBSceneChangeRemoveChild,
            FBSceneChangeType.kFBSceneChangeDestroy,
            FBSceneChangeType.kFBSceneChangeRenamed
        ]

        if pEvent.Type not in relevant_events:
            return

        print(f"[Character Mapper Qt] Scene change detected, refreshing list")
        self.update_scene_objects()

    def update_scene_objects(self):
        """Update the objects list with current scene objects"""
        print("[Character Mapper Qt] update_scene_objects() called")

        try:
            # Get all models from scene
            self.all_models = get_all_models()

            # Sort by name
            self.all_models.sort(key=lambda x: x.Name)

            # Apply filter
            self.apply_filter()

            print(f"[Character Mapper Qt] Loaded {len(self.all_models)} objects")

        except Exception as e:
            print(f"[Character Mapper Qt] ERROR in update_scene_objects: {e}")
            import traceback
            traceback.print_exc()

    def apply_filter(self):
        """Apply search filter to objects list"""
        filter_text = self.searchEdit.text().lower() if self.searchEdit else ""

        # Clear list
        self.objectsList.clear()

        # Filter and populate
        if not filter_text:
            # No filter, show all
            for model in self.all_models:
                self.objectsList.addItem(model.Name)
        else:
            # Filter by name
            for model in self.all_models:
                if filter_text in model.Name.lower():
                    self.objectsList.addItem(model.Name)

    def on_search_changed(self, text):
        """Handle search text change"""
        self.apply_filter()

    def on_refresh_clicked(self):
        """Handle refresh button click"""
        print("[Character Mapper Qt] Refresh button clicked")
        self.update_scene_objects()

    def on_bone_dropped(self, target_item, dropped_model_name):
        """Handle a bone being dropped onto a character slot"""
        # Get the slot index
        slot_index = self.mappingList.row(target_item)
        if slot_index < 0 or slot_index >= len(CHARACTER_SLOTS):
            return

        slot_name = CHARACTER_SLOTS[slot_index][0]

        # Find the model
        model = None
        for m in self.all_models:
            if m.Name == dropped_model_name:
                model = m
                break

        if not model:
            print(f"[Character Mapper Qt] WARNING: Model '{dropped_model_name}' not found")
            return

        # Store mapping
        self.bone_mappings[slot_name] = model

        # Update display
        target_item.setText(f"{slot_name}: {model.Name}")

        print(f"[Character Mapper Qt] Mapped {slot_name} -> {model.Name}")

    def on_clear_mapping(self):
        """Clear all bone mappings"""
        for i, (slot_name, _) in enumerate(CHARACTER_SLOTS):
            self.bone_mappings[slot_name] = None
            item = self.mappingList.item(i)
            if item:
                item.setText(f"{slot_name}: <None>")

        print("[Character Mapper Qt] Cleared all mappings")

    def on_create_character(self):
        """Create character from current mapping"""
        print("[Character Mapper Qt] Creating character...")

        try:
            # Check required bones
            required = ["Hips", "LeftUpLeg", "RightUpLeg", "Spine"]
            missing = [slot for slot in required if not self.bone_mappings.get(slot)]

            if missing:
                QMessageBox.warning(
                    self,
                    "Missing Required Bones",
                    f"Please map these required bones:\n{', '.join(missing)}"
                )
                return

            # Create character
            char_name = self.presetNameEdit.text() or "Character"
            self.character = FBCharacter(char_name)

            # Map bones
            for slot_name, _ in CHARACTER_SLOTS:
                model = self.bone_mappings.get(slot_name)
                if model:
                    self.character.SetCharacterizeOn(False)
                    prop_list = self.character.PropertyList.Find(slot_name + "Link")
                    if prop_list:
                        prop_list.append(model)
                        print(f"[Character Mapper Qt] Linked {slot_name} -> {model.Name}")
                    else:
                        print(f"[Character Mapper Qt WARNING] Could not find property {slot_name}Link")

            # Characterize
            self.character.SetCharacterizeOn(True)

            if self.character.GetCharacterizeError():
                error_msg = "Characterization failed. Check bone positions and hierarchy."
                QMessageBox.critical(self, "Characterization Error", error_msg)
                print(f"[Character Mapper Qt ERROR] {error_msg}")
            else:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Character '{self.character.Name}' created successfully!"
                )
                print(f"[Character Mapper Qt] Character created: {self.character.Name}")

        except Exception as e:
            logger.error(f"Characterization failed: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create character:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def on_save_preset(self):
        """Save current mapping as a preset"""
        preset_name = self.presetNameEdit.text() or "Character"

        # Build preset data
        preset_data = {
            "name": preset_name,
            "version": "1.0",
            "mappings": {}
        }

        # Save model names, not objects
        for slot_name, model in self.bone_mappings.items():
            if model:
                preset_data["mappings"][slot_name] = model.LongName

        # Save to file
        preset_file = self.preset_path / f"{preset_name}.json"
        try:
            with open(preset_file, 'w') as f:
                json.dump(preset_data, f, indent=2)

            QMessageBox.information(
                self,
                "Preset Saved",
                f"Preset saved to:\n{preset_file}"
            )
            print(f"[Character Mapper Qt] Saved preset: {preset_file}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save preset:\n{str(e)}")
            logger.error(f"Failed to save preset: {str(e)}")

    def on_load_preset(self):
        """Load a preset"""
        preset_name = self.presetNameEdit.text() or "Character"
        preset_file = self.preset_path / f"{preset_name}.json"

        if not preset_file.exists():
            QMessageBox.warning(
                self,
                "Preset Not Found",
                f"Preset '{preset_name}' not found.\n\nAvailable presets in:\n{self.preset_path}"
            )
            return

        try:
            with open(preset_file, 'r') as f:
                preset_data = json.load(f)

            # Clear and apply mappings
            self.on_clear_mapping()

            # Find models by name and map them
            for slot_name, bone_name in preset_data.get("mappings", {}).items():
                if slot_name in self.bone_mappings:
                    # Find the model
                    model = self._find_model_by_name(bone_name)
                    if model:
                        self.bone_mappings[slot_name] = model

                        # Update display
                        for i, (s_name, _) in enumerate(CHARACTER_SLOTS):
                            if s_name == slot_name:
                                item = self.mappingList.item(i)
                                if item:
                                    item.setText(f"{slot_name}: {model.Name}")
                                break
                    else:
                        print(f"[Character Mapper Qt WARNING] Model '{bone_name}' not found in scene")

            QMessageBox.information(self, "Preset Loaded", f"Preset '{preset_name}' loaded successfully!")
            print(f"[Character Mapper Qt] Loaded preset: {preset_file}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load preset:\n{str(e)}")
            logger.error(f"Failed to load preset: {str(e)}")

    def _find_model_by_name(self, name):
        """Find a model by its LongName"""
        for model in self.all_models:
            if model.LongName == name:
                return model
        return None

    def on_export_preset(self):
        """Export preset to external file"""
        preset_name = self.presetNameEdit.text() or "Character"
        preset_file = self.preset_path / f"{preset_name}.json"

        if not preset_file.exists():
            QMessageBox.warning(
                self,
                "Preset Not Found",
                f"Preset '{preset_name}' not found.\nPlease save the preset first."
            )
            return

        # Show file save dialog
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Character Preset",
            f"{preset_name}.json",
            "JSON Files (*.json)"
        )

        if export_path:
            try:
                shutil.copy2(preset_file, export_path)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Preset exported to:\n{export_path}"
                )
                print(f"[Character Mapper Qt] Exported preset to: {export_path}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export preset:\n{str(e)}")
                logger.error(f"Failed to export preset: {str(e)}")

    def on_import_preset(self):
        """Import preset from external file"""
        # Show file open dialog
        import_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Character Preset",
            "",
            "JSON Files (*.json)"
        )

        if import_path:
            try:
                import_path = Path(import_path)

                # Read the preset
                with open(import_path, 'r') as f:
                    preset_data = json.load(f)

                preset_name = preset_data.get("name", import_path.stem)

                # Copy to presets directory
                dest_file = self.preset_path / f"{preset_name}.json"
                shutil.copy2(import_path, dest_file)

                # Update preset name field
                self.presetNameEdit.setText(preset_name)

                # Load the preset
                self.on_clear_mapping()

                # Find models by name and map them
                for slot_name, bone_name in preset_data.get("mappings", {}).items():
                    if slot_name in self.bone_mappings:
                        model = self._find_model_by_name(bone_name)
                        if model:
                            self.bone_mappings[slot_name] = model

                            # Update display
                            for i, (s_name, _) in enumerate(CHARACTER_SLOTS):
                                if s_name == slot_name:
                                    item = self.mappingList.item(i)
                                    if item:
                                        item.setText(f"{slot_name}: {model.Name}")
                                    break
                        else:
                            print(f"[Character Mapper Qt WARNING] Model '{bone_name}' not found in scene")

                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Preset '{preset_name}' imported and loaded!"
                )
                print(f"[Character Mapper Qt] Imported preset from: {import_path}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import preset:\n{str(e)}")
                logger.error(f"Failed to import preset: {str(e)}")
