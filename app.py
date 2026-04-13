import streamlit as st
import sqlite3
import pandas as pd
import requests
import os
from pathlib import Path
import gdown
# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "gaming_warehouse.db"

# Asegurar que la carpeta existe
DB_DIR.mkdir(parents=True, exist_ok=True)

# --- SECCIÓN DE DEBUG (Para saber qué está pasando) ---
with st.sidebar.expander("🛠️ Debug: Estado de la Base de Datos"):
    if DB_PATH.exists():
        size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
        st.write(f"Archivo detectado: `{DB_PATH.name}`")
        st.write(f"Tamaño: `{size_mb:.2f} MB`")
        if st.button("🗑️ Borrar y Forzar Redescarga"):
            os.remove(DB_PATH)
            st.rerun()
    else:
        st.write("❌ Archivo no encontrado localmente.")

@st.cache_resource
def descargar_db(file_id):
    if not DB_PATH.exists() or os.path.getsize(DB_PATH) < 1_000_000:
        if DB_PATH.exists():
            os.remove(DB_PATH)
        
        with st.spinner("Descargando base de datos (355MB)... Esto tomará un momento."):
            url = f"https://drive.google.com/uc?id={file_id}"
            gdown.download(url, str(DB_PATH), quiet=False, fuzzy=True)
        
        size_mb = os.path.getsize(DB_PATH) / (1024 * 1024) if DB_PATH.exists() else 0
        if size_mb < 1:
            st.error(f"❌ Drive bloqueó la descarga ({size_mb:.1f} MB recibidos). Intenta de nuevo.")
            if DB_PATH.exists(): os.remove(DB_PATH)
            st.stop()
        
        st.success(f"✅ Base de datos descargada: {size_mb:.1f} MB")
    
    return str(DB_PATH)

# --- CARGA DE SECRETOS ---
# Si estás en local y no has creado el .toml, pedirá el ID
try:
    ID_DRIVE = st.secrets["DRIVE_FILE_ID"]
except:
    st.warning("⚠️ No se encontró DRIVE_FILE_ID en los secretos.")
    ID_DRIVE = st.text_input("Introduce el ID de Google Drive para continuar:")
    if not ID_DRIVE: st.stop()

db_final = descargar_db(ID_DRIVE)

# --- INTERFAZ DE BÚSQUEDA ---
st.title("🎮 GameLens: Gaming Warehouse")

busqueda = st.text_input("Buscar juego en el catálogo:", placeholder="Ej: Witcher 3, Elden Ring...")

if busqueda:
    try:
        conn = sqlite3.connect(db_final)
        # Usamos tus nombres de tabla y columna: CAT_Juego y titulo
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
            cols = st.columns(3)
            for idx, row in df.iterrows():
                with cols[idx % 3]:
                    st.image(row['url_portada'] if row['url_portada'] else "https://via.placeholder.com/150", use_container_width=True)
                    st.subheader(row['titulo'])
                    st.write(f"⭐ Score: {row['puntuacion_igdb']} | ⏱️ {row['hltb_historia_principal']}h")
                    st.write(f"💰 Precio: ${row['steam_price_final']}")
                    st.divider()
        else:
            st.info("No se encontraron juegos con ese nombre.")
    except Exception as e:
        st.error(f"Error en la base de datos: {e}")