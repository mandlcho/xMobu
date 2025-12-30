"""
Menu builder for MotionBuilder integration
"""

from pyfbsdk import FBMenuManager, FBGenericMenu
from core.logger import logger
from core.config import config
import importlib
import sys
from pathlib import Path


class MenuBuilder:
    """Builds and manages the xMobu menu in MotionBuilder"""

    def __init__(self):
        self.menu_manager = FBMenuManager()
        self.menu_name = config.get('mobu.menu_name', 'xMobu')
        self.main_menu = None

    def build_menu(self, force_rebuild=False):
        """Build the complete xMobu menu structure"""
        print(f"[xMobu] Building '{self.menu_name}' menu...")
        logger.info("Building xMobu menu...")

        # Check if menu already exists
        print(f"[xMobu] Checking for existing '{self.menu_name}' menu...")
        existing_menu = self.menu_manager.GetMenu(self.menu_name)

        if existing_menu and not force_rebuild:
            print(f"[xMobu] Menu already exists - skipping rebuild")
            print(f"[xMobu] NOTE: MotionBuilder doesn't support deleting menus")
            print(f"[xMobu] NOTE: To see menu changes, restart MotionBuilder")
            print(f"[xMobu] NOTE: Tool code changes are still reloaded!")
            logger.info("Skipping menu rebuild - menu already exists")
            return

        if existing_menu and force_rebuild:
            print(f"[xMobu] WARNING: Menu already exists but rebuild forced")
            print(f"[xMobu] WARNING: This will create duplicate menu items!")

        # Create menu
        print(f"[xMobu] Creating '{self.menu_name}' menu...")
        self.main_menu = self.menu_manager.InsertLast(None, self.menu_name)
        print(f"[xMobu] Main menu '{self.menu_name}' created")

        # Get enabled categories from config
        categories = config.get('mobu.tool_categories', [])
        print(f"[xMobu] Found {len(categories)} total categories")

        enabled_categories = [c for c in categories if c.get('enabled', True)]
        print(f"[xMobu] {len(enabled_categories)} categories enabled")

        # Build category submenus
        for category in categories:
            if category.get('enabled', True):
                print(f"[xMobu] Building category: {category['name']}")
                self._build_category_menu(category['name'])

        # Add separator and utilities
        self.menu_manager.InsertLast(self.menu_name, "")  # Separator
        print("[xMobu] Adding utility menu items...")
        self._add_utility_items()

        print(f"[xMobu] Menu '{self.menu_name}' built successfully")
        logger.info("xMobu menu built successfully")


    def _build_category_menu(self, category_name):
        """Build a submenu for a specific tool category"""
        print(f"[xMobu]   Creating submenu: {category_name}")
        # InsertLast expects (parent_menu_name, item_name) - both strings
        category_menu = self.menu_manager.InsertLast(self.menu_name, category_name)

        # Dynamically load tools from the category folder
        tools = self._discover_tools(category_name)

        # Build the category menu path for sub-items
        category_menu_path = f"{self.menu_name}/{category_name}"

        # Store callbacks by menu item name for this category
        category_callbacks = {}

        if not tools:
            # Add placeholder if no tools found
            print(f"[xMobu]   No tools found for: {category_name}")
            item_name = f"No {category_name} tools found"
            self.menu_manager.InsertLast(category_menu_path, item_name)
            category_callbacks[item_name] = self._no_tools_callback
        else:
            print(f"[xMobu]   Found {len(tools)} tool(s) in {category_name}")
            # Add each tool to the menu
            for tool in tools:
                self.menu_manager.InsertLast(category_menu_path, tool['name'])
                category_callbacks[tool['name']] = tool['callback']
                print(f"[xMobu]     - {tool['name']}")

        # Get the category menu and register a single callback handler
        menu_obj = self.menu_manager.GetMenu(category_menu_path)
        if menu_obj:
            # Create a closure that captures the category callbacks
            def menu_handler(control, event):
                callback = category_callbacks.get(event.Name)
                if callback:
                    try:
                        callback(control, event)
                    except Exception as e:
                        print(f"[xMobu ERROR] Tool '{event.Name}' failed: {str(e)}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"[xMobu] No handler for menu item: {event.Name}")

            menu_obj.OnMenuActivate.Add(menu_handler)
            print(f"[xMobu]   Registered menu handler for {category_name}")

    def _discover_tools(self, category_name):
        """
        Discover and load tools from a category folder

        Returns:
            list: List of tool dictionaries with 'name' and 'callback'
        """
        tools = []
        category_folder = category_name.lower().replace(' ', '_')

        # Handle special case for "Unreal Engine" category
        if category_folder == 'unreal_engine':
            category_folder = 'unreal'

        tools_path = Path(__file__).parent / 'tools' / category_folder

        print(f"[xMobu]   Scanning for tools in: {category_folder}/")

        if not tools_path.exists():
            print(f"[xMobu]   WARNING: Tools folder not found: {tools_path}")
            logger.warning(f"Tools folder not found: {tools_path}")
            return tools

        # Look for Python files in the category folder
        for tool_file in tools_path.glob('*.py'):
            if tool_file.name.startswith('_'):
                continue

            try:
                # Import the tool module
                module_name = f"mobu.tools.{category_folder}.{tool_file.stem}"
                if module_name in sys.modules:
                    # Reload if already imported
                    module = importlib.reload(sys.modules[module_name])
                else:
                    module = importlib.import_module(module_name)

                # Look for tool classes or functions
                if hasattr(module, 'TOOL_NAME') and hasattr(module, 'execute'):
                    tools.append({
                        'name': module.TOOL_NAME,
                        'callback': module.execute
                    })
                    logger.debug(f"Loaded tool: {module.TOOL_NAME}")
                else:
                    print(f"[xMobu]   WARNING: {tool_file.name} missing TOOL_NAME or execute")

            except Exception as e:
                print(f"[xMobu]   ERROR: Failed to load {tool_file.name}: {str(e)}")
                logger.error(f"Failed to load tool from {tool_file.name}: {str(e)}")

        return tools

    def _add_utility_items(self):
        """Add utility menu items (settings, reload, about, etc.)"""
        # Build utility callbacks dictionary
        utility_callbacks = {}

        # Settings
        self.menu_manager.InsertLast(self.menu_name, "Settings...")
        utility_callbacks["Settings..."] = self._open_settings

        # Settings (Qt Designer version)
        self.menu_manager.InsertLast(self.menu_name, "Settings (Qt)...")
        utility_callbacks["Settings (Qt)..."] = self._open_settings_qt

        # Constraint Manager (Qt Designer version)
        self.menu_manager.InsertLast(self.menu_name, "Constraint Manager (Qt)...")
        utility_callbacks["Constraint Manager (Qt)..."] = self._open_constraint_manager_qt

        # Reload
        self.menu_manager.InsertLast(self.menu_name, "Reload xMobu")
        utility_callbacks["Reload xMobu"] = self._reload_xmobu

        # Separator
        self.menu_manager.InsertLast(self.menu_name, "")

        # About
        self.menu_manager.InsertLast(self.menu_name, "About xMobu")
        utility_callbacks["About xMobu"] = self._show_about

        # Register callback handler for main menu
        main_menu_obj = self.menu_manager.GetMenu(self.menu_name)
        if main_menu_obj:
            def utility_handler(control, event):
                callback = utility_callbacks.get(event.Name)
                if callback:
                    try:
                        callback(control, event)
                    except Exception as e:
                        print(f"[xMobu ERROR] Utility '{event.Name}' failed: {str(e)}")
                        import traceback
                        traceback.print_exc()

            main_menu_obj.OnMenuActivate.Add(utility_handler)
            print("[xMobu] Registered utility menu handler")

    def _no_tools_callback(self, control, event):
        """Callback for placeholder menu items"""
        logger.info("No tools available in this category yet")

    def _open_settings(self, control, event):
        """Open settings dialog"""
        try:
            from mobu.tools.pipeline.settings import execute
            execute(control, event)
        except Exception as e:
            from pyfbsdk import FBMessageBox
            print(f"[xMobu ERROR] Failed to open settings: {str(e)}")
            FBMessageBox(
                "Error",
                f"Failed to open settings:\n{str(e)}",
                "OK"
            )

    def _open_settings_qt(self, control, event):
        """Open Qt Designer settings dialog"""
        try:
            from mobu.tools.pipeline.settings_qt import execute
            execute(control, event)
        except Exception as e:
            from pyfbsdk import FBMessageBox
            print(f"[xMobu ERROR] Failed to open Qt settings: {str(e)}")
            import traceback
            traceback.print_exc()
            FBMessageBox(
                "Error",
                f"Failed to open Qt settings:\n{str(e)}",
                "OK"
            )

    def _open_constraint_manager_qt(self, control, event):
        """Open Qt Designer constraint manager dialog"""
        try:
            from mobu.tools.rigging.constraint_manager_qt import execute
            execute(control, event)
        except Exception as e:
            from pyfbsdk import FBMessageBox
            print(f"[xMobu ERROR] Failed to open Qt constraint manager: {str(e)}")
            import traceback
            traceback.print_exc()
            FBMessageBox(
                "Error",
                f"Failed to open Qt constraint manager:\n{str(e)}",
                "OK"
            )

    def _reload_xmobu(self, control, event):
        """Reload xMobu system"""
        print("[xMobu] ========================================")
        print("[xMobu] Reloading xMobu...")
        print("[xMobu] ========================================")
        logger.info("Reloading xMobu...")

        try:
            # Reload all xMobu modules in correct order
            print("[xMobu] Reloading core modules...")

            # Core modules
            import core.logger
            import core.config
            import core.decorators
            import core.utils
            importlib.reload(core.logger)
            importlib.reload(core.config)
            importlib.reload(core.decorators)
            importlib.reload(core.utils)
            print("[xMobu] Core modules reloaded")

            # Reload tool modules
            print("[xMobu] Reloading tool modules...")
            import mobu.tools.animation.keyframe_tools
            import mobu.tools.rigging.constraint_helper
            import mobu.tools.rigging.character_mapper
            import mobu.tools.pipeline.scene_manager
            import mobu.tools.pipeline.settings
            import mobu.tools.pipeline.settings_qt
            import mobu.tools.rigging.constraint_manager_qt
            import mobu.tools.unreal.content_browser

            importlib.reload(mobu.tools.animation.keyframe_tools)
            importlib.reload(mobu.tools.rigging.constraint_helper)
            importlib.reload(mobu.tools.rigging.character_mapper)
            importlib.reload(mobu.tools.rigging.constraint_manager_qt)
            importlib.reload(mobu.tools.pipeline.scene_manager)
            importlib.reload(mobu.tools.pipeline.settings)
            importlib.reload(mobu.tools.pipeline.settings_qt)
            importlib.reload(mobu.tools.unreal.content_browser)
            print("[xMobu] Tool modules reloaded")

            print("[xMobu] ========================================")
            print("[xMobu] Reload completed successfully!")
            print("[xMobu] ========================================")
            print("[xMobu] NOTE: Menu structure cannot be changed without restart")
            print("[xMobu] NOTE: Tool code changes are active - test your tools!")
            print("[xMobu] ========================================")

            from pyfbsdk import FBMessageBox
            FBMessageBox(
                "xMobu Reloaded",
                "Tool modules reloaded successfully!\n\n"
                "Tool code changes are now active.\n\n"
                "Note: Menu structure changes require\n"
                "restarting MotionBuilder (MotionBuilder API limitation).",
                "OK"
            )

        except Exception as e:
            print(f"[xMobu ERROR] Failed to reload: {str(e)}")
            logger.error(f"Failed to reload xMobu: {str(e)}")
            import traceback
            traceback.print_exc()

            from pyfbsdk import FBMessageBox
            FBMessageBox("xMobu Error", f"Failed to reload: {str(e)}\n\nCheck Python Console for details.", "OK")

    def _show_about(self, control, event):
        """Show about dialog"""
        from pyfbsdk import FBMessageBox
        from core import __version__

        about_text = f"""xMobu Pipeline Toolset
Version: {__version__}

A comprehensive pipeline toolset for MotionBuilder
with support for Animation, Rigging, Pipeline, and
Unreal Engine integration.

Visit github.com/yourorg/xMobu for more information.
"""
        FBMessageBox("About xMobu", about_text, "OK")
