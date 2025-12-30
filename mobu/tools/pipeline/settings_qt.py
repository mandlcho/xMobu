"""
xMobu Settings Tool (Qt Designer version)
Configure P4 connection and export paths using Qt Designer UI
"""

from pathlib import Path
import subprocess
import os

try:
    from PySide2 import QtWidgets, QtCore, QtUiTools
    from PySide2.QtWidgets import QDialog, QFileDialog, QMessageBox, QApplication
    from PySide2.QtCore import QFile, Qt
except ImportError:
    try:
        from PySide import QtGui as QtWidgets
        from PySide import QtCore, QtUiTools
        from PySide.QtGui import QDialog, QFileDialog, QMessageBox, QApplication
        from PySide.QtCore import QFile, Qt
    except ImportError:
        print("[Settings Qt] ERROR: Neither PySide2 nor PySide found")
        QtWidgets = None

from core.config import config
from core.logger import logger

TOOL_NAME = "xMobu Settings"

# Global reference to prevent garbage collection
_settings_dialog = None


def get_mobu_main_window():
    """Get MotionBuilder's main window to use as parent"""
    try:
        app = QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                if widget.objectName() == "MotionBuilder":
                    return widget
        return None
    except:
        return None


def execute(control, event):
    """Execute the Settings tool"""
    global _settings_dialog

    if _settings_dialog is not None:
        print("[Settings Qt] Bringing existing dialog to front")
        _settings_dialog.show()
        _settings_dialog.raise_()
        _settings_dialog.activateWindow()
        return

    print("[Settings Qt] Creating new settings dialog")
    parent = get_mobu_main_window()
    _settings_dialog = SettingsDialog(parent)
    _settings_dialog.show()


class SettingsDialog(QDialog):
    """Settings dialog using Qt Designer UI"""

    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        # Set window flags to make it a proper dialog
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        self.workspaces = []

        # Load the UI file
        ui_path = Path(__file__).parent / "settings.ui"
        self.load_ui(str(ui_path))

    def load_ui(self, ui_file):
        """Load UI from .ui file"""
        try:
            # Set window properties
            self.setWindowTitle("xMobu Settings")
            self.resize(480, 340)
            self.setMinimumSize(480, 340)
            self.setMaximumSize(600, 450)

            loader = QtUiTools.QUiLoader()
            file = QFile(ui_file)

            if not file.exists():
                print(f"[Settings Qt] UI file not found: {ui_file}")
                print(f"[Settings Qt] Searched path: {ui_file}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"UI file not found:\n{ui_file}"
                )
                return

            file.open(QFile.ReadOnly)
            print(f"[Settings Qt] Loading UI from: {ui_file}")
            ui_widget = loader.load(file, self)
            file.close()

            if ui_widget:
                print(f"[Settings Qt] UI widget loaded, type: {type(ui_widget)}")

                # Create layout and add the loaded widget
                layout = QtWidgets.QVBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(ui_widget)
                self.setLayout(layout)

                # Store references to UI elements using findChild
                self.p4ServerEdit = ui_widget.findChild(QtWidgets.QLineEdit, "p4ServerEdit")
                self.p4UserEdit = ui_widget.findChild(QtWidgets.QLineEdit, "p4UserEdit")
                self.p4WorkspaceList = ui_widget.findChild(QtWidgets.QListWidget, "p4WorkspaceList")
                self.testP4Button = ui_widget.findChild(QtWidgets.QPushButton, "testP4Button")
                self.p4StatusLabel = ui_widget.findChild(QtWidgets.QLabel, "p4StatusLabel")
                self.fbxPathEdit = ui_widget.findChild(QtWidgets.QLineEdit, "fbxPathEdit")
                self.browseFbxButton = ui_widget.findChild(QtWidgets.QPushButton, "browseFbxButton")
                self.saveButton = ui_widget.findChild(QtWidgets.QPushButton, "saveButton")
                self.resetButton = ui_widget.findChild(QtWidgets.QPushButton, "resetButton")
                self.applyCloseButton = ui_widget.findChild(QtWidgets.QPushButton, "applyCloseButton")

                # Debug - print what we found
                print(f"[Settings Qt] Found p4ServerEdit: {self.p4ServerEdit}")
                print(f"[Settings Qt] Found p4UserEdit: {self.p4UserEdit}")
                print(f"[Settings Qt] Found saveButton: {self.saveButton}")

                # Connect signals
                self.connect_signals()
                # Load settings
                self.load_settings()

                print("[Settings Qt] UI loaded successfully")
            else:
                print("[Settings Qt] Failed to load UI widget")
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to load UI file. Check console for details."
                )

        except Exception as e:
            print(f"[Settings Qt] Error loading UI: {str(e)}")
            logger.error(f"Failed to load UI file: {str(e)}")
            import traceback
            traceback.print_exc()

    def closeEvent(self, event):
        """Handle dialog close event"""
        global _settings_dialog
        _settings_dialog = None
        event.accept()

    def connect_signals(self):
        """Connect UI signals to slots"""
        if not self.p4ServerEdit:
            print("[Settings Qt] WARNING: Widgets not found, cannot connect signals")
            return

        # P4 fields - auto-load workspaces
        self.p4ServerEdit.textChanged.connect(self.on_p4_credentials_changed)
        self.p4UserEdit.textChanged.connect(self.on_p4_credentials_changed)

        # Buttons
        self.testP4Button.clicked.connect(self.on_test_p4_connection)
        self.browseFbxButton.clicked.connect(self.on_browse_fbx_path)
        self.saveButton.clicked.connect(self.on_save_settings)
        self.resetButton.clicked.connect(self.on_reset_settings)
        self.applyCloseButton.clicked.connect(self.on_apply_and_close)

        print("[Settings Qt] Signals connected")

    def load_settings(self):
        """Load settings from config"""
        if not self.p4ServerEdit:
            print("[Settings Qt] WARNING: Widgets not found, cannot load settings")
            return

        # Load P4 settings
        self.p4ServerEdit.setText(config.get('perforce.server', ''))
        self.p4UserEdit.setText(config.get('perforce.user', ''))

        saved_workspace = config.get('perforce.workspace', '')

        # Load export settings
        self.fbxPathEdit.setText(config.get('export.fbx_path', ''))

        # Try to load workspaces if server and user are set
        if self.p4ServerEdit.text() and self.p4UserEdit.text():
            self.load_workspaces()
            # Select the saved workspace if it exists
            if saved_workspace:
                items = self.p4WorkspaceList.findItems(saved_workspace, QtCore.Qt.MatchContains)
                if items:
                    self.p4WorkspaceList.setCurrentItem(items[0])

        print("[Settings Qt] Loaded settings from config")

    def on_p4_credentials_changed(self):
        """Called when server or user fields change"""
        server = self.p4ServerEdit.text()
        user = self.p4UserEdit.text()

        if server and user:
            print(f"[Settings Qt] P4 credentials changed, loading workspaces...")
            self.load_workspaces()

    def load_workspaces(self):
        """Query P4 for available workspaces"""
        server = self.p4ServerEdit.text()
        user = self.p4UserEdit.text()

        if not server or not user:
            return

        # Clear existing list
        self.p4WorkspaceList.clear()

        print(f"[Settings Qt] Querying workspaces for {user}@{server}...")
        self.p4StatusLabel.setText("Status: Loading workspaces...")

        try:
            # Set P4 environment
            env = os.environ.copy()
            env['P4PORT'] = server
            env['P4USER'] = user

            # Query P4 for workspaces
            result = subprocess.run(
                ['p4', '-p', server, '-u', user, 'clients', '-u', user],
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )

            if result.returncode == 0:
                workspaces = []
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('Client '):
                        parts = line.split()
                        if len(parts) >= 2:
                            workspaces.append(parts[1])

                if workspaces:
                    self.workspaces = workspaces
                    self.p4WorkspaceList.addItems(workspaces)
                    self.p4StatusLabel.setText(f"Status: Found {len(workspaces)} workspace(s)")
                    print(f"[Settings Qt] Found {len(workspaces)} workspaces")
                else:
                    self.p4WorkspaceList.addItem("(No workspaces found)")
                    self.p4StatusLabel.setText("Status: No workspaces found")
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.p4WorkspaceList.addItem("(Error loading workspaces)")
                self.p4StatusLabel.setText(f"Status: Error - {error_msg[:30]}...")
                logger.error(f"P4 query failed: {error_msg}")

        except FileNotFoundError:
            self.p4WorkspaceList.addItem("(P4 command not found)")
            self.p4StatusLabel.setText("Status: P4 CLI not installed")
            print("[Settings Qt] P4 command-line tool not found")
            QMessageBox.warning(
                self,
                "P4 Not Found",
                "Perforce command-line tool (p4) not found.\n\n"
                "Please install P4 CLI and ensure it's in your PATH."
            )

        except subprocess.TimeoutExpired:
            self.p4WorkspaceList.addItem("(Connection timeout)")
            self.p4StatusLabel.setText("Status: Connection timeout")

        except Exception as e:
            self.p4WorkspaceList.addItem("(Error loading workspaces)")
            self.p4StatusLabel.setText(f"Status: Error - {str(e)[:30]}...")
            logger.error(f"Failed to load workspaces: {str(e)}")

    def on_test_p4_connection(self):
        """Test P4 connection"""
        server = self.p4ServerEdit.text()
        user = self.p4UserEdit.text()

        current_item = self.p4WorkspaceList.currentItem()
        workspace = current_item.text() if current_item else ""

        if not server or not user or not workspace or workspace.startswith("("):
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please fill in Server, User, and select a Workspace"
            )
            return

        try:
            # Set P4 environment variables
            os.environ['P4PORT'] = server
            os.environ['P4USER'] = user
            os.environ['P4CLIENT'] = workspace

            self.p4StatusLabel.setText("Status: Connection configured")
            QMessageBox.information(
                self,
                "P4 Configuration",
                f"Perforce settings configured:\n\n"
                f"Server: {server}\n"
                f"User: {user}\n"
                f"Workspace: {workspace}\n\n"
                f"Environment variables have been set."
            )
            print("[Settings Qt] P4 configuration set successfully")

        except Exception as e:
            self.p4StatusLabel.setText(f"Status: Error - {str(e)}")
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Failed to test P4 connection:\n{str(e)}"
            )
            logger.error(f"P4 connection test failed: {str(e)}")

    def on_browse_fbx_path(self):
        """Browse for FBX export directory"""
        current_path = self.fbxPathEdit.text() or ""

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select FBX Export Directory",
            current_path
        )

        if directory:
            self.fbxPathEdit.setText(directory)
            print(f"[Settings Qt] FBX export path set to: {directory}")

    def on_save_settings(self):
        """Save settings to config"""
        try:
            # Save P4 settings
            config.set('perforce.server', self.p4ServerEdit.text())
            config.set('perforce.user', self.p4UserEdit.text())

            # Get selected workspace
            current_item = self.p4WorkspaceList.currentItem()
            workspace = current_item.text() if current_item else ""
            if workspace.startswith("("):
                workspace = ""
            config.set('perforce.workspace', workspace)

            # Save export settings
            fbx_path = self.fbxPathEdit.text()
            if fbx_path:
                path_obj = Path(fbx_path)
                if not path_obj.exists():
                    reply = QMessageBox.question(
                        self,
                        "Path Not Found",
                        f"The path does not exist:\n{fbx_path}\n\nCreate it?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        try:
                            path_obj.mkdir(parents=True, exist_ok=True)
                        except Exception as e:
                            QMessageBox.critical(
                                self,
                                "Error",
                                f"Failed to create directory:\n{str(e)}"
                            )
                            return
                    else:
                        return

            config.set('export.fbx_path', fbx_path)

            # Save to file
            config.save()

            QMessageBox.information(
                self,
                "Success",
                "Settings saved successfully!"
            )
            print("[Settings Qt] Settings saved to config file")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save settings:\n{str(e)}"
            )
            logger.error(f"Failed to save settings: {str(e)}")

    def on_reset_settings(self):
        """Reset settings to defaults"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all settings to default values?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.p4ServerEdit.clear()
            self.p4UserEdit.clear()
            self.p4WorkspaceList.clear()
            self.fbxPathEdit.clear()
            self.p4StatusLabel.setText("Status: Not connected")
            print("[Settings Qt] Settings reset to defaults")

    def on_apply_and_close(self):
        """Save settings and close"""
        self.on_save_settings()
        print("[Settings Qt] Settings applied, closing window")
        self.close()
