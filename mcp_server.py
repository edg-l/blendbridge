"""BlendBridge MCP Server — bridges Claude to Blender via the BlendBridge addon."""

import io
import json
import os
import re
import shutil
import urllib.request
import urllib.parse
import zipfile

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
_textures_dir = os.path.expanduser(_config.get("textures_dir", os.path.join(os.path.dirname(__file__), "textures")))
_blender_textures_dir = _config.get("blender_textures_dir")
if _blender_textures_dir:
    _blender_textures_dir = os.path.expanduser(_blender_textures_dir)

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
os.makedirs(_textures_dir, exist_ok=True)
# blender_textures_dir must be writable by the MCP server and readable by Blender
if _blender_textures_dir:
    os.makedirs(_blender_textures_dir, exist_ok=True)

_user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

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
    if not full_path.startswith(os.path.normpath(_export_base) + os.sep):
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


@mcp.tool()
def search_textures(query: str) -> str:
    """Search AmbientCG for PBR materials by keyword.

    Returns the top 5 matching materials with their names, tags, and categories
    so you can pick the best match before downloading.

    Args:
        query: Search keyword, e.g. "brushed metal", "oak wood", "brick wall".

    Returns:
        JSON with a list of matching materials (asset_id, name, tags, category).
        Pass the chosen asset_id to fetch_texture to download it.
    """
    params = urllib.parse.urlencode({
        "type": "Material",
        "q": query,
        "limit": 5,
    })
    api_url = f"https://ambientcg.com/api/v2/full_json?{params}"

    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": _user_agent})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return json.dumps({"error": f"AmbientCG API request failed: {e}"})

    assets = data.get("foundAssets", [])
    if not assets:
        return json.dumps({"error": f"No materials found for query: {query!r}"})

    results = []
    for asset in assets:
        results.append({
            "asset_id": asset["assetId"],
            "name": asset.get("displayName", asset["assetId"]),
            "tags": asset.get("tags", []),
            "category": asset.get("displayCategory", ""),
        })

    return json.dumps({"results": results}, indent=2)


@mcp.tool()
def fetch_texture(asset_id: str, resolution: str = "2K") -> str:
    """Download a specific PBR material from AmbientCG by asset ID.

    Use search_textures first to find the right material, then call this
    with the chosen asset_id to download and extract the PBR maps.

    Results are cached — if the texture was already downloaded, the existing
    paths are returned immediately without re-downloading.

    Use the returned texture_dir path with apply_pbr in a bpy script:
        from bl_ext.user_default.blendbridge_addon.textures import apply_pbr
        apply_pbr(obj, "<texture_dir>")

    Args:
        asset_id: AmbientCG asset ID from search_textures (e.g. "Metal049A").
        resolution: Texture resolution. One of: "1K", "2K", "4K". Default "2K".

    Returns:
        JSON with asset_id, texture_dir, and a map of PBR channel names to
        absolute file paths.
    """
    valid_resolutions = {"1K", "2K", "4K"}
    if resolution not in valid_resolutions:
        return json.dumps({"error": f"Invalid resolution {resolution!r}. Must be one of: {sorted(valid_resolutions)}"})

    # Sanitize asset_id — AmbientCG IDs are alphanumeric with optional letter suffix
    if not re.match(r'^[A-Za-z0-9_-]+$', asset_id):
        return json.dumps({"error": f"Invalid asset_id format: {asset_id!r}"})

    # Prefer blender-accessible path when configured (for cross-filesystem setups)
    dir_name = f"{asset_id}_{resolution}"
    base_dir = _blender_textures_dir or _textures_dir
    texture_dir = os.path.join(base_dir, dir_name)

    # Check cache — skip download if already extracted successfully
    sentinel = os.path.join(texture_dir, ".complete")
    if os.path.isfile(sentinel):
        maps = _scan_pbr_maps(texture_dir)
        return json.dumps({
            "asset_id": asset_id,
            "texture_dir": texture_dir,
            "maps": maps,
            "cached": True,
        }, indent=2)

    # Download URL — AmbientCG uses a consistent URL pattern
    file_param = urllib.parse.quote(f"{asset_id}_{resolution}-JPG.zip")
    download_url = f"https://ambientcg.com/get?file={file_param}"

    # Download zip (200 MB limit)
    max_zip_bytes = 200 * 1024 * 1024
    try:
        req = urllib.request.Request(download_url, headers={"User-Agent": _user_agent})
        with urllib.request.urlopen(req, timeout=60) as resp:
            zip_data = resp.read(max_zip_bytes + 1)
            if len(zip_data) > max_zip_bytes:
                return json.dumps({"error": "Texture zip exceeds 200 MB limit"})
    except Exception as e:
        return json.dumps({"error": f"Failed to download texture zip: {e}"})

    # Extract with path traversal and symlink protection
    os.makedirs(texture_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            real_dir = os.path.realpath(texture_dir)
            for member in zf.infolist():
                # Reject symlinks
                unix_mode = (member.external_attr >> 16) & 0xFFFF
                if (unix_mode & 0xF000) == 0xA000:
                    raise zipfile.BadZipFile(f"Zip contains symlink: {member.filename}")
                # Reject path traversal
                member_path = os.path.realpath(os.path.join(texture_dir, member.filename))
                if not member_path.startswith(real_dir + os.sep) and member_path != real_dir:
                    raise zipfile.BadZipFile(f"Zip contains unsafe path: {member.filename}")
            zf.extractall(texture_dir)
    except Exception as e:
        shutil.rmtree(texture_dir, ignore_errors=True)
        return json.dumps({"error": f"Failed to extract texture zip: {e}"})

    # Mark extraction as complete for cache
    with open(sentinel, "w"):
        pass

    maps = _scan_pbr_maps(texture_dir)
    return json.dumps({
        "asset_id": asset_id,
        "texture_dir": texture_dir,
        "maps": maps,
        "cached": False,
    }, indent=2)


def _scan_pbr_maps(texture_dir: str) -> dict:
    """Scan a texture directory for AmbientCG PBR map files by filename suffix.

    Note: mirrors the suffix logic in addon/blendbridge_addon/textures.py._scan_maps.
    Keep both in sync when adding new map types.
    """
    suffix_to_channel = {
        "_Color": "color",
        "_NormalGL": "normal",
        "_Roughness": "roughness",
        "_AmbientOcclusion": "ao",
        "_Displacement": "displacement",
    }
    maps = {}
    for fname in os.listdir(texture_dir):
        fpath = os.path.join(texture_dir, fname)
        if not os.path.isfile(fpath):
            continue
        stem, _ = os.path.splitext(fname)
        for suffix, channel in suffix_to_channel.items():
            if stem.endswith(suffix):
                maps[channel] = fpath
                break
    return maps


if __name__ == "__main__":
    mcp.run(transport="stdio")
