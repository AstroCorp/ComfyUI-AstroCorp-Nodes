from transformers import pipeline
from huggingface_hub import login

class InstructNode:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text": ("STRING", {"multiline": True, "forceInput": True}),
                "system_role": ("STRING", {"multiline": True}),
                "model_id": ("STRING", {"default": "Qwen/Qwen2.5-7B-Instruct", "multiline": False}),
                "hf_token": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "execute"
    CATEGORY = "AstroCorp"

    def execute(self, input_text, system_role, model_id, hf_token):
        if hf_token.strip():
            login(token=hf_token)
            
        pipe = pipeline("text-generation", model=model_id)
        messages = [
            {"role": "system", "content": system_role},
            {"role": "user", "content": input_text},
        ]
        outputs = pipe(messages)
        response = outputs[0]["generated_text"][-1]
        content = response["content"]

        return (content,)

NODE_CLASS_MAPPINGS = {
    "InstructNode": InstructNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "InstructNode": "Instruct"
}
