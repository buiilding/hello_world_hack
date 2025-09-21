"""
UI-Venus-Ground agent loop implementation for click prediction.

This agent loop uses the UIVenusGroundModel to provide grounding functionality
for UI-Venus-Ground models.
"""

from typing import List, Dict, Any, Optional, Tuple
import base64
from io import BytesIO
from PIL import Image

# Hugging Face imports are local to avoid hard dependency at module import
try:
    import torch
    from transformers import Qwen2_5_VLForConditionalGeneration, AutoTokenizer, AutoProcessor
    from qwen_vl_utils import process_vision_info
    HF_AVAILABLE = True
except Exception:
    HF_AVAILABLE = False

# Agent loop imports
from ..decorators import register_agent
from ..types import AgentCapability
from .base import AsyncAgentConfig


class UIVenusGroundModel:
    """UI-Venus-Ground model handler for grounding UI elements to coordinates.

    This model takes an instruction and image, and returns bounding box coordinates
    for the described UI element.
    """

    def __init__(self, model_name: str, device: str = "auto", trust_remote_code: bool = False, quantization_bits: Optional[int] = None) -> None:
        if not HF_AVAILABLE:
            raise ImportError(
                "Required dependencies not found. Install with: pip install transformers torch qwen-vl-utils bitsandbytes accelerate"
            )
        self.model_name = model_name
        self.device = device
        self.trust_remote_code = trust_remote_code
        self.quantization_bits = quantization_bits
        self.model = None
        self.tokenizer = None
        self.processor = None
        self.generation_config = {
            "max_new_tokens": 2048,
            "do_sample": False
            # Removed temperature since do_sample=False uses greedy decoding
        }
        self._load()

    def _load(self) -> None:
        # Load model
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        load_params = {
            "trust_remote_code": self.trust_remote_code,
            "attn_implementation": "flash_attention_2"
        }

        if self.quantization_bits == 8:
            if not torch.cuda.is_available():
                raise ImportError("8-bit quantization is only available with CUDA.")
            load_params["load_in_8bit"] = True
            load_params["device_map"] = "auto"
        elif self.quantization_bits == 4:
            if not torch.cuda.is_available():
                 raise ImportError("4-bit quantization is only available with CUDA.")
            load_params["load_in_4bit"] = True
            load_params["device_map"] = "auto"
        else:
            load_params["torch_dtype"] = dtype
            load_params["device_map"] = self.device

        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                        self.model_name,
                        **load_params
                    ).eval()

        # Load tokenizer and processor
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=self.trust_remote_code)
        # Use slow processor to avoid the fast processor warning
        self.processor = AutoProcessor.from_pretrained(self.model_name, use_fast=False)

    def generate(self, messages: List[Dict[str, Any]], max_new_tokens: int = 128) -> str:
        """Generate text for the given HF-format messages.

        For UI grounding, we expect messages to contain an image and instruction.
        Returns bounding box coordinates in format: [x1,y1,x2,y2]
        """
        assert self.model is not None and self.processor is not None

        # Extract instruction and image from messages
        instruction = ""
        image_path = None

        for message in messages:
            if message.get("role") == "user":
                content = message.get("content", [])
                for item in content:
                    if item.get("type") == "text":
                        instruction = item.get("text", "")
                    elif item.get("type") == "image":
                        image_path = item.get("image", "")

        if not instruction or not image_path:
            return "[0,0,0,0]"  # Return empty bbox if missing data

        # Prepare the prompt
        prompt_origin = 'Outline the position corresponding to the instruction: {}. The output should be only [x1,y1,x2,y2].'
        full_prompt = prompt_origin.format(instruction)

        # Set image processing parameters
        min_pixels = 2000000
        max_pixels = 4800000

        # Prepare messages for Qwen model
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image": image_path,
                        "min_pixels": min_pixels,
                        "max_pixels": max_pixels
                    },
                    {"type": "text", "text": full_prompt},
                ],
            }
        ]

        # Apply chat template and tokenize
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        model_inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt"
        ).to(self.model.device)

        # Generate response
        with torch.no_grad():
            generated_ids = self.model.generate(**model_inputs, **self.generation_config)

        # Trim prompt tokens from output
        generated_ids_trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        # Decode
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )

        return output_text[0] if output_text else "[0,0,0,0]"

    def predict_click(self, image_b64: str, instruction: str) -> Optional[Tuple[int, int]]:
        """Predict click coordinates for grounding.

        Args:
            image_b64: Base64 encoded image
            instruction: Description of element to click

        Returns:
            Tuple of (x, y) coordinates or None if prediction fails
        """
        print(f"🔬 UI-Venus predict_click called with instruction: '{instruction}'")
        try:
            # Ensure we have a clean base64 string
            if isinstance(image_b64, bytes):
                image_b64 = image_b64.decode("utf-8", errors="ignore")
            if image_b64.startswith("data:image"):
                image_b64 = image_b64.split(",")[-1]

            # Decode base64 → bytes
            image_data = base64.b64decode(image_b64)
            image = Image.open(BytesIO(image_data))
            print(f"   📏 Image size: {image.size}")

            # Save to temporary file (required for Qwen model)
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                image.save(temp_file.name)
                temp_path = temp_file.name
            print(f"   💾 Saved image to: {temp_path}")

            try:
                # Prepare messages for model
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": temp_path},
                            {"type": "text", "text": instruction}
                        ]
                    }
                ]

                print(f"   🤖 [GROUNDING MODEL: {self.model_name}] Processing instruction: '{instruction}'")
                # Generate bounding box
                bbox_str = self.generate(messages)
                print(f"   📦 [GROUNDING MODEL] Raw model output: '{bbox_str}'")

                # Parse bounding box coordinates
                try:
                    box = eval(bbox_str)
                    print(f"   📐 Parsed bounding box: {box}")
                    if isinstance(box, list) and len(box) == 4:
                        # The model returns ABSOLUTE pixel coordinates, not normalized ones.
                        abs_x1 = float(box[0])
                        abs_y1 = float(box[1])
                        abs_x2 = float(box[2])
                        abs_y2 = float(box[3])

                        # Return center point of bounding box
                        center_x = int((abs_x1 + abs_x2) / 2)
                        center_y = int((abs_y1 + abs_y2) / 2)

                        print(f"   🎯 [GROUNDING MODEL] Calculated center coordinates: ({center_x}, {center_y})")
                        return (center_x, center_y)
                    else:
                        print(f"   ❌ Invalid bounding box format: {box}")
                except (ValueError, SyntaxError, IndexError) as parse_error:
                    print(f"   ❌ Failed to parse bounding box: {parse_error}")

            finally:
                # Clean up temporary file unless KEEP_DEBUG_IMG is set
                if not os.getenv("KEEP_DEBUG_IMG"):
                    os.unlink(temp_path)
                else:
                    print(f"   🧩 KEEP_DEBUG_IMG set, keeping temp file: {temp_path}")

        except Exception as e:
            print(f"   💥 Error in predict_click: {e}")
            import traceback
            traceback.print_exc()

        print(f"   🚫 Returning None")
        return None


@register_agent(models=r"(?i).*UI.*Venus.*Ground.*|.*ui.*venus.*ground.*")
class UIVenusGroundConfig(AsyncAgentConfig):
    """
    UI-Venus-Ground agent configuration for grounding UI elements to coordinates.

    This agent loop loads and uses the UIVenusGroundModel to predict click coordinates
    based on image and instruction inputs.
    """

    def __init__(self):
        self.model_instance: Optional[UIVenusGroundModel] = None

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
        UI-Venus-Ground doesn't support step prediction, only click prediction.
        This method is implemented to satisfy the protocol but will raise an error.
        """
        raise NotImplementedError(
            "UI-Venus-Ground agent only supports click prediction, not step prediction. "
            "Use predict_click() method instead."
        )

    async def predict_click(
        self,
        model: str,
        image_b64: str,
        instruction: str,
        **kwargs
    ) -> Optional[Tuple[int, int]]:
        """
        Predict click coordinates using UI-Venus-Ground model.

        Args:
            model: Model name (should match UI-Venus-Ground pattern)
            image_b64: Base64 encoded image
            instruction: Description of element to click

        Returns:
            Tuple of (x, y) coordinates or None if prediction fails
        """
        try:
            # Initialize model if not already done
            if self.model_instance is None:
                print(f"🔧 Initializing UI-Venus-Ground model: {model}")
                self.model_instance = UIVenusGroundModel(
                    model_name=model,
                    device="auto",
                    trust_remote_code=False
                )

            # Use the model's predict_click method
            print(f"🎯 [GROUNDING MODEL: {model}] Predicting click for: '{instruction}'")
            print("   🖼️  Image provided to grounding model")

            # Initialize model if not already done
            if self.model_instance is None:
                print(f"   🔧 Initializing UI-Venus-Ground model: {model}")
                self.model_instance = UIVenusGroundModel(
                    model_name=model,
                    device="auto",
                    trust_remote_code=False
                )
                print("   ✅ Model initialized successfully")

            print(f"   🤖 Calling predict_click with instruction: '{instruction}'")
            coordinates = self.model_instance.predict_click(image_b64, instruction)

            if coordinates:
                print(f"✅ [GROUNDING MODEL: {model}] Prediction successful: ({coordinates[0]}, {coordinates[1]})")
                return coordinates
            else:
                print(f"❌ [GROUNDING MODEL: {model}] Prediction failed")
                return None

        except Exception as e:
            print(f"💥 Error in UI-Venus-Ground prediction: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_capabilities(self) -> List[AgentCapability]:
        """
        Get list of capabilities supported by this agent config.

        Returns:
            List of capability strings
        """
        return ["click"]