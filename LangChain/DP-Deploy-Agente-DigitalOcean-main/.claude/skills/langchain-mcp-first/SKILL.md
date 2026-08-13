---
name: langchain-mcp-first
description: Consulta los MCP oficiales de LangChain (docs-langchain para guías y conceptos, reference-langchain para firmas de API exactas) ANTES de escribir o modificar código de LangChain, LangGraph o LangSmith. Úsala cuando el trabajo toque chains, agents, retrievers, vectorstores, tools, memoria, checkpointers, graphs o pipelines RAG; cuando el archivo importe langchain, langchain_core, langchain_community, langchain_openai, langchain_text_splitters, langgraph o langsmith; y cuando el usuario pida crear, refactorizar, migrar o debuggear código LangChain o pregunte "cómo hago X con LangChain".
---

# LangChain MCP First

En este repo **no se escribe código de LangChain desde la memoria del modelo**. La API cambia
rápido y `langchain-community` está en *sunset*, así que las suposiciones envejecen mal.
Antes de tocar código, se consultan los MCP oficiales.

> Esta skill reemplaza a la global `langchain-docs-first` dentro de este proyecto: cubre lo
> mismo y además el MCP de referencia de API. Si ambas aparecen listadas, usa esta.

## Los dos MCP y para qué sirve cada uno

Son complementarios, no intercambiables. Usar el equivocado es la causa más común de
código que "parece bien" pero no compila.

| MCP | Sirve para | No sirve para |
|:--|:--|:--|
| **`docs-langchain`**<br>`docs.langchain.com/mcp` | Conceptos, guías how-to, tutoriales, patrones canónicos, decidir *qué* usar | Firmas exactas, lista completa de parámetros |
| **`reference-langchain`**<br>`reference.langchain.com/mcp` | Firma exacta de clases y métodos, nombres y tipos de parámetros, valores de retorno, atributos | Entender *por qué* o *cuándo* usar algo |

**La regla de oro:** `docs-langchain` te dice **qué** usar; `reference-langchain` te dice
**cómo se llama exactamente**. Para cualquier cambio no trivial, consulta los dos.

Los nombres de las tools se exponen como `mcp__docs-langchain__*` y
`mcp__reference-langchain__*`. Si no aparecen en la lista de tools disponibles, **no
inventes sus nombres**: usa `ToolSearch` para descubrirlas, y si no existen, avisa al
usuario (probablemente añadió el MCP después de arrancar la sesión y hace falta reiniciar).

## Workflow

### 1. Descompón la petición en temas concretos

| Petición | Temas a consultar |
|:--|:--|
| "Un agente con tools" | `create_agent` / `create_react_agent`, `bind_tools`, `@tool` |
| "RAG con Supabase/Pinecone" | `vectorstores`, `retrievers`, la integración concreta |
| "Memoria conversacional" | `checkpointers`, `MessagesState`, `*ChatMessageHistory` |
| "Migrar esto a la API nueva" | El símbolo legacy + su reemplazo actual |

### 2. Consulta `docs-langchain` para el patrón

Busca la página oficial del tema y lee el snippet canónico. Prioriza:
1. La sección **How-to** o **Tutorial**.
2. Páginas sin tag de *legacy* o *deprecated*.
3. **LangGraph** para cualquier cosa de agentes — es la vía recomendada actual.

### 3. Verifica las firmas en `reference-langchain`

Antes de escribir la llamada, confirma contra el reference:
- El **import exacto** (el módulo se mueve entre paquetes con frecuencia).
- El **nombre y tipo de cada parámetro** que vas a pasar.
- Si es `sync` o `async`, y qué devuelve.

Esto es obligatorio cuando pasas más de dos argumentos a un constructor, o cuando el
parámetro no aparece literal en el snippet de las docs.

### 4. Di al usuario qué vas a usar, antes de escribir

Tres a cinco líneas: qué clase/función, de qué página viene, y por qué esa y no la
alternativa. Si hay una decisión de diseño, es aquí donde se discute — no después.

### 5. Escribe alineado a la fuente

Usa los imports literales de la doc. Replica el patrón canónico antes de improvisar.
Cuando una decisión no sea obvia, deja la referencia en un comentario corto:

```python
# Pattern from: docs.langchain.com/oss/python/langgraph/agents
agent = create_react_agent(model, tools)
```

## Reglas duras

- **Nunca escribas código LangChain sin consultar primero.** Aunque "sepas" la API.
- **Si el MCP no responde o no cubre el tema, detente y avísalo.** No improvises: cae a
  leer el código instalado en `site-packages`, que es autoritativo, y **di que lo hiciste**.
- **No mezcles APIs viejas y nuevas** en el mismo archivo.
- **Verifica Python vs JS/TS** antes de consultar: las docs cubren ambos.
- **Un warning de deprecación no es ruido.** Si aparece, consúltalo y reporta el reemplazo.

## Contexto de este repo

Trampas ya encontradas aquí, para no repetir el diagnóstico:

- **`langchain-community` está en sunset.** `PyPDFLoader` y `SupabaseVectorStore` vienen de
  ahí y emiten `DeprecationWarning`. Antes de tocar esos imports, consulta el reemplazo
  standalone en los MCP.
- **`SupabaseVectorStore.from_documents()` no envía la columna `id`.** La tabla de Postgres
  necesita `default gen_random_uuid()`, o falla con el error `23502`. El SQL correcto vive
  en `RAG-Classic-con-LangChain/snippet para Supabase.md`.
- **Los nombres de tabla y de función RPC deben coincidir** entre `rag.py`,
  `tools/Base_de_conocimiento.py` y el snippet SQL. Ya se desincronizaron una vez.
- **El modelo por defecto del curso es GPT-4.1**, y los embeddings son
  `text-embedding-ada-002` (1536 dimensiones — la tabla depende de ese número).

## Material adicional de la skill global

`~/.claude/skills/langchain-docs-first/references/` tiene tres documentos que siguen
siendo válidos y que esta skill no duplica:

- `langchain-vs-langgraph.md` — para decidir entre ambos frameworks.
- `migration-checklist.md` — para migrar código legacy (`AgentExecutor`, `RetrievalQA`…).
- `common-topics.md` — para mapear una petición vaga a temas de doc concretos.
