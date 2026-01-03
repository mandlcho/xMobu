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
    FBMessageBox, FBSystem, FBCharacter, FBBodyNodeId, FBVector3d, FBCamera
)
from core.logger import logger
from mobu.utils import get_all_models, get_children, SceneEventManager, refresh_list_widget

TOOL_NAME = "Character Mapper"

# Global reference to prevent garbage collection
_character_mapper_dialog = None


# Character bone slots in logical order
# REQUIRED bones: Hips, Spine, LeftUpLeg, RightUpLeg
# OPTIONAL bones: All other bones including Spine1-9, arms, hands, feet, neck, head, etc.
# Note: Only ONE Spine bone is required. Additional spine bones provide more control.
CHARACTER_SLOTS = [
    # Reference
    ("Reference", "Reference"),

    # Hips and Spine
    ("Hips", "Hips"),                    # REQUIRED
    ("Spine", "Spine"),                  # REQUIRED (only this one, not Spine1-9)
    ("Spine1", "Spine1"),                # Optional
    ("Spine2", "Spine2"),                # Optional
    ("Spine3", "Spine3"),                # Optional
    ("Spine4", "Spine4"),                # Optional
    ("Spine5", "Spine5"),                # Optional
    ("Spine6", "Spine6"),                # Optional
    ("Spine7", "Spine7"),                # Optional
    ("Spine8", "Spine8"),                # Optional
    ("Spine9", "Spine9"),                # Optional

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
        self.selected_objects = []  # Track selected objects in objectsList (tracks order)
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
                self.listChildrenButton = self.findChild(QtWidgets.QPushButton, "listChildrenButton")
                self.createCharacterButton = self.findChild(QtWidgets.QPushButton, "createCharacterButton")
                self.clearMappingButton = self.findChild(QtWidgets.QPushButton, "clearMappingButton")
                self.presetNameEdit = self.findChild(QtWidgets.QLineEdit, "presetNameEdit")
                self.savePresetButton = self.findChild(QtWidgets.QPushButton, "savePresetButton")
                self.loadPresetButton = self.findChild(QtWidgets.QPushButton, "loadPresetButton")
                self.exportPresetButton = self.findChild(QtWidgets.QPushButton, "exportPresetButton")
                self.importPresetButton = self.findChild(QtWidgets.QPushButton, "importPresetButton")
                self.forceTposeCheckbox = self.findChild(QtWidgets.QCheckBox, "forceTposeCheckbox")

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

        if self.objectsList:
            self.objectsList.itemClicked.connect(self.on_object_list_item_clicked)

        if self.refreshButton:
            self.refreshButton.clicked.connect(self.on_refresh_clicked)

        if self.listChildrenButton:
            self.listChildrenButton.clicked.connect(self.on_list_children_clicked)

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
        """Callback for file operations (new/open/merge)"""
        if self._is_closing:
            return

        print(f"[Character Mapper Qt] File event detected, refreshing scene list")
        self.update_scene_objects()
        # Clear selections and mappings on file operations
        self.selected_objects = []
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
        """Update the objects list with current scene objects, filtering cameras"""
        print("[Character Mapper Qt] update_scene_objects() called")

        # Get all models from scene
        all_models = get_all_models()

        # Filter out cameras
        self.all_models = [model for model in all_models if not isinstance(model, FBCamera)]

        # Sort by name for easier finding
        self.all_models.sort(key=lambda x: x.Name)

        # Use utility function to refresh the list widget
        success = refresh_list_widget(
            parent_widget=self,
            list_widget_name="objectsList",
            models=self.all_models,
            selected_objects=self.selected_objects,
            tool_name="Character Mapper Qt"
        )

        if success:
            print(f"[Character Mapper Qt] List updated with {len(self.all_models)} objects (cameras filtered)")
            print(f"[Character Mapper Qt] UI refresh complete")
        else:
            print("[Character Mapper Qt] Failed to refresh list widget")

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
        print("[Character Mapper Qt] ===== REFRESH BUTTON CLICKED =====")
        self.update_scene_objects()
        print("[Character Mapper Qt] ===== REFRESH COMPLETE =====")

    def on_object_list_item_clicked(self, item):
        """Handle clicking on list item - select object in viewport"""
        # Get the model name from the clicked item
        model_name = item.text()

        # Find the corresponding model
        model = None
        for obj in self.all_models:
            if obj.Name == model_name:
                model = obj
                break

        if not model:
            print(f"[Character Mapper Qt] WARNING: Model '{model_name}' not found")
            return

        # Check if Ctrl or Shift is pressed for multi-selection
        modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.ControlModifier:
            # Ctrl: Toggle selection (add/remove from selection)
            if model in self.selected_objects:
                self.selected_objects.remove(model)
                model.Selected = False
                print(f"[Character Mapper Qt] Removed from selection: {model.Name}")
            else:
                self.selected_objects.append(model)
                model.Selected = True
                print(f"[Character Mapper Qt] Added to selection: {model.Name}")
        else:
            # No modifier: Clear selection and select only this object
            # Clear all selections first
            for obj in self.selected_objects:
                obj.Selected = False

            self.selected_objects = [model]
            model.Selected = True
            print(f"[Character Mapper Qt] Selected: {model.Name}")

        print(f"[Character Mapper Qt] Selection order: {[obj.Name for obj in self.selected_objects]}")

    def on_list_children_clicked(self):
        """List children of the selected object in the objects list"""
        if not self.selected_objects:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select an object from the Scene Objects list first."
            )
            return

        # Use the first selected object
        selected_object = self.selected_objects[0]

        print(f"[Character Mapper Qt] ===== LISTING CHILDREN OF {selected_object.Name} =====")

        # Get children of selected object
        children = get_children(selected_object, recursive=False)

        if not children:
            QMessageBox.information(
                self,
                "No Children",
                f"'{selected_object.Name}' has no children."
            )
            print(f"[Character Mapper Qt] No children found for {selected_object.Name}")
            return

        # Filter out cameras from children
        children = [child for child in children if not isinstance(child, FBCamera)]

        if not children:
            QMessageBox.information(
                self,
                "No Children",
                f"'{selected_object.Name}' has no non-camera children."
            )
            print(f"[Character Mapper Qt] No non-camera children found for {selected_object.Name}")
            return

        # Update the all_models list to only show children
        self.all_models = children
        self.all_models.sort(key=lambda x: x.Name)

        # Clear selections when listing children
        for obj in self.selected_objects:
            obj.Selected = False
        self.selected_objects = []

        # Clear search filter and apply
        if self.searchEdit:
            self.searchEdit.clear()
        self.apply_filter()

        print(f"[Character Mapper Qt] Showing {len(children)} children of {selected_object.Name}")
        print("[Character Mapper Qt] ===== LIST CHILDREN COMPLETE =====")

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

    def apply_tpose(self):
        """Apply T-pose by calculating proper arm rotations based on skeleton structure"""
        print("[Character Mapper Qt] Applying intelligent T-pose to arm bones...")

        # Process left and right arms
        for side in ["Left", "Right"]:
            shoulder = self.bone_mappings.get(f"{side}Shoulder")
            arm = self.bone_mappings.get(f"{side}Arm")
            forearm = self.bone_mappings.get(f"{side}ForeArm")

            if not arm or not forearm:
                print(f"[Character Mapper Qt] Skipping {side} arm - bones not mapped")
                continue

            # Get world positions
            arm_pos = arm.Translation
            forearm_pos = forearm.Translation

            # Calculate the vector from shoulder/arm to forearm (arm direction)
            arm_vec = FBVector3d(
                forearm_pos[0] - arm_pos[0],
                forearm_pos[1] - arm_pos[1],
                forearm_pos[2] - arm_pos[2]
            )

            # Normalize the vector
            length = (arm_vec[0]**2 + arm_vec[1]**2 + arm_vec[2]**2)**0.5
            if length > 0.001:
                arm_vec = FBVector3d(
                    arm_vec[0] / length,
                    arm_vec[1] / length,
                    arm_vec[2] / length
                )

            # Calculate the angle needed to make arm horizontal (parallel to ground)
            # We want the arm to point along +X (right) or -X (left) axis
            # Current Y component tells us how much it's angled up/down

            # Target: Y component should be ~0 (horizontal)
            # We'll rotate around Z axis to achieve this

            current_y = arm_vec[1]
            current_x = arm_vec[0]

            # Calculate angle from horizontal
            # atan2(y, x) gives us the angle in the XY plane
            import math
            current_angle = math.atan2(current_y, abs(current_x)) * (180.0 / math.pi)

            # For T-pose, we want arms horizontal (0 degrees from horizontal)
            # So we need to rotate by negative of current angle
            correction_angle = -current_angle

            print(f"[Character Mapper Qt] {side} arm current angle from horizontal: {current_angle:.1f}°")
            print(f"[Character Mapper Qt] {side} arm applying correction: {correction_angle:.1f}° on Z-axis")

            # Get current rotation
            current_rot = arm.Rotation

            # Apply correction on Z-axis for T-pose
            # For left arm: positive Z rotation lifts arm
            # For right arm: negative Z rotation lifts arm
            sign = 1 if side == "Left" else -1
            new_rotation = FBVector3d(
                current_rot[0],  # X - keep current
                current_rot[1],  # Y - keep current
                current_rot[2] + (correction_angle * sign)  # Z - apply correction
            )

            arm.Rotation = new_rotation
            print(f"[Character Mapper Qt] {side}Arm ({arm.Name}) rotation: {current_rot} -> {new_rotation}")

            # Straighten forearm (remove bend)
            if forearm:
                forearm.Rotation = FBVector3d(0, 0, 0)
                print(f"[Character Mapper Qt] {side}ForeArm ({forearm.Name}) straightened")

            # Zero shoulder rotation if present
            if shoulder:
                shoulder.Rotation = FBVector3d(0, 0, 0)
                print(f"[Character Mapper Qt] {side}Shoulder ({shoulder.Name}) zeroed")

    def check_tpose_vs_apose(self):
        """Check if arms are in T-pose or A-pose by checking shoulder rotation"""
        left_arm = self.bone_mappings.get("LeftArm")
        right_arm = self.bone_mappings.get("RightArm")

        if not left_arm or not right_arm:
            return True, "Cannot check pose - arm bones not mapped"

        # Get arm rotations (Y rotation indicates T-pose vs A-pose)
        # T-pose: arms roughly horizontal (Y rotation close to 0)
        # A-pose: arms angled down (Y rotation > 30 degrees typically)
        left_rot_y = abs(left_arm.Rotation[1])
        right_rot_y = abs(right_arm.Rotation[1])

        # Threshold: if Y rotation > 20 degrees, likely A-pose
        threshold = 20.0

        if left_rot_y > threshold or right_rot_y > threshold:
            return False, f"Arms appear to be in A-pose (LeftArm Y:{left_rot_y:.1f}°, RightArm Y:{right_rot_y:.1f}°)"

        return True, "Arms appear to be in T-pose"

    def on_create_character(self):
        """Create character from current mapping - follows MotionBuilder workflow"""
        print("[Character Mapper Qt] Creating character...")

        try:
            # Step 1: Check required bones
            required = ["Hips", "LeftUpLeg", "RightUpLeg", "Spine"]
            missing = [slot for slot in required if not self.bone_mappings.get(slot)]

            if missing:
                QMessageBox.warning(
                    self,
                    "Missing Required Bones",
                    f"Please map these required bones:\n{', '.join(missing)}\n\n"
                    f"Note: Only 'Spine' is required. Additional spine bones (Spine1-9) are optional."
                )
                return

            # Step 2: Check T-pose vs A-pose
            is_tpose, pose_msg = self.check_tpose_vs_apose()
            print(f"[Character Mapper Qt] Pose check: {pose_msg}")

            if not is_tpose:
                reply = QMessageBox.warning(
                    self,
                    "A-Pose Detected",
                    f"{pose_msg}\n\nCharacterization requires T-pose (arms horizontal).\n\n"
                    f"Options:\n"
                    f"• Yes - Apply automatic T-pose\n"
                    f"• No - Continue anyway (may fail)\n"
                    f"• Cancel - Go back and manually adjust",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )

                if reply == QMessageBox.Cancel:
                    return
                elif reply == QMessageBox.Yes:
                    print("[Character Mapper Qt] Applying T-pose...")
                    self.apply_tpose()

            # Step 3: Ask for character type (Biped/Quadruped)
            char_type_msg = QMessageBox.question(
                self,
                "Character Type",
                "Is this a Biped character?\n\n"
                "• Yes - Biped (human, humanoid)\n"
                "• No - Quadruped (animal with 4 legs)",
                QMessageBox.Yes | QMessageBox.No
            )

            is_biped = (char_type_msg == QMessageBox.Yes)

            # Step 4: Ask for IK/FK setup
            ik_fk_reply = QMessageBox.question(
                self,
                "Control Rig Setup",
                "Create Control Rig with IK/FK?\n\n"
                "• Yes - Full IK/FK rig (recommended for animation)\n"
                "• No - FK only (lighter, for retargeting)",
                QMessageBox.Yes | QMessageBox.No
            )

            create_ik_fk = (ik_fk_reply == QMessageBox.Yes)

            # Step 5: Get character name
            try:
                char_name = self.presetNameEdit.text() if self.presetNameEdit else "Character"
            except RuntimeError:
                char_name = "Character"

            # Step 6: Create character and map bones
            print(f"[Character Mapper Qt] Creating character: {char_name} (Biped: {is_biped}, IK/FK: {create_ik_fk})")
            self.character = FBCharacter(char_name)

            # Ensure characterization is off before mapping
            self.character.SetCharacterizeOn(False)

            # Map bones to character
            mapped_count = 0
            for slot_name, _ in CHARACTER_SLOTS:
                model = self.bone_mappings.get(slot_name)
                if model:
                    prop_list = self.character.PropertyList.Find(slot_name + "Link")
                    if prop_list:
                        prop_list.append(model)
                        mapped_count += 1
                        print(f"[Character Mapper Qt] Linked {slot_name} -> {model.Name}")
                    else:
                        print(f"[Character Mapper Qt WARNING] Could not find property {slot_name}Link")

            print(f"[Character Mapper Qt] Mapped {mapped_count} bones total")

            # Step 7: Characterize (with biped/quadruped flag)
            print(f"[Character Mapper Qt] Characterizing as {'Biped' if is_biped else 'Quadruped'}...")
            self.character.SetCharacterizeOn(is_biped)

            if self.character.GetCharacterizeError():
                error_msg = self.character.GetCharacterizeError()
                QMessageBox.critical(
                    self,
                    "Characterization Failed",
                    f"Characterization failed:\n{error_msg}\n\n"
                    f"Check:\n"
                    f"• Bone hierarchy (parent-child relationships)\n"
                    f"• Bone positions (joints should be at correct locations)\n"
                    f"• T-pose (arms horizontal, not angled down)"
                )
                print(f"[Character Mapper Qt ERROR] {error_msg}")
                return

            print("[Character Mapper Qt] Characterization successful!")

            # Step 8: Create Control Rig if requested
            if create_ik_fk:
                print("[Character Mapper Qt] Creating IK/FK Control Rig...")
                if self.character.CreateControlRig(True):  # True = IK/FK, False = FK only
                    print("[Character Mapper Qt] Control Rig created successfully!")
                else:
                    print("[Character Mapper Qt] Warning: Control Rig creation failed")

            # Success!
            QMessageBox.information(
                self,
                "Success",
                f"Character '{self.character.Name}' created successfully!\n\n"
                f"Type: {'Biped' if is_biped else 'Quadruped'}\n"
                f"Control Rig: {'IK/FK' if create_ik_fk else 'FK Only'}"
            )
            print(f"[Character Mapper Qt] Character creation complete: {self.character.Name}")

        except Exception as e:
            logger.error(f"Characterization failed: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create character:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def on_save_preset(self):
        """Save current mapping as a preset"""
        try:
            preset_name = self.presetNameEdit.text() if self.presetNameEdit else "Character"
        except RuntimeError:
            preset_name = "Character"

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
        preset_name = "Character"

        # Try to get the preset name from the text field
        try:
            # Re-find the widget if needed
            if not hasattr(self, 'presetNameEdit') or self.presetNameEdit is None:
                self.presetNameEdit = self.findChild(QtWidgets.QLineEdit, "presetNameEdit")
                print(f"[Character Mapper Qt] Re-finding presetNameEdit widget")

            if self.presetNameEdit:
                text = self.presetNameEdit.text()
                if text:
                    preset_name = text
                    print(f"[Character Mapper Qt] Load preset: got name '{preset_name}' from field")
                else:
                    print(f"[Character Mapper Qt] Load preset: field is empty, using default")
            else:
                print(f"[Character Mapper Qt] Load preset: presetNameEdit widget not found")
        except RuntimeError as e:
            print(f"[Character Mapper Qt] Load preset: RuntimeError accessing field: {e}")
        except Exception as e:
            print(f"[Character Mapper Qt] Load preset: Unexpected error: {e}")

        print(f"[Character Mapper Qt] Loading preset: {preset_name}")
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
        """Find a model by its LongName or Name"""
        # First try exact LongName match (for full paths)
        for model in self.all_models:
            if model.LongName == name:
                return model

        # Then try Name match (for simple names)
        for model in self.all_models:
            if model.Name == name:
                return model

        return None

    def on_export_preset(self):
        """Export preset to external file"""
        try:
            preset_name = self.presetNameEdit.text() if self.presetNameEdit else "Character"
        except RuntimeError:
            preset_name = "Character"

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

                # Copy to presets directory (skip if already there)
                dest_file = self.preset_path / f"{preset_name}.json"
                if import_path.resolve() != dest_file.resolve():
                    shutil.copy2(import_path, dest_file)
                else:
                    print(f"[Character Mapper Qt] File already in presets directory, skipping copy")

                # Update preset name field
                try:
                    if self.presetNameEdit:
                        self.presetNameEdit.setText(preset_name)
                except RuntimeError:
                    # Widget was deleted
                    print(f"[Character Mapper Qt] Warning: preset name field no longer accessible")
                    pass

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
