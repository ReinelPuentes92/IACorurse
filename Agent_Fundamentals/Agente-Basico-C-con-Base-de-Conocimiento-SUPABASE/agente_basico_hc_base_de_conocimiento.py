"""
Agente IA con Tools + Histórico de Conversación
- RAG como Tool: El LLM decide cuándo buscar en la base de conocimiento
- Histórico: Guarda conversaciones en PostgreSQL
- Extensible: Fácil agregar más Tools

Autor: Ing. Kevin Inofuente Colque - DataPath
"""

import os
import sys
import uuid
from urllib.parse import quote_plus
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Agregar el directorio raíz al path para importar tools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_postgres import PostgresChatMessageHistory
import psycopg

# Importar tools desde la carpeta tools/
from tools.Base_de_conocimiento import buscar_informacion_tramites

# ============================================
# 1. CONFIGURACIÓN DE BASE DE DATOS (Histórico)
# ============================================
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

if not all([DB_USER, DB_PASSWORD, DB_HOST]):
    raise ValueError(
        "❌ Faltan variables de base de datos en .env\n"
        "Requeridas: DB_USER, DB_PASSWORD, DB_HOST"
    )

DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"🔌 Conectando como: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# ============================================
# 2. LISTA DE TOOLS DISPONIBLES
# ============================================
# Agregar aquí todas las tools que quieras usar
tools = [
    buscar_informacion_tramites,
]

# ============================================
# 3. CONFIGURACIÓN DEL MODELO CON TOOLS
# ============================================
chat = init_chat_model("gpt-4.1", temperature=0.7)
chat_con_tools = chat.bind_tools(tools)

# ============================================
# 4. PROMPT DEL AGENTE
# ============================================
system_prompt = """<system_prompt>
  <identity>
    <name>Sofía</name>
    <role>Asistente Virtual experta en atención al ciudadano</role>
    <organization>Municipio de Girardota</organization>
    <nature>Sistema de inteligencia artificial</nature>
    <tone>Empático, claro, servicial y profesional</tone>
  </identity>

  <objective>
    Orientar a los usuarios respondiendo sus consultas sobre trámites administrativos,
    impuestos, certificados y servicios del municipio, basándote ÚNICAMENTE en la base
    de conocimiento oficial proporcionada.
  </objective>

  <core_rules>
    <rule id="1" name="uso_estricto_de_herramienta">
      Para CUALQUIER pregunta relacionada con requisitos, costos, cuentas bancarias,
      tiempos de respuesta o procedimientos de la Alcaldía, DEBES invocar la herramienta
      <tool>buscar_informacion_tramites</tool>.
    </rule>

    <rule id="2" name="cero_alucinaciones">
      Si la herramienta no devuelve la información solicitada, o el trámite consultado
      no existe en la base de datos, informa amablemente que no dispones de esos datos
      precisos. NUNCA inventes requisitos, tarifas ni nombres de formularios.
    </rule>

    <rule id="3" name="estructura_de_respuesta">
      Al detallar un trámite, organiza la información así:
      - Requisitos: listas con viñetas (bullet points).
      - Tiempo de obtención: mención obligatoria.
      - Costo asociado: mención obligatoria si aplica.
    </rule>

    <rule id="4" name="conversacion_general">
      Para saludos, despedidas, agradecimientos o charla general, responde directamente
      SIN invocar herramientas, de forma natural y concisa. Recuerdas toda la
      conversación gracias a tu memoria persistente.
    </rule>
  </core_rules>

  <tool_usage_guide>
    <no_usar_herramienta label="Casos donde NO se usa la herramienta">
      <example>
        <user>Hola, buenos días</user>
        <sofia>¡Buenos días! Soy Sofía, tu asistente virtual. ¿En qué trámite del
        Municipio de Girardota te puedo ayudar hoy?</sofia>
      </example>
      <example>
        <user>Muchas gracias por la ayuda</user>
        <sofia>¡Con mucho gusto! Quedo a tu disposición si necesitas hacer alguna
        otra consulta.</sofia>
      </example>
      <example>
        <user>¿Eres humana?</user>
        <sofia>Soy una inteligencia artificial diseñada para ayudarte con tus
        trámites municipales.</sofia>
      </example>
    </no_usar_herramienta>

    <sí_usar_herramienta label="Casos donde SÍ se usa la herramienta: buscar_informacion_tramites">
      <example>
        <user>¿Qué documentos necesito para el certificado de estratificación?</user>
        <action>Invocar buscar_informacion_tramites</action>
      </example>
      <example>
        <user>¿En qué bancos puedo pagar el impuesto de delineación urbana?</user>
        <action>Invocar buscar_informacion_tramites</action>
      </example>
      <example>
        <user>¿Cómo registro un perro potencialmente peligroso?</user>
        <action>Invocar buscar_informacion_tramites</action>
      </example>
      <example>
        <user>¿Cuánto se demora la licencia para intervenir el espacio público?</user>
        <action>Invocar buscar_informacion_tramites</action>
      </example>
    </sí_usar_herramienta>
  </tool_usage_guide>
</system_prompt> """

# ============================================
# 5. CREAR TABLA DE HISTORIAL
# ============================================
def crear_tabla_historial():
    try:
        sync_connection = psycopg.connect(DATABASE_URL)
        PostgresChatMessageHistory.create_tables(sync_connection, "chat_history_usuarios_consultas")
        sync_connection.close()
    except Exception as e:
        print(f"⚠️ Nota sobre tabla: {e}")

crear_tabla_historial()

# ============================================
# 6. HISTÓRICO DE CONVERSACIÓN
# ============================================
def get_session_history(session_id: str) -> PostgresChatMessageHistory:
    sync_connection = psycopg.connect(DATABASE_URL)
    return PostgresChatMessageHistory(
        "chat_history_usuarios_consultas",
        session_id,
        sync_connection=sync_connection
    )

# ============================================
# 7. FUNCIÓN DE CHAT CON AGENTE + TOOLS
# ============================================
def chat_con_agente(mensaje_usuario: str, session_id: str) -> str:
    """
    Ejecuta el agente con tools y memoria.
    El agente decide si usar herramientas o responder directamente.
    """
    # Obtener historial
    history = get_session_history(session_id)
    mensajes_previos = history.messages
    
    # Construir mensajes para el modelo
    messages = [{"role": "system", "content": system_prompt}]
    
    # Agregar historial
    for msg in mensajes_previos:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})
    
    # Agregar mensaje actual
    messages.append({"role": "user", "content": mensaje_usuario})
    
    # Invocar modelo con tools
    response = chat_con_tools.invoke(messages)
    
    # Procesar tool calls si existen
    if response.tool_calls:
        # Ejecutar cada tool
        tool_results = []
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            # Buscar y ejecutar la tool
            for t in tools:
                if t.name == tool_name:
                    result = t.invoke(tool_args)
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "result": result
                    })
                    break
        
        # Agregar respuesta del modelo con tool calls y resultados
        messages.append(response)
        for tr in tool_results:
            messages.append(ToolMessage(
                content=tr["result"],
                tool_call_id=tr["tool_call_id"]
            ))
        
        # Segunda llamada para obtener respuesta final
        final_response = chat_con_tools.invoke(messages)
        respuesta_final = final_response.content
    else:
        # Sin tool calls, respuesta directa
        respuesta_final = response.content
    
    # Guardar en historial
    history.add_user_message(mensaje_usuario)
    history.add_ai_message(respuesta_final)
    
    return respuesta_final


# ============================================
# 8. LOOP DE CONVERSACIÓN
# ============================================
def main():
    print("=" * 60)
    print("🤖 DataBot - Agente con TOOLS + MEMORIA PERSISTENTE")
    print("=" * 60)
    print("🔧 Tools disponibles:")
    for t in tools:
        print(f"   - {t.name}")
    print("💾 Historial: PostgreSQL")
    
    # Menú de sesión
    print("\nOpciones de sesión:")
    print("  1. Nueva conversación")
    print("  2. Continuar sesión existente (pegar UUID)")
    
    opcion = input("\nElige (1/2): ").strip()
    
    if opcion == "2":
        session_id = input("Pega el UUID de la sesión: ").strip()
        try:
            uuid.UUID(session_id)
        except ValueError:
            print("⚠️ UUID inválido. Creando nueva sesión...")
            session_id = str(uuid.uuid4())
    else:
        session_id = str(uuid.uuid4())
    
    print(f"\n📝 Session ID: {session_id}")
    print("   (Guarda este ID para continuar después)")
    print("✅ El agente DECIDE cuándo buscar en la base de conocimiento")
    print("Escribe 'salir' para volver al menú.\n")
    
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