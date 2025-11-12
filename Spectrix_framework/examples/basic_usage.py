#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Basic Usage Examples

This example provides simple, beginner-friendly demonstrations of BioQL
functionality. It's designed to help new users get started with quantum
computing for bioinformatics applications quickly and easily.

The examples focus on:
- Simple quantum operations and measurements
- Basic bioinformatics applications
- Clear explanations of quantum concepts
- Step-by-step tutorials with expected outputs
- Common use cases and practical applications
- Troubleshooting and debugging tips

This is the perfect starting point for users new to BioQL or quantum computing.

Requirements:
- BioQL framework
- Python 3.7+
- Basic understanding of quantum computing concepts (helpful but not required)
"""

import os
import sys
import time

# Add parent directory to path for bioql imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from bioql import (
        QuantumResult,
        check_installation,
        configure_debug_mode,
        get_info,
        get_version,
        quantum,
    )
except ImportError as e:
    print(f"Error importing BioQL: {e}")
    print("Make sure BioQL is properly installed and in your Python path")
    print("Try: pip install -e . from the bioql directory")
    sys.exit(1)


def welcome_message():
    """Display welcome message and system information."""
    print("🧬 Welcome to BioQL! 🧬")
    print("=" * 50)
    print("BioQL: Quantum Computing for Bioinformatics")
    print("=" * 50)

    # Show version information
    version = get_version()
    print(f"BioQL Version: {version}")

    # Check system information
    info = get_info()
    print(f"Python Version: {info.get('python_version', 'Unknown')}")
    print(f"Qiskit Available: {'✓' if info.get('qiskit_available') else '✗'}")

    # Check installation
    installation_ok = check_installation()
    print(f"Installation Status: {'✓ Ready' if installation_ok else '⚠ Issues detected'}")

    if not info.get("qiskit_available"):
        print("\n⚠ Warning: Qiskit not found. Install with:")
        print("  pip install qiskit qiskit-aer")
        print("  Some quantum features may not work without Qiskit.")

    print("\nLet's get started with some basic examples!")
    print("-" * 50)


def example_1_hello_quantum():
    """Example 1: Your first quantum program - creating a simple qubit."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Hello Quantum World!")
    print("=" * 60)
    print("Let's create your first quantum program.")
    print("We'll create a single qubit and measure it.")

    try:
        print("\n1. Creating a qubit in |0⟩ state:")
        result = quantum("Create a single qubit in state 0", shots=100)

        if result.success:
            print(f"✓ Success! Results: {result.counts}")
            print(f"  Total measurements: {result.total_shots}")
            print(f"  Most likely outcome: {result.most_likely_outcome}")
            print(f"  Explanation: The qubit started in |0⟩, so we always measure 0")
        else:
            print(f"✗ Error: {result.error_message}")

        print("\n2. Creating a qubit in superposition:")
        result = quantum("Put a qubit in superposition", shots=1000)

        if result.success:
            print(f"✓ Success! Results: {result.counts}")

            # Calculate probabilities
            probs = result.probabilities()
            print(f"  Probabilities: {probs}")
            print(f"  Explanation: Superposition means 50% chance of measuring 0 or 1")

            # Check if results are roughly balanced
            if "0" in probs and "1" in probs:
                if abs(probs["0"] - 0.5) < 0.1:
                    print("  ✓ Results look good - roughly 50/50 distribution!")
                else:
                    print("  ⚠ Results are unbalanced - this is normal with quantum randomness")

    except Exception as e:
        print(f"✗ Error in Example 1: {e}")
        print("💡 Tip: Make sure BioQL is properly installed")


def example_2_quantum_randomness():
    """Example 2: Quantum random number generation."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Quantum Random Number Generation")
    print("=" * 60)
    print("Quantum computers are excellent random number generators!")
    print("Let's generate some quantum random numbers.")

    try:
        print("\n1. Single random bit:")
        result = quantum("Generate a random bit", shots=1)

        if result.success:
            random_bit = result.most_likely_outcome
            print(f"✓ Your quantum random bit: {random_bit}")
            print(f"  This bit is truly random thanks to quantum mechanics!")

        print("\n2. Multiple random bits:")
        result = quantum("Generate random bits with 2 qubits", shots=500)

        if result.success:
            print(f"✓ Random bit distribution: {result.counts}")

            # Show what each outcome means
            print("  Outcome meanings:")
            for outcome, count in result.counts.items():
                percentage = (count / result.total_shots) * 100
                print(f"    {outcome}: {count} times ({percentage:.1f}%)")

            print("  Each 2-bit combination should appear roughly 25% of the time")

        print("\n3. Quantum coin flip:")
        print("Let's flip a quantum coin 10 times!")

        coin_flips = []
        for i in range(10):
            result = quantum("Generate random bit", shots=1)
            if result.success:
                bit = result.most_likely_outcome
                coin = "Heads" if bit == "0" else "Tails"
                coin_flips.append(coin)
                print(f"  Flip {i+1}: {coin}")

        heads = coin_flips.count("Heads")
        tails = coin_flips.count("Tails")
        print(f"\nResults: {heads} Heads, {tails} Tails")

    except Exception as e:
        print(f"✗ Error in Example 2: {e}")


def example_3_entanglement():
    """Example 3: Quantum entanglement basics."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Quantum Entanglement")
    print("=" * 60)
    print("Entanglement is one of the most fascinating quantum phenomena!")
    print("Let's create entangled qubits.")

    try:
        print("\n1. Creating a Bell state (maximally entangled state):")
        result = quantum("Create a Bell state with 2 qubits", shots=1000)

        if result.success:
            print(f"✓ Bell state results: {result.counts}")

            # Explain the results
            print("\nWhat's happening:")
            print("  - The qubits are entangled")
            print("  - When we measure, we get either |00⟩ or |11⟩")
            print("  - We never see |01⟩ or |10⟩ - the qubits are correlated!")

            # Check if we see the expected pattern
            unwanted_states = ["01", "10"]
            if any(state in result.counts for state in unwanted_states):
                print("  ⚠ Unexpected states detected - this might indicate noise")
            else:
                print("  ✓ Perfect entanglement observed!")

        print("\n2. Three-qubit entanglement (GHZ state):")
        result = quantum("Create GHZ state with 3 qubits", shots=500)

        if result.success:
            print(f"✓ GHZ state results: {result.counts}")
            print("\nGHZ states show even stranger correlations:")
            print("  - We should see mostly |000⟩ and |111⟩")
            print("  - All three qubits are entangled together")

    except Exception as e:
        print(f"✗ Error in Example 3: {e}")


def example_4_basic_bioinformatics():
    """Example 4: Simple bioinformatics applications."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Basic Bioinformatics with Quantum")
    print("=" * 60)
    print("Now let's apply quantum computing to some biology problems!")

    try:
        print("\n1. DNA sequence representation:")
        print("We can encode DNA bases using quantum states:")
        print("  A = |00⟩, T = |01⟩, G = |10⟩, C = |11⟩")

        result = quantum("Represent DNA base A using quantum state", shots=100)
        if result.success:
            print(f"✓ Quantum DNA base A: {result.counts}")
            print("  The |00⟩ state represents Adenine (A)")

        print("\n2. Simple protein folding simulation:")
        result = quantum("Model simple protein folding with 2 amino acids", shots=200)

        if result.success:
            print(f"✓ Protein folding states: {result.counts}")
            print("  Each quantum state represents a different protein conformation")
            print("  |00⟩ = fully extended, |11⟩ = fully folded")

        print("\n3. Molecular interaction modeling:")
        result = quantum("Model molecular binding interaction", shots=150)

        if result.success:
            print(f"✓ Binding states: {result.counts}")
            print("  Different states represent bound vs unbound molecules")
            print("  This could help in drug discovery!")

    except Exception as e:
        print(f"✗ Error in Example 4: {e}")


def example_5_working_with_results():
    """Example 5: Understanding and working with quantum results."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Understanding Quantum Results")
    print("=" * 60)
    print("Let's learn how to interpret and work with quantum measurement results.")

    try:
        # Generate some results to work with
        result = quantum("Create superposition and measure", shots=1000)

        if result.success:
            print(f"Raw results: {result.counts}")

            print(f"\n1. Basic information:")
            print(f"   Total shots: {result.total_shots}")
            print(f"   Number of different outcomes: {len(result.counts)}")
            print(f"   Most likely outcome: {result.most_likely_outcome}")

            print(f"\n2. Probability analysis:")
            probabilities = result.probabilities()
            for outcome, prob in probabilities.items():
                count = result.counts[outcome]
                print(f"   |{outcome}⟩: {prob:.3f} probability ({count} times)")

            print(f"\n3. Statistical analysis:")
            if "0" in probabilities and "1" in probabilities:
                prob_0 = probabilities["0"]
                prob_1 = probabilities["1"]

                print(f"   Difference from ideal 50/50: {abs(prob_0 - 0.5):.3f}")

                if abs(prob_0 - 0.5) < 0.05:
                    print("   ✓ Results are very close to expected 50/50 distribution")
                elif abs(prob_0 - 0.5) < 0.1:
                    print("   ✓ Results are reasonably close to expected distribution")
                else:
                    print(
                        "   ⚠ Results show significant deviation (this is normal with small samples)"
                    )

            print(f"\n4. Metadata information:")
            metadata = result.metadata
            if metadata:
                print(f"   Backend used: {metadata.get('backend', 'Unknown')}")
                print(f"   Circuit depth: {metadata.get('circuit_depth', 'Unknown')}")
                print(f"   Number of qubits: {metadata.get('num_qubits', 'Unknown')}")

    except Exception as e:
        print(f"✗ Error in Example 5: {e}")


def example_6_debugging_tips():
    """Example 6: Debugging and troubleshooting tips."""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Debugging and Troubleshooting")
    print("=" * 60)
    print("Let's learn how to debug quantum programs and handle errors.")

    try:
        print("\n1. Using debug mode:")
        configure_debug_mode(True)

        result = quantum("Create Bell state", debug=True, shots=50)
        if result.success:
            print("✓ Debug mode provides extra information in the logs")

        # Turn off debug mode
        configure_debug_mode(False)

        print("\n2. Handling errors gracefully:")
        # This should trigger an error handling example
        result = quantum("", shots=10)  # Empty program

        if not result.success:
            print(f"✓ Error caught successfully: {result.error_message}")
            print("  The error was handled gracefully without crashing")

        print("\n3. Checking different shot counts:")
        shot_counts = [10, 100, 1000]

        for shots in shot_counts:
            result = quantum("Generate random bit", shots=shots)
            if result.success:
                probs = result.probabilities()
                prob_0 = probs.get("0", 0)
                deviation = abs(prob_0 - 0.5)
                print(f"   {shots:4d} shots: P(0) = {prob_0:.3f}, deviation = {deviation:.3f}")

        print("   Notice: More shots generally give more accurate results")

        print(f"\n4. Performance tips:")
        print("   - Start with small shot counts for testing")
        print("   - Use debug mode when developing")
        print("   - Check result.success before using results")
        print("   - Simulators are faster for development")

    except Exception as e:
        print(f"✗ Error in Example 6: {e}")


def example_7_practical_workflow():
    """Example 7: A practical workflow for quantum bioinformatics."""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Practical Quantum Bioinformatics Workflow")
    print("=" * 60)
    print("Let's simulate a complete workflow for a bioinformatics problem.")

    try:
        print("\nScenario: Analyzing protein-drug interactions")
        print("Step 1: Model the protein binding site")

        protein_result = quantum("Model protein binding site with quantum states", shots=200)

        if protein_result.success:
            print(f"✓ Protein binding sites modeled: {len(protein_result.counts)} states")

            print("\nStep 2: Model drug candidates")
            drug_results = []

            for i, drug_name in enumerate(["Drug_A", "Drug_B", "Drug_C"]):
                result = quantum(f"Model drug candidate interaction", shots=100)
                if result.success:
                    drug_results.append((drug_name, result))
                    print(f"✓ {drug_name} modeled: {result.most_likely_outcome} binding state")

            print("\nStep 3: Analyze binding affinities")
            best_drug = None
            best_score = 0

            for drug_name, result in drug_results:
                # Simple scoring based on measurement distribution
                if result.counts:
                    # Use the probability of the most likely outcome as a crude "binding score"
                    probs = result.probabilities()
                    score = max(probs.values()) if probs else 0

                    print(f"   {drug_name}: binding score = {score:.3f}")

                    if score > best_score:
                        best_score = score
                        best_drug = drug_name

            print(f"\nStep 4: Results and recommendations")
            if best_drug:
                print(f"✓ Best drug candidate: {best_drug} (score: {best_score:.3f})")
                print(f"  Recommendation: Focus further research on {best_drug}")

            print(f"\nStep 5: Next steps")
            print("   - Run more detailed simulations with higher shot counts")
            print("   - Consider quantum error correction for production use")
            print("   - Validate results with experimental data")

    except Exception as e:
        print(f"✗ Error in Example 7: {e}")


def interactive_tutorial():
    """Interactive tutorial for hands-on learning."""
    print("\n" + "=" * 60)
    print("INTERACTIVE TUTORIAL")
    print("=" * 60)
    print("Let's try some interactive quantum programming!")

    try:
        # Simple interactive session
        print("\nLet's build a quantum program step by step:")
        print("1. We'll create a superposition")
        print("2. Then measure it multiple times")
        print("3. Observe the quantum randomness")

        input("\nPress Enter to start...")

        print("\nCreating superposition...")
        time.sleep(1)

        result = quantum("Put qubit in superposition", shots=10)
        if result.success:
            print(f"First 10 measurements: {result.counts}")

        input("\nPress Enter to measure 100 more times...")

        result = quantum("Put qubit in superposition", shots=100)
        if result.success:
            print(f"100 measurements: {result.counts}")
            probs = result.probabilities()
            print(f"Probabilities: {probs}")

        input("\nPress Enter to measure 1000 times...")

        result = quantum("Put qubit in superposition", shots=1000)
        if result.success:
            print(f"1000 measurements: {result.counts}")
            probs = result.probabilities()
            print(f"Probabilities: {probs}")

            print("\nNotice how the probabilities get closer to 50/50 with more measurements!")
            print("This demonstrates the law of large numbers in quantum mechanics.")

        print("\n✓ Interactive tutorial completed!")

    except KeyboardInterrupt:
        print("\n\nTutorial interrupted by user.")
    except Exception as e:
        print(f"✗ Error in interactive tutorial: {e}")


def quick_reference():
    """Display a quick reference guide."""
    print("\n" + "=" * 60)
    print("BIOQL QUICK REFERENCE GUIDE")
    print("=" * 60)

    print(
        """
🧬 BASIC USAGE:
    from bioql import quantum
    result = quantum("your quantum program", shots=1000)

📊 WORKING WITH RESULTS:
    result.counts          # Raw measurement counts
    result.probabilities() # Normalized probabilities
    result.total_shots     # Number of measurements
    result.most_likely_outcome  # Most frequent result
    result.success         # True if execution succeeded
    result.error_message   # Error details if failed

🔧 COMMON PARAMETERS:
    shots=1000            # Number of measurements
    debug=True            # Enable debug output
    backend='simulator'   # Quantum backend to use

🧪 EXAMPLE PROGRAMS:
    "Create a Bell state"
    "Put qubit in superposition"
    "Generate random bit"
    "Model protein folding with 3 amino acids"
    "Simulate molecular binding"

🐛 DEBUGGING:
    configure_debug_mode(True)   # Enable global debug mode
    check_installation()         # Verify BioQL setup
    get_info()                  # System information

💡 TIPS:
    - Start with small shot counts (10-100) for testing
    - Use debug mode when developing
    - Always check result.success before using results
    - More shots = more accurate probabilities
    - Simulators are fast and free for development
    """
    )


def main():
    """
    Main function that runs all basic usage examples.
    """
    welcome_message()

    try:
        # Run all examples
        example_1_hello_quantum()
        example_2_quantum_randomness()
        example_3_entanglement()
        example_4_basic_bioinformatics()
        example_5_working_with_results()
        example_6_debugging_tips()
        example_7_practical_workflow()

        # Ask if user wants interactive tutorial
        try:
            user_input = input("\nWould you like to try the interactive tutorial? (y/n): ").lower()
            if user_input.startswith("y"):
                interactive_tutorial()
        except (EOFError, KeyboardInterrupt):
            print("\nSkipping interactive tutorial.")

        # Show quick reference
        quick_reference()

        print("\n" + "=" * 60)
        print("🎉 CONGRATULATIONS! 🎉")
        print("=" * 60)
        print("You've completed the BioQL basic usage examples!")
        print("\nWhat you've learned:")
        print("✓ How to create and run quantum programs")
        print("✓ Understanding quantum measurement results")
        print("✓ Basic quantum phenomena (superposition, entanglement)")
        print("✓ Simple bioinformatics applications")
        print("✓ Debugging and troubleshooting techniques")
        print("✓ Practical workflow for quantum bioinformatics")

        print("\nNext steps:")
        print("1. Explore the advanced examples:")
        print("   - protein_folding.py")
        print("   - drug_discovery.py")
        print("   - dna_matching.py")
        print("   - advanced_features.py")
        print("\n2. Try your own quantum programs")
        print("3. Read the full documentation")
        print("4. Join the BioQL community!")

        print("\nHappy quantum computing! 🚀")

    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user. Thanks for trying BioQL!")
    except Exception as e:
        print(f"\n✗ Error running basic examples: {e}")
        import traceback

        traceback.print_exc()

        print("\n🔧 TROUBLESHOOTING:")
        print("1. Make sure BioQL is properly installed:")
        print("   pip install -e . (from bioql directory)")
        print("2. Check that all dependencies are available:")
        print("   pip install -r requirements.txt")
        print("3. Try running individual examples:")
        print("   python -c \"from bioql import quantum; print(quantum('test', shots=1))\"")
        print("4. Enable debug mode for more information:")
        print("   configure_debug_mode(True)")


if __name__ == "__main__":
    main()
