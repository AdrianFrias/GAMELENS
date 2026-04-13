import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "gaming_warehouse.db"

st.set_page_config(page_title="Project M5 - Explorer", layout="wide")

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎮 Project M5: Gaming Warehouse")

# --- VALIDACIÓN DE CONEXIÓN ---
if not DB_PATH.exists():
    st.error(f"❌ No se encontró la DB en: {DB_PATH}")
    st.stop()

# --- BUSCADOR ---
busqueda = st.text_input("Buscar videojuego por título:", placeholder="Ej. Batman, Witcher, Portal...")

if busqueda:
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Buscamos en CAT_Juego usando la columna 'titulo'
        query = """
            SELECT titulo, categoria, url_portada, puntuacion_igdb, 
                   hltb_historia_principal, hltb_completacionista, 
                   steam_price_final, resumen
            FROM CAT_Juego 
            WHERE titulo LIKE ? and id_steam is not null
            LIMIT 10
        """
        df = pd.read_sql(query, conn, params=(f'%{busqueda}%',))
        conn.close()

        if not df.empty:
            for _, row in df.iterrows():
                # Creamos una "tarjeta" por cada juego usando columnas
                with st.container():
                    col1, col2 = st.columns([1, 4])
                    
                    with col1:
                        # Si hay URL de portada, la mostramos
                        if row['url_portada']:
                            st.image(row['url_portada'], use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/150?text=No+Image", use_container_width=True)
                    
                    with col2:
                        st.subheader(row['titulo'])
                        st.caption(f"Categoría: {row['categoria']} | Score IGDB: {row['puntuacion_igdb'] or 'N/A'}")
                        
                        # Métricas rápidas de HLTB y Precio
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Historia", f"{row['hltb_historia_principal'] or 0}h")
                        m2.metric("100%", f"{row['hltb_completacionista'] or 0}h")
                        m3.metric("Precio Steam", f"${row['steam_price_final'] or 0}")
                        
                        with st.expander("Ver Resumen"):
                            st.write(row['resumen'] if row['resumen'] else "Sin resumen disponible.")
                st.divider()
        else:
            st.warning(f"No se encontraron juegos que coincidan con '{busqueda}'")
            
    except Exception as e:
        st.error(f"Error en la consulta: {e}")

# --- ESTADÍSTICAS RÁPIDAS (Sidebar) ---
with st.sidebar:
    st.header("Estado de la DB")
    if st.button("Verificar Tablas"):
        conn = sqlite3.connect(DB_PATH)
        tablas = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
        st.write(tablas)
        conn.close()