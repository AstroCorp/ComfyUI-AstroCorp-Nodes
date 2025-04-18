import os
from .nodes.InstructNode import NODE_CLASS_MAPPINGS as TEXT_NODES
from .nodes.InstructNode import NODE_DISPLAY_NAME_MAPPINGS as TEXT_DISPLAY_NAMES
from .nodes.TextareaNode import NODE_CLASS_MAPPINGS as TEXTAREA_NODES
from .nodes.TextareaNode import NODE_DISPLAY_NAME_MAPPINGS as TEXTAREA_DISPLAY_NAMES

NODE_CLASS_MAPPINGS = {**TEXT_NODES, **TEXTAREA_NODES}
NODE_DISPLAY_NAME_MAPPINGS = {**TEXT_DISPLAY_NAMES, **TEXTAREA_DISPLAY_NAMES}

WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "web")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
