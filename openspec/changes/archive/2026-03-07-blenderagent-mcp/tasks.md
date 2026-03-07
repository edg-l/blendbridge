# Tasks — BlenderAgent MCP

## Phase 1: Proof of Life

- [x] **1.1 Blender addon skeleton** — `bl_info`, register/unregister, addon preferences (port config). Verify against Blender 5.0 addon API.
- [x] **1.2 Addon HTTP server** — Background thread HTTP server in addon, starts on enable, stops on disable. Single endpoint: `POST /execute` that accepts a Python script string.
- [x] **1.3 Addon executor** — `bpy.app.timers` queue-based executor. Receives scripts from HTTP handler, runs on main thread, returns result/error.
- [x] **1.4 MCP server with execute_script** — MCP server (stdio transport) with one tool: `execute_script`. Reads config.yaml, calls Blender addon via HTTP.
- [x] **1.5 End-to-end test** — Install addon in Blender 5.0, register MCP in Claude Code, verify Claude can create a cube in Blender.

## Phase 2: Feedback Loop

- [x] **2.1 Screenshot tool** — Viewport capture endpoint in addon + MCP tool. Return image as base64.
- [x] **2.2 Render tool** — Full render endpoint in addon + MCP tool. Configurable resolution.
- [x] **2.3 get_scene_info tool** — Endpoint + MCP tool. Returns objects list with transforms, types, materials, vertex counts.
- [x] **2.4 clear_scene tool** — Endpoint + MCP tool. Full scene cleanup.

## Phase 3: Production Workflow

- [x] **3.1 export_model tool** — glTF/GLB export with path safety (no traversal outside export_base). Apply transforms before export.
- [x] **3.2 Config system** — config.yaml loading with defaults for port, export_base, screenshot_dir, system_prompt path.
- [x] **3.3 Default system prompt** — `prompts/default.md` with bpy patterns, low-poly conventions, glTF export tips, Godot/Bevy specifics.
- [x] **3.4 README** — Installation instructions for Claude Code (`claude mcp add`), Blender 5.0 addon install, configuration, quick demo prompt to verify setup.
