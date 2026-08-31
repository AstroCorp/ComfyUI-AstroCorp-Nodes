import os
import random

import folder_paths
from comfy.cli_args import args
from comfy_api.latest import io, ui, Types
from comfy_extras.nodes_video import SaveVideo


class VideoResultNode(SaveVideo):
    @classmethod
    def define_schema(cls):
        schema = SaveVideo.define_schema()
        schema.node_id = "VideoResultNode"
        schema.display_name = "Video Result"
        schema.category = "🚀🌍 AstroCorp 🌍🚀"
        schema.description = "Same as Save Video, plus a toggle to preview without saving."
        schema.search_aliases = ["preview video"]
        schema.essentials_category = None
        schema.inputs = [
            schema.inputs[0],
            io.Boolean.Input("save", default=False),
            *schema.inputs[1:],
        ]
        return schema

    @classmethod
    def execute(cls, video, filename_prefix, format, codec=None, save=False) -> io.NodeOutput:
        if isinstance(format, dict):
            format_name = format["format"]
            codec = format.get("codec") or codec
        else:
            format_name = format
        if codec is None:
            codec = {"codec": "auto"}
        codec_name = codec["codec"]
        if format_name == "auto":
            format_name = "webm" if codec_name == "av1" else "mp4"
        encoding = codec.get("encoding") or {}
        if save:
            output_dir = folder_paths.get_output_directory()
            folder_type = io.FolderType.output
        else:
            output_dir = folder_paths.get_temp_directory()
            folder_type = io.FolderType.temp
            filename_prefix += "_temp_" + "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(5))

        width, height = video.get_dimensions()
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(
            filename_prefix, output_dir, width, height
        )
        saved_metadata = None
        if not args.disable_metadata:
            metadata = {}
            if cls.hidden.extra_pnginfo is not None:
                metadata.update(cls.hidden.extra_pnginfo)
            if cls.hidden.prompt is not None:
                metadata["prompt"] = cls.hidden.prompt
            if metadata:
                saved_metadata = metadata
        file = f"{filename}_{counter:05}_.{Types.VideoContainer.get_extension(format_name)}"
        video.save_to(
            os.path.join(full_output_folder, file),
            format=Types.VideoContainer(format_name),
            codec=Types.VideoCodec(codec_name),
            metadata=saved_metadata,
            crf=encoding.get("crf"),
        )
        return io.NodeOutput(video, ui=ui.PreviewVideo([ui.SavedResult(file, subfolder, folder_type)]))


NODE_CLASS_MAPPINGS = {
    "VideoResultNode": VideoResultNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VideoResultNode": "Video Result",
}
