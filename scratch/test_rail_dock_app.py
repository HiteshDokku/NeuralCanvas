import streamlit as st

st.set_page_config(layout="wide")

st.markdown(
    """
<style>
/* Sidebar container overrides for docked rail */
[data-testid="stSidebar"] {
    height: 100dvh !important;
    overflow: hidden !important;
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    height: 100dvh !important;
    max-height: 100dvh !important;
    overflow: hidden !important;
    padding: 0 !important;
    display: flex !important;
    flex-direction: column !important;
}

[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    height: 100dvh !important;
    max-height: 100dvh !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
}

[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] {
    height: 100dvh !important;
    max-height: 100dvh !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
}

/* Scrollable rail content */
[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-scroll) {
    flex: 1 1 0px !important;
    min-height: 0 !important;
    height: auto !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
}

.st-key-nc-rail-scroll {
    height: 100% !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    overscroll-behavior: contain !important;
    scrollbar-width: thin !important;
    scrollbar-gutter: stable !important;
    padding: 0.75rem 0.75rem 16px 0.75rem !important;
    box-sizing: border-box !important;
}

/* Docked bottom rail */
[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock) {
    flex: 0 0 auto !important;
    width: 100% !important;
    background-color: #131313 !important;
    border-top: 1px solid #2A2A2A !important;
    z-index: 100 !important;
}

.st-key-nc-rail-dock {
    padding: 8px 12px 12px 12px !important;
    background-color: #131313 !important;
    box-sizing: border-box !important;
}
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    scroll_c = st.container(key="nc-rail-scroll")
    dock_c = st.container(key="nc-rail-dock")

    with scroll_c:
        st.title("Neural Canvas")
        st.write("Tagline")
        for i in range(25):
            st.checkbox(f"Option {i}", key=f"opt_{i}")
        st.checkbox("Keep photo colors", key="keep_colors")

    with dock_c:
        st.markdown(
            '<div class="sidebar-device-line" style="text-align: center; color: #888; font-size: 11px;">RTX 5060 Laptop GPU, 8 GB</div>',
            unsafe_allow_html=True,
        )
        st.button("Stylize", type="primary", use_container_width=True)

st.write("Main Content")
