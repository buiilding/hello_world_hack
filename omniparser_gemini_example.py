#!/usr/bin/env python3
"""
Omniparser + Gemini Integration Example

This example demonstrates how to use the omniparser with Gemini models in different configurations:
1. Simple omniparser + Gemini 1.5 Pro
2. Omniparser with Gemini 2.0 Flash
3. Omniparser + Gemini with custom instructions

The omniparser allows you to use Gemini models for computer automation tasks:
- Thinking models: For high-level planning and decision making
- Direct interaction: With computer interfaces through screenshots
"""

import asyncio
import os
import sys
import logging
import subprocess
from typing import List, Dict, Any
from pathlib import Path

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

class OmniparserDebugCallback(AsyncCallbackHandler):
    """Callback to capture and display omniparser model interactions"""

    async def on_llm_start(self, messages):
        """Called before LLM processing"""
        print("\n🤖 === OMNIPARSER MODEL INPUT ===")
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
        print("🤖 === END OMNIPARSER MODEL INPUT ===\n")
        return messages

    async def on_llm_end(self, messages):
        """Called after LLM processing"""
        print("\n🧠 === OMNIPARSER MODEL OUTPUT ===")
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
        print("🧠 === END OMNIPARSER MODEL OUTPUT ===\n")
        return messages

def cleanup_docker_containers():
    """Clean up any existing omniparser containers and any containers using port 8000"""
    try:
        # Stop and remove any existing omniparser containers
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=omniparser-", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            containers = result.stdout.strip().split('\n')
            for container in containers:
                if container and container.strip():
                    print(f"🧹 Cleaning up existing container: {container}")
                    subprocess.run(["docker", "stop", container], timeout=10, capture_output=True)
                    subprocess.run(["docker", "rm", container], timeout=10, capture_output=True)
        
        # Also check for any containers using port 8000
        port_result = subprocess.run(
            ["docker", "ps", "--filter", "publish=8000", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10
        )
        if port_result.returncode == 0 and port_result.stdout.strip():
            port_containers = port_result.stdout.strip().split('\n')
            for container in port_containers:
                if container and container.strip():
                    print(f"🧹 Stopping container using port 8000: {container}")
                    subprocess.run(["docker", "stop", container], timeout=10, capture_output=True)
                    
    except Exception as e:
        print(f"⚠️  Warning: Could not cleanup containers: {e}")

async def setup_computer(example_name="demo"):
    """Setup and return a computer instance"""
    print("📦 Setting up Docker computer...")
    
    # Use unique names to avoid conflicts
    import random
    import time
    port_offset = random.randint(1000, 9999)
    container_name = f"omniparser-{example_name}-{port_offset}"
    
    # Wait a bit to ensure any previous containers are fully cleaned up
    await asyncio.sleep(1)
    
    computer = Computer(
        os_type="linux",
        provider_type=VMProviderType.DOCKER,
        name=container_name,
        image="trycua/cua-ubuntu:latest",
    )
    await computer.run()
    return computer

async def run_omniparser_gemini_example():
    """Example 1: Simple omniparser + Gemini"""
    print("\n🚀 Example 1: Simple Omniparser + Gemini 1.5 Pro")
    print("=" * 60)
    
    computer = await setup_computer("example1")
    
    try:
        # Create agent with omniparser + Gemini
        agent = ComputerAgent(
            model="omniparser+gemini/gemini-2.5-flash",
            tools=[computer],
            trajectory_dir="omniparser_trajectories",
            only_n_most_recent_images=3,
            verbosity=logging.INFO,
            callbacks=[OmniparserDebugCallback()]
        )
        
        # Simple task
        task = "Take a screenshot and tell me what you see on the desktop"
        
        print(f"📋 Task: {task}")
        async for result in agent.run(task, stream=True):
            for item in result.get("output", []):
                if item.get('type') == 'message':
                    content = item.get('content', [])
                    if isinstance(content, list) and content:
                        for part in content:
                            if part.get('type') == 'output_text':
                                print(f"💬 Response: {part.get('text', '')}")
        
        print("✅ Example 1 completed!")
        
    finally:
        await computer.stop()


async def run_gemini_flash_example():
    """Example 2: Omniparser with Gemini 2.0 Flash"""
    print("\n⚡ Example 2: Omniparser with Gemini 2.0 Flash")
    print("=" * 60)
    
    computer = await setup_computer("example2")
    
    try:
        # Use Gemini 2.0 Flash
        model_name = "gemini/gemini-2.0-flash-exp"
        
        print(f"🔄 Testing with: {model_name}")
        
        agent = ComputerAgent(
            model=f"omniparser+{model_name}",
            tools=[computer],
            trajectory_dir="gemini_flash_trajectories",
            only_n_most_recent_images=3,
            verbosity=logging.INFO,
            callbacks=[OmniparserDebugCallback()]
        )
        
        # Test task
        task = "Take a screenshot and describe what you see on the desktop"
        
        print(f"📋 Task: {task}")
        async for result in agent.run(task, stream=True):
            for item in result.get("output", []):
                if item.get('type') == 'message':
                    content = item.get('content', [])
                    if isinstance(content, list) and content:
                        for part in content:
                            if part.get('type') == 'output_text':
                                print(f"💬 {model_name} response: {part.get('text', '')}")
                elif item.get('type') == 'computer_call':
                    action = item.get('action', {})
                    print(f"🖱️  Computer action: {action.get('type', 'unknown')}")
        
        print(f"✅ {model_name} test completed!")
        
    finally:
        await computer.stop()

async def run_custom_instructions_example():
    """Example 3: Omniparser + Gemini with custom instructions"""
    print("\n📝 Example 3: Omniparser + Gemini with Custom Instructions")
    print("=" * 65)
    
    computer = await setup_computer("example3")
    
    try:
        # Custom instructions for the agent
        custom_instructions = """
        You are an expert computer automation assistant using omniparser with Gemini.
        
        Your capabilities:
        - You can see and interact with computer interfaces through screenshots
        - You use a grounding model to detect UI elements and a thinking model for planning
        - You can click, type, scroll, and navigate through applications
        
        Guidelines:
        - Always describe UI elements clearly when interacting with them
        - Take screenshots when you need to see the current state
        - Think step-by-step about complex tasks
        - Provide clear feedback about what you're doing
        
        Available actions:
        - click: Click on a described element
        - double_click: Double-click on a described element  
        - type: Type text into a field
        - screenshot: Take a screenshot (done automatically)
        - scroll: Scroll in a direction
        - wait: Wait for the interface to update
        """
        
        agent = ComputerAgent(
            model="omniparser+gemini/gemini-2.5-flash",
            tools=[computer],
            instructions=custom_instructions,
            trajectory_dir="custom_instructions_trajectories",
            only_n_most_recent_images=3,
            verbosity=logging.INFO,
            callbacks=[OmniparserDebugCallback()]
        )
        
        # Multi-step task
        tasks = [
            "Take a screenshot and describe what you see",
            "Look for any web browser icons on the desktop",
            "If you find a browser, click on it to open it"
        ]
        
        for i, task in enumerate(tasks, 1):
            print(f"\n📋 Task {i}/{len(tasks)}: {task}")
            
            async for result in agent.run(task, stream=True):
                for item in result.get("output", []):
                    if item.get('type') == 'message':
                        content = item.get('content', [])
                        if isinstance(content, list) and content:
                            for part in content:
                                if part.get('type') == 'output_text':
                                    print(f"💬 Response: {part.get('text', '')}")
                    elif item.get('type') == 'computer_call':
                        action = item.get('action', {})
                        print(f"🖱️  Action: {action.get('type', 'unknown')}")
            
            print(f"✅ Task {i} completed!")
        
        print("✅ Example 3 completed!")
        
    finally:
        await computer.stop()

async def main():
    """Main function to run all examples"""
    print("🚀 Omniparser + Gemini Integration Examples")
    print("=" * 50)
    
    # Check for required API keys
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY environment variable not set")
        print("Please set your Google API key: export GOOGLE_API_KEY=your_key_here")
        return
    
    print(f"✅ Google API key found: {os.getenv('GOOGLE_API_KEY')[:10]}...")
    
    # Clean up any existing containers first
    cleanup_docker_containers()
    
    try:
        # Run examples with delays between them
        await run_omniparser_gemini_example()
        await asyncio.sleep(2)  # Wait between examples
        
        await run_gemini_flash_example()
        await asyncio.sleep(2)  # Wait between examples
        
        await run_custom_instructions_example()
        
        print("\n🎉 All examples completed successfully!")
        print("\n📁 Trajectory files saved to:")
        print("  - omniparser_trajectories/")
        print("  - gemini_flash_trajectories/")
        print("  - custom_instructions_trajectories/")
        print("\n🌐 View trajectories at: https://trycua.com/trajectory-viewer")
        
    except Exception as e:
        logger.error(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Final cleanup
        cleanup_docker_containers()

if __name__ == "__main__":
    asyncio.run(main())
