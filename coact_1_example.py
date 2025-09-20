#!/usr/bin/env python3
"""
CUA Example: CoAct-1 Multi-Agent System

This example implements the CoAct-1 architecture, a multi-agent system
for computer automation, as described in the paper.

The system consists of three agents:
1. Orchestrator: A high-level planner that decomposes tasks and delegates.
2. Programmer: An agent that writes and executes Python or Bash scripts.
3. GUI Operator: A vision-language agent for GUI manipulation.
"""

import asyncio
import os
import sys
import logging
import json
import subprocess
import tempfile
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
from agent import ComputerAgent
from computer import Computer, VMProviderType
from agent.callbacks import AsyncCallbackHandler
from agent.computers.base import AsyncComputerHandler
from agent.computers.cua import cuaComputerHandler
import litellm

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# --- Toolkits for Agents ---

class ProgrammerTools:
    """A toolkit for the Programmer agent that provides code and system-level tools."""
    def __init__(self, computer: Computer):
        self._computer = computer

    async def run_command(self, command: str, run_in_background: bool = False) -> str:
        """
        Runs a shell command in the computer's environment and returns the output.

        Args:
            command (str): The shell command to execute.
            run_in_background (bool): Whether to run the command in the background. Use this for starting applications. Defaults to False.

        Returns:
            str: The stdout and stderr from the command execution, or a confirmation message for background commands.
        """
        if run_in_background:
            await self._computer.interface.run_command(command, run_in_background=True)
            return f"Command '{command}' started in the background."

        result = await self._computer.interface.run_command(command)
        output = f"Stdout:\n{result.stdout}\n"
        if result.stderr:
            output += f"Stderr:\n{result.stderr}\n"
        return output

    async def list_dir(self, path: str) -> List[str]:
        """Lists the contents of a directory."""
        return await self._computer.interface.list_dir(path)

    async def read_file(self, path: str) -> str:
        """Reads the text content of a file."""
        return await self._computer.interface.read_text(path)

    async def write_file(self, path: str, content: str):
        """Writes text content to a file."""
        await self._computer.interface.write_text(path, content)
    
    async def venv_cmd(self, venv_name: str, command: str) -> str:
        """
        Execute a shell command in a virtual environment.
        
        Args:
            venv_name: Name of the virtual environment.
            command: Shell command to execute.
            
        Returns:
            The stdout and stderr from the command execution.
        """
        stdout, stderr = await self._computer.venv_cmd(venv_name, command)
        output = f"Stdout:\n{stdout}\n"
        if stderr:
            output += f"Stderr:\n{stderr}\n"
        return output

def get_last_image_b64(messages: List[Dict[str, Any]]) -> Optional[str]:
    """Get the last image from a list of messages, checking both user messages and tool outputs."""
    for message in reversed(messages):
        # Check user messages with content lists
        if message.get("role") == "user" and isinstance(message.get("content"), list):
            for content_item in reversed(message["content"]):
                if content_item.get("type") == "image_url":
                    image_url = content_item.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:image/png;base64,"):
                        return image_url.split(",", 1)[1]
        
        # Check computer call outputs
        elif message.get("type") == "computer_call_output" and isinstance(message.get("output"), dict):
            output = message["output"]
            if output.get("type") == "input_image":
                image_url = output.get("image_url", "")
                if image_url.startswith("data:image/png;base64,"):
                    return image_url.split(",", 1)[1]
    return None

class GuiOperatorComputerProxy:
    """
    A proxy for the Computer object that exposes only GUI-related methods.
    This is necessary because the ComputerAgent has special handling for 'computer' tools,
    and we want to provide a restricted set of a computer's capabilities.
    """
    def __init__(self, computer: Computer):
        # We need to hold a reference to the original computer object
        # and its interface to delegate the calls.
        self._computer_instance = computer
        self.interface = self._create_gui_interface_proxy(computer.interface)
        self.is_gui_proxy = True

    def _create_gui_interface_proxy(self, real_interface):
        class GuiInterfaceProxy:
            """A proxy that exposes only the GUI-related methods of the real interface."""
            def __init__(self, interface):
                self._real_interface = interface

            # GUI Mouse Methods
            async def left_click(self, x: int, y: int, delay: Optional[float] = None): return await self._real_interface.left_click(x, y, delay)
            async def right_click(self, x: int, y: int, delay: Optional[float] = None): return await self._real_interface.right_click(x, y, delay)
            async def double_click(self, x: int, y: int, delay: Optional[float] = None): return await self._real_interface.double_click(x, y, delay)
            async def move_cursor(self, x: int, y: int, delay: Optional[float] = None): return await self._real_interface.move_cursor(x, y, delay)
            async def mouse_down(self, x: int, y: int, button: str = "left"): return await self._real_interface.mouse_down(x, y, button)
            async def mouse_up(self, x: int, y: int, button: str = "left"): return await self._real_interface.mouse_up(x, y, button)
            async def drag(self, path, button="left", duration=0.5): return await self._real_interface.drag(path, button, duration)

            # GUI Keyboard Methods
            async def type_text(self, text: str, delay: Optional[float] = None): return await self._real_interface.type_text(text, delay)
            async def press_key(self, key: str, delay: Optional[float] = None): return await self._real_interface.press_key(key, delay)
            async def hotkey(self, *keys: str, delay: Optional[float] = None): return await self._real_interface.hotkey(*keys, delay=delay)
            
            # GUI Screen Methods
            async def screenshot(self): return await self._real_interface.screenshot()
            async def get_screen_size(self): return await self._real_interface.get_screen_size()
            async def scroll(self, x: int, y: int, delay: Optional[float] = None): return await self._real_interface.scroll(x, y, delay)

        return GuiInterfaceProxy(real_interface)

    # The ComputerAgent's handler needs to check if the computer is initialized.
    @property
    def _initialized(self):
        return self._computer_instance._initialized

class OrchestratorTools:
    """A toolkit for the Orchestrator agent that provides observation tools."""
    def __init__(self, computer_handler: 'cuaComputerHandler'):
        self._handler = computer_handler
    
    async def get_environment(self) -> str:
        """Get the current environment type (e.g., 'linux', 'windows')."""
        return await self._handler.get_environment()

    async def get_dimensions(self) -> tuple[int, int]:
        """Get screen dimensions as (width, height)."""
        return await self._handler.get_dimensions()

    async def get_current_url(self) -> str:
        """Get current URL (for browser environments)."""
        return await self._handler.get_current_url()

# --- Orchestrator Agent Tools ---

def delegate_to_programmer(subtask: str):
    """Delegates a subtask to the programmer agent for code-based execution."""
    pass

def delegate_to_gui_operator(subtask: str):
    """Delegates a subtask to the GUI operator for visual, UI-based execution."""
    pass

def task_completed():
    """Signals that the overall task is completed."""
    pass

# --- CoAct-1 System ---

class CoAct1:
    """
    Implements the CoAct-1 multi-agent system.
    """
    def __init__(self, computer: Computer, orchestrator_model: str, programmer_model: str, gui_operator_model: str):
        self.computer = computer
        
        # Store model names
        self.orchestrator_model = orchestrator_model
        self.programmer_model = programmer_model
        self.gui_operator_model = gui_operator_model

        # The cuaComputerHandler is the component that translates agent actions
        # into calls on the computer interface. We can reuse it.
        computer_handler = cuaComputerHandler(computer)

        # Create specialized toolkits for each agent
        self.orchestrator_tools = OrchestratorTools(computer_handler)
        self.programmer_tools = ProgrammerTools(computer)
        self.gui_operator_computer = GuiOperatorComputerProxy(computer)
        
        self.orchestrator = self._create_orchestrator()
        self.programmer = self._create_programmer()
        self.gui_operator = self._create_gui_operator()

    def _create_orchestrator(self) -> ComputerAgent:
        instructions = """
        You are the Orchestrator agent. Your role is to decompose a user's high-level task into a sequence of subtasks.
        For each subtask, you must decide whether to delegate it to the 'Programmer' agent or the 'GUI Operator' agent.
        For each subtask, delegate the task to the agent that could do it more easily and effectively.
        For each subtask, you should only delegate it to the GUI Operator if you are sure it requires visual interaction with the graphical user interface.
        You can also delegate it to yourself to solve it.

        - Use the 'Programmer' agent for tasks that can be solved with code (Python or Bash), such as file operations, data processing, and system commands.
        - Use the 'GUI Operator' agent for tasks that require visual interaction with a graphical user interface, such as clicking buttons, filling forms, and navigating web pages.
        - Use your observation tools to understand the system state before delegating.
        - Use the 'task_completed' function when the user's overall goal has been achieved.

        You will be given the user's task, the conversation history, and a recent screenshot of the computer screen.
        Based on this information, decide the next best subtask and delegate it to the appropriate agent.
        """
        
        # Gather all methods from the toolkit instance to pass to the agent
        orchestrator_tool_methods = [
            self.orchestrator_tools.get_environment,
            self.orchestrator_tools.get_dimensions,
            self.orchestrator_tools.get_current_url,
            delegate_to_programmer, 
            delegate_to_gui_operator, 
            task_completed
        ]

        return ComputerAgent(
            model=self.orchestrator_model,
            tools=orchestrator_tool_methods,
            instructions=instructions,
            verbosity=logging.WARNING
        )

    def _create_programmer(self) -> ComputerAgent:
        instructions = """
        You are the Programmer agent. You solve tasks by writing and executing Python or Bash scripts using the 'run_command' tool.
        When using `run_command` to start an application (like 'firefox' or 'code'), you MUST set `run_in_background=True` to prevent the system from hanging.
        For all other commands, you can omit this parameter.
        You can also use other file system tools to interact with the OS.
        You will be given a subtask from the Orchestrator. Write the necessary code or commands to complete it.
        You can use multiple rounds of coding to reflect on the execution output and refine your commands.
        Once the subtask is complete, respond with a summary of what you did.
        """
        
        # Gather all methods from the toolkit instance
        programmer_tool_methods = [
            self.programmer_tools.run_command,
            self.programmer_tools.list_dir,
            self.programmer_tools.read_file,
            self.programmer_tools.write_file,
            self.programmer_tools.venv_cmd,
        ]

        return ComputerAgent(
            model=self.programmer_model,
            tools=programmer_tool_methods,
            instructions=instructions,
            verbosity=logging.WARNING
        )

    def _create_gui_operator(self) -> ComputerAgent:
        instructions = """
        You are the GUI Operator, a vision-based agent. Your ONLY way to interact with the computer is by using the `computer` tool to perform visual actions like clicking and typing on elements.
        You CANNOT execute shell commands.

        CRITICAL: You MUST use the function name "computer" (not "function_name" or any other name) when making tool calls.

        You will be given a subtask from the Orchestrator and a view of the screen.
        Your task is to identify visual elements on the screen and use them to accomplish the subtask.

        TOOL USAGE RULES:
        1. ALWAYS use the function name "computer" for all tool calls
        2. For clicking: computer(action='click', element_description='clear description of the element')
        3. For typing: computer(action='type', element_description='clear description of the input field', text='text to type')
        4. For other actions: computer(action='action_name', element_description='clear description')

        ELEMENT DESCRIPTION GUIDELINES:
        - Be specific and descriptive (e.g., "the blue login button with text 'Log In'" not just "button")
        - Include visual characteristics like color, text, position, or size
        - Use consistent descriptions for the same element across multiple attempts
        - If an element is not found, try a more general description

        WORKFLOW:
        1. Analyze the screen carefully
        2. Identify the target element with a clear, specific description
        3. Make ONE computer call with the correct function name "computer"
        4. Wait for the result and evaluate if the action was successful
        5. If unsuccessful, try a different element description or approach
        6. Once the subtask is complete, respond with a final message summarizing your actions


        CRITICAL GUI OPERATION RULES:
        - To open any app on the desktop, you MUST use double_click, NOT single click
        - For app icons: computer(action='double_click', element_description='app name icon')
        - For buttons and links: computer(action='click', element_description='button description')
        - For text fields: computer(action='type', element_description='input field description', text='text to type')

        Remember: Use "computer" as the function name, be specific in element descriptions, and evaluate results before making additional attempts.
        """
        return ComputerAgent(
            model=self.gui_operator_model,
            tools=[self.gui_operator_computer],
            instructions=instructions,
            verbosity=logging.WARNING,
            quantization_bits=8,
        )

    async def _summarize_interaction(self, history: List[Dict[str, Any]], screenshot_b64: str) -> str:
        """Summarizes a sub-agent's conversation history."""
        prompt = "Please summarize the following interaction history in one sentence for the Orchestrator. The user's request is at the beginning, followed by the agent's actions. The final screenshot shows the result of the actions."
        
        # Filter out screenshots from the history to reduce token count
        filtered_history = []
        image_count = 0
        for item in history:
            if "image_url" not in json.dumps(item):
                filtered_history.append(item)
            else:
                image_count += 1

        # Debug: Print details about the input before summarization
        print(f"📊 Summarization input details:")
        print(f"   📝 Total history items: {len(history)}")
        print(f"   🖼️  Images in history: {image_count}")
        print(f"   📄 Filtered history items: {len(filtered_history)}")
        print(f"   📸 Screenshot provided: {'Yes' if screenshot_b64 else 'No'}")
        print(f"   📝 Full text input:")
        print(f"   {json.dumps(filtered_history, indent=2)}")

        summary_messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": f"{prompt}\n\nHistory:\n{json.dumps(filtered_history, indent=2)}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
            ]
        }]

        try:
            response = await litellm.acompletion(
                model="gemini/gemini-1.5-pro",
                messages=summary_messages,
            )
            summary = response.choices[0].message.content or "No summary available."
            return summary.strip()
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
            return "Could not summarize the interaction."

    async def run(self, task: str):
        """Runs the CoAct-1 agent system on a given task."""
        orchestrator_history: List[Dict[str, Any]] = [{"role": "user", "content": task}]
    
        for i in range(10): # Max 10 steps
            print(f"\n--- Step {i+1} ---")

            # 1. Get screenshot
            print("📸 Taking screenshot...")
            screenshot_bytes = await self.computer.interface.screenshot()
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # Add screenshot to orchestrator history
            orchestrator_history.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "Here is the current screen. What is the next subtask?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
                ]
            })

            # 2. Call Orchestrator
            print("🤔 Orchestrator is planning...")
            delegation = None
            async for result in self.orchestrator.run(orchestrator_history):
                for item in result.get("output", []):
                    if item.get("type") == "function_call":
                        delegation = item
                        break
                if delegation:
                    break
            
            if not delegation:
                print("🛑 Orchestrator did not delegate a task. Ending.")
                break

            tool_name = delegation.get("name")
            arguments = json.loads(delegation.get("arguments", "{}"))
            subtask = arguments.get("subtask", "")

            orchestrator_history.append(delegation) # Add delegation to history

            if tool_name == "task_completed":
                print("✅ Task completed!")
                break
            
            sub_agent = None
            if tool_name == "delegate_to_programmer":
                print(f"👨‍💻 Delegating to Programmer: {subtask}")
                sub_agent = self.programmer
            elif tool_name == "delegate_to_gui_operator":
                print(f"🖱️ Delegating to GUI Operator: {subtask}")
                sub_agent = self.gui_operator
            else:
                print(f"❓ Unknown delegation: {tool_name}")
                continue

            # 3. Run sub-agent with the task and the current screenshot
            sub_agent_history = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": subtask},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
                ]
            }]
            async for result in sub_agent.run(sub_agent_history):
                sub_agent_history.extend(result.get("output", []))

            # 4. Get the latest screenshot from the sub-agent's history for the summary
            summary_screenshot_b64 = get_last_image_b64(sub_agent_history) or screenshot_b64

            # 5. Summarize and update Orchestrator history
            print("📝 Summarizing sub-task...")
            summary = await self._summarize_interaction(sub_agent_history, summary_screenshot_b64)
            print(f"Summary: {summary}")

            orchestrator_history.append({
                "type": "function_call_output",
                "call_id": delegation["call_id"],
                "output": summary,
            })

    async def run_direct_gui(self, task: str):
        """Runs the CoAct-1 system but directly delegates the task to the GUI Operator."""
        orchestrator_history: List[Dict[str, Any]] = [{"role": "user", "content": task}]

        print("\n--- Direct GUI Run ---")

        # 1. Get screenshot
        print("📸 Taking screenshot...")
        screenshot_bytes = await self.computer.interface.screenshot()
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')

        # Add screenshot to history
        orchestrator_history.append({
            "role": "user",
            "content": [
                {"type": "text", "text": f"Direct GUI task: {task}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
            ]
        })

        # 2. Instead of Orchestrator → directly delegate to GUI Operator
        subtask = "Double click on the Firefox web browser icon on the screen."
        print(f"🖱️ Directly delegating to GUI Operator: {subtask}")

        sub_agent = self.gui_operator
        sub_agent_history = [{
            "role": "user",
            "content": [
                {"type": "text", "text": subtask},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
            ]
        }]

        # 3. Run the GUI Operator
        async for result in sub_agent.run(sub_agent_history):
            sub_agent_history.extend(result.get("output", []))

        # 4. Get the latest screenshot
        summary_screenshot_b64 = get_last_image_b64(sub_agent_history) or screenshot_b64

        # 5. Summarize
        print("📝 Summarizing GUI Operator sub-task...")
        summary = await self._summarize_interaction(sub_agent_history, summary_screenshot_b64)
        print(f"Summary: {summary}")

        orchestrator_history.append({
            "type": "function_call_output",
            "output": summary,
        })

        print("✅ Direct GUI task completed!")
    


async def main():
    """Main function to run the CoAct-1 example."""
    print("🚀 Starting CoAct-1 Example")
    print("=" * 60)

    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY environment variable not set.")
        return

    computer_instance = None
    try:
        print("📦 Setting up Docker computer...")
        computer_instance = Computer(
            os_type="linux",
            provider_type=VMProviderType.DOCKER,
            name="cua-coact1-demo",
            image="trycua/cua-ubuntu:latest",
        )
        await computer_instance.run()

        # Define model names for each agent
        orchestrator_model_name = "gemini/gemini-2.0-flash"
        programmer_model_name = "gemini/gemini-1.5-pro"
        gui_operator_model_name = "inclusionAI/UI-Venus-Ground-7B+gemini/gemini-2.0-flash"

        coact_system = CoAct1(
            computer=computer_instance,
            orchestrator_model=orchestrator_model_name,
            programmer_model=programmer_model_name,
            gui_operator_model=gui_operator_model_name,
        )

        # Example Task
        task = "Open Firefox"
        
        await coact_system.run_direct_gui(task)

    except Exception as e:
        logger.error(f"❌ Error running example: {e}")
        raise
    finally:
        if computer_instance:
            # await computer_instance.stop()
            print("\n🧹 Computer connection closed")

if __name__ == "__main__":
    asyncio.run(main())
