## ADDED Requirements

### Requirement: Scripts can import from utils directory
Scripts executed via `execute_script` SHALL be able to import Python modules from `scripts/utils/` using standard import syntax (e.g., `from utils.bake import bake_object`).

#### Scenario: Import helper module
- **WHEN** a script contains `from utils.bake import bake_object` and `scripts/utils/bake.py` exists
- **THEN** the import SHALL succeed and the function SHALL be callable

#### Scenario: Scripts without imports are unaffected
- **WHEN** a script does not use any imports from `scripts/utils/`
- **THEN** the script SHALL execute identically to before this change

### Requirement: sys.path injection by MCP server
The MCP server SHALL prepend a `sys.path.insert(0, "<scripts_dir>")` line to every script before sending it to the Blender addon for execution. The `scripts_dir` value SHALL come from the MCP server's configuration.

#### Scenario: Path injection
- **WHEN** the MCP server sends a script to the addon
- **THEN** the script SHALL be prefixed with `import sys; sys.path.insert(0, "<scripts_dir>")` where `<scripts_dir>` is the configured scripts directory

#### Scenario: scripts_dir from config
- **WHEN** `scripts_dir` is set in `config.yaml`
- **THEN** that path SHALL be used for sys.path injection
- **WHEN** `scripts_dir` is not set
- **THEN** the default `scripts/` directory relative to the project root SHALL be used
