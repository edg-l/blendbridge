# BlenderAgent MCP

## Problem

Making low-poly 3D models for game dev (Godot, Bevy) is manual and repetitive. An LLM could handle the modeling if it could control Blender programmatically and see the results.

## Approach

A **script-first MCP server** paired with a **Blender 5.0 addon**. Instead of exposing dozens of granular tools, the LLM writes complete `bpy` Python scripts and executes them in Blender. A screenshot feedback loop lets it see and iterate on results.

### Architecture

```
Claude (writes bpy scripts)
    │ MCP Protocol (stdio)
    ▼
MCP Server (Python, thin layer, 6 tools)
    │ HTTP (localhost:8400)
    ▼
Blender Addon (HTTP server thread + main thread executor)
```

### Tools

| Tool | Purpose |
|------|---------|
| `execute_script` | Run a bpy Python script in Blender (the workhorse) |
| `screenshot` | Viewport capture (fast, for iteration) |
| `render` | Full render (pretty, for final check) |
| `get_scene_info` | List objects, transforms, materials |
| `export_model` | glTF/GLB export to configured base path |
| `clear_scene` | Reset scene to empty |

### Configuration

```yaml
# config.yaml — all optional, sensible defaults
port: 8400
export_base: ./exports/
screenshot_dir: /tmp/blenderagent/
system_prompt: null  # uses built-in default, or path to custom .md
```

- **port**: configurable, default 8400
- **export_base**: safe base directory for exports (no path traversal)
- **system_prompt**: override with custom prompt, or null to use built-in default with bpy patterns, low-poly conventions, and Godot/Bevy export tips

### Blender Addon Threading Model

Blender requires all `bpy` calls on the main thread. The addon uses:
1. Background thread — HTTP server accepting requests
2. Queue — passes requests to main thread
3. `bpy.app.timers.register()` — polls queue, executes scripts
4. Response — results flow back to waiting HTTP handler

## Targets

- **Blender 5.0** (verify all APIs against 5.0 docs)
- **Export format**: glTF/GLB (native in both Godot and Bevy)
- **Claude Code**: README with installation instructions tailored for `claude mcp add`

## Non-goals

- Sculpting, physics, animation, rigging, particles
- Complex material/shader editing
- Replacing Blender's UI for experienced modelers

## Risks

- **Blender 5.0 API changes**: some bpy APIs may differ from 4.x. Must verify against 5.0 docs.
- **Threading in Blender**: the timer+queue pattern is well-known but needs careful error handling
- **System prompt quality**: the prompt encoding bpy patterns and low-poly tips will need iteration based on real usage
