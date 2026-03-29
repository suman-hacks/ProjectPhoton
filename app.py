"""
app.py — Project Photon navigation entry point.
Defines page order, titles, and shared page config.
"""

import streamlit as st

st.set_page_config(
    page_title="Project Photon",
    page_icon="⚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Navigation — Overview first, then the live dashboard
# ---------------------------------------------------------------------------
pg = st.navigation(
    [
        st.Page("pages/overview.py",   title="Overview",   icon="📋", default=True),
        st.Page("pages/dashboard.py",  title="App",        icon="⚛"),
        st.Page("pages/challenge.py",  title="Challenge",  icon="🎯"),
    ],
    position="sidebar",
)
pg.run()
