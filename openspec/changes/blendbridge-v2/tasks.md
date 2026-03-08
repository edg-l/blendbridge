## 1. fetch_texture MCP tool

- [x] 1.1 Add `textures_dir` config field to `config.yaml` and load it in `mcp_server.py`
- [x] 1.2 Implement `fetch_texture` tool in `mcp_server.py` — search AmbientCG API by keyword, download zip, extract to `textures/<AssetID>_<Resolution>/`, return map paths
- [x] 1.3 Add caching — skip download if texture directory already exists
- [x] 1.4 Add `fetch_texture` method to `blender_client.py` is NOT needed (pure MCP-side, no Blender call)

## 2. apply_pbr addon helper

- [x] 2.1 Create `addon/blendbridge_addon/textures.py` with `apply_pbr(obj, texture_dir)` function
- [x] 2.2 Implement map detection by filename suffix (`*_Color.*`, `*_NormalGL.*`, `*_Roughness.*`, `*_AmbientOcclusion.*`, `*_Displacement.*`)
- [x] 2.3 Build Principled BSDF node tree — wire available maps (Color, Normal Map node, Roughness, AO via glTF Occlusion)
- [x] 2.4 Auto UV unwrap (Smart UV Project) if object has no UV layers
- [x] 2.5 Name material from texture directory name

## 3. System prompt rewrite

- [x] 3.1 Add style tiers section — low-poly, mid-poly, detailed with vertex budgets, shading, and texture guidance
- [x] 3.2 Add quality loop section — mandatory critique checklist, auto-fix behavior, 3-iteration cap
- [x] 3.3 Add texture workflow section — `fetch_texture` usage, `apply_pbr` helper, when to use procedural vs PBR
- [x] 3.4 Trim procedural texture recipes — condense wood/stone/metal from full code blocks to brief summaries
- [x] 3.5 Update intro and modeling conventions to be style-tier-aware (remove hard low-poly constraints)

## 4. Config and wiring

- [x] 4.1 Update `config.yaml` with `textures_dir` field and comment
- [x] 4.2 Ensure `textures/` directory is created on startup in `mcp_server.py`
- [x] 4.3 Rebuild addon zip and test `apply_pbr` import from bpy script
