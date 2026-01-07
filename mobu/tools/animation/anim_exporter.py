"""
Animation Exporter Tool
Export multiple animation takes with custom frame ranges
"""

from pathlib import Path
import json

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import (
        QDialog, QMessageBox, QApplication, QVBoxLayout, QHBoxLayout,
        QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
        QLineEdit, QLabel, QFormLayout, QDialogButtonBox, QFileDialog,
        QComboBox, QStyledItemDelegate
    )
    from PySide2.QtCore import Qt
except ImportError:
    try:
        from PySide import QtGui as QtWidgets
        from PySide import QtCore
        from PySide.QtGui import (
            QDialog, QMessageBox, QApplication, QVBoxLayout, QHBoxLayout,
            QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
            QLineEdit, QLabel, QFormLayout, QDialogButtonBox, QFileDialog,
            QComboBox, QStyledItemDelegate
        )
        from PySide.QtCore import Qt
    except ImportError:
        print("[Anim Exporter] ERROR: Neither PySide2 nor PySide found")
        QtWidgets = None

from pyfbsdk import (
    FBMessageBox, FBSystem, FBNote, FBPlayerControl, FBPropertyString, FBPropertyType
)
from core.logger import logger

TOOL_NAME = "Anim Exporter"

# Global reference to prevent garbage collection
_anim_exporter_dialog = None
_q_application_instance = None


def get_mobu_main_window():
    """Get MotionBuilder's main window to use as parent"""
    try:
        app = QApplication.instance()
        if app:
            # Try to find MotionBuilder main window
            for widget in app.topLevelWidgets():
                if widget.objectName() == "MotionBuilder" or "MotionBuilder" in widget.windowTitle():
                    print(f"[Anim Exporter] Found parent window: {widget.windowTitle()}")
                    return widget
            # Fallback: return first top-level widget
            widgets = app.topLevelWidgets()
            if widgets:
                print(f"[Anim Exporter] Using first top-level widget as parent: {widgets[0].windowTitle()}")
                return widgets[0]
        return None
    except Exception as e:
        print(f"[Anim Exporter] Error finding parent: {str(e)}")
        return None


def execute(control, event):
    """Execute the Animation Exporter tool"""
    global _anim_exporter_dialog
    global _q_application_instance

    if _anim_exporter_dialog is not None:
        print("[Anim Exporter] Bringing existing dialog to front")
        _anim_exporter_dialog.show()
        _anim_exporter_dialog.raise_()
        _anim_exporter_dialog.activateWindow()
        return

    print("[Anim Exporter] Creating new dialog")

    # Store QApplication instance globally to prevent premature garbage collection
    _q_application_instance = QApplication.instance()

    parent = get_mobu_main_window()
    _anim_exporter_dialog = AnimExporterDialog(parent)
    _anim_exporter_dialog.show()


class BrowsePathDelegate(QStyledItemDelegate):
    """Custom delegate for Path column with browse button"""

    def paint(self, painter, option, index):
        """Paint the cell with a browse button indicator"""
        # Draw the default cell
        super(BrowsePathDelegate, self).paint(painter, option, index)

        # Draw [...] button on the right side
        button_rect = option.rect.adjusted(option.rect.width() - 35, 2, -2, -2)

        painter.save()
        painter.setPen(painter.pen().color())
        painter.drawRect(button_rect)

        # Draw the text "[...]"
        painter.drawText(button_rect, Qt.AlignCenter, "[...]")
        painter.restore()

    def createEditor(self, parent, option, index):
        """Create a widget with line edit and browse button"""
        container = QtWidgets.QWidget(parent)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit(container)
        browse_btn = QPushButton("...", container)
        browse_btn.setMaximumWidth(30)

        layout.addWidget(line_edit)
        layout.addWidget(browse_btn)

        # Store reference to line edit for later
        container.line_edit = line_edit

        # Connect browse button
        browse_btn.clicked.connect(lambda: self.browse_path(line_edit))

        return container

    def setEditorData(self, editor, index):
        """Set the current value in the editor"""
        value = index.model().data(index, Qt.EditRole)
        if hasattr(editor, 'line_edit'):
            editor.line_edit.setText(str(value) if value else "")

    def setModelData(self, editor, model, index):
        """Get the value from the editor and set it in the model"""
        if hasattr(editor, 'line_edit'):
            model.setData(index, editor.line_edit.text(), Qt.EditRole)

    def browse_path(self, line_edit):
        """Open file browser"""
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Select Export Path",
            line_edit.text() or "",
            "FBX Files (*.fbx);;All Files (*.*)"
        )
        if file_path:
            line_edit.setText(file_path)


class TakeDelegate(QStyledItemDelegate):
    """Custom delegate for Take column with combobox"""

    def __init__(self, parent=None):
        super(TakeDelegate, self).__init__(parent)
        self.parent_dialog = parent

    def paint(self, painter, option, index):
        """Paint the cell with a dropdown arrow indicator"""
        # Draw the default cell
        super(TakeDelegate, self).paint(painter, option, index)

        # Draw dropdown arrow on the right side
        arrow_rect = option.rect.adjusted(option.rect.width() - 20, 0, -2, 0)

        # Create triangle points for dropdown arrow
        center_y = arrow_rect.center().y()
        center_x = arrow_rect.center().x()

        from PySide2.QtGui import QPolygon
        from PySide2.QtCore import QPoint

        arrow = QPolygon([
            QPoint(center_x - 4, center_y - 2),
            QPoint(center_x + 4, center_y - 2),
            QPoint(center_x, center_y + 3)
        ])

        painter.save()
        painter.setBrush(painter.pen().color())
        painter.drawPolygon(arrow)
        painter.restore()

    def createEditor(self, parent, option, index):
        """Create a combobox with scene takes"""
        combo = QComboBox(parent)
        combo.setEditable(True)

        # Add empty option
        combo.addItem("")

        # Get takes from scene
        takes = self.get_scene_takes()
        for take in takes:
            combo.addItem(take)

        return combo

    def setEditorData(self, editor, index):
        """Set the current value in the combobox"""
        value = index.model().data(index, Qt.EditRole)
        if value:
            idx = editor.findText(str(value))
            if idx >= 0:
                editor.setCurrentIndex(idx)
            else:
                editor.setEditText(str(value))

    def setModelData(self, editor, model, index):
        """Get the value from combobox and set it in the model"""
        model.setData(index, editor.currentText(), Qt.EditRole)

    def get_scene_takes(self):
        """Get list of take names from the scene"""
        from pyfbsdk import FBSystem
        takes = []

        try:
            scene = FBSystem().Scene
            for i in range(scene.Takes.GetCount()):
                take = scene.Takes[i]
                takes.append(take.Name)
        except Exception as e:
            print(f"[Anim Exporter] Error getting takes: {str(e)}")

        return takes


class NamespaceDelegate(QStyledItemDelegate):
    """Custom delegate for Namespace column with combobox"""

    def __init__(self, parent=None):
        super(NamespaceDelegate, self).__init__(parent)
        self.parent_dialog = parent

    def paint(self, painter, option, index):
        """Paint the cell with a dropdown arrow indicator"""
        # Draw the default cell
        super(NamespaceDelegate, self).paint(painter, option, index)

        # Draw dropdown arrow on the right side
        arrow_rect = option.rect.adjusted(option.rect.width() - 20, 0, -2, 0)

        # Create triangle points for dropdown arrow
        center_y = arrow_rect.center().y()
        center_x = arrow_rect.center().x()

        from PySide2.QtGui import QPolygon
        from PySide2.QtCore import QPoint

        arrow = QPolygon([
            QPoint(center_x - 4, center_y - 2),
            QPoint(center_x + 4, center_y - 2),
            QPoint(center_x, center_y + 3)
        ])

        painter.save()
        painter.setBrush(painter.pen().color())
        painter.drawPolygon(arrow)
        painter.restore()

    def createEditor(self, parent, option, index):
        """Create a combobox with scene characters"""
        combo = QComboBox(parent)
        combo.setEditable(True)

        # Add empty option
        combo.addItem("")

        # Get characters from scene
        characters = self.get_scene_characters()
        for char in characters:
            combo.addItem(char)

        return combo

    def setEditorData(self, editor, index):
        """Set the current value in the combobox"""
        value = index.model().data(index, Qt.EditRole)
        if value:
            idx = editor.findText(str(value))
            if idx >= 0:
                editor.setCurrentIndex(idx)
            else:
                editor.setEditText(str(value))

    def setModelData(self, editor, model, index):
        """Get the value from combobox and set it in the model"""
        model.setData(index, editor.currentText(), Qt.EditRole)

    def get_scene_characters(self):
        """Get list of character names from the scene"""
        from pyfbsdk import FBCharacter
        characters = []

        try:
            scene = FBSystem().Scene
            for comp in scene.Components:
                if isinstance(comp, FBCharacter):
                    characters.append(comp.Name)
        except Exception as e:
            print(f"[Anim Exporter] Error getting characters: {str(e)}")

        return sorted(characters)


class AddAnimationDialog(QDialog):
    """Dialog for adding a new animation entry"""

    def __init__(self, parent=None, default_start=0, default_end=100):
        super(AddAnimationDialog, self).__init__(parent)

        self.setWindowTitle("Add Animation")
        self.setFixedSize(650, 180)  # Fixed size - no resizing

        # Store the input values
        self.animation_data = None

        # Create main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Top row - Animation Name and Frame Range
        top_row = QHBoxLayout()

        top_row.addWidget(QLabel("Animation Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Idle, Walk, Run")
        top_row.addWidget(self.name_input, stretch=1)

        top_row.addSpacing(20)

        top_row.addWidget(QLabel("Start:"))
        self.start_frame_input = QLineEdit()
        self.start_frame_input.setText(str(default_start))
        self.start_frame_input.setAlignment(Qt.AlignCenter)
        self.start_frame_input.setMaximumWidth(60)
        top_row.addWidget(self.start_frame_input)

        top_row.addWidget(QLabel("End:"))
        self.end_frame_input = QLineEdit()
        self.end_frame_input.setText(str(default_end))
        self.end_frame_input.setAlignment(Qt.AlignCenter)
        self.end_frame_input.setMaximumWidth(60)
        top_row.addWidget(self.end_frame_input)

        layout.addLayout(top_row)

        # Middle row - Take and Namespace
        middle_row = QHBoxLayout()

        middle_row.addWidget(QLabel("Take:"))
        self.take_combo = QComboBox()
        self.take_combo.setEditable(False)  # Not editable - dropdown only
        self.take_combo.addItem("")  # Empty default
        self.take_combo.setMinimumWidth(150)

        # Populate with scene takes
        takes = self.get_scene_takes()
        for take in takes:
            self.take_combo.addItem(take)

        middle_row.addWidget(self.take_combo)

        middle_row.addSpacing(20)

        middle_row.addWidget(QLabel("Namespace:"))
        self.namespace_combo = QComboBox()
        self.namespace_combo.setEditable(False)  # Not editable - dropdown only
        self.namespace_combo.addItem("")  # Empty default
        self.namespace_combo.setMinimumWidth(150)

        # Populate with scene characters
        characters = self.get_scene_characters()
        for char in characters:
            self.namespace_combo.addItem(char)

        middle_row.addWidget(self.namespace_combo)
        middle_row.addStretch()

        layout.addLayout(middle_row)

        # Bottom row - Path
        bottom_row = QHBoxLayout()

        bottom_row.addWidget(QLabel("Path:"))
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Export path (optional)")
        bottom_row.addWidget(self.path_input, stretch=1)

        self.browse_btn = QPushButton("[...]")
        self.browse_btn.setObjectName("browseBtn")
        self.browse_btn.setMaximumWidth(40)
        self.browse_btn.clicked.connect(self.on_browse_path)
        bottom_row.addWidget(self.browse_btn)

        layout.addLayout(bottom_row)

        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)

        # Rename OK button to "Add"
        add_button = button_box.button(QDialogButtonBox.Ok)
        add_button.setText("Add")

        layout.addWidget(button_box)

        # Set focus to name input
        self.name_input.setFocus()

    def get_scene_takes(self):
        """Get list of take names from the scene"""
        from pyfbsdk import FBSystem
        takes = []

        try:
            scene = FBSystem().Scene
            for i in range(scene.Takes.GetCount()):
                take = scene.Takes[i]
                takes.append(take.Name)
        except Exception as e:
            print(f"[Anim Exporter] Error getting takes: {str(e)}")

        return takes

    def get_scene_characters(self):
        """Get list of character names from the scene"""
        from pyfbsdk import FBCharacter
        characters = []

        try:
            scene = FBSystem().Scene
            for comp in scene.Components:
                if isinstance(comp, FBCharacter):
                    characters.append(comp.Name)
        except Exception as e:
            print(f"[Anim Exporter] Error getting characters: {str(e)}")

        return sorted(characters)

    def on_browse_path(self):
        """Open file browser to select export path"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Export Path",
            "",
            "FBX Files (*.fbx);;All Files (*.*)"
        )

        if file_path:
            self.path_input.setText(file_path)

    def on_accept(self):
        """Validate and accept the dialog"""
        # Validate animation name
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Animation Name is required!")
            self.name_input.setFocus()
            return

        # Validate frame numbers
        try:
            start_frame = int(self.start_frame_input.text())
            end_frame = int(self.end_frame_input.text())

            if end_frame <= start_frame:
                QMessageBox.warning(self, "Validation Error", "End Frame must be greater than Start Frame!")
                self.end_frame_input.setFocus()
                return

        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Start Frame and End Frame must be valid numbers!")
            return

        # Store the data
        self.animation_data = {
            'name': self.name_input.text().strip(),
            'take': self.take_combo.currentText().strip(),
            'start_frame': start_frame,
            'end_frame': end_frame,
            'namespace': self.namespace_combo.currentText().strip(),
            'path': self.path_input.text().strip()
        }

        self.accept()


class AnimExporterDialog(QDialog):
    """Animation Exporter dialog"""

    def __init__(self, parent=None):
        super(AnimExporterDialog, self).__init__(parent)

        # Set window flags - don't use Qt.Window to allow proper parenting
        if parent:
            self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
            print(f"[Anim Exporter] Dialog created with parent: {parent.windowTitle()}")
        else:
            self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
            print("[Anim Exporter] WARNING: No parent found, creating as standalone window")

        self.note_object = None
        self._is_closing = False
        self.selected_rows = []  # Track selected rows for Export Selected

        # Setup UI
        self.setup_ui()

        # Create or find note file in scene
        self.setup_note_file()

        # Load existing data from note
        self.load_data_from_note()

    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Anim Exporter")
        self.resize(800, 500)
        self.setMinimumSize(800, 400)

        # Main layout
        main_layout = QHBoxLayout(self)

        # Left side - Table in GroupBox
        table_layout = QVBoxLayout()

        # === Animations GroupBox ===
        animations_group = QtWidgets.QGroupBox("Animations")
        animations_group_layout = QVBoxLayout()

        # Create table widget with specified columns
        self.animation_table = QTableWidget()
        self.animation_table.setColumnCount(6)
        self.animation_table.setHorizontalHeaderLabels([
            "Animation Name",
            "Take",
            "Start Frame",
            "End Frame",
            "Namespace",
            "Path"
        ])

        # Configure table
        self.animation_table.horizontalHeader().setStretchLastSection(True)
        self.animation_table.horizontalHeader().setHighlightSections(False)  # Prevent header highlighting
        self.animation_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.animation_table.setSelectionMode(QTableWidget.ExtendedSelection)  # Single by default, multi with Shift/Ctrl
        self.animation_table.setAlternatingRowColors(True)

        # Set column widths
        self.animation_table.setColumnWidth(0, 150)  # Animation Name
        self.animation_table.setColumnWidth(1, 120)  # Take
        self.animation_table.setColumnWidth(2, 80)   # Start Frame
        self.animation_table.setColumnWidth(3, 80)   # End Frame
        self.animation_table.setColumnWidth(4, 100)  # Namespace
        # Path column will stretch

        # Set custom delegates for special columns
        # Take column - dropdown with scene takes
        self.take_delegate = TakeDelegate(self)
        self.animation_table.setItemDelegateForColumn(1, self.take_delegate)

        # Namespace column - dropdown with characters
        self.namespace_delegate = NamespaceDelegate(self)
        self.animation_table.setItemDelegateForColumn(4, self.namespace_delegate)

        # Path column - browse button
        self.path_delegate = BrowsePathDelegate()
        self.animation_table.setItemDelegateForColumn(5, self.path_delegate)

        # Connect table signals
        self.animation_table.itemChanged.connect(self.on_table_data_changed)
        self.animation_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.animation_table.clicked.connect(self.on_cell_clicked)

        animations_group_layout.addWidget(self.animation_table)
        animations_group.setLayout(animations_group_layout)
        table_layout.addWidget(animations_group)

        # Right side - Buttons with sections
        button_layout = QVBoxLayout()

        # === Animation GroupBox ===
        anim_group = QtWidgets.QGroupBox("Animation")
        anim_group_layout = QVBoxLayout()

        # Add Animation button
        self.add_animation_btn = QPushButton("Add Animation")
        self.add_animation_btn.setMinimumWidth(120)
        self.add_animation_btn.clicked.connect(self.on_add_animation)
        anim_group_layout.addWidget(self.add_animation_btn)

        # Delete Selected button
        self.delete_selected_btn = QPushButton("Delete Selected")
        self.delete_selected_btn.setMinimumWidth(120)
        self.delete_selected_btn.clicked.connect(self.on_delete_selected)
        anim_group_layout.addWidget(self.delete_selected_btn)

        # Delete All button
        self.delete_all_btn = QPushButton("Delete All")
        self.delete_all_btn.setMinimumWidth(120)
        self.delete_all_btn.clicked.connect(self.on_delete_all)
        anim_group_layout.addWidget(self.delete_all_btn)

        anim_group.setLayout(anim_group_layout)
        button_layout.addWidget(anim_group)

        # Spacer to push export section to bottom
        button_layout.addStretch()

        # === Export GroupBox ===
        export_group = QtWidgets.QGroupBox("Export")
        export_group_layout = QVBoxLayout()

        # Export Selected button
        self.export_selected_btn = QPushButton("Export Selected")
        self.export_selected_btn.setMinimumWidth(120)
        self.export_selected_btn.clicked.connect(self.on_export_selected)
        export_group_layout.addWidget(self.export_selected_btn)

        # Export All button
        self.export_all_btn = QPushButton("Export All")
        self.export_all_btn.setMinimumWidth(120)
        self.export_all_btn.clicked.connect(self.on_export_all)
        export_group_layout.addWidget(self.export_all_btn)

        export_group.setLayout(export_group_layout)
        button_layout.addWidget(export_group)

        # Add layouts to main layout
        main_layout.addLayout(table_layout, stretch=1)
        main_layout.addLayout(button_layout)

        print("[Anim Exporter] UI setup complete")

    def setup_note_file(self):
        """Create or find note file in MotionBuilder scene"""
        try:
            scene = FBSystem().Scene
            note_name = "AnimNoteData"

            # Search for existing note
            for note in scene.Notes:
                if note.Name == note_name:
                    self.note_object = note
                    print(f"[Anim Exporter] Found existing note: {note_name}")
                    self._setup_custom_property()
                    return

            # Create new note if not found
            self.note_object = FBNote(note_name)
            self.note_object.Comments = "Animation Exporter data storage"
            print(f"[Anim Exporter] Created new note: {note_name}")

            # Setup custom property
            self._setup_custom_property()

        except Exception as e:
            print(f"[Anim Exporter] Error creating note: {str(e)}")
            logger.error(f"Failed to create note: {str(e)}")
            QMessageBox.warning(
                self,
                "Warning",
                f"Could not create note file in scene:\n{str(e)}"
            )

    def _setup_custom_property(self):
        """Setup custom property on the note for storing animation data"""
        # No longer needed - we'll create individual properties dynamically
        print("[Anim Exporter] Custom properties will be created per animation entry")
        pass

    def load_data_from_note(self):
        """Load animation data from individual custom properties (Anim00, Anim01, etc.)"""
        if not self.note_object:
            print("[Anim Exporter] No note object available")
            return

        try:
            # Find all animation properties (Anim00, Anim01, etc.)
            animation_props = []
            prop_list = self.note_object.PropertyList

            # Scan for anim00, anim01, anim02... properties (lowercase)
            index = 0
            while True:
                prop_name = f"anim{index:02d}"
                prop = prop_list.Find(prop_name)

                if not prop:
                    # No more animation properties found
                    break

                animation_props.append((prop_name, prop))
                index += 1

            if not animation_props:
                print("[Anim Exporter] No animation data found in note")
                return

            print(f"[Anim Exporter] Found {len(animation_props)} animation(s) in note")

            # Populate table (disable change tracking temporarily)
            self.animation_table.itemChanged.disconnect(self.on_table_data_changed)

            for prop_name, prop in animation_props:
                try:
                    # Parse JSON data from property
                    data_str = prop.Data
                    if data_str:
                        anim_data = json.loads(data_str)
                        self._add_row_to_table(
                            anim_data.get('name', ''),
                            anim_data.get('take', ''),
                            anim_data.get('start_frame', 0),
                            anim_data.get('end_frame', 100),
                            anim_data.get('namespace', ''),
                            anim_data.get('path', '')
                        )
                except json.JSONDecodeError as e:
                    print(f"[Anim Exporter] Error parsing {prop_name}: {str(e)}")
                except Exception as e:
                    print(f"[Anim Exporter] Error loading {prop_name}: {str(e)}")

            # Re-enable change tracking
            self.animation_table.itemChanged.connect(self.on_table_data_changed)

        except Exception as e:
            print(f"[Anim Exporter] Error loading data from note: {str(e)}")
            logger.error(f"Failed to load data from note: {str(e)}")

    def save_data_to_note(self):
        """Save animation data to individual custom properties (Anim00, Anim01, etc.)"""
        if not self.note_object:
            print("[Anim Exporter] No note object available")
            return

        try:
            prop_list = self.note_object.PropertyList

            # First, check existing anim## properties
            index = 0
            while True:
                prop_name = f"anim{index:02d}"
                prop = prop_list.Find(prop_name)
                if not prop:
                    break
                # Note: MotionBuilder doesn't support removing properties easily
                # So we'll just overwrite them
                index += 1

            # Now create/update properties for current table data
            row_count = self.animation_table.rowCount()

            for row in range(row_count):
                prop_name = f"anim{row:02d}"

                # Collect animation data for this row
                anim_data = {
                    'name': self.animation_table.item(row, 0).text(),
                    'take': self.animation_table.item(row, 1).text(),
                    'start_frame': int(self.animation_table.item(row, 2).text()),
                    'end_frame': int(self.animation_table.item(row, 3).text()),
                    'namespace': self.animation_table.item(row, 4).text(),
                    'path': self.animation_table.item(row, 5).text()
                }

                # Convert to JSON string
                data_str = json.dumps(anim_data)

                # Find or create the property
                prop = prop_list.Find(prop_name)
                if not prop:
                    prop = self.note_object.PropertyCreate(prop_name, FBPropertyString, "String", True, True)
                    print(f"[Anim Exporter] Created property: {prop_name}")

                # Save the data
                prop.Data = data_str

            # Clear any extra properties beyond current row count
            # (overwrite with empty string)
            extra_index = row_count
            while True:
                prop_name = f"anim{extra_index:02d}"
                prop = prop_list.Find(prop_name)
                if not prop:
                    break
                prop.Data = ""  # Clear the data
                extra_index += 1

            print(f"[Anim Exporter] Saved {row_count} animation(s) to note as individual properties")

        except Exception as e:
            print(f"[Anim Exporter] Error saving data: {str(e)}")
            logger.error(f"Failed to save data to note: {str(e)}")

    def _create_animation_property(self, row_index, anim_data):
        """
        Create/update a custom property for a specific animation

        Args:
            row_index: The row number in the table (0-based)
            anim_data: Dictionary with animation data
        """
        if not self.note_object:
            print("[Anim Exporter] No note object available")
            return

        try:
            # 1. Get AnimNoteData note object (already have it as self.note_object)
            print(f"[Anim Exporter] Working with note: {self.note_object.Name}")
            prop_list = self.note_object.PropertyList

            # 2. Create property name (anim00, anim01, etc.) - lowercase
            prop_name = f"anim{row_index:02d}"
            print(f"[Anim Exporter] Creating/updating property: {prop_name}")

            # 3. Convert data to JSON string first
            data_str = json.dumps(anim_data)
            print(f"[Anim Exporter] Data to save: {data_str}")

            # 4. Find or create the custom property
            prop = prop_list.Find(prop_name)

            if not prop:
                # Create new property using MotionBuilder SDK pattern
                print(f"[Anim Exporter] Property '{prop_name}' not found, creating new...")

                # PropertyCreate(pName, pType, pDataType, pAnimatable, pIsUser, pReferenceSource)
                prop = self.note_object.PropertyCreate(
                    prop_name,                      # pName: "Anim00", "Anim01", etc.
                    FBPropertyType.kFBPT_charptr,   # pType: String type
                    "String",                       # pDataType: MotionBuilder animation node type
                    False,                          # pAnimatable: Not animatable
                    True,                           # pIsUser: User/custom property (shows in UI)
                    None                            # pReferenceSource: No reference
                )

                if prop:
                    print(f"[Anim Exporter] Successfully created custom property: {prop_name}")
                else:
                    print(f"[Anim Exporter] ERROR: Failed to create property {prop_name}")
                    return
            else:
                print(f"[Anim Exporter] Found existing property: {prop_name}")

            # 5. Set Custom Property.Data to JSON entry
            if prop:
                prop.Data = data_str
                print(f"[Anim Exporter] Set data for {prop_name}")

                # Verify the data was set
                verify_data = prop.Data
                print(f"[Anim Exporter] Verified data: {verify_data}")
            else:
                print(f"[Anim Exporter] ERROR: Property object is None")

        except Exception as e:
            print(f"[Anim Exporter] ERROR creating animation property: {str(e)}")
            import traceback
            traceback.print_exc()
            logger.error(f"Failed to create animation property: {str(e)}")

    def on_table_data_changed(self, item):
        """Handle table data changes and update the corresponding property"""
        row = item.row()
        print(f"[Anim Exporter] Table data changed at row {row}, column {item.column()}")

        # Collect data for this specific row
        try:
            anim_data = {
                'name': self.animation_table.item(row, 0).text(),
                'take': self.animation_table.item(row, 1).text(),
                'start_frame': int(self.animation_table.item(row, 2).text()),
                'end_frame': int(self.animation_table.item(row, 3).text()),
                'namespace': self.animation_table.item(row, 4).text(),
                'path': self.animation_table.item(row, 5).text()
            }

            # Update the property for this specific row
            self._create_animation_property(row, anim_data)

        except Exception as e:
            print(f"[Anim Exporter] Error updating property for row {row}: {str(e)}")

    def _add_row_to_table(self, name, take, start_frame, end_frame, namespace, path):
        """Add a row to the table with the given data"""
        row_count = self.animation_table.rowCount()
        self.animation_table.insertRow(row_count)

        # Column 0: Animation Name (left-aligned)
        name_item = QTableWidgetItem(name)
        self.animation_table.setItem(row_count, 0, name_item)

        # Column 1: Take (centered)
        take_item = QTableWidgetItem(take)
        take_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.animation_table.setItem(row_count, 1, take_item)

        # Column 2: Start Frame (centered)
        start_item = QTableWidgetItem(str(start_frame))
        start_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.animation_table.setItem(row_count, 2, start_item)

        # Column 3: End Frame (centered)
        end_item = QTableWidgetItem(str(end_frame))
        end_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.animation_table.setItem(row_count, 3, end_item)

        # Column 4: Namespace (centered)
        namespace_item = QTableWidgetItem(namespace)
        namespace_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.animation_table.setItem(row_count, 4, namespace_item)

        # Column 5: Path (centered)
        path_item = QTableWidgetItem(path)
        path_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.animation_table.setItem(row_count, 5, path_item)

    def on_add_animation(self):
        """Handle Add Animation button click - show dialog"""
        # Get current timeline range as defaults
        player = FBPlayerControl()
        start_frame = int(player.LoopStart.GetFrame())
        end_frame = int(player.LoopStop.GetFrame())

        # Show the add animation dialog
        dialog = AddAnimationDialog(self, start_frame, end_frame)

        if dialog.exec_() == QDialog.Accepted:
            # Get the data from the dialog
            data = dialog.animation_data

            if data:
                # Disable change tracking temporarily to avoid multiple saves
                self.animation_table.itemChanged.disconnect(self.on_table_data_changed)

                # Add row to table
                self._add_row_to_table(
                    data['name'],
                    data['take'],
                    data['start_frame'],
                    data['end_frame'],
                    data['namespace'],
                    data['path']
                )

                # Re-enable change tracking
                self.animation_table.itemChanged.connect(self.on_table_data_changed)

                # Create custom property immediately for this new animation
                self._create_animation_property(
                    self.animation_table.rowCount() - 1,  # Last row added
                    data
                )

                print(f"[Anim Exporter] Added animation: {data['name']}")

    def on_cell_clicked(self, index):
        """Handle single click on cell - open editor for special columns"""
        column = index.column()

        # Columns with custom delegates that should open on single click
        # Column 1: Take (combobox)
        # Column 4: Namespace (combobox)
        # Column 5: Path (browse button)
        if column in [1, 4, 5]:
            self.animation_table.edit(index)

    def on_selection_changed(self):
        """Handle table selection changes - track selected rows"""
        selected_items = self.animation_table.selectedItems()
        self.selected_rows = []

        # Get unique row indices from selected items
        for item in selected_items:
            row = item.row()
            if row not in self.selected_rows:
                self.selected_rows.append(row)

        self.selected_rows.sort()
        print(f"[Anim Exporter] Selected rows: {self.selected_rows}")

    def on_delete_selected(self):
        """Delete selected rows from the table"""
        if not self.selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select rows to delete")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete {len(self.selected_rows)} selected animation(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Disable change tracking
            self.animation_table.itemChanged.disconnect(self.on_table_data_changed)

            # Remove rows in reverse order to maintain indices
            for row in reversed(self.selected_rows):
                self.animation_table.removeRow(row)

            # Re-enable change tracking
            self.animation_table.itemChanged.connect(self.on_table_data_changed)

            # Renumber remaining rows
            self._renumber_rows()

            # Save to note after deletion
            self.save_data_to_note()

            self.selected_rows = []
            print(f"[Anim Exporter] Deleted selected animations")

    def on_delete_all(self):
        """Delete all rows from the table"""
        if self.animation_table.rowCount() == 0:
            QMessageBox.information(self, "No Data", "No animations to delete")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete All",
            f"Delete all {self.animation_table.rowCount()} animation(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Disable change tracking
            self.animation_table.itemChanged.disconnect(self.on_table_data_changed)

            # Clear all rows
            self.animation_table.setRowCount(0)

            # Re-enable change tracking
            self.animation_table.itemChanged.connect(self.on_table_data_changed)

            # Save to note (will clear all properties)
            self.save_data_to_note()

            self.selected_rows = []
            print(f"[Anim Exporter] Deleted all animations")

    def _renumber_rows(self):
        """No longer needed - removed # column"""
        pass

    def on_export_selected(self):
        """Export selected animations"""
        if not self.selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select animations to export")
            return

        print(f"[Anim Exporter] Exporting {len(self.selected_rows)} selected animation(s)...")

        for row in self.selected_rows:
            self._export_animation(row)

        QMessageBox.information(
            self,
            "Export Complete",
            f"Exported {len(self.selected_rows)} animation(s)"
        )

    def on_export_all(self):
        """Export all animations"""
        row_count = self.animation_table.rowCount()

        if row_count == 0:
            QMessageBox.information(self, "No Data", "No animations to export")
            return

        print(f"[Anim Exporter] Exporting all {row_count} animation(s)...")

        for row in range(row_count):
            self._export_animation(row)

        QMessageBox.information(
            self,
            "Export Complete",
            f"Exported {row_count} animation(s)"
        )

    def _export_animation(self, row):
        """
        Export a single animation

        Args:
            row: Row index in the table
        """
        try:
            # Get animation data from table
            anim_name = self.animation_table.item(row, 0).text()
            take_name = self.animation_table.item(row, 1).text()
            start_frame = int(self.animation_table.item(row, 2).text())
            end_frame = int(self.animation_table.item(row, 3).text())
            namespace = self.animation_table.item(row, 4).text()
            export_path = self.animation_table.item(row, 5).text()

            print(f"[Anim Exporter] Exporting '{anim_name}': take '{take_name}', frames {start_frame}-{end_frame}, namespace: '{namespace}', path: '{export_path}'")

            # TODO: Implement actual FBX export logic here
            # For now, just log the export
            # You would use FBFbxOptions and FBApplication().FileSave() here

            if not export_path:
                print(f"[Anim Exporter] WARNING: No export path specified for '{anim_name}'")
                return

            # Placeholder for actual export implementation
            print(f"[Anim Exporter] Would export '{anim_name}' to '{export_path}'")

        except Exception as e:
            print(f"[Anim Exporter] Error exporting row {row}: {str(e)}")
            import traceback
            traceback.print_exc()

    def closeEvent(self, event):
        """Handle dialog close event"""
        global _anim_exporter_dialog
        global _q_application_instance

        self._is_closing = True
        _anim_exporter_dialog = None
        _q_application_instance = None
        event.accept()
