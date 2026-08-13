import torch

from comfy import model_management
import comfy.utils

from .upscale_common import CATEGORY, ENGINE_MAX_DIM, OnnxUpscaleModel


class ImageUpscaleWithModelNode:
    """Upscale con tiling como el nodo nativo de ComfyUI."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "upscale_model": ("UPSCALE_MODEL",),
                "image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "upscale"
    CATEGORY = CATEGORY

    def upscale(self, upscale_model, image):
        if isinstance(upscale_model, OnnxUpscaleModel):
            device = model_management.get_torch_device()
        else:
            # PyTorch: ComfyUI mueve pesos a GPU y estima VRAM como el nodo oficial.
            device = upscale_model.patcher.load_device
            memory_required = (512 * 512 * 3) * image.element_size() * max(upscale_model.scale, 1.0) * 384.0
            memory_required += image.nelement() * image.element_size()
            model_management.load_models_gpu(
                [upscale_model.patcher], memory_required=memory_required, force_full_load=True
            )

        in_img = image.movedim(-1, -3).to(device)
        tile = int(getattr(upscale_model, "tile_size", ENGINE_MAX_DIM))
        overlap = 32
        output_device = model_management.intermediate_device()
        oom = True
        while oom:
            try:
                steps = in_img.shape[0] * comfy.utils.get_tiled_scale_steps(
                    in_img.shape[3], in_img.shape[2], tile_x=tile, tile_y=tile, overlap=overlap
                )
                pbar = comfy.utils.ProgressBar(steps)
                s = comfy.utils.tiled_scale(
                    in_img,
                    lambda a: upscale_model(a.float()),
                    tile_x=tile,
                    tile_y=tile,
                    overlap=overlap,
                    upscale_amount=upscale_model.scale,
                    pbar=pbar,
                    output_device=output_device,
                )
                oom = False
            except Exception as e:
                # Si no es OOM, se relanza. Si es OOM, se parte el tile a la mitad.
                model_management.raise_non_oom(e)
                tile //= 2
                if tile < 128:
                    raise e

        s = torch.clamp(s.movedim(-3, -1), min=0, max=1.0).to(model_management.intermediate_dtype())
        return (s,)


NODE_CLASS_MAPPINGS = {
    "AstroCorpImageUpscaleWithModel": ImageUpscaleWithModelNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AstroCorpImageUpscaleWithModel": "Upscale Image (using Model)",
}
