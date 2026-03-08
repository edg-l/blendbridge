## Why

BlendBridge is currently locked to low-poly game assets only. Users who want to create mid-to-high detail models (e.g., a realistic gun with proper PBR textures) hit hard vertex budget limits and have no way to use real-world textures. Additionally, the LLM tends to be sycophantic about its own output — saying "looks great!" when screenshots show obvious problems like floating parts, gaps, or wrong proportions. These three issues (style rigidity, no PBR textures, poor self-assessment) limit BlendBridge's usefulness for serious game asset creation.

## What Changes

- **Style tiers**: Replace the low-poly-only modeling conventions with three style tiers (low-poly, mid-poly, detailed) with appropriate vertex budgets, shading, and texture guidance. Default to mid-poly.
- **AmbientCG texture integration**: New `fetch_texture` MCP tool that searches ambientcg.com for PBR materials, downloads and extracts them locally. New `textures.py` addon helper that wires PBR maps (color, normal, roughness, AO) into Principled BSDF nodes.
- **Self-critique loop**: Mandatory quality checklist after every screenshot — the LLM must check proportions, alignment, materials, silhouette, and floating parts before responding. Auto-fix issues and re-screenshot up to 3 times. Never say "looks good" without running the checklist.
- **System prompt trim**: Condense verbose procedural texture recipes (less critical now that AmbientCG provides real textures) and reorganize for clarity. Keep the file under manageable size.

## Capabilities

### New Capabilities
- `fetch-texture`: MCP tool to search and download PBR textures from AmbientCG, with local caching
- `apply-pbr`: Addon helper to apply downloaded PBR texture maps to objects via shader nodes
- `quality-loop`: Self-critique and auto-fix behavior after screenshots, defined in system prompt
- `style-tiers`: Multi-fidelity modeling guidance (low-poly, mid-poly, detailed) in system prompt

### Modified Capabilities

_None — no existing specs to modify._

## Impact

- **`mcp_server.py`**: New `fetch_texture` tool, new `textures_dir` config
- **`blender_client.py`**: No changes needed (fetch_texture doesn't go through Blender)
- **`config.yaml`**: New `textures_dir` field
- **`addon/blendbridge_addon/`**: New `textures.py` module
- **`prompts/default.md`**: Major rewrite — style tiers, critique loop, texture workflow, trimmed examples
- **Dependencies**: `requests` or `urllib` + `zipfile` (both stdlib except requests) for AmbientCG downloads
- **Disk**: Downloaded textures cached in `textures/` directory
