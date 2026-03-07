# BlenderAgent

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
cd /path/to/blenderagent
uv sync
```

### 2. Install the Blender Addon

1. Open Blender 5.0
2. Go to **Edit > Preferences > Add-ons**
3. Click **Install from Disk...**
4. Navigate to `addon/blenderagent_addon/` and select the folder (or zip it first)
5. Enable **BlenderAgent** in the addon list

Alternatively, symlink the addon into Blender's addon directory:

```bash
ln -s /path/to/blenderagent/addon/blenderagent_addon ~/.config/blender/5.0/scripts/addons/blenderagent_addon
```

Then enable it in Blender's addon preferences.

### 3. Configure the Addon (Optional)

In Blender's addon preferences for BlenderAgent:
- **Port**: HTTP server port (default: 8400)
- **Auto-start**: Start server when addon is enabled (default: yes)

### 4. Register the MCP Server in Claude Code

```bash
claude mcp add blenderagent -- uv run --directory /path/to/blenderagent python mcp_server.py
```

That's it. The MCP server communicates with the Blender addon over HTTP on localhost.

## Configuration

Edit `config.yaml` to customize:

```yaml
# All optional — defaults shown
port: 8400                    # Must match Blender addon port
export_base: ./exports/       # Where exported models are saved
screenshot_dir: /tmp/blenderagent/  # Temporary screenshots
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
blenderagent/
├── README.md
├── pyproject.toml           # Project config + dependencies
├── config.yaml              # MCP server config
├── mcp_server.py            # MCP server (stdio transport)
├── blender_client.py        # HTTP client → Blender addon
├── prompts/
│   └── default.md           # Built-in system prompt
└── addon/
    └── blenderagent_addon/  # Blender addon
        ├── __init__.py      # Addon registration
        ├── server.py        # HTTP server (background thread)
        ├── executor.py      # Main thread script executor
        └── handlers.py      # Request handlers
```

## Requirements

- Blender 5.0
- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- Claude Code
