import joblib
import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

PRIOR_GLOBAL_DESC = 0.19
PRIOR_METACRITIC_SCORE = 72.0


@st.cache_resource
def cargar_modelo():
    try:
        modelo = joblib.load(MODELS_DIR / "modelo_descuentos_rf.pkl")
        umbral = joblib.load(MODELS_DIR / "threshold_descuentos.pkl")
        columnas = joblib.load(MODELS_DIR / "features_cols.pkl")
        return modelo, umbral, columnas
    except Exception:
        return None, None, None


def _seguro_num(val, default=0.0):
    try:
        v = float(val)
        return default if np.isnan(v) else v
    except (TypeError, ValueError):
        return default


def _features_historial(conn, itad_id, hoy, fecha_lanzamiento=None):
    defaults = dict(
        dias_desde_ultimo_desc=60,
        n_eventos_desc=0,
        desc_max_historico=0.0,
        desc_avg_historico=0.0,
        frecuencia_desc=-1.0,
        duracion_promedio_desc=0.0,
        cooldown_mediano=-1.0,
        esta_en_cooldown=0,
        ratio_precio_vs_base=1.0,
        esta_en_precio_full=1,
        ratio_precio_vs_minimo=-1.0,
        tiempo_hasta_primer_desc=64.0,
    )

    if conn is None or not itad_id:
        return defaults

    try:
        query = """
            SELECT precio_base, precio, descuento,
                   datetime(fecha_unix, 'unixepoch') AS fecha
            FROM   Hist_Precios_ITAD
            WHERE  itad_id_texto = ?
            ORDER  BY fecha_unix
        """
        df = pd.read_sql(query, conn, params=(itad_id,))
        if df.empty:
            return defaults

        df["fecha"] = pd.to_datetime(df["fecha"])
        eventos = df[df["descuento"] >= 20]
        n = len(eventos)

        if n > 0:
            ultimo = eventos["fecha"].max()
            dias_desde_ultimo = max(0, (hoy - ultimo).days)
        else:
            dias_desde_ultimo = -1

        desc_max = float(eventos["descuento"].max()) if n > 0 else 0.0
        desc_avg = round(float(eventos["descuento"].mean()), 2) if n > 0 else 0.0

        if n >= 2:
            rango = (df["fecha"].max() - df["fecha"].min()).days
            frecuencia = round(rango / n, 1)
        else:
            frecuencia = -1.0

        if n > 0:
            flags = (df["descuento"] >= 20).astype(int).tolist()
            duraciones, dur = [], 0
            for flag in flags:
                if flag == 1:
                    dur += 1
                elif dur > 0:
                    duraciones.append(dur)
                    dur = 0
            if dur > 0:
                duraciones.append(dur)
            duracion_prom = round(float(np.mean(duraciones)), 1) if duraciones else 1.0
        else:
            duracion_prom = 0.0

        if n >= 2:
            fechas_desc = eventos["fecha"].sort_values().values
            gaps = [
                int((fechas_desc[j + 1] - fechas_desc[j]) / np.timedelta64(1, "D"))
                for j in range(len(fechas_desc) - 1)
            ]
            cooldown = int(np.median(gaps))
            en_cooldown = 1 if (dias_desde_ultimo != -1 and dias_desde_ultimo < cooldown) else 0
        else:
            cooldown = -1
            en_cooldown = 0

        ultima = df.iloc[-1]
        precio_base_actual = _seguro_num(ultima["precio_base"], default=1.0) or 1.0
        precio_actual = _seguro_num(ultima["precio"])
        descuento_actual = _seguro_num(ultima["descuento"])

        ratio_vs_base = round(precio_actual / precio_base_actual, 4) if precio_base_actual > 0 else 1.0
        en_precio_full = 1 if descuento_actual == 0 else 0

        precio_min = None
        eventos_precio = df[df["descuento"] >= 20]["precio"]
        if not eventos_precio.empty:
            precio_min = float(eventos_precio.min())

        ratio_vs_min = round(precio_actual / precio_min, 4) if precio_min and precio_min > 0 else -1.0

        tiempo_primer_desc = 64.0
        if n > 0 and fecha_lanzamiento is not None:
            try:
                primer_desc = eventos["fecha"].min()
                tiempo_primer_desc = float(max(0, (primer_desc - fecha_lanzamiento).days))
            except Exception:
                pass

        return dict(
            dias_desde_ultimo_desc=dias_desde_ultimo,
            n_eventos_desc=n,
            desc_max_historico=desc_max,
            desc_avg_historico=desc_avg,
            frecuencia_desc=frecuencia,
            duracion_promedio_desc=duracion_prom,
            cooldown_mediano=float(cooldown),
            esta_en_cooldown=en_cooldown,
            ratio_precio_vs_base=ratio_vs_base,
            esta_en_precio_full=en_precio_full,
            ratio_precio_vs_minimo=ratio_vs_min,
            tiempo_hasta_primer_desc=tiempo_primer_desc,
        )

    except Exception:
        return defaults


def _features_publisher(conn, juego_id):
    defaults = dict(
        desc_max_publisher=50.0,
        freq_desc_publisher=0.1,
        pct_juegos_publisher_con_desc=0.5,
        otros_juegos_publisher_en_desc_ahora=0,
        publisher_en_sale_activa=0,
    )

    if conn is None or not juego_id:
        return defaults

    try:
        empresa_df = pd.read_sql(
            "SELECT empresa_id FROM REL_Juego_Editor WHERE juego_id = ? LIMIT 1",
            conn,
            params=(int(juego_id),),
        )
        if empresa_df.empty:
            return defaults

        empresa_id = int(empresa_df.iloc[0, 0])

        query_pub = """
            SELECT j.itad_id_texto
            FROM   REL_Juego_Editor re
            JOIN   CAT_Juego j ON j.juego_id = re.juego_id
            WHERE  re.empresa_id = ?
              AND  j.itad_id_texto IS NOT NULL
              AND  j.juego_id NOT IN (SELECT juego_id_dlc FROM REL_Juego_DLC)
        """
        pub_juegos = pd.read_sql(query_pub, conn, params=(empresa_id,))
        if pub_juegos.empty:
            return defaults

        itad_ids = pub_juegos["itad_id_texto"].dropna().tolist()
        placeholders = ",".join(["?"] * len(itad_ids))

        query_hist = f"""
            SELECT itad_id_texto,
                   MAX(descuento)                             AS desc_max,
                   AVG(CASE WHEN descuento >= 20 THEN 1.0 ELSE 0.0 END) AS freq_desc
            FROM   Hist_Precios_ITAD
            WHERE  itad_id_texto IN ({placeholders})
            GROUP  BY itad_id_texto
        """
        hist = pd.read_sql(query_hist, conn, params=itad_ids)
        if hist.empty:
            return defaults

        desc_max_pub = float(hist["desc_max"].max())
        freq_pub = float(hist["freq_desc"].mean())
        pct_con_desc = float((hist["desc_max"] >= 20).mean())

        query_actual = f"""
            SELECT itad_id_texto, descuento_actual
            FROM   Datos_Actuales_ITAD
            WHERE  itad_id_texto IN ({placeholders})
        """
        actuals = pd.read_sql(query_actual, conn, params=itad_ids)
        otros_en_desc = 0
        pub_en_sale = 0
        if not actuals.empty:
            en_desc = (actuals["descuento_actual"] >= 20).sum()
            otros_en_desc = max(0, int(en_desc) - 1)
            pub_en_sale = 1 if en_desc > 0 else 0

        return dict(
            desc_max_publisher=desc_max_pub,
            freq_desc_publisher=freq_pub,
            pct_juegos_publisher_con_desc=pct_con_desc,
            otros_juegos_publisher_en_desc_ahora=otros_en_desc,
            publisher_en_sale_activa=pub_en_sale,
        )

    except Exception:
        return defaults


def _features_tenc_etiquetas(conn, juego_id):
    defaults = dict(
        tenc_etiqueta_top1=PRIOR_GLOBAL_DESC,
        tenc_etiqueta_top2=PRIOR_GLOBAL_DESC,
        tenc_etiqueta_top3=PRIOR_GLOBAL_DESC,
    )

    if conn is None or not juego_id:
        return defaults

    try:
        query = """
            SELECT e.etiqueta_id,
                   COUNT(*) OVER (PARTITION BY e.etiqueta_id) AS freq_global
            FROM   REL_Juego_Etiqueta r
            JOIN   CAT_Etiqueta e ON r.etiqueta_id = e.etiqueta_id
            WHERE  r.juego_id = ?
            ORDER  BY freq_global DESC
            LIMIT  3
        """
        top3 = pd.read_sql(query, conn, params=(int(juego_id),))
        if top3.empty:
            return defaults

        vals = [PRIOR_GLOBAL_DESC] * 3
        return dict(
            tenc_etiqueta_top1=vals[0],
            tenc_etiqueta_top2=vals[1] if len(top3) > 1 else PRIOR_GLOBAL_DESC,
            tenc_etiqueta_top3=vals[2] if len(top3) > 2 else PRIOR_GLOBAL_DESC,
        )

    except Exception:
        return defaults


def predecir_descuento(juego, generos, etiquetas, conn=None):
    modelo, umbral, columnas = cargar_modelo()
    if modelo is None:
        return None, None

    hoy = pd.Timestamp.now()
    mes = hoy.month

    target_junio = pd.Timestamp(
        year=hoy.year if mes <= 6 else hoy.year + 1, month=6, day=25
    )
    target_dic = pd.Timestamp(
        year=hoy.year if mes <= 12 else hoy.year + 1, month=12, day=22
    )
    dias_para_junio = (target_junio - hoy).days
    dias_para_diciembre = (target_dic - hoy).days

    edad_dias = 365
    fecha_lanz = None
    if pd.notna(juego.get("fecha_lanzamiento")):
        try:
            fecha_lanz = pd.to_datetime(juego["fecha_lanzamiento"])
            edad_dias = max(0, (hoy - fecha_lanz).days)
        except Exception:
            pass

    itad_id = juego.get("itad_id_texto")
    juego_id = juego.get("juego_id")

    hist = _features_historial(conn, itad_id, hoy, fecha_lanzamiento=fecha_lanz)
    pub = _features_publisher(conn, juego_id)
    tenc = _features_tenc_etiquetas(conn, juego_id)

    datos = {
        "mes": mes,
        "semana": hoy.isocalendar()[1],
        "es_junio": 1 if mes == 6 else 0,
        "es_diciembre": 1 if mes == 12 else 0,
        "dias_para_junio": dias_para_junio,
        "dias_para_diciembre": dias_para_diciembre,
        "dias_desde_ultimo_desc": hist["dias_desde_ultimo_desc"],
        "n_eventos_desc": hist["n_eventos_desc"],
        "desc_max_historico": hist["desc_max_historico"],
        "desc_avg_historico": hist["desc_avg_historico"],
        "frecuencia_desc": hist["frecuencia_desc"],
        "duracion_promedio_desc": hist["duracion_promedio_desc"],
        "cooldown_mediano": hist["cooldown_mediano"],
        "esta_en_cooldown": hist["esta_en_cooldown"],
        "ratio_precio_vs_base": hist["ratio_precio_vs_base"],
        "esta_en_precio_full": hist["esta_en_precio_full"],
        "ratio_precio_vs_minimo": hist["ratio_precio_vs_minimo"],
        "desc_max_publisher": pub["desc_max_publisher"],
        "freq_desc_publisher": pub["freq_desc_publisher"],
        "pct_juegos_publisher_con_desc": pub["pct_juegos_publisher_con_desc"],
        "otros_juegos_publisher_en_desc_ahora": pub["otros_juegos_publisher_en_desc_ahora"],
        "publisher_en_sale_activa": pub["publisher_en_sale_activa"],
        "puntuacion_igdb": _seguro_num(juego.get("puntuacion_igdb")),
        "metacritic_score": _seguro_num(juego.get("metacritic_score"), default=PRIOR_METACRITIC_SCORE),
        "recommendations_count": _seguro_num(juego.get("recommendations_count")),
        "conteo_dlc": _seguro_num(juego.get("conteo_dlc")),
        "edad_dias": float(edad_dias),
        "tiempo_hasta_primer_desc": hist["tiempo_hasta_primer_desc"],
        "tenc_etiqueta_top1": tenc["tenc_etiqueta_top1"],
        "tenc_etiqueta_top2": tenc["tenc_etiqueta_top2"],
        "tenc_etiqueta_top3": tenc["tenc_etiqueta_top3"],
    }

    df_pred = pd.DataFrame([datos])
    generos_lower = [g.lower() for g in generos]
    etiquetas_lower = [e.lower() for e in etiquetas]

    for col in columnas:
        if col in df_pred.columns:
            continue
        col_lower = col.lower()
        if col_lower.startswith("genero_"):
            sufijo = col_lower[len("genero_"):]
            df_pred[col] = 1 if sufijo in generos_lower else 0
        elif col_lower.startswith("genre_"):
            sufijo = col_lower[len("genre_"):]
            df_pred[col] = 1 if sufijo in generos_lower else 0
        elif col_lower.startswith("etiqueta_") or col_lower.startswith("tag_"):
            df_pred[col] = 1 if any(e in col_lower for e in etiquetas_lower) else 0
        elif col_lower.startswith("categoria_") or col_lower.startswith("category_"):
            cat_juego = str(juego.get("categoria", "")).lower()
            df_pred[col] = 1 if cat_juego in col_lower else 0
        else:
            df_pred[col] = 0

    df_final: pd.DataFrame = pd.DataFrame(df_pred[columnas]).astype(float)
    probabilidad = float(modelo.predict_proba(df_final)[0][1])
    return probabilidad, umbral
