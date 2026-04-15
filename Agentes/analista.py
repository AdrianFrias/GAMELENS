from openai import OpenAI

def generar_gancho_comercial(api_key, titulo, descripcion, historia):
    client = OpenAI(api_key=api_key)
    prompt = f"Eres un publicista de videojuegos. En un párrafo corto y emocionante, cuéntame de qué trata '{titulo}' y por qué debería jugarlo hoy. Usa este contexto: {descripcion}. Historia: {historia}. ¡Sé breve y usa un tono épico!"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=200
        )
        return response.choices[0].message.content
    except: return "No pude generar el gancho comercial."

def generar_analisis_critico(api_key, titulo, top_pos, top_neg, hltb):
    client = OpenAI(api_key=api_key)
    tiempos = f"Principal: {hltb[0]}h, Completo: {hltb[2]}h"
    prompt = f"Eres un crítico experto. Analiza '{titulo}'. Pros: {', '.join(top_pos)}. Contras: {', '.join(top_neg)}. Duración: {tiempos}. Da un veredicto técnico en dos párrafos cortos sobre si vale la pena por su precio y lo que dice la gente."
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=400
        )
        return response.choices[0].message.content
    except: return "Análisis no disponible en este momento."