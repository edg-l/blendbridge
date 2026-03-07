"""HTTP request handlers for the BlendBridge addon."""

import json
from http.server import BaseHTTPRequestHandler

from . import executor


class BlendBridgeHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests from the MCP server."""

    def log_message(self, format, *args):
        """Suppress default logging to avoid cluttering Blender console."""
        pass

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw)

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok"})
        elif self.path == "/scene_info":
            self._handle_scene_info()
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/execute":
            self._handle_execute()
        elif self.path == "/screenshot":
            self._handle_screenshot()
        elif self.path == "/render":
            self._handle_render()
        elif self.path == "/export":
            self._handle_export()
        elif self.path == "/clear_scene":
            self._handle_clear_scene()
        else:
            self._send_json({"error": "not found"}, 404)

    def _handle_execute(self):
        body = self._read_body()
        script = body.get("script", "")
        timeout = body.get("timeout", 30.0)

        if not script:
            self._send_json({"error": "No script provided"}, 400)
            return

        result = executor.submit(script, timeout=timeout)
        self._send_json({
            "success": result.success,
            "output": result.output,
            "error": result.error,
        })

    def _handle_scene_info(self):
        script = """
import bpy, json

objects = []
for obj in bpy.data.objects:
    info = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "materials": [m.name for m in obj.data.materials] if hasattr(obj.data, "materials") and obj.data else [],
    }
    if obj.type == "MESH" and obj.data:
        info["vertex_count"] = len(obj.data.vertices)
        info["face_count"] = len(obj.data.polygons)
    objects.append(info)

print(json.dumps({"objects": objects}))
"""
        result = executor.submit(script)
        if result.success and result.output:
            try:
                data = json.loads(result.output.strip())
                self._send_json(data)
                return
            except json.JSONDecodeError:
                pass
        self._send_json({
            "success": result.success,
            "output": result.output,
            "error": result.error,
        })

    def _handle_screenshot(self):
        import json as _json
        body = self._read_body()

        script = f"""
import bpy
import os
import tempfile
import base64

filepath = {repr(body.get("filepath", ""))}
if not filepath:
    filepath = os.path.join(tempfile.gettempdir(), "blendbridge_screenshot.png")

# Find a 3D viewport
area = None
for a in bpy.context.screen.areas:
    if a.type == 'VIEW_3D':
        area = a
        break

if area is None:
    raise RuntimeError("No 3D viewport found")

# Use offscreen render of the viewport
space = area.spaces.active
region = None
for r in area.regions:
    if r.type == 'WINDOW':
        region = r
        break

# Override context for screenshot
with bpy.context.temp_override(area=area, region=region):
    bpy.ops.screen.screenshot_area(filepath=filepath)

with open(filepath, "rb") as f:
    encoded = base64.b64encode(f.read()).decode("ascii")

import json
print(json.dumps({{"image_base64": encoded, "filepath": filepath}}))
"""
        result = executor.submit(script, timeout=10.0)
        if result.success and result.output:
            try:
                data = _json.loads(result.output.strip().split("\n")[-1])
                self._send_json(data)
                return
            except _json.JSONDecodeError:
                pass
        self._send_json({
            "success": result.success,
            "output": result.output,
            "error": result.error,
        })

    def _handle_render(self):
        import json as _json
        body = self._read_body()
        resolution_x = body.get("resolution_x", 512)
        resolution_y = body.get("resolution_y", 512)

        script = f"""
import bpy
import os
import tempfile
import base64

filepath = {repr(body.get("filepath", ""))}
if not filepath:
    filepath = os.path.join(tempfile.gettempdir(), "blendbridge_render.png")

scene = bpy.context.scene
scene.render.resolution_x = {resolution_x}
scene.render.resolution_y = {resolution_y}
scene.render.filepath = filepath
bpy.ops.render.render(write_still=True)

with open(filepath, "rb") as f:
    encoded = base64.b64encode(f.read()).decode("ascii")

import json
print(json.dumps({{"image_base64": encoded, "filepath": filepath}}))
"""
        result = executor.submit(script, timeout=120.0)
        if result.success and result.output:
            try:
                data = _json.loads(result.output.strip().split("\n")[-1])
                self._send_json(data)
                return
            except _json.JSONDecodeError:
                pass
        self._send_json({
            "success": result.success,
            "output": result.output,
            "error": result.error,
        })

    def _handle_export(self):
        import json as _json
        body = self._read_body()
        filename = body.get("filename", "export.glb")
        export_format = body.get("format", "GLB")

        script = f"""
import bpy
import json

filename = {repr(filename)}
export_format = {repr(export_format)}

# Apply all transforms
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

bpy.ops.export_scene.gltf(
    filepath=filename,
    export_format=export_format,
)

print(json.dumps({{"filepath": filename, "format": export_format}}))
"""
        result = executor.submit(script, timeout=60.0)
        if result.success and result.output:
            try:
                data = _json.loads(result.output.strip().split("\n")[-1])
                self._send_json(data)
                return
            except _json.JSONDecodeError:
                pass
        self._send_json({
            "success": result.success,
            "output": result.output,
            "error": result.error,
        })

    def _handle_clear_scene(self):
        script = """
import bpy

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Clean orphan data
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)
for block in bpy.data.textures:
    if block.users == 0:
        bpy.data.textures.remove(block)
for block in bpy.data.images:
    if block.users == 0:
        bpy.data.images.remove(block)

print("Scene cleared")
"""
        result = executor.submit(script)
        self._send_json({
            "success": result.success,
            "output": result.output,
            "error": result.error,
        })
