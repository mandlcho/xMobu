"""
xMobu Settings Tool (Qt Designer version)
Configure P4 connection and export paths using Qt Designer UI
"""

from pathlib import Path
import subprocess
import os

try:
    from PySide2 import QtWidgets, QtCore, QtUiTools
    from PySide2.QtWidgets import QDialog, QFileDialog, QMessageBox
    from PySide2.QtCore import QFile
except ImportError:
    try:
        from PySide import QtGui as QtWidgets
        from PySide import QtCore, QtUiTools
        from PySide.QtGui import QDialog, QFileDialog, QMessageBox
        from PySide.QtCore import QFile
    except ImportError:
        print("[Settings Qt] ERROR: Neither PySide2 nor PySide found")
        QtWidgets = None

from core.config import config
from core.logger import logger

TOOL_NAME = "xMobu Settings (Qt)"

# Global reference to prevent garbage collection
_settings_dialog = None


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
    _settings_dialog = SettingsDialog()
    _settings_dialog.show()


class SettingsDialog(QDialog):
    """Settings dialog using Qt Designer UI"""

    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.workspaces = []

        # Load the UI file
        ui_path = Path(__file__).parent / "settings.ui"
        self.load_ui(str(ui_path))

    def load_ui(self, ui_file):
        """Load UI from .ui file"""
        try:
            loader = QtUiTools.QUiLoader()
            file = QFile(ui_file)

            if not file.exists():
                print(f"[Settings Qt] UI file not found: {ui_file}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"UI file not found:\n{ui_file}"
                )
                return

            file.open(QFile.ReadOnly)
            ui = loader.load(file, self)
            file.close()

            if ui:
                # Set the loaded UI as the layout
                layout = QtWidgets.QVBoxLayout(self)
                layout.addWidget(ui)
                self.setLayout(layout)

                # Store references to UI elements
                self.ui = ui

                # Connect signals
                self.connect_signals()
                # Load settings
                self.load_settings()

                print("[Settings Qt] UI loaded successfully")
            else:
                print("[Settings Qt] Failed to load UI")

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
        # P4 fields - auto-load workspaces
        self.ui.p4ServerEdit.textChanged.connect(self.on_p4_credentials_changed)
        self.ui.p4UserEdit.textChanged.connect(self.on_p4_credentials_changed)

        # Buttons
        self.ui.testP4Button.clicked.connect(self.on_test_p4_connection)
        self.ui.browseFbxButton.clicked.connect(self.on_browse_fbx_path)
        self.ui.saveButton.clicked.connect(self.on_save_settings)
        self.ui.resetButton.clicked.connect(self.on_reset_settings)
        self.ui.applyCloseButton.clicked.connect(self.on_apply_and_close)

    def load_settings(self):
        """Load settings from config"""
        # Load P4 settings
        self.ui.p4ServerEdit.setText(config.get('perforce.server', ''))
        self.ui.p4UserEdit.setText(config.get('perforce.user', ''))

        saved_workspace = config.get('perforce.workspace', '')

        # Load export settings
        self.ui.fbxPathEdit.setText(config.get('export.fbx_path', ''))

        # Try to load workspaces if server and user are set
        if self.ui.p4ServerEdit.text() and self.ui.p4UserEdit.text():
            self.load_workspaces()
            # Select the saved workspace if it exists
            if saved_workspace:
                items = self.ui.p4WorkspaceList.findItems(saved_workspace, QtCore.Qt.MatchContains)
                if items:
                    self.ui.p4WorkspaceList.setCurrentItem(items[0])

        print("[Settings Qt] Loaded settings from config")

    def on_p4_credentials_changed(self):
        """Called when server or user fields change"""
        server = self.ui.p4ServerEdit.text()
        user = self.ui.p4UserEdit.text()

        if server and user:
            print(f"[Settings Qt] P4 credentials changed, loading workspaces...")
            self.load_workspaces()

    def load_workspaces(self):
        """Query P4 for available workspaces"""
        server = self.ui.p4ServerEdit.text()
        user = self.ui.p4UserEdit.text()

        if not server or not user:
            return

        # Clear existing list
        self.ui.p4WorkspaceList.clear()

        print(f"[Settings Qt] Querying workspaces for {user}@{server}...")
        self.ui.p4StatusLabel.setText("Status: Loading workspaces...")

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
                    self.ui.p4WorkspaceList.addItems(workspaces)
                    self.ui.p4StatusLabel.setText(f"Status: Found {len(workspaces)} workspace(s)")
                    print(f"[Settings Qt] Found {len(workspaces)} workspaces")
                else:
                    self.ui.p4WorkspaceList.addItem("(No workspaces found)")
                    self.ui.p4StatusLabel.setText("Status: No workspaces found")
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.ui.p4WorkspaceList.addItem("(Error loading workspaces)")
                self.ui.p4StatusLabel.setText(f"Status: Error - {error_msg[:30]}...")
                logger.error(f"P4 query failed: {error_msg}")

        except FileNotFoundError:
            self.ui.p4WorkspaceList.addItem("(P4 command not found)")
            self.ui.p4StatusLabel.setText("Status: P4 CLI not installed")
            print("[Settings Qt] P4 command-line tool not found")
            QMessageBox.warning(
                self.ui,
                "P4 Not Found",
                "Perforce command-line tool (p4) not found.\n\n"
                "Please install P4 CLI and ensure it's in your PATH."
            )

        except subprocess.TimeoutExpired:
            self.ui.p4WorkspaceList.addItem("(Connection timeout)")
            self.ui.p4StatusLabel.setText("Status: Connection timeout")

        except Exception as e:
            self.ui.p4WorkspaceList.addItem("(Error loading workspaces)")
            self.ui.p4StatusLabel.setText(f"Status: Error - {str(e)[:30]}...")
            logger.error(f"Failed to load workspaces: {str(e)}")

    def on_test_p4_connection(self):
        """Test P4 connection"""
        server = self.ui.p4ServerEdit.text()
        user = self.ui.p4UserEdit.text()

        current_item = self.ui.p4WorkspaceList.currentItem()
        workspace = current_item.text() if current_item else ""

        if not server or not user or not workspace or workspace.startswith("("):
            QMessageBox.warning(
                self.ui,
                "Missing Information",
                "Please fill in Server, User, and select a Workspace"
            )
            return

        try:
            # Set P4 environment variables
            os.environ['P4PORT'] = server
            os.environ['P4USER'] = user
            os.environ['P4CLIENT'] = workspace

            self.ui.p4StatusLabel.setText("Status: Connection configured")
            QMessageBox.information(
                self.ui,
                "P4 Configuration",
                f"Perforce settings configured:\n\n"
                f"Server: {server}\n"
                f"User: {user}\n"
                f"Workspace: {workspace}\n\n"
                f"Environment variables have been set."
            )
            print("[Settings Qt] P4 configuration set successfully")

        except Exception as e:
            self.ui.p4StatusLabel.setText(f"Status: Error - {str(e)}")
            QMessageBox.critical(
                self.ui,
                "Connection Error",
                f"Failed to test P4 connection:\n{str(e)}"
            )
            logger.error(f"P4 connection test failed: {str(e)}")

    def on_browse_fbx_path(self):
        """Browse for FBX export directory"""
        current_path = self.ui.fbxPathEdit.text() or ""

        directory = QFileDialog.getExistingDirectory(
            self.ui,
            "Select FBX Export Directory",
            current_path
        )

        if directory:
            self.ui.fbxPathEdit.setText(directory)
            print(f"[Settings Qt] FBX export path set to: {directory}")

    def on_save_settings(self):
        """Save settings to config"""
        try:
            # Save P4 settings
            config.set('perforce.server', self.ui.p4ServerEdit.text())
            config.set('perforce.user', self.ui.p4UserEdit.text())

            # Get selected workspace
            current_item = self.ui.p4WorkspaceList.currentItem()
            workspace = current_item.text() if current_item else ""
            if workspace.startswith("("):
                workspace = ""
            config.set('perforce.workspace', workspace)

            # Save export settings
            fbx_path = self.ui.fbxPathEdit.text()
            if fbx_path:
                path_obj = Path(fbx_path)
                if not path_obj.exists():
                    reply = QMessageBox.question(
                        self.ui,
                        "Path Not Found",
                        f"The path does not exist:\n{fbx_path}\n\nCreate it?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        try:
                            path_obj.mkdir(parents=True, exist_ok=True)
                        except Exception as e:
                            QMessageBox.critical(
                                self.ui,
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
                self.ui,
                "Success",
                "Settings saved successfully!"
            )
            print("[Settings Qt] Settings saved to config file")

        except Exception as e:
            QMessageBox.critical(
                self.ui,
                "Error",
                f"Failed to save settings:\n{str(e)}"
            )
            logger.error(f"Failed to save settings: {str(e)}")

    def on_reset_settings(self):
        """Reset settings to defaults"""
        reply = QMessageBox.question(
            self.ui,
            "Reset Settings",
            "Reset all settings to default values?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.ui.p4ServerEdit.clear()
            self.ui.p4UserEdit.clear()
            self.ui.p4WorkspaceList.clear()
            self.ui.fbxPathEdit.clear()
            self.ui.p4StatusLabel.setText("Status: Not connected")
            print("[Settings Qt] Settings reset to defaults")

    def on_apply_and_close(self):
        """Save settings and close"""
        self.on_save_settings()
        print("[Settings Qt] Settings applied")
