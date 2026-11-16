import streamlit as st

st.set_page_config(layout="wide")

c_center = st.container(key="nc-center")
c_settings = st.container(key="nc-settings")

with c_center:
    st.write("Center content")

with c_settings:
    st.write("Settings content")
