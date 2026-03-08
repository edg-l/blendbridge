## Context

BlendBridge currently has 7 MCP tools, an addon with `bake.py` as the only helper module, and a 425-line system prompt focused exclusively on low-poly modeling. The MCP server communicates with Blender's addon via HTTP on localhost:8400. Both run on the same machine, sharing the filesystem.

## Goals / Non-Goals

**Goals:**
- Add `fetch_texture` MCP tool for AmbientCG PBR texture download
- Add `textures.py` addon helper for applying PBR maps to objects
- Rewrite system prompt with style tiers, quality loop, and texture workflow
- Trim system prompt — condense verbose procedural texture recipes
- Keep it all in one prompt file (no multi-file split)

**Non-Goals:**
- No image texture painting or editing tools
- No custom texture upload mechanism (user can reference any file path in scripts)
- No LOD generation or texture atlas tooling
- No changes to existing MCP tools or addon HTTP endpoints
- Not splitting the system prompt into multiple files

## Decisions

### 1. Texture download happens in the MCP server, not the addon

**Decision**: `fetch_texture` is a pure MCP server tool using `urllib` + `zipfile` (stdlib). It does not go through Blender at all.

**Rationale**: AmbientCG downloads are just HTTP + zip extraction — no bpy needed. Adding an HTTP endpoint to the addon would add complexity for no benefit. Since MCP server and Blender share the filesystem (localhost), Blender can read files the MCP server writes.

**Alternative considered**: Addon-side download via new HTTP endpoint. Rejected because it adds unnecessary coupling — the addon shouldn't need internet access.

### 2. Use stdlib only for downloads (urllib + zipfile)

**Decision**: No new dependencies (no `requests`). Use `urllib.request` for HTTP and `zipfile` for extraction.

**Rationale**: The project already uses `urllib` in `blender_client.py`. AmbientCG's API is simple GET requests and zip downloads — no auth, no complex headers. Adding `requests` for this would be dependency bloat.

### 3. Texture helper lives in addon as `textures.py`

**Decision**: New `addon/blendbridge_addon/textures.py` module with `apply_pbr(obj, texture_dir)` function. Follows the `bake.py` pattern.

**Rationale**: The texture application requires bpy (loading images, creating shader nodes, UV unwrapping). It must run inside Blender. Making it a helper function means bpy scripts can call it directly without duplicating node wiring code every time.

### 4. Single system prompt file, trimmed

**Decision**: Keep `prompts/default.md` as a single file. Condense the procedural texture recipes (wood/stone/metal — ~120 lines) into short summaries since AmbientCG textures replace most use cases. Add style tiers, quality loop, and texture workflow sections.

**Rationale**: One file is easier to maintain and understand. The procedural recipes are less critical now — keep them as brief references for cases where AmbientCG doesn't have what's needed, but don't burn 120 lines on full code examples.

### 5. AmbientCG map file detection by suffix convention

**Decision**: `apply_pbr` detects map types by filename suffix: `*_Color.*`, `*_NormalGL.*`, `*_Roughness.*`, `*_AmbientOcclusion.*`, `*_Displacement.*`. This matches AmbientCG's naming convention.

**Rationale**: AmbientCG uses consistent naming. Pattern matching is simpler and more reliable than metadata files or user-specified map assignments.

### 6. Quality loop is prompt-only, no new tools

**Decision**: The self-critique and auto-fix loop is implemented entirely in the system prompt. No new MCP tools or code changes.

**Rationale**: The behavior we want is: look at screenshot → find problems → fix → re-check. The LLM already has all the tools needed (screenshot, execute_script, edit). We just need to instruct it to use them in a loop instead of being satisfied on first try.

## Risks / Trade-offs

- **[AmbientCG API stability]** → The API is public and has been stable. No auth required. If it changes, only `fetch_texture` needs updating.
- **[Disk usage from cached textures]** → 2K JPG zips are ~5-10MB each. Caching prevents re-downloads. Users can clear `textures/` manually.
- **[Quality loop token cost]** → Each auto-fix iteration costs an extra screenshot + script edit + execute. Cap at 3 iterations to bound cost.
- **[Style inference accuracy]** → The LLM may misread style intent. Default to mid-poly is a safe middle ground. Users can always override explicitly.
- **[Prompt length]** → Adding sections while trimming others. Net prompt size should stay roughly the same or decrease slightly.
