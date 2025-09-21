#!/usr/bin/env python3
"""
Simple HF-based UI-Venus grounding smoke test (no Gemini):
- Starts CUA computer (Docker), takes a screenshot via CUA
- Loads UI-Venus-Ground (HF) via transformers/torch
- Runs hard-coded or provided instructions on the live screenshot
- Prints predicted center coordinates

Usage examples:
  python test_ui_venus_ground_hf.py \
    --hf_model inclusionAI/UI-Venus-Ground-7B \
    --instruction "Firefox Web Browser"

  python test_ui_venus_ground_hf.py \
    --hf_model inclusionAI/UI-Venus-Ground-7B \
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
    agent_path = os.path.join(cua_path, "agent")
    computer_path = os.path.join(cua_path, "computer")
    core_path = os.path.join(cua_path, "core")
    for path in [agent_path, cua_path, computer_path, core_path]:
        if path not in sys.path:
            sys.path.insert(0, path)


async def main() -> int:
    add_cua_paths()

    # Lazy import after sys.path setup
    from agent.adapters.models.ui_venus_ground import UIVenusGroundModel  # type: ignore
    from agent.computers.cua import cuaComputerHandler  # type: ignore
    from computer import Computer, VMProviderType  # type: ignore

    # Direct configuration variables (no CLI args)
    HF_MODEL = "inclusionAI/UI-Venus-Ground-7B"  # Hugging Face model ID
    INSTRUCTIONS = ["Applications"]  # Test instructions
    
    instructions = INSTRUCTIONS

    print("🧪 HF Grounding Smoke Test")
    print("-" * 40)
    print(f"HF model: {HF_MODEL}")
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

        # Prepare HF model
        try:
            model = UIVenusGroundModel(model_name=HF_MODEL, quantization_bits=8)
        except Exception as e:
            print("❌ Failed to initialize UIVenusGroundModel (HF):", e)
            print("   Ensure you have: pip install transformers torch qwen-vl-utils Pillow")
            return 1

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


