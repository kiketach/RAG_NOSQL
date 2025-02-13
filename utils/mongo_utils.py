from pymongo import MongoClient
from gridfs import GridFS
from bson import ObjectId
import os
from dotenv import load_dotenv
import mimetypes

# Cargar variables de entorno
load_dotenv()

# Conectar a MongoDB
client = MongoClient(os.getenv("MONGO_CONNECTION"))
db = client[os.getenv("DATABASE_NAME")]
fs = GridFS(db)

def subir_archivo_a_gridfs(ruta_archivo, nombre_personalizado):
    """
    Sube un archivo a GridFS y almacena su tipo MIME.
    :param ruta_archivo: Ruta local del archivo a subir.
    :param nombre_personalizado: Nombre personalizado para el archivo en GridFS.
    :return: ID del archivo en GridFS.
    """
    # Determinar el tipo MIME basado en la extensión del archivo
    tipo_mime, _ = mimetypes.guess_type(nombre_personalizado)
    
    with open(ruta_archivo, "rb") as archivo:
        archivo_id = fs.put(
            archivo,
            filename=nombre_personalizado,  # Almacena el nombre personalizado con extensión
            content_type=tipo_mime  # Almacena el tipo MIME
        )
    return archivo_id

def guardar_fragmento_en_mongo(coleccion, documento):
    """
    Guarda un fragmento en MongoDB.
    :param coleccion: Nombre de la colección donde se guardará el documento.
    :param documento: Diccionario con los datos del fragmento.
    """
    collection = db[coleccion]
    collection.insert_one(documento)

def buscar_documentos_por_embedding(coleccion, query_vector):
    """
    Realiza una búsqueda semántica en MongoDB usando vectorSearch.
    :param coleccion: Nombre de la colección donde se realizará la búsqueda.
    :param query_vector: Vector de embedding para la consulta.
    :return: Lista de documentos que coinciden con la consulta.
    """
    resultado = db[coleccion].aggregate([
        {
            "$vectorSearch": {
                "index": "default",  # Nombre del índice de búsqueda vectorial
                "path": "embedding",  # Campo donde están almacenados los embeddings
                "queryVector": query_vector,
                "numCandidates": 300,  # Número de candidatos a considerar
                "limit": 5  # Límite de resultados
            }
        },
        {
            "$project": {
                "_id": 0,  # Excluir el campo _id
                "nombre_archivo": 1,
                "texto_fragmento": 1,
                "archivo_original": 1,
                "score": {"$meta": "vectorSearchScore"}  # Incluir el score de similitud
            }
        },
        {
            "$match": {
                "score": { "$gte": 0.8 }  # Filtrar resultados con un score mínimo
            }
        },
        {
            "$sort": { "score": -1 }  # Ordenar por score descendente
        }
    ])
    return list(resultado)