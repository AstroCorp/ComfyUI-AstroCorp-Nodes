# ComfyUI AstroCorp Nodes

A collection of personal ComfyUI nodes designed to enhance and automate workflows.

- [Nodes](#nodes)
- [Installation](#installation)
- [Usage](#usage)

## Nodes

### Load Upscale Model+ / Upscale Image (using Model)

Same as ComfyUI’s upscaler, using files from `models/upscale_models`, plus support for ONNX models. The first ONNX run compiles a TensorRT engine under `models/tensorrt/upscaler`.

![Upscale nodes](./examples/upscaler_nodes.png)

### Load Image Clipboard

Loads an image like ComfyUI’s Load Image node, with an extra button to use the clipboard image.

![Load Image Clipboard](./examples/load_image_clipboard_node.png)

### Image Result

Combining the "Preview Image" and "Save Image" nodes of comfyUI.

![Image Result](./examples/image_result_node.png)

### Video Result

Same as ComfyUI’s Save Video, plus a toggle to preview without saving.

![Video Result](./examples/video_result_node.png)

### Empty Latent Image With Rotate

Same as ComfyUI’s Empty Latent Image, plus a button to swap width and height.

![Empty Latent Image With Rotation](./examples/empty_latent_image_with_rotate_node.png)

### Textarea

A text field that allows manual text input and also previews text from other nodes.

![Textarea Node](./examples/textarea_node.png)

## Merge Texts

Merge different input texts into a single output text, with the option to specify a custom separator between them.

![Merge Texts Node](./examples/merge_texts_node.png)

## Installation

Add this repository to your ComfyUI custom nodes directory:
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/your-username/comfyui_astro_nodes.git
```

ONNX upscaling uses TensorRT when it is installed in the ComfyUI Python environment. If TensorRT is missing, install `onnxruntime-gpu` (or `onnxruntime`) as a fallback.

> [!NOTE]  
> ComfyUI AstroCorp Nodes now available in ComfyUI Manager.

## Usage

After installation, restart ComfyUI to load the new nodes. The nodes will appear in the node menu under the "AstroCorp" category.
