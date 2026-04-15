import pandas as pd

def obtener_generos(conn, juego_id):
    query = """
    SELECT g.nombre
    FROM REL_Juego_Genero r
    JOIN CAT_Genero g ON r.genero_id = g.genero_id
    WHERE r.juego_id = ?
    """
    df = pd.read_sql(query, conn, params=(juego_id,))
    return df['nombre'].tolist()

def obtener_etiquetas(conn, juego_id):
    query = """
    SELECT e.nombre
    FROM REL_Juego_Etiqueta r
    JOIN CAT_Etiqueta e ON r.etiqueta_id = e.etiqueta_id
    WHERE r.juego_id = ?
    """
    df = pd.read_sql(query, conn, params=(juego_id,))
    return df['nombre'].tolist()

def score_propio(row):
    score = 0
    if pd.notnull(row['puntuacion_igdb']):
        score += row['puntuacion_igdb'] * 0.4
    if pd.notnull(row['metacritic_score']):
        score += row['metacritic_score'] * 0.4
    if pd.notnull(row['recommendations_count']):
        score += min(row['recommendations_count'] / 1000, 1) * 20
    return round(score, 1)

def juegos_similares(conn, juego_id):
    query = """
    SELECT j2.titulo, j2.url_portada
    FROM REL_Juego_Etiqueta r1
    JOIN REL_Juego_Etiqueta r2 ON r1.etiqueta_id = r2.etiqueta_id
    JOIN CAT_Juego j2 ON j2.juego_id = r2.juego_id
    WHERE r1.juego_id = ? AND j2.juego_id != ?
    GROUP BY j2.juego_id
    ORDER BY COUNT(*) DESC
    LIMIT 10
    """
    return pd.read_sql(query, conn, params=(juego_id, juego_id))

def detalle_juego(conn, titulo):
    query = """
        SELECT *
        FROM CAT_Juego
        WHERE titulo = ?
        LIMIT 1
    """
    return pd.read_sql(query, conn, params=(titulo,))

def buscar_juegos(conn, busqueda):
    query = """
        SELECT titulo, categoria, url_portada, hltb_historia_principal,
               steam_price_final, puntuacion_igdb
        FROM CAT_Juego
        WHERE titulo LIKE ?
        AND id_steam IS NOT NULL
        LIMIT 50
    """
    df = pd.read_sql(query, conn, params=(f'%{busqueda}%',))
    if not df.empty:
        df['completitud'] = df[['categoria', 'hltb_historia_principal', 'steam_price_final', 'puntuacion_igdb']].notnull().sum(axis=1)
        df = df.sort_values(by=['steam_price_final', 'completitud'], ascending=[False, False])
    return df