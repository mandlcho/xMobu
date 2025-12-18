# Character Presets

This directory contains character mapping presets for the Character Mapper tool.

## Preset Format

Character presets are JSON files with the following structure:

```json
{
  "name": "CharacterName",
  "version": "1.0",
  "description": "Optional description",
  "mappings": {
    "Hips": "BoneNameInScene",
    "Spine": "Spine_Bone",
    "LeftArm": "L_Arm",
    ...
  }
}
```

## Available Bone Slots

### Required (Minimum for Characterization)
- **Hips** - Root of the skeleton
- **LeftUpLeg** - Left thigh
- **RightUpLeg** - Right thigh
- **Spine** - Lower spine

### Core Skeleton
- **Reference** - Scene reference (usually root)
- **Spine1, Spine2, Spine3** - Upper spine sections
- **Neck** - Neck bone
- **Head** - Head bone

### Arms
- **LeftShoulder / RightShoulder** - Shoulder/clavicle
- **LeftArm / RightArm** - Upper arm
- **LeftForeArm / RightForeArm** - Lower arm/forearm
- **LeftHand / RightHand** - Hand

### Legs
- **LeftUpLeg / RightUpLeg** - Upper leg/thigh
- **LeftLeg / RightLeg** - Lower leg/shin
- **LeftFoot / RightFoot** - Foot

## Using Presets

### In the Character Mapper Tool:

1. **Save Preset:**
   - Map bones visually in the tool
   - Enter preset name
   - Click "Save Preset"

2. **Load Preset:**
   - Enter preset name
   - Click "Load Preset"
   - Mappings appear in the UI

3. **Export/Import:**
   - Export: Share preset as external file
   - Import: Load preset from external file

### Naming Conventions

Bone names in the preset should match the **exact names** or **LongName paths** of bones in your MotionBuilder scene.

Examples:
- Simple: `"Hips": "Hips"`
- With namespace: `"Hips": "Character:Hips"`
- Full path: `"Hips": "Root/Skeleton/Hips"`

## Creating Presets

### Option 1: Use the Tool
1. Open Character Mapper (xMobu > Rigging > Character Mapper)
2. Map bones visually
3. Save as preset

### Option 2: Manual Creation
1. Create a `.json` file in this directory
2. Follow the format above
3. Use exact bone names from your rig

### Option 3: Copy and Modify
1. Copy `Example_Biped.json`
2. Rename it
3. Edit bone names to match your rig

## Tips

- **Consistent naming**: Use a consistent naming convention across your rigs
- **Share presets**: Export and share presets with your team
- **Version control**: Commit presets to git for team collaboration
- **Backup**: Presets are automatically saved here, but export important ones

## Common Naming Patterns

### Pattern 1: Standard
```
Hips, Spine, Spine1, LeftArm, LeftForeArm, LeftHand...
```

### Pattern 2: With Prefixes
```
Root, Spine_01, Spine_02, L_UpperArm, L_LowerArm, L_Hand...
```

### Pattern 3: Namespaced
```
Character:Hips, Character:Spine, Character:L_Arm...
```

The preset system works with any naming pattern - just use the exact names from your scene!
