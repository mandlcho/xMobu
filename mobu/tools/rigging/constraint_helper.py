"""
Constraint Manager Tool
Create and manage constraints easily in MotionBuilder
"""

from pyfbsdk import (
    FBTool, FBLayout, FBButton, FBLabel, FBList, FBEdit,
    FBAttachType, FBMessageBox, FBModelList, FBGetSelectedModels,
    FBSystem, FBFilePopup, FBFilePopupStyle, FBAddRegionParam,
    ShowTool, FBTextStyle, FBListStyle, FBSlider, FBConstraintManager,
    FBTextJustify
)
from core.logger import logger
from pathlib import Path
import json

TOOL_NAME = "Constraint Manager"

# Global reference to the active tool instance
_active_tool_instance = None


class ConstraintManagerUI(FBTool):
    """Visual constraint management tool with preset functionality"""

    def __init__(self, name):
        FBTool.__init__(self, name)
        self.selected_objects = []
        self.constraint_sources = []
        self.constraint_target = None
        self.preset_path = self._get_preset_path()

        # Default constraint settings
        self.constraint_weight = 100.0
        self.constraint_snap = False

        self.BuildUI()
        self.RefreshSelection()

        print("[Constraint Manager] Tool initialized")

    def _get_preset_path(self):
        """Get the path to the presets directory"""
        root = Path(__file__).parent.parent.parent.parent
        preset_dir = root / "presets" / "constraints"
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
        x_right = FBAddRegionParam(350, FBAttachType.kFBAttachLeft, "")
        x_end = FBAddRegionParam(0, FBAttachType.kFBAttachRight, "")

        y_top = FBAddRegionParam(0, FBAttachType.kFBAttachTop, "")
        y_mid = FBAddRegionParam(-200, FBAttachType.kFBAttachBottom, "")
        y_bottom = FBAddRegionParam(0, FBAttachType.kFBAttachBottom, "")

        # Left panel - Constraint Creation
        creation_layout = FBLayout()
        main.AddRegion("creation", "creation", x_left, y_top, x_right, y_mid)
        main.SetControl("creation", creation_layout)

        # Right panel - Selection
        selection_layout = FBLayout()
        main.AddRegion("selection", "selection", x_right, y_top, x_end, y_mid)
        main.SetControl("selection", selection_layout)

        # Bottom panel - Presets
        presets_layout = FBLayout()
        main.AddRegion("presets", "presets", x_left, y_mid, x_end, y_bottom)
        main.SetControl("presets", presets_layout)

        # Build sub-panels
        self._build_creation_panel(creation_layout)
        self._build_selection_panel(selection_layout)
        self._build_presets_panel(presets_layout)

    def _build_creation_panel(self, layout):
        """Build the constraint creation panel"""
        # Title
        label = FBLabel()
        label.Caption = "Create Constraints"
        label.Style = FBTextStyle.kFBTextStyleBold

        x = FBAddRegionParam(5, FBAttachType.kFBAttachLeft, "")
        y = FBAddRegionParam(5, FBAttachType.kFBAttachTop, "")
        w = FBAddRegionParam(-5, FBAttachType.kFBAttachRight, "")
        h = FBAddRegionParam(25, FBAttachType.kFBAttachTop, "")

        layout.AddRegion("title", "title", x, y, w, h)
        layout.SetControl("title", label)

        # Constraint type buttons
        y_offset = 30
        button_height = 30
        spacing = 5

        # Parent Constraint
        parent_btn = FBButton()
        parent_btn.Caption = "Parent Constraint"
        parent_btn.OnClick.Add(self.OnCreateParentConstraint)

        y1 = FBAddRegionParam(y_offset, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(y_offset + button_height, FBAttachType.kFBAttachTop, "")
        layout.AddRegion("parent_btn", "parent_btn", x, y1, w, y2)
        layout.SetControl("parent_btn", parent_btn)
        y_offset += button_height + spacing

        # Position Constraint
        pos_btn = FBButton()
        pos_btn.Caption = "Position Constraint"
        pos_btn.OnClick.Add(self.OnCreatePositionConstraint)

        y1 = FBAddRegionParam(y_offset, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(y_offset + button_height, FBAttachType.kFBAttachTop, "")
        layout.AddRegion("pos_btn", "pos_btn", x, y1, w, y2)
        layout.SetControl("pos_btn", pos_btn)
        y_offset += button_height + spacing

        # Rotation Constraint
        rot_btn = FBButton()
        rot_btn.Caption = "Rotation Constraint"
        rot_btn.OnClick.Add(self.OnCreateRotationConstraint)

        y1 = FBAddRegionParam(y_offset, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(y_offset + button_height, FBAttachType.kFBAttachTop, "")
        layout.AddRegion("rot_btn", "rot_btn", x, y1, w, y2)
        layout.SetControl("rot_btn", rot_btn)
        y_offset += button_height + spacing

        # Aim Constraint
        aim_btn = FBButton()
        aim_btn.Caption = "Aim Constraint"
        aim_btn.OnClick.Add(self.OnCreateAimConstraint)

        y1 = FBAddRegionParam(y_offset, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(y_offset + button_height, FBAttachType.kFBAttachTop, "")
        layout.AddRegion("aim_btn", "aim_btn", x, y1, w, y2)
        layout.SetControl("aim_btn", aim_btn)
        y_offset += button_height + spacing

        # Relation Constraint
        rel_btn = FBButton()
        rel_btn.Caption = "Relation Constraint"
        rel_btn.OnClick.Add(self.OnCreateRelationConstraint)

        y1 = FBAddRegionParam(y_offset, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(y_offset + button_height, FBAttachType.kFBAttachTop, "")
        layout.AddRegion("rel_btn", "rel_btn", x, y1, w, y2)
        layout.SetControl("rel_btn", rel_btn)
        y_offset += button_height + spacing * 2

        # Weight slider
        weight_label = FBLabel()
        weight_label.Caption = "Constraint Weight:"

        y1 = FBAddRegionParam(y_offset, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(y_offset + 20, FBAttachType.kFBAttachTop, "")
        layout.AddRegion("weight_label", "weight_label", x, y1, w, y2)
        layout.SetControl("weight_label", weight_label)
        y_offset += 25

        self.weight_slider = FBSlider()
        self.weight_slider.Min = 0.0
        self.weight_slider.Max = 100.0
        self.weight_slider.Value = self.constraint_weight
        self.weight_slider.OnChange.Add(self.OnWeightChanged)

        y1 = FBAddRegionParam(y_offset, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(y_offset + 20, FBAttachType.kFBAttachTop, "")
        layout.AddRegion("weight_slider", "weight_slider", x, y1, w, y2)
        layout.SetControl("weight_slider", self.weight_slider)
        y_offset += 25

        # Weight value display
        self.weight_value = FBLabel()
        self.weight_value.Caption = f"{self.constraint_weight:.1f}%"

        y1 = FBAddRegionParam(y_offset, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(y_offset + 20, FBAttachType.kFBAttachTop, "")
        layout.AddRegion("weight_value", "weight_value", x, y1, w, y2)
        layout.SetControl("weight_value", self.weight_value)
        y_offset += 30

        # Snap button
        snap_btn = FBButton()
        snap_btn.Caption = "Snap (Active)"
        snap_btn.OnClick.Add(self.OnSnapConstrainedObjects)

        y1 = FBAddRegionParam(y_offset, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(y_offset + button_height, FBAttachType.kFBAttachTop, "")
        layout.AddRegion("snap_btn", "snap_btn", x, y1, w, y2)
        layout.SetControl("snap_btn", snap_btn)

    def _build_selection_panel(self, layout):
        """Build the selection panel"""
        # Title
        label = FBLabel()
        label.Caption = "Selection"
        label.Style = FBTextStyle.kFBTextStyleBold

        x = FBAddRegionParam(5, FBAttachType.kFBAttachLeft, "")
        y = FBAddRegionParam(5, FBAttachType.kFBAttachTop, "")
        w = FBAddRegionParam(-5, FBAttachType.kFBAttachRight, "")
        h = FBAddRegionParam(25, FBAttachType.kFBAttachTop, "")

        layout.AddRegion("sel_title", "sel_title", x, y, w, h)
        layout.SetControl("sel_title", label)

        # Instructions
        info_label = FBLabel()
        info_label.Caption = "Select source(s) then target(s)"
        info_label.Justify = FBTextJustify.kFBTextJustifyCenter

        y1 = FBAddRegionParam(30, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(50, FBAttachType.kFBAttachTop, "")
        layout.AddRegion("info", "info", x, y1, w, y2)
        layout.SetControl("info", info_label)

        # Selected objects list
        sel_label = FBLabel()
        sel_label.Caption = "Selected Objects:"

        y1 = FBAddRegionParam(55, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(75, FBAttachType.kFBAttachTop, "")
        layout.AddRegion("sel_label", "sel_label", x, y1, w, y2)
        layout.SetControl("sel_label", sel_label)

        self.selection_list = FBList()
        self.selection_list.Style = FBListStyle.kFBVerticalList
        self.selection_list.MultiSelect = False

        y1 = FBAddRegionParam(80, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(-90, FBAttachType.kFBAttachBottom, "")
        layout.AddRegion("sel_list", "sel_list", x, y1, w, y2)
        layout.SetControl("sel_list", self.selection_list)

        # Buttons
        y1 = FBAddRegionParam(-85, FBAttachType.kFBAttachBottom, "")
        y2 = FBAddRegionParam(-55, FBAttachType.kFBAttachBottom, "")

        refresh_btn = FBButton()
        refresh_btn.Caption = "Refresh Selection"
        refresh_btn.OnClick.Add(self.OnRefreshSelection)
        layout.AddRegion("refresh_sel", "refresh_sel", x, y1, w, y2)
        layout.SetControl("refresh_sel", refresh_btn)

        y1 = FBAddRegionParam(-50, FBAttachType.kFBAttachBottom, "")
        y2 = FBAddRegionParam(-20, FBAttachType.kFBAttachBottom, "")

        set_source_btn = FBButton()
        set_source_btn.Caption = "Set as Source(s)"
        set_source_btn.OnClick.Add(self.OnSetSources)
        layout.AddRegion("set_source", "set_source", x, y1, w, y2)
        layout.SetControl("set_source", set_source_btn)

    def _build_presets_panel(self, layout):
        """Build the presets panel"""
        # Title
        label = FBLabel()
        label.Caption = "Constraint Templates"
        label.Style = FBTextStyle.kFBTextStyleBold

        x = FBAddRegionParam(5, FBAttachType.kFBAttachLeft, "")
        y = FBAddRegionParam(5, FBAttachType.kFBAttachTop, "")
        w = FBAddRegionParam(-5, FBAttachType.kFBAttachRight, "")
        h = FBAddRegionParam(25, FBAttachType.kFBAttachTop, "")

        layout.AddRegion("preset_title", "preset_title", x, y, w, h)
        layout.SetControl("preset_title", label)

        # Preset name
        y1 = FBAddRegionParam(30, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(50, FBAttachType.kFBAttachTop, "")

        name_label = FBLabel()
        name_label.Caption = "Template Name:"

        x_left = FBAddRegionParam(5, FBAttachType.kFBAttachLeft, "")
        x_mid = FBAddRegionParam(120, FBAttachType.kFBAttachLeft, "")
        x_right = FBAddRegionParam(-5, FBAttachType.kFBAttachRight, "")

        layout.AddRegion("name_label", "name_label", x_left, y1, x_mid, y2)
        layout.SetControl("name_label", name_label)

        self.preset_name = FBEdit()
        self.preset_name.Text = "MyConstraintSetup"
        layout.AddRegion("preset_name", "preset_name", x_mid, y1, x_right, y2)
        layout.SetControl("preset_name", self.preset_name)

        # Available presets list
        y1 = FBAddRegionParam(55, FBAttachType.kFBAttachTop, "")
        y2 = FBAddRegionParam(-55, FBAttachType.kFBAttachBottom, "")

        self.presets_list = FBList()
        self.presets_list.Style = FBListStyle.kFBVerticalList
        self.presets_list.MultiSelect = False
        self.presets_list.OnChange.Add(self.OnPresetSelected)

        layout.AddRegion("presets_list", "presets_list", x, y1, w, y2)
        layout.SetControl("presets_list", self.presets_list)

        # Load presets
        self.RefreshPresetsList()

        # Buttons row 1
        y1 = FBAddRegionParam(-50, FBAttachType.kFBAttachBottom, "")
        y2 = FBAddRegionParam(-25, FBAttachType.kFBAttachBottom, "")

        x_btn1 = FBAddRegionParam(5, FBAttachType.kFBAttachLeft, "")
        x_btn2 = FBAddRegionParam(0, FBAttachType.kFBAttachNone, "")
        x_btn3 = FBAddRegionParam(-5, FBAttachType.kFBAttachRight, "")

        save_btn = FBButton()
        save_btn.Caption = "Save Template"
        save_btn.OnClick.Add(self.OnSavePreset)
        layout.AddRegion("save_preset", "save_preset", x_btn1, y1, x_btn2, y2)
        layout.SetControl("save_preset", save_btn)

        load_btn = FBButton()
        load_btn.Caption = "Apply Template"
        load_btn.OnClick.Add(self.OnLoadPreset)
        layout.AddRegion("load_preset", "load_preset", x_btn2, y1, x_btn3, y2)
        layout.SetControl("load_preset", load_btn)

        # Buttons row 2
        y1 = FBAddRegionParam(-20, FBAttachType.kFBAttachBottom, "")
        y2 = FBAddRegionParam(0, FBAttachType.kFBAttachBottom, "")

        delete_btn = FBButton()
        delete_btn.Caption = "Delete Template"
        delete_btn.OnClick.Add(self.OnDeletePreset)
        layout.AddRegion("delete_preset", "delete_preset", x_btn1, y1, x_btn3, y2)
        layout.SetControl("delete_preset", delete_btn)

    def OnWeightChanged(self, control, event):
        """Update constraint weight value"""
        self.constraint_weight = self.weight_slider.Value
        self.weight_value.Caption = f"{self.constraint_weight:.1f}%"

    def RefreshSelection(self):
        """Refresh the selected objects list"""
        self.selected_objects = []

        # Clear list
        while len(self.selection_list.Items) > 0:
            self.selection_list.Items.removeAt(0)

        # Get selected models
        selected = FBModelList()
        FBGetSelectedModels(selected)

        for model in selected:
            self.selected_objects.append(model)
            self.selection_list.Items.append(model.Name)

        print(f"[Constraint Manager] Selected {len(self.selected_objects)} objects")

    def OnRefreshSelection(self, control, event):
        """Refresh button callback"""
        self.RefreshSelection()

    def OnSetSources(self, control, event):
        """Set selected objects as constraint sources"""
        if not self.selected_objects:
            FBMessageBox("No Selection", "Please select objects first", "OK")
            return

        self.constraint_sources = self.selected_objects[:]

        names = [obj.Name for obj in self.constraint_sources]
        FBMessageBox(
            "Sources Set",
            f"Set {len(self.constraint_sources)} source(s):\n" + "\n".join(names),
            "OK"
        )
        print(f"[Constraint Manager] Set {len(self.constraint_sources)} sources")

    def OnCreateParentConstraint(self, control, event):
        """Create parent constraint"""
        if not self._validate_constraint_setup():
            return

        try:
            for target in self.selected_objects:
                # Create constraint
                constraint = FBConstraintManager().TypeCreateConstraint("Parent/Child")
                if constraint:
                    constraint.Name = f"Parent_{target.Name}"
                    constraint.ReferenceAdd(0, target)  # Constrained object

                    # Add sources
                    for source in self.constraint_sources:
                        constraint.ReferenceAdd(1, source)  # Parent

                    constraint.Weight = self.constraint_weight
                    constraint.Active = True
                    constraint.Snap()

                    print(f"[Constraint Manager] Created parent constraint for {target.Name}")

            FBMessageBox("Success", f"Created {len(self.selected_objects)} parent constraint(s)", "OK")

        except Exception as e:
            logger.error(f"Failed to create parent constraint: {str(e)}")
            FBMessageBox("Error", f"Failed to create constraint:\n{str(e)}", "OK")

    def OnCreatePositionConstraint(self, control, event):
        """Create position constraint"""
        if not self._validate_constraint_setup():
            return

        try:
            for target in self.selected_objects:
                constraint = FBConstraintManager().TypeCreateConstraint("Position")
                if constraint:
                    constraint.Name = f"Position_{target.Name}"
                    constraint.ReferenceAdd(0, target)

                    for source in self.constraint_sources:
                        constraint.ReferenceAdd(1, source)

                    constraint.Weight = self.constraint_weight
                    constraint.Active = True
                    constraint.Snap()

                    print(f"[Constraint Manager] Created position constraint for {target.Name}")

            FBMessageBox("Success", f"Created {len(self.selected_objects)} position constraint(s)", "OK")

        except Exception as e:
            logger.error(f"Failed to create position constraint: {str(e)}")
            FBMessageBox("Error", f"Failed to create constraint:\n{str(e)}", "OK")

    def OnCreateRotationConstraint(self, control, event):
        """Create rotation constraint"""
        if not self._validate_constraint_setup():
            return

        try:
            for target in self.selected_objects:
                constraint = FBConstraintManager().TypeCreateConstraint("Rotation")
                if constraint:
                    constraint.Name = f"Rotation_{target.Name}"
                    constraint.ReferenceAdd(0, target)

                    for source in self.constraint_sources:
                        constraint.ReferenceAdd(1, source)

                    constraint.Weight = self.constraint_weight
                    constraint.Active = True
                    constraint.Snap()

                    print(f"[Constraint Manager] Created rotation constraint for {target.Name}")

            FBMessageBox("Success", f"Created {len(self.selected_objects)} rotation constraint(s)", "OK")

        except Exception as e:
            logger.error(f"Failed to create rotation constraint: {str(e)}")
            FBMessageBox("Error", f"Failed to create constraint:\n{str(e)}", "OK")

    def OnCreateAimConstraint(self, control, event):
        """Create aim constraint"""
        if not self._validate_constraint_setup():
            return

        try:
            for target in self.selected_objects:
                constraint = FBConstraintManager().TypeCreateConstraint("Aim")
                if constraint:
                    constraint.Name = f"Aim_{target.Name}"
                    constraint.ReferenceAdd(0, target)

                    for source in self.constraint_sources:
                        constraint.ReferenceAdd(1, source)

                    constraint.Weight = self.constraint_weight
                    constraint.Active = True
                    constraint.Snap()

                    print(f"[Constraint Manager] Created aim constraint for {target.Name}")

            FBMessageBox("Success", f"Created {len(self.selected_objects)} aim constraint(s)", "OK")

        except Exception as e:
            logger.error(f"Failed to create aim constraint: {str(e)}")
            FBMessageBox("Error", f"Failed to create constraint:\n{str(e)}", "OK")

    def OnCreateRelationConstraint(self, control, event):
        """Create relation constraint"""
        FBMessageBox(
            "Relation Constraint",
            "Relation constraints require custom setup.\n\n"
            "This will create a basic relation constraint.\n"
            "Use the Relations Editor to customize the expression.",
            "OK"
        )

        try:
            # Create a basic relation constraint
            constraint = FBConstraintManager().TypeCreateConstraint("Relation")
            if constraint:
                constraint.Name = "Relation_Custom"
                constraint.Active = True

                FBMessageBox(
                    "Success",
                    f"Created relation constraint: {constraint.Name}\n\n"
                    "Use the Relations Editor (Window > Relations) to set up expressions.",
                    "OK"
                )
                print(f"[Constraint Manager] Created relation constraint")

        except Exception as e:
            logger.error(f"Failed to create relation constraint: {str(e)}")
            FBMessageBox("Error", f"Failed to create constraint:\n{str(e)}", "OK")

    def OnSnapConstrainedObjects(self, control, event):
        """Snap all active constraints on selected objects"""
        if not self.selected_objects:
            FBMessageBox("No Selection", "Please select constrained objects", "OK")
            return

        try:
            snapped_count = 0
            for model in self.selected_objects:
                # Find all constraints on this object
                for constraint in FBSystem().Scene.Constraints:
                    if constraint.Active:
                        # Check if this model is constrained by this constraint
                        for i in range(constraint.ReferenceGroupGetCount(0)):
                            if constraint.ReferenceGet(0, i) == model:
                                constraint.Snap()
                                snapped_count += 1
                                break

            if snapped_count > 0:
                FBMessageBox("Success", f"Snapped {snapped_count} constraint(s)", "OK")
            else:
                FBMessageBox("Info", "No active constraints found on selected objects", "OK")

        except Exception as e:
            logger.error(f"Failed to snap constraints: {str(e)}")
            FBMessageBox("Error", f"Failed to snap constraints:\n{str(e)}", "OK")

    def _validate_constraint_setup(self):
        """Validate that we have source and target objects"""
        if not self.constraint_sources:
            FBMessageBox(
                "No Sources",
                "Please set source object(s) first:\n"
                "1. Select source object(s)\n"
                "2. Click 'Set as Source(s)'\n"
                "3. Select target object(s)\n"
                "4. Create constraint",
                "OK"
            )
            return False

        if not self.selected_objects:
            FBMessageBox(
                "No Targets",
                "Please select target object(s) to constrain",
                "OK"
            )
            return False

        return True

    def RefreshPresetsList(self):
        """Refresh the list of available presets"""
        # Clear list
        while len(self.presets_list.Items) > 0:
            self.presets_list.Items.removeAt(0)

        # Find all preset files
        if self.preset_path.exists():
            for preset_file in self.preset_path.glob("*.json"):
                self.presets_list.Items.append(preset_file.stem)

    def OnPresetSelected(self, control, event):
        """When a preset is selected, update the name field"""
        if self.presets_list.ItemIndex >= 0:
            preset_name = self.presets_list.Items[self.presets_list.ItemIndex]
            self.preset_name.Text = preset_name

    def OnSavePreset(self, control, event):
        """Save current constraint setup as a template"""
        preset_name = self.preset_name.Text or "ConstraintSetup"

        if not self.selected_objects:
            FBMessageBox("No Selection", "Please select objects with constraints to save", "OK")
            return

        try:
            preset_data = {
                "name": preset_name,
                "version": "1.0",
                "constraints": []
            }

            # Gather constraint information from selected objects
            for model in self.selected_objects:
                for constraint in FBSystem().Scene.Constraints:
                    # Check if this constraint affects this model
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
                        preset_data["constraints"].append(constraint_info)

            if not preset_data["constraints"]:
                FBMessageBox("No Constraints", "No constraints found on selected objects", "OK")
                return

            # Save to file
            preset_file = self.preset_path / f"{preset_name}.json"
            with open(preset_file, 'w') as f:
                json.dump(preset_data, f, indent=2)

            FBMessageBox(
                "Template Saved",
                f"Saved {len(preset_data['constraints'])} constraint(s) to:\n{preset_file}",
                "OK"
            )
            print(f"[Constraint Manager] Saved preset: {preset_file}")

            self.RefreshPresetsList()

        except Exception as e:
            logger.error(f"Failed to save preset: {str(e)}")
            FBMessageBox("Error", f"Failed to save template:\n{str(e)}", "OK")

    def OnLoadPreset(self, control, event):
        """Load and apply a constraint template"""
        preset_name = self.preset_name.Text or "ConstraintSetup"
        preset_file = self.preset_path / f"{preset_name}.json"

        if not preset_file.exists():
            FBMessageBox(
                "Template Not Found",
                f"Template '{preset_name}' not found in:\n{self.preset_path}",
                "OK"
            )
            return

        try:
            with open(preset_file, 'r') as f:
                preset_data = json.load(f)

            info = f"Template: {preset_data.get('name', 'Unknown')}\n"
            info += f"Constraints: {len(preset_data.get('constraints', []))}\n\n"

            for c in preset_data.get('constraints', []):
                info += f"- {c.get('type')} ({c.get('weight', 100)}%)\n"

            info += "\nNote: This shows template info.\n"
            info += "Create constraints manually using the buttons above."

            FBMessageBox("Template Info", info, "OK")

        except Exception as e:
            logger.error(f"Failed to load preset: {str(e)}")
            FBMessageBox("Error", f"Failed to load template:\n{str(e)}", "OK")

    def OnDeletePreset(self, control, event):
        """Delete a constraint template"""
        preset_name = self.preset_name.Text or "ConstraintSetup"
        preset_file = self.preset_path / f"{preset_name}.json"

        if not preset_file.exists():
            FBMessageBox("Template Not Found", f"Template '{preset_name}' not found", "OK")
            return

        # Confirm deletion
        result = FBMessageBox(
            "Confirm Delete",
            f"Delete template '{preset_name}'?",
            "Yes", "No"
        )

        if result == 1:  # Yes
            try:
                preset_file.unlink()
                FBMessageBox("Deleted", f"Template '{preset_name}' deleted", "OK")
                print(f"[Constraint Manager] Deleted preset: {preset_file}")
                self.RefreshPresetsList()

            except Exception as e:
                logger.error(f"Failed to delete preset: {str(e)}")
                FBMessageBox("Error", f"Failed to delete template:\n{str(e)}", "OK")


def execute(control, event):
    """Show the Constraint Manager tool"""
    global _active_tool_instance

    tool_name = "Constraint Manager"

    # Check if we already have an instance
    if _active_tool_instance is not None:
        print(f"[Constraint Manager] Instance already exists, destroying it...")
        try:
            # Try to destroy the tool using FBDestroy
            from pyfbsdk import FBDestroy
            FBDestroy(_active_tool_instance)
            print("[Constraint Manager] Previous instance destroyed")
        except Exception as e:
            print(f"[Constraint Manager] Could not destroy: {e}")
        finally:
            _active_tool_instance = None

    # Always create a fresh instance
    print("[Constraint Manager] Creating new instance...")
    tool = ConstraintManagerUI(tool_name)
    tool.StartSizeX = 750
    tool.StartSizeY = 600

    _active_tool_instance = tool

    ShowTool(tool)
    print("[Constraint Manager] Tool shown")
