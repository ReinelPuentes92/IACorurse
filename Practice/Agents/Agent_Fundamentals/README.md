# DP-LangChain-Agents-Design-2026

Diseño de Agentes IA con **LangChain v1.0** — Módulo 2, Sesiones 1 y 2.

Programa AI Engineer · **DataPath**
Autor: Ing. Kevin Inofuente Colque

---

## ¿De qué trata este repo?

Cuatro agentes que se construyen **uno encima del otro**. Cada uno agrega una capacidad
nueva, para que veas exactamente qué problema resuelve cada pieza de la arquitectura:

| Agente | Qué agrega | Qué aprendes |
|:--|:--|:--|
| **A** | Nada — solo modelo + prompt | El problema: un LLM **no recuerda** nada |
| **B** | Memoria persistente en PostgreSQL | Cómo darle historial real a un agente |
| **C** | Base de conocimiento (RAG como tool) | Cómo el LLM **decide** cuándo consultar tus datos |
| **D** | Internet + fecha/hora | Cómo orquestar **varias tools** en un solo agente |

Y al final, `main_chatwoot_ia_off.py` conecta el agente D a un canal real de atención
(**Chatwoot**), con control humano sobre cuándo responde la IA.

---

## Instalación

### 1. Clona el repositorio

```bash
git clone https://github.com/KevinInoCol/DP-LangChain-Agents-Design-2026.git
cd DP-LangChain-Agents-Design-2026
```

### 2. Crea y activa el entorno virtual (Python 3.11)

```bash
conda create --name LangChain-Agente-Basico python=3.11
conda activate LangChain-Agente-Basico
```

### 3. Instala las dependencias

```bash
pip install -r requirements.txt
```

### 4. Configura tus credenciales

```bash
cp .env.example .env
```

Abre el `.env` y rellena **solo** lo que necesita el agente que vas a correr:

| Variable | Para qué sirve | La necesitan |
|:--|:--|:--|
| `OPENAI_API_KEY` | Modelo de chat y embeddings | A, B, C, D |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` | Histórico en PostgreSQL | B, C, D |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Base de conocimiento (RAG) | C, D |
| `TAVILY_API_KEY` | Búsqueda en internet | D |
| `AGENT_TIMEZONE` | Zona horaria del agente | D |
| `CHATWOOT_*` | Integración con Chatwoot | `main_chatwoot_ia_off.py` |

> ⚠️ El `.env` **nunca** se sube a GitHub — ya está en el `.gitignore`.
> El archivo que sí se versiona es `.env.example`, que no lleva credenciales reales.

---

## Cómo ejecutarlo

### Opción recomendada: el orquestador

```bash
python main.py
```

Te muestra un menú y eliges el agente con una letra:

```
  A. Agente Básico (sin memoria)
  B. Agente con Histórico de Conversación (PostgreSQL)
  C. Agente con Base de Conocimiento (RAG + Tool)
  D. Agente Completo (RAG + Internet + Memoria)
```

### Opción directa: cada agente por separado

```bash
python Agente-Basico-A/agente_basico.py
python Agente-Basico-B-con-Historico-de-Conversacion/agente_basico_conversation_history.py
python Agente-Basico-C-con-Base-de-Conocimiento-SUPABASE/agente_basico_hc_base_de_conocimiento.py
python Agente-Basico-D-con-BC-HC-ToolExterna/agente_basico_hc_bc_toolexterna.py
```

En cualquiera, escribe `salir` para terminar.

---

## Los agentes, uno por uno

### Agente A — Sin memoria

El punto de partida. Una chain LCEL mínima: `prompt | modelo`.

```python
chain = prompt | chat
```

**El experimento:** dile tu nombre, y en el mensaje siguiente pregúntale cuál es.
No lo sabe. Cada invocación arranca de cero — ese es justamente el problema
que resuelve el Agente B.

---

### Agente B — Memoria persistente en PostgreSQL

Agrega `RunnableWithMessageHistory` sobre la misma chain, con
`PostgresChatMessageHistory` guardando los mensajes en Supabase.

- El prompt incorpora un `MessagesPlaceholder(variable_name="history")`
- Cada conversación se identifica con un **`session_id` (UUID)**
- Tabla: `chat_history_usuarios_consultas` (se crea sola en el primer arranque)

**El experimento:** al iniciar, elige *"1. Nueva conversación"* y **copia el UUID** que
imprime. Sal del programa, vuelve a entrar, elige *"2. Continuar sesión existente"*,
pega ese UUID — y verás que sí recuerda lo que hablaron.

---

### Agente C — Base de conocimiento (RAG como tool)

Aquí llega el cambio conceptual importante: el RAG **no** se inyecta a la fuerza en
cada mensaje. Se expone como una **tool** y es el LLM quien decide si la necesita.

```python
chat_con_tools = chat.bind_tools([buscar_informacion_tramites])
```

- **Persona:** *Sofía*, asistente de trámites del Municipio de Girardota (Colombia)
- **Vectores:** Supabase, tabla `documents_langchain_asistente_de_informacion`
- **Embeddings:** `text-embedding-ada-002`
- **Búsqueda:** similitud coseno calculada en Python con `numpy`, top-5 resultados

**El experimento:** salúdalo con un *"hola"* — responde directo, sin tocar la base.
Pregúntale por los requisitos de un trámite — verás en consola el `🔍 Buscando:`
de la tool. Esa decisión la tomó el modelo, no tu código.

---

### Agente D — Agente completo, tres tools

El agente final: RAG + internet + tiempo, todo con memoria persistente.

| Tool | Qué hace |
|:--|:--|
| `buscar_informacion_tramites` | Consulta la base de conocimiento (RAG) |
| `buscar_internet` | Busca información actual con **Tavily** (5 resultados) |
| `obtener_fecha_hora` | Fecha y hora por zona IANA, solo con `zoneinfo` (sin API externa) |

Además, en **cada turno** se le inyecta la fecha y hora actual al system prompt, para
que entienda bien "hoy", "ahora" o "esta semana". Tabla de historial: `chat_history`.

**El experimento:** hazle una pregunta que necesite **dos tools a la vez** — por ejemplo,
comparar algo de la base de conocimiento con información actual de internet. Verás
encadenarse el `🔍` y el `🌐` en consola.

---

## Integración con Chatwoot

`main_chatwoot_ia_off.py` levanta un servidor **FastAPI** que conecta el agente D a
Chatwoot como canal de atención real.

```bash
python main_chatwoot_ia_off.py
# Servidor en http://0.0.0.0:8000
```

| Endpoint | Método | Para qué |
|:--|:--|:--|
| `/webhook` | POST | Recibe los mensajes que envía Chatwoot |
| `/test` | POST | Probar el agente sin depender de Chatwoot |
| `/health` | GET | Verificar que la config está completa |
| `/` | GET | Estado general del servicio |

**El control humano:** una etiqueta (*label*) en la conversación de Chatwoot decide
si el bot contesta o no. Configúrala con `CHATWOOT_BOT_LABEL`:

- `atiende-ia` → el agente responde automáticamente
- `ia-off` → el agente calla y atiende una persona

Así un asesor humano puede tomar el control de una conversación en cualquier momento.

> Para desarrollo local necesitarás exponer el puerto 8000 a internet (por ejemplo con
> `ngrok`) y registrar esa URL pública como webhook en Chatwoot.

---

## Estructura del proyecto

```
.
├── main.py                          # Orquestador: menú para elegir agente
├── main_chatwoot_ia_off.py          # Servidor FastAPI ↔ Chatwoot
│
├── Agente-Basico-A/                 # Sin memoria
├── Agente-Basico-B-con-Historico-de-Conversacion/
├── Agente-Basico-C-con-Base-de-Conocimiento-SUPABASE/
├── Agente-Basico-D-con-BC-HC-ToolExterna/
│
├── tools/                           # Tools reutilizables por los agentes
│   ├── Base_de_conocimiento.py      # RAG sobre Supabase
│   ├── Busqueda_internet.py         # Tavily
│   └── Hora_y_fecha.py              # Fecha/hora por zona horaria
│
├── .env.example                     # Plantilla de credenciales
├── requirements.txt
└── Comandos.md                      # Comandos rápidos de setup
```

**Cómo agregar tu propia tool:** crea el archivo en `tools/`, decórala con `@tool`,
expórtala en `tools/__init__.py` y agrégala a la lista `tools = [...]` del agente.
El resto lo maneja `bind_tools`.

---

## Stack

- **LangChain v1.0** (`langchain`, `langchain-openai`, `langchain-community`)
- **Modelo:** GPT-4.1 vía `init_chat_model`, `temperature=0.7`
- **Memoria:** `langchain-postgres` + `psycopg` (v3) sobre PostgreSQL / Supabase
- **RAG:** Supabase + `OpenAIEmbeddings` + `numpy`
- **Tools:** `langchain-tavily`
- **API:** FastAPI + Uvicorn

---

## Problemas frecuentes

| Síntoma | Causa y solución |
|:--|:--|
| `❌ Faltan variables de base de datos en .env` | Faltan `DB_USER`, `DB_PASSWORD` o `DB_HOST`. Cópialos del *Transaction pooler* de Supabase. |
| `❌ Faltan variables de Supabase en .env` | Usa la key **`service_role`**, no la `anon`. |
| `❌ Falta TAVILY_API_KEY en .env` | Regístrate gratis en [tavily.com](https://tavily.com). |
| El agente no recuerda nada | Estás en el Agente A — es su comportamiento esperado. Usa B, C o D. |
| No retoma una conversación anterior | Debes pegar el **mismo UUID** de sesión; si es inválido, se crea una sesión nueva. |
| `⚠️ Chatwoot no configurado` | Faltan `CHATWOOT_BASE_URL`, `CHATWOOT_ACCOUNT_ID` o `CHATWOOT_API_ACCESS_TOKEN`. |

---

## Licencia y uso

Material educativo del programa **AI Engineer** de DataPath.
Úsalo, modifícalo y adáptalo para tus propios proyectos.
