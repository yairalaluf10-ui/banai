"""BanAI UX/UI prototype in Streamlit.

Three columns, as in the product spec: AI designer (left), 3D viewer (center),
properties editor (right). One canonical design dict (integer mm) drives everything.
The chat is a rule-based stand-in for the real agent: it only produces proposals,
and nothing is committed until the user presses Confirm (stale proposals are rejected).

Run:  streamlit run app.py
"""
import copy
import json
import re
from pathlib import Path

import streamlit as st

HERE = Path(__file__).parent

# ---- Canonical design (integer mm). Defaults are configurable prototype values. ----
COLORS = {
    "White": "#F4F2EE",
    "Oak": "#C9A877",
    "Walnut": "#6B4A32",
    "Graphite": "#3A3C3F",
    "Sage": "#A9B8A3",
    "Sand": "#D9CBB4",
}
FINISHES = ["matte", "satin", "gloss"]
LIMITS = {"width": (300, 6000), "height": (300, 3500), "depth": (200, 1200)}


def default_design() -> dict:
    return {
        "width": 2000, "height": 2400, "depth": 600, "panel": 18,
        "color": "White", "finish": "matte",
        "doors": "hinged", "slidingPanels": 2, "doorColor": "White",
        "compartments": [
            {"share": 1.0, "shelves": 3, "rail": False},
            {"share": 1.0, "shelves": 0, "rail": True},
            {"share": 1.0, "shelves": 2, "rail": False},
        ],
    }


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("design", default_design())
    ss.setdefault("revision", 0)
    ss.setdefault("selected", 0)
    ss.setdefault("show_interior", False)
    ss.setdefault("pending", None)
    ss.setdefault("chat", [("ai", "Describe the wardrobe you want, for example "
                                  "“240 cm wide, 4 compartments, sliding doors, oak”. "
                                  "I'll propose changes and wait for your approval.")])


def commit(new_design: dict) -> None:
    st.session_state.design = new_design
    st.session_state.revision += 1  # a manual edit also invalidates older proposals


# ---- Rule-based proposal builder (stand-in for the OpenAI agent) ----
def build_proposal(text: str, design: dict):
    t = text.lower()
    changes, labels = {}, []

    def num(pattern):
        m = re.search(pattern, t)
        return float(m.group(1)) if m else None

    for key, pat in (("width", r"(\d+(?:\.\d+)?)\s*(?:cm)?\s*(?:wide|width)|(?:width|רוחב)\s*(\d+(?:\.\d+)?)"),
                     ("height", r"(\d+(?:\.\d+)?)\s*(?:cm)?\s*(?:tall|high|height)|(?:height|גובה)\s*(\d+(?:\.\d+)?)"),
                     ("depth", r"(\d+(?:\.\d+)?)\s*(?:cm)?\s*(?:deep|depth)|(?:depth|עומק)\s*(\d+(?:\.\d+)?)")):
        m = re.search(pat, t)
        if m:
            v = float(next(g for g in m.groups() if g))
            mm = int(round(v * 10))
            lo, hi = LIMITS[key]
            if lo <= mm <= hi:
                changes[key] = mm
                labels.append(f"Set {key} to {mm / 10:g} cm")
            else:
                labels.append(f"Skipped {key}: {mm / 10:g} cm is outside {lo / 10:g}–{hi / 10:g} cm")

    m = re.search(r"(\d+)\s*(?:compartments?|sections?|תאים)", t)
    if m and 1 <= int(m.group(1)) <= 8:
        n = int(m.group(1))
        old = design["compartments"]
        comps = [copy.deepcopy(old[i]) if i < len(old) else {"share": 1.0, "shelves": 2, "rail": False}
                 for i in range(n)]
        changes["compartments"] = comps
        labels.append(f"Use {n} compartments")

    m = re.search(r"(\d+)\s*(?:shelves|shelf|מדפים)", t)
    if m and 0 <= int(m.group(1)) <= 10:
        comps = copy.deepcopy(changes.get("compartments", design["compartments"]))
        idx = st.session_state.selected if st.session_state.selected < len(comps) else 0
        comps[idx]["shelves"] = int(m.group(1))
        changes["compartments"] = comps
        labels.append(f"{m.group(1)} shelves in compartment {idx + 1}")

    if "hanging" in t or "rail" in t or "תלייה" in t:
        comps = copy.deepcopy(changes.get("compartments", design["compartments"]))
        idx = st.session_state.selected if st.session_state.selected < len(comps) else 0
        comps[idx]["rail"] = True
        changes["compartments"] = comps
        labels.append(f"Add hanging rail to compartment {idx + 1}")

    if "sliding" in t or "הזזה" in t:
        changes["doors"] = "sliding"; labels.append("Use sliding doors")
    elif "hinged" in t or "צירים" in t:
        changes["doors"] = "hinged"; labels.append("Use hinged doors")
    elif "no door" in t or "without door" in t:
        changes["doors"] = "none"; labels.append("Remove doors")

    for name in COLORS:
        if name.lower() in t:
            changes["color"] = name; changes["doorColor"] = name
            labels.append(f"Colour: {name}")
            break

    for f in FINISHES:
        if f in t:
            changes["finish"] = f; labels.append(f"Finish: {f}")
            break

    if not labels:
        return None
    return {"changes": changes, "labels": labels, "baseRevision": st.session_state.revision}


def apply_proposal(p: dict) -> bool:
    if p["baseRevision"] != st.session_state.revision:
        return False  # stale
    new = copy.deepcopy(st.session_state.design)
    new.update(copy.deepcopy(p["changes"]))
    commit(new)
    return True


# ---- UI ----
def css() -> None:
    st.markdown(f"<style>{(HERE / 'styles.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def viewer(design: dict) -> None:
    payload = {
        **design,
        "color": COLORS[design["color"]],
        "doorColor": COLORS[design["doorColor"]],
        "selected": st.session_state.selected,
        "showInterior": st.session_state.show_interior,
    }
    html = (HERE / "viewer.html").read_text(encoding="utf-8").replace("__DESIGN__", json.dumps(payload))
    st.iframe(html, height=640)


def chat_panel() -> None:
    st.markdown('<div class="panel-title">AI Designer</div>', unsafe_allow_html=True)
    box = st.container(height=470, border=False)
    with box:
        for role, text in st.session_state.chat:
            st.markdown(f'<div class="msg {role}">{text}</div>', unsafe_allow_html=True)
        p = st.session_state.pending
        if p:
            items = "".join(f"<li>{l}</li>" for l in p["labels"])
            st.markdown(f'<div class="proposal"><div class="tag">PROPOSED CHANGES</div><ul>{items}</ul></div>',
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("Confirm", type="primary", use_container_width=True, key="confirm"):
                ok = apply_proposal(p)
                st.session_state.chat.append(
                    ("ai", "Applied." if ok else "That proposal is out of date because the design changed. "
                                                 "Ask me again and I'll use the latest state."))
                st.session_state.pending = None
                st.rerun()
            if c2.button("Cancel", use_container_width=True, key="cancel"):
                st.session_state.chat.append(("ai", "Cancelled. Nothing was changed."))
                st.session_state.pending = None
                st.rerun()

    prompt = st.chat_input("Describe a change…")
    if prompt:
        st.session_state.chat.append(("user", prompt.replace("<", "&lt;")))
        proposal = build_proposal(prompt, st.session_state.design)
        if proposal:
            st.session_state.pending = proposal
            st.session_state.chat.append(("ai", "Here is what I would change. Confirm to apply."))
        else:
            st.session_state.pending = None
            st.session_state.chat.append(("ai", "I couldn't find a change in that. Try dimensions, "
                                                 "compartments, shelves, doors, colour or finish."))
        st.rerun()


def mm_input(label: str, key: str, value_mm: int, lo: int, hi: int) -> int:
    v = st.number_input(label, min_value=lo / 10, max_value=hi / 10, value=value_mm / 10,
                        step=0.5, format="%.1f", key=key)
    return int(round(v * 10))


def properties_panel() -> None:
    d = copy.deepcopy(st.session_state.design)
    rev = st.session_state.revision
    st.markdown('<div class="panel-title">Properties</div>', unsafe_allow_html=True)

    with st.expander("Dimensions (cm)", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: d["width"] = mm_input("Width", f"w{rev}", d["width"], *LIMITS["width"])
        with c2: d["height"] = mm_input("Height", f"h{rev}", d["height"], *LIMITS["height"])
        with c3: d["depth"] = mm_input("Depth", f"d{rev}", d["depth"], *LIMITS["depth"])

    with st.expander("Doors", expanded=True):
        d["doors"] = st.radio("Type", ["hinged", "sliding", "none"], horizontal=True,
                              index=["hinged", "sliding", "none"].index(d["doors"]), key=f"dt{rev}")
        if d["doors"] == "sliding":
            d["slidingPanels"] = st.slider("Sliding panels", 2, 4, d["slidingPanels"], key=f"sp{rev}")

    with st.expander("Material", expanded=False):
        d["color"] = st.selectbox("Body colour", list(COLORS), index=list(COLORS).index(d["color"]), key=f"bc{rev}")
        d["doorColor"] = st.selectbox("Door colour", list(COLORS),
                                      index=list(COLORS).index(d["doorColor"]), key=f"dc{rev}")
        d["finish"] = st.select_slider("Finish", FINISHES, value=d["finish"], key=f"fi{rev}")

    with st.expander("Compartments", expanded=True):
        n = len(d["compartments"])
        idx = min(st.session_state.selected, n - 1)
        st.session_state.selected = st.selectbox(
            "Selected", range(n), index=idx, format_func=lambda i: f"Compartment {i + 1}", key=f"sel{rev}")
        i = st.session_state.selected
        comp = d["compartments"][i]
        comp["share"] = st.slider("Relative width", 0.4, 2.0, float(comp["share"]), 0.1, key=f"sh{rev}_{i}")
        comp["shelves"] = st.number_input("Shelves", 0, 10, int(comp["shelves"]), key=f"sv{rev}_{i}")
        comp["rail"] = st.toggle("Hanging rail", value=bool(comp["rail"]), key=f"rl{rev}_{i}")
        a, b = st.columns(2)
        if a.button("Add compartment", use_container_width=True, disabled=n >= 8, key=f"add{rev}"):
            d["compartments"].append({"share": 1.0, "shelves": 2, "rail": False})
            commit(d); st.rerun()
        if b.button("Remove", use_container_width=True, disabled=n <= 1, key=f"rm{rev}"):
            d["compartments"].pop(i); st.session_state.selected = 0
            commit(d); st.rerun()

    if d != st.session_state.design:
        commit(d)
        st.rerun()

    if st.button("Reset to basic wardrobe", use_container_width=True, key="reset"):
        commit(default_design()); st.session_state.selected = 0; st.rerun()


def main() -> None:
    st.set_page_config(page_title="BanAI · Wardrobe Designer", page_icon="🗄️", layout="wide")
    css()
    init_state()

    st.markdown('<div class="brand"><h1>BanAI</h1><span>AI wardrobe designer · prototype UI</span></div>',
                unsafe_allow_html=True)
    left, center, right = st.columns([1.05, 2.1, 1.15], gap="medium")
    with left:
        chat_panel()
    with center:
        st.markdown('<div class="panel-title">3D View</div>', unsafe_allow_html=True)
        st.session_state.show_interior = st.toggle("Show interior", value=st.session_state.show_interior)
        viewer(st.session_state.design)
    with right:
        properties_panel()


main()
