"""
Character Mapper Tool
Visual character mapping with preset save/load functionality
"""

from pyfbsdk import (
    FBTool, FBLayout, FBButton, FBLabel, FBList, FBEdit,
    FBAttachType, FBMessageBox, FBCharacter, FBBodyNodeId,
    FBModelList, FBGetSelectedModels, FBApplication,
    FBEditProperty, FBPropertyListComponent, FBFilePopup,
    FBFilePopupStyle
)
from pyfbsdk_additions import FBPropertyListComponentList
from core.logger import logger
from pathlib import Path
import json
import shutil

TOOL_NAME = "Character Mapper"

# Character bone slots in logical order
CHARACTER_SLOTS = [
    # Reference
    ("Reference", FBBodyNodeId.kFBReferenceNodeId),

    # Hips and Spine
    ("Hips", FBBodyNodeId.kFBHipsNodeId),
    ("Spine", FBBodyNodeId.kFBSpineNodeId),
    ("Spine1", FBBodyNodeId.kFBSpine1NodeId),
    ("Spine2", FBBodyNodeId.kFBSpine2NodeId),
    ("Spine3", FBBodyNodeId.kFBSpine3NodeId),

    # Neck and Head
    ("Neck", FBBodyNodeId.kFBNeckNodeId),
    ("Head", FBBodyNodeId.kFBHeadNodeId),

    # Left Arm
    ("LeftShoulder", FBBodyNodeId.kFBLeftShoulderNodeId),
    ("LeftArm", FBBodyNodeId.kFBLeftArmNodeId),
    ("LeftForeArm", FBBodyNodeId.kFBLeftForeArmNodeId),
    ("LeftHand", FBBodyNodeId.kFBLeftHandNodeId),

    # Right Arm
    ("RightShoulder", FBBodyNodeId.kFBRightShoulderNodeId),
    ("RightArm", FBBodyNodeId.kFBRightArmNodeId),
    ("RightForeArm", FBBodyNodeId.kFBRightForeArmNodeId),
    ("RightHand", FBBodyNodeId.kFBRightHandNodeId),

    # Left Leg
    ("LeftUpLeg", FBBodyNodeId.kFBLeftUpLegNodeId),
    ("LeftLeg", FBBodyNodeId.kFBLeftLegNodeId),
    ("LeftFoot", FBBodyNodeId.kFBLeftFootNodeId),

    # Right Leg
    ("RightUpLeg", FBBodyNodeId.kFBRightUpLegNodeId),
    ("RightLeg", FBBodyNodeId.kFBRightLegNodeId),
    ("RightFoot", FBBodyNodeId.kFBRightFootNodeId),
]


class CharacterMapperUI(FBTool):
    """Visual character mapping tool with preset management"""

    def __init__(self, name):
        FBTool.__init__(self, name)
        self.character = None
        self.bone_mappings = {}  # slot_name -> model
        self.preset_path = self._get_preset_path()
        self.BuildUI()
        self.LoadSceneModels()

    def _get_preset_path(self):
        """Get the path to the presets directory"""
        root = Path(__file__).parent.parent.parent.parent
        preset_dir = root / "presets" / "characters"
        preset_dir.mkdir(parents=True, exist_ok=True)
        return preset_dir

    def BuildUI(self):
        """Build the tool interface"""
        # Main regions
        x = FBAddRegionParam(0, FBAttachType.kFBAttachLeft, "")
        y = FBAddRegionParam(0, FBAttachType.kFBAttachTop, "")
        w = FBAddRegionParam(0, FBAttachType.kFBAttachRight, "")
        h = FBAddRegionParam(0, FBAttachType.kFBAttachBottom, "")

        # Create main layout
        main = FBLayout()
        self.AddRegion("main", "main", x, y, w, h)
        self.SetControl("main", main)

        # Split into sections
        x_left = FBAddRegionParam(0, FBAttachType.kFBAttachLeft, "")
        x_right = FBAddRegionParam(300, FBAttachType.kFBAttachLeft, "")
        x_end = FBAddRegionParam(0, FBAttachType.kFBAttachRight, "")

        y_top = FBAddRegionParam(0, FBAttachType.kFBAttachTop, "")
        y_mid = FBAddRegionParam(-150, FBAttachType.kFBAttachBottom, "")
        y_bottom = FBAddRegionParam(0, FBAttachType.kFBAttachBottom, "")

        # Left panel - Bone mapping
        mapping_layout = FBLayout()
        main.AddRegion("mapping", "mapping", x_left, y_top, x_right, y_mid)
        main.SetControl("mapping", mapping_layout)

        # Right panel - Scene objects
        objects_layout = FBLayout()
        main.AddRegion("objects", "objects", x_right, y_top, x_end, y_mid)
        main.SetControl("objects", objects_layout)

        # Bottom panel - Actions
        actions_layout = FBLayout()
        main.AddRegion("actions", "actions", x_left, y_mid, x_end, y_bottom)
        main.SetControl("actions", actions_layout)

        # Build sub-panels
        self._build_mapping_panel(mapping_layout)
        self._build_objects_panel(objects_layout)
        self._build_actions_panel(actions_layout)

    def _build_mapping_panel(self, layout):
        """Build the bone mapping panel"""
        # Title
        y_offset = 5
        label = FBLabel()
        label.Caption = "Character Bone Mapping"
        label.Style = FBTextStyle.kFBTextStyleBold

        x = FBAddRegionParam(5, FBAttachType.kFBAttachLeft, "")
        y = FBAddRegionParam(y_offset, FBAttachType.kFBAttachTop, "")
        w = FBAddRegionParam(-5, FBAttachType.kFBAttachRight, "")
        h = FBAddRegionParam(y_offset + 20, FBAttachType.kFBAttachTop, "")

        layout.AddRegion("title", "title", x, y, w, h)
        layout.SetControl("title", label)

        # Scrollable list of bone mappings
        y_list_top = FBAddRegionParam(30, FBAttachType.kFBAttachTop, "")
        y_list_bottom = FBAddRegionParam(-5, FBAttachType.kFBAttachBottom, "")

        self.mapping_list = FBList()
        self.mapping_list.Style = FBListStyle.kFBDropDownList
        self.mapping_list.MultiSelect = False

        layout.AddRegion("mappings", "mappings", x, y_list_top, w, y_list_bottom)
        layout.SetControl("mappings", self.mapping_list)

        # Populate with character slots
        for slot_name, slot_id in CHARACTER_SLOTS:
            self.mapping_list.Items.append(f"{slot_name}: <None>")
            self.bone_mappings[slot_name] = None

    def _build_objects_panel(self, layout):
        """Build the scene objects panel"""
        # Title
        label = FBLabel()
        label.Caption = "Scene Objects"
        label.Style = FBTextStyle.kFBTextStyleBold

        x = FBAddRegionParam(5, FBAttachType.kFBAttachLeft, "")
        y = FBAddRegionParam(5, FBAttachType.kFBAttachTop, "")
        w = FBAddRegionParam(-5, FBAttachType.kFBAttachRight, "")
        h = FBAddRegionParam(25, FBAttachType.kFBAttachTop, "")

        layout.AddRegion("obj_title", "obj_title", x, y, w, h)
        layout.SetControl("obj_title", label)

        # Object list
        y_list_top = FBAddRegionParam(30, FBAttachType.kFBAttachTop, "")
        y_btn_top = FBAddRegionParam(-35, FBAttachType.kFBAttachBottom, "")
        y_list_bottom = FBAddRegionParam(-40, FBAttachType.kFBAttachBottom, "")
        y_btn_bottom = FBAddRegionParam(-5, FBAttachType.kFBAttachBottom, "")

        self.objects_list = FBList()
        self.objects_list.MultiSelect = False
        self.objects_list.OnDblClick.Add(self.OnAssignBone)

        layout.AddRegion("objects_list", "objects_list", x, y_list_top, w, y_list_bottom)
        layout.SetControl("objects_list", self.objects_list)

        # Assign button
        assign_btn = FBButton()
        assign_btn.Caption = "Assign to Selected Slot"
        assign_btn.OnClick.Add(self.OnAssignBone)

        layout.AddRegion("assign_btn", "assign_btn", x, y_btn_top, w, y_btn_bottom)
        layout.SetControl("assign_btn", assign_btn)

    def _build_actions_panel(self, layout):
        """Build the actions panel"""
        # Characterize button
        x_col1 = FBAddRegionParam(5, FBAttachType.kFBAttachLeft, "")
        x_col2 = FBAddRegionParam(0, FBAttachType.kFBAttachRight, "")
        x_col2_start = FBAddRegionParam(-205, FBAttachType.kFBAttachRight, "")

        y_row1 = FBAddRegionParam(5, FBAttachType.kFBAttachTop, "")
        y_row2 = FBAddRegionParam(35, FBAttachType.kFBAttachTop, "")
        y_row3 = FBAddRegionParam(65, FBAttachType.kFBAttachTop, "")
        y_row4 = FBAddRegionParam(95, FBAttachType.kFBAttachTop, "")
        y_h = FBAddRegionParam(30, FBAttachType.kFBAttachNone, "")

        # Characterize
        char_btn = FBButton()
        char_btn.Caption = "Create Character"
        char_btn.OnClick.Add(self.OnCharacterize)
        layout.AddRegion("char_btn", "char_btn", x_col1, y_row1, x_col2_start, y_row1, 0, y_h)
        layout.SetControl("char_btn", char_btn)

        # Clear
        clear_btn = FBButton()
        clear_btn.Caption = "Clear Mapping"
        clear_btn.OnClick.Add(self.OnClearMapping)
        layout.AddRegion("clear_btn", "clear_btn", x_col2_start, y_row1, x_col2, y_row1, 0, y_h)
        layout.SetControl("clear_btn", clear_btn)

        # Preset name
        preset_label = FBLabel()
        preset_label.Caption = "Preset Name:"
        layout.AddRegion("preset_label", "preset_label", x_col1, y_row2, x_col2_start, y_row2, 0, y_h)
        layout.SetControl("preset_label", preset_label)

        self.preset_name = FBEdit()
        self.preset_name.Text = "MyCharacter"
        layout.AddRegion("preset_name", "preset_name", x_col2_start, y_row2, x_col2, y_row2, 0, y_h)
        layout.SetControl("preset_name", self.preset_name)

        # Save preset
        save_btn = FBButton()
        save_btn.Caption = "Save Preset"
        save_btn.OnClick.Add(self.OnSavePreset)
        layout.AddRegion("save_btn", "save_btn", x_col1, y_row3, x_col2_start, y_row3, 0, y_h)
        layout.SetControl("save_btn", save_btn)

        # Load preset
        load_btn = FBButton()
        load_btn.Caption = "Load Preset"
        load_btn.OnClick.Add(self.OnLoadPreset)
        layout.AddRegion("load_btn", "load_btn", x_col2_start, y_row3, x_col2, y_row3, 0, y_h)
        layout.SetControl("load_btn", load_btn)

        # Export/Import
        export_btn = FBButton()
        export_btn.Caption = "Export Preset..."
        export_btn.OnClick.Add(self.OnExportPreset)
        layout.AddRegion("export_btn", "export_btn", x_col1, y_row4, x_col2_start, y_row4, 0, y_h)
        layout.SetControl("export_btn", export_btn)

        import_btn = FBButton()
        import_btn.Caption = "Import Preset..."
        import_btn.OnClick.Add(self.OnImportPreset)
        layout.AddRegion("import_btn", "import_btn", x_col2_start, y_row4, x_col2, y_row4, 0, y_h)
        layout.SetControl("import_btn", import_btn)

    def LoadSceneModels(self):
        """Load all scene models into the objects list"""
        self.objects_list.Items.clear()

        # Get all models in scene
        app = FBApplication()
        scene = app.FBXScene

        for model in scene.RootModel.Children:
            self._add_model_recursive(model)

    def _add_model_recursive(self, model):
        """Recursively add models to the list"""
        self.objects_list.Items.append(model.LongName)
        for child in model.Children:
            self._add_model_recursive(child)

    def OnAssignBone(self, control, event):
        """Assign selected object to selected bone slot"""
        if self.mapping_list.ItemIndex < 0:
            FBMessageBox("Error", "Please select a bone slot first", "OK")
            return

        if self.objects_list.ItemIndex < 0:
            FBMessageBox("Error", "Please select an object", "OK")
            return

        slot_name = CHARACTER_SLOTS[self.mapping_list.ItemIndex][0]
        object_name = self.objects_list.Items[self.objects_list.ItemIndex]

        # Store mapping
        self.bone_mappings[slot_name] = object_name

        # Update display
        self.mapping_list.Items[self.mapping_list.ItemIndex] = f"{slot_name}: {object_name}"

        print(f"[Character Mapper] Mapped {slot_name} -> {object_name}")

    def OnClearMapping(self, control, event):
        """Clear all bone mappings"""
        for i, (slot_name, slot_id) in enumerate(CHARACTER_SLOTS):
            self.bone_mappings[slot_name] = None
            self.mapping_list.Items[i] = f"{slot_name}: <None>"

        print("[Character Mapper] Cleared all mappings")

    def OnCharacterize(self, control, event):
        """Create character from current mapping"""
        print("[Character Mapper] Creating character...")

        try:
            # Check if we have required bones
            required = ["Hips", "LeftUpLeg", "RightUpLeg", "Spine"]
            missing = [slot for slot in required if not self.bone_mappings.get(slot)]

            if missing:
                FBMessageBox(
                    "Missing Required Bones",
                    f"Please map these required bones:\n{', '.join(missing)}",
                    "OK"
                )
                return

            # Create character
            self.character = FBCharacter(self.preset_name.Text or "Character")

            # Map bones
            app = FBApplication()
            for slot_name, slot_id in CHARACTER_SLOTS:
                bone_name = self.bone_mappings.get(slot_name)
                if bone_name:
                    # Find model in scene
                    model = app.FBXScene.FindModelByLabelName(bone_name)
                    if model:
                        self.character.SetCharacterizeOn(False)
                        self.character.SetCharacterizeOn(False)
                        prop_list = self.character.PropertyList.Find(slot_name + "Link")
                        if prop_list:
                            prop_list.append(model)
                        print(f"[Character Mapper] Linked {slot_name} -> {model.Name}")

            # Characterize
            self.character.SetCharacterizeOn(True)

            if self.character.GetCharacterizeError():
                error_msg = "Characterization failed. Check bone positions and hierarchy."
                FBMessageBox("Characterization Error", error_msg, "OK")
                print(f"[Character Mapper ERROR] {error_msg}")
            else:
                FBMessageBox(
                    "Success",
                    f"Character '{self.character.Name}' created successfully!",
                    "OK"
                )
                print(f"[Character Mapper] Character created: {self.character.Name}")

        except Exception as e:
            logger.error(f"Characterization failed: {str(e)}")
            FBMessageBox("Error", f"Failed to create character:\n{str(e)}", "OK")
            import traceback
            traceback.print_exc()

    def OnSavePreset(self, control, event):
        """Save current mapping as a preset"""
        preset_name = self.preset_name.Text or "Character"

        # Build preset data
        preset_data = {
            "name": preset_name,
            "version": "1.0",
            "mappings": {}
        }

        for slot_name, bone_name in self.bone_mappings.items():
            if bone_name:
                preset_data["mappings"][slot_name] = bone_name

        # Save to file
        preset_file = self.preset_path / f"{preset_name}.json"
        try:
            with open(preset_file, 'w') as f:
                json.dump(preset_data, f, indent=2)

            FBMessageBox(
                "Preset Saved",
                f"Preset saved to:\n{preset_file}",
                "OK"
            )
            print(f"[Character Mapper] Saved preset: {preset_file}")

        except Exception as e:
            FBMessageBox("Error", f"Failed to save preset:\n{str(e)}", "OK")
            logger.error(f"Failed to save preset: {str(e)}")

    def OnLoadPreset(self, control, event):
        """Load a preset"""
        # TODO: Show preset browser
        preset_name = self.preset_name.Text or "Character"
        preset_file = self.preset_path / f"{preset_name}.json"

        if not preset_file.exists():
            FBMessageBox(
                "Preset Not Found",
                f"Preset '{preset_name}' not found.\n\nAvailable presets in:\n{self.preset_path}",
                "OK"
            )
            return

        try:
            with open(preset_file, 'r') as f:
                preset_data = json.load(f)

            # Apply mappings
            self.OnClearMapping(None, None)

            for slot_name, bone_name in preset_data.get("mappings", {}).items():
                if slot_name in self.bone_mappings:
                    self.bone_mappings[slot_name] = bone_name

                    # Update display
                    for i, (s_name, s_id) in enumerate(CHARACTER_SLOTS):
                        if s_name == slot_name:
                            self.mapping_list.Items[i] = f"{slot_name}: {bone_name}"
                            break

            FBMessageBox("Preset Loaded", f"Preset '{preset_name}' loaded successfully!", "OK")
            print(f"[Character Mapper] Loaded preset: {preset_file}")

        except Exception as e:
            FBMessageBox("Error", f"Failed to load preset:\n{str(e)}", "OK")
            logger.error(f"Failed to load preset: {str(e)}")

    def OnExportPreset(self, control, event):
        """Export preset to external file"""
        preset_name = self.preset_name.Text or "Character"
        preset_file = self.preset_path / f"{preset_name}.json"

        if not preset_file.exists():
            FBMessageBox(
                "Preset Not Found",
                f"Preset '{preset_name}' not found.\nPlease save the preset first.",
                "OK"
            )
            return

        # Show file save dialog
        popup = FBFilePopup()
        popup.Caption = "Export Character Preset"
        popup.Style = FBFilePopupStyle.kFBFilePopupSave
        popup.Filter = "*.json"
        popup.FileName = f"{preset_name}.json"

        if popup.Execute():
            try:
                export_path = popup.FullFilename
                shutil.copy2(preset_file, export_path)

                FBMessageBox(
                    "Export Successful",
                    f"Preset exported to:\n{export_path}",
                    "OK"
                )
                print(f"[Character Mapper] Exported preset to: {export_path}")

            except Exception as e:
                FBMessageBox("Error", f"Failed to export preset:\n{str(e)}", "OK")
                logger.error(f"Failed to export preset: {str(e)}")

    def OnImportPreset(self, control, event):
        """Import preset from external file"""
        # Show file open dialog
        popup = FBFilePopup()
        popup.Caption = "Import Character Preset"
        popup.Style = FBFilePopupStyle.kFBFilePopupOpen
        popup.Filter = "*.json"

        if popup.Execute():
            try:
                import_path = Path(popup.FullFilename)

                # Read the preset
                with open(import_path, 'r') as f:
                    preset_data = json.load(f)

                preset_name = preset_data.get("name", import_path.stem)

                # Copy to presets directory
                dest_file = self.preset_path / f"{preset_name}.json"
                shutil.copy2(import_path, dest_file)

                # Update preset name field
                self.preset_name.Text = preset_name

                # Load the preset
                self.OnClearMapping(None, None)

                for slot_name, bone_name in preset_data.get("mappings", {}).items():
                    if slot_name in self.bone_mappings:
                        self.bone_mappings[slot_name] = bone_name

                        # Update display
                        for i, (s_name, s_id) in enumerate(CHARACTER_SLOTS):
                            if s_name == slot_name:
                                self.mapping_list.Items[i] = f"{slot_name}: {bone_name}"
                                break

                FBMessageBox(
                    "Import Successful",
                    f"Preset '{preset_name}' imported and loaded!",
                    "OK"
                )
                print(f"[Character Mapper] Imported preset from: {import_path}")

            except Exception as e:
                FBMessageBox("Error", f"Failed to import preset:\n{str(e)}", "OK")
                logger.error(f"Failed to import preset: {str(e)}")


def execute(control, event):
    """Show the Character Mapper tool"""
    tool = CharacterMapperUI("Character Mapper")
    tool.StartSizeX = 700
    tool.StartSizeY = 600
    ShowTool(tool)
