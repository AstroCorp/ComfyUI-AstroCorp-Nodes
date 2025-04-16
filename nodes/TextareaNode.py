class TextareaNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "input_text": ("STRING", {"forceInput": True}),
            },
            "hidden": {
                "text": ("STRING", {"multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "AstroCorp"

    def execute(self, input_text="", text=""):
        output_text = input_text

        if not input_text:
            output_text = text

        return {
            "ui": {
                "string": [
                    output_text,
                ]
            },
            "result": (output_text,),
        }

NODE_CLASS_MAPPINGS = {
    "TextareaNode": TextareaNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TextareaNode": "Textarea"
} 