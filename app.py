import streamlit as st
import sqlite3
import pandas as pd
import os
from pathlib import Path
import gdown

# Importamos las funciones desde nuestro nuevo módulo
from db.queries import (
    obtener_generos, 
    obtener_etiquetas, 
    score_propio, 
    juegos_similares, 
    detalle_juego, 
    buscar_juegos
)

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

try:
    ID_DRIVE = st.secrets["DRIVE_FILE_ID"]
except:
    ID_DRIVE = st.text_input("ID Drive:", type="password")
    if not ID_DRIVE:
        st.stop()

db_final = descargar_db(ID_DRIVE)

header_col1, header_col2 = st.columns([1, 3])

with header_col1:
    if st.button("🚀 GameLens"):
        st.session_state["juego_seleccionado"] = None
        st.rerun()

with header_col2:
    busqueda = st.text_input("", placeholder="Buscar título...", label_visibility="collapsed")

st.divider()

# ==========================================
# VISTA DETALLE DEL JUEGO
# ==========================================
if st.session_state["juego_seleccionado"]:
    conn = sqlite3.connect(db_final)

    # Usamos la función importada
    juego_df = detalle_juego(conn, st.session_state["juego_seleccionado"])

    if not juego_df.empty:
        juego = juego_df.iloc[0]

        generos = obtener_generos(conn, juego['juego_id'])
        etiquetas = obtener_etiquetas(conn, juego['juego_id'])
        score = score_propio(juego)

        if st.button("⬅ Volver a la búsqueda"):
            st.session_state["juego_seleccionado"] = None
            st.rerun()

        st.markdown("---")
        col1, col2 = st.columns([1, 2])

        # COLUMNA IZQUIERDA: Imagen y Score
        with col1:
            st.image(
                juego['url_portada'] if juego['url_portada'] else "https://via.placeholder.com/300x400",
                use_container_width=True
            )
            st.markdown(f"### ⭐ Score GameLens: {score}")

        # COLUMNA DERECHA: Datos del juego
        with col2:
            st.title(juego['titulo'])
            st.markdown(f"**Categoría:** {juego['categoria'] or 'N/A'} | **Fecha lanzamiento:** {juego['fecha_lanzamiento'] or 'N/A'}")
            st.markdown(f"**Géneros:** {' | '.join(generos) if generos else 'N/A'}")
            st.markdown(f"**Etiquetas:** {', '.join(etiquetas[:10]) if etiquetas else 'N/A'}")
            st.markdown(f"**Score IGDB:** {juego['puntuacion_igdb'] or 'N/A'} | **Metacritic:** {juego['metacritic_score'] or 'N/A'}")

            precio = f"${juego['steam_price_final']:.2f}" if pd.notnull(juego['steam_price_final']) else "N/A"
            descuento = f"{juego['steam_discount_percent']}%" if pd.notnull(juego['steam_discount_percent']) else "0%"

            st.markdown(f"**Precio:** {precio} | **Descuento:** {descuento}")
            st.markdown("---")

            st.subheader("Descripción")
            st.write(juego['resumen'] or "Sin descripción")

            st.subheader("Historia")
            st.write(juego['historia'] or "No disponible")

            st.subheader("Duración (HLTB)")
            st.write(f"""
            * **Principal:** {juego['hltb_historia_principal'] or 'N/A'} h  
            * **Extra:** {juego['hltb_historia_extra'] or 'N/A'} h  
            * **Completo:** {juego['hltb_completacionista'] or 'N/A'} h
            """)

        # SECCIÓN INFERIOR: Juegos similares
        st.divider()
        st.subheader("🎮 Juegos similares")
        similares = juegos_similares(conn, juego['juego_id'])

        if not similares.empty:
            filas_sim = [similares[i:i + 5] for i in range(0, len(similares), 5)]
            for fila in filas_sim:
                cols = st.columns(5)
                for i, (_, sim) in enumerate(fila.iterrows()):
                    with cols[i]:
                        st.image(
                            sim['url_portada'] if sim['url_portada'] else "https://via.placeholder.com/150x200",
                            use_container_width=True
                        )
                        if st.button(sim['titulo'], key=f"sim_{sim['titulo']}_{i}", use_container_width=True):
                            st.session_state["juego_seleccionado"] = sim['titulo']
                            st.rerun()

    conn.close()

# ==========================================
# VISTA RESULTADOS BÚSQUEDA
# ==========================================
elif busqueda:
    try:
        conn = sqlite3.connect(db_final)
        
        # Usamos la función importada
        df = buscar_juegos(conn, busqueda)
        conn.close()

        if not df.empty:
            filas = [df[i:i + 5] for i in range(0, len(df), 5)]
            for r_idx, fila in enumerate(filas):
                cols = st.columns(5)
                for c_idx, (_, row) in enumerate(fila.iterrows()):
                    with cols[c_idx]:
                        st.image(
                            row['url_portada'] if row['url_portada'] else "https://via.placeholder.com/150x200?text=Imagen+N/A",
                            use_container_width=True
                        )
                        if st.button(row['titulo'], key=f"btn_search_{row['titulo']}_{r_idx}_{c_idx}", use_container_width=True):
                            st.session_state["juego_seleccionado"] = row['titulo']
                            st.rerun()

                        cat = row['categoria'] if row['categoria'] else "Sin categoría"
                        score = f"{row['puntuacion_igdb']:.1f}" if pd.notnull(row['puntuacion_igdb']) else "N/A"
                        tiempo = f"{row['hltb_historia_principal']:.1f}h" if pd.notnull(row['hltb_historia_principal']) else "N/A"
                        precio = f"${row['steam_price_final']:.2f}" if pd.notnull(row['steam_price_final']) else "N/A"

                        st.caption(f"{cat}")
                        st.caption(f"Score: {score} | Tiempo: {tiempo}")
                        st.caption(f"Precio: {precio}")
                        st.divider()

        else:
            st.info("No se encontraron resultados para la búsqueda.")

    except Exception as e:
        st.error(f"Error en la consulta: {e}")

else:
    st.write("Ingrese un término para iniciar la exploración del almacén de datos.")