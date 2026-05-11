import torch

import comfy.model_management

MAX_RESOLUTION = 16384


class EmptyLatentImageWithRotate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 512, "min": 16, "max": MAX_RESOLUTION, "step": 8}),
                "height": ("INT", {"default": 512, "min": 16, "max": MAX_RESOLUTION, "step": 8}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 4096}),
            }
        }

    RETURN_TYPES = ("LATENT",)
    FUNCTION = "generate"
    CATEGORY = "🚀🌍 AstroCorp 🌍🚀"

    def generate(self, width, height, batch_size=1):
        latent = torch.zeros(
            [batch_size, 4, height // 8, width // 8],
            device=comfy.model_management.intermediate_device(),
            dtype=comfy.model_management.intermediate_dtype(),
        )
        return ({"samples": latent, "downscale_ratio_spacial": 8},)


NODE_CLASS_MAPPINGS = {
    "EmptyLatentImageWithRotate": EmptyLatentImageWithRotate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmptyLatentImageWithRotate": "Empty Latent Image With Rotate",
}
