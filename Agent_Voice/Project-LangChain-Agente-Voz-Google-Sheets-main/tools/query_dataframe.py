"""Tool que le permite al agente consultar el DataFrame de alquileres con pandas."""

import pandas as pd
from langchain.tools import tool


def ejecutar_consulta(df: pd.DataFrame, code: str) -> str:
    """Ejecuta código pandas sobre `df` y devuelve el resultado como texto.

    Versión imperativa: se puede testear sin el LLM ni el micrófono.
        >>> ejecutar_consulta(df, "result = df['Price'].mean()")
    """
    try:
        local_vars = {"df": df, "pd": pd}
        exec(code, {"pd": pd}, local_vars)
        result = local_vars.get("result", "Código ejecutado correctamente")
        return str(result)
    except Exception as e:
        return f"Error al ejecutar el código: {str(e)}"


def get_query_dataframe_tool(df: pd.DataFrame):
    """Factory: cierra el DataFrame en clausura, así el LLM solo ve el parámetro `code`."""

    @tool
    def query_dataframe(code: str) -> str:
        """Ejecuta código Python/pandas sobre el dataframe 'df' y retorna el resultado.
        El dataframe ya está disponible como variable 'df'. Asigna el resultado final
        a una variable llamada 'result'. Ejemplo: result = df.head()"""
        return ejecutar_consulta(df, code)

    return query_dataframe
