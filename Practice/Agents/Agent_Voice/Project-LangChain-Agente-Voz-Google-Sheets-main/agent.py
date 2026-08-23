"""Orquestador del agente: ensambla DataFrame + system prompt + LLM + tools + memoria.

No sabe nada de audio, así que se puede probar sin micrófono:

    from agent import build_agent
    from conversation_history import nueva_sesion

    agent = build_agent()
    config = {"configurable": {"thread_id": nueva_sesion()}}

    r = agent.invoke({"messages": [
        {"role": "user", "content": "¿Cuál es el alquiler promedio en Pinheiros?"}
    ]}, config)
    print(r["messages"][-1].content)

    #segundo turno: gracias al checkpointer, recuerda de qué barrio hablabas
    r = agent.invoke({"messages": [
        {"role": "user", "content": "¿Y cuántas de esas tienen piscina?"}
    ]}, config)
    print(r["messages"][-1].content)
"""

from pathlib import Path

import pandas as pd
import yaml
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from conversation_history import get_checkpointer
from tools.query_dataframe import get_query_dataframe_tool

BASE_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BASE_DIR / "prompt" / "prompt.yaml"
CSV_PATH = BASE_DIR / "data" / "df_rent.csv"

DEFAULT_MODEL = "openai:gpt-4.1-mini"


def load_dataframe() -> pd.DataFrame:
    """Carga el dataset de alquileres de São Paulo.

    index_col=0 descarta la columna de índice sin nombre del CSV, para que no
    se cuele como "Unnamed: 0" en el system prompt.
    """
    return pd.read_csv(CSV_PATH, index_col=0)


def load_system_prompt(df: pd.DataFrame) -> str:
    """Carga el system prompt desde prompt/prompt.yaml e inyecta los datos
    reales del DataFrame en los placeholders declarados en `variables`."""
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        prompt_cfg = yaml.safe_load(f)

    system_prompt = prompt_cfg["system_prompt"]

    reemplazos = {
        "{num_filas}": f"{len(df):,}",
        "{num_columnas}": str(len(df.columns)),
        "{lista_columnas}": ", ".join(df.columns.tolist()),
        "{muestra_datos}": df.head(3).to_string(index=False),
    }
    for placeholder, valor in reemplazos.items():
        system_prompt = system_prompt.replace(placeholder, valor)

    return system_prompt


def build_agent(model: str = DEFAULT_MODEL, con_memoria: bool = True):
    """Construye el agente listo para invocar.

    Con `con_memoria=True` el agente recuerda la conversación: hay que pasarle
    un `thread_id` en cada invoke, si no LangGraph no sabe qué hilo releer.

        config = {"configurable": {"thread_id": session_id}}
        agent.invoke({"messages": [...]}, config)
    """
    df = load_dataframe()

    return create_agent(
        init_chat_model(model),
        #Tools que le permiten al agente consultar el DataFrame de alquileres con pandas.
        tools=[get_query_dataframe_tool(df)],        
        system_prompt=load_system_prompt(df),
        #Historico de conversacion en posrgress.
        checkpointer=get_checkpointer() if con_memoria else None,
    )
