import streamlit as st
import sqlite3
import pandas as pd
import os
from pathlib import Path
import gdown

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="GameLens",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "gaming_warehouse.db"
DB_DIR.mkdir(parents=True, exist_ok=True)

# --- DESCARGA SILENCIOSA ---
@st.cache_resource
def descargar_db(file_id):
    if not DB_PATH.exists() or os.path.getsize(DB_PATH) < 1_000_000:
        if DB_PATH.exists():
            os.remove(DB_PATH)
        url = f"https://drive.google.com/uc?id={file_id}"
        try:
            gdown.download(url, str(DB_PATH), quiet=True)
        except Exception as e:
            st.error(f"Error descargando la base de datos: {e}")
            st.stop()
        size_mb = os.path.getsize(DB_PATH) / (1024 * 1024) if DB_PATH.exists() else 0
        if size_mb < 1:
            if DB_PATH.exists(): os.remove(DB_PATH)
            st.error("❌ La descarga falló. Intenta recargar la página.")
            st.stop()
    return str(DB_PATH)

# --- SECRETOS ---
try:
    ID_DRIVE = st.secrets["DRIVE_FILE_ID"]
except:
    ID_DRIVE = st.text_input("🔑 Introduce el ID de Google Drive:")
    if not ID_DRIVE: st.stop()

with st.spinner("⏳ Cargando GameLens..."):
    db_final = descargar_db(ID_DRIVE)

# --- UI PRINCIPAL ---
st.title("🎮 GameLens")
st.caption("Busca cualquier juego del catálogo")

busqueda = st.text_input("", placeholder="Ej: Witcher 3, Elden Ring, Batman...")

if busqueda:
    try:
        conn = sqlite3.connect(db_final)
        query = """
            SELECT titulo, categoria, url_portada, hltb_historia_principal,
                   steam_price_final, puntuacion_igdb
            FROM CAT_Juego
            WHERE titulo LIKE ?
            LIMIT 15
        """
        df = pd.read_sql(query, conn, params=(f'%{busqueda}%',))
        conn.close()

        if not df.empty:
            st.markdown(f"**{len(df)} resultado(s) para:** `{busqueda}`")
            cols = st.columns(3)
            for idx, row in df.iterrows():
                with cols[idx % 3]:
                    st.image(
                        row['url_portada'] if row['url_portada'] else "https://via.placeholder.com/150x200?text=Sin+imagen",
                        use_container_width=True
                    )
                    st.subheader(row['titulo'])
                    score = f"{row['puntuacion_igdb']:.1f}" if row['puntuacion_igdb'] else "N/A"
                    hltb  = f"{row['hltb_historia_principal']:.1f}h" if row['hltb_historia_principal'] else "N/A"
                    precio = f"${row['steam_price_final']:.2f}" if row['steam_price_final'] else "N/A"
                    st.write(f"⭐ {score} | ⏱️ {hltb} | 💰 {precio}")
                    st.divider()
        else:
            st.info("No se encontraron juegos con ese nombre.")
    except Exception as e:
        st.error(f"Error en la base de datos: {e}")