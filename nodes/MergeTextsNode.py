class MergeTextsNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text_1": ("STRING", {"forceInput": True}),
                "input_text_2": ("STRING", {"forceInput": True}),
                "separator": ("STRING", {"default": " "}),
            },
            "hidden": {
                "text_result": ("STRING", {"multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "execute"
    CATEGORY = "🚀🌍 AstroCorp 🌍🚀"

    def execute(self, input_text_1="", input_text_2="", separator=""):
        output_text = input_text_1 + separator + input_text_2

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