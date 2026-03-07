## Context

BlendBridge currently creates low-poly models with flat-color Principled BSDF materials. Scripts run via `exec()` in `executor.py` with a bare namespace (`{"bpy": bpy}`), and `scripts/` is not on `sys.path`, so scripts cannot import shared utilities.

The system prompt (`prompts/default.md`) covers geometry, materials (flat color only), and export. There is no guidance on UV unwrapping, procedural shader nodes, or texture baking.

Blender's glTF exporter already embeds image textures into GLB files when materials reference them — no export changes needed.

## Goals / Non-Goals

**Goals:**
- LLM can create procedural textures (wood, stone, metal) via bpy scripts
- Bake procedural textures to images for game engine export
- Baked textures embed in GLB automatically
- Reusable bake helper importable from any script
- Preview works in Blender viewport with MATERIAL shading (no bake needed for preview)

**Non-Goals:**
- Image texture painting or external texture file support
- Texture atlas / palette optimization
- UV editing beyond Smart UV Project
- Custom render bake settings (always bake DIFFUSE at configurable resolution)
- Multi-material baking in a single call (user calls bake per object)

## Decisions

### 1. Bake helper as importable script utility (not MCP tool)

**Choice**: `scripts/utils/bake.py` importable via `sys.path` injection.

**Alternatives considered:**
- **Dedicated MCP tool**: Would hide complexity but is inflexible — the LLM can't customize bake settings or handle edge cases. Also adds server/addon code for something that's pure bpy.
- **Inline bake code**: LLM writes bake boilerplate each time — error-prone, verbose, defeats script reuse.

**Rationale**: A helper script is the right abstraction level. The bake pipeline is 100% bpy code — no need for HTTP round-trips through the addon. The LLM imports and calls it like any other Python module. If a script needs custom bake behavior, it can call lower-level functions or skip the helper entirely.

### 2. sys.path injection in MCP server (not addon)

**Choice**: `mcp_server.py` prepends `import sys; sys.path.insert(0, "<scripts_dir>")` to every script before sending it to the addon.

**Alternatives considered:**
- **Modify executor.py**: Cleaner but requires addon reinstall. The addon shouldn't know about the MCP server's scripts directory.
- **`__file__` based path**: Doesn't work — `exec()` namespace doesn't set `__file__`.

**Rationale**: The MCP server knows `scripts_dir` from config. Prepending one line to each script is minimal, transparent, and requires no addon changes. Scripts that don't use imports are unaffected.

### 3. Bake pipeline: Cycles switch, bake, rewire, restore

**Choice**: The bake helper handles the full sequence:
1. Store current render engine
2. Switch to Cycles (required for baking)
3. For the target object: UV unwrap if no UVs exist, create blank image, add unconnected Image Texture node, select it, bake DIFFUSE
4. Save image to temp location
5. Rewire material: disconnect procedural nodes, connect baked image to Base Color
6. Restore original render engine

**Rationale**: This is the minimal correct sequence. Storing/restoring the render engine avoids disrupting the user's viewport. UV unwrap is auto-applied only if the mesh has no UV map, so manual UV work is preserved.

### 4. Baked image storage

**Choice**: Save baked images to `<screenshot_dir>/textures/` (temp location). They get embedded in GLB on export — no persistent storage needed.

**Rationale**: Baked images are intermediate artifacts. The GLB file is the deliverable. Keeping them in a temp dir avoids cluttering the project. If users want standalone textures, they can specify a custom path.

### 5. System prompt: recipe-based guidance

**Choice**: Add concrete node setup recipes to `prompts/default.md` — copy-paste-ready code blocks for wood grain, stone, metal, plus UV unwrap and bake workflow sections.

**Rationale**: The LLM works best with concrete examples. Abstract node API documentation would lead to trial-and-error. Tested recipes for common materials cover 80% of use cases and can be mixed/modified for the rest.

## Risks / Trade-offs

- **Bake time**: Cycles baking can take 5-30s per object depending on resolution and scene complexity. → Acceptable per user ("i dont mind if baking takes time"). Default to 1024x1024.
- **Cycles availability**: Baking requires Cycles. If Blender is built without Cycles (rare), baking fails. → Document in prompt; no mitigation needed for standard Blender installs.
- **sys.path pollution**: Prepending scripts_dir to sys.path could shadow standard library modules if a script file has a conflicting name. → Use `scripts/utils/` subdirectory to namespace helpers, reducing collision risk.
- **UV quality**: Smart UV Project produces functional but not optimal UVs. For low-poly models this is fine — seams are less visible on simple geometry. → Document that manual UV work is possible for users who want better results.
