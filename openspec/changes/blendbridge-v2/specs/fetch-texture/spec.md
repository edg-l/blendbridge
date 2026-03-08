## ADDED Requirements

### Requirement: Search textures by keyword
The `fetch_texture` MCP tool SHALL accept a search query string and return matching PBR materials from AmbientCG.

#### Scenario: Search returns results
- **WHEN** `fetch_texture(query="brushed metal", resolution="2K")` is called
- **THEN** the tool searches AmbientCG API and returns metadata for the best matching material including asset ID, name, and available maps

#### Scenario: Search returns no results
- **WHEN** `fetch_texture(query="xyznonexistent")` is called
- **THEN** the tool returns an error message indicating no materials matched the query

### Requirement: Download and extract PBR textures
The tool SHALL download the texture zip from AmbientCG and extract PBR map images to a local `textures/<AssetID>/` directory.

#### Scenario: Successful download
- **WHEN** a matching material is found
- **THEN** the tool downloads the zip for the requested resolution, extracts all image files (Color, Normal, Roughness, AO, Displacement), and returns absolute paths to each map file

#### Scenario: Already cached
- **WHEN** the requested material and resolution already exist in `textures/<AssetID>/`
- **THEN** the tool skips the download and returns the existing file paths

### Requirement: Configurable resolution
The tool SHALL accept a `resolution` parameter to control download quality.

#### Scenario: Resolution selection
- **WHEN** `resolution="1K"` is specified
- **THEN** the tool downloads the 1K-JPG variant from AmbientCG

#### Scenario: Default resolution
- **WHEN** no resolution is specified
- **THEN** the tool defaults to `"2K"`

### Requirement: Configurable textures directory
The textures directory SHALL be configurable via `textures_dir` in `config.yaml`.

#### Scenario: Custom textures directory
- **WHEN** `textures_dir: /path/to/textures` is set in config.yaml
- **THEN** all downloaded textures are stored under that directory

#### Scenario: Default textures directory
- **WHEN** `textures_dir` is not set in config.yaml
- **THEN** textures are stored in `./textures/` relative to the project root
