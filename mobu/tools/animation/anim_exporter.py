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
        QLineEdit, QLabel, QFormLayout, QDialogButtonBox, QFileDialog
    )
    from PySide2.QtCore import Qt
except ImportError:
    try:
        from PySide import QtGui as QtWidgets
        from PySide import QtCore
        from PySide.QtGui import (
            QDialog, QMessageBox, QApplication, QVBoxLayout, QHBoxLayout,
            QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
            QLineEdit, QLabel, QFormLayout, QDialogButtonBox, QFileDialog
        )
        from PySide.QtCore import Qt
    except ImportError:
        print("[Anim Exporter] ERROR: Neither PySide2 nor PySide found")
        QtWidgets = None

from pyfbsdk import (
    FBMessageBox, FBSystem, FBNote, FBPlayerControl, FBPropertyString
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


class AddAnimationDialog(QDialog):
    """Dialog for adding a new animation entry"""

    def __init__(self, parent=None, default_start=0, default_end=100):
        super(AddAnimationDialog, self).__init__(parent)

        self.setWindowTitle("Add Animation")
        self.setMinimumWidth(400)

        # Store the input values
        self.animation_data = None

        # Create form layout
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Create input fields
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Idle, Walk, Run")

        self.start_frame_input = QLineEdit()
        self.start_frame_input.setText(str(default_start))
        self.start_frame_input.setAlignment(Qt.AlignCenter)

        self.end_frame_input = QLineEdit()
        self.end_frame_input.setText(str(default_end))
        self.end_frame_input.setAlignment(Qt.AlignCenter)

        self.namespace_input = QLineEdit()
        self.namespace_input.setPlaceholderText("Optional")

        # Path input with browse button
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Export path (optional)")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.on_browse_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_btn)

        # Add fields to form
        form_layout.addRow("Animation Name:", self.name_input)
        form_layout.addRow("Start Frame:", self.start_frame_input)
        form_layout.addRow("End Frame:", self.end_frame_input)
        form_layout.addRow("Namespace:", self.namespace_input)
        form_layout.addRow("Path:", path_layout)

        layout.addLayout(form_layout)

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
            'start_frame': start_frame,
            'end_frame': end_frame,
            'namespace': self.namespace_input.text().strip(),
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
        self.data_property = None
        self._is_closing = False

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

        # Left side - Table
        table_layout = QVBoxLayout()

        # Create table widget with specified columns
        self.animation_table = QTableWidget()
        self.animation_table.setColumnCount(6)
        self.animation_table.setHorizontalHeaderLabels([
            "#",
            "Animation Name",
            "Start Frame",
            "End Frame",
            "Namespace",
            "Path"
        ])

        # Configure table
        self.animation_table.horizontalHeader().setStretchLastSection(True)
        self.animation_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.animation_table.setAlternatingRowColors(True)

        # Set column widths
        self.animation_table.setColumnWidth(0, 40)   # #
        self.animation_table.setColumnWidth(1, 150)  # Animation Name
        self.animation_table.setColumnWidth(2, 80)   # Start Frame
        self.animation_table.setColumnWidth(3, 80)   # End Frame
        self.animation_table.setColumnWidth(4, 100)  # Namespace
        # Path column will stretch

        # Connect table data change signal to save function
        self.animation_table.itemChanged.connect(self.on_table_data_changed)

        table_layout.addWidget(self.animation_table)

        # Right side - Buttons
        button_layout = QVBoxLayout()

        # Add Animation button
        self.add_animation_btn = QPushButton("Add Animation")
        self.add_animation_btn.setMinimumWidth(120)
        self.add_animation_btn.clicked.connect(self.on_add_animation)

        button_layout.addWidget(self.add_animation_btn)
        button_layout.addStretch()

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
        try:
            # Check if property already exists
            prop = self.note_object.PropertyList.Find("AnimNoteData")

            if not prop:
                # Create new custom property
                prop = self.note_object.PropertyCreate("AnimNoteData", FBPropertyString, "String", True, True)
                print("[Anim Exporter] Created custom property: AnimNoteData")
            else:
                print("[Anim Exporter] Found existing custom property: AnimNoteData")

            self.data_property = prop

        except Exception as e:
            print(f"[Anim Exporter] Error creating custom property: {str(e)}")
            logger.error(f"Failed to create custom property: {str(e)}")

    def load_data_from_note(self):
        """Load animation data from the note's custom property"""
        if not self.data_property:
            print("[Anim Exporter] No data property available")
            return

        try:
            # Get the data from the property
            data_str = self.data_property.Data

            if not data_str:
                print("[Anim Exporter] No data found in note property")
                return

            # Parse JSON data
            animation_list = json.loads(data_str)
            print(f"[Anim Exporter] Loaded {len(animation_list)} animation(s) from note")

            # Populate table (disable change tracking temporarily)
            self.animation_table.itemChanged.disconnect(self.on_table_data_changed)

            for anim_data in animation_list:
                self._add_row_to_table(
                    anim_data.get('name', ''),
                    anim_data.get('start_frame', 0),
                    anim_data.get('end_frame', 100),
                    anim_data.get('namespace', ''),
                    anim_data.get('path', '')
                )

            # Re-enable change tracking
            self.animation_table.itemChanged.connect(self.on_table_data_changed)

        except json.JSONDecodeError as e:
            print(f"[Anim Exporter] Error parsing JSON data: {str(e)}")
            logger.error(f"Failed to parse animation data: {str(e)}")
        except Exception as e:
            print(f"[Anim Exporter] Error loading data: {str(e)}")
            logger.error(f"Failed to load data from note: {str(e)}")

    def save_data_to_note(self):
        """Save animation data to the note's custom property"""
        if not self.data_property:
            print("[Anim Exporter] No data property available")
            return

        try:
            # Collect all animation data from table
            animation_list = []

            for row in range(self.animation_table.rowCount()):
                anim_data = {
                    'name': self.animation_table.item(row, 1).text(),
                    'start_frame': int(self.animation_table.item(row, 2).text()),
                    'end_frame': int(self.animation_table.item(row, 3).text()),
                    'namespace': self.animation_table.item(row, 4).text(),
                    'path': self.animation_table.item(row, 5).text()
                }
                animation_list.append(anim_data)

            # Convert to JSON and save
            data_str = json.dumps(animation_list, indent=2)
            self.data_property.Data = data_str

            print(f"[Anim Exporter] Saved {len(animation_list)} animation(s) to note")

        except Exception as e:
            print(f"[Anim Exporter] Error saving data: {str(e)}")
            logger.error(f"Failed to save data to note: {str(e)}")

    def on_table_data_changed(self, item):
        """Handle table data changes and save to note"""
        print(f"[Anim Exporter] Table data changed at row {item.row()}, column {item.column()}")
        self.save_data_to_note()

    def _add_row_to_table(self, name, start_frame, end_frame, namespace, path):
        """Add a row to the table with the given data"""
        row_count = self.animation_table.rowCount()
        self.animation_table.insertRow(row_count)

        # Column 0: Row number (centered)
        number_item = QTableWidgetItem(str(row_count + 1))
        number_item.setFlags(number_item.flags() & ~Qt.ItemIsEditable)  # Read-only
        number_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.animation_table.setItem(row_count, 0, number_item)

        # Column 1: Animation Name (left-aligned)
        name_item = QTableWidgetItem(name)
        self.animation_table.setItem(row_count, 1, name_item)

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
                    data['start_frame'],
                    data['end_frame'],
                    data['namespace'],
                    data['path']
                )

                # Re-enable change tracking
                self.animation_table.itemChanged.connect(self.on_table_data_changed)

                # Save to note
                self.save_data_to_note()

                print(f"[Anim Exporter] Added animation: {data['name']}")

    def closeEvent(self, event):
        """Handle dialog close event"""
        global _anim_exporter_dialog
        global _q_application_instance

        self._is_closing = True
        _anim_exporter_dialog = None
        _q_application_instance = None
        event.accept()
