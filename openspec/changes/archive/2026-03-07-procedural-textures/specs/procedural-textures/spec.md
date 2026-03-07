## ADDED Requirements

### Requirement: Procedural material node setup via scripts
The system SHALL provide documented bpy patterns in the system prompt for creating procedural shader node trees (wood grain, stone, metal) that the LLM can use in scripts. Each recipe SHALL include Texture Coordinate, Mapping, texture nodes (Wave, Noise, Voronoi), color mixing, and connection to the Principled BSDF Base Color input.

#### Scenario: Wood grain material
- **WHEN** a script creates a material using the wood grain recipe from the system prompt
- **THEN** the material SHALL produce visible wood grain bands with organic variation when viewed with MATERIAL shading

#### Scenario: Stone material
- **WHEN** a script creates a material using the stone recipe from the system prompt
- **THEN** the material SHALL produce a rough, mottled stone appearance

#### Scenario: Metal material
- **WHEN** a script creates a material using the metal recipe from the system prompt
- **THEN** the material SHALL produce a brushed or weathered metallic appearance with appropriate roughness/metallic values

### Requirement: UV unwrap before texturing
The system prompt SHALL document that objects MUST be UV-unwrapped before procedural textures will bake correctly. The recommended pattern SHALL be Smart UV Project, applied via `bpy.ops.uv.smart_project()` in edit mode.

#### Scenario: UV unwrap in script
- **WHEN** a script selects an object, enters edit mode, selects all geometry, and calls `bpy.ops.uv.smart_project()`
- **THEN** the object SHALL have a valid UV map suitable for texture baking

### Requirement: Bake procedural textures to images
The system SHALL provide a bake helper at `scripts/utils/bake.py` that converts procedural node materials into image-backed materials suitable for game engine export.

#### Scenario: Bake single object
- **WHEN** a script calls the bake helper with an object name and optional resolution
- **THEN** the helper SHALL switch to Cycles, create a blank image at the specified resolution (default 1024), add an Image Texture node, bake the DIFFUSE pass, save the image, and rewire the material to use the baked image instead of procedural nodes

#### Scenario: Object without UV map
- **WHEN** the bake helper is called on an object with no UV map
- **THEN** it SHALL auto-apply Smart UV Project before baking

#### Scenario: Restore render engine after bake
- **WHEN** the bake completes (success or failure)
- **THEN** the render engine SHALL be restored to its pre-bake setting

#### Scenario: Bake all textured objects
- **WHEN** a script calls the bake-all helper
- **THEN** it SHALL bake every mesh object in the scene that has a procedural material (materials containing texture nodes other than Image Texture)

### Requirement: Baked textures embed in GLB export
Baked image textures SHALL be automatically embedded in GLB files when using the existing `export_model` tool, with no changes to the export pipeline.

#### Scenario: Export after baking
- **WHEN** a user bakes textures and then calls `export_model` with GLB format
- **THEN** the exported GLB SHALL contain the baked texture images embedded in the binary, and materials SHALL reference them correctly

### Requirement: Preview without baking
Procedural materials SHALL be viewable in the Blender viewport without baking, using the existing `screenshot` tool with MATERIAL shading mode.

#### Scenario: Preview procedural texture
- **WHEN** a script creates a procedural material and the user takes a screenshot with `shading="MATERIAL"`
- **THEN** the screenshot SHALL show the procedural texture applied to the object
