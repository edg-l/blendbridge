## ADDED Requirements

### Requirement: Apply PBR texture maps to an object
The `apply_pbr` addon helper SHALL create a Principled BSDF material from a directory of PBR image files and assign it to the specified object.

#### Scenario: Full PBR map set
- **WHEN** `apply_pbr(obj, "/path/to/Metal049A/")` is called and the directory contains Color, Normal, Roughness, and AO maps
- **THEN** the helper creates a material with all four maps wired to the Principled BSDF (Color → Base Color, Normal → Normal Map node → Normal, Roughness → Roughness, AO → glTF Occlusion slot)

#### Scenario: Partial map set
- **WHEN** the texture directory only contains Color and Normal maps
- **THEN** the helper wires available maps and uses Principled BSDF defaults for missing channels

### Requirement: Auto UV unwrap if missing
The helper SHALL ensure the object has a UV map before applying textures.

#### Scenario: Object has no UV map
- **WHEN** `apply_pbr` is called on an object with no UV layers
- **THEN** the helper runs Smart UV Project to generate UVs before applying the material

#### Scenario: Object already has UVs
- **WHEN** the object already has a UV map
- **THEN** the helper uses the existing UV map without modification

### Requirement: Material naming
The helper SHALL name the material based on the texture directory name.

#### Scenario: Material name from directory
- **WHEN** `apply_pbr(obj, "/path/to/Metal049A_2K/")` is called
- **THEN** the material is named `"Metal049A_2K"`

### Requirement: Importable from bpy scripts
The helper SHALL be importable in bpy scripts via the addon's extension path.

#### Scenario: Import in script
- **WHEN** a bpy script runs `from bl_ext.user_default.blendbridge_addon.textures import apply_pbr`
- **THEN** the function is available and callable
