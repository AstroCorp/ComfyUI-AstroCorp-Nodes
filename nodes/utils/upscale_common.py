"""
Lógica compartida de upscale: listado de modelos, carga PyTorch/ONNX y engine TensorRT.
Los nodos de ComfyUI viven en LoadUpscaleModelNode e ImageUpscaleWithModelNode.
"""

import importlib.util
import logging
import os
import re
import time

import numpy as np
import torch
from spandrel import ImageModelDescriptor, ModelLoader

import folder_paths
from comfy import model_management
import comfy.model_patcher
import comfy.utils

# Arquitecturas extra de spandrel (no comerciales). Si no está el paquete, se ignora.
try:
    from spandrel_extra_arches import EXTRA_REGISTRY
    from spandrel import MAIN_REGISTRY
    MAIN_REGISTRY.add(*EXTRA_REGISTRY)
except Exception:
    pass

CATEGORY = "🚀🌍 AstroCorp 🌍🚀/upscaling"
UPSCALE_FOLDER = "upscale_models"
ONNX_EXT = ".onnx"

# Rango espacial del engine TensorRT (NCHW).
# ComfyUI recorta en tiles de 512 y baja a 256 si hay OOM.
# Por debajo de 256 algunas convoluciones ESRGAN fallan al ejecutar el engine.
ENGINE_MIN_DIM = 256
ENGINE_OPT_DIM = 512
ENGINE_MAX_DIM = 512
LOGGER = logging.getLogger("AstroCorp")

# TensorRT-RTX (p. ej. en Blackwell) rompe estas convs ESRGAN; se prioriza TensorRT completo.
if importlib.util.find_spec("tensorrt") is not None:
    import tensorrt as trt
    TRT_AVAILABLE = True
elif importlib.util.find_spec("tensorrt_rtx") is not None:
    import tensorrt_rtx as trt
    TRT_AVAILABLE = True
else:
    trt = None
    TRT_AVAILABLE = False

# Fallback si no hay TensorRT o CUDA.
if importlib.util.find_spec("onnxruntime") is not None:
    import onnxruntime as ort
    ORT_AVAILABLE = True
else:
    ort = None
    ORT_AVAILABLE = False

_TRT_LOGGER = trt.Logger(trt.Logger.WARNING) if TRT_AVAILABLE else None

# Dtypes de TensorRT → PyTorch (el nombre llega como DataType.FLOAT, etc.).
_TRT_DTYPE = {
    "FLOAT": torch.float32,
    "HALF": torch.float16,
    "BF16": torch.bfloat16,
    "INT32": torch.int32,
    "INT8": torch.int8,
    "BOOL": torch.bool,
}


def upscale_model_names():
    """
    Nombres de archivo para el combo del loader.

    No usa get_filename_list: ComfyUI cachea esa lista antes de cargar custom nodes
    y nunca incluye .onnx. Aquí se recorre la carpeta y se añade la extensión a mano.
    """
    names = set()
    folders, exts = folder_paths.folder_names_and_paths[UPSCALE_FOLDER]
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        files, _ = folder_paths.recursive_search(folder, excluded_dir_names=[".git"])
        names.update(folder_paths.filter_files_extensions(files, set(exts) | {ONNX_EXT}))
    return sorted(names) or [""]


def _scale_from_filename(filename):
    """Intenta leer el factor (2x, 4x, _x4…) del nombre del archivo."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    match = re.search(r"(?:^|[_\-])(\d+)x(?:[_\-]|$)", stem, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"[_\-]x(\d+)(?:[_\-]|$)", stem, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _spatial_scale(out_h, in_h, model_name):
    """
    Factor de upscale = alto_salida / alto_entrada.
    Si la forma no cuadra, se usa el número del nombre del archivo.
    """
    scale = out_h / in_h
    if scale == int(scale) and scale >= 1:
        return int(scale)
    named = _scale_from_filename(model_name)
    if named is None:
        raise RuntimeError(f"No se pudo deducir el factor de escala ONNX ({out_h}/{in_h})")
    return named


def load_torch_upscale_model(model_path):
    """Misma ruta que el loader nativo de ComfyUI: state dict → spandrel → patcher."""
    state_dict = comfy.utils.load_torch_file(model_path, safe_load=True)
    # Algunos checkpoints guardan el modelo envuelto en nn.DataParallel (prefijo module.).
    if "module.layers.0.residual_group.blocks.0.norm1.weight" in state_dict:
        state_dict = comfy.utils.state_dict_prefix_replace(state_dict, {"module.": ""})
    model = ModelLoader().load_from_state_dict(state_dict).eval()
    if not isinstance(model, ImageModelDescriptor):
        raise Exception("Upscale model must be a single-image model.")
    model.patcher = comfy.model_patcher.CoreModelPatcher(
        model.model,
        load_device=model_management.get_torch_device(),
        offload_device=model_management.unet_offload_device(),
    )
    return model


def _trt_to_torch_dtype(dtype):
    """Convierte un DataType de TensorRT al dtype equivalente de torch."""
    name = str(dtype).split(".")[-1].upper()
    if name not in _TRT_DTYPE:
        raise RuntimeError(f"Unsupported TensorRT dtype: {dtype}")
    return _TRT_DTYPE[name]


def _dims_list(dims):
    """TensorRT devuelve Dims; lo pasamos a lista de int (los -1 son ejes dinámicos)."""
    return [int(dims[i]) for i in range(len(dims))]


def _create_trt_network(builder):
    """
    Crea la red TensorRT según la versión instalada.

    TRT ≤10: EXPLICIT_BATCH + flag FP16 del builder.
    TRT 11: STRONGLY_TYPED; fp16/fp32 salen de los tensores del ONNX.
    """
    flags = 0
    creation = trt.NetworkDefinitionCreationFlag
    if hasattr(creation, "EXPLICIT_BATCH"):
        flags |= 1 << int(creation.EXPLICIT_BATCH)
    elif hasattr(creation, "STRONGLY_TYPED"):
        flags |= 1 << int(creation.STRONGLY_TYPED)
    return builder.create_network(flags)


class TensorrtUpscaleEngine:
    """Compila, carga y ejecuta un engine TensorRT a partir de un ONNX de upscale."""

    def __init__(self, engine_path):
        self.engine_path = engine_path
        self.min_dim = ENGINE_MIN_DIM
        self.max_dim = ENGINE_MAX_DIM
        self.engine = None
        self.context = None
        self.stream = None
        self.input_name = None
        self.output_name = None
        self.tensors = {}
        self._bound_shape = None

    def build(self, onnx_path):
        """Parsea el ONNX, define el perfil dinámico y escribe el .trt en disco."""
        builder = trt.Builder(_TRT_LOGGER)
        network = _create_trt_network(builder)
        parser = trt.OnnxParser(network, _TRT_LOGGER)
        if hasattr(trt, "OnnxParserFlag") and hasattr(trt.OnnxParserFlag, "NATIVE_INSTANCENORM"):
            parser.set_flag(trt.OnnxParserFlag.NATIVE_INSTANCENORM)
        if not parser.parse_from_file(onnx_path):
            errors = [str(parser.get_error(i)) for i in range(parser.num_errors)]
            raise RuntimeError("Failed to parse ONNX for TensorRT:\n" + "\n".join(errors))

        input_tensor = network.get_input(0)
        input_shape = _dims_list(input_tensor.shape)
        if len(input_shape) != 4:
            raise RuntimeError(f"ONNX upscale models must have a 4D input, got {input_shape}")
        if input_shape[3] == 3 and input_shape[1] != 3:
            raise RuntimeError("NHWC ONNX upscale models are not supported. Export NCHW (B, C, H, W).")

        config = builder.create_builder_config()
        # En TRT antiguo se puede pedir FP16 al builder si el ONNX ya es half.
        dtype_name = str(input_tensor.dtype).split(".")[-1].upper()
        if dtype_name in ("HALF", "FLOAT16") and hasattr(trt.BuilderFlag, "FP16"):
            config.set_flag(trt.BuilderFlag.FP16)

        # Ejes -1 = forma dinámica: hay que declarar min / óptimo / max para el tiling.
        if any(dim < 0 for dim in input_shape):
            profile = builder.create_optimization_profile()
            profile.set_shape(
                input_tensor.name,
                (1, 3, self.min_dim, self.min_dim),
                (1, 3, ENGINE_OPT_DIM, ENGINE_OPT_DIM),
                (1, 3, self.max_dim, self.max_dim),
            )
            config.add_optimization_profile(profile)

        LOGGER.info("Building TensorRT engine for %s", os.path.basename(onnx_path))
        started = time.time()
        engine_bytes = builder.build_serialized_network(network, config)
        if engine_bytes is None:
            raise RuntimeError(f"Failed to build TensorRT engine from {onnx_path}")
        os.makedirs(os.path.dirname(self.engine_path), exist_ok=True)
        with open(self.engine_path, "wb") as engine_file:
            engine_file.write(memoryview(engine_bytes))
        LOGGER.info("TensorRT engine built in %.1fs: %s", time.time() - started, self.engine_path)

    def load(self):
        """Deserializa el .trt, crea el contexto y elige el perfil 0."""
        runtime = trt.Runtime(_TRT_LOGGER)
        with open(self.engine_path, "rb") as engine_file:
            self.engine = runtime.deserialize_cuda_engine(engine_file.read())
        if self.engine is None:
            raise RuntimeError(f"Failed to deserialize TensorRT engine: {self.engine_path}")

        self.context = self.engine.create_execution_context()
        # Stream propio: el stream por defecto de CUDA mete sync extra en enqueueV3.
        self.stream = torch.cuda.Stream(device=model_management.get_torch_device())
        if self.engine.num_optimization_profiles > 0:
            self.context.set_optimization_profile_async(0, self.stream.cuda_stream)
            self.stream.synchronize()

        self.input_name = None
        self.output_name = None
        for i in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(i)
            if self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                self.input_name = name
            else:
                self.output_name = name
        if not self.input_name or not self.output_name:
            raise RuntimeError("TensorRT engine is missing input or output tensors")

        self.tensors = {}
        self._bound_shape = None
        self._read_profile_limits()

    def _read_profile_limits(self):
        """Copia min/max espaciales del perfil (o de la forma fija si no hay perfil)."""
        if self.engine.num_optimization_profiles > 0:
            min_shape, _, max_shape = self.engine.get_tensor_profile_shape(self.input_name, 0)
            self.min_dim = min(int(min_shape[2]), int(min_shape[3]))
            self.max_dim = max(int(max_shape[2]), int(max_shape[3]))
            return
        shape = _dims_list(self.engine.get_tensor_shape(self.input_name))
        if len(shape) == 4 and shape[2] > 0 and shape[3] > 0:
            self.min_dim = min(shape[2], shape[3])
            self.max_dim = max(shape[2], shape[3])

    def infer(self, image):
        """Ejecuta el engine. image es BCHW. Si es más pequeña que min_dim, se rellena y luego se recorta."""
        if image.ndim != 4:
            raise RuntimeError(f"Expected BCHW input, got {tuple(image.shape)}")

        _, _, height, width = image.shape
        pad_h = max(0, self.min_dim - height)
        pad_w = max(0, self.min_dim - width)
        if pad_h or pad_w:
            image = torch.nn.functional.pad(image, (0, pad_w, 0, pad_h), mode="reflect")

        if image.shape[2] > self.max_dim or image.shape[3] > self.max_dim:
            raise RuntimeError(
                f"ONNX/TensorRT tile {image.shape[3]}x{image.shape[2]} exceeds engine max {self.max_dim}px"
            )

        self._bind(image)
        self.tensors[self.input_name].copy_(image.contiguous())
        for name, tensor in self.tensors.items():
            self.context.set_tensor_address(name, tensor.data_ptr())
        with torch.cuda.stream(self.stream):
            if not self.context.execute_async_v3(self.stream.cuda_stream):
                raise RuntimeError("TensorRT inference failed")
            self.stream.synchronize()

        output = self.tensors[self.output_name]
        if pad_h or pad_w:
            scale_h = output.shape[2] / image.shape[2]
            scale_w = output.shape[3] / image.shape[3]
            output = output[:, :, : int(height * scale_h), : int(width * scale_w)]
        return output

    def _bind(self, image):
        """Reserva buffers de I/O si cambia la forma del tile; si no, reutiliza los de antes."""
        shape = tuple(image.shape)
        if self._bound_shape == shape and self.tensors:
            return
        if not self.context.set_input_shape(self.input_name, shape):
            raise RuntimeError(f"TensorRT rejected input shape {shape}")
        self.context.infer_shapes()
        self.tensors = {}
        for i in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(i)
            tensor_shape = tuple(self.context.get_tensor_shape(name))
            if any(dim < 0 for dim in tensor_shape):
                raise RuntimeError(f"TensorRT could not resolve shape for {name}: {tensor_shape}")
            dtype = _trt_to_torch_dtype(self.engine.get_tensor_dtype(name))
            tensor = torch.empty(tensor_shape, dtype=dtype, device=image.device).contiguous()
            self.tensors[name] = tensor
            self.context.set_tensor_address(name, tensor.data_ptr())
        self._bound_shape = shape


class OnnxUpscaleModel:
    """
    Modelo callable para comfy.utils.tiled_scale (misma interfaz que spandrel).

    No lleva patcher de ComfyUI: el engine TensorRT ya está en GPU y
    load_models_gpu sobre un nn.Module vacío revienta la reserva VBAR.
    """

    def __init__(self, run, scale, tile_size=ENGINE_MAX_DIM):
        self.scale = scale
        self.tile_size = tile_size
        self._run = run

    def __call__(self, image):
        return self._run(image.float())


def _engine_path(model_name):
    """Ruta del .trt en models/tensorrt/upscaler, incluyendo versión de TensorRT."""
    rel = model_name.replace("\\", "/").replace("/", "__")
    stem = os.path.splitext(rel)[0]
    filename = f"{stem}_{trt.__version__}_1x3x{ENGINE_MIN_DIM}-{ENGINE_MAX_DIM}.trt"
    return os.path.join(folder_paths.models_dir, "tensorrt", "upscaler", filename)


def _load_trt_upscale_model(model_path, model_name):
    """Construye el engine si no existe o el ONNX es más nuevo, lo carga y mide el scale."""
    if not torch.cuda.is_available():
        raise RuntimeError("TensorRT upscaling requires CUDA.")

    engine_path = _engine_path(model_name)
    engine = TensorrtUpscaleEngine(engine_path)
    if not os.path.exists(engine_path) or os.path.getmtime(engine_path) < os.path.getmtime(model_path):
        model_management.soft_empty_cache()
        engine.build(model_path)
    engine.load()

    device = model_management.get_torch_device()
    probe = engine.min_dim
    dummy = torch.zeros(1, 3, probe, probe, device=device, dtype=torch.float32)
    output = engine.infer(dummy)
    scale = _spatial_scale(output.shape[2], probe, model_name)

    def run(image):
        if image.device.type != "cuda":
            image = image.to(device=device)
        return engine.infer(image).to(dtype=torch.float32)

    return OnnxUpscaleModel(run, scale, tile_size=engine.max_dim)


def _ort_providers():
    """Orden de backends de onnxruntime: TensorRT EP → CUDA → CPU."""
    available = ort.get_available_providers()
    providers = []
    if "TensorrtExecutionProvider" in available:
        cache_dir = os.path.join(folder_paths.models_dir, "tensorrt", "upscaler")
        os.makedirs(cache_dir, exist_ok=True)
        providers.append((
            "TensorrtExecutionProvider",
            {
                "trt_engine_cache_enable": True,
                "trt_engine_cache_path": cache_dir,
                "trt_fp16_enable": True,
            },
        ))
    if "CUDAExecutionProvider" in available:
        providers.append("CUDAExecutionProvider")
    providers.append("CPUExecutionProvider")
    return providers


def _is_nhwc(shape):
    """True si el layout es NHWC (canales al final) en vez del NCHW de ComfyUI/ESRGAN."""
    return len(shape) == 4 and shape[-1] == 3 and shape[1] != 3


def _load_ort_upscale_model(model_path, model_name):
    """Carga ONNX con onnxruntime cuando TensorRT no está disponible."""
    session = ort.InferenceSession(model_path, providers=_ort_providers())
    input_info = session.get_inputs()[0]
    output_name = session.get_outputs()[0].name
    input_name = input_info.name
    nhwc = _is_nhwc(input_info.shape)

    probe = ENGINE_MIN_DIM
    dummy = np.zeros((1, probe, probe, 3) if nhwc else (1, 3, probe, probe), dtype=np.float32)
    output = session.run([output_name], {input_name: dummy})[0]
    if _is_nhwc(output.shape):
        output = np.transpose(output, (0, 3, 1, 2))
    scale = _spatial_scale(output.shape[2], probe, model_name)

    def run(image):
        image_np = image.detach().float().contiguous().cpu().numpy()
        if nhwc:
            image_np = np.transpose(image_np, (0, 2, 3, 1))
        result = session.run([output_name], {input_name: image_np})[0]
        if _is_nhwc(result.shape):
            result = np.transpose(result, (0, 3, 1, 2))
        return torch.from_numpy(np.ascontiguousarray(result)).to(device=image.device, dtype=torch.float32)

    return OnnxUpscaleModel(run, scale)


def load_onnx_upscale_model(model_path, model_name):
    """TensorRT si hay CUDA; si no, onnxruntime."""
    if TRT_AVAILABLE and torch.cuda.is_available():
        return _load_trt_upscale_model(model_path, model_name)
    if ORT_AVAILABLE:
        return _load_ort_upscale_model(model_path, model_name)
    raise RuntimeError(
        "ONNX upscale models need TensorRT (NVIDIA) or onnxruntime. "
        "Install tensorrt or onnxruntime-gpu in the ComfyUI Python environment."
    )
