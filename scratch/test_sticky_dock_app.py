import streamlit as st

st.set_page_config(layout="wide")

st.markdown(
    """
<style>
[data-testid="stSidebar"] [data-testid="stSidebarContent"],
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding-bottom: 0 !important;
}
    height: 100dvh !important;
    max-height: 100dvh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    overscroll-behavior: contain !important;
    padding: 0 !important;
    position: relative !important;
    background-color: #1A1A1A !important;
}

/* Content wrapper with top padding and bottom padding equal to dock height + 16px */
.st-key-nc-rail-content {
    padding: 0.75rem 0.75rem 90px 0.75rem !important;
    box-sizing: border-box !important;
    width: 100% !important;
}

/* Docked bottom container */
[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock) {
    position: sticky !important;
    bottom: 0 !important;
    z-index: 999 !important;
    width: 100% !important;
    background-color: #131313 !important;
    border-top: 1px solid #2A2A2A !important;
    box-sizing: border-box !important;
}

.st-key-nc-rail-dock {
    padding: 8px 12px 12px 12px !important;
    background-color: #131313 !important;
    box-sizing: border-box !important;
    width: 100% !important;
}
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    with st.container(key="nc-rail-content"):
        st.title("Neural Canvas")
        st.write("Tagline")
        for i in range(25):
            st.checkbox(f"Option {i}", key=f"opt_{i}")
        st.checkbox("Keep photo colors", key="keep_colors")

    with st.container(key="nc-rail-dock"):
        st.markdown(
            '<div class="sidebar-device-line" style="text-align: center; color: #888; font-size: 11px; margin-bottom: 4px;">RTX 5060 Laptop GPU, 8 GB</div>',
            unsafe_allow_html=True,
        )
        st.button("Stylize", type="primary", use_container_width=True)

st.write("Main Content")
