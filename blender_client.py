"""HTTP client that talks to the BlenderAgent Blender addon."""

import json
import urllib.request
import urllib.error


class BlenderClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8400):
        self.base_url = f"http://{host}:{port}"

    def _request(self, method: str, path: str, data: dict | None = None, timeout: float = 120.0) -> dict:
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data else None

        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body else {},
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Cannot connect to Blender addon at {self.base_url}. "
                f"Is Blender running with the BlenderAgent addon enabled? Error: {e}"
            )

    def health(self) -> dict:
        return self._request("GET", "/health")

    def execute_script(self, script: str, timeout: float = 30.0) -> dict:
        return self._request("POST", "/execute", {"script": script, "timeout": timeout})

    def screenshot(self, filepath: str = "", shading: str = "", frame_object: str = "") -> dict:
        data = {"filepath": filepath}
        if shading:
            data["shading"] = shading
        if frame_object:
            data["frame_object"] = frame_object
        return self._request("POST", "/screenshot", data, timeout=15.0)

    def render(self, resolution_x: int = 512, resolution_y: int = 512, filepath: str = "") -> dict:
        return self._request("POST", "/render", {
            "resolution_x": resolution_x,
            "resolution_y": resolution_y,
            "filepath": filepath,
        }, timeout=120.0)

    def get_scene_info(self) -> dict:
        return self._request("GET", "/scene_info")

    def export_model(self, filename: str, fmt: str = "GLB") -> dict:
        return self._request("POST", "/export", {"filename": filename, "format": fmt}, timeout=60.0)

    def set_viewport(self, preset: str = "", rotation: list = None,
                     distance: float = 0, target: list = None,
                     frame_object: str = "") -> dict:
        data = {}
        if preset:
            data["preset"] = preset
        if rotation:
            data["rotation"] = rotation
        if distance:
            data["distance"] = distance
        if target:
            data["target"] = target
        if frame_object:
            data["frame_object"] = frame_object
        return self._request("POST", "/set_viewport", data, timeout=5.0)

    def clear_scene(self) -> dict:
        return self._request("POST", "/clear_scene")
