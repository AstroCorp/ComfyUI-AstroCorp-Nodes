class MergeTextsNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "separator": ("STRING", {"default": ", "}),
            },
            "hidden": {
                "text_result": ("STRING", {"multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "execute"
    CATEGORY = "🚀🌍 AstroCorp 🌍🚀"

    def execute(self, separator="", **kwargs):
        output_text = separator.join(kwargs.values())

        return {
            "ui": {
                "string": [
                    output_text,
                ]
            },
            "result": (output_text,),
        }

NODE_CLASS_MAPPINGS = {
    "MergeTextsNode": MergeTextsNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MergeTextsNode": "Merge Texts"
} 