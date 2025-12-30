"""
Quick test script for Random Objects Generator
Run this in MotionBuilder's Python Console to test the tool
"""

try:
    from mobu.tools.debug.random_objects import execute
    execute(None, None)
    print("Random Objects Generator executed successfully!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
