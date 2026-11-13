import math
import mimetypes
import os
from fractions import Fraction

import av
import folder_paths
from comfy_api.latest import io, ui
from PIL import Image

# Windows has no registered type for .apng, so /view would serve it as application/octet-stream.
mimetypes.add_type("image/apng", ".apng")


class VideoToGifNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VideoToGifNode",
            display_name="Video To GIF/APNG",
            category="🚀🌍 AstroCorp 🌍🚀",
            description="Converts a video into a GIF or a lossless APNG saved in the output directory.",
            search_aliases=["save gif", "save apng", "animated png"],
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input("format", options=["gif", "apng"], default="gif"),
                io.String.Input("filename_prefix", default="ComfyUI"),
                io.Boolean.Input("loop", default=True),
            ],
            is_output_node=True,
        )

    @staticmethod
    def frame_durations(frame_count, frame_rate):
        # Spread the rounding error so the animation keeps the source duration.
        step = 1000 / float(frame_rate)
        return [round((index + 1) * step) - round(index * step) for index in range(frame_count)]

    @classmethod
    def save_gif(cls, images, frame_rate, path, loop):
        height, width = images.shape[1], images.shape[2]
        # GIF delays are centiseconds and browsers play anything under 20ms at 100ms, so cap at 50 fps.
        gif_rate = min(frame_rate, Fraction(50))
        indices = [int(i * frame_rate / gif_rate) for i in range(math.ceil(len(images) * gif_rate / frame_rate))]

        graph = av.filter.Graph()
        source = graph.add_buffer(width=width, height=height, format="rgb24", time_base=1 / gif_rate)
        split = graph.add("split")
        # Opaque frames, so the palette keeps all 256 entries for color.
        palettegen = graph.add("palettegen", "stats_mode=single:reserve_transparent=0")
        paletteuse = graph.add("paletteuse", "new=1:dither=sierra2_4a")
        sink = graph.add("buffersink")
        source.link_to(split)
        split.link_to(palettegen, 0, 0)
        split.link_to(paletteuse, 1, 0)
        palettegen.link_to(paletteuse, 0, 1)
        paletteuse.link_to(sink)
        graph.configure()

        with av.open(path, "w", format="gif", options={"loop": "0" if loop else "-1"}) as output:
            stream = output.add_stream("gif", rate=gif_rate)
            stream.width = width
            stream.height = height
            stream.pix_fmt = "pal8"

            def encode_ready_frames():
                while True:
                    try:
                        frame = graph.pull()
                    except (av.BlockingIOError, av.EOFError):
                        return
                    output.mux(stream.encode(frame))

            for pts, index in enumerate(indices):
                frame = av.VideoFrame.from_ndarray((images[index] * 255).clamp(0, 255).byte().cpu().numpy(), format="rgb24")
                frame.pts = pts
                frame.time_base = 1 / gif_rate
                graph.push(frame)
                encode_ready_frames()
            graph.push(None)
            encode_ready_frames()
            output.mux(stream.encode(None))

    @classmethod
    def save_apng(cls, images, frame_rate, path, loop):
        frames = [Image.fromarray((image * 255).clamp(0, 255).byte().cpu().numpy(), "RGB") for image in images]
        frames[0].save(
            path,
            save_all=True,
            append_images=frames[1:],
            duration=cls.frame_durations(len(frames), frame_rate),
            loop=0 if loop else 1,
            compress_level=9,
        )

    @classmethod
    def execute(cls, video, format, filename_prefix, loop) -> io.NodeOutput:
        if format not in ("gif", "apng"):
            raise ValueError(f"Unsupported format: {format}")
        components = video.get_components()
        images = components.images
        frame_rate = Fraction(round(components.frame_rate * 1000), 1000)
        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            filename_prefix, folder_paths.get_output_directory(), images.shape[2], images.shape[1]
        )
        file = f"{filename}_{counter:05}_.{format}"
        path = os.path.join(full_output_folder, file)
        if format == "apng":
            cls.save_apng(images, frame_rate, path, loop)
        else:
            cls.save_gif(images, frame_rate, path, loop)
        return io.NodeOutput(ui=ui.SavedImages([ui.SavedResult(file, subfolder, io.FolderType.output)], is_animated=True))


NODE_CLASS_MAPPINGS = {
    "VideoToGifNode": VideoToGifNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VideoToGifNode": "Video To GIF/APNG",
}
