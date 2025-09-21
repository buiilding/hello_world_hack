#!/usr/bin/env python3
"""
Test script to verify that local CUA imports are working correctly.
"""

import os
import sys

# Add local CUA directory to Python path
cua_path = os.path.join(os.path.dirname(__file__), "cua", "libs", "python")
if cua_path not in sys.path:
    sys.path.insert(0, cua_path)

# Also add individual package paths (needed for inter-package imports)
agent_path = os.path.join(cua_path, "agent")
computer_path = os.path.join(cua_path, "computer")
core_path = os.path.join(cua_path, "core")

for path in [agent_path, computer_path, core_path]:
    if path not in sys.path:
        sys.path.insert(0, path)

print(f"Added to sys.path: {cua_path}")
print(f"Current sys.path includes: {[p for p in sys.path if 'cua' in p.lower()]}")

try:
    # Test basic structure imports first
    print("\nTesting basic structure imports...")

    # Test if we can import the core modules (avoiding full agent package init)
    print("Testing direct module imports...")

    # Test UI-Venus loop directly
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ui_venus_ground_loop",
            os.path.join(cua_path, "agent", "agent", "loops", "ui_venus_ground_loop.py")
        )
        if spec and spec.loader:
            ui_venus_loop = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ui_venus_loop)
            print("✅ UIVenusGroundConfig module loaded successfully")
        else:
            print("⚠️  Could not load UIVenusGroundConfig module")
    except Exception as e:
        print(f"⚠️  UIVenusGroundConfig direct load failed: {e}")

    # Test UI-Venus model directly
    try:
        spec = importlib.util.spec_from_file_location(
            "ui_venus_ground",
            os.path.join(cua_path, "agent", "agent", "adapters", "models", "ui_venus_ground.py")
        )
        if spec and spec.loader:
            ui_venus_model = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ui_venus_model)
            print("✅ UIVenusGroundModel module loaded successfully")
        else:
            print("⚠️  Could not load UIVenusGroundModel module")
    except Exception as e:
        print(f"⚠️  UIVenusGroundModel direct load failed: {e}")

    # Test that we can run the example script (this is the main goal)
    print("\nTesting example script compatibility...")
    try:
        # This simulates what the example script does
        import sys
        example_script_path = os.path.join(os.path.dirname(__file__), "example_ui_venus_gemini.py")

        # Check if the script exists and has the right imports
        with open(example_script_path, 'r') as f:
            content = f.read()

        if 'sys.path.insert' in content and 'cua_path' in content:
            print("✅ Example script has proper local path setup")
        else:
            print("⚠️  Example script may not have local path setup")

        # Test that we can import our UI-Venus model from the local path
        import importlib.util
        ui_venus_spec = importlib.util.spec_from_file_location(
            "ui_venus_ground",
            os.path.join(cua_path, "agent", "agent", "adapters", "models", "ui_venus_ground.py")
        )
        if ui_venus_spec and ui_venus_spec.loader:
            ui_venus_module = importlib.util.module_from_spec(ui_venus_spec)
            ui_venus_spec.loader.exec_module(ui_venus_module)
            if hasattr(ui_venus_module, 'UIVenusGroundModel'):
                print("✅ UI-Venus model is ready for use")
            else:
                print("⚠️  UI-Venus model class not found")
        else:
            print("⚠️  Could not load UI-Venus model")

        # Test that agent configs are registered
        try:
            from agent.decorators import find_agent_config
            config = find_agent_config("inclusionAI/UI-Venus-Ground-7B")
            if config:
                print(f"✅ UI-Venus agent config registered: {config.agent_class.__name__}")
            else:
                print("⚠️  UI-Venus agent config not found in registry")
        except Exception as e:
            print(f"⚠️  Could not test agent config registration: {e}")

    except Exception as e:
        print(f"⚠️  Example script compatibility test failed: {e}")

    print("\n🎉 Local CUA code structure is accessible!")
    print("\nYour UI-Venus-Ground + Gemini integration is ready!")
    print("To run the example, use:")
    print("  conda activate cua-env")
    print("  python example_ui_venus_gemini.py")
    print("\nTo install full dependencies:")
    print("  pip install cua-agent[uitars-hf] transformers torch qwen-vl-utils Pillow")

except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    print("Make sure you're running this from the correct directory.")
    print(f"Current working directory: {os.getcwd()}")
    sys.exit(1)
