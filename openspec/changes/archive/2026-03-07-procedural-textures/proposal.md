## Why

BlendBridge currently only supports flat-color materials (single BSDF with a solid base color). Real low-poly game assets need surface detail — wood grain, stone roughness, metal patina — to read correctly in-engine. Without texture support, exported GLB models look like untextured prototypes regardless of how good the geometry is.

## What Changes

- Add a **bake helper utility** (`scripts/utils/bake.py`) that handles the full bake pipeline: switch to Cycles, create image, add image texture node, bake, save, rewire material, cleanup. Callable from any user script.
- Make `scripts/utils/` **importable** from executed scripts by adding the scripts directory to `sys.path` in the executor.
- Add **procedural texture recipes** to the system prompt — node setups for wood, stone, metal, and other common low-poly materials, plus UV unwrap patterns and bake workflow guidance.
- Baked textures are **embedded in GLB** on export (Blender's glTF exporter handles this automatically once materials reference image textures).

## Capabilities

### New Capabilities
- `procedural-textures`: Procedural shader node setup patterns (wood, stone, metal) with UV unwrap, covering both the scripting patterns and the bake-to-image pipeline for game engine export.
- `script-imports`: Making `scripts/utils/` importable from executed scripts so helpers like the bake utility can be reused across scripts.

### Modified Capabilities

(none — no existing specs)

## Impact

- **`addon/blendbridge_addon/executor.py`**: Small change to inject `sys.path` so scripts can import from `scripts/utils/`.
- **`prompts/default.md`**: New sections for UV unwrapping, procedural node recipes, and bake workflow.
- **New file `scripts/utils/bake.py`**: Bake helper (~80-120 lines).
- **`mcp_server.py`**: May need to pass `scripts_dir` path to executed scripts or configure it in the addon.
- **Export**: No changes needed — glTF exporter already handles image-backed materials.
