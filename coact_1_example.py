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

    async def run_command(self, command: str) -> str:
        """
        Runs a shell command and waits for output.
        Use this for commands where you need to see the results (ls, cat, grep, etc.).

        Args:
            command (str): The shell command to execute.

        Returns:
            str: The command output.
        """
        try:
            result = await self._computer.interface.run_command(command)
            output = f"Stdout:\n{result.stdout}\n"
            if result.stderr:
                output += f"Stderr:\n{result.stderr}\n"
            return output
        except Exception as e:
            return f"Error running command '{command}': {e}"

    async def run_command_in_background(self, command: str) -> str:
        """
        Runs a shell command in the background without waiting for output.
        Use this for opening applications (firefox, chrome, xterm, etc.).

        Args:
            command (str): The shell command to execute.

        Returns:
            str: Confirmation that the command was started in background.
        """
        # Run command in background with complete detachment
        background_command = f"setsid {command} >/dev/null 2>&1 &"

        # Create a task to run the command without blocking
        async def run_background_command():
            try:
                await self._computer.interface.run_command(background_command)
            except Exception:
                # Ignore errors since we're not waiting anyway
                pass

        # Start the task but don't wait for it
        asyncio.create_task(run_background_command())

        # Return immediately - no output capture, no waiting
        return f"Command '{command}' started in background."

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

        # Check function call outputs (for orchestrator results with multimodal content)
        elif message.get("type") == "function_call_output" and isinstance(message.get("output"), list):
            for content_item in reversed(message["output"]):
                if content_item.get("type") == "image_url":
                    image_url = content_item.get("image_url", {}).get("url", "")
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
            async def scroll(self, x: int = 0, y: int = 0, scroll_x: int = 0, scroll_y: int = 0):
                """Handle scrolling with scroll amounts."""
                # Use scroll_down/scroll_up for vertical scrolling by amounts
                if scroll_y > 0:
                    # Scroll down by the specified amount
                    clicks = max(1, scroll_y // 100)  # Convert scroll amount to clicks
                    if hasattr(self._real_interface, 'scroll_down'):
                        return await self._real_interface.scroll_down(clicks)
                    else:
                        return await self._real_interface.scroll(x, y)
                elif scroll_y < 0:
                    # Scroll up by the specified amount
                    clicks = max(1, abs(scroll_y) // 100)  # Convert scroll amount to clicks
                    if hasattr(self._real_interface, 'scroll_up'):
                        return await self._real_interface.scroll_up(clicks)
                    else:
                        return await self._real_interface.scroll(x, y)
                else:
                    # No vertical scroll, just use coordinates
                    return await self._real_interface.scroll(x, y)

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

        print("🏗️  [COACT-1] Initializing multi-agent system...")
        print(f"   🤖 Orchestrator: {orchestrator_model}")
        print(f"   👨‍💻 Programmer: {programmer_model}")
        print(f"   🎭 GUI Operator: {gui_operator_model}")

        # Create specialized toolkits for each agent
        self.orchestrator_tools = OrchestratorTools(computer_handler)
        self.programmer_tools = ProgrammerTools(computer)
        self.gui_operator_computer = GuiOperatorComputerProxy(computer)
        
        self.orchestrator = self._create_orchestrator()
        self.programmer = self._create_programmer()
        self.gui_operator = self._create_gui_operator()

        print("✅ [COACT-1] All agents initialized successfully!")

    def _create_orchestrator(self) -> ComputerAgent:
        instructions = """
        You are the Orchestrator agent. Your role is to decompose a user's high-level task into a sequence of simple, manageable subtasks.
        
        TASK DECOMPOSITION PRINCIPLE:
        - Analyze BOTH the user's text input AND the current screenshot to understand the starting state
        - Break down complex tasks into the SMALLEST possible steps - the easier, the better
        - Each subtask should be a single, clear action that can be completed in one step
        - Consider what you can see on the current screen when planning the first subtask
        - Start with the most basic action needed to begin the task
        
        For each subtask, decide whether to delegate it to the 'Programmer' agent, the 'GUI Operator' agent, or handle it yourself.

        DELEGATION STRATEGY:
        - Always prefer the 'Programmer' agent whenever possible for efficiency and reliability.
        - Only use the 'GUI Operator' agent if the subtask cannot reasonably be accomplished through code or command-line execution.
        
        PROGRAMMER AGENT - Use for:
        - Opening applications (e.g., "Open Firefox Web Browser" → delegate to Programmer with run_command_in_background("firefox"))
        - File operations and system commands (e.g., "Check if file exists" → delegate to Programmer with run_command("ls filename"))
        - Any task that can be accomplished with shell commands
        
        GUI OPERATOR AGENT - Use for:
        - Visual interactions that require seeing the screen (clicking buttons, filling forms)
        - Web browsing and navigation that requires visual feedback
        - Interacting with graphical applications that don't have command-line interfaces
        - Drag-and-drop operations
        - Visual element selection and manipulation
        - Tasks requiring visual confirmation of results

        TASK DECOMPOSITION EXAMPLES:
        
        Example 1: User says "Open Firefox" + Screenshot shows desktop
        - Analysis: Desktop is visible, need to open Firefox browser
        - Subtask 1: Delegate to Programmer: "Open Firefox Web Browser using run_command_in_background"
        - Reason: Single, simple action - opening GUI application
        
        Example 2: User says "Check if file exists" + Screenshot shows desktop
        - Analysis: Need to check file system
        - Subtask 1: Delegate to Programmer: "Check if file exists using run_command"
        - Reason: Simple file operation that returns output

        DECOMPOSITION GUIDELINES:
        - If you see a desktop: First subtask should be opening the required application
        - If you see a browser: First subtask should be navigating to the target website
        - If you see a website: First subtask should be the most basic interaction (click, type, scroll)
        - For terminal tasks: Group terminal operations into single subtasks (e.g., "Create terminal session and run ls command")
        - For GUI applications: Use run_command_in_background (no parameters needed)
        - Always break complex actions into individual steps (e.g., "search for laptops" becomes "click search box" + "type laptops" + "press enter")
        - Each subtask should be completable in 5-10 seconds
        - Avoid combining multiple actions in a single subtask
        - IMPORTANT: For terminal tasks, include both session creation AND command execution in one subtask
        
        EVALUATION PROCESS:
        After each sub-agent completes a task, you will receive both a text summary of their actions AND a screenshot showing the final screen state.
        Carefully evaluate both the summary text and the visual screenshot to determine:
        - Whether the sub-task was completed successfully
        - If you need to delegate again to the same agent to fix or continue the task
        - If you should switch to a different agent or approach
        - Whether the overall goal has been achieved
        
        Use the 'task_completed' function when the user's overall goal has been achieved.
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

        print(f"🎯 [ORCHESTRATOR] Initializing with model: {self.orchestrator_model}")
        return ComputerAgent(
            model=self.orchestrator_model,
            tools=orchestrator_tool_methods,
            instructions=instructions,
            verbosity=logging.WARNING
        )

    def _create_programmer(self) -> ComputerAgent:
        instructions = """
        You are the Programmer agent. You solve tasks by writing and executing shell commands.

        COMMAND EXECUTION TOOLS:

        1. 'run_command' - Runs a shell command and waits for output:
           - Use this for commands where you need to see the results (ls, cat, grep, etc.)
           - Executes the command and returns stdout/stderr output
           - Waits for the command to complete

        2. 'run_command_in_background' - Runs a shell command in the background:
           - Use this for opening applications (firefox, chrome, xterm, etc.)
           - Commands start immediately without waiting for output
           - Perfect for GUI applications that run indefinitely

        DECISION GUIDELINES:
        - Use 'run_command' for: file operations, checking status, getting output, any command where you need results
        - Use 'run_command_in_background' for: opening browsers, editors, terminals, any GUI application

        You will be given a subtask from the Orchestrator. Execute the appropriate commands to complete it.
        """
        
        # Gather all methods from the toolkit instance
        programmer_tool_methods = [
            self.programmer_tools.run_command,
            self.programmer_tools.run_command_in_background,
        ]

        print(f"👨‍💻 [PROGRAMMER] Initializing with model: {self.programmer_model}")
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

        CRITICAL EFFICIENCY PRINCIPLE: Minimize grounding model calls by preferring keyboard actions over mouse clicks whenever possible. Use Enter, Tab, arrows, and shortcuts instead of clicking buttons and UI elements.

        CRITICAL: You MUST use the function name "computer" (not "function_name" or any other name) when making tool calls.

        You will be given a subtask from the Orchestrator and views of the screen.
        Your task is to identify visual elements on the screen and use them to accomplish the subtask with maximum efficiency.

        IMPORTANT: For each action you take, you must also predict what the screen will look like after the action executes. Include this prediction in your response as: "Expected screen state: [brief description of what the screen should look like after this action]".

        On subsequent turns, you will receive both the "BEFORE ACTION" image (what you saw when deciding on the previous action) and the "AFTER ACTION" image (actual result of that action), allowing you to compare your prediction with reality and learn from discrepancies.

        TOOL USAGE RULES:
        1. ALWAYS use the function name "computer" for all tool calls
        2. PRIORITIZE actions that DON'T require grounding model calls (keypress, type without element_description)
        3. For typing: FIRST click on the input field to focus it, THEN use computer(action='type', text='text to type')
        4. For clicking: ONLY use computer(action='click', element_description='...') when absolutely necessary
        5. For keyboard shortcuts: Use computer(action='keypress', keys=['key']) instead of clicking buttons
        6. For form submission: Use Enter key instead of clicking submit buttons
        7. For navigation: Use Tab, arrow keys instead of clicking when possible

        ELEMENT DESCRIPTION GUIDELINES:
        - Be specific and descriptive (e.g., "the blue login button with text 'Log In'" not just "button")
        - Include visual characteristics like color, text, position, or size
        - Use consistent descriptions but different in wording for the same element across multiple attempts

        CRITICAL EFFICIENCY WORKFLOW:
        - MINIMIZE grounding model calls by preferring keyboard actions over mouse clicks
        - For search/forms: Type text, then press Enter instead of clicking search/submit buttons
        - For navigation: Use Tab, arrow keys, Page Up/Down instead of scrolling or clicking
        - For common actions: Use keyboard shortcuts (Ctrl+A, Ctrl+C, Ctrl+V, etc.)
        - Only click when keyboard navigation is impossible or inefficient
        - For typing: Click input field to focus, then type + Enter when possible
        - ERROR RECOVERY: If action result is unexpected, immediately try keyboard recovery:
          - Wrong page/navigation: Alt+Left Arrow (browser back)
          - Wrong text input: Ctrl+Z (undo)
          - Modal/dialog appeared: ESC (cancel)
          - Page didn't load: F5 (refresh)
          - If all keyboard methods fail: Click browser back button (requires grounding)

        WORKFLOW:
        1. Analyze the screen and think about the most efficient way to accomplish the task
        2. Prioritize keyboard-based actions (Enter, Tab, arrows, shortcuts) over mouse clicks
        3. For forms/search: Focus input field → Type text → Press Enter (avoids clicking buttons)
        4. For navigation: Use keyboard shortcuts and arrow keys when possible
        5. Only use mouse clicks (with grounding) when keyboard navigation is impossible
        6. Make computer calls with the correct function name "computer"
        7. Wait for the result and evaluate if the action was successful
        8. If unsuccessful, try keyboard alternatives first, then mouse clicks as last resort
        9. ERROR RECOVERY: If screenshot shows unexpected state, use these recovery methods (in priority order):
           - Browser: Alt+Left Arrow (back) or Ctrl+[ (back in some browsers)
           - General: ESC key to cancel dialogs/modals
           - Text editing: Ctrl+Z (undo)
           - Navigation: Ctrl+Home (go to top) or Ctrl+End (go to bottom)
           - Browser refresh: F5 or Ctrl+R (if page didn't load properly)
           - LAST RESORT (requires grounding): Click browser back button with computer(action='click', element_description='browser back button arrow')
        10. Once the subtask is complete, respond with a final message summarizing your actions

        EFFICIENCY RULES (HIGHEST PRIORITY):
        - MINIMIZE mouse clicks - use keyboard actions whenever possible
        - For search boxes: Type query + press Enter (no button clicking needed)
        - For forms: Fill fields + press Enter or Tab to submit
        - For navigation: Use arrow keys, Tab, Page Up/Down, Home/End
        - For selection: Use Shift+arrow keys instead of drag-selecting
        - For copy/paste: Use Ctrl+C, Ctrl+V instead of right-click menus
        - ERROR RECOVERY (keyboard-first):
          - Browser back: Alt+Left Arrow or Ctrl+[
          - Cancel/escape: ESC key
          - Undo: Ctrl+Z
          - Page navigation: Ctrl+Home/End
          - Refresh: F5 or Ctrl+R
          - Last resort (grounding required): Click browser back button

        GUI OPERATION RULES (when mouse clicks are necessary):
        - To open any app on the desktop, you MUST use double_click, NOT single click
        - For app icons: computer(action='double_click', element_description='app name icon')
        - For buttons and links: computer(action='click', element_description='button description') - USE AS LAST RESORT
        - For text fields: FIRST use computer(action='click', element_description='input field description') to focus the field, THEN use computer(action='type', text='text to type') to input text

        Remember: Use "computer" as the function name, be specific in element descriptions, and evaluate results before making additional attempts. If the results meet the requirements, you can end the task.
        """
        print(f"🎭 [GUI OPERATOR] Initializing with model: {self.gui_operator_model}")
        return ComputerAgent(
            model=self.gui_operator_model,
            tools=[self.gui_operator_computer],
            instructions=instructions,
            verbosity=logging.WARNING,
            quantization_bits=8,
            trust_remote_code=True,  # Required for InternVL models
            screenshot_delay=1.0,  # Wait 1 second after actions before screenshot
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

        content = [{"type": "text", "text": f"{prompt}\n\nHistory:\n{json.dumps(filtered_history, indent=2)}"}]

        if screenshot_b64:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}})

        summary_messages = [{
            "role": "user",
            "content": content
        }]

        try:
            response = await litellm.acompletion(
                model="gemini/gemini-2.5-flash",
                messages=summary_messages,
            )
            summary = response.choices[0].message.content or "No summary available."
            return summary.strip()
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
            return "Could not summarize the interaction."

    async def run(self, task: str):
        """Runs the CoAct-1 agent system on a given task."""
        print(f"\n🎬 [COACT-1 RUN] Starting task: '{task}'")

        # Take initial screenshot for orchestrator context
        print("📸 Taking initial screenshot for orchestrator...")
        # Initialize the computer handler if needed
        if hasattr(self.orchestrator_tools._handler, '_initialize'):
            await self.orchestrator_tools._handler._initialize()
        # Get the screenshot from the computer handler
        initial_screenshot_b64 = await self.orchestrator_tools._handler.screenshot()
        print("   ✅ Initial screenshot taken")

        # Create initial user message with task and screenshot
        initial_content = [
            {"type": "text", "text": f"{task}\n\nHere is the current screen. What is the next subtask?"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{initial_screenshot_b64}"}}
        ]

        orchestrator_history: List[Dict[str, Any]] = [{"role": "user", "content": initial_content}]
    
        for i in range(10): # Max 10 steps
            print(f"\n--- Step {i+1} ---")

            # For subsequent steps, add a simple prompt (screenshots will come from sub-agent summaries)
            orchestrator_history.append({
                "role": "user",
                "content": "What is the next subtask based on the current progress? (or you can call task_completed)"
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

            # Handle both direct format and nested function format
            function_info = delegation.get("function", delegation)
            tool_name = function_info.get("name")
            arguments = function_info.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
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

            # 3. Run sub-agent with the task and current image context
            # Get the current screenshot from orchestrator history
            current_image_b64 = get_last_image_b64(orchestrator_history)

            # Create sub-agent history starting with the subtask
            if current_image_b64:
                # Include the image directly in the subtask message
                sub_agent_history = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{subtask}\n\nHere is the current screen state:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{current_image_b64}"}}
                    ]
                }]
                print("   🖼️ Provided image context to sub-agent")
            else:
                sub_agent_history = [{
                    "role": "user",
                    "content": subtask
                }]

            async for result in sub_agent.run(sub_agent_history):
                sub_agent_history.extend(result.get("output", []))

            # 4. Get the latest screenshot from the sub-agent's history for the summary
            summary_screenshot_b64 = get_last_image_b64(sub_agent_history)

            # 5. Summarize and update Orchestrator history
            print("📝 Summarizing sub-task...")
            summary = await self._summarize_interaction(sub_agent_history, summary_screenshot_b64)
            print(f"Summary: {summary}")

            # Create a message with both summary text and the final screenshot for orchestrator evaluation
            orchestrator_result_content = [
                {"type": "text", "text": f"Sub-task completed. Summary: {summary}\n\nHere is the final screen state. Evaluate whether the sub-task was successful and determine the next action."}
            ]

            if summary_screenshot_b64:
                orchestrator_result_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{summary_screenshot_b64}"}
                })

            orchestrator_history.append({
                "type": "function_call_output",
                "call_id": delegation.get("call_id", f"call_{hash(str(delegation))}"),
                "output": orchestrator_result_content,
            })

    async def run_direct_gui(self, task: str):
        """Runs the CoAct-1 system but directly delegates the task to the GUI Operator."""
        print(f"\n🎬 [COACT-1 DIRECT GUI] Starting task: '{task}'")

        # Take initial screenshot for GUI operator context
        print("📸 Taking initial screenshot for GUI operator...")
        # Initialize the computer handler if needed
        if hasattr(self.orchestrator_tools._handler, '_initialize'):
            await self.orchestrator_tools._handler._initialize()
        # Get the screenshot from the computer handler
        initial_screenshot_b64 = await self.orchestrator_tools._handler.screenshot()
        print("   ✅ Initial screenshot taken")

        orchestrator_history: List[Dict[str, Any]] = [{"role": "user", "content": task}]

        print("🎭 [DIRECT GUI] Delegating directly to GUI Operator...")

        # 1. Add prompt for direct GUI task
        orchestrator_history.append({
            "role": "user",
            "content": f"Direct GUI task: {task}"
        })

        # 2. Instead of Orchestrator → directly delegate to GUI Operator
        subtask = "Double click on the Firefox web browser icon on the screen."
        print(f"🖱️ Directly delegating to GUI Operator: {subtask}")

        sub_agent = self.gui_operator

        # Create sub-agent history with image context
        if initial_screenshot_b64:
            sub_agent_history = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{subtask}\n\nHere is the current screen state:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{initial_screenshot_b64}"}}
                ]
            }]
            print("   🖼️ Provided image context to GUI operator")
        else:
            sub_agent_history = [{
                "role": "user",
                "content": subtask
            }]

        # 3. Run the GUI Operator
        async for result in sub_agent.run(sub_agent_history):
            sub_agent_history.extend(result.get("output", []))

        # 4. Get the latest screenshot
        summary_screenshot_b64 = get_last_image_b64(sub_agent_history)

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
        orchestrator_model_name = "gemini/gemini-2.5-flash"
        programmer_model_name = "gemini/gemini-2.5-flash"
        gui_operator_model_name = "huggingface-local/OpenGVLab/InternVL3_5-4B+gemini/gemini-2.5-flash"

        coact_system = CoAct1(
            computer=computer_instance,
            orchestrator_model=orchestrator_model_name,
            programmer_model=programmer_model_name,
            gui_operator_model=gui_operator_model_name,
        )

        # Example Task
        task = "go to youtube and play the never gonna give you up video"
        
        await coact_system.run(task)

    except Exception as e:
        logger.error(f"❌ Error running example: {e}")
        raise
    finally:
        if computer_instance:
            # await computer_instance.stop()
            print("\n🧹 Computer connection closed")

if __name__ == "__main__":
    asyncio.run(main())
