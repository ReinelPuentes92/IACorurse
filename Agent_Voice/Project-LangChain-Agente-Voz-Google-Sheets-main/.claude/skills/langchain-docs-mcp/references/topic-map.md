# Mapa de temas → consultas al MCP `docs-langchain`

Usa esta tabla cuando no sepas qué buscar. La columna de la derecha son *queries* para
`mcp__docs-langchain__search_docs_by_lang_chain`; las rutas son puntos de entrada típicos para
`query_docs_filesystem_docs_by_lang_chain` (verifica siempre con `search` o `ls` — no las asumas).

## Agentes

| Necesito… | Query | Entrada típica |
|---|---|---|
| Crear un agente | `create_agent python` | `/oss/python/langchain/agents` |
| Añadir tools | `tool decorator python`, `tool calling` | `/oss/python/langchain/tools` |
| System prompt / persona | `create_agent system_prompt` | `/oss/python/langchain/agents` |
| Interceptar pasos del agente | `agent middleware` | `/oss/python/langchain/middleware` |
| Salida estructurada | `structured output response_format` | `/oss/python/langchain/structured-output` |
| Multi-agente / supervisor | `multi agent supervisor langgraph` | `/oss/python/langgraph/*` |

## Modelos

| Necesito… | Query |
|---|---|
| Instanciar el LLM | `init_chat_model` |
| Elegir proveedor | `chat models openai` |
| Parámetros (temperature, max_tokens) | `chat model parameters` |
| Streaming de tokens | `stream messages agent` |

## Memoria / persistencia

| Necesito… | Query |
|---|---|
| Que recuerde la conversación | `checkpointer persistence` |
| Sesiones separadas | `thread_id configurable` |
| Guardar en Postgres | `postgres checkpointer` |
| Memoria de largo plazo | `store long term memory` |
| Recortar historial | `trim messages`, `summarization middleware` |

> Ojo: en v1 **no** existe `ConversationBufferMemory` ni `PostgresChatMessageHistory` como camino
> recomendado. La memoria vive en el estado del grafo + checkpointer.

## RAG / retrievers

| Necesito… | Query |
|---|---|
| Pipeline RAG | `rag tutorial python` |
| Cargar documentos | `document loaders` |
| Chunking | `text splitters` |
| Embeddings | `embedding models` |
| Vector store (Chroma/Pinecone/PGVector) | `<nombre> vector store integration` |
| Retriever como tool | `retriever tool agent` |

## Prompts / LCEL

| Necesito… | Query |
|---|---|
| Plantilla de prompt | `prompt templates` |
| Encadenar runnables | `LCEL runnable sequence` |
| Paralelizar pasos | `RunnableParallel` |

## Observabilidad

| Necesito… | Query |
|---|---|
| Trazas | `langsmith tracing setup` |
| Evaluación | `langsmith evaluation` |

## Migración v0 → v1 (señales de código viejo)

| Código v0 que veas | Query de reemplazo |
|---|---|
| `AgentExecutor`, `initialize_agent` | `create_agent migration` |
| `create_react_agent` de `langgraph.prebuilt` | `create_agent python` |
| `LLMChain`, `ConversationChain` | `LCEL migration chains` |
| `RetrievalQA` | `rag tutorial python` |
| `from langchain.memory import ...` | `checkpointer persistence` |
| `from langchain.prompts import ...` | `langchain_core.prompts` |
| Bucle manual sobre `response.tool_calls` | `create_agent tool calling` |

Si el reemplazo no aparece en la doc actual, probablemente quedó en **`langchain-classic`**:
dilo al usuario y ofrece la alternativa v1 en vez de instalar el paquete legacy por defecto.
