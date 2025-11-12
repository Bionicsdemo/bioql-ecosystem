#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Demo: Ejecutar en IBM Torino con Quillow + BioQL (v2 - con timeout correcto)
=============================================================================

IMPORTANTE: Este script tiene timeout de 1 hora (3600s) para hardware real.

Autor: SpectrixRD
Fecha: 2025-10-26
"""

import importlib
import sys

# Forzar recarga de módulos para asegurar que usa el código más reciente
if "quillow.backends.bioql_backend" in sys.modules:
    del sys.modules["quillow.backends.bioql_backend"]
if "quillow.core.surface_code" in sys.modules:
    del sys.modules["quillow.core.surface_code"]
if "quillow.core.noise_models" in sys.modules:
    del sys.modules["quillow.core.noise_models"]

sys.path.insert(0, "/Users/heinzjungbluth/Desktop/Quillow")

import time

from quillow.backends.bioql_backend import BioQLBackend, BioQLConfig
from quillow.core import RotatedSurfaceCode
from quillow.core.noise_models import DepolarizingNoise
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# API key de BioQL
API_KEY = "__BIOQL_REDACTED__"


def print_header():
    """Imprimir encabezado."""
    console.print("\n")
    console.print(
        Panel.fit(
            "[bold cyan]🚀 QUILLOW + IBM TORINO (v2)[/bold cyan]\n\n"
            "Ejecución en hardware cuántico real con protección QEC\n"
            "[dim]Timeout: 1 hora (3600s)[/dim]",
            border_style="cyan",
        )
    )
    console.print()


def check_bioql_connection():
    """Verificar conexión a BioQL."""
    console.print("[bold]📡 Paso 1: Verificando conexión a BioQL[/bold]")
    console.print()

    config = BioQLConfig(api_key=API_KEY, base_url="https://api.bioql.bio")

    # Verificar timeout
    console.print(
        f"   ⏱️  Timeout configurado: {config.timeout} segundos ({config.timeout/60:.0f} minutos)"
    )

    if config.timeout < 3600:
        console.print("   [red]⚠️  ADVERTENCIA: Timeout demasiado corto para hardware real![/red]")
        console.print(f"   [red]   Actual: {config.timeout}s, Recomendado: 3600s[/red]")
        return None

    backend = BioQLBackend(config, qec_distance=5)

    # Validar API key
    console.print("   🔑 Validando API key...", end=" ")
    if not backend.validate_api_key():
        console.print("[red]❌ API key inválida[/red]")
        return None
    console.print("[green]✅ Válida[/green]")

    # Verificar balance
    console.print("   💰 Verificando balance...", end=" ")
    quota = backend.check_quota()

    if "error" in quota:
        console.print(f"[red]❌ Error: {quota['error']}[/red]")
        return None

    balance = quota.get("balance", 0)
    console.print(f"[green]${balance:.2f}[/green]")

    console.print()
    console.print(
        Panel(
            f"[green]✅ Conexión verificada[/green]\n\n"
            f"Balance: ${balance:,.2f}\n"
            f"Tier: {quota.get('tier', 'N/A')}\n"
            f"Shots usados: {quota.get('shots_used', 0):,}\n"
            f"Timeout: {config.timeout}s ({config.timeout/60:.0f} min)",
            border_style="green",
        )
    )
    console.print()

    return backend


def build_qec_circuit():
    """Construir circuito con protección QEC."""
    console.print("[bold]🔧 Paso 2: Construyendo circuito con QEC d=5[/bold]")
    console.print()

    # Crear surface code
    console.print("   • Creando surface code d=5...", end=" ")
    surface_code = RotatedSurfaceCode(distance=5, rounds=5)
    console.print("[green]✅[/green]")

    console.print(f"   • Qubits de datos: {surface_code.layout.n_data}")
    console.print(f"   • Qubits de síndrome: {surface_code.layout.n_syndrome}")
    console.print(f"   • Total qubits: {surface_code.layout.total_qubits}")

    # Construir circuito
    console.print("   • Generando circuito Stim...", end=" ")
    noise_model = DepolarizingNoise(error_rate=0.001)
    circuit = surface_code.build_stim_circuit(noise_model=noise_model)
    console.print("[green]✅[/green]")

    console.print(f"   • Detectores: {circuit.num_detectors}")
    console.print(f"   • Observables: {circuit.num_observables}")
    console.print()

    return circuit


def execute_on_ibm_torino(backend, circuit):
    """Ejecutar en IBM Torino."""
    console.print("[bold]🚀 Paso 3: Ejecutando en IBM Torino[/bold]")
    console.print()

    shots = 2048

    console.print(f"   [yellow]Backend:[/yellow] IBM Torino (133 qubits)")
    console.print(f"   [yellow]Shots:[/yellow] {shots:,}")
    console.print(f"   [yellow]QEC Distance:[/yellow] d=5")
    console.print(f"   [yellow]Costo estimado:[/yellow] ~${shots * 0.001 * 1.5:.2f}")
    console.print(
        f"   [yellow]Timeout:[/yellow] {backend.config.timeout}s ({backend.config.timeout/60:.0f} min)"
    )
    console.print()

    # Advertencia
    console.print(
        Panel(
            "[bold yellow]⚠️  ADVERTENCIA: Ejecución en hardware real[/bold yellow]\n\n"
            "Este trabajo se ejecutará en IBM Torino, un procesador cuántico real.\n\n"
            "• El trabajo puede tardar 5-30 minutos en completarse\n"
            "• Se consumirán créditos de tu cuenta BioQL\n"
            "• El script esperará pacientemente (timeout: 1 hora)\n\n"
            "¿Deseas continuar?",
            border_style="yellow",
        )
    )
    console.print()

    response = input("   Escribe 'SI' para ejecutar en IBM Torino: ")
    if response.upper() != "SI":
        console.print("\n   [yellow]❌ Ejecución cancelada[/yellow]")
        return None

    console.print()
    console.print("   [cyan]📤 Enviando trabajo a IBM Torino...[/cyan]")
    console.print("   [dim]Esto puede tardar 5-30 minutos. Por favor espera...[/dim]")

    try:
        start_time = time.time()

        # Ejecutar con barra de progreso
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task(
                "⏳ Esperando respuesta de IBM Torino (puede tardar 5-30 min)...", total=None
            )

            result = backend.execute(circuit, shots=shots, backend="ibm_torino")

            progress.update(task, completed=True)

        elapsed = time.time() - start_time

        console.print()
        console.print(
            Panel(
                "[bold green]✅ Ejecución completada en IBM Torino[/bold green]\n\n"
                f"Tiempo transcurrido: {elapsed/60:.1f} minutos\n"
                f"Logical error rate: {result.metadata.get('logical_error_rate', 'N/A')}\n"
                f"QEC distance: {result.metadata.get('qec_distance', 'N/A')}\n"
                f"Backend: {result.backend_name}\n"
                f"Shots: {shots:,}",
                border_style="green",
            )
        )

        return result

    except Exception as e:
        elapsed = time.time() - start_time
        console.print()
        console.print(
            Panel(
                f"[bold red]❌ Error durante la ejecución[/bold red]\n\n"
                f"Error: {str(e)}\n"
                f"Tiempo transcurrido: {elapsed/60:.1f} minutos\n\n"
                "Posibles causas:\n"
                "• Cola de IBM muy larga (>1 hora)\n"
                "• Error de red\n"
                "• Servidor ocupado (reintentar más tarde)",
                border_style="red",
            )
        )
        return None


def main():
    """Función principal."""
    print_header()

    # Paso 1: Verificar conexión
    backend = check_bioql_connection()
    if backend is None:
        console.print("[red]❌ No se pudo conectar a BioQL. Abortando.[/red]")
        return

    # Paso 2: Construir circuito
    circuit = build_qec_circuit()

    # Paso 3: Ejecutar en IBM Torino
    result = execute_on_ibm_torino(backend, circuit)
    if result is None:
        console.print("\n[yellow]Demo terminada sin ejecución en hardware.[/yellow]")
        return

    # Resumen final
    console.print("\n" + "=" * 70)
    console.print(
        Panel.fit(
            "[bold green]✅ Demo de IBM Torino completada[/bold green]\n\n"
            "Has ejecutado exitosamente:\n"
            "  • Circuito QEC d=5 en IBM Torino (hardware real)\n\n"
            "[cyan]Quillow[/cyan] ha protegido tus qubits con surface codes,\n"
            "detectado errores, y corregido resultados automáticamente.\n\n"
            "[dim]pip install quillow[/dim]",
            border_style="green",
        )
    )
    console.print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Demo interrumpida por usuario[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback

        traceback.print_exc()
