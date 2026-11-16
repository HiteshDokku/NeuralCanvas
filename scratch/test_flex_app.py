import streamlit as st

st.set_page_config(layout="wide")

st.markdown(
    """
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"] {
    height: 100dvh !important;
    max-height: 100dvh !important;
    overflow: hidden !important;
}
[data-testid="stMainBlockContainer"] {
    height: 100dvh !important;
    max-height: 100dvh !important;
    padding: 0 !important;
    overflow: hidden !important;
}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    height: 100dvh !important;
    overflow: hidden !important;
    gap: 0 !important;
}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {
    position: absolute !important;
    top: -9999px !important;
    left: -9999px !important;
    width: 0 !important;
    height: 0 !important;
    pointer-events: none !important;
}
[data-testid="stLayoutWrapper"]:has(> .st-key-nc-center) {
    flex: 1 1 0px !important;
    min-width: 0 !important;
    height: 100dvh !important;
    display: flex !important;
    flex-direction: column !important;
}
.st-key-nc-center {
    height: 100% !important;
    overflow-y: auto !important;
    padding: 16px !important;
    box-sizing: border-box !important;
    background: #131313 !important;
    color: #fff !important;
}
[data-testid="stLayoutWrapper"]:has(> .st-key-nc-settings) {
    flex: 0 0 300px !important;
    width: 300px !important;
    height: 100dvh !important;
    display: flex !important;
    flex-direction: column !important;
}
.st-key-nc-settings {
    height: 100% !important;
    overflow-y: auto !important;
    padding: 16px !important;
    box-sizing: border-box !important;
    background: #1a1a1a !important;
    border-left: 1px solid #2a2a2a !important;
    color: #fff !important;
}
</style>
""",
    unsafe_allow_html=True,
)

c_center = st.container(key="nc-center")
c_settings = st.container(key="nc-settings")

with c_center:
    st.title("Center Result Plate")
    cols = st.columns([1, 2])
    with cols[0]:
        st.write("Col Left")
    with cols[1]:
        st.write("Col Right")
    for i in range(50):
        st.write(f"Center item {i}")

with c_settings:
    st.subheader("Settings Panel")
    for i in range(50):
        st.write(f"Settings item {i}")
