"""Room layout model for the BanAI prototype (pure functions, integer mm).

Room coordinates: origin at the back-left floor corner, +x to the right, +z toward the viewer
(front wall). A wardrobe/item position is the CENTER of its footprint. Rotation is in degrees
(0/90/180/270) about the vertical axis; at 0 the wardrobe front faces +z (toward the room).

Checks are layout hints (overlap, blocked access, covering an opening). They are not
manufacturing or structural validation.
"""
from __future__ import annotations

import uuid

WALLS = ("back", "left", "right", "front")
ROTATIONS = (0, 90, 180, 270)

# name -> (kind, width, depth, height) in mm, width along x at rotation 0
PRESETS = {
    "Bed (160×200)": ("bed", 1600, 2000, 500),
    "Nightstand": ("nightstand", 450, 400, 500),
    "Desk": ("desk", 1400, 700, 750),
    "Sofa": ("sofa", 2000, 900, 800),
    "Armchair": ("armchair", 800, 800, 850),
    "Dresser": ("dresser", 1000, 450, 850),
    "Table": ("table", 1200, 800, 750),
    "Bookcase": ("bookcase", 800, 300, 1800),
}

OPENING_TYPES = ("door", "window")
OPENING_HEIGHT = {"door": 2050, "window": 1200}
OPENING_SILL = {"door": 0, "window": 900}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def make_item(name: str, x: int, z: int, rot: int = 0) -> dict:
    kind, w, d, h = PRESETS[name]
    return {"id": new_id("itm"), "name": name.split(" (")[0], "kind": kind,
            "w": w, "d": d, "h": h, "x": x, "z": z, "rot": rot}


def default_room() -> dict:
    return {
        "enabled": False,
        "width": 4000, "depth": 3500, "height": 2600,
        "wardrobe": {"x": 1000, "z": 300, "rot": 0},
        "items": [
            {**make_item("Bed (160×200)", 3000, 1750, 90)},
            {**make_item("Nightstand", 3775, 650, 90)},
            {**make_item("Desk", 1500, 3150, 180)},
        ],
        "openings": [
            {"id": new_id("opn"), "type": "door", "wall": "front", "offset": 2800, "width": 900},
            {"id": new_id("opn"), "type": "window", "wall": "right", "offset": 1300, "width": 1400},
        ],
        "selectedItem": 0,
    }


def extent(w: int, d: int, rot: int) -> tuple[int, int]:
    """Footprint size along room x and z after rotation."""
    return (d, w) if rot % 180 == 90 else (w, d)


def rect(cx: int, cz: int, w: int, d: int, rot: int) -> tuple[int, int, int, int]:
    ew, ed = extent(w, d, rot)
    return (cx - ew // 2, cz - ed // 2, cx + ew // 2, cz + ed // 2)


def overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def wardrobe_rect(design: dict, room: dict):
    wd = room["wardrobe"]
    return rect(wd["x"], wd["z"], design["width"], design["depth"], wd["rot"])


def access_depth(design: dict) -> int:
    """Floor depth in front of the wardrobe that should stay free (configurable prototype value)."""
    if design["doors"] == "hinged":
        n = max(1, len(design["compartments"]))
        return min(900, (design["width"] - 2 * design["panel"]) // n)  # one door leaf swinging open
    return 500  # sliding or no doors: standing room


def access_zone(design: dict, room: dict):
    wd = room["wardrobe"]
    ew, ed = extent(design["width"], design["depth"], wd["rot"])
    depth = access_depth(design)
    x0, z0, x1, z1 = wardrobe_rect(design, room)
    rot = wd["rot"]
    if rot == 0:
        return (x0, z1, x1, z1 + depth)
    if rot == 180:
        return (x0, z0 - depth, x1, z0)
    if rot == 90:   # front faces +x
        return (x1, z0, x1 + depth, z1)
    return (x0 - depth, z0, x0, z1)  # 270: front faces -x


def snap_wardrobe(design: dict, room: dict, wall: str) -> dict:
    """Return a new wardrobe placement with its back against `wall`, keeping the along-wall position."""
    wd = dict(room["wardrobe"])
    rw, rd = room["width"], room["depth"]
    d, w = design["depth"], design["width"]
    if wall == "back":
        wd.update(rot=0, z=d // 2, x=min(max(wd["x"], w // 2), rw - w // 2))
    elif wall == "front":
        wd.update(rot=180, z=rd - d // 2, x=min(max(wd["x"], w // 2), rw - w // 2))
    elif wall == "left":
        wd.update(rot=90, x=d // 2, z=min(max(wd["z"], w // 2), rd - w // 2))
    elif wall == "right":
        wd.update(rot=270, x=rw - d // 2, z=min(max(wd["z"], w // 2), rd - w // 2))
    return wd


def center_wardrobe(design: dict, room: dict) -> dict:
    wd = dict(room["wardrobe"])
    wd.update(x=room["width"] // 2, z=room["depth"] // 2)
    return wd


def _opening_span(room: dict, o: dict):
    """(wall, start, end) with start/end along the wall's own axis."""
    return o["wall"], o["offset"], o["offset"] + o["width"]


def check(design: dict, room: dict) -> list[tuple[str, str]]:
    """Layout hints as (level, message); level is 'warn' or 'info'."""
    out: list[tuple[str, str]] = []
    rw, rd = room["width"], room["depth"]
    wr = wardrobe_rect(design, room)
    inside = lambda r: r[0] >= 0 and r[1] >= 0 and r[2] <= rw and r[3] <= rd

    if not inside(wr):
        out.append(("warn", "The wardrobe extends outside the room."))
    if design["height"] > room["height"]:
        out.append(("warn", f"The wardrobe ({design['height'] / 10:g} cm) is taller than the room "
                            f"({room['height'] / 10:g} cm)."))

    zone = access_zone(design, room)
    if not inside(zone):
        out.append(("warn", "The area in front of the wardrobe goes outside the room."))

    for it in room["items"]:
        ir = rect(it["x"], it["z"], it["w"], it["d"], it["rot"])
        if not inside(ir):
            out.append(("warn", f"{it['name']} extends outside the room."))
        if overlap(wr, ir):
            out.append(("warn", f"The wardrobe overlaps {it['name']}."))
        elif overlap(zone, ir):
            what = "Door swing area" if design["doors"] == "hinged" else "Access area"
            out.append(("warn", f"{what} is blocked by {it['name']}."))

    # Wardrobe covering a door/window on the wall it touches
    touches = {"back": wr[1] <= 1, "front": wr[3] >= rd - 1, "left": wr[0] <= 1, "right": wr[2] >= rw - 1}
    along = {"back": (wr[0], wr[2]), "front": (wr[0], wr[2]), "left": (wr[1], wr[3]), "right": (wr[1], wr[3])}
    for o in room["openings"]:
        wall, s, e = _opening_span(room, o)
        if touches[wall] and s < along[wall][1] and along[wall][0] < e:
            if o["type"] == "door" or design["height"] > OPENING_SILL["window"]:
                out.append(("warn", f"The wardrobe covers the {o['type']} on the {wall} wall."))
        # items in front of a door
    for o in room["openings"]:
        if o["type"] != "door":
            continue
        wall, s, e = _opening_span(room, o)
        clear = 800
        if wall == "back":
            zr = (s, 0, e, clear)
        elif wall == "front":
            zr = (s, rd - clear, e, rd)
        elif wall == "left":
            zr = (0, s, clear, e)
        else:
            zr = (rw - clear, s, rw, e)
        for it in room["items"]:
            if overlap(zr, rect(it["x"], it["z"], it["w"], it["d"], it["rot"])):
                out.append(("warn", f"{it['name']} blocks the door on the {wall} wall."))

    if not out:
        out.append(("info", "No layout conflicts found."))
    return out


def viewer_payload(design: dict, room: dict) -> dict:
    zone = access_zone(design, room)
    blocked = any(
        overlap(zone, rect(i["x"], i["z"], i["w"], i["d"], i["rot"])) for i in room["items"]
    )
    sel = room.get("selectedItem", 0)
    return {
        "width": room["width"], "depth": room["depth"], "height": room["height"],
        "wardrobe": room["wardrobe"],
        "items": [{**i, "sel": k == sel} for k, i in enumerate(room["items"])],
        "openings": room["openings"],
        "openingHeight": OPENING_HEIGHT, "openingSill": OPENING_SILL,
        "zone": {"x0": zone[0], "z0": zone[1], "x1": zone[2], "z1": zone[3], "blocked": blocked},
    }
