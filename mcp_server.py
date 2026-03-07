"""BlendBridge MCP Server — bridges Claude to Blender via the BlendBridge addon."""

import json
import os

from PIL import Image
import yaml
from mcp.server.fastmcp import FastMCP

from blender_client import BlenderClient

# Load config
_config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
_config = {}
if os.path.exists(_config_path):
    with open(_config_path) as f:
        _config = yaml.safe_load(f) or {}

_port = _config.get("port", 8400)
_export_base = os.path.expanduser(_config.get("export_base", os.path.join(os.path.dirname(__file__), "exports")))
_screenshot_dir = os.path.expanduser(_config.get("screenshot_dir", "/tmp/blenderagent"))
_scripts_dir = os.path.expanduser(_config.get("scripts_dir", os.path.join(os.path.dirname(__file__), "scripts")))
_screenshot_max_width = _config.get("screenshot_max_width", 512)
_screenshot_max_height = _config.get("screenshot_max_height", 512)

# Load system prompt
_system_prompt_path = _config.get("system_prompt")
if _system_prompt_path:
    _system_prompt_path = os.path.expanduser(_system_prompt_path)
else:
    _system_prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "default.md")

_system_prompt = ""
if os.path.exists(_system_prompt_path):
    with open(_system_prompt_path) as f:
        _system_prompt = f.read()

# Ensure directories exist
os.makedirs(_export_base, exist_ok=True)
os.makedirs(_screenshot_dir, exist_ok=True)
os.makedirs(_scripts_dir, exist_ok=True)

client = BlenderClient(port=_port)

mcp = FastMCP(
    "BlendBridge",
    instructions=_system_prompt or "BlendBridge MCP server for controlling Blender. Use execute_script to run bpy Python scripts.",
)


@mcp.tool()
def execute_script(script: str = "", script_path: str = "", timeout: float = 30.0) -> str:
    """Execute a Python script in Blender using the bpy API.

    This is the primary tool for creating and modifying 3D content.
    Write complete bpy scripts to create meshes, set materials, transform objects, etc.
    The script runs in Blender's Python environment with bpy already available.

    Two modes:
    - Inline: pass code directly via `script` (quick one-offs).
    - File-based: pass a path via `script_path` (for iterating — write the file
      with your editor, then execute by path. Edit specific lines between runs
      instead of rewriting everything).

    If both are provided, `script_path` takes priority.

    Args:
        script: Python source code to execute in Blender. bpy is pre-imported.
        script_path: Absolute path to a .py file to execute instead of inline script.
        timeout: Max execution time in seconds (default 30).

    Returns:
        JSON with success status, stdout output, and any error traceback.
    """
    if script_path:
        if not os.path.isabs(script_path):
            return json.dumps({"success": False, "error": "script_path must be an absolute path."})
        if not os.path.isfile(script_path):
            return json.dumps({"success": False, "error": f"File not found: {script_path}"})
        with open(script_path) as f:
            script = f.read()
    if not script:
        return json.dumps({"success": False, "error": "Either script or script_path must be provided."})
    result = client.execute_script(script, timeout=timeout)
    return json.dumps(result, indent=2)


@mcp.tool()
def screenshot(shading: str = "", frame_object: str = "") -> str:
    """Capture a screenshot of the active 3D viewport in Blender.

    Use this after execute_script to see what was created or modified.
    Saves a PNG to disk. Read the file at the returned path to see the image.
    Uses OpenGL viewport render — works reliably regardless of window focus.

    Args:
        shading: Viewport shading mode. One of: MATERIAL (recommended — shows
            colors and basic PBR), SOLID (geometry only), RENDERED (full lighting,
            slower), WIREFRAME (edges only). Leave empty to keep current mode.
        frame_object: Name of an object to auto-frame in the viewport before
            capturing. Leave empty to keep current view.

    Returns:
        JSON with the file path to the screenshot PNG.
    """
    filepath = os.path.join(_screenshot_dir, "screenshot.png")
    result = client.screenshot(filepath=filepath, shading=shading, frame_object=frame_object)

    if "image_base64" in result:
        saved_path = result.get("filepath", filepath)
        # Downscale to save tokens when the LLM reads the image
        try:
            img = Image.open(saved_path)
            img.thumbnail((_screenshot_max_width, _screenshot_max_height))
            img.save(saved_path)
        except Exception:
            pass  # if resize fails, return the original
        return json.dumps({"image_path": saved_path})

    return json.dumps(result, indent=2)


@mcp.tool()
def set_viewport(
    preset: str = "",
    rotation: list[float] | None = None,
    distance: float = 0,
    target: list[float] | None = None,
    frame_object: str = "",
) -> str:
    """Set the 3D viewport camera angle and position.

    Use this before screenshot to control what angle the model is viewed from.
    Supports preset angles or fully custom rotation.

    Args:
        preset: Named angle preset. One of: FRONT, BACK, LEFT, RIGHT, TOP,
            BOTTOM, THREE_QUARTER. Overrides rotation if both are provided.
        rotation: Custom rotation as [rx, ry, rz] in degrees (Euler angles).
            Example: [78, 0, 35] for a 3/4 hero angle.
        distance: Camera distance from target point. 0 keeps current distance.
        target: Look-at point as [x, y, z]. Default keeps current target.
        frame_object: Name of an object to auto-frame (overrides distance/target
            to fit the object in view).

    Returns:
        JSON with success status.
    """
    result = client.set_viewport(
        preset=preset,
        rotation=rotation,
        distance=distance,
        target=target,
        frame_object=frame_object,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def render(resolution_x: int = 512, resolution_y: int = 512) -> str:
    """Render the current scene using Blender's render engine.

    Slower than screenshot but produces a properly lit, rendered image.
    Saves a PNG to disk. Read the file at the returned path to see the image.

    Args:
        resolution_x: Render width in pixels (default 512).
        resolution_y: Render height in pixels (default 512).

    Returns:
        JSON with the file path to the rendered PNG.
    """
    filepath = os.path.join(_screenshot_dir, "render.png")
    result = client.render(resolution_x=resolution_x, resolution_y=resolution_y, filepath=filepath)

    if "image_base64" in result:
        return json.dumps({"image_path": result.get("filepath", filepath)})

    return json.dumps(result, indent=2)


@mcp.tool()
def get_scene_info() -> str:
    """Get information about all objects in the current Blender scene.

    Returns a list of objects with their names, types, transforms,
    materials, and mesh stats (vertex/face counts).

    Use this to understand what's currently in the scene before making changes.

    Returns:
        JSON with list of scene objects and their properties.
    """
    result = client.get_scene_info()
    return json.dumps(result, indent=2)


@mcp.tool()
def export_model(filename: str, format: str = "GLB") -> str:
    """Export the current scene to glTF/GLB format for use in game engines.

    The file is saved relative to the configured export base directory.
    Subdirectories are allowed (e.g., "weapons/sword.glb").
    All transforms are applied before export.

    Args:
        filename: Output filename relative to export base (e.g., "boat.glb").
        format: Export format — "GLB" (binary, default) or "GLTF_SEPARATE".

    Returns:
        JSON with the absolute path of the exported file.
    """
    # Path safety: resolve and verify it stays within export_base
    full_path = os.path.normpath(os.path.join(_export_base, filename))
    if not full_path.startswith(os.path.normpath(_export_base)):
        return json.dumps({"error": "Path traversal not allowed. Filename must be relative to export base."})

    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    result = client.export_model(full_path, fmt=format)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_scripts() -> str:
    """List saved bpy scripts in the project scripts directory.

    Scripts are saved .py files that can be re-executed to recreate scenes.
    Use this to discover existing scripts you can iterate on or learn from.

    Returns:
        JSON with the scripts directory path and list of .py files with their sizes.
    """
    scripts = []
    for f in sorted(os.listdir(_scripts_dir)):
        if f.endswith(".py"):
            fpath = os.path.join(_scripts_dir, f)
            scripts.append({"name": f, "path": fpath, "size_bytes": os.path.getsize(fpath)})
    return json.dumps({"scripts_dir": _scripts_dir, "scripts": scripts}, indent=2)


@mcp.tool()
def clear_scene() -> str:
    """Remove all objects and clean up orphan data in the Blender scene.

    Clears meshes, materials, textures, and images with no users.
    Use this to start fresh before creating a new model.

    Returns:
        JSON with success status.
    """
    result = client.clear_scene()
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
