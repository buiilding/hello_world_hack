#!/usr/bin/env python3
"""
Simple GGUF grounding smoke test (no Gemini):
- Starts CUA computer (Docker), takes a screenshot via CUA
- Loads UI-Venus-Ground GGUF via llama-cpp-python
- Runs hard-coded or provided instructions on the live screenshot
- Prints raw bbox-derived center coordinates

Usage examples:
  python test_ui_venus_ground_gguf.py \
    --gguf /abs/path/UI-Venus-Ground-7B.Q8_0.gguf \
    --instruction "Firefox Web Browser"

  python test_ui_venus_ground_gguf.py \
    --gguf /abs/path/UI-Venus-Ground-7B.Q8_0.gguf \
    --instruction "Firefox Web Browser" \
    --instruction "search bar"
"""

import os
import sys
import base64
import asyncio
import argparse


def add_cua_paths() -> None:
    base_dir = os.path.dirname(__file__)
    cua_path = os.path.join(base_dir, "cua", "libs", "python")
    # Add common subpackages for robustness (matches example script)
    agent_path = os.path.join(cua_path, "agent")
    computer_path = os.path.join(cua_path, "computer")
    core_path = os.path.join(cua_path, "core")
    # Ensure 'agent' resolves to the subpackage (agent/agent) by prioritizing agent_path
    for path in [agent_path, cua_path, computer_path, core_path]:
        if path not in sys.path:
            sys.path.insert(0, path)


async def main() -> int:
    add_cua_paths()

    # Lazy import after sys.path setup
    from agent.adapters.models.lm_studio import LMStudioModel  # type: ignore
    from agent.computers.cua import cuaComputerHandler  # type: ignore
    from computer import Computer, VMProviderType  # type: ignore

    # Direct configuration variables (no CLI args)
    LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
    LMSTUDIO_MODEL = "UI-Venus-Ground-7B.Q8_0"  # Model name as shown in LM Studio
    INSTRUCTIONS = ["Firefox Web Browser"]  # Test instructions
    
    # Set environment variables for the LM Studio adapter
    os.environ["LMSTUDIO_BASE_URL"] = LMSTUDIO_BASE_URL
    os.environ["LMSTUDIO_MODEL"] = LMSTUDIO_MODEL
    
    instructions = INSTRUCTIONS

    print("🧪 LM Studio Grounding Smoke Test")
    print("-" * 40)
    print(f"LM Studio URL: {LMSTUDIO_BASE_URL}")
    print(f"LM Studio model: {LMSTUDIO_MODEL}")
    print(f"Instructions: {instructions}")

    # Start computer and take screenshot
    computer = Computer(
        os_type="linux",
        provider_type=VMProviderType.DOCKER,
        name="cua-demo",
        image="trycua/cua-ubuntu:latest",
    )

    try:
        print("📦 Starting CUA computer (Docker)...")
        await computer.run()
        print("📸 Taking screenshot via CUA...")
        handler = cuaComputerHandler(computer)
        await handler._initialize()
        image_b64 = await handler.screenshot()
        if not image_b64:
            print("❌ Failed to capture screenshot from CUA")
            return 1

        # Prepare model
        model = LMStudioModel(model_name=LMSTUDIO_MODEL)

        # Run tests
        for desc in instructions:
            print(f"\n🎯 Instruction: '{desc}'")
            coords = model.predict_click(image_b64=image_b64, instruction=desc)
            if coords:
                print(f"✅ Predicted center coordinates: {coords}")
            else:
                print("❌ No coordinates predicted")

    finally:
        try:
            await computer.close()
            print("🧹 Computer connection closed")
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))


