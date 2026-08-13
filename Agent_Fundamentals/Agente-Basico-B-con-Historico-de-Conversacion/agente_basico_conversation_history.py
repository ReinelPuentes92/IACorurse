"""
Agente IA con Histórico de Conversación en PostgreSQL
Mantiene memoria persistente de las conversaciones

Este agente:
- Guarda cada mensaje en PostgreSQL
- Recuerda conversaciones anteriores
- Puede retomar conversaciones por session_id

Autor: Ing. Kevin Inofuente Colque - DataPath
"""

import os
import uuid
from urllib.parse import quote_plus
from dotenv import load_dotenv, find_dotenv

# Busca el .env en la carpeta actual o en las carpetas padre
load_dotenv(find_dotenv())

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_postgres import PostgresChatMessageHistory
import psycopg


# ============================================
# 1. CONFIGURACIÓN DE BASE DE DATOS
# ============================================
# Variables de entorno esperadas en .env (en la raíz del proyecto):
# DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")  # Default: 5432
DB_NAME = os.getenv("DB_NAME", "postgres")  # Default: postgres

# Validar que las variables requeridas estén configuradas
if not all([DB_USER, DB_PASSWORD, DB_HOST]):
    raise ValueError(
        "❌ Faltan variables de base de datos en .env\n"
        "Requeridas: DB_USER, DB_PASSWORD, DB_HOST\n"
        "Opcionales: DB_PORT (default: 5432), DB_NAME (default: postgres)"
    )

# Construir la URL de conexión (quote_plus maneja caracteres especiales como @)
DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Debug: mostrar qué usuario se está usando (sin mostrar password)
print(f"🔌 Conectando como: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# ============================================
# 2. CONFIGURACIÓN DEL MODELO
# ============================================
chat = init_chat_model(
    "gpt-4.1",
    #"google_genai:gemini-3-flash-preview",
    temperature=0.7,
)

# ============================================
# 3. PROMPT CON PLACEHOLDER PARA HISTORIAL
# ============================================
prompt = ChatPromptTemplate.from_messages([
    ("system", """Eres un asistente de IA útil y amigable llamado DataBot.
Responde las preguntas del usuario de manera clara y concisa.
Puedes recordar conversaciones anteriores gracias a tu memoria persistente.
Responde siempre en español."""),
    MessagesPlaceholder(variable_name="history"),  # Aquí se inyecta el historial
    ("human", "{input}")
])

# ============================================
# 4. CREAR LA CHAIN BASE
# ============================================
chain = prompt | chat

# ============================================
# 5. CREAR TABLA DE HISTORIAL (si no existe)
# ============================================
# Crear la tabla en PostgreSQL si no existe
def crear_tabla_historial():
    """Crea la tabla de historial si no existe."""
    try:
        sync_connection = psycopg.connect(DATABASE_URL)
        PostgresChatMessageHistory.create_tables(sync_connection, "chat_history_usuarios_consultas")
        sync_connection.close()
    except Exception as e:
        print(f"⚠️ Nota sobre tabla: {e}")

crear_tabla_historial()

# ============================================
# 6. FUNCIÓN PARA OBTENER HISTORIAL DE POSTGRES
# ============================================
def get_session_history(session_id: str) -> PostgresChatMessageHistory:
    """
    Obtiene o crea el historial de una sesión desde PostgreSQL.
    """
    sync_connection = psycopg.connect(DATABASE_URL)
    return PostgresChatMessageHistory(
        "chat_history_usuarios_consultas",  # nombre de la tabla
        session_id,
        sync_connection=sync_connection
    )

# ============================================
# 7. CHAIN CON MEMORIA PERSISTENTE
# ============================================
chain_con_historial = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

# ============================================
# 8. FUNCIÓN DE CHAT
# ============================================
def chat_con_agente(mensaje_usuario: str, session_id: str) -> str:
    """
    Envía un mensaje al agente con historial persistente.
    
    Args:
        mensaje_usuario: El mensaje del usuario
        session_id: ID único de la sesión/conversación
    
    Returns:
        La respuesta del agente
    """
    respuesta = chain_con_historial.invoke(
        {"input": mensaje_usuario},
        config={"configurable": {"session_id": session_id}}
    )
    return respuesta.content

# ============================================
# 9. LOOP DE CONVERSACIÓN
# ============================================
def main():
    print("=" * 60)
    print("🤖 DataBot - Agente CON MEMORIA PERSISTENTE (PostgreSQL)")
    print("=" * 60)
    
    # Pedir session_id (UUID) o generar uno nuevo
    print("\nOpciones de sesión:")
    print("  1. Nueva conversación")
    print("  2. Continuar sesión existente (pegar UUID)")
    
    opcion = input("\nElige (1/2): ").strip()
    
    if opcion == "2":
        session_id = input("Pega el UUID de la sesión: ").strip()
        # Validar que sea un UUID válido
        try:
            uuid.UUID(session_id)
        except ValueError:
            print("⚠️ UUID inválido. Creando nueva sesión...")
            session_id = str(uuid.uuid4())
    else:
        session_id = str(uuid.uuid4())
    
    print(f"\n📝 Session ID: {session_id}")
    print("   (Guarda este ID para continuar la conversación después)")
    print("✅ Este agente RECUERDA tus mensajes anteriores")
    print("Escribe 'salir' para terminar.\n")
    
    while True:
        usuario = input("Tú: ").strip()
        
        if usuario.lower() in ['salir', 'exit', 'quit']:
            print(f"\n💾 Tu sesión está guardada.")
            print(f"   UUID: {session_id}")
            print("👋 ¡Hasta luego!")
            break
        
        if not usuario:
            continue
        
        try:
            respuesta = chat_con_agente(usuario, session_id)
            print(f"\n🤖 DataBot: {respuesta}\n")
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    main()