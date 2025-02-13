from openai import OpenAI
import os

# Inicializar cliente de OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text):
    """Genera un embedding usando OpenAI."""
    response = openai_client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding

def generar_respuesta_final(query, fragmento):
    """Genera una respuesta refinada usando OpenAI."""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Responde la pregunta del usuario usando el contexto del fragmento recuperado."},
            {"role": "user", "content": f"Pregunta del usuario: {query}"},
            {"role": "assistant", "content": f"Fragmento recuperado: {fragmento}"}
        ]
    )
    return response.choices[0].message.content