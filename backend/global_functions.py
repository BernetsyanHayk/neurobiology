"""
This file contains global functions to use in the project
"""

import json, os, logging, importlib
from jinja2 import FileSystemLoader, Environment

logging.basicConfig(level=logging.INFO)

_loaded_jinja_extensions = None

########################################
# Jinja extension loading and env setup
########################################
def load_jinja_extensions(json_path: str):

    # Check for "cached" extension list
    global _loaded_jinja_extensions
    if _loaded_jinja_extensions:
        return _loaded_jinja_extensions
    
    # Default extensions and logic to populate json if DNE
    DEFAULT_EXTENSIONS = [
        "jinja2.ext.do",
        "jinja2.ext.loopcontrols",
        "jinja_try_catch.TryCatchExtension"
    ]
    if not os.path.exists(json_path):
        with open(json_path, "w") as f:
            json.dump(DEFAULT_EXTENSIONS, f, indent=2)

    with open(json_path, "r") as f:
        extensions = json.load(f)
    
    resolved_extensions = []
    for ext in extensions:
        if "." in ext:
            # Dynamically import the extension
            module_path, class_name = ext.rsplit(".", 1)
            module = importlib.import_module(module_path)
            resolved_extensions.append(getattr(module, class_name))
        else:
            resolved_extensions.append(ext)  # Already imported string extension
    _loaded_jinja_extensions = resolved_extensions
    return resolved_extensions

def get_jinja_env(widget_folders_array: list = None, ext_json_path: str = "configs/jinja_ext.json"):
    extensions = load_jinja_extensions(ext_json_path)
    
    env = Environment(
        loader=FileSystemLoader(widget_folders_array or []),
        extensions=extensions,
    )
    return env