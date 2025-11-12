#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Demo - Quantum Computing for Bioinformatics
Demostración completa de las capacidades de BioQL
"""

import time

from bioql import configure_debug_mode, get_info, quantum


def main():
    print("🧬⚛️ BioQL Demo - Quantum Computing for Bioinformatics ⚛️🧬")
    print("=" * 60)

    # Verificar instalación
    print("\n📋 Verificando instalación de BioQL...")
    info = get_info()
    print(f"✅ BioQL versión: {info['version']}")
    print(f"✅ Qiskit disponible: {info['qiskit_available']}")
    print(f"✅ Python: {info['python_version']}")

    # Habilitar modo debug
    configure_debug_mode(False)  # Mantener limpio para demo

    print("\n🔬 Iniciando demostraciones de biología cuántica...\n")

    # Demo 1: Plegamiento de proteínas
    print("1️⃣ PLEGAMIENTO DE PROTEÍNAS")
    print("-" * 30)

    start_time = time.time()
    result1 = quantum(
        """
        Simulate protein folding for a 4-amino acid peptide.
        Model alpha-helix vs beta-sheet conformations.
        Calculate energy landscape and stability.
    """,
        shots=1024,
    )

    if result1.success:
        print(f"✅ Simulación exitosa en {time.time() - start_time:.2f}s")
        print(f"   Conformaciones encontradas: {len(result1.counts)}")
        print(f"   Conformación más probable: {result1.most_likely_outcome}")
        print(f"   Total mediciones: {result1.total_shots}")

        # Mostrar primeras 3 conformaciones
        sorted_counts = sorted(result1.counts.items(), key=lambda x: x[1], reverse=True)
        print("   Top 3 conformaciones:")
        for i, (state, count) in enumerate(sorted_counts[:3]):
            prob = count / result1.total_shots
            print(f"     {i+1}. {state}: {count} ({prob:.3f})")
    else:
        print(f"❌ Error: {result1.error_message}")

    print()

    # Demo 2: Descubrimiento de fármacos
    print("2️⃣ DESCUBRIMIENTO DE FÁRMACOS")
    print("-" * 32)

    start_time = time.time()
    result2 = quantum(
        """
        Optimize drug-target binding affinity for aspirin and COX-2.
        Model molecular docking and calculate IC50.
        Evaluate binding energy and selectivity.
    """,
        shots=2048,
    )

    if result2.success:
        print(f"✅ Optimización exitosa en {time.time() - start_time:.2f}s")
        print(f"   Configuraciones de enlace: {len(result2.counts)}")
        print(f"   Configuración óptima: {result2.most_likely_outcome}")
        print(f"   Mediciones totales: {result2.total_shots}")

        # Analizar probabilidades
        probs = result2.probabilities()
        max_prob = max(probs.values())
        print(f"   Probabilidad máxima de enlace: {max_prob:.3f}")
    else:
        print(f"❌ Error: {result2.error_message}")

    print()

    # Demo 3: Análisis de ADN
    print("3️⃣ ANÁLISIS DE SECUENCIAS DE ADN")
    print("-" * 33)

    start_time = time.time()
    result3 = quantum(
        """
        Search for TATA box promoter sequences in genomic DNA.
        Use Grover's algorithm for pattern matching.
        Identify regulatory elements and binding sites.
    """,
        shots=1500,
    )

    if result3.success:
        print(f"✅ Búsqueda exitosa en {time.time() - start_time:.2f}s")
        print(f"   Patrones encontrados: {len(result3.counts)}")
        print(f"   Sitio más probable: {result3.most_likely_outcome}")
        print(f"   Análisis de: {result3.total_shots} posiciones")

        # Calcular eficiencia de búsqueda
        if result3.counts:
            top_hit_count = max(result3.counts.values())
            efficiency = top_hit_count / result3.total_shots
            print(f"   Eficiencia de búsqueda: {efficiency:.3f}")
    else:
        print(f"❌ Error: {result3.error_message}")

    print()

    # Demo 4: Estado cuántico complejo
    print("4️⃣ ESTADO CUÁNTICO COMPLEJO")
    print("-" * 29)

    start_time = time.time()
    result4 = quantum(
        """
        Create a 3-qubit entangled state for quantum biology.
        Model quantum coherence in photosynthesis.
        Generate GHZ state and measure correlations.
    """,
        shots=4096,
        debug=True,
    )

    if result4.success:
        print(f"✅ Estado cuántico creado en {time.time() - start_time:.2f}s")
        print(f"   Estados cuánticos: {len(result4.counts)}")
        print(f"   Estado principal: {result4.most_likely_outcome}")

        # Analizar entrelazamiento
        if "000" in result4.counts and "111" in result4.counts:
            ghz_fidelity = (
                result4.counts.get("000", 0) + result4.counts.get("111", 0)
            ) / result4.total_shots
            print(f"   Fidelidad GHZ: {ghz_fidelity:.3f}")

        # Mostrar metadata en modo debug
        if result4.metadata:
            backend = result4.metadata.get("backend_used", "unknown")
            print(f"   Backend utilizado: {backend}")
    else:
        print(f"❌ Error: {result4.error_message}")

    print("\n" + "=" * 60)
    print("🎉 DEMO COMPLETADA - BioQL está funcionando perfectamente!")
    print("\n💡 Próximos pasos:")
    print("   1. Explorar los ejemplos en examples/")
    print("   2. Probar con backends cuánticos reales (IBM Quantum)")
    print("   3. Usar las extensiones IDE para desarrollo")
    print("   4. Consultar la documentación completa")

    print("\n🌐 Recursos:")
    print("   📚 Documentación: README.md")
    print("   🧪 Ejemplos: examples/")
    print("   🔧 Extensiones: bioql install cursor")
    print("   ⚙️  Configuración: .env.example")

    print("\n🚀 ¡Bienvenido a la era de la bioinformática cuántica!")


if __name__ == "__main__":
    main()
