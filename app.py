import streamlit as st
import sqlite3
import pandas as pd
import requests
import os
from pathlib import Path
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

# --- SINCRONIZACIÓN ROBUSTA ---
@st.cache_resource
def descargar_db(file_id):
    if not DB_PATH.exists() or os.path.getsize(DB_PATH) < 1000000: # Si no existe o pesa menos de 1MB
        if DB_PATH.exists(): os.remove(DB_PATH)
        
        session = requests.Session()
        URL = "https://docs.google.com/uc?export=download"
        
        try:
            with st.spinner("Descargando base de datos pesada (355MB)... Esto tomará un momento."):
                # 1. Intentar petición inicial
                response = session.get(URL, params={'id': file_id}, stream=True)
                
                # 2. Buscar el token de confirmación en las cookies o en el HTML
                token = None
                for key, value in response.cookies.items():
                    if key.startswith('download_warning'):
                        token = value
                        break
                
                # 3. Si hay token (archivo grande), pedir el archivo de nuevo con el token
                if token:
                    params = {'id': file_id, 'confirm': token}
                    response = session.get(URL, params=params, stream=True)
                
                # 4. Descarga real del flujo de datos
                response.raise_for_status()
                with open(DB_PATH, "wb") as f:
                    for chunk in response.iter_content(chunk_size=32768): # Chunks más grandes para 355MB
                        if chunk: f.write(chunk)
            
            st.success(f"✅ ¡Base de datos de {os.path.getsize(DB_PATH)/(1024*1024):.1f} MB descargada!")
        except Exception as e:
            st.error(f"Error crítico en la descarga: {e}")
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