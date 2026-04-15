import streamlit as st
import pandas as pd
from db.queries import buscar_juegos

def mostrar_resultados(conn, busqueda):
    df = buscar_juegos(conn, busqueda)

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