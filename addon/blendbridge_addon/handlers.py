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
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok"})
        elif self.path == "/scene_info":
            self._handle_scene_info()
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        body = self._read_body()
        if body is None:
            self._send_json({"error": "Invalid JSON in request body"}, 400)
            return
        if self.path == "/execute":
            self._handle_execute(body)
        elif self.path == "/screenshot":
            self._handle_screenshot(body)
        elif self.path == "/render":
            self._handle_render(body)
        elif self.path == "/export":
            self._handle_export(body)
        elif self.path == "/clear_scene":
            self._handle_clear_scene()
        elif self.path == "/set_viewport":
            self._handle_set_viewport(body)
        else:
            self._send_json({"error": "not found"}, 404)

    def _handle_execute(self, body):
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
from mathutils import Vector

objects = []
for obj in bpy.data.objects:
    info = {
        "name": obj.name,
        "type": obj.type,
        "location": [round(v, 4) for v in obj.location],
        "rotation": [round(v, 4) for v in obj.rotation_euler],
        "scale": [round(v, 4) for v in obj.scale],
        "materials": [m.name for m in obj.data.materials] if hasattr(obj.data, "materials") and obj.data else [],
    }
    if obj.type == "MESH" and obj.data:
        mesh = obj.data
        info["vertex_count"] = len(mesh.vertices)
        info["face_count"] = len(mesh.polygons)
        info["triangle_count"] = sum(len(f.vertices) - 2 for f in mesh.polygons)
        # Bounding box in world space
        bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs = [v.x for v in bbox]
        ys = [v.y for v in bbox]
        zs = [v.z for v in bbox]
        info["bounds"] = {
            "min": [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)],
            "max": [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)],
        }
    if obj.type == "LIGHT" and obj.data:
        light = obj.data
        info["light_type"] = light.type
        info["energy"] = round(light.energy, 2)
        info["color"] = [round(c, 3) for c in light.color]
    objects.append(info)

# Material details
materials = []
for mat in bpy.data.materials:
    m_info = {"name": mat.name, "users": mat.users}
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                bc = node.inputs["Base Color"].default_value
                m_info["base_color"] = [round(c, 3) for c in bc[:3]]
                m_info["metallic"] = round(node.inputs["Metallic"].default_value, 3)
                m_info["roughness"] = round(node.inputs["Roughness"].default_value, 3)
                break
    materials.append(m_info)

print(json.dumps({"objects": objects, "materials": materials}))
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

    def _handle_screenshot(self, body):
        shading = body.get("shading", "")  # SOLID, MATERIAL, RENDERED, WIREFRAME
        frame_object = body.get("frame_object", "")

        script = f"""
import bpy
import os
import tempfile
import base64

filepath = {repr(body.get("filepath", ""))}
if not filepath:
    filepath = os.path.join(tempfile.gettempdir(), "blendbridge_screenshot.png")

shading_mode = {repr(shading)}
frame_obj_name = {repr(frame_object)}

# Find a 3D viewport
area = None
for a in bpy.context.screen.areas:
    if a.type == 'VIEW_3D':
        area = a
        break

if area is None:
    raise RuntimeError("No 3D viewport found")

space = area.spaces.active
region = None
for r in area.regions:
    if r.type == 'WINDOW':
        region = r
        break

# Set shading mode if requested
old_shading = space.shading.type
if shading_mode and shading_mode in ('SOLID', 'MATERIAL', 'RENDERED', 'WIREFRAME'):
    space.shading.type = shading_mode

# Frame object if requested
if frame_obj_name:
    obj = bpy.data.objects.get(frame_obj_name)
    if obj:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.view3d.view_selected()

# Use render.opengl for reliable viewport capture (independent of window focus)
scene = bpy.context.scene
old_filepath = scene.render.filepath
old_format = scene.render.image_settings.file_format
scene.render.filepath = filepath
scene.render.image_settings.file_format = 'PNG'

with bpy.context.temp_override(area=area, region=region):
    bpy.ops.render.opengl(write_still=True)

# Restore settings
scene.render.filepath = old_filepath
scene.render.image_settings.file_format = old_format
if shading_mode:
    space.shading.type = old_shading

with open(filepath, "rb") as f:
    encoded = base64.b64encode(f.read()).decode("ascii")

import json
print(json.dumps({{"image_base64": encoded, "filepath": filepath}}))
"""
        result = executor.submit(script, timeout=15.0)
        if result.success and result.output:
            try:
                data = json.loads(result.output.strip().split("\n")[-1])
                self._send_json(data)
                return
            except json.JSONDecodeError:
                pass
        self._send_json({
            "success": result.success,
            "output": result.output,
            "error": result.error,
        })

    def _handle_render(self, body):
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
old_res_x = scene.render.resolution_x
old_res_y = scene.render.resolution_y
old_res_pct = scene.render.resolution_percentage
old_filepath = scene.render.filepath
old_format = scene.render.image_settings.file_format

scene.render.resolution_x = {resolution_x}
scene.render.resolution_y = {resolution_y}
scene.render.resolution_percentage = 100
scene.render.filepath = filepath
scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)

scene.render.resolution_x = old_res_x
scene.render.resolution_y = old_res_y
scene.render.resolution_percentage = old_res_pct
scene.render.filepath = old_filepath
scene.render.image_settings.file_format = old_format

with open(filepath, "rb") as f:
    encoded = base64.b64encode(f.read()).decode("ascii")

import json
print(json.dumps({{"image_base64": encoded, "filepath": filepath}}))
"""
        result = executor.submit(script, timeout=120.0)
        if result.success and result.output:
            try:
                data = json.loads(result.output.strip().split("\n")[-1])
                self._send_json(data)
                return
            except json.JSONDecodeError:
                pass
        self._send_json({
            "success": result.success,
            "output": result.output,
            "error": result.error,
        })

    def _handle_export(self, body):
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
                data = json.loads(result.output.strip().split("\n")[-1])
                self._send_json(data)
                return
            except json.JSONDecodeError:
                pass
        self._send_json({
            "success": result.success,
            "output": result.output,
            "error": result.error,
        })

    def _handle_set_viewport(self, body):
        preset = body.get("preset", "")         # FRONT, BACK, LEFT, RIGHT, TOP, THREE_QUARTER
        rotation = body.get("rotation", None)    # [rx, ry, rz] euler degrees
        distance = body.get("distance", 0)       # camera distance
        target = body.get("target", None)        # [x, y, z] look-at point
        frame_object = body.get("frame_object", "")

        script = f"""
import bpy
from mathutils import Euler
import math

preset = {repr(preset)}
custom_rotation = {repr(rotation)}
distance = {repr(distance)}
target = {repr(target)}
frame_obj_name = {repr(frame_object)}

PRESETS = {{
    "FRONT":         (90, 0, 0),
    "BACK":          (90, 0, 180),
    "LEFT":          (90, 0, -90),
    "RIGHT":         (90, 0, 90),
    "TOP":           (0, 0, 0),
    "BOTTOM":        (180, 0, 0),
    "THREE_QUARTER": (78, 0, 35),
}}

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        rv3d = area.spaces[0].region_3d
        region = None
        for r in area.regions:
            if r.type == 'WINDOW':
                region = r
                break

        # Apply rotation
        if preset and preset in PRESETS:
            rx, ry, rz = PRESETS[preset]
            rv3d.view_rotation = Euler((math.radians(rx), math.radians(ry), math.radians(rz))).to_quaternion()
        elif custom_rotation:
            rx, ry, rz = custom_rotation
            rv3d.view_rotation = Euler((math.radians(rx), math.radians(ry), math.radians(rz))).to_quaternion()

        if distance:
            rv3d.view_distance = float(distance)

        if target:
            rv3d.view_location = tuple(target)

        rv3d.view_perspective = 'PERSP'

        # Frame object if requested
        if frame_obj_name:
            obj = bpy.data.objects.get(frame_obj_name)
            if obj:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                with bpy.context.temp_override(area=area, region=region):
                    bpy.ops.view3d.view_selected()
        break

import json
print(json.dumps({{"success": True}}))
"""
        result = executor.submit(script, timeout=5.0)
        if result.success and result.output:
            try:
                data = json.loads(result.output.strip().split("\n")[-1])
                self._send_json(data)
                return
            except json.JSONDecodeError:
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
