# Agente de Voz con LangChain y Whisper

Agente conversacional por voz que permite hacer consultas en lenguaje natural sobre un dataset de propiedades en alquiler de São Paulo, Brasil. El usuario habla, Whisper transcribe, un agente LangChain v1 analiza el dataframe pandas y responde en voz alta usando OpenAI TTS.

## Arquitectura

```
Voz del usuario
      ↓
  Whisper (STT)
      ↓
  Agente LangChain v1  ←→  query_dataframe (tool pandas)
      ↓
  OpenAI TTS
      ↓
  Respuesta en audio
```

## Módulos

Progresión didáctica — cada parte añade una capa sobre la anterior:

| Archivo | Descripción |
|---|---|
| `talking_llm_part_1_save_audio.py` | Grabación de audio con hotkey y guardado en WAV |
| `talking_llm_part_2_llm_y_TTS.py` | Transcripción con Whisper + respuesta del LLM + TTS |
| `talking_llm_part_3_completo_con_agente.py` | Versión completa: orquesta voz (audio → Whisper → agente → TTS) |

La parte 3 delega el agente en módulos aparte, para poder probarlo sin micrófono:

| Archivo | Descripción |
|---|---|
| `agent.py` | Ensambla DataFrame + system prompt + LLM + tools + memoria |
| `tools/query_dataframe.py` | Tool que ejecuta pandas sobre el dataset |
| `prompt/prompt.yaml` | System prompt del agente (formato YAML + tags XML) |
| `conversation_history/chat_history.py` | Histórico de conversación en PostgreSQL |

### Histórico de conversación

Son dos piezas con funciones distintas:

| Pieza | Tabla | Para qué |
|---|---|---|
| **Checkpointer** (`PostgresSaver`) | `checkpoints*` | Que el agente **recuerde**. LangGraph relee el hilo por `thread_id` en cada turno. Formato binario. |
| **Log plano** | `voice_chat_log` | **Auditar** con SQL: una fila por mensaje, con rol y timestamp. |

Ambas se crean solas la primera vez que arranca el agente.

```sql
SELECT rol, contenido, creado_en
FROM voice_chat_log
WHERE session_id = '<uuid>'
ORDER BY creado_en;
```

Al arrancar, el programa imprime el **Session ID**. Para retomar esa conversación
en una ejecución posterior:

```bash
VOICE_SESSION_ID=<uuid> python talking_llm_part_3_completo_con_agente.py
```

También se puede leer desde la terminal:

```bash
python conversation_history/chat_history.py <session_id>
```

Si faltan las variables de BD o la conexión falla, el agente **no se cae**: cae a
memoria RAM con un aviso visible. Recuerda dentro de la sesión, pero no persiste.

### Probar el agente sin voz

```python
from agent import build_agent

agent = build_agent()
r = agent.invoke({"messages": [
    {"role": "user", "content": "¿Cuál es el alquiler promedio en Pinheiros?"}
]})
print(r["messages"][-1].content)
```

## Requisitos

- Python 3.9 / 3.10 / 3.11
- Clave de API de OpenAI

## Instalación

**1. Crear y activar el entorno virtual:**

```bash
conda create -n LangChain-Agente-Voz-Sheets python=3.11
conda activate LangChain-Agente-Voz-Sheets
```

**2. Instalar dependencias:**

```bash
pip install -r requirements.txt
```

**3. Configurar variables de entorno:**

Copia la plantilla y rellena los valores:

```bash
cp .env.example .env
```

El `.env` está en `.gitignore` y no debe subirse nunca. Contenido:

```
OPENAI_API_KEY=sk-...

# Histórico de conversación (PostgreSQL / Supabase)
DB_USER=postgres.xxxxxxxxxxxx
DB_PASSWORD=...
DB_HOST=aws-0-sa-east-1.pooler.supabase.com
DB_PORT=5432          # 5432 = session mode. NO uses 6543 (transaction mode)
DB_NAME=postgres
```

**4. Añadir el dataset:**

Coloca el archivo `df_rent.csv` en la carpeta `data/`.

## Uso

Ejecuta el agente completo:

```bash
python talking_llm_part_3_completo_con_agente.py
```

- Presiona `Cmd` para **comenzar** a grabar tu pregunta.
- Presiona `Cmd` de nuevo para **detener** la grabación.
- El agente procesará tu pregunta y responderá en voz alta.

## Dataset

El dataset `df_rent.csv` contiene propiedades en alquiler de São Paulo con las siguientes columnas:

| Columna | Descripción |
|---|---|
| `Price` | Precio mensual del alquiler (R$) |
| `Condo` | Valor del condominio mensual (R$) |
| `Size` | Tamaño en metros cuadrados |
| `Rooms` | Número de habitaciones |
| `Toilets` | Número de baños |
| `Suites` | Número de suites |
| `Parking` | Espacios de estacionamiento |
| `Elevator` | Tiene ascensor (1/0) |
| `Furnished` | Está amueblado (1/0) |
| `Swimming Pool` | Tiene piscina (1/0) |
| `District` | Barrio de São Paulo |
| `Latitude` | Coordenada geográfica |
| `Longitude` | Coordenada geográfica |

## Stack tecnológico

- **LangChain v1** — framework del agente (`create_agent`, `@tool`, `init_chat_model`)
- **LangGraph v1** — runtime del agente (usado internamente por LangChain v1)
- **OpenAI Whisper** — transcripción de voz a texto (STT)
- **OpenAI TTS** — síntesis de voz (modelo `tts-1`, voz `alloy`)
- **OpenAI GPT-4.1 mini** — modelo de lenguaje del agente
- **sounddevice / soundfile** — captura y reproducción de audio
- **pandas** — análisis del dataset
