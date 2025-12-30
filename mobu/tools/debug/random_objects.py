"""
Random Objects Generator - Debug Tool
Generates random markers and nulls for testing constraints and other tools
"""

import random
from pyfbsdk import (
    FBModelMarker, FBModelNull, FBVector3d, FBSystem, FBMessageBox
)
from core.logger import logger

TOOL_NAME = "Random Objects Generator"


def execute(control, event):
    """Generate random markers and nulls for testing"""
    try:
        # Configuration
        num_objects = 10
        position_range = 200  # Units from origin
        marker_size = 10.0
        null_size = 20.0

        created_objects = []

        print(f"[Random Objects] Generating {num_objects} random objects...")

        for i in range(num_objects):
            # Randomly choose object type (markers or nulls with different looks)
            obj_type = random.choice(['marker', 'null_cube', 'null_sphere', 'null_cross'])

            # Create object based on type
            if obj_type == 'marker':
                obj = FBModelMarker(f"DebugMarker_{i+1}")
                obj.Size = marker_size
                obj.Look = random.choice([0, 1, 2, 3, 4])  # Different marker styles
            elif obj_type == 'null_cube':
                obj = FBModelNull(f"DebugNull_Cube_{i+1}")
                obj.Size = null_size
                obj.Look = 0  # Cube look
            elif obj_type == 'null_sphere':
                obj = FBModelNull(f"DebugNull_Sphere_{i+1}")
                obj.Size = null_size
                obj.Look = 1  # Sphere look
            else:  # null_cross
                obj = FBModelNull(f"DebugNull_Cross_{i+1}")
                obj.Size = null_size
                obj.Look = 2  # Cross look

            # Set random position
            x = random.uniform(-position_range, position_range)
            y = random.uniform(0, position_range * 1.5)  # Keep above ground
            z = random.uniform(-position_range, position_range)
            obj.Translation = FBVector3d(x, y, z)

            # Set random rotation
            rx = random.uniform(0, 360)
            ry = random.uniform(0, 360)
            rz = random.uniform(0, 360)
            obj.Rotation = FBVector3d(rx, ry, rz)

            # Random color
            r = random.uniform(0.3, 1.0)
            g = random.uniform(0.3, 1.0)
            b = random.uniform(0.3, 1.0)
            obj.Color = FBVector3d(r, g, b)

            obj.Show = True
            created_objects.append(obj)

            print(f"[Random Objects]   Created {obj_type}: {obj.Name} at ({x:.1f}, {y:.1f}, {z:.1f})")

        # Create a null to group them
        group_null = FBModelNull("DebugObjects_Group")
        group_null.Show = True

        for obj in created_objects:
            obj.Parent = group_null

        print(f"[Random Objects] Created {len(created_objects)} objects")
        logger.info(f"Generated {len(created_objects)} random debug objects")

        FBMessageBox(
            "Objects Created",
            f"Generated {len(created_objects)} random objects!\n\n"
            f"Objects are grouped under: {group_null.Name}\n\n"
            f"Types: Markers and Nulls (Cube, Sphere, Cross)\n"
            f"Range: {position_range} units from origin",
            "OK"
        )

    except Exception as e:
        error_msg = f"Failed to generate random objects: {str(e)}"
        print(f"[Random Objects ERROR] {error_msg}")
        logger.error(error_msg)
        import traceback
        traceback.print_exc()

        FBMessageBox(
            "Error",
            f"Failed to generate objects:\n{str(e)}",
            "OK"
        )
