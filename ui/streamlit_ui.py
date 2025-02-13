import streamlit as st
from utils.mongo_utils import db, subir_archivo_a_gridfs, guardar_fragmento_en_mongo, buscar_documentos_por_embedding
from utils.openai_utils import get_embedding, generar_respuesta_final
from utils.file_utils import fragmentar_texto, limpiar_texto, generar_link_descarga, eliminar_archivo
import os
from datetime import datetime, timezone

def run_app():
    # Configuración de la página
    st.set_page_config(page_title="Consulta de papeles de auditorías", layout="wide")
    
# Agregar logo en el sidebar
    logo_path = "./data/logo.png"
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, use_container_width=True)
    
    # Sidebar
    st.sidebar.title("Menú")
    opcion = st.sidebar.radio("Selecciona una función:", ["ETL", "Consulta Semántica", "Eliminar Archivo"])
    
    if opcion == "ETL":
        procesar_etl()
    elif opcion == "Consulta Semántica":
        realizar_consulta()
    elif opcion == "Eliminar Archivo":
        mostrar_archivos_para_eliminar()

def procesar_etl():
    st.title("📂 Procesamiento de Documentos (ETL)")
    archivo_cargado = st.file_uploader("Cargar archivo")
    coleccion = st.text_input("Nombre de la colección:", "archivos")
    nombre_personalizado = st.text_input("Nombre personalizado para el archivo:", "")
    
    if st.button("Procesar"):
        if archivo_cargado is not None:
            ruta_temporal = f"./temp_{archivo_cargado.name}"
            with open(ruta_temporal, "wb") as f:
                f.write(archivo_cargado.getvalue())
            mensaje = procesar_documento(ruta_temporal, coleccion, nombre_personalizado)
            st.success(mensaje)
            os.remove(ruta_temporal)
        else:
            st.error("Por favor, carga un archivo.")

def realizar_consulta():
    st.title("📂 Consulta de papeles de auditorías")
    query_text = st.text_input("🔍 Escribe tu pregunta sobre la auditoría:")
    
    if st.button("Buscar respuesta"):
        if query_text:
            st.write("⏳ Buscando en la base de datos...")
            respuesta = buscar_respuesta_semantica(query_text)
            if respuesta:
                st.subheader("✅ Respuesta final")
                st.write(respuesta["respuesta"])
                with st.expander("📄 Ver fragmento recuperado"):
                    st.write(respuesta["fragmento"])
                if respuesta["link_descarga"]:
                    st.markdown(respuesta["link_descarga"], unsafe_allow_html=True)
            else:
                st.error("❌ No se encontraron respuestas relevantes.")
        else:
            st.error("Por favor, ingresa una pregunta.")

def procesar_documento(ruta_archivo, coleccion, nombre_personalizado):
    from utils.azure_utils import analyze_local_document
    
    # Extraer texto y tablas
    resultado = analyze_local_document(ruta_archivo)
    
    # Procesar texto
    texto_extraido = "\n".join([p.content for p in resultado.paragraphs]) if resultado.paragraphs else ""
    texto_limpio = limpiar_texto(texto_extraido)
    fragmentos = fragmentar_texto(texto_limpio)
    
    # Procesar tablas
    tablas = []
    if resultado.tables:
        for table_idx, table in enumerate(resultado.tables):
            tabla = {
                "table_idx": table_idx,
                "row_count": table.row_count,
                "column_count": table.column_count,
                "celdas": []
            }
            for cell in table.cells:
                tabla["celdas"].append({
                    "fila": cell.row_index,
                    "columna": cell.column_index,
                    "contenido": cell.content
                })
            tablas.append(tabla)
    
    # Subir archivo a GridFS
    archivo_id = subir_archivo_a_gridfs(ruta_archivo, nombre_personalizado)
    
    # Guardar fragmentos de texto
    for i, fragmento in enumerate(fragmentos):
        embedding = get_embedding(fragmento)
        documento = {
            "nombre_archivo": nombre_personalizado,
            "tipo_archivo": ruta_archivo.split(".")[-1],
            "texto_fragmento": fragmento,
            "embedding": embedding,
            "archivo_original": archivo_id,
            "indice_fragmento": i,
            "fecha_procesado": datetime.now(timezone.utc)
        }
        guardar_fragmento_en_mongo(coleccion, documento)
    
    # Guardar tablas
    if tablas:
        for tabla in tablas:
            documento_tabla = {
                "nombre_archivo": nombre_personalizado,
                "tipo_archivo": ruta_archivo.split(".")[-1],
                "tabla": tabla,
                "archivo_original": archivo_id,
                "fecha_procesado": datetime.now(timezone.utc)
            }
            guardar_fragmento_en_mongo("tablas", documento_tabla)  # Usar una colección separada para tablas
    
    return f"Archivo {nombre_personalizado} procesado con éxito. {len(fragmentos)} fragmentos creados y {len(tablas)} tablas procesadas."

def buscar_respuesta_semantica(query_text):
    query_vector = get_embedding(query_text)
    
    # Buscar en fragmentos de texto (colección 'archivos')
    resultado_texto = buscar_documentos_por_embedding("archivos", query_vector)
    
    # Buscar en tablas (colección 'tablas')
    resultado_tablas = buscar_documentos_por_embedding("tablas", query_vector)
    
    # Combinar resultados y seleccionar el más relevante
    resultados_combinados = resultado_texto + resultado_tablas
    
    if resultados_combinados:
        # Ordenar resultados por similitud (asumiendo que `buscar_documentos_por_embedding` devuelve resultados ordenados)
        resultados_combinados.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Seleccionar el resultado más relevante
        mejor_resultado = resultados_combinados[0]
        
        # Generar respuesta final
        if "texto_fragmento" in mejor_resultado:
            respuesta_final = generar_respuesta_final(query_text, mejor_resultado["texto_fragmento"])
            fragmento = mejor_resultado["texto_fragmento"]
        else:
            # Si es una tabla, convertirla a texto para generar la respuesta
            tabla = mejor_resultado["tabla"]
            texto_tabla = "\n".join(
                [f"Fila {celda['fila']}, Columna {celda['columna']}: {celda['contenido']}"
                 for celda in tabla["celdas"]]
            )
            respuesta_final = generar_respuesta_final(query_text, texto_tabla)
            fragmento = texto_tabla
        
        # Generar enlace de descarga
        archivo_asociado = mejor_resultado["archivo_original"]
        nombre_archivo = mejor_resultado["nombre_archivo"]
        link_descarga = generar_link_descarga(archivo_asociado)
        
        return {
            "respuesta": respuesta_final,
            "fragmento": fragmento,
            "link_descarga": link_descarga
        }
    return None
def mostrar_archivos_para_eliminar():
    """
    Muestra una lista de archivos almacenados en la colección 'archivos' y permite eliminar uno.
    """
    st.title("Eliminar Archivo")
    
    # Obtener la lista de archivos desde la colección 'archivos'
    archivos = list(db["archivos"].find({}, {"nombre_archivo": 1, "archivo_original": 1}))
    
    if not archivos:
        st.write("No hay archivos disponibles para eliminar.")
        return
    
    # Crear una lista de nombres de archivo para el selector
    opciones = [f"{archivo['nombre_archivo']} (ID: {archivo['archivo_original']})" for archivo in archivos]
    seleccion = st.selectbox("Selecciona un archivo para eliminar:", opciones)
    
    if st.button("Eliminar Archivo"):
        # Extraer el ID del archivo seleccionado
        archivo_id = seleccion.split("(ID: ")[1].rstrip(")")
        
        # Llamar a la función para eliminar el archivo
        eliminar_archivo(archivo_id)
        st.success("Archivo eliminado correctamente.")