#!/usr/bin/env python3
"""
CUA Example: Using UI-Venus-Ground-7B + Gemini for Composed Grounded Agent

This example demonstrates how to use the composed grounded configuration with:
- UI-Venus-Ground-7B as the grounding model (for element detection)
- Gemini 1.5 Pro as the thinking/planning model

The composed grounded approach works in two stages:
1. Grounding model: Converts element descriptions to coordinates
2. Thinking model: Makes high-level decisions and plans actions
"""

import asyncio
import os
import sys
import logging
from typing import List, Dict, Any

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
from agent import ComputerAgent
from computer import Computer, VMProviderType
from agent.callbacks import AsyncCallbackHandler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelDebugCallback(AsyncCallbackHandler):
    """Callback to capture and display model inputs/outputs"""

    async def on_llm_start(self, messages):
        """Called before LLM processing"""
        print("\n🤖 === THINKING MODEL INPUT ===")
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if isinstance(content, list):
                # Handle structured content (like with images)
                for j, part in enumerate(content):
                    if part.get('type') == 'text':
                        print(f"  {i}.{j} [{role}]: {part.get('text', '')[:200]}...")
                    elif part.get('type') == 'image_url':
                        print(f"  {i}.{j} [{role}]: [SCREENSHOT IMAGE]")
            else:
                print(f"  {i} [{role}]: {str(content)[:200]}...")
        print("🤖 === END THINKING MODEL INPUT ===\n")
        return messages

    async def on_llm_end(self, messages):
        """Called after LLM processing"""
        print("\n🧠 === THINKING MODEL OUTPUT ===")
        for i, msg in enumerate(messages):
            msg_type = msg.get('type', 'unknown')
            if msg_type == 'message':
                content = msg.get('content', '')
                print(f"  {i} [{msg_type}]: {content}")
            elif msg_type == 'function_call':
                print(f"  {i} [{msg_type}]: Tool call detected")
                print(f"    Function: {msg.get('name')}")
                print(f"    Arguments: {msg.get('arguments')}")
            elif msg_type == 'computer_call':
                print(f"  {i} [{msg_type}]: Computer call detected")
                action = msg.get('action', {})
                print(f"    Action: {action}")
            else:
                print(f"  {i} [{msg_type}]: {str(msg)[:200]}...")
        print("🧠 === END THINKING MODEL OUTPUT ===\n")
        return messages

async def main():
    """Run the UI-Venus-Ground + Gemini example."""

    print("🚀 Starting CUA with UI-Venus-Ground-7B + Gemini 1.5 Pro")
    print("=" * 60)

    # Check for required API keys
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY environment variable not set")
        print("Please set your Google API key: export GOOGLE_API_KEY=your_key_here")
        return

    try:
        # Setup Docker computer
        print("📦 Setting up Docker computer...")
        computer = Computer(
            os_type="linux",
            provider_type=VMProviderType.DOCKER,
            name="cua-demo",
            image="trycua/cua-ubuntu:latest",
        )
        await computer.run()

        # Create ComputerAgent with composed grounded config
        print("🤖 Creating ComputerAgent with UI-Venus-Ground-7B + Gemini 1.5 Pro...")

        # Model configuration: grounding_model+thinking_model
        # Use LM Studio for grounding and Gemini for thinking.
        # Configure LM Studio settings as variables below:
        
        # LM Studio Configuration
        LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
        LMSTUDIO_MODEL = "UI-Venus-Ground-7B.Q8_0"  # Model name as shown in LM Studio
        
        # Set environment variables for the LM Studio adapter
        os.environ["LMSTUDIO_BASE_URL"] = LMSTUDIO_BASE_URL
        os.environ["LMSTUDIO_MODEL"] = LMSTUDIO_MODEL
        
        model = f"inclusionAI/UI-Venus-Ground-7B+gemini/gemini-1.5-pro"

        debug_callback = ModelDebugCallback()

        # Instructions for the thinking model
        instructions = """
        You are an AI assistant that controls a computer to help users complete tasks.

        You can see the computer screen through screenshots and interact with UI elements by describing them.
        When you want to interact with an element, use descriptions like:
        - "the blue login button"
        - "the search text field at the top"
        - "the firefox icon on the dock"
        - "the close button in the top-right corner"

        Available actions:
        - click: Click on a described element
        - double_click: Double-click on a described element
        - type: Type text into a field
        - screenshot: Take a screenshot (done automatically)
        - scroll: Scroll in a direction
        - wait: Wait for the interface to update

        Always think step-by-step about what you need to do to complete the user's request.
        """

        agent = ComputerAgent(
            model=model,  # Composed model: grounding+thinking
            tools=[computer],
            instructions=instructions,
            callbacks=[debug_callback],
            only_n_most_recent_images=3,  # Keep last 3 screenshots for context
            verbosity=logging.INFO,
            trajectory_dir="cua_trajectories",
            use_prompt_caching=True,
            quantization_bits=8,
        )

        # Example tasks to demonstrate the agent capabilities
        tasks = [
            "Click on firefox, you might have to double click",
        ]

        # Conversation history
        history: List[Dict[str, Any]] = []

        print("\n🎯 Starting agent tasks...")
        print("-" * 40)

        for i, task in enumerate(tasks, 1):
            print(f"\n📋 Task {i}/{len(tasks)}: {task}")

            # Add user message to history
            history.append({"role": "user", "content": task})

            # Run agent with conversation history
            try:
                async for result in agent.run(history, stream=True):
                    # Debug: Print raw result structure
                    print("\n🔍 Agent Result:")
                    print(f"  Keys: {list(result.keys())}")
                    print(f"  Output count: {len(result.get('output', []))}")

                    # Add agent outputs to history
                    history.extend(result.get("output", []))

                    # Print detailed information about each output item
                    for idx, item in enumerate(result["output"]):
                        print(f"  📝 Output {idx}: {item.get('type', 'unknown')}")
                        if item.get('type') == 'message':
                            content = item.get('content', [])
                            if isinstance(content, list) and content:
                                for part in content:
                                    if part.get('type') == 'output_text':
                                        text = part.get('text', '')
                                        print(f"    💬 Message: {text[:200]}{'...' if len(text) > 200 else ''}")
                        elif item.get('type') == 'computer_call':
                            action = item.get('action', {})
                            print(f"    🖱️  Computer action: {action.get('type', 'unknown')}")
                            if 'element_description' in action:
                                print(f"    🎯 Element: '{action['element_description']}'")
                            elif 'x' in action and 'y' in action:
                                print(f"    📍 Coordinates: ({action['x']}, {action['y']})")
                            if 'text' in action:
                                print(f"    ⌨️  Text to type: '{action['text'][:50]}{'...' if len(action['text']) > 50 else ''}'")
                        elif item.get('type') == 'computer_call_output':
                            output = item.get('output', {})
                            if isinstance(output, dict):
                                if output.get('type') == 'input_image':
                                    print(f"    📸 Screenshot taken")
                                else:
                                    print(f"    📄 Output: {output}")
                            else:
                                print(f"    📄 Output: {str(output)[:200]}{'...' if len(str(output)) > 200 else ''}")

                    # Print usage information if available
                    if 'usage' in result:
                        usage = result['usage']
                        print(f"  📊 Usage: {usage.get('total_tokens', 'unknown')} tokens")
                        if 'response_cost' in usage:
                            print(f"  💰 Cost: ${usage['response_cost']:.6f}")

                print(f"✅ Task {i} completed!")

            except Exception as task_error:
                print(f"❌ Task {i} failed: {task_error}")
                import traceback
                print("🔍 Detailed error traceback:")
                traceback.print_exc()
                print("📋 Current history state:")
                for idx, msg in enumerate(history[-5:]):  # Show last 5 messages
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    if isinstance(content, str):
                        content_preview = content[:100] + "..." if len(content) > 100 else content
                    else:
                        content_preview = f"[structured content with {len(content) if isinstance(content, list) else 'unknown'} items]"
                    print(f"  {len(history)-5+idx}: {role} - {content_preview}")
                # Continue with next task
                continue

    except Exception as e:
        logger.error(f"❌ Error running example: {e}")
        raise

    finally:
        # Clean up
        try:
            if 'computer' in locals():
                await computer.close()
                print("\n🧹 Computer connection closed")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
