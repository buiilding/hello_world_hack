# CUA with UI-Venus-Ground-7B + Gemini Setup Guide

This guide explains how to set up and use the Computer Use Agent (CUA) with a composed grounded configuration using UI-Venus-Ground-7B as the grounding model and Gemini as the thinking/planning model.

## Overview

The **composed grounded** approach splits the computer use task into two specialized models:

1. **Grounding Model (UI-Venus-Ground-7B)**: Converts natural language element descriptions (like "the blue login button") into precise screen coordinates
2. **Thinking Model (Gemini)**: Makes high-level decisions, plans actions, and generates element descriptions

## Architecture

```
User Request → Thinking Model (Gemini) → Element Description → Grounding Model (UI-Venus) → Coordinates → Computer Action
```

## Prerequisites

### System Requirements
- Python 3.10+
- Docker (for computer environment)
- CUDA-compatible GPU (recommended for UI-Venus model)
- ~16GB VRAM minimum for UI-Venus-7B

### Dependencies
```bash
# Install CUA agent
pip install cua-agent[uitars-hf]

# Additional dependencies for UI-Venus
pip install transformers torch qwen-vl-utils Pillow

# Optional: Pre-download the UI-Venus model (large, ~14GB)
# This will be downloaded automatically on first use, but you can pre-download:
python -c "from transformers import AutoModelForImageTextToText, AutoTokenizer, AutoProcessor; AutoModelForImageTextToText.from_pretrained('inclusionAI/UI-Venus-Ground-7B', torch_dtype='auto')"
```

### Development Setup (Using Local CUA Code)

If you want to use the local CUA code instead of the installed package:

**First, install dependencies:**
```bash
# Install required packages
pip install cua-agent[uitars-hf] transformers torch qwen-vl-utils Pillow

# Optional: Install other CUA packages if needed
pip install cua-computer cua-core
```

**Then choose one of these approaches:**

**Option 1: PYTHONPATH approach**
```bash
# Run the example script directly - it automatically adds the local path
python example_ui_venus_gemini.py
```

**Option 2: Shell script**
```bash
# Use the provided script
./run_example_local.sh
```

**Option 3: Editable installation**
```bash
# Install local packages in editable mode
./setup_local_dev.sh
# Now all Python scripts will use local CUA code
python example_ui_venus_gemini.py
```

**Option 4: Manual PYTHONPATH**
```bash
export PYTHONPATH="$(pwd)/cua/libs/python:$(pwd)/cua/libs/python/agent:$(pwd)/cua/libs/python/computer:$(pwd)/cua/libs/python/core:$PYTHONPATH"
python example_ui_venus_gemini.py
```

**Test setup:**
```bash
# Verify local imports are working
python test_local_imports.py
```

## Setup Instructions

### 1. API Keys
Set your API keys as environment variables:

```bash
export GOOGLE_API_KEY="your_google_api_key_here"
```

### 2. Model Configuration
The composed model uses the format: `grounding_model+thinking_model`

```python
# Direct specification - the system automatically detects UI-Venus models
model = "inclusionAI/UI-Venus-Ground-7B+gemini/gemini-1.5-pro"
```

### 3. Docker Setup
Ensure Docker is running and pull the CUA Ubuntu image:

```bash
docker pull trycua/cua-ubuntu:latest
```

## Usage Examples

### Basic Example

```python
import asyncio
from agent import ComputerAgent
from computer import Computer, VMProviderType

async def main():
    # Setup computer environment
    computer = Computer(
        os_type="linux",
        provider_type=VMProviderType.DOCKER,
        name="cua-demo",
        image="trycua/cua-ubuntu:latest",
    )
    await computer.run()

    # Create agent with composed grounded config
    agent = ComputerAgent(
        model="inclusionAI/UI-Venus-Ground-7B+gemini/gemini-1.5-pro",
        tools=[computer],
        instructions="You are a helpful computer assistant...",
    )

    # Run tasks
    history = [{"role": "user", "content": "Open Firefox and go to google.com"}]
    async for result in agent.run(history):
        print(result)

asyncio.run(main())
```

### Advanced Example with Callbacks

See `example_ui_venus_gemini.py` for a complete example with:
- Debug callbacks showing model inputs/outputs
- Multi-step task execution
- Error handling
- Proper cleanup

## How It Works

### 1. Initial Screenshot
The agent automatically takes a screenshot when no recent image is available.

### 2. Thinking Phase (Gemini)
Gemini receives the user request + screenshot and decides what actions to take. It outputs element descriptions like:
- "the firefox icon in the dock"
- "the google search box"

### 3. Grounding Phase (UI-Venus)
For each element description, UI-Venus analyzes the screenshot and returns bounding box coordinates `[x1,y1,x2,y2]`.

### 4. Coordinate Conversion
The system converts bounding boxes to click coordinates (center point of the box).

### 5. Action Execution
Coordinates are sent to the computer interface for execution.

## Model-Specific Details

### UI-Venus-Ground-7B
- **Purpose**: UI element grounding (description → coordinates)
- **Input**: Image + text instruction
- **Output**: Normalized bounding box `[x1,y1,x2,y2]`
- **Architecture**: Qwen2.5-VL based
- **Memory**: ~14GB VRAM required

### Gemini 1.5 Pro
- **Purpose**: High-level reasoning and planning
- **Input**: Conversation history + screenshots
- **Output**: Action plans with element descriptions
- **API**: Google AI API (requires GOOGLE_API_KEY)

## Troubleshooting

### Common Issues

1. **"Model not found" errors**
   - Ensure UI-Venus model name is correct: `inclusionAI/UI-Venus-Ground-7B`
   - Check internet connection for model download

2. **CUDA out of memory**
   - Reduce image resolution in UI-Venus model
   - Use smaller batch sizes
   - Consider CPU mode (slower but less memory)

3. **Gemini API errors**
   - Verify GOOGLE_API_KEY is set
   - Check API quota and billing status
   - Ensure correct model name: `gemini/gemini-1.5-pro`

4. **Docker issues**
   - Ensure Docker daemon is running
   - Check available disk space
   - Verify port 8006 is available

### Performance Tips

1. **Caching**: Enable prompt caching for repeated tasks
2. **Image Limits**: Use `only_n_most_recent_images=3` to reduce context size
3. **Model Selection**: Try `gemini/gemini-1.5-flash` for faster responses

## Customization

### Custom Instructions
Provide detailed instructions to Gemini about how to describe UI elements:

```python
instructions = """
You are a computer assistant. When referring to UI elements, use precise descriptions like:
- "the blue 'Sign In' button in the top right"
- "the search input field with placeholder 'Search...'"
- "the Firefox icon on the desktop"
- "the close button (X) in the window title bar"
"""
```

### Custom Grounding Models
To add your own grounding model:

1. Create a new model handler in `agent/adapters/models/`
2. Implement `predict_click(image_b64, instruction)` method
3. Update `agent/adapters/models/__init__.py` to register it
4. Use model name that triggers your handler

### Alternative Thinking Models
Replace Gemini with other LiteLLM-supported models:

```python
# OpenAI GPT-4
model = "inclusionAI/UI-Venus-Ground-7B+gpt-4"

# Anthropic Claude
model = "inclusionAI/UI-Venus-Ground-7B+claude-3-5-sonnet-20241022"

# Local models via Ollama
model = "inclusionAI/UI-Venus-Ground-7B+ollama/llama3.1"
```

## File Structure

```
cua/libs/python/agent/
├── agent.py                    # Main ComputerAgent class
├── loops/
│   ├── composed_grounded.py    # Composed grounded implementation
│   └── ui_venus_ground_loop.py # UI-Venus AsyncAgentConfig
├── adapters/
│   ├── models/
│   │   ├── ui_venus_ground.py  # UI-Venus model handler
│   │   └── __init__.py         # Model factory
│   └── huggingfacelocal_adapter.py  # HF model adapter
└── responses.py                # Message format conversions
```

## Contributing

To contribute improvements:

1. Test your changes with the example script
2. Add proper error handling
3. Update documentation
4. Consider performance implications

## References

- [CUA Documentation](https://docs.cua.computer/)
- [UI-Venus-Ground Model](https://huggingface.co/inclusionAI/UI-Venus-Ground-7B)
- [Gemini API](https://ai.google.dev/docs)
- [Qwen2.5-VL](https://github.com/QwenLM/Qwen2.5-VL)
