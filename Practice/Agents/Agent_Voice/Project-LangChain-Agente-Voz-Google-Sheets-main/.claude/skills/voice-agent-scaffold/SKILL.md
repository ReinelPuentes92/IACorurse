---
name: voice-agent-scaffold
description: Estructura canónica para proyectos de agentes de voz (LangChain v1 + Whisper STT + TTS) — conversation_history/ con checkpointer PostgreSQL, prompt/prompt.yaml con tags, una tool por módulo dentro de tools/, y data/ solo para datasets batch. Use when scaffolding a new voice agent project, adding a tool or an API endpoint to one, deciding where a new file belongs, wiring conversation memory or the system prompt, or refactoring an existing voice/chat agent into this layout.
---

# Scaffold de proyectos de agente de voz

Estructura de referencia tomada de **Proyecto-Agente-de-Voz-con-LangChain-y-Whisper**. Todo proyecto de voz nuevo la respeta salvo que el usuario diga explícitamente lo contrario.

Antes de escribir código LangChain, aplica también la skill **`langchain-docs-mcp`** (consultar la doc oficial vía MCP). Para el contenido del prompt, la skill global **`agent-prompt-yaml-format`**.

## Layout canónico

```
<proyecto>/
├── agent.py                     # orquestador: prompt + LLM + tools + memoria. NO sabe de audio
├── talking_llm.py               # capa de voz: hotkey → grabación → Whisper → agent → TTS
├── prompt/
│   └── prompt.yaml              # system prompt: metadata + bloque system_prompt con TAGS
├── tools/
│   ├── __init__.py              # re-exporta cada tool
│   ├── <tool_uno>.py            # 1 módulo = 1 tool
│   └── <tool_dos>.py
├── conversation_history/
│   ├── __init__.py              # re-exporta la API pública
│   └── chat_history.py          # checkpointer PostgreSQL + log plano
├── data/                        # OPCIONAL — solo datasets batch locales (CSV/parquet)
├── .env                         # nunca al repo
├── .env.example                 # documenta TODAS las variables
├── requirements.txt
└── README.md
```

Plantillas de cada archivo: [references/templates.md](references/templates.md).

## Reglas de estructura (no negociables)

### 1. `conversation_history/` — siempre paquete, nunca archivo suelto

- El histórico vive en **`conversation_history/chat_history.py`**. Nunca `chat_history.py` en la raíz ni `memory.py`.
- `conversation_history/__init__.py` re-exporta la API pública para que el resto importe `from conversation_history import get_checkpointer, nueva_sesion`.
- Dos piezas con roles distintos, ambas obligatorias:
  | Pieza | Qué hace | Tablas |
  |---|---|---|
  | **Checkpointer** (`PostgresSaver` de LangGraph) | Que el agente **recuerde** entre turnos, releído por `thread_id` | `checkpoints*` (binario) |
  | **Log plano** (`registrar_turno`) | **Auditar** con SQL: una fila por mensaje | `<algo>_chat_log` |
- La sesión es un **UUID** que se usa como `thread_id`. Funciones: `nueva_sesion()`, `validar_sesion()`.
- **Degradación explícita**: si faltan variables o la conexión falla → `InMemorySaver` + aviso visible en consola. El agente no se cae, pero se nota. `historial_persistente()` reporta el modo.
- Singleton + `ExitStack` + `atexit` para cerrar la conexión.

### 2. Variables de entorno de PostgreSQL — mismos nombres siempre

```
DB_USER, DB_PASSWORD, DB_HOST, DB_PORT (default 5432), DB_NAME (default postgres)
```

- Se arma `DATABASE_URL` con `quote_plus(DB_PASSWORD)` (escapa `@ / : #`).
- Si falta `DB_USER`, `DB_PASSWORD` o `DB_HOST` → `DATABASE_URL = None` → modo RAM.
- **Supabase: puerto `5432` (session pooler), nunca `6543`.** El modo transaction no soporta prepared statements y revienta el checkpointer con `DuplicatePreparedStatement`. Deja este comentario en el código y en `.env.example`.
- `.env.example` documenta cada variable con su para-qué; `.env` va en `.gitignore`.
- Opcional: `<PREFIJO>_SESSION_ID` para retomar una conversación anterior.

### 3. `prompt/prompt.yaml` — YAML con metadata + tags

Un único archivo YAML con dos partes:

```yaml
name: <slug>-system-prompt
version: 1.0.0
description: >
  ...
language: es
author: <email>
created_at: <YYYY-MM-DD>
tags: [voz, tool-calling, ...]

variables:            # placeholders que agent.py inyecta en runtime
  - num_filas

system_prompt: |
  <Identidad> ... </Identidad>
  <Personalidad> ... </Personalidad>
  <Objetivo_Principal> ... </Objetivo_Principal>
  <Herramientas_Disponibles> ... </Herramientas_Disponibles>
  <Reglas_De_Uso_De_Tools> ... </Reglas_De_Uso_De_Tools>
  <Formato_De_Respuesta> ... </Formato_De_Respuesta>
  <Seguridad> ... </Seguridad>
  <IMPORTANTE> ... </IMPORTANTE>
```

- **El cuerpo del prompt SIEMPRE va en tags estilo XML.** Nada de prosa suelta ni listas markdown sin tag contenedor. Los tags concretos se adaptan al negocio; `<Identidad>`, `<Objetivo_Principal>`, `<Herramientas_Disponibles>`, `<Formato_De_Respuesta>`, `<Seguridad>` e `<IMPORTANTE>` son el mínimo.
- En proyectos de **voz**, `<Formato_De_Respuesta>` siempre prohíbe Markdown, tablas y símbolos: el texto se escucha, no se lee.
- Los placeholders se declaran en `variables:` y se sustituyen en `load_system_prompt()`. Nunca hardcodees en el YAML datos que se pueden calcular en runtime.
- Un prompt por agente. Si hay varios agentes: `prompt/<agente>.yaml`.

### 4. `tools/` — una tool por módulo, siempre

- **Un módulo Python = exactamente una tool.** Dos `@tool` en el mismo archivo es un error de estructura, aunque sean parecidas.
- Nombre del archivo = nombre de la tool (`query_dataframe.py` → `query_dataframe`).
- Patrón de dos capas dentro del módulo:
  1. Una **función imperativa** pura (`ejecutar_consulta(df, code)`) — testeable sin LLM ni micrófono.
  2. Una **factory** (`get_<tool>_tool(deps)`) que devuelve la `@tool`, cerrando las dependencias en clausura para que el LLM solo vea los parámetros que debe rellenar.
- El docstring de la `@tool` es lo que lee el LLM: describe qué hace, qué formato espera y da un ejemplo.
- `tools/__init__.py` re-exporta la función imperativa y la factory de cada módulo.
- `agent.py` las ensambla: `tools=[get_a_tool(...), get_b_tool(...)]`.

### 5. `data/` — opcional, solo batch local

| Origen de los datos | Dónde va |
|---|---|
| CSV / parquet / snapshot local que se carga entero en memoria | `data/` + una tool que consulta el DataFrame |
| Base de datos **en producción** | **Tool** por caso de uso, nada en `data/` |
| **API REST** | **Una tool por endpoint**, un módulo por tool |
| **MCP** | Tool que envuelve la llamada al MCP; nada en `data/` |

Si no hay dataset batch local, **no crees `data/`**. No copies una BD de producción a un CSV para "simplificar".

Ejemplo de API con 3 endpoints:

```
tools/
├── buscar_cliente.py       # GET /clientes/search
├── crear_reserva.py        # POST /reservas
└── consultar_estado.py     # GET /reservas/{id}
```

Nunca un `api_client.py` con las tres tools dentro. El HTTP compartido (base URL, headers, auth) va en un helper aparte —`tools/_http.py` o `clients/`— que **no** define tools.

### 6. `agent.py` — orquestador sin audio

Expone `build_agent()` y no importa nada de micrófono ni de TTS, para poder probar el agente por texto:

```python
agent = build_agent()
config = {"configurable": {"thread_id": nueva_sesion()}}
agent.invoke({"messages": [{"role": "user", "content": "..."}]}, config)
```

Ensambla: carga de datos (si aplica) → `load_system_prompt()` → `create_agent(init_chat_model(model), tools=[...], system_prompt=..., checkpointer=get_checkpointer())`.

### 7. Capa de voz — separada

La clase de voz (`TalkingLLM` o equivalente) solo hace: hotkey → grabar → WAV → Whisper (STT) → `agent.invoke` → TTS → reproducir → `registrar_turno()`. Si toca lógica de negocio, está mal ubicada.

## Checklist al crear un proyecto nuevo

1. `agent.py`, `prompt/prompt.yaml`, `tools/`, `conversation_history/` — los cuatro, siempre.
2. `data/` solo si hay dataset batch local.
3. `.env.example` con `OPENAI_API_KEY` + las cinco `DB_*` + comentario del puerto 5432.
4. `.gitignore` con `.env`, `__pycache__/`, `*.wav`.
5. Una tool = un módulo. Un endpoint = una tool.
6. Prompt en YAML con tags, y `<Formato_De_Respuesta>` sin Markdown.
7. `README.md` con el diagrama de flujo, la tabla de módulos y el SQL para leer `*_chat_log`.

## Al modificar un proyecto existente

- ¿Nueva capacidad del agente? → módulo nuevo en `tools/`, registrar en `__init__.py` y en `agent.py`, y documentarla en `<Herramientas_Disponibles>` del prompt. Las tres cosas.
- ¿Cambia el comportamiento/tono/reglas? → se edita `prompt/prompt.yaml`, **no** se hardcodea en Python.
- ¿Aparece un `chat_history.py` suelto, dos tools en un módulo o instrucciones de prompt dentro de `.py`? → señálalo y ofrece moverlo a la estructura canónica.
