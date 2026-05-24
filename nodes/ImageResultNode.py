import nodes

class ImageResultNode(nodes.SaveImage):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "save": ("BOOLEAN", {"default": False}),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    FUNCTION = "execute"
    CATEGORY = "🚀🌍 AstroCorp 🌍🚀"

    def execute(self, image, save=False, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        preview = nodes.PreviewImage()
        result = preview.save_images(image, prompt=prompt, extra_pnginfo=extra_pnginfo)

        if save:
            super().save_images(image, filename_prefix, prompt, extra_pnginfo)

        return result


NODE_CLASS_MAPPINGS = {
    "ImageResultNode": ImageResultNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageResultNode": "Image Result",
}
