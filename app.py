import streamlit as st
import sqlite3
import pandas as pd
import os
from pathlib import Path
import gdown

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="GameLens",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "gaming_warehouse.db"

# --- DESCARGA ---
@st.cache_resource
def descargar_db(file_id):
    if not DB_PATH.exists() or os.path.getsize(DB_PATH) < 1_000_000:
        if DB_PATH.exists(): os.remove(DB_PATH)
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, str(DB_PATH), quiet=True)
    return str(DB_PATH)

# --- CARGA ---
try:
    ID_DRIVE = st.secrets["DRIVE_FILE_ID"]
except:
    ID_DRIVE = st.text_input("ID Drive:", type="password")
    if not ID_DRIVE: st.stop()

db_final = descargar_db(ID_DRIVE)

# --- CABECERA COMPACTA ---
header_col1, header_col2 = st.columns([1, 3])

with header_col1:
    st.header("GameLens")

with header_col2:
    busqueda = st.text_input("", placeholder="Buscar título...", label_visibility="collapsed")

st.divider()

# --- GRID DE 5 COLUMNAS CON FILTROS DE DATOS ---
if busqueda:
    try:
        conn = sqlite3.connect(db_final)
        query = """
            SELECT titulo, categoria, url_portada, hltb_historia_principal,
                   steam_price_final, puntuacion_igdb
            FROM CAT_Juego
            WHERE titulo LIKE ?
            and id_steam is not null
            LIMIT 50
        """
        df = pd.read_sql(query, conn, params=(f'%{busqueda}%',))
        conn.close()

        if not df.empty:
            # 1. ORDENAMIENTO POR COMPLETITUD
            # Contamos cuántas columnas no son nulas por cada fila para priorizar datos llenos
            df['completitud'] = df[['categoria', 'hltb_historia_principal', 'steam_price_final', 'puntuacion_igdb']].notnull().sum(axis=1)
            df = df.sort_values(by=['steam_price_final', 'completitud'], ascending=[False, False])


            # 2. RENDERIZADO
            filas = [df[i:i + 5] for i in range(0, len(df), 5)]
            
            for fila in filas:
                cols = st.columns(5)
                for i, (_, row) in enumerate(fila.iterrows()):
                    with cols[i]:
                        # Imagen con placeholder si no existe
                        st.image(
                            row['url_portada'] if row['url_portada'] else "https://via.placeholder.com/150x200?text=Imagen+N/A",
                            use_container_width=True
                        )
                        
                        # Título
                        st.markdown(f"**{row['titulo']}**")
                        
                        # Manejo de Nulos con etiquetas de texto
                        cat = row['categoria'] if row['categoria'] else "Sin categoría"
                        score = f"Score: {row['puntuacion_igdb']:.1f}" if pd.notnull(row['puntuacion_igdb']) else "Sin puntuación"
                        tiempo = f"Tiempo: {row['hltb_historia_principal']:.1f}h" if pd.notnull(row['hltb_historia_principal']) else "Tiempo N/A"
                        precio = f"Precio: ${row['steam_price_final']:.2f}" if pd.notnull(row['steam_price_final']) else "Sin precio"
                        
                        # Visualización de datos
                        st.caption(cat)
                        st.caption(f"{score} | {tiempo}")
                        st.caption(precio)
                        st.divider()
        else:
            st.info("No se encontraron resultados para la búsqueda.")
    except Exception as e:
        st.error(f"Error en la consulta: {e}")
else:
    st.write("Ingrese un término para iniciar la exploración del almacén de datos.")