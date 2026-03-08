## ADDED Requirements

### Requirement: Three modeling style tiers
The system prompt SHALL define three style tiers with distinct vertex budgets, shading, and texture approaches.

#### Scenario: Low-poly style
- **WHEN** the user requests a "low-poly", "stylized", or "mobile" asset
- **THEN** the LLM follows low-poly conventions: props <300 verts, flat shading, flat colors or procedural textures

#### Scenario: Mid-poly style
- **WHEN** the user requests a "game asset" or "realistic prop" without specifying poly count
- **THEN** the LLM follows mid-poly conventions: props <5K verts, smooth shading, PBR textures from AmbientCG

#### Scenario: Detailed style
- **WHEN** the user requests a "detailed", "high quality", or "realistic" asset
- **THEN** the LLM follows detailed conventions: props <50K verts, smooth shading with subdivision, PBR textures with normal maps

### Requirement: Default to mid-poly
The system prompt SHALL default to mid-poly when no style preference is stated.

#### Scenario: No style specified
- **WHEN** the user says "make me a sword" without style qualifiers
- **THEN** the LLM uses mid-poly conventions

### Requirement: Style inference from context
The LLM SHALL infer the appropriate style from contextual clues in the user's request.

#### Scenario: Context implies detailed
- **WHEN** the user says "make me a realistic assault rifle with proper textures"
- **THEN** the LLM selects the detailed style tier based on "realistic" and "proper textures"

#### Scenario: Context implies low-poly
- **WHEN** the user says "make me a cute little house"
- **THEN** the LLM selects the low-poly style tier based on "cute little"
