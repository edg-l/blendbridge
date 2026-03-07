## 1. Script Import Support

- [x] ~~1.1 Add `scripts/utils/__init__.py` (empty, makes it a package)~~ — Dropped: bake.py moved into addon instead
- [x] ~~1.2 Modify `mcp_server.py` `execute_script` to prepend `sys.path.insert(0, scripts_dir)` to every script before sending to addon~~ — Dropped: not needed with addon approach
- [x] 1.3 Test: import bake helper from addon — verified `from bl_ext.user_default.blendbridge_addon.bake import bake_object, bake_all` works

## 2. Bake Helper

- [x] 2.1 Create `addon/blendbridge_addon/bake.py` with `bake_object(name, size=1024, textures_dir=None)` function — handles full pipeline: store engine, switch Cycles, auto-UV if needed, create image, add Image Texture node, bake DIFFUSE, save image, rewire material, restore engine
- [x] 2.2 Add `bake_all(size=1024)` function that iterates mesh objects with procedural materials and calls `bake_object` on each
- [x] 2.3 Test: created cube with procedural wood material, called `bake_object`, verified material rewired to image texture and image file exists at /tmp/blendbridge/textures/

## 3. System Prompt — Procedural Texture Recipes

- [x] 3.1 Add UV unwrap section to `prompts/default.md` — Smart UV Project pattern in edit mode
- [x] 3.2 Add procedural materials section with wood grain recipe (Wave Texture + Noise, two-tone brown mix, connected to BSDF Base Color)
- [x] 3.3 Add stone recipe (Noise Texture + Voronoi, gray/brown color ramp)
- [x] 3.4 Add metal recipe (Noise Texture for variation, low roughness, high metallic)
- [x] 3.5 Add bake workflow section — when to bake, how to call the helper, export after baking

## 4. Integration Testing

- [x] 4.1 End-to-end test: created wood block with procedural texture, baked (1024x1024), exported GLB (216 KB with embedded texture)
- [x] 4.2 Preview test: procedural material visible in screenshot with MATERIAL shading before baking
