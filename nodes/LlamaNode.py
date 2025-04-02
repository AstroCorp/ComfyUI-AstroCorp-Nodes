import torch
from transformers import pipeline

class LlamaNode:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text": ("STRING", {"multiline": True, "forceInput": True}),
                "system_role": ("STRING", {"multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "execute"
    CATEGORY = "AstroCorp"

    def execute(self, input_text, system_role):
        chat = [
            {"role": "system", "content": system_role},
            {"role": "user", "content": input_text},
        ]

        model = pipeline(
            task="text-generation", 
            model="meta-llama/Llama-3.2-1B-Instruct", 
            torch_dtype=torch.bfloat16, 
            device_map="auto"
        )

        response = model(chat, max_new_tokens=512)

        return response[0]["generated_text"][-1]["content"]

NODE_CLASS_MAPPINGS = {
    "LlamaNode": LlamaNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LlamaNode": "Llama Node"
}
