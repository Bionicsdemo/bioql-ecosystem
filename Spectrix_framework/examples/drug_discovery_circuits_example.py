# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Drug Discovery Circuit Templates - Comprehensive Examples

This example demonstrates how to use BioQL's quantum circuit templates
for drug discovery applications.

Includes examples for:
1. ADME prediction
2. Binding affinity calculation
3. Toxicity prediction
4. Pharmacophore generation
"""

from bioql.circuits.drug_discovery import (
    ADMECircuit,
)
from bioql.circuits.drug_discovery import BindingAffinityCircuitNew as BindingAffinityCircuit
from bioql.circuits.drug_discovery import (
    PharmacophoreCircuit,
    ToxicityPredictionCircuit,
)


def example_adme_prediction():
    """
    Example: Predict ADME properties of a drug candidate.

    ADME (Absorption, Distribution, Metabolism, Excretion) properties
    are critical for determining if a molecule will be an effective drug.
    """
    print("=" * 60)
    print("ADME PREDICTION EXAMPLE")
    print("=" * 60)

    # Example molecule: Aspirin
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"

    # Create ADME circuit
    adme_circuit = ADMECircuit(
        molecule_smiles=aspirin_smiles,
        properties=["absorption", "distribution", "metabolism", "excretion"],
        n_qubits=8,
    )

    # Predict all ADME properties
    print(f"\nMolecule: Aspirin (SMILES: {aspirin_smiles})")
    print("\nPredicting ADME properties...")

    result = adme_circuit.batch_predict()

    print(f"\nResults:")
    print(f"  Absorption:    {result.absorption_score:.3f}")
    print(f"  Distribution:  {result.distribution_score:.3f}")
    print(f"  Metabolism:    {result.metabolism_score:.3f}")
    print(f"  Excretion:     {result.excretion_score:.3f}")
    print(f"\n  Bioavailability: {result.bioavailability:.1f}%")
    print(f"  Half-life:       {result.half_life:.1f} hours")
    print(f"  Confidence:      {result.confidence:.3f}")

    # Check resource requirements
    resources = adme_circuit.estimate_resources()
    print(f"\nQuantum Resources:")
    print(f"  Qubits required:  {resources.num_qubits}")
    print(f"  Circuit depth:    {resources.circuit_depth}")
    print(f"  Total gates:      {resources.gate_count}")
    print(f"  Execution time:   {resources.execution_time_estimate:.2f}s")


def example_binding_affinity():
    """
    Example: Calculate ligand-receptor binding affinity.

    Binding affinity determines how strongly a drug binds to its target
    protein. Lower binding energy = stronger binding.
    """
    print("\n" + "=" * 60)
    print("BINDING AFFINITY CALCULATION EXAMPLE")
    print("=" * 60)

    # Example: Ibuprofen binding to COX enzyme
    ibuprofen_smiles = "CC(C)Cc1ccc(cc1)C(C)C(=O)O"
    receptor_pdb = "cox1.pdb"

    # Create binding affinity circuit
    binding_circuit = BindingAffinityCircuit(
        ligand_smiles=ibuprofen_smiles, receptor_pdb=receptor_pdb, n_qubits=12, vqe_depth=3
    )

    print(f"\nLigand:   Ibuprofen (SMILES: {ibuprofen_smiles})")
    print(f"Receptor: COX-1 enzyme ({receptor_pdb})")
    print("\nCalculating binding affinity using VQE...")

    # Estimate affinity
    result = binding_circuit.estimate_affinity()

    print(f"\nResults:")
    print(f"  Binding Energy:     {result.binding_energy:.2f} kcal/mol")
    print(f"  Binding Affinity:   {result.binding_affinity_kd:.2f} nM")
    print(f"  Interaction Score:  {result.interaction_score:.3f}")
    print(f"  Ligand Efficiency:  {result.ligand_efficiency:.3f}")
    print(f"  Confidence:         {result.confidence:.3f}")

    print(f"\nInteraction Types Detected:")
    for interaction in result.interaction_types:
        print(f"  - {interaction}")

    print(f"\nVQE Optimization:")
    print(f"  Ground State Energy: {result.vqe_energy:.6f} Hartree")
    print(f"  VQE Iterations:      {result.vqe_iterations}")

    # Resource requirements
    resources = binding_circuit.estimate_resources()
    print(f"\nQuantum Resources:")
    print(f"  Qubits required:  {resources.num_qubits}")
    print(f"  Circuit depth:    {resources.circuit_depth}")
    print(f"  Two-qubit gates:  {resources.two_qubit_gates}")


def example_toxicity_prediction():
    """
    Example: Predict toxicity of a drug candidate.

    Early toxicity prediction is crucial for drug safety and can
    save millions in development costs by identifying problematic
    compounds early.
    """
    print("\n" + "=" * 60)
    print("TOXICITY PREDICTION EXAMPLE")
    print("=" * 60)

    # Example molecule: Nitrobenzene (known to have toxicity concerns)
    nitrobenzene_smiles = "c1ccc(cc1)[N+](=O)[O-]"

    # Create toxicity prediction circuit
    toxicity_circuit = ToxicityPredictionCircuit(
        molecule_smiles=nitrobenzene_smiles,
        toxicity_endpoints=["hepatotoxicity", "cardiotoxicity", "mutagenicity"],
        n_qubits=10,
        classifier_depth=3,
    )

    print(f"\nMolecule: Nitrobenzene (SMILES: {nitrobenzene_smiles})")
    print("\nPredicting toxicity endpoints...")

    result = toxicity_circuit.predict_toxicity()

    print(f"\nToxicity Risk Scores:")
    if result.hepatotoxicity_risk is not None:
        print(f"  Hepatotoxicity:  {result.hepatotoxicity_risk:.3f}")
    if result.cardiotoxicity_risk is not None:
        print(f"  Cardiotoxicity:  {result.cardiotoxicity_risk:.3f}")
    if result.mutagenicity_risk is not None:
        print(f"  Mutagenicity:    {result.mutagenicity_risk:.3f}")

    print(f"\nOverall Assessment:")
    print(f"  Overall Risk:    {result.overall_risk:.3f}")
    print(f"  Risk Category:   {result.risk_category.upper()}")
    print(f"  Confidence:      {result.confidence:.3f}")

    if result.alerts:
        print(f"\nStructural Alerts (Toxicophores):")
        for alert in result.alerts:
            print(f"  - {alert}")

    print(f"\nRecommendations:")
    for rec in result.recommendations:
        print(f"  - {rec}")


def example_pharmacophore_generation():
    """
    Example: Generate pharmacophore model from a molecule.

    Pharmacophores represent the essential 3D features required for
    biological activity. They're used in virtual screening and
    lead optimization.
    """
    print("\n" + "=" * 60)
    print("PHARMACOPHORE GENERATION EXAMPLE")
    print("=" * 60)

    # Example molecule: Dopamine (neurotransmitter)
    dopamine_smiles = "NCCc1ccc(O)c(O)c1"

    # Create pharmacophore circuit
    pharmacophore_circuit = PharmacophoreCircuit(
        molecule_smiles=dopamine_smiles, n_qubits=8, n_conformers=10, optimization_depth=2
    )

    print(f"\nMolecule: Dopamine (SMILES: {dopamine_smiles})")
    print("\nGenerating pharmacophore model...")

    model = pharmacophore_circuit.generate_pharmacophore()

    print(f"\nPharmacophore Model:")
    print(f"  Quality Score:       {model.score:.3f}")
    print(f"  Number of Features:  {len(model.features)}")
    print(f"  Conformers Analyzed: {model.n_conformers}")
    print(f"  Quantum Enhanced:    {model.quantum_enhanced}")

    print(f"\nPharmacophore Features:")
    for i, feature in enumerate(model.features, 1):
        print(f"  {i}. {feature.feature_type}")
        print(
            f"     Position: ({feature.position[0]:.2f}, {feature.position[1]:.2f}, {feature.position[2]:.2f})"
        )
        print(f"     Radius:   {feature.radius:.2f} Å")
        print(f"     Importance: {feature.importance:.2f}")

    if model.constraints:
        print(f"\nDistance Constraints: {len(model.constraints)}")
        for i, constraint in enumerate(model.constraints[:3], 1):  # Show first 3
            print(
                f"  {i}. Feature {constraint['feature1_idx']} <-> Feature {constraint['feature2_idx']}"
            )
            print(f"     Distance: {constraint['distance']:.2f} ± {constraint['tolerance']:.2f} Å")

    # Export to dictionary
    model_dict = model.to_dict()
    print(f"\nModel can be exported to JSON for further use")


def example_complete_workflow():
    """
    Example: Complete drug discovery workflow.

    This demonstrates how to use multiple circuit templates together
    to evaluate a drug candidate comprehensively.
    """
    print("\n" + "=" * 60)
    print("COMPLETE DRUG DISCOVERY WORKFLOW")
    print("=" * 60)

    # Example molecule: Caffeine
    caffeine_smiles = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"

    print(f"\nEvaluating Drug Candidate: Caffeine")
    print(f"SMILES: {caffeine_smiles}")
    print("\n" + "-" * 60)

    # Step 1: ADME prediction
    print("\nStep 1: ADME Prediction")
    adme = ADMECircuit(caffeine_smiles)
    adme_result = adme.batch_predict()
    print(f"  Bioavailability: {adme_result.bioavailability:.1f}%")
    print(f"  Status: {'PASS' if adme_result.bioavailability > 30 else 'FAIL'}")

    # Step 2: Toxicity screening
    print("\nStep 2: Toxicity Screening")
    toxicity = ToxicityPredictionCircuit(caffeine_smiles)
    tox_result = toxicity.predict_toxicity()
    print(f"  Overall Risk: {tox_result.overall_risk:.3f} ({tox_result.risk_category})")
    print(f"  Status: {'PASS' if tox_result.overall_risk < 0.5 else 'WARNING'}")

    # Step 3: Pharmacophore generation
    print("\nStep 3: Pharmacophore Analysis")
    pharmacophore = PharmacophoreCircuit(caffeine_smiles)
    pharm_result = pharmacophore.generate_pharmacophore()
    print(f"  Features Identified: {len(pharm_result.features)}")
    print(f"  Model Quality: {pharm_result.score:.3f}")

    # Overall assessment
    print("\n" + "-" * 60)
    print("Overall Assessment:")
    adme_pass = adme_result.bioavailability > 30
    tox_pass = tox_result.overall_risk < 0.5
    pharm_pass = pharm_result.score > 0.5

    print(f"  ADME:         {'✓ PASS' if adme_pass else '✗ FAIL'}")
    print(f"  Toxicity:     {'✓ PASS' if tox_pass else '✗ WARNING'}")
    print(f"  Pharmacophore: {'✓ GOOD' if pharm_pass else '✗ POOR'}")

    if adme_pass and tox_pass and pharm_pass:
        print("\n  Recommendation: PROCEED to binding affinity studies")
    else:
        print("\n  Recommendation: Further optimization needed")


if __name__ == "__main__":
    """
    Run all examples.
    """
    print("\n" + "=" * 60)
    print("BioQL Drug Discovery Circuit Templates - Examples")
    print("=" * 60)

    # Run individual examples
    example_adme_prediction()
    example_binding_affinity()
    example_toxicity_prediction()
    example_pharmacophore_generation()

    # Run complete workflow
    example_complete_workflow()

    print("\n" + "=" * 60)
    print("Examples completed successfully!")
    print("=" * 60 + "\n")
