"""
Tool: Base de Conocimiento (RAG con Supabase)
Permite buscar en el Manual de Trámites del Municipio de Girardota.

Autor: Ing. Kevin Inofuente Colque - DataPath
"""

import os
import json
import numpy as np
from dotenv import load_dotenv, find_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool
from supabase import create_client

load_dotenv(find_dotenv())

# ============================================
# CONFIGURACIÓN DE SUPABASE
# ============================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError(
        "❌ Faltan variables de Supabase en .env\n"
        "Requeridas: SUPABASE_URL, SUPABASE_SECRET_KEY"
    )

supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
embedding_model = OpenAIEmbeddings(model='text-embedding-ada-002')

# Nombre de la tabla de documentos
TABLA_DOCUMENTOS = "documents_langchain_asistente_de_informacion"


# ============================================
# FUNCIONES INTERNAS
# ============================================
def calcular_similitud_coseno(vec1, vec2):
    """Calcula la similitud de coseno entre dos vectores."""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return 1 - np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def buscar_en_base_conocimiento_interno(query: str, top_k: int = 5) -> str:
    """
    Función interna de búsqueda RAG.
    
    Args:
        query: Consulta de búsqueda
        top_k: Número de documentos a retornar
    
    Returns:
        str: Información encontrada formateada
    """
    try:
        # Generar embedding de la consulta
        query_embedding = embedding_model.embed_query(query)
        
        # Obtener documentos de Supabase
        result = supabase_client.table(TABLA_DOCUMENTOS).select('*').execute()
        
        if not result.data:
            return "No hay documentos en la base de conocimientos."
        
        # Calcular similitud para cada documento
        documentos_con_score = []
        for doc in result.data:
            if doc.get('embedding'):
                doc_embedding = doc['embedding']
                if isinstance(doc_embedding, str):
                    doc_embedding = json.loads(doc_embedding)
                
                doc_embedding = [float(x) for x in doc_embedding]
                score = calcular_similitud_coseno(query_embedding, doc_embedding)
                
                documentos_con_score.append({
                    'content': doc.get('content', ''),
                    'score': score
                })
        
        # Ordenar por similitud
        documentos_con_score.sort(key=lambda x: x['score'])
        top_docs = documentos_con_score[:top_k]
        
        if not top_docs:
            return "No encontré información relevante."
        
        # Formatear resultados
        contexto = "Información encontrada:\n\n"
        for i, doc in enumerate(top_docs, 1):
            similitud = 1 - doc['score']
            contexto += f"[{i}] (Relevancia: {similitud:.0%})\n{doc['content']}\n\n"
        
        return contexto
        
    except Exception as e:
        return f"Error al buscar: {str(e)}"


# ============================================
# TOOL EXPORTABLE
# ============================================
@tool
def buscar_informacion_tramites(consulta: str) -> str:
    """
    Busca información sobre TRAMITES en la base de conocimientos.
    Usa esta herramienta cuando el usuario pregunte sobre:
    - Los requisitos.
    - Propósitos.
    - Tiempos de respuesta.
    - Costos y cuentas bancarias de los trámites administrativos.
    y toda información oficial ante las distintas secretarias del Municipio de Girardota, Colombia.
    
    Args:
        consulta: La pregunta o tema a buscar
    """
    print(f"   🔍 Buscando: '{consulta}'")
    resultado = buscar_en_base_conocimiento_interno(consulta)
    return resultado
