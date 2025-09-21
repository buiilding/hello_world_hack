"""
Composed-grounded agent loop implementation that combines grounding and thinking models.
Uses a two-stage approach: grounding model for element detection, thinking model for reasoning.
"""

import uuid
import asyncio
import json
import base64
from typing import Dict, List, Any, Optional, Tuple
from io import BytesIO
from PIL import Image
import litellm

from ..decorators import register_agent
from ..types import Messages, AgentResponse, Tools, AgentCapability
from ..loops.base import AsyncAgentConfig
from ..responses import (
    convert_computer_calls_xy2desc,
    convert_responses_items_to_completion_messages,
    convert_completion_messages_to_responses_items,
    convert_computer_calls_desc2xy,
    get_all_element_descriptions
)
from ..agent import find_agent_config

GROUNDED_COMPUTER_TOOL_SCHEMA = {
  "type": "function",
  "function": {
    "name": "computer",
    "description": "Control a computer by taking screenshots and interacting with UI elements. This tool uses element descriptions to locate and interact with UI elements on the screen (e.g., 'red submit button', 'search text field', 'hamburger menu icon', 'close button in top right corner').",
    "parameters": {
        "type": "object",
        "properties": {
        "action": {
            "type": "string",
            "enum": [
            "screenshot",
            "click",
            "double_click",
            "drag",
            "type",
            "keypress",
            "scroll",
            "move",
            "wait",
            "get_current_url",
            "get_dimensions",
            "get_environment"
            ],
            "description": "The action to perform (required for all actions)"
        },
        "element_description": {
            "type": "string",
            "description": "Description of the element to interact with (required for click, double_click, move, scroll actions)"
        },
        "start_element_description": {
            "type": "string",
            "description": "Description of the element to start dragging from (required for drag action)"
        },
        "end_element_description": {
            "type": "string",
            "description": "Description of the element to drag to (required for drag action)"
        },
        "text": {
            "type": "string",
            "description": "The text to type (required for type action)"
        },
        "keys": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Key(s) to press (required for keypress action)"
        },
        "button": {
            "type": "string",
            "enum": [
                "left",
                "right",
                "wheel",
                "back",
                "forward"
            ],
            "description": "The mouse button to use for click action (required for click and double_click action)",
        },
        "scroll_x": {
            "type": "integer",
            "description": "Horizontal scroll amount for scroll action (required for scroll action)",
        },
        "scroll_y": {
            "type": "integer",
            "description": "Vertical scroll amount for scroll action (required for scroll action)",
        },
        },
        "required": [
            "action"
        ]
    }
  }
}

def _prepare_tools_for_grounded(tool_schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prepare tools for grounded API format"""
    grounded_tools = []
    
    for schema in tool_schemas:
        if schema["type"] == "computer":
            grounded_tools.append(GROUNDED_COMPUTER_TOOL_SCHEMA)
        else:
            grounded_tools.append(schema)
    
    return grounded_tools

def get_last_image_b64(messages: List[Dict[str, Any]]) -> Optional[str]:
    """Get the last image from a list of messages, checking user messages, tool outputs, and computer call outputs."""
    for message in reversed(messages):
        # Check user messages with content lists (including the new format from CoAct-1)
        if message.get("role") == "user" and isinstance(message.get("content"), list):
            for content_item in reversed(message["content"]):
                if content_item.get("type") == "image_url":
                    image_url = content_item.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:image/png;base64,"):
                        return image_url.split(",", 1)[1]

        # Check computer call outputs (for tool results with images)
        elif message.get("type") == "computer_call_output" and isinstance(message.get("output"), dict):
            output = message["output"]
            if output.get("type") == "input_image":
                image_url = output.get("image_url", "")
                if image_url.startswith("data:image/png;base64,"):
                    return image_url.split(",", 1)[1]

        # Check function call outputs (for orchestrator results with multimodal content)
        elif message.get("type") == "function_call_output" and isinstance(message.get("output"), list):
            for content_item in reversed(message["output"]):
                if content_item.get("type") == "image_url":
                    image_url = content_item.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:image/png;base64,"):
                        return image_url.split(",", 1)[1]
    return None

def get_failed_coordinates(messages: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
    """Extract coordinates from failed computer calls in the conversation history."""
    failed_coords = []
    
    for message in messages:
        # Look for computer calls that were executed but may have failed
        if message.get("type") == "computer_call" and "action" in message:
            action = message["action"]
            if "x" in action and "y" in action:
                x, y = action["x"], action["y"]
                # Check if this call was followed by an error or if it's in a sequence of attempts
                failed_coords.append((x, y))
    
    return failed_coords


@register_agent(r".*\+.*", priority=1)
class ComposedGroundedConfig(AsyncAgentConfig):
    """
    Composed-grounded agent configuration that uses both grounding and thinking models.

    The model parameter should be in format: "grounding_model+thinking_model"
    e.g., "huggingface-local/HelloKKMe/GTA1-7B+gemini/gemini-1.5-pro"
    """

    def __init__(self):
        self.desc2xy: Dict[str, Tuple[float, float]] = {}
        self.grounding_agents: Dict[str, Any] = {}
        self.last_before_image: Optional[str] = None  # Store image before last action
    
    async def predict_step(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_retries: Optional[int] = None,
        stream: bool = False,
        computer_handler=None,
        use_prompt_caching: Optional[bool] = False,
        _on_api_start=None,
        _on_api_end=None,
        _on_usage=None,
        _on_screenshot=None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Composed-grounded predict step implementation.
        
        Process:
        0. Store last computer call image, if none then take a screenshot
        1. Convert computer calls from xy to descriptions
        2. Convert responses items to completion messages
        3. Call thinking model with litellm.acompletion
        4. Convert completion messages to responses items
        5. Get all element descriptions and populate desc2xy mapping
        6. Convert computer calls from descriptions back to xy coordinates
        7. Return output and usage
        """
        # Parse the composed model
        if "+" not in model:
            raise ValueError(f"Composed model must be in format 'grounding_model+thinking_model', got: {model}")
        grounding_model, thinking_model = model.split("+", 1)
        
        # Step 0: Find the latest screenshot from the history (checks user messages and computer_call_output)
        last_image_b64 = get_last_image_b64(messages)

        # Step 0.1: If no screenshot exists, take one automatically
        if not last_image_b64 and computer_handler:
            print("📸 No screenshot found in history, taking automatic screenshot...")
            try:
                last_image_b64 = await computer_handler.screenshot()
                print("   ✅ Screenshot taken successfully")
            except Exception as e:
                print(f"   ❌ Failed to take screenshot: {e}")
                last_image_b64 = None

        # Step 0.2: Store current image for potential use in next call
        # This will become the "before" image if the agent takes an action
        current_image_for_next_call = last_image_b64
        
        # Step 0.5: Get failed coordinates from previous attempts
        failed_coords = get_failed_coordinates(messages)
        
        tool_schemas = _prepare_tools_for_grounded(tools) # type: ignore

        # Step 1: Convert computer calls from xy to descriptions
        messages_with_descriptions = convert_computer_calls_xy2desc(messages, self.desc2xy)
        
        # Step 2: Convert responses items to completion messages
        completion_messages = convert_responses_items_to_completion_messages(
            messages_with_descriptions, 
            allow_images_in_tool_results=False
        )
        
        # Step 2.1: Add or replace images in the last user message
        # For decision making, show only the most relevant current images
        if completion_messages:
            last_message = completion_messages[-1]
            if last_message.get("role") == "user":
                # Convert text content to list format if it's a string
                if isinstance(last_message.get("content"), str):
                    last_message["content"] = [{"type": "text", "text": last_message["content"]}]

                if isinstance(last_message.get("content"), list):
                    # Remove any existing images from the last user message (to avoid accumulation)
                    last_message["content"] = [
                        item for item in last_message["content"]
                        if item.get("type") != "image_url"
                    ]

                    # Determine if this is the first call or subsequent call by checking for tool results
                    has_tool_results = any(msg.get("type") in ["function_call_output", "computer_call_output"] for msg in messages)

                    if has_tool_results and self.last_before_image and last_image_b64:
                        # Subsequent calls: Show before and after images for comparison
                        last_message["content"].extend([
                            {
                                "type": "text",
                                "text": "\n--- BEFORE ACTION (what screen looked like when previous action was decided) ---"
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{self.last_before_image}"}
                            },
                            {
                                "type": "text",
                                "text": "\n--- AFTER ACTION (actual result of the previous action) ---"
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{last_image_b64}"}
                            }
                        ])
                    elif last_image_b64:
                        # First call: Only show current screen state
                        last_message["content"].append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{last_image_b64}"}
                        })

                    # Store current image as before_image for next call (after action execution)
                    if last_image_b64:
                        self.last_before_image = current_image_for_next_call
        
        # Step 3: Call thinking model with litellm.acompletion
        api_kwargs = {
            "model": thinking_model,
            "messages": completion_messages,
            "tools": tool_schemas,
            "max_retries": max_retries,
            "stream": stream,
            **kwargs
        }

        if use_prompt_caching:
            api_kwargs["use_prompt_caching"] = use_prompt_caching
        
        # Call API start hook
        if _on_api_start:
            await _on_api_start(api_kwargs)

        # Log the thinking model call
        print(f"🤔 [THINKING MODEL: {thinking_model}] Making API call with {len(completion_messages)} messages")
        for i, msg in enumerate(completion_messages):
            role = msg.get("role", "")
            content = msg.get("content", "")
            print(f"   Message {i}: role={role}")

            if role == "user":
                if isinstance(content, list):
                    has_text = False
                    image_count = 0
                    for item in content:
                        if item.get("type") == "text":
                            has_text = True
                            print(f"     📝 Text: {item['text'][:100]}{'...' if len(item['text']) > 100 else ''}")
                        elif item.get("type") == "image_url":
                            image_count += 1
                            print("     🖼️  Image present")
                    print(f"     📊 Summary: has_text={has_text}, images={image_count}")
                    if not has_text and image_count > 0:
                        print("     ⚠️  WARNING: User message has images but no text!")
                else:
                    print(f"     📝 String content: {content[:100]}{'...' if len(content) > 100 else ''}")

        # Make the completion call
        response = await litellm.acompletion(**api_kwargs)

        # Log the thinking model response
        print(f"✅ [THINKING MODEL: {thinking_model}] Received response")
        choice = response.choices[0]
        if hasattr(choice.message, 'content') and choice.message.content:
            print(f"   💬 Response: {choice.message.content[:300]}{'...' if len(choice.message.content) > 300 else ''}")
        if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
            print(f"   🔧 Tool calls: {len(choice.message.tool_calls)}")
            for tc in choice.message.tool_calls[:2]:  # Show first 2 tool calls
                if tc.function:
                    print(f"      • {tc.function.name}: {tc.function.arguments[:200]}{'...' if len(tc.function.arguments) > 200 else ''}")
        
        # Call API end hook
        if _on_api_end:
            await _on_api_end(api_kwargs, response)
        
        # Extract usage information
        usage = {
            **response.usage.model_dump(), # type: ignore
            "response_cost": response._hidden_params.get("response_cost", 0.0),
        }
        if _on_usage:
            await _on_usage(usage)
        
        # Step 4: Convert completion messages back to responses items format
        response_dict = response.model_dump() # type: ignore
        choice_messages = [choice["message"] for choice in response_dict["choices"]]
        thinking_output_items = []
        
        for choice_message in choice_messages:
            thinking_output_items.extend(convert_completion_messages_to_responses_items([choice_message]))
        
        # Step 5: Get all element descriptions and populate desc2xy mapping
        element_descriptions = get_all_element_descriptions(thinking_output_items)
        
        if element_descriptions and last_image_b64:
            # Use grounding model to predict coordinates for each description
            print(f"🎯 Grounding phase: Processing {len(element_descriptions)} element descriptions")
            print(f"   Descriptions: {element_descriptions}")

            # Get or create cached grounding agent
            if grounding_model not in self.grounding_agents:
                grounding_agent_conf = find_agent_config(grounding_model)
                if grounding_agent_conf:
                    self.grounding_agents[grounding_model] = grounding_agent_conf.agent_class()
                    print(f"   Instantiated grounding agent: {grounding_agent_conf.agent_class.__name__}")
                else:
                    self.grounding_agents[grounding_model] = None
            
            grounding_agent = self.grounding_agents.get(grounding_model)

            if grounding_agent:
                print(f"   Using grounding agent: {grounding_agent.__class__.__name__}")

                for desc in element_descriptions:
                    print(f"   🔍 Grounding element: '{desc}'")
                    success = False
                    for attempt in range(3): # try 3 times
                        print(f"     Attempt {attempt + 1}/3...")
                        
                        # Enhance instruction with failed coordinates if available
                        enhanced_instruction = desc
                        if failed_coords and attempt > 0:
                            failed_coords_str = ", ".join([f"({x}, {y})" for x, y in failed_coords])
                            enhanced_instruction = f"{desc}. Avoid these previously failed coordinates: {failed_coords_str}"
                            print(f"     📍 Enhanced instruction with failed coords: {enhanced_instruction}")
                        
                        coords = await grounding_agent.predict_click(
                            model=grounding_model,
                            image_b64=last_image_b64,
                            instruction=enhanced_instruction,
                            **kwargs
                        )
                        if coords:
                            self.desc2xy[desc] = coords
                            print(f"     ✅ Success! Coordinates: ({coords[0]}, {coords[1]})")
                            success = True
                            break
                        else:
                            print(f"     ❌ Attempt {attempt + 1} failed")
                    if not success:
                        print(f"     💥 All attempts failed for element: '{desc}'")
            else:
                print(f"   ❌ No grounding agent config found for model: {grounding_model}")
        
        # Step 6: Convert computer calls from descriptions back to xy coordinates
        final_output_items = convert_computer_calls_desc2xy(thinking_output_items, self.desc2xy)
        
        # Step 7: Return output and usage
        return {
            "output": final_output_items,
            "usage": usage
        }
    
    async def predict_click(
        self,
        model: str,
        image_b64: str,
        instruction: str,
        **kwargs
    ) -> Optional[Tuple[int, int]]:
        """
        Predict click coordinates using the grounding model.
        
        For composed models, uses only the grounding model part for click prediction.
        """
        # Parse the composed model to get grounding model
        if "+" not in model:
            raise ValueError(f"Composed model must be in format 'grounding_model+thinking_model', got: {model}")
        grounding_model, thinking_model = model.split("+", 1)
        
        # Find and use the grounding agent
        grounding_agent_conf = find_agent_config(grounding_model)
        if grounding_agent_conf:
            grounding_agent = grounding_agent_conf.agent_class()
            return await grounding_agent.predict_click(
                model=grounding_model,
                image_b64=image_b64,
                instruction=instruction,
                **kwargs
            )
        
        return None
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Return the capabilities supported by this agent."""
        return ["click", "step"]