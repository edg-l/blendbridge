# BlendBridge

MCP server that lets Claude control Blender 5.0 for creating low-poly 3D models. Designed for game dev workflows targeting Godot and Bevy.

## How It Works

Claude writes complete `bpy` Python scripts, executes them in Blender, takes viewport screenshots to see the results, iterates, and exports to GLB.

```
Claude ──MCP──► mcp_server.py ──HTTP──► Blender Addon ──bpy──► Blender
                                                          ◄── screenshot
```

## Installation

### 1. Install Python Dependencies

```bash
cd /path/to/blendbridge
uv sync
```

### 2. Install the Blender Addon

1. Open Blender 5.0
2. Go to **Edit > Preferences > Add-ons**
3. Click **Install from Disk...**
4. Navigate to `addon/blendbridge_addon/` and select the folder (or zip it first)
5. Enable **BlendBridge** in the addon list

Alternatively, symlink the addon into Blender's addon directory:

```bash
ln -s /path/to/blendbridge/addon/blendbridge_addon ~/.config/blender/5.0/scripts/addons/blendbridge_addon
```

Then enable it in Blender's addon preferences.

### 3. Configure the Addon (Optional)

In Blender's addon preferences for BlendBridge:
- **Port**: HTTP server port (default: 8400)
- **Auto-start**: Start server when addon is enabled (default: yes)

### 4. Register the MCP Server in Claude Code

```bash
claude mcp add blendbridge -- uv run --directory /path/to/blendbridge python mcp_server.py
```

That's it. The MCP server communicates with the Blender addon over HTTP on localhost.

## Configuration

Edit `config.yaml` to customize:

```yaml
# All optional — defaults shown
port: 8400                    # Must match Blender addon port
export_base: ./exports/       # Where exported models are saved
screenshot_dir: /tmp/blendbridge/  # Temporary screenshots
system_prompt: null           # Path to custom .md prompt (null = built-in)
```

### Custom System Prompt

The built-in prompt (`prompts/default.md`) includes bpy patterns, low-poly conventions, and Godot/Bevy export tips. To override:

```yaml
system_prompt: ~/my-game/blender-style-guide.md
```

## Quick Test

1. Open Blender 5.0 with the addon enabled
2. Start a Claude Code session
3. Ask Claude:

> Create a low-poly tree in Blender and take a screenshot

Claude should write a bpy script to create a tree, execute it, and show you a viewport screenshot.

## Tools

| Tool | Description |
|------|-------------|
| `execute_script` | Run a bpy Python script in Blender |
| `screenshot` | Capture the 3D viewport (fast, for iteration) |
| `render` | Full render (slower, for final quality) |
| `get_scene_info` | List all objects with transforms and materials |
| `export_model` | Export to GLB/glTF for Godot/Bevy |
| `clear_scene` | Remove everything and start fresh |

## Project Structure

```
blendbridge/
├── README.md
├── pyproject.toml           # Project config + dependencies
├── config.yaml              # MCP server config
├── mcp_server.py            # MCP server (stdio transport)
├── blender_client.py        # HTTP client → Blender addon
├── prompts/
│   └── default.md           # Built-in system prompt
└── addon/
    └── blendbridge_addon/  # Blender addon
        ├── __init__.py      # Addon registration
        ├── server.py        # HTTP server (background thread)
        ├── executor.py      # Main thread script executor
        └── handlers.py      # Request handlers
```

## Development

### Updating the Blender Addon

After changing any files in `addon/blendbridge_addon/`:

1. Re-build the zip:
   ```bash
   cd addon && zip -r ../blendbridge_addon.zip blendbridge_addon/ -x "blendbridge_addon/__pycache__/*"
   ```

2. In Blender: **Edit > Preferences > Get Extensions** — uninstall the old version

3. **Install from Disk** with the new zip

4. Restart Blender (some changes require a full restart)

### Updating the MCP Server

Changes to `mcp_server.py`, `blender_client.py`, or `config.yaml` take effect on the next Claude Code session (the MCP server restarts automatically).

### Testing the Addon HTTP Server

```bash
# Health check
curl http://127.0.0.1:8400/health

# Run a script
curl -X POST http://127.0.0.1:8400/execute \
  -H "Content-Type: application/json" \
  -d '{"script": "import bpy; print(list(bpy.data.objects))"}'

# Scene info
curl http://127.0.0.1:8400/scene_info
```

## Requirements

- Blender 5.0
- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- Claude Code
