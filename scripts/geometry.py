"""Small COLMAP text reader and CV -> AE exchange. No DCC or model dependency.

Pose convention informed by vfx-workbench 1211bef and B2AC a1e3c50 (MIT).
COLMAP stores world-to-camera; AE world here uses +X right, +Y down, +Z forward.
"""
from __future__ import annotations

import math
from pathlib import Path


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def unit(a):
    n = math.sqrt(dot(a, a))
    if not math.isfinite(n) or n < 1e-10:
        raise ValueError("Degenerate axis: choose distinct, non-collinear points")
    return [v/n for v in a]


def mv(m, v):
    return [dot(row, v) for row in m]


def transpose(m):
    return [list(row) for row in zip(*m)]


def quaternion(q):
    if len(q) != 4 or not all(math.isfinite(v) for v in q):
        raise ValueError("Invalid COLMAP quaternion")
    n = math.sqrt(dot(q, q))
    if n < 1e-10:
        raise ValueError("Zero quaternion")
    w, x, y, z = [v/n for v in q]
    return [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
            [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]


def read_model(folder):
    """Read documented TXT format; preserve the empty POINTS2D line per image."""
    folder = Path(folder)
    cameras, images, points = {}, {}, {}
    for line in (folder / "cameras.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        p = line.split()
        ident = int(p[0])
        if ident in cameras:
            raise ValueError("Duplicate camera ID")
        cameras[ident] = {"id": ident, "model": p[1], "width": int(p[2]),
                          "height": int(p[3]), "params": list(map(float, p[4:]))}
    lines = (folder / "images.txt").read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]; i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        p = line.split(maxsplit=9)
        if len(p) != 10 or i >= len(lines):
            raise ValueError("Malformed COLMAP images.txt pose/observations pair")
        observation = lines[i].split(); i += 1
        if len(observation) % 3:
            raise ValueError("Malformed POINTS2D triples")
        name = p[9]
        if name in images:
            raise ValueError("Duplicate image name")
        r = quaternion(list(map(float, p[1:5])))
        t = list(map(float, p[5:8]))
        if not all(math.isfinite(v) for v in t):
            raise ValueError("Non-finite camera translation")
        images[name] = {"id": int(p[0]), "name": name, "camera_id": int(p[8]),
                        "rotation": r, "translation": t,
                        "center": [-v for v in mv(transpose(r), t)]}
    for line in (folder / "points3D.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        p = line.split()
        if len(p) < 8 or (len(p)-8) % 2:
            raise ValueError("Malformed POINT3D record")
        ident = int(p[0]); xyz = list(map(float, p[1:4])); rgb = list(map(int, p[4:7]))
        if ident in points or not all(math.isfinite(v) for v in xyz+[float(p[7])]):
            raise ValueError("Duplicate/non-finite point")
        if any(v < 0 or v > 255 for v in rgb):
            raise ValueError("RGB must be 0..255")
        points[ident] = {"id": ident, "xyz": xyz, "rgb": rgb, "error": float(p[7]),
                         "track_length": (len(p)-8)//2}
    if not cameras or not images or not points:
        raise ValueError("Empty reconstruction")
    return cameras, images, points


def pinhole(camera):
    p = camera["params"]
    if camera["model"] == "SIMPLE_PINHOLE" and len(p) == 3:
        fx, cx, cy = p; fy = fx
    elif camera["model"] == "PINHOLE" and len(p) == 4:
        fx, fy, cx, cy = p
    elif camera["model"] == "SIMPLE_RADIAL" and len(p) == 4 and p[3] == 0:
        # COLMAP can retain this model after undistortion when k is exactly zero.
        # Its image projection is then exactly pinhole; no pixel remapping needed.
        fx, cx, cy, _ = p; fy = fx
    else:
        raise ValueError("Export requires COLMAP-undistorted PINHOLE, not a distorted camera")
    if not all(math.isfinite(v) for v in [fx, fy, cx, cy]) or min(fx, fy) <= 0:
        raise ValueError("Invalid intrinsics")
    if abs(fx-fy) > max(fx, fy)*1e-7:
        raise ValueError("Anamorphic/non-square fx/fy needs a separate calibrated workflow")
    return fx, fy, cx, cy


def centered_plate(camera):
    """Pad/translate the ACTUAL plate, rather than silently replacing cx/cy."""
    fx, fy, cx, cy = pinhole(camera)
    w, h = camera["width"], camera["height"]
    if w <= 0 or h <= 0 or not (0 < cx < w and 0 < cy < h):
        raise ValueError("Unsupported principal point/image extent")
    width = 2*math.ceil(max(cx, w-cx))
    height = 2*math.ceil(max(cy, h-cy))
    return {"width": width, "height": height, "fx": fx, "fy": fy,
            "cx": width/2, "cy": height/2, "shift_x": width/2-cx, "shift_y": height/2-cy,
            "source_width": w, "source_height": h,
            "source_cx": cx, "source_cy": cy}


def project(image, xyz, k):
    v = [a+b for a, b in zip(mv(image["rotation"], xyz), image["translation"])]
    if v[2] <= 1e-8:
        return None
    return [k["fx"]*v[0]/v[2]+k["cx"], k["fy"]*v[1]/v[2]+k["cy"]]


def select_points(points, image, k, limit):
    ranked = sorted(points.values(), key=lambda p: (-p["track_length"], p["error"], p["id"]))
    selected, occupied = [], set()
    candidates = []
    for p in ranked:
        uv = project(image, p["xyz"], k)
        if p["track_length"] < 2 or uv is None or not (0 <= uv[0] < k["width"] and 0 <= uv[1] < k["height"]):
            continue
        candidates.append(p)
        cell = (int(uv[0]*12/k["width"]), int(uv[1]*8/k["height"]))
        if cell not in occupied and len(selected) < limit:
            selected.append(p); occupied.add(cell)
    seen = {p["id"] for p in selected}
    selected.extend(p for p in candidates if p["id"] not in seen)
    return selected[:limit]


def plane_transform(points, ids, kind, scale, baseline_units=None):
    if len(ids) != 3 or len(set(ids)) != 3 or kind not in {"floor", "wall"}:
        raise ValueError("Choose three distinct point IDs and floor or wall")
    by_id = {p["id"]: p["xyz"] for p in points}
    a, b, c = [by_id[i] for i in ids]
    right = unit(sub(b, a)); across = unit(sub(c, a))
    if abs(dot(right, across)) > 0.995:
        raise ValueError("Points nearly collinear; choose a wider triangle")
    normal = unit(cross(right, across))
    down = [-v for v in normal] if kind == "floor" else unit(cross(normal, right))
    forward = unit(cross(right, down))
    if baseline_units is not None:
        if not math.isfinite(baseline_units) or baseline_units <= 0:
            raise ValueError("baseline-units must be positive")
        scale = baseline_units / math.sqrt(dot(sub(b, a), sub(b, a)))
    return {"origin": a, "basis": [right, down, forward], "scale": scale,
            "plane": kind, "point_ids": ids, "baseline_units": baseline_units}


def world_position(xyz, transform, k):
    v = mv(transform["basis"], sub(xyz, transform["origin"]))
    return [k["cx"]+v[0]*transform["scale"], k["cy"]+v[1]*transform["scale"], v[2]*transform["scale"]]


def cloud_glyphs(scene):
    """Preserve centers/RGB; size display glyphs to visible first-frame pixels."""
    pixels = scene.get("point_size_px", 6)
    if not math.isfinite(pixels) or not 1 <= pixels <= 30:
        raise ValueError("Point display diameter must be 1..30 pixels")
    first, k, tr = scene["frames"][0], scene["intrinsics"], scene["world"]
    points = scene.get("cloud_points", scene["points"])
    depths = [abs(mv(first["rotation"], p["xyz"])[2]+first["translation"][2]) for p in points]
    positive = sorted(z for z in depths if z > 1e-8)
    reference = positive[len(positive)//2] if positive else 1
    return [{"id":p["id"], "position":world_position(p["xyz"],tr,k),
             "color":[v/255 for v in p["rgb"]],
             "diameter":pixels*max(z,reference*.01)*tr["scale"]/k["fx"]}
            for p,z in zip(points,depths)]


def ae_poses(scene):
    k, tr = scene["intrinsics"], scene["world"]
    if not math.isfinite(tr["scale"]) or tr["scale"] <= 0:
        raise ValueError("Positive finite world scale required")
    result, previous = [], None
    for image in scene["frames"]:
        axes = transpose(image["rotation"])
        # Columns of CV camera-to-world are right, down, forward in world space.
        down = mv(tr["basis"], [row[1] for row in axes])
        forward = unit(mv(tr["basis"], [row[2] for row in axes]))
        if abs(dot([0, 1, 0], forward)) > 0.995:
            raise ValueError("Camera too close to vertical for this starter's AE POI/roll adapter")
        base_right = unit(cross([0, 1, 0], forward))
        base_down = unit(cross(forward, base_right))
        roll = math.degrees(math.atan2(dot(forward, cross(base_down, down)), dot(base_down, down)))
        if previous is not None:
            while roll-previous > 180: roll -= 360
            while roll-previous < -180: roll += 360
        previous = roll
        pos = world_position(image["center"], tr, k)
        result.append({"frame": image["frame"], "position": pos,
                       "poi": [pos[i]+1000*forward[i] for i in range(3)], "roll": roll})
    return result
