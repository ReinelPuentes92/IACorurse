"""
Módulo de Tools para Agentes IA
Contiene todas las herramientas disponibles para los agentes.
"""

from Practice.Agents.Agent_Fundamentals.tools.Base_de_conocimiento import buscar_informacion_tramites
from Practice.Agents.Agent_Fundamentals.tools.Busqueda_internet import buscar_internet
from Practice.Agents.Agent_Fundamentals.tools.Hora_y_fecha import obtener_fecha_hora

# Lista de todas las tools disponibles
__all__ = [
    "buscar_informacion_tramites",
    "buscar_internet",
    "obtener_fecha_hora",
]
