# Plantillas copiables

Esqueletos mínimos de cada archivo del blueprint. Copiá y adaptá el dominio;
no cambies la forma.

---

## `requirements.txt`

```txt
# LangChain 1.x
langchain>=1.0,<2.0
langchain-openai>=1.0,<2.0
langchain-community>=0.4,<1.0
langchain-text-splitters>=1.0,<2.0

# Vector store (RAG)
langchain-qdrant>=0.2,<1.0
qdrant-client~=1.19.0
pypdf>=4.0,<7.0

# Memoria
langchain-postgres
psycopg[binary]

# Tools
langchain-tavily
gspread
google-auth

# Canal
fastapi
uvicorn
requests

# Config
python-dotenv>=1.0,<2.0
pyyaml
```

---

## `.gitignore` (bloque de secretos)

```gitignore
# Secretos y credenciales
.env
.env.*
# La plantilla SÍ se versiona: solo lleva placeholders, ningún valor real
!.env.example
credentials/
*.json
!requirements*.json

# Python
__pycache__/
*.py[cod]
.venv/
venv/
```

---

## `vector_store.py` — fuente única

```python
"""
Configuración del vector store. FUENTE ÚNICA del par (embedding model, colección).

La ingesta (RAG-.../rag.py) y la consulta (tools/Base_de_conocimiento.py)
importan de acá. Nunca escribas el modelo de embeddings en otro archivo:
si la ingesta y la consulta usan modelos distintos, la búsqueda devuelve
vacío sin lanzar ningún error.
"""

import os

from dotenv import load_dotenv, find_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

load_dotenv(find_dotenv())

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "tenant_id_<negocio>")

MODELO_EMBEDDING = "text-embedding-3-small"

if not QDRANT_URL:
    raise ValueError("❌ Falta QDRANT_URL en .env")


def get_embedding_model() -> OpenAIEmbeddings:
    """Modelo de embeddings. El mismo para ingestar y para consultar."""
    return OpenAIEmbeddings(model=MODELO_EMBEDDING)


def get_client() -> QdrantClient:
    """Cliente de Qdrant.

    port=None es obligatorio: sin eso qdrant-client le pega :6333 a la URL por
    su cuenta y muere con "Connection refused", porque el proxy del VPS publica
    Qdrant en el 443 de https.
    """
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, port=None)


def get_vectorstore() -> QdrantVectorStore:
    """Vector store listo para consultar."""
    return QdrantVectorStore(
        client=get_client(),
        collection_name=COLLECTION_NAME,
        embedding=get_embedding_model(),
    )
```

---

## `model_config/model_config.yaml`

```yaml
# ============================================
# Configuración del modelo LLM del agente
# ============================================
# Config pura: sin código y sin prompt (el prompt vive en prompt/prompt.yaml).
# Solo claves que el código realmente lee.

llm:
  provider: openai
  model: gpt-4.1
  temperature: 0.7

agent:
  # Zona horaria por defecto. La variable AGENT_TIMEZONE del .env tiene prioridad.
  timezone: America/Lima
```

---

## `prompt/prompt.yaml` — esqueleto

Formato completo en la skill `agent-prompt-yaml-format`. Una sola convención de
tags por archivo, todos cerrados.

```yaml
name: <negocio>-system-prompt
version: 1.0.0
description: >
  Qué agente es, para qué negocio, con qué fuentes de datos y sobre qué canal opera.
language: es
author: tu@email.com
created_at: YYYY-MM-DD
tags: [rag, tool-calling, <rubro>]

variables:
  - fecha_hora_actual

system_prompt: |
  <Identidad>
  Quién es, de qué empresa, dónde opera.
  </Identidad>

  <Objetivo_Principal>
  El resultado que persigue cada conversación.
  </Objetivo_Principal>

  <Contexto_Temporal>
  FECHA Y HORA ACTUAL (referencia para este turno): {fecha_hora_actual}
  </Contexto_Temporal>

  <Herramientas_Disponibles>
  Nombre EXACTO de cada tool + para qué sirve.
  </Herramientas_Disponibles>

  <Fuentes_De_Datos>
  Qué tool es autoritativa para qué tema. Una sola por tema.
  </Fuentes_De_Datos>

  <Identificacion_Del_Cliente>
  Qué datos necesita antes de consultar, y qué hacer si no matchea.
  </Identificacion_Del_Cliente>

  <Reglas_De_Uso_De_Tools>
  Pregunta típica → tool. Cuándo NO usar ninguna.
  </Reglas_De_Uso_De_Tools>

  <Formato_De_Respuesta>
  Idioma, longitud, moneda, agrupaciones, emojis o no.
  </Formato_De_Respuesta>

  <Escalamiento>
  Cuándo derivar a un humano sin intentar resolverlo.
  </Escalamiento>

  <IMPORTANTE>
  Los 4-6 guardrails críticos, repetidos al final.
  </IMPORTANTE>
```

---

## `agent.py` — orquestador

```python
"""
Agente <negocio>: RAG + tools + histórico.
- Config del modelo: model_config/model_config.yaml
- System prompt: prompt/prompt.yaml
"""

import os
import sys
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from tools import <tool_a>, <tool_b>
from conversation_history import crear_tabla_historial, get_session_history

# ============================================
# 1. CARGA DE CONFIGURACIÓN (YAML)
# ============================================
# Rutas con __file__: sobreviven a que arranquen el script desde otro directorio.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_CONFIG_PATH = os.path.join(BASE_DIR, "model_config", "model_config.yaml")
PROMPT_PATH = os.path.join(BASE_DIR, "prompt", "prompt.yaml")


def _cargar_yaml(ruta: str) -> dict:
    """Lee un archivo YAML de configuración y lo devuelve como dict."""
    with open(ruta, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


model_config = _cargar_yaml(MODEL_CONFIG_PATH)
prompt_config = _cargar_yaml(PROMPT_PATH)

# ============================================
# 2. TOOLS
# ============================================
tools = [<tool_a>, <tool_b>]

# ============================================
# 3. MODELO CON TOOLS
# ============================================
_llm_cfg = model_config["llm"]
chat = init_chat_model(
    _llm_cfg["model"],
    model_provider=_llm_cfg["provider"],
    temperature=_llm_cfg["temperature"],
)
chat_con_tools = chat.bind_tools(tools)

# ============================================
# 4. PROMPT + CONTEXTO TEMPORAL
# ============================================
AGENT_TIMEZONE = os.getenv(
    "AGENT_TIMEZONE",
    model_config.get("agent", {}).get("timezone", "America/Lima"),
)
SYSTEM_PROMPT_TEMPLATE = prompt_config["system_prompt"]


def _contexto_fecha_hora() -> str:
    """Fecha y hora actual para inyectar en el system prompt (cada turno)."""
    try:
        tz = ZoneInfo(AGENT_TIMEZONE)
    except Exception:
        tz = ZoneInfo("America/Lima")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S") + f" (zona {AGENT_TIMEZONE})"


def _render_system_prompt() -> str:
    """Renderiza el prompt reemplazando los placeholders declarados en variables."""
    # .replace() y no .format(): el prompt lleva llaves literales.
    return SYSTEM_PROMPT_TEMPLATE.replace("{fecha_hora_actual}", _contexto_fecha_hora())


crear_tabla_historial()


# ============================================
# 5. CHAT CON TOOLS
# ============================================
def chat_con_agente(mensaje_usuario: str, session_id: str) -> str:
    """Ejecuta el agente con tools y memoria."""
    history = get_session_history(session_id)

    messages = [{"role": "system", "content": _render_system_prompt()}]
    for msg in history.messages:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})
    messages.append({"role": "user", "content": mensaje_usuario})

    response = chat_con_tools.invoke(messages)

    if response.tool_calls:
        messages.append(response)
        for tool_call in response.tool_calls:
            for t in tools:
                if t.name == tool_call["name"]:
                    messages.append(ToolMessage(
                        content=t.invoke(tool_call["args"]),
                        tool_call_id=tool_call["id"],
                    ))
                    break
        respuesta_final = chat_con_tools.invoke(messages).content
    else:
        respuesta_final = response.content

    history.add_user_message(mensaje_usuario)
    history.add_ai_message(respuesta_final)
    return respuesta_final
```

---

## `tools/<Fuente>.py` — forma de una tool

```python
"""
Tool: <qué hace>.

Autor: ...
"""

import os

from dotenv import load_dotenv, find_dotenv
from langchain_core.tools import tool

load_dotenv(find_dotenv())

# ============================================
# CONFIGURACIÓN
# ============================================
MI_VARIABLE = os.getenv("MI_VARIABLE")

if not MI_VARIABLE:
    raise ValueError("❌ Falta MI_VARIABLE en .env")


# ============================================
# TOOL EXPORTABLE
# ============================================
@tool
def mi_accion(parametro: str) -> str:
    """
    <Qué devuelve, en una línea.>

    Úsala cuando el usuario pregunte:
    - "<pregunta real 1>"
    - "<pregunta real 2>"

    Args:
        parametro: qué es y con qué formato. Ejemplos: "...", "...".
    """
    # El docstring es el contrato real con el modelo: si miente, el ruteo falla.
    try:
        resultado = ...
        if not resultado:
            # Decilo explícito para que el modelo no rellene el hueco.
            return "No encontré <X>. Pedile al usuario que confirme <Y>."
        return resultado
    except Exception as e:
        return f"Error al consultar <fuente>: {e}"
```

Y en `tools/__init__.py`:

```python
"""Tools disponibles para el agente."""

from tools.<Fuente> import mi_accion

__all__ = ["mi_accion"]
```

---

## `conversation_history/postgres_chat_history.py`

```python
"""
Histórico de conversación persistente en PostgreSQL.

Requeridas en .env: DB_USER, DB_PASSWORD, DB_HOST
Opcionales: DB_PORT (5432), DB_NAME (postgres), DB_CHAT_TABLE (chat_history)
"""

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv, find_dotenv
from langchain_postgres import PostgresChatMessageHistory
import psycopg

load_dotenv(find_dotenv())

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

if not all([DB_USER, DB_PASSWORD, DB_HOST]):
    raise ValueError("❌ Faltan DB_USER, DB_PASSWORD o DB_HOST en .env")

# quote_plus: passwords con caracteres especiales rompen la URL sin esto.
DATABASE_URL = (
    f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
TABLE_NAME = os.getenv("DB_CHAT_TABLE", "chat_history")
```

En el canal, el `session_id` se deriva del ID de conversación de forma
determinista para que el cliente retome su hilo:

```python
session_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"<canal>-{conversation_id}"))
```

---

## `RAG-.../rag.py` — ingesta

Estructura en 4 pasos, con la config arriba y la validación **antes** de leer el
PDF (para no gastar llamadas de embeddings y morir después por un nombre mal
puesto):

```python
RUTA_PDF = "Base_de_Conocimiento/<archivo>.pdf"
TAMANO_CHUNK = 500
SOLAPAMIENTO_CHUNK = 200

from vector_store import get_client, get_embedding_model, COLLECTION_NAME

def verificar_configuracion() -> None:
    if not os.getenv("QDRANT_URL"):
        raise ValueError("Falta QDRANT_URL en .env")
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("Falta OPENAI_API_KEY en .env")
    if not os.path.exists(RUTA_PDF):
        raise FileNotFoundError(f"No se encontró el PDF: {RUTA_PDF}")
    validacion = validar_qdrant(COLLECTION_NAME)
    if not validacion.ok:
        raise ValueError(f"Nombre de colección inválido: {validacion.motivos}")

if __name__ == "__main__":
    verificar_configuracion()

    documentos = PyPDFLoader(RUTA_PDF).load()
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=TAMANO_CHUNK, chunk_overlap=SOLAPAMIENTO_CHUNK
    ).split_documents(documents=documentos)

    embedding_model = get_embedding_model()
    # El tamaño lo dicta el modelo, no se escribe a mano.
    vector_size = len(embedding_model.embed_query("texto de muestra"))

    client = get_client()
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    QdrantVectorStore(
        client=client, collection_name=COLLECTION_NAME, embedding=embedding_model
    ).add_documents(documents=chunks)

    print(f"✓ {client.count(COLLECTION_NAME).count} vectores en '{COLLECTION_NAME}'")
```

**Ojo:** `RUTA_PDF` es relativa al cwd porque este script se corre desde su propia
carpeta. Si lo movés, cambiala a `__file__`.

---

## `.env.example` — encabezado

```bash
# ============================================
# Plantilla de variables de entorno
# Copiar a .env y rellenar:  cp .env.example .env
# El .env real NUNCA se sube al repo (está en .gitignore).
# ============================================

# ============================================
# OpenAI (LLM + embeddings)  [REQUERIDA]
# El modelo se configura en model_config/model_config.yaml, no acá.
# ============================================
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Cada bloque: para qué sirve, `[REQUERIDA]`/`[OPCIONAL]`, y qué módulo lo lee.
Las opcionales van comentadas con su default documentado.
