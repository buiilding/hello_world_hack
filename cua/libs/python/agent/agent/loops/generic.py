"""
Generic agent loop implementation using liteLLM for models that don't have specialized configs
"""

import asyncio
import json
from typing import Dict, List, Any, AsyncGenerator, Union, Optional, Tuple
import litellm

from ..decorators import register_agent
from ..types import Messages, AgentResponse, Tools, AgentCapability
from ..loops.base import AsyncAgentConfig
from ..responses import (
    make_reasoning_item,
    make_output_text_item,
    make_click_item,
    make_double_click_item,
    make_drag_item,
    make_keypress_item,
    make_move_item,
    make_scroll_item,
    make_type_item,
    make_wait_item,
    make_input_image_item,
    make_screenshot_item,
    make_failed_tool_call_items,
    make_left_mouse_down_item,
    make_left_mouse_up_item
)


async def _prepare_tools_for_generic(tool_schemas: List[Dict[str, Any]]) -> Tools:
    """Prepare tools for generic API format (liteLLM compatible)"""
    generic_tools = []
    
    for schema in tool_schemas:
        if schema["type"] == "computer":
            # For computer tools, we need to create a function-like schema
            # that the model can understand
            computer_tool = {
                "type": "function",
                "function": {
                    "name": "computer",
                    "description": "Execute computer actions like clicking, typing, scrolling, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "The action to perform (click, type, scroll, etc.)",
                                "enum": [
                                    "click", "double_click", "drag", "keypress", "move", 
                                    "scroll", "type", "wait", "screenshot", "left_mouse_down", "left_mouse_up"
                                ]
                            },
                            "x": {
                                "type": "number",
                                "description": "X coordinate for click/move actions"
                            },
                            "y": {
                                "type": "number", 
                                "description": "Y coordinate for click/move actions"
                            },
                            "text": {
                                "type": "string",
                                "description": "Text to type"
                            },
                            "key": {
                                "type": "string",
                                "description": "Key to press (e.g., 'enter', 'tab', 'ctrl+c')"
                            },
                            "dx": {
                                "type": "number",
                                "description": "Delta X for scroll/move actions"
                            },
                            "dy": {
                                "type": "number",
                                "description": "Delta Y for scroll/move actions"
                            },
                            "duration": {
                                "type": "number",
                                "description": "Duration for wait actions in seconds"
                            }
                        },
                        "required": ["action"]
                    }
                }
            }
            generic_tools.append(computer_tool)
        elif schema["type"] == "function":
            # Function tools use standard schema
            generic_tools.append({
                "type": "function",
                "function": schema["function"]
            })
    
    return generic_tools


async def _process_generic_response(response: Dict[str, Any], tool_schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process response from generic model and convert to standard format"""
    output_items = []
    
    # Handle reasoning if present
    if "reasoning" in response:
        output_items.append(make_reasoning_item(response["reasoning"]))
    
    # Handle text output
    if "content" in response and response["content"]:
        output_items.append(make_output_text_item(response["content"]))
    
    # Handle tool calls
    if "tool_calls" in response and response["tool_calls"]:
        for tool_call in response["tool_calls"]:
            try:
                function_name = tool_call.get("function", {}).get("name", "")
                function_args = tool_call.get("function", {}).get("arguments", "{}")
                
                if isinstance(function_args, str):
                    function_args = json.loads(function_args)
                
                # Map function calls to appropriate response items
                if function_name == "computer":
                    action = function_args.get("action", "")
                    
                    if action == "click":
                        x = function_args.get("x", 0)
                        y = function_args.get("y", 0)
                        output_items.append(make_click_item(x, y))
                    elif action == "double_click":
                        x = function_args.get("x", 0)
                        y = function_args.get("y", 0)
                        output_items.append(make_double_click_item(x, y))
                    elif action == "drag":
                        x = function_args.get("x", 0)
                        y = function_args.get("y", 0)
                        dx = function_args.get("dx", 0)
                        dy = function_args.get("dy", 0)
                        output_items.append(make_drag_item(x, y, dx, dy))
                    elif action == "keypress":
                        key = function_args.get("key", "")
                        output_items.append(make_keypress_item(key))
                    elif action == "move":
                        x = function_args.get("x", 0)
                        y = function_args.get("y", 0)
                        output_items.append(make_move_item(x, y))
                    elif action == "scroll":
                        dx = function_args.get("dx", 0)
                        dy = function_args.get("dy", 0)
                        output_items.append(make_scroll_item(dx, dy))
                    elif action == "type":
                        text = function_args.get("text", "")
                        output_items.append(make_type_item(text))
                    elif action == "wait":
                        duration = function_args.get("duration", 1.0)
                        output_items.append(make_wait_item(duration))
                    elif action == "screenshot":
                        output_items.append(make_screenshot_item())
                    elif action == "left_mouse_down":
                        x = function_args.get("x", 0)
                        y = function_args.get("y", 0)
                        output_items.append(make_left_mouse_down_item(x, y))
                    elif action == "left_mouse_up":
                        x = function_args.get("x", 0)
                        y = function_args.get("y", 0)
                        output_items.append(make_left_mouse_up_item(x, y))
                    else:
                        # Unknown action, create failed tool call
                        output_items.extend(make_failed_tool_call_items(
                            [tool_call], f"Unknown computer action: {action}"
                        ))
                else:
                    # Handle other function calls
                    output_items.append({
                        "type": "function_call",
                        "function": {
                            "name": function_name,
                            "arguments": function_args
                        }
                    })
                    
            except Exception as e:
                # Create failed tool call for any errors
                output_items.extend(make_failed_tool_call_items(
                    [tool_call], f"Error processing tool call: {str(e)}"
                ))
    
    return output_items


@register_agent(models=r"gemini/.*|litellm/gemini.*|google/.*", priority=1)
class GenericConfig(AsyncAgentConfig):
    """
    Generic agent configuration for models that don't have specialized configs.
    
    Supports Gemini and other models through liteLLM.
    """
    
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
        Predict the next step based on input items.
        
        Args:
            messages: Input items following Responses format
            model: Model name to use
            tools: Optional list of tool schemas
            max_retries: Maximum number of retries
            stream: Whether to stream responses
            computer_handler: Computer handler instance
            _on_api_start: Callback for API start
            _on_api_end: Callback for API end
            _on_usage: Callback for usage tracking
            _on_screenshot: Callback for screenshot events
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with "output" (output items) and "usage" array
        """
        tools = tools or []
        
        # Prepare tools for the API
        api_tools = await _prepare_tools_for_generic(tools)
        
        # Prepare messages for liteLLM
        api_messages = []
        for message in messages:
            if message.get("type") == "message":
                api_messages.append({
                    "role": message["role"],
                    "content": message["content"]
                })
            elif message.get("type") == "function_call":
                api_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": message.get("call_id", "call_1"),
                        "type": "function",
                        "function": {
                            "name": message["function"]["name"],
                            "arguments": json.dumps(message["function"]["arguments"])
                        }
                    }]
                })
            elif message.get("type") == "function_output":
                api_messages.append({
                    "role": "tool",
                    "content": message["output"],
                    "tool_call_id": message.get("call_id", "call_1")
                })
            elif message.get("type") == "function_call_output":
                # Handle function call output with multimodal content (text + images)
                if isinstance(message.get("output"), list):
                    # Convert multimodal content to liteLLM format
                    content = []
                    for item in message["output"]:
                        if item.get("type") == "text":
                            content.append({
                                "type": "text",
                                "text": item["text"]
                            })
                        elif item.get("type") == "image_url":
                            content.append({
                                "type": "image_url",
                                "image_url": item["image_url"]
                            })
                    api_messages.append({
                        "role": "user",  # Function results are shown as user messages
                        "content": content
                    })
                else:
                    # Handle simple string output
                    api_messages.append({
                        "role": "user",
                        "content": str(message["output"])
                    })
            elif message.get("role"):
                # Handle liteLLM format messages that already have "role" instead of "type"
                api_messages.append(message)
            else:
                # Fallback for unknown message format
                print(f"⚠️  Unknown message format: {message}")
                api_messages.append(message)
        
        # Prepare API call parameters
        api_kwargs = {
            "model": model,
            "messages": api_messages,
            "tools": api_tools if api_tools else None,
            "tool_choice": "auto" if api_tools else None,
            "max_retries": max_retries or 3,
            "stream": stream,
            **kwargs
        }

        # Call the model
        try:
            if _on_api_start:
                await _on_api_start(api_kwargs)
            
            print(f"🤖 [GENERIC AGENT: {model}] Making API call with {len(api_messages)} messages")

            # Log the input to the generic agent - show all messages for debugging
            for i, msg in enumerate(api_messages):
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

            response = await litellm.acompletion(**api_kwargs)

            # Log the response from generic agent
            if not stream:
                choice = response.choices[0]
                message = choice.message
                print(f"✅ [GENERIC AGENT: {model}] Response received")
                if hasattr(message, 'content') and message.content:
                    print(f"   💬 Content: {message.content[:300]}{'...' if len(message.content) > 300 else ''}")
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    print(f"   🔧 Tool calls: {len(message.tool_calls)}")
                    for tc in message.tool_calls:
                        if tc.function:
                            print(f"      • {tc.function.name}: {tc.function.arguments[:200]}{'...' if len(tc.function.arguments) > 200 else ''}")
            
            if _on_api_end:
                await _on_api_end(api_kwargs, response)
            
            # Process the response
            if stream:
                # Handle streaming response
                output_items = []
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            output_items.append(make_output_text_item(delta.content))
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            # Handle streaming tool calls
                            for tool_call in delta.tool_calls:
                                if tool_call.type == "function":
                                    output_items.append({
                                        "type": "function_call",
                                        "function": {
                                            "name": tool_call.function.name,
                                            "arguments": tool_call.function.arguments
                                        },
                                        "call_id": tool_call.id
                                    })
            else:
                # Handle non-streaming response
                choice = response.choices[0]
                message = choice.message
                
                # Convert to our response format
                response_dict = {}
                if hasattr(message, 'content') and message.content:
                    response_dict["content"] = message.content
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    response_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                
                output_items = await _process_generic_response(response_dict, tools)
            
            # Extract usage information
            usage = []
            if hasattr(response, 'usage') and response.usage:
                usage.append({
                    "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                    "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                    "total_tokens": getattr(response.usage, 'total_tokens', 0)
                })
            
            if _on_usage and usage:
                await _on_usage(usage[0])
            
            return {
                "output": output_items,
                "usage": usage
            }
            
        except Exception as e:
            if _on_api_end:
                await _on_api_end(api_kwargs, response)
            raise e
    
    async def predict_click(
        self,
        model: str,
        image_b64: str,
        instruction: str
    ) -> Optional[Tuple[int, int]]:
        """
        Predict click coordinates based on image and instruction.
        
        Args:
            model: Model name to use
            image_b64: Base64 encoded image
            instruction: Instruction for where to click
            
        Returns:
            None or tuple with (x, y) coordinates
        """
        try:
            # Create a simple prompt for click prediction
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Look at this image and tell me the x,y coordinates to click for: {instruction}. Respond with just the coordinates in the format 'x,y' (e.g., '100,200')."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ]
            
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                max_tokens=50
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse coordinates from response
            if "," in content:
                try:
                    x_str, y_str = content.split(",")
                    x = int(float(x_str.strip()))
                    y = int(float(y_str.strip()))
                    return (x, y)
                except (ValueError, IndexError):
                    pass
            
            return None
            
        except Exception:
            return None
    
    def get_capabilities(self) -> List[AgentCapability]:
        """
        Get list of capabilities supported by this agent config.
        
        Returns:
            List of capability strings
        """
        return ["step", "click"]