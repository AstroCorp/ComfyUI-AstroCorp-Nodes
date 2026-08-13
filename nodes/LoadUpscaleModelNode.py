import os

import folder_paths

from .upscale_common import (
    CATEGORY,
    ONNX_EXT,
    UPSCALE_FOLDER,
    load_onnx_upscale_model,
    load_torch_upscale_model,
    upscale_model_names,
)


class LoadUpscaleModelNode:
    """Combo con los archivos de models/upscale_models (PyTorch y ONNX)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"model_name": (upscale_model_names(),)}}

    RETURN_TYPES = ("UPSCALE_MODEL",)
    FUNCTION = "load_model"
    CATEGORY = CATEGORY
    DESCRIPTION = "Loads ComfyUI upscale models (.pth, .pt, .safetensors, …) and ONNX models from models/upscale_models."

    def load_model(self, model_name, **_unused):
        # **_unused absorbe el widget precision de workflows antiguos.
        model_path = folder_paths.get_full_path_or_raise(UPSCALE_FOLDER, model_name)
        if os.path.splitext(model_path)[1].lower() == ONNX_EXT:
            return (load_onnx_upscale_model(model_path, model_name),)
        return (load_torch_upscale_model(model_path),)


NODE_CLASS_MAPPINGS = {
    "AstroCorpLoadUpscaleModel": LoadUpscaleModelNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AstroCorpLoadUpscaleModel": "Load Upscale Model+",
}
