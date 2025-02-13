import os
import base64
from bson import ObjectId
from utils.mongo_utils import db, fs

def fragmentar_texto(texto, tamano_fragmento=700, solapamiento=300):
    """Fragmenta un texto en partes más pequeñas."""
    palabras = texto.split()
    fragmentos = []
    for i in range(0, len(palabras), tamano_fragmento - solapamiento):
        fragmento = " ".join(palabras[i:i + tamano_fragmento])
        fragmentos.append(fragmento)
    return fragmentos

def limpiar_texto(texto):
    """Limpia un texto eliminando espacios innecesarios."""
    return " ".join(texto.split())

def generar_link_descarga(archivo_id):
    """Genera un enlace de descarga para un archivo almacenado en GridFS."""
    try:
        file_data = fs.get(ObjectId(archivo_id))
        nombre_archivo = file_data.filename
        tipo_mime = file_data.content_type or "application/octet-stream"
        b64 = base64.b64encode(file_data.read()).decode()
        return f'<a href="data:{tipo_mime};base64,{b64}" download="{nombre_archivo}">📥 Descargar archivo</a>'
    except Exception as e:
        print(f"Error al recuperar el archivo: {e}")
        return None

def eliminar_archivo(archivo_id):
    """
    Elimina un archivo de GridFS y su referencia en la colección 'archivos'.
    :param archivo_id: ID del archivo en GridFS.
    """
    try:
        archivo_id = ObjectId(archivo_id) # Convertir a ObjectId        
        # Eliminar el archivo de GridFS
        fs.delete(archivo_id)  # Esto elimina tanto el registro en fs.files como los chunks en fs.chunks
        
        # Eliminar la referencia del archivo en la colección 'archivos'
        db["archivos"].delete_many({"archivo_original": archivo_id})
        
        print(f"Archivo con ID {archivo_id} eliminado correctamente.")
    except Exception as e:
        print(f"Error al eliminar el archivo: {e}")