class TextFileEditorNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "execute"
    CATEGORY = "🚀🌍 AstroCorp 🌍🚀"

    def execute(self, text):
        return (text,)


NODE_CLASS_MAPPINGS = {
    "TextFileEditorNode": TextFileEditorNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TextFileEditorNode": "Text File Editor",
}
