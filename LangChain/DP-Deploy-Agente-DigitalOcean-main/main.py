"""
Main - Orquestador de Agentes IA
================================
Punto de entrada centralizado para ejecutar cualquier agente.

Autor: Ing. Kevin Inofuente Colque - DataPath
"""

import sys
import importlib.util
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Cargar variables de entorno
load_dotenv(find_dotenv())

# Directorio base
BASE_DIR = Path(__file__).parent


def cargar_modulo(nombre_carpeta: str, nombre_archivo: str):
    """Carga un módulo Python desde una carpeta con guiones en el nombre."""
    ruta = BASE_DIR / nombre_carpeta / nombre_archivo
    spec = importlib.util.spec_from_file_location(nombre_archivo.replace(".py", ""), ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def mostrar_menu():
    """Muestra el menú de agentes disponibles."""
    print("\n" + "=" * 60)
    print("🤖 ORQUESTADOR DE AGENTES IA - DataPath")
    print("=" * 60)
    print("\nAgentes disponibles:\n")
    print("  A. Agente Básico (sin memoria)")
    print("  B. Agente con Histórico de Conversación (PostgreSQL)")
    print("  C. Agente con Base de Conocimiento (RAG + Tool)")
    print("  D. Agente Completo (RAG + Internet + Memoria)")
    print("\n  0. Salir")
    print("-" * 60)


def main():
    """Función principal del orquestador."""
    while True:
        mostrar_menu()
        
        try:
            opcion = input("\nSelecciona un agente (A/B/C/D o 0): ").strip().upper()
            
            if opcion == "0":
                print("\n¡Hasta luego! 👋\n")
                sys.exit(0)
            
            elif opcion == "A":
                modulo = cargar_modulo("Agente-Basico-A", "agente_basico.py")
                modulo.main()
            
            elif opcion == "B":
                modulo = cargar_modulo(
                    "Agente-Basico-B-con-Historico-de-Conversacion", 
                    "agente_basico_conversation_history.py"
                )
                modulo.main()
            
            elif opcion == "C":
                modulo = cargar_modulo(
                    "Agente-Basico-C-con-Base-de-Conocimiento-SUPABASE", 
                    "agente_basico_hc_base_de_conocimiento.py"
                )
                modulo.main()
            
            elif opcion == "D":
                modulo = cargar_modulo(
                    "Agente-Basico-D-con-BC-HC-ToolExterna", 
                    "agente_basico_hc_bc_toolexterna.py"
                )
                modulo.main()
            
            else:
                print("\n❌ Opción no válida. Intenta de nuevo.\n")
        
        except KeyboardInterrupt:
            print("\n\n¡Hasta luego! 👋\n")
            sys.exit(0)
        
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
