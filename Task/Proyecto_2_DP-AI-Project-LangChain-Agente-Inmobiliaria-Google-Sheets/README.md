# Agente IA — Alpha State Assessoria Imobiliária

Agente conversacional construido con **LangChain 1.x** que atiende a los locatarios de
[Alpha State](https://www.google.com/maps/search/Rua+Tranquillo+Prosperi+383+Campinas)
(administradora de inmuebles en Barão Geraldo, Campinas/SP, Brasil).

Responde dos tipos de consulta:

| Consulta del locatario | Fuente de verdad |
|---|---|
| "¿Cuánto debo pagar este mes?", "¿qué incluye mi boleto?" | **Google Sheets** — la hoja de cálculo con los importes del mes |
| "¿Cuánto es la multa por atraso?", "¿qué documentos necesito?" | **RAG sobre Qdrant** — base de conocimiento con las políticas de Alpha State |

Además busca en internet (Tavily) para temas ajenos al contrato, y recuerda la
conversación entre mensajes gracias al histórico en PostgreSQL.

Se puede usar por **CLI** o exponerlo como **webhook de Chatwoot**.

---

## Estructura

```
.
├── agent.py                       # Orquestador: ensambla LLM + tools + prompt + memoria
├── main_chatwoot.py               # Entrypoint FastAPI: webhook de Chatwoot
│
├── model_config/
│   └── model_config.yaml          # Proveedor, modelo y temperatura del LLM
├── prompt/
│   └── prompt.yaml                # System prompt (YAML + tags XML) con metadata versionada
│
├── tools/                         # Una tool por archivo
│   ├── Google_Sheets.py           #   consultar_total_inquilino / consultar_desglose_inquilino
│   ├── Base_de_conocimiento.py    #   buscar_alpha_state  (RAG sobre Qdrant)
│   ├── Busqueda_internet.py       #   buscar_internet  (Tavily)
│   └── Hora_y_fecha.py            #   obtener_fecha_hora
│
├── conversation_history/          # Persistencia de la conversación por session_id
│   └── postgres_chat_history.py   #   PostgresChatMessageHistory sobre PostgreSQL
│
├── vector_store.py                # FUENTE ÚNICA del par (embedding model, colección)
│
├── RAG-Clasico-con-Qdrant/        # Pipeline de INGESTA (reindexado de la base de conocimiento)
│   ├── rag.py                     #   loader → splitter → embeddings → Qdrant
│   ├── validacion_nombre_tenant_id.py
│   └── Base_de_Conocimiento/      #   PDFs fuente
│
├── credentials/                   # JSON de la cuenta de servicio de Google (NO se versiona)
├── .env.example                   # Plantilla de variables de entorno
└── requirements.txt
```

La configuración vive en YAML, no en el código: para cambiar el modelo se toca
`model_config/model_config.yaml`, y para cambiar la persona del agente,
`prompt/prompt.yaml`. `agent.py` solo cambia cuando cambia la orquestación.

`vector_store.py` es la **fuente única** del par (modelo de embeddings, colección):
tanto la ingesta como la tool de consulta importan de ahí. Si cada uno definiera el
suyo y no coincidieran, la búsqueda devolvería vacío sin lanzar ningún error.

---

## Puesta en marcha

### 1. Dependencias

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Variables de entorno

```bash
cp .env.example .env
```

Rellena el `.env` con tus valores. Cada bloque está marcado como `[REQUERIDA]` u
`[OPCIONAL]` e indica qué módulo lo lee. Las imprescindibles para arrancar:

| Variable | Para qué |
|---|---|
| `OPENAI_API_KEY` | LLM y embeddings |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST` | Histórico de conversación en PostgreSQL |
| `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION` | Base de conocimiento (RAG) |
| `TAVILY_API_KEY` | Búsqueda en internet |
| `GOOGLE_SHEET_ID`, `GOOGLE_APPLICATION_CREDENTIALS` | Tool de Google Sheets |
| `CHATWOOT_*` | Solo si expones el webhook |

> El `.env` y la carpeta `credentials/` están en `.gitignore` y nunca deben subirse.

### 3. Credenciales de Google

Coloca el JSON de la cuenta de servicio en `credentials/` y comparte la hoja de
cálculo con el email de esa cuenta (permiso de **lectura** basta: el agente nunca
escribe en la hoja).

### 4. Indexar la base de conocimiento

```bash
cd RAG-Clasico-con-Qdrant
python rag.py
```

Carga el PDF, lo parte en chunks, genera los embeddings y los sube a la colección
de Qdrant. La colección sigue la convención multi-tenant con prefijo `tenant_id_`.

---

## Uso

### CLI

```bash
python agent.py
```

Permite iniciar una conversación nueva o retomar una existente pegando su UUID.
El histórico se guarda por `session_id`, así que la conversación sobrevive al cierre.

### Webhook de Chatwoot

```bash
python main_chatwoot.py        # levanta en http://0.0.0.0:8000
```

| Endpoint | Método | Para qué |
|---|---|---|
| `/webhook` | POST | Recibe los eventos de Chatwoot y responde en la conversación |
| `/test` | POST | Probar el agente sin Chatwoot: `{"message": "...", "session_id": "..."}` |
| `/health` | GET | Healthcheck |

Apunta el webhook de tu cuenta de Chatwoot a `https://<tu-dominio>/webhook`.
El agente ignora las conversaciones etiquetadas con `ia-off` y deriva a un asesor
humano cuando el locatario lo pide.

---

## Stack

- **LangChain 1.x** — orquestación y tool calling
- **OpenAI GPT-4.1** — modelo del agente
- **Qdrant** — vector store de la base de conocimiento
- **PostgreSQL** — histórico de conversación
- **Google Sheets API** — importes del boleto (solo lectura)
- **Tavily** — búsqueda en internet
- **FastAPI + Chatwoot** — canal de mensajería

---

Autor: **Ing. Kevin Inofuente Colque** — DataPath, Programa AI Engineer.
