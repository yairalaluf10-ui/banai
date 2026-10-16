"""BanAI landing page (Nordic style): calm, light, lots of air, one accent colour."""
from pathlib import Path

import streamlit as st

HERE = Path(__file__).parent

HERO_SVG = HERE / "hero.svg"  # line drawing of a three-door wardrobe

STEPS = [
    ("01", "Describe", "Tell the AI designer what you need in plain words. It proposes changes and waits for your approval."),
    ("02", "Adjust", "Fine-tune sizes, doors, shelves and materials by hand. Every change shows up in 3D at once."),
    ("03", "Place", "Put the wardrobe in your room and check the space around it before you decide."),
]

FEATURES = [
    ("Nothing changes without you", "Every AI suggestion is a proposal. You confirm or cancel, and your manual edits are never overwritten."),
    ("One design, three views", "Chat, properties and 3D all read the same design, so they always agree with each other."),
    ("Room-aware", "Add a bed, a desk, a door and a window. We flag overlaps and blocked door swings."),
]


def render() -> None:
    """Draw the page. Sets st.session_state.page / view_mode when a call-to-action is pressed."""
    st.markdown(f"<style>{(HERE / 'landing.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

    st.html('<nav class="nav"><span class="logo">BanAI</span><span class="tag">Wardrobe designer</span></nav>')

    left, right = st.columns([1.1, 1], gap="large", vertical_alignment="center")
    with left:
        st.html(
            '<div class="hero">'
            '<p class="eyebrow">Designed for calm spaces</p>'
            '<h1>Design a wardrobe<br>that fits your room.</h1>'
            '<p class="lead">Describe it, adjust it, and see it in 3D. '
            'Straight wardrobes with doors, shelves, drawers and rails, placed among your furniture.</p>'
            '</div>'
        )
        b1, b2, _ = st.columns([1, 1, 0.6])
        if b1.button("Start designing", type="primary", use_container_width=True, key="cta_start"):
            st.session_state.page = "designer"
            st.rerun()
        if b2.button("See it in a room", use_container_width=True, key="cta_room"):
            st.session_state.page = "designer"
            st.session_state.view_mode = "In room"
            st.rerun()
    with right:
        st.image(str(HERO_SVG), width="stretch")

    st.html('<hr class="rule">')

    st.html('<h2 class="section">How it works</h2>')
    cols = st.columns(3, gap="large")
    for col, (num, title, text) in zip(cols, STEPS):
        with col:
            st.html(f'<div class="step"><span class="num">{num}</span><h3>{title}</h3><p>{text}</p></div>')

    st.html('<hr class="rule">')

    cols = st.columns(3, gap="large")
    for col, (title, text) in zip(cols, FEATURES):
        with col:
            st.html(f'<div class="feature"><h3>{title}</h3><p>{text}</p></div>')

    st.html(
        '<footer class="foot">'
        '<p>BanAI shows illustrative 3D previews. It does not produce manufacturing drawings '
        'and does not check whether a design can be built.</p>'
        '</footer>'
    )
