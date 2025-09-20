#!/usr/bin/env python3
"""
Comprehensive Grounding Model Tester

This script allows you to test all available grounding models interactively.
You can input element descriptions and see the predicted coordinates from different models.
"""

import asyncio
import os
import sys
import base64
import time
from typing import List, Dict, Any, Optional, Tuple

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
from agent import ComputerAgent

# Define all available grounding models
GROUNDING_MODELS = {
    # UI-Venus Models
    "UI-Venus-7B": "inclusionAI/UI-Venus-Ground-7B",
    
    # UI-TARS Models
    "UI-TARS-1.5-7B": "huggingface-local/ByteDance-Seed/UI-TARS-1.5-7B",
    
    # OpenCUA Models
    "OpenCUA-7B": "huggingface-local/xlangai/OpenCUA-7B",
    "OpenCUA-32B": "huggingface-local/xlangai/OpenCUA-32B",
    
    # GTA1 Models
    "GTA1-7B": "huggingface-local/HelloKKMe/GTA1-7B",
    "GTA1-32B": "huggingface-local/HelloKKMe/GTA1-32B",
    "GTA1-72B": "huggingface-local/HelloKKMe/GTA1-72B",
    
    # Holo Models
    "Holo1.5-3B": "huggingface-local/Hcompany/Holo1.5-3B",
    "Holo1.5-7B": "huggingface-local/Hcompany/Holo1.5-7B",
    "Holo1.5-72B": "huggingface-local/Hcompany/Holo1.5-72B",
    
    # InternVL Models
    "InternVL3.5-1B": "huggingface-local/OpenGVLab/InternVL3_5-1B",
    "InternVL3.5-2B": "huggingface-local/OpenGVLab/InternVL3_5-2B",
    "InternVL3.5-4B": "huggingface-local/OpenGVLab/InternVL3_5-4B",
    "InternVL3.5-8B": "huggingface-local/OpenGVLab/InternVL3_5-8B",
    
    # Composed Models (Grounding + Thinking)
    "UI-Venus+Gemini": "inclusionAI/UI-Venus-Ground-7B+gemini/gemini-2.0-flash",
    "UI-Venus+Claude": "inclusionAI/UI-Venus-Ground-7B+anthropic/claude-3-5-sonnet-20241022",
    "GTA1+Gemini": "huggingface-local/HelloKKMe/GTA1-7B+gemini/gemini-2.0-flash",
    
    # API-based Models (require API keys)
    "Claude-4.1": "claude-opus-4-1-20250805",
    "Claude-4": "claude-sonnet-4-20250514",
    "Claude-3.7": "claude-3-7-sonnet-20250219",
    "Claude-3.5": "claude-3-5-sonnet-20241022",
    "OpenAI-Preview": "computer-use-preview",
}

class GroundingModelTester:
    def __init__(self):
        self.computer_instance = None
        self.loaded_models = {}
        self.screenshot_b64 = None
        
    async def setup(self):
        """Setup the computer and take initial screenshot."""
        print("📦 Setting up Docker computer...")
        self.computer_instance = Computer(
            os_type="linux",
            provider_type=VMProviderType.DOCKER,
            name="cua-grounding-test-all",
            image="trycua/cua-ubuntu:latest",
        )
        await self.computer_instance.run()
        
        print("📸 Taking initial screenshot...")
        screenshot_bytes = await self.computer_instance.interface.screenshot()
        self.screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        print(f"✅ Screenshot taken (size: {len(self.screenshot_b64)} chars)")
        
    async def load_model(self, model_name: str, model_id: str) -> Optional[ComputerAgent]:
        """Load a specific grounding model."""
        if model_name in self.loaded_models:
            return self.loaded_models[model_name]
            
        try:
            print(f"🤖 Loading {model_name}...")
            start_time = time.time()
            
            # Create ComputerAgent with the model
            agent = ComputerAgent(
                model=model_id,
                tools=[self.computer_instance],
                verbosity=0,  # Suppress verbose output
            )
            
            # Test if the model supports click prediction
            capabilities = agent.get_capabilities()
            if "click" not in capabilities:
                print(f"❌ {model_name} does not support click prediction")
                return None
                
            load_time = time.time() - start_time
            print(f"✅ {model_name} loaded in {load_time:.2f}s")
            
            self.loaded_models[model_name] = agent
            return agent
            
        except Exception as e:
            print(f"❌ Failed to load {model_name}: {e}")
            return None
    
    async def test_model(self, model_name: str, model_id: str, instruction: str) -> Optional[Tuple[int, int]]:
        """Test a specific model with an instruction."""
        agent = await self.load_model(model_name, model_id)
        if not agent:
            return None
            
        try:
            start_time = time.time()
            coords = await agent.predict_click(
                instruction=instruction,
                image_b64=self.screenshot_b64
            )
            prediction_time = time.time() - start_time
            
            if coords:
                print(f"✅ {model_name}: ({coords[0]}, {coords[1]}) in {prediction_time:.2f}s")
                return coords
            else:
                print(f"❌ {model_name}: Failed to predict in {prediction_time:.2f}s")
                return None
                
        except Exception as e:
            print(f"❌ {model_name}: Error - {e}")
            return None
    
    async def test_all_models(self, instruction: str):
        """Test all available models with the same instruction."""
        print(f"\n🔍 Testing all models with: '{instruction}'")
        print("=" * 60)
        
        results = {}
        
        for model_name, model_id in GROUNDING_MODELS.items():
            coords = await self.test_model(model_name, model_id, instruction)
            results[model_name] = coords
            
        # Summary
        print(f"\n📊 Results Summary for '{instruction}':")
        print("-" * 40)
        successful = 0
        for model_name, coords in results.items():
            if coords:
                print(f"✅ {model_name}: ({coords[0]}, {coords[1]})")
                successful += 1
            else:
                print(f"❌ {model_name}: Failed")
        
        print(f"\n📈 Success rate: {successful}/{len(GROUNDING_MODELS)} ({successful/len(GROUNDING_MODELS)*100:.1f}%)")
        
        return results
    
    async def interactive_mode(self):
        """Run interactive testing mode."""
        print("🎯 Interactive Grounding Model Tester")
        print("=" * 50)
        print("\nCommands:")
        print("  - Type any element description to test all models")
        print("  - Type 'model <name>' to test specific model")
        print("  - Type 'screenshot' to take a new screenshot")
        print("  - Type 'list' to see available models")
        print("  - Type 'quit' or 'exit' to stop")
        print("  - Type 'help' for more commands")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n🎯 Enter element description (or command): ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                elif user_input.lower() == 'help':
                    print("\n📖 Available commands:")
                    print("  <description> - Test all models with this description")
                    print("  model <name> - Test specific model (e.g., 'model UI-Venus-7B')")
                    print("  screenshot - Take a new screenshot")
                    print("  list - Show all available models")
                    print("  quit/exit/q - Exit the program")
                    print("  help - Show this help message")
                    continue
                elif user_input.lower() == 'list':
                    print("\n📋 Available Models:")
                    for i, (name, model_id) in enumerate(GROUNDING_MODELS.items(), 1):
                        print(f"  {i:2d}. {name}")
                    continue
                elif user_input.lower() == 'screenshot':
                    print("📸 Taking new screenshot...")
                    screenshot_bytes = await self.computer_instance.interface.screenshot()
                    self.screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    print(f"✅ New screenshot taken (size: {len(self.screenshot_b64)} chars)")
                    continue
                elif user_input.lower().startswith('model '):
                    model_name = user_input[6:].strip()
                    if model_name in GROUNDING_MODELS:
                        model_id = GROUNDING_MODELS[model_name]
                        instruction = input("Enter element description: ").strip()
                        if instruction:
                            await self.test_model(model_name, model_id, instruction)
                    else:
                        print(f"❌ Model '{model_name}' not found. Use 'list' to see available models.")
                    continue
                
                # Test all models with the instruction
                await self.test_all_models(user_input)
                    
            except KeyboardInterrupt:
                print("\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue

async def main():
    """Main function to run the comprehensive grounding model tester."""
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY environment variable not set.")
        print("   Some models (like Gemini-based ones) require this API key.")
        print("   You can still test local models without it.")
        
        proceed = input("Continue anyway? (y/n): ").strip().lower()
        if proceed not in ['y', 'yes']:
            return

    tester = GroundingModelTester()
    
    try:
        await tester.setup()
        await tester.interactive_mode()
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        raise
    finally:
        if tester.computer_instance:
            # await tester.computer_instance.stop()
            print("\n🧹 Computer connection closed")

if __name__ == "__main__":
    asyncio.run(main())
