"""
Character Mapper Tool
Visual character mapping with preset save/load functionality
"""

from pyfbsdk import (
    FBTool, FBLayout, FBButton, FBLabel, FBList, FBEdit,
    FBAttachType, FBMessageBox, FBCharacter, FBBodyNodeId,
    FBModelList, FBGetSelectedModels, FBApplication, FBSystem,
    FBFilePopup, FBFilePopupStyle, FBAddRegionParam,
    ShowTool, FBTextStyle, FBListStyle
)
from core.decorators import CreateUniqueTool
from core.logger import logger
from pathlib import Path
import json
import shutil

TOOL_NAME = "Character Mapper"

def execute(control, event):
    """Execute the Character Mapper tool"""
    tool = CharacterMapperUI()
    tool.StartSizeX = 700
    tool.StartSizeY = 600
    return tool


# Character bone slots in logical order
# Using only guaranteed FBBodyNodeId attributes
CHARACTER_SLOTS = [
    # Reference
    ("Reference", "Reference"),

    # Hips and Spine (using string names for flexibility)
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


@CreateUniqueTool
class CharacterMapperUI(FBTool):
    """Visual character mapping tool with preset management"""

    def __init__(self):
        FBTool.__init__(self, "CharacterMapperUI")
        self.character = None
        self.bone_mappings = {}  # slot_name -> model
        self.all_models = []  # Store all scene models
        self.filtered_models = []  # Store filtered models
        self.preset_path = self._get_preset_path()

        # Register file callbacks for auto-refresh
        self.app = FBApplication()
        self.file_open_callback_id = None
        self.file_merge_callback_id = None
        self.file_new_callback_id = None

        self.BuildUI()
        self.LoadSceneModels()

        # Register callbacks AFTER UI is built
        self.file_open_callback_id = self.app.OnFileOpen.Add(self.OnFileOpenCallback)
        self.file_merge_callback_id = self.app.OnFileMerge.Add(self.OnFileMergeCallback)
        self.file_new_callback_id = self.app.OnFileNew.Add(self.OnFileNewCallback)

        print("[Character Mapper] Tool initialized with auto-refresh enabled")
        print("[Character Mapper] Registered callbacks: OnFileOpen, OnFileMerge, OnFileNew")

    def __del__(self):
        """Cleanup when tool is destroyed"""
        try:
            # Remove file callbacks
            if hasattr(self, 'app') and self.app:
                if hasattr(self, 'file_open_callback_id') and self.file_open_callback_id is not None:
                    self.app.OnFileOpen.Remove(self.file_open_callback_id)
                if hasattr(self, 'file_merge_callback_id') and self.file_merge_callback_id is not None:
                    self.app.OnFileMerge.Remove(self.file_merge_callback_id)
                if hasattr(self, 'file_new_callback_id') and self.file_new_callback_id is not None:
                    self.app.OnFileNew.Remove(self.file_new_callback_id)
            print("[Character Mapper] Tool destroyed and callbacks removed")
        except Exception as e:
            print(f"[Character Mapper] Cleanup error: {e}")
            pass

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
        self.mapping_list.Style = FBListStyle.kFBVerticalList
        self.mapping_list.MultiSelect = False

        layout.AddRegion("mappings", "mappings", x, y_list_top, w, y_list_bottom)
        layout.SetControl("mappings", self.mapping_list)

        # Populate with character slots
        for slot_name, _ in CHARACTER_SLOTS:
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

        # Search label
        search_label = FBLabel()
        search_label.Caption = "Search:"

        y_search_label = FBAddRegionParam(30, FBAttachType.kFBAttachTop, "")
        h_search_label = FBAddRegionParam(50, FBAttachType.kFBAttachTop, "")

        layout.AddRegion("search_label", "search_label", x, y_search_label, w, h_search_label)
        layout.SetControl("search_label", search_label)

        # Search filter
        y_search = FBAddRegionParam(55, FBAttachType.kFBAttachTop, "")
        h_search = FBAddRegionParam(80, FBAttachType.kFBAttachTop, "")

        self.search_filter = FBEdit()
        self.search_filter.Text = ""
        self.search_filter.OnChange.Add(self.OnFilterChanged)

        layout.AddRegion("search_filter", "search_filter", x, y_search, w, h_search)
        layout.SetControl("search_filter", self.search_filter)

        # Object list
        y_list_top = FBAddRegionParam(85, FBAttachType.kFBAttachTop, "")
        y_btn1_top = FBAddRegionParam(-70, FBAttachType.kFBAttachBottom, "")
        y_btn1_bottom = FBAddRegionParam(-40, FBAttachType.kFBAttachBottom, "")
        y_btn2_top = FBAddRegionParam(-35, FBAttachType.kFBAttachBottom, "")
        y_list_bottom = FBAddRegionParam(-75, FBAttachType.kFBAttachBottom, "")
        y_btn2_bottom = FBAddRegionParam(-5, FBAttachType.kFBAttachBottom, "")

        self.objects_list = FBList()
        self.objects_list.MultiSelect = False
        self.objects_list.Style = FBListStyle.kFBVerticalList

        layout.AddRegion("objects_list", "objects_list", x, y_list_top, w, y_list_bottom)
        layout.SetControl("objects_list", self.objects_list)

        # Refresh button
        refresh_btn = FBButton()
        refresh_btn.Caption = "Refresh Scene"
        refresh_btn.OnClick.Add(self.OnRefreshScene)

        layout.AddRegion("refresh_btn", "refresh_btn", x, y_btn1_top, w, y_btn1_bottom)
        layout.SetControl("refresh_btn", refresh_btn)

        # Assign button
        assign_btn = FBButton()
        assign_btn.Caption = "Assign to Selected Slot"
        assign_btn.OnClick.Add(self.OnAssignBone)

        layout.AddRegion("assign_btn", "assign_btn", x, y_btn2_top, w, y_btn2_bottom)
        layout.SetControl("assign_btn", assign_btn)

    def _build_actions_panel(self, layout):
        """Build the actions panel"""
        # Column positions
        x_col1 = FBAddRegionParam(5, FBAttachType.kFBAttachLeft, "")
        x_col2 = FBAddRegionParam(0, FBAttachType.kFBAttachRight, "")
        x_col2_start = FBAddRegionParam(-205, FBAttachType.kFBAttachRight, "")

        # Row positions (top and bottom for each row)
        y_row1_top = FBAddRegionParam(5, FBAttachType.kFBAttachTop, "")
        y_row1_bot = FBAddRegionParam(35, FBAttachType.kFBAttachTop, "")

        y_row2_top = FBAddRegionParam(40, FBAttachType.kFBAttachTop, "")
        y_row2_bot = FBAddRegionParam(70, FBAttachType.kFBAttachTop, "")

        y_row3_top = FBAddRegionParam(75, FBAttachType.kFBAttachTop, "")
        y_row3_bot = FBAddRegionParam(105, FBAttachType.kFBAttachTop, "")

        y_row4_top = FBAddRegionParam(110, FBAttachType.kFBAttachTop, "")
        y_row4_bot = FBAddRegionParam(140, FBAttachType.kFBAttachTop, "")

        # Characterize
        char_btn = FBButton()
        char_btn.Caption = "Create Character"
        char_btn.OnClick.Add(self.OnCharacterize)
        layout.AddRegion("char_btn", "char_btn", x_col1, y_row1_top, x_col2_start, y_row1_bot)
        layout.SetControl("char_btn", char_btn)

        # Clear
        clear_btn = FBButton()
        clear_btn.Caption = "Clear Mapping"
        clear_btn.OnClick.Add(self.OnClearMapping)
        layout.AddRegion("clear_btn", "clear_btn", x_col2_start, y_row1_top, x_col2, y_row1_bot)
        layout.SetControl("clear_btn", clear_btn)

        # Preset name
        preset_label = FBLabel()
        preset_label.Caption = "Preset Name:"
        layout.AddRegion("preset_label", "preset_label", x_col1, y_row2_top, x_col2_start, y_row2_bot)
        layout.SetControl("preset_label", preset_label)

        self.preset_name = FBEdit()
        self.preset_name.Text = "MyCharacter"
        layout.AddRegion("preset_name", "preset_name", x_col2_start, y_row2_top, x_col2, y_row2_bot)
        layout.SetControl("preset_name", self.preset_name)

        # Save preset
        save_btn = FBButton()
        save_btn.Caption = "Save Preset"
        save_btn.OnClick.Add(self.OnSavePreset)
        layout.AddRegion("save_btn", "save_btn", x_col1, y_row3_top, x_col2_start, y_row3_bot)
        layout.SetControl("save_btn", save_btn)

        # Load preset
        load_btn = FBButton()
        load_btn.Caption = "Load Preset"
        load_btn.OnClick.Add(self.OnLoadPreset)
        layout.AddRegion("load_btn", "load_btn", x_col2_start, y_row3_top, x_col2, y_row3_bot)
        layout.SetControl("load_btn", load_btn)

        # Export/Import
        export_btn = FBButton()
        export_btn.Caption = "Export Preset..."
        export_btn.OnClick.Add(self.OnExportPreset)
        layout.AddRegion("export_btn", "export_btn", x_col1, y_row4_top, x_col2_start, y_row4_bot)
        layout.SetControl("export_btn", export_btn)

        import_btn = FBButton()
        import_btn.Caption = "Import Preset..."
        import_btn.OnClick.Add(self.OnImportPreset)
        layout.AddRegion("import_btn", "import_btn", x_col2_start, y_row4_top, x_col2, y_row4_bot)
        layout.SetControl("import_btn", import_btn)

    def LoadSceneModels(self):
        """Load all scene models into the objects list"""
        # Clear existing lists
        self.all_models = []
        self.filtered_models = []

        # Get all models in scene
        scene = FBSystem().Scene

        for model in scene.RootModel.Children:
            self._add_model_recursive(model)

        # Store filtered models (initially all)
        self.filtered_models = self.all_models[:]

        # Update display
        self._update_objects_display()

    def _add_model_recursive(self, model):
        """Recursively add models to the list"""
        self.all_models.append(model)
        for child in model.Children:
            self._add_model_recursive(child)

    def _update_objects_display(self):
        """Update the objects list display with filtered models"""
        # Clear existing items
        while len(self.objects_list.Items) > 0:
            self.objects_list.Items.removeAt(0)

        # Add filtered models
        for model in self.filtered_models:
            self.objects_list.Items.append(model.LongName)

    def OnFilterChanged(self, control, event):
        """Filter the objects list based on search text"""
        filter_text = self.search_filter.Text.lower()

        if not filter_text:
            # No filter, show all models
            self.filtered_models = self.all_models[:]
        else:
            # Filter models by name
            self.filtered_models = [
                model for model in self.all_models
                if filter_text in model.LongName.lower()
            ]

        # Update display
        self._update_objects_display()

    def OnRefreshScene(self, control, event):
        """Refresh the scene models list"""
        print("[Character Mapper] Refreshing scene models...")
        self.LoadSceneModels()
        # Reapply filter if there is one
        if self.search_filter.Text:
            self.OnFilterChanged(None, None)
        print(f"[Character Mapper] Loaded {len(self.all_models)} models")

    def OnFileOpenCallback(self, control, event):
        """Callback when a file is opened - auto refresh scene"""
        print("[Character Mapper] File opened detected - auto-refreshing scene...")
        self.LoadSceneModels()
        # Reapply filter if there is one
        if hasattr(self, 'search_filter') and self.search_filter.Text:
            self.OnFilterChanged(None, None)
        print(f"[Character Mapper] Auto-refresh complete: {len(self.all_models)} models loaded")

    def OnFileMergeCallback(self, control, event):
        """Callback when a file is merged - auto refresh scene"""
        print("[Character Mapper] File merge detected - auto-refreshing scene...")
        self.LoadSceneModels()
        # Reapply filter if there is one
        if hasattr(self, 'search_filter') and self.search_filter.Text:
            self.OnFilterChanged(None, None)
        print(f"[Character Mapper] Auto-refresh complete: {len(self.all_models)} models loaded")

    def OnFileNewCallback(self, control, event):
        """Callback when a new file is created - auto refresh scene"""
        print("[Character Mapper] File new detected - auto-refreshing scene...")
        self.LoadSceneModels()
        # Reapply filter if there is one
        if hasattr(self, 'search_filter') and self.search_filter.Text:
            self.OnFilterChanged(None, None)
        print(f"[Character Mapper] Auto-refresh complete: {len(self.all_models)} models loaded")

    def OnAssignBone(self, control, event):
        """Assign selected object to selected bone slot"""
        print("[Character Mapper] OnAssignBone called")

        if self.mapping_list.ItemIndex < 0:
            print("[Character Mapper] No bone slot selected")
            FBMessageBox("Error", "Please select a bone slot first", "OK")
            return

        if self.objects_list.ItemIndex < 0:
            print("[Character Mapper] No object selected")
            FBMessageBox("Error", "Please select an object", "OK")
            return

        slot_index = self.mapping_list.ItemIndex
        slot_name = CHARACTER_SLOTS[slot_index][0]

        print(f"[Character Mapper] Slot index: {slot_index}, Slot name: {slot_name}")
        print(f"[Character Mapper] Object index: {self.objects_list.ItemIndex}")
        print(f"[Character Mapper] Filtered models count: {len(self.filtered_models)}")

        # Get the actual model object from filtered list
        selected_model = self.filtered_models[self.objects_list.ItemIndex]

        print(f"[Character Mapper] Selected model: {selected_model.Name} ({selected_model.LongName})")

        # Store mapping (store the model object, not the name)
        self.bone_mappings[slot_name] = selected_model

        # Update display - FBList requires removeAt then insert
        self.mapping_list.Items.removeAt(slot_index)
        self.mapping_list.Items.insert(slot_index, f"{slot_name}: {selected_model.Name}")

        # Restore selection
        self.mapping_list.ItemIndex = slot_index

        print(f"[Character Mapper] Successfully mapped {slot_name} -> {selected_model.LongName}")

    def OnClearMapping(self, control, event):
        """Clear all bone mappings"""
        for i, (slot_name, _) in enumerate(CHARACTER_SLOTS):
            self.bone_mappings[slot_name] = None
            # Update display - FBList requires removeAt then insert
            self.mapping_list.Items.removeAt(i)
            self.mapping_list.Items.insert(i, f"{slot_name}: <None>")

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
            for slot_name, _ in CHARACTER_SLOTS:
                model = self.bone_mappings.get(slot_name)
                if model:
                    # Use the model object directly (no need to search)
                    self.character.SetCharacterizeOn(False)
                    prop_list = self.character.PropertyList.Find(slot_name + "Link")
                    if prop_list:
                        prop_list.append(model)
                        print(f"[Character Mapper] Linked {slot_name} -> {model.Name}")
                    else:
                        print(f"[Character Mapper WARNING] Could not find property {slot_name}Link")

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

        # Save model names, not objects
        for slot_name, model in self.bone_mappings.items():
            if model:
                preset_data["mappings"][slot_name] = model.LongName

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

            # Find models by name and map them
            for slot_name, bone_name in preset_data.get("mappings", {}).items():
                if slot_name in self.bone_mappings:
                    # Find the model in the scene
                    model = self._find_model_by_name(bone_name)
                    if model:
                        self.bone_mappings[slot_name] = model

                        # Update display
                        for i, (s_name, _) in enumerate(CHARACTER_SLOTS):
                            if s_name == slot_name:
                                self.mapping_list.Items.removeAt(i)
                                self.mapping_list.Items.insert(i, f"{slot_name}: {model.Name}")
                                break
                    else:
                        print(f"[Character Mapper WARNING] Model '{bone_name}' not found in scene")

            FBMessageBox("Preset Loaded", f"Preset '{preset_name}' loaded successfully!", "OK")
            print(f"[Character Mapper] Loaded preset: {preset_file}")

        except Exception as e:
            FBMessageBox("Error", f"Failed to load preset:\n{str(e)}", "OK")
            logger.error(f"Failed to load preset: {str(e)}")

    def _find_model_by_name(self, name):
        """Find a model by its LongName in the scene"""
        for model in self.all_models:
            if model.LongName == name:
                return model
        return None

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

                # Find models by name and map them
                for slot_name, bone_name in preset_data.get("mappings", {}).items():
                    if slot_name in self.bone_mappings:
                        # Find the model in the scene
                        model = self._find_model_by_name(bone_name)
                        if model:
                            self.bone_mappings[slot_name] = model

                            # Update display
                            for i, (s_name, _) in enumerate(CHARACTER_SLOTS):
                                if s_name == slot_name:
                                    self.mapping_list.Items.removeAt(i)
                                    self.mapping_list.Items.insert(i, f"{slot_name}: {model.Name}")
                                    break
                        else:
                            print(f"[Character Mapper WARNING] Model '{bone_name}' not found in scene")

                FBMessageBox(
                    "Import Successful",
                    f"Preset '{preset_name}' imported and loaded!",
                    "OK"
                )
                print(f"[Character Mapper] Imported preset from: {import_path}")

            except Exception as e:
                FBMessageBox("Error", f"Failed to import preset:\n{str(e)}", "OK")
                logger.error(f"Failed to import preset: {str(e)}")
