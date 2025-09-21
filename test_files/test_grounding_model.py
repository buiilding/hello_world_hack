#!/usr/bin/env python3
"""
Interactive Grounding Model Tester

This script allows you to test the UI-Venus grounding model interactively.
You can input element descriptions and see the predicted coordinates.
"""

import asyncio
import os
import sys
import base64
from typing import List, Dict, Any, Optional

# Add local CUA directory to Python path (for development)
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

# Import CUA components
from computer import Computer, VMProviderType
from agent.adapters.models.ui_venus_ground import UIVenusGroundModel

async def main():
    """Main function to run the interactive grounding model tester."""
    print("🎯 Interactive Grounding Model Tester")
    print("=" * 50)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY environment variable not set.")
        return

    computer_instance = None
    grounding_model = None
    
    try:
        print("📦 Setting up Docker computer...")
        computer_instance = Computer(
            os_type="linux",
            provider_type=VMProviderType.DOCKER,
            name="cua-grounding-test",
            image="trycua/cua-ubuntu:latest",
        )
        await computer_instance.run()
        
        print("🤖 Loading UI-Venus grounding model...")
        grounding_model = UIVenusGroundModel(
            model_name="inclusionAI/UI-Venus-Ground-7B",
            # quantization_bits=8
        )
        
        print("✅ Setup complete! Starting interactive mode...")
        print("\nCommands:")
        print("  - Type any element description to get coordinates")
        print("  - Type 'screenshot' to take a new screenshot")
        print("  - Type 'quit' or 'exit' to stop")
        print("  - Type 'help' for more commands")
        print("-" * 50)
        
        # Take initial screenshot
        print("📸 Taking initial screenshot...")
        screenshot_bytes = await computer_instance.interface.screenshot()
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        print(f"✅ Screenshot taken (size: {len(screenshot_b64)} chars)")
        
        # Interactive loop
        while True:
            try:
                # Get user input
                user_input = input("\n🎯 Enter element description (or command): ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                elif user_input.lower() == 'help':
                    print("\n📖 Available commands:")
                    print("  screenshot - Take a new screenshot")
                    print("  quit/exit/q - Exit the program")
                    print("  help - Show this help message")
                    print("  Any other text - Predict coordinates for that element")
                    continue
                elif user_input.lower() == 'screenshot':
                    print("📸 Taking new screenshot...")
                    screenshot_bytes = await computer_instance.interface.screenshot()
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    print(f"✅ New screenshot taken (size: {len(screenshot_b64)} chars)")
                    continue
                
                # Predict coordinates
                print(f"🔍 Predicting coordinates for: '{user_input}'")
                print("⏳ Processing...")
                
                coords = grounding_model.predict_click(
                    image_b64=screenshot_b64,
                    instruction=user_input
                )
                
                if coords:
                    x, y = coords
                    print(f"✅ Predicted coordinates: ({x}, {y})")
                    
                    # Ask if user wants to click
                    click_choice = input("🖱️  Do you want to click at these coordinates? (y/n): ").strip().lower()
                    if click_choice in ['y', 'yes']:
                        print(f"🖱️  Clicking at ({x}, {y})...")
                        await computer_instance.interface.left_click(x, y)
                        print("✅ Click executed!")
                        
                        # Take new screenshot after click
                        print("📸 Taking screenshot after click...")
                        screenshot_bytes = await computer_instance.interface.screenshot()
                        screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                        print("✅ New screenshot taken")
                else:
                    print("❌ Failed to predict coordinates")
                    
            except KeyboardInterrupt:
                print("\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
                
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        raise
    finally:
        if computer_instance:
            # await computer_instance.stop()
            print("\n🧹 Computer connection closed")

if __name__ == "__main__":
    asyncio.run(main())
