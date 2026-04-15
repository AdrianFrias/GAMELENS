import streamlit as st
import sqlite3
import os
from pathlib import Path
import gdown

from ui.detalle import mostrar_detalle
from ui.buscador import mostrar_resultados

st.set_page_config(
    page_title="GameLens",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "gaming_warehouse.db"

@st.cache_resource
def descargar_db(file_id):
    if not DB_PATH.exists() or os.path.getsize(DB_PATH) < 1_000_000:
        if DB_PATH.exists():
            os.remove(DB_PATH)
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, str(DB_PATH), quiet=True)
    return str(DB_PATH)

if "juego_seleccionado" not in st.session_state:
    st.session_state["juego_seleccionado"] = None
if "busqueda_guardada" not in st.session_state:
    st.session_state["busqueda_guardada"] = ""

if st.session_state.get("_aplicar_busqueda") is not None:
    st.session_state["search_input"] = st.session_state.pop("_aplicar_busqueda")


try:
    ID_DRIVE = st.secrets["DRIVE_FILE_ID"]
except:
    ID_DRIVE = os.getenv("DRIVE_FILE_ID")

if not ID_DRIVE:
    ID_DRIVE = st.text_input("ID Drive:", type="password")
    if not ID_DRIVE:
        st.stop()

db_final = descargar_db(ID_DRIVE)

try:
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except:
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_KEY:
    OPENAI_KEY = st.text_input("🔑 OpenAI API Key:", type="password")
    if not OPENAI_KEY:
        st.warning("Ingresa tu API Key de OpenAI para continuar.")
        st.stop()

st.session_state["OPENAI_KEY"] = OPENAI_KEY


header_col1, header_col2 = st.columns([1, 3])

with header_col1:
    if st.button("💎 GameLens"):
        st.session_state["juego_seleccionado"] = None
        st.rerun()

with header_col2:
    busqueda = st.text_input("", placeholder="Buscar título...", label_visibility="collapsed", key="search_input")

st.divider()

try:
    conn = sqlite3.connect(db_final, check_same_thread=False)
    
    if busqueda:
        st.session_state["juego_seleccionado"] = None
        mostrar_resultados(conn, busqueda)

    elif st.session_state["juego_seleccionado"]:
        mostrar_detalle(conn)

    else:
        st.info("👋 Ingresa el nombre de un juego arriba para iniciar la exploración.")
        
finally:
    conn.close()