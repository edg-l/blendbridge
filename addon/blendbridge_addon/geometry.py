"""Geometry helpers for building unified meshes from multiple bmesh primitives.

Usage from a script:
    from bl_ext.user_default.blendbridge_addon.geometry import bm_box, merge_geometry
"""

import bmesh


def bm_box(bm, x0, y0, z0, x1, y1, z1):
    """Add an axis-aligned box to a bmesh.

    Creates 8 vertices and 6 quad faces with outward-facing normals.

    Args:
        bm: The bmesh to add the box to.
        x0, y0, z0: Minimum corner coordinates.
        x1, y1, z1: Maximum corner coordinates.

    Returns:
        List of 8 created BMVert objects.
    """
    verts = [
        bm.verts.new((x0, y0, z0)), bm.verts.new((x1, y0, z0)),
        bm.verts.new((x1, y1, z0)), bm.verts.new((x0, y1, z0)),
        bm.verts.new((x0, y0, z1)), bm.verts.new((x1, y0, z1)),
        bm.verts.new((x1, y1, z1)), bm.verts.new((x0, y1, z1)),
    ]
    bm.faces.new([verts[0], verts[3], verts[2], verts[1]])  # bottom (-Z)
    bm.faces.new([verts[4], verts[5], verts[6], verts[7]])  # top (+Z)
    bm.faces.new([verts[0], verts[1], verts[5], verts[4]])  # front (-Y)
    bm.faces.new([verts[2], verts[3], verts[7], verts[6]])  # back (+Y)
    bm.faces.new([verts[0], verts[4], verts[7], verts[3]])  # left (-X)
    bm.faces.new([verts[1], verts[2], verts[6], verts[5]])  # right (+X)
    return verts


def merge_geometry(bm, dist=0.001):
    """Merge touching vertices and remove duplicate internal faces.

    Call this after adding multiple touching/adjacent boxes to a bmesh
    to produce a single unified mesh with no z-fighting or internal faces.

    Args:
        bm: The bmesh to clean up.
        dist: Merge distance for coincident vertices (default 0.001).

    Returns:
        Dict with counts: {"merged_verts": int, "removed_faces": int}.
    """
    # Merge coincident vertices
    result = bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=dist)
    merged_count = len(result.get("verts", []))

    # Remove duplicate faces (same vertex set = internal shared face)
    face_map = {}
    for f in bm.faces:
        key = frozenset(v.index for v in f.verts)
        face_map.setdefault(key, []).append(f)

    # Remove ALL copies — shared faces are interior walls between volumes.
    # Keeping one would leave a face floating inside the unified mesh.
    dupes = []
    for faces in face_map.values():
        if len(faces) > 1:
            dupes.extend(faces)

    removed_count = len(dupes)
    if dupes:
        bmesh.ops.delete(bm, geom=dupes, context='FACES_ONLY')

    # Fix normals
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    return {"merged_verts": merged_count, "removed_faces": removed_count}
