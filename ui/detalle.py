import streamlit as st
import pandas as pd
import concurrent.futures
import streamlit.components.v1 as components
from db.queries import detalle_juego, obtener_topicos_resenas, score_propio, obtener_generos, obtener_etiquetas
from db.predictor import predecir_descuento
from Agentes.analista import generar_gancho_comercial, generar_analisis_critico

def scroll_to_top():
    js = "<script>window.parent.scrollTo({top: 0, behavior: 'smooth'});</script>"
    components.html(js, height=0)

def mostrar_detalle(conn):
    scroll_to_top()

    juego_df = detalle_juego(conn, st.session_state["juego_seleccionado"])

    if not juego_df.empty:
        juego = juego_df.iloc[0]
        id_juego = int(juego['juego_id'])
        api_key = st.session_state.get("OPENAI_KEY", "")

        score_gl = round(score_propio(juego))
        score_igdb = round(juego['puntuacion_igdb']) if pd.notnull(juego['puntuacion_igdb']) else "N/A"
        score_meta = round(juego['metacritic_score']) if pd.notnull(juego['metacritic_score']) else "N/A"

        if st.button("⬅ Volver"):
            st.session_state["_aplicar_busqueda"] = st.session_state.get("busqueda_guardada", "")
            st.session_state["juego_seleccionado"] = None
            st.rerun()

        st.divider()
        col_izq, col_der = st.columns([1, 3])

        with col_izq:
            st.image(juego['url_portada'] or "https://via.placeholder.com/300x400", use_container_width=True)
            st.caption(f"⏳ **Historia:** {juego['hltb_historia_principal'] or 'N/A'}h | **Completo:** {juego['hltb_completacionista'] or 'N/A'}h")

        with col_der:
            st.title(juego['titulo'])

            precio = f"${juego['steam_price_final']:.2f}" if pd.notnull(juego['steam_price_final']) else "N/A"

            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"#### 🏷️ {precio}")
            c2.markdown(f"#### 💎 {score_gl}")
            c3.markdown(f"#### 🎮 {score_igdb}")
            c4.markdown(f"#### 🏆 {score_meta}")

            st.write("")

            generos_lista = obtener_generos(conn, id_juego)
            etiquetas_lista = obtener_etiquetas(conn, id_juego)

            probabilidad, umbral = predecir_descuento(juego, generos_lista, etiquetas_lista, conn=conn)

            if probabilidad is not None:
                prob_pct = int(probabilidad * 100)

                st.markdown("### 🔮 Radar de Descuentos (7 días)")
                st.progress(probabilidad)

                if probabilidad >= umbral:
                    st.success(f"**¡Espera antes de comprar! ({prob_pct}%)** Hay señales de que el precio bajará pronto. Añádelo a tu lista de deseados y estate atento.")
                elif probabilidad >= (umbral / 2):
                    st.warning(f"**Señales mixtas ({prob_pct}%).** Puede que haya una oferta, pero no hay certeza. Decide según tu urgencia.")
                else:
                    st.info(f"**Sin descuentos previstos ({prob_pct}%).** Es muy poco probable que haya oferta esta semana. Si lo quieres, no hay razón para esperar.")

            st.markdown("---")
            top_pos, top_neg = obtener_topicos_resenas(conn, id_juego)

            with st.spinner("✨ Consultando a los expertos..."):
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futuro_gancho = executor.submit(
                        generar_gancho_comercial,
                        api_key, juego['titulo'], juego['resumen'], juego['historia']
                    )
                    futuro_analisis = executor.submit(
                        generar_analisis_critico,
                        api_key, juego['titulo'], top_pos, top_neg,
                        [juego['hltb_historia_principal'], juego['hltb_historia_extra'], juego['hltb_completacionista']]
                    )

                    gancho = futuro_gancho.result()
                    analisis = futuro_analisis.result()

                st.markdown(f"### Sinopsis\n{gancho}")
                st.write("")
                st.markdown(f"### Veredicto de la Comunidad\n\n{analisis}")
