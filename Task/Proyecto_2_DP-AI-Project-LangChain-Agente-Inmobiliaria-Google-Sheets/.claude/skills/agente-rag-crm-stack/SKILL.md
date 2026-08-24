---
name: agente-rag-crm-stack
description: Blueprint completo del stack y la modularización que usamos para agentes conversacionales de producción — LangChain 1.x + GPT-4.1, RAG sobre Qdrant, memoria en PostgreSQL, tools de datos externos (Google Sheets/API), y canal de mensajería (Chatwoot/FastAPI), con config y prompt fuera del código en YAML. Use when scaffolding a new conversational agent from scratch, adding a piece to an existing one, deciding where a new file belongs, choosing which library to use, or when the user mentions "otro agente", "nuevo agente", "replicar la estructura", "empezar de cero", "armar el proyecto". Apply this layout and stack by default unless the user explicitly says otherwise.
---

# Stack y estructura de nuestros agentes conversacionales

Blueprint probado en producción. Cubre **un solo agente** que combina LLM +
tool calling + RAG + memoria persistente, expuesto por CLI y por un canal de
mensajería. No es multi-agente: esa es la forma que resuelve la mayoría de los
casos reales (atención y consulta sobre datos propios, con acciones sobre
sistemas externos).

Si vas a arrancar un agente nuevo, **esta es la estructura de partida**. No
inventes una distinta salvo que el usuario lo pida.

---

## 1. Stack por defecto

| Capa | Elección | Notas |
|---|---|---|
| Framework | **LangChain 1.x** (`langchain>=1.0,<2.0`) | API v1. Nunca escribir idioms v0 — ver skill `langchain-v1-idioms` |
| LLM | **GPT-4.1** vía `init_chat_model` | Default del usuario — ver skill `default-llm-model` |
| Embeddings | **`text-embedding-3-small`** | Un solo modelo en todo el proyecto. Ver regla 2 |
| Vector store | **Qdrant** (`langchain-qdrant` + `qdrant-client`) | Remoto en VPS. Colecciones con prefijo `tenant_id_` |
| Memoria | **PostgreSQL** (`langchain-postgres` + `psycopg[binary]`) | `PostgresChatMessageHistory` por `session_id` |
| Búsqueda web | **Tavily** (`langchain-tavily`) | Solo para lo ajeno al dominio del negocio |
| Datos de negocio | **Google Sheets** (`gspread` + `google-auth`) o la API que toque | Scope de **solo lectura** salvo que se pida escribir |
| Canal | **Chatwoot** vía **FastAPI** + `uvicorn` | Webhook `POST /webhook` |
| Config | **YAML** (`pyyaml`) + **`.env`** (`python-dotenv`) | Ver regla 1 |
| Loader PDF | `pypdf` / `PyPDFLoader` | Para la ingesta del RAG |

Antes de escribir código de LangChain, consultá la documentación oficial —
skill `langchain-docs-first`. Las APIs de v1 cambiaron respecto de los
tutoriales que circulan.

---

## 2. Layout

```
<project-root>/
├── agent.py                       ← orquestador: ensambla LLM + tools + prompt + memoria
├── main_<canal>.py                ← entrypoint del canal (webhook FastAPI). Ej: main_chatwoot.py
│
├── model_config/
│   └── model_config.yaml          ← proveedor, modelo, temperatura, y config del agente
├── prompt/
│   └── prompt.yaml                ← system prompt (YAML + tags XML) con metadata versionada
│
├── tools/                         ← una tool por archivo
│   ├── __init__.py                    exporta todas + __all__
│   ├── Base_de_conocimiento.py        RAG como tool (consulta)
│   ├── Busqueda_internet.py           Tavily
│   ├── Hora_y_fecha.py                contexto temporal
│   └── <Fuente_De_Datos>.py           Google Sheets / API del negocio
│
├── conversation_history/          ← persistencia de la conversación
│   ├── __init__.py
│   └── postgres_chat_history.py       PostgresChatMessageHistory por session_id
│
├── RAG-Clasico-con-Qdrant/        ← pipeline de INGESTA (reindexado)
│   ├── rag.py                         loader → splitter → embeddings → Qdrant
│   ├── validacion_nombre_tenant_id.py validador de la convención de colecciones
│   ├── requirements.txt
│   └── Base_de_Conocimiento/          PDFs fuente
│
├── vector_store.py                ← FUENTE ÚNICA del par (embedding model, colección)
├── credentials/                   ← JSON de service accounts. NO se versiona
├── .env                           ← secretos. NO se versiona
├── .env.example                   ← plantilla. SÍ se versiona
├── .gitignore
├── requirements.txt
└── README.md
```

### Dónde va cada cosa

| Si cambio… | Toco |
|---|---|
| Proveedor de LLM, modelo, temperatura | `model_config/model_config.yaml` |
| Persona, tono o reglas del agente | `prompt/prompt.yaml` |
| Backend de memoria (Postgres → Redis) | `conversation_history/` |
| Vector DB, embedding model, nombre de colección | `vector_store.py` |
| Fuente documental o estrategia de chunking | `RAG-Clasico-con-Qdrant/rag.py` |
| Agrego o modifico una acción del agente | `tools/<una>.py` |
| API del canal (Chatwoot, WhatsApp…) | `main_<canal>.py` o `<canal>/` si crece |
| Cómo se ensamblan las piezas | `agent.py` |

Si la respuesta natural es "agent.py" para cualquier otra cosa, **algo está mal**.
`agent.py` solo cambia cuando cambia la orquestación.

---

## 3. Las reglas que evitan los bugs caros

Cada una viene de un bug real. No son estilo.

### Regla 1 — La configuración vive en YAML, nunca hardcodeada

El modelo en `model_config/model_config.yaml`, el prompt en `prompt/prompt.yaml`.
`agent.py` los carga y punto.

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_CONFIG_PATH = os.path.join(BASE_DIR, "model_config", "model_config.yaml")
PROMPT_PATH = os.path.join(BASE_DIR, "prompt", "prompt.yaml")
```

**Las rutas se arman con `__file__`, nunca relativas al cwd.** Así el proyecto
sobrevive a que lo arranquen desde otro directorio o a que renombren el módulo.

**No dejes claves muertas en el YAML.** Si `model_config.yaml` declara algo que
ningún módulo lee, es una mentira que alguien va a creer.

### Regla 2 — `vector_store.py` es la fuente única de (embedding model, colección)

La ingesta (`RAG-.../rag.py`) y la consulta (`tools/Base_de_conocimiento.py`)
importan de ahí. **Nunca** se escribe el nombre del modelo de embeddings en dos
archivos.

Sin esto aparece el bug clásico: indexás con `text-embedding-3-small` y consultás
con `text-embedding-ada-002`, o indexás en una colección y consultás otra. El
agente responde *"no encontré información"* sobre documentos que sí están
indexados, **sin lanzar ningún error**. Es el bug más caro de diagnosticar de un
RAG porque no falla: miente.

Regla derivada: si cambiás el embedding model, **hay que reindexar**. No es
retrocompatible.

### Regla 3 — El docstring de la tool es el contrato real con el modelo

El prompt es contexto; el docstring es lo que el LLM lee para decidir si llama a
la tool. Si tras un cambio de dominio el docstring dice "cuota de mantenimiento"
y el prompt dice "boleto de alquiler", **gana el docstring** y el ruteo se rompe.

Al repuntar un agente a otro negocio, actualizá los dos.

### Regla 4 — La lista de tools nunca se duplica en strings

Se declara una vez y todo lo demás la deriva:

```python
tools = [buscar_datapath, buscar_internet, obtener_fecha_hora, ...]
...
"tools": [t.name for t in tools]      # ✅
"tools": ["buscar_datapath", ...]     # ❌ se desactualiza y nadie se entera
```

### Regla 5 — El prompt NO duplica la base de conocimiento

Tarifas, políticas, porcentajes de multa, precios y direcciones viven en el RAG y
se recuperan con la tool. El prompt solo dice **cuándo** consultarla. Duplicarlos
crea dos fuentes de verdad que se desincronizan, y el prompt gana silenciosamente.

Formato obligatorio del prompt: YAML con metadata + bloque `system_prompt` con
tags estilo XML — ver skill `agent-prompt-yaml-format`.

### Regla 6 — Los nombres describen función, no implementación

`agent.py`, no `agente_hc_bc_toolexterna_pinecone.py`. El día que cambies Pinecone
por Qdrant el nombre miente, y renombrar después obliga a perseguir imports por
todo el repo.

### Regla 7 — `.env.example` se versiona; `.env` y `credentials/` no

Trampa real: un `.gitignore` con `.env.*` **también excluye `.env.example`**.
Hace falta la excepción explícita:

```gitignore
.env
.env.*
!.env.example        # ← sin esta línea, la plantilla nunca llega al repo
credentials/
*.json
!requirements*.json
```

El `.env.example` debe listar **todas** las variables que el código lee, marcadas
`[REQUERIDA]` u `[OPCIONAL]`, diciendo qué módulo lee cada una, y con placeholders
— jamás un valor real.

### Regla 8 — Recursos pesados se inicializan una vez

El vector store, el cliente de Qdrant y el LLM se crean a nivel de módulo, no por
mensaje. Cargarlos en cada turno mata el tiempo de respuesta.

---

## 4. Contratos por carpeta

### `model_config/model_config.yaml`
Config pura, sin código y sin prompt.

```yaml
llm:
  provider: openai
  model: gpt-4.1
  temperature: 0.7

agent:
  timezone: America/Lima     # el .env tiene prioridad sobre esto
```

### `prompt/prompt.yaml`
Prompt puro en formato YAML + tags XML, con `name`, `version`, `description`,
`language`, `variables`. Los placeholders (`{fecha_hora_actual}`) se inyectan en
`agent.py` con `.replace()`, nunca con `str.format()` — el prompt lleva llaves
literales y `format()` reventaría con `KeyError`.

Subí la `version` en todo cambio de dominio: es lo único que te dice qué prompt
está corriendo en producción.

### `tools/`
Un archivo por tool. Cada una:
- Docstring que explica **cuándo** usarla, con ejemplos de preguntas reales.
- Devuelve **string** legible por el modelo, no un objeto.
- Captura sus excepciones y devuelve un mensaje útil: si revienta, el agente debe
  poder decírselo al usuario, no morirse.
- Nunca inventa: si no encuentra el dato, lo dice explícitamente para que el
  modelo no rellene el hueco.

### `conversation_history/`
`PostgresChatMessageHistory` por `session_id`. En canales de mensajería el
`session_id` se deriva de forma determinista del ID de la conversación:

```python
uuid.uuid5(uuid.NAMESPACE_DNS, f"chatwoot-{conversation_id}")
```

Así el mismo cliente retoma su hilo sin guardar un mapeo aparte.

### `RAG-Clasico-con-Qdrant/`
Solo **ingesta**, ejecutable directo (`python rag.py`). La config de retrieval
(`top_k`) vive en la tool de consulta, no acá.

Valida el nombre de la colección **antes** de cargar el PDF y de gastar llamadas
de embeddings — `validacion_nombre_tenant_id.py`. Convención multi-tenant:
`tenant_id_<negocio>` en Qdrant (guiones bajos), `tenant-id-<negocio>` en Pinecone
(guiones, máx. 45 chars). Ver skill `rag-tenant-collection-naming`.

El tamaño del vector se deriva del modelo, no se escribe a mano:

```python
vector_size = len(embedding_model.embed_query("texto de muestra"))
```

### Entrypoint del canal
Separa tres cosas que tienden a mezclarse:
- **Cliente HTTP del canal** (enviar mensaje, actualizar etiquetas)
- **Reglas de negocio** (cuándo derivar a humano)
- **Rutas FastAPI** (`/webhook`, `/test`, `/health`)

Si el archivo pasa de ~250 líneas, sacá el cliente a `<canal>/client.py`.

---

## 5. Orden dentro de cada `.py`

Docstring → imports → `load_dotenv(find_dotenv())` → variables de entorno →
constantes en mayúsculas → funciones. Ver skill `python-module-structure`.

La carga de los YAML va **después de todos los imports**, no en medio.

---

## 6. Checklist para un agente nuevo

1. Crear el árbol de la sección 2 y un `.venv`.
2. `requirements.txt` con el stack de la sección 1.
3. `.env.example` completo + `.gitignore` con la excepción de la regla 7.
4. `vector_store.py` con el par (embedding, colección) — **antes** de escribir la
   ingesta o la tool de RAG.
5. `RAG-.../rag.py` e indexar. Verificar que la colección quedó con vectores.
6. `tools/` una por una, probándolas sueltas antes de conectarlas.
7. `model_config/model_config.yaml` y `prompt/prompt.yaml`.
8. `agent.py` que ensambla todo, con CLI mínimo para probar.
9. Entrypoint del canal.
10. `README.md` con estructura, puesta en marcha y uso.

---

## 7. Validaciones antes de dar por cerrado

```bash
# El prompt parsea, los tags cierran y las tools existen de verdad
python -c "
import re, yaml, pathlib
p = yaml.safe_load(open('prompt/prompt.yaml'))
sp = p['system_prompt']
ab = re.findall(r'^[ \t]*<([A-Za-z_]+)>[ \t]*$', sp, re.M)
ce = re.findall(r'^[ \t]*</([A-Za-z_]+)>[ \t]*$', sp, re.M)
assert not set(ab) ^ set(ce), f'tags sin cerrar: {set(ab) ^ set(ce)}'
src = ''.join(f.read_text() for f in pathlib.Path('tools').glob('*.py'))
reg = set(re.findall(r'@tool\s*(?:\([^)]*\)\s*)?\ndef (\w+)', src))
men = set(re.findall(r'\b(buscar_\w+|consultar_\w+|obtener_\w+)\b', sp))
assert not men - reg, f'tools en el prompt que no existen: {men - reg}'
print('OK', p['name'], 'v'+str(p['version']), '|', len(reg), 'tools')
"

# Ningún secreto quedaría versionado
git check-ignore -q .env credentials && echo "OK secretos ignorados"
git check-ignore -q .env.example && echo "MAL: .env.example está siendo ignorado"
```

Y a ojo: que el embedding model de la ingesta y el de la consulta sean el mismo.

---

## Skills relacionadas

- `agent-project-structure` — la convención general de la que esto es la
  instancia concreta de este equipo.
- `agent-prompt-yaml-format` — formato obligatorio de `prompt/prompt.yaml`.
- `rag-tenant-collection-naming` — convención `tenant_id_` y su validador.
- `python-module-structure` — orden de bloques dentro de cada `.py`.
- `langchain-v1-idioms` y `langchain-docs-first` — no escribir código v0.
- `default-llm-model` — GPT-4.1 por defecto.
- `agent-domain-swap` — repuntar un agente ya hecho a otro negocio.

Plantillas copiables de cada archivo: `references/plantillas.md`.
