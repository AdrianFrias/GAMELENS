import streamlit as st
import sqlite3
import pandas as pd
import requests
import os
from pathlib import Path

# BASE_DIR será: C:\Proyectos\GameLens
BASE_DIR = Path(__file__).resolve().parent

# DB_PATH será: C:\Proyectos\GameLens\db\gaming_warehouse.db
DB_PATH = BASE_DIR / "db" / "gaming_warehouse.db"

st.set_page_config(page_title="GameLens M5", layout="wide")

# --- SINCRONIZACIÓN CON DRIVE ---
@st.cache_resource
def descargar_db(file_id):
    if not DB_PATH.exists():
        # Session para mantener las cookies de confirmación de Google
        session = requests.Session()
        confirm_url = "https://docs.google.com/uc?export=download"
        
        try:
            with st.spinner("Descargando base de datos desde Drive (esto puede tardar)..."):
                # Primera petición para obtener el token de confirmación
                response = session.get(confirm_url, params={'id': file_id}, stream=True)
                token = None
                
                for key, value in response.cookies.items():
                    if key.startswith('download_warning'):
                        token = value
                        break

                # Si hay un token, hacemos la petición definitiva con el token
                if token:
                    params = {'id': file_id, 'confirm': token}
                    response = session.get(confirm_url, params=params, stream=True)
                
                response.raise_for_status()
                
                # Guardar el archivo
                with open(DB_PATH, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk: f.write(chunk)
            
            # Verificación de seguridad: ¿Es realmente un archivo SQLite?
            with open(DB_PATH, "rb") as f:
                header = f.read(16)
                if header != b'SQLite format 3\x00':
                    os.remove(DB_PATH) # Borramos el archivo falso (HTML)
                    st.error("❌ El archivo descargado no es una base de datos válida. Verifica que el ID sea correcto y el archivo sea público.")
                    st.stop()
            
            st.success("✅ Base de datos sincronizada correctamente.")
        except Exception as e:
            st.error(f"Error al conectar con Drive: {e}")
            st.stop()
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