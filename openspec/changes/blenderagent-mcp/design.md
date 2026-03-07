# Design — BlenderAgent MCP

## Project Structure

```
blenderagent/
├── README.md                  # Installation for Claude Code + Blender
├── mcp_server.py              # MCP server (stdio transport)
├── blender_client.py          # HTTP client → talks to addon
├── config.yaml                # Default config
├── prompts/
│   └── default.md             # Built-in system prompt
│
└── addon/
    └── blenderagent_addon/
        ├── __init__.py        # Addon registration (bl_info)
        ├── server.py          # HTTP server (background thread)
        ├── executor.py        # Timer-based script runner (main thread)
        └── handlers.py        # Request handlers (/execute, /screenshot, etc.)
```

## Communication Flow

```
MCP Server                          Blender Addon
──────────                          ─────────────

tool call ──► blender_client.py
              │
              POST /execute ──────► server.py (bg thread)
                                    │
                                    queue.put(script)
                                    │
                                    executor.py (main thread, timer)
                                    │
                                    exec(script) in bpy context
                                    │
                                    result/error → queue
              ◄────────────────────
              return to MCP
```

## MCP Server

- **Transport**: stdio (standard for Claude Code MCP servers)
- **Framework**: `mcp` Python SDK
- **Config loading**: reads `config.yaml` from server directory, all fields optional with defaults
- **System prompt**: loaded from `prompts/default.md` unless overridden in config. Exposed as MCP resource or embedded in tool descriptions.

## Blender Addon

- **Blender version**: 5.0 (verify `bl_info` format and API compatibility)
- **Registration**: standard addon with enable/disable that starts/stops HTTP server
- **HTTP server**: `http.server` from stdlib, running in daemon thread
- **Port**: from addon preferences (default 8400), configurable in Blender's addon preferences UI
- **Executor**: `bpy.app.timers.register()` with ~0.1s interval, checks queue

### Addon Preferences

The Blender addon should expose preferences in the UI:
- Port number (default 8400)
- Auto-start server on enable (default: yes)

## Tool Details

### execute_script
- Input: `script` (string, Python code using bpy)
- Executes via `exec()` in a prepared namespace with `bpy` and standard libs imported
- Captures stdout/stderr
- Returns: `{"success": bool, "output": str, "error": str | null}`
- Timeout: configurable, default 30s

### screenshot
- Input: none (or optional `filepath`)
- Uses viewport capture (gpu/offscreen or `bpy.ops.screen.screenshot_area`)
- Returns: image as base64 or file path
- Fast (~100ms), for iteration

### render
- Input: optional `resolution` (default 512x512), optional `filepath`
- Sets render output, calls `bpy.ops.render.render(write_still=True)`
- Returns: rendered image as base64 or file path
- Slower, for final quality check

### get_scene_info
- Input: none
- Walks `bpy.data.objects`
- Returns: list of objects with name, type, location, rotation, scale, material names, vertex count

### export_model
- Input: `filename` (relative to export_base), optional `format` (default "GLB")
- Validates path stays within export_base (no `..` traversal)
- Applies transforms before export
- Calls `bpy.ops.export_scene.gltf()`
- Returns: absolute path of exported file

### clear_scene
- Input: none
- Removes all objects, materials, meshes (full cleanup)
- Returns: confirmation

## Error Handling

- Script execution errors: full traceback returned to MCP server → LLM can self-correct
- HTTP connection errors: clear message if Blender addon isn't running
- Timeout: scripts killed after timeout, error returned
- All errors include actionable context (not just "failed")

## System Prompt (default.md)

Should cover:
- bpy scripting patterns (deselect all first, context.active_object after ops, etc.)
- Low-poly modeling conventions (vertex budgets, flat shading, ico sphere subdivisions)
- glTF export best practices (apply transforms, name objects meaningfully, material naming)
- Godot/Bevy-specific tips (object names → nodes/entities, material count → draw calls)
- Iteration workflow (write script → screenshot → adjust → export)
