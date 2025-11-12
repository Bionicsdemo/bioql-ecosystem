# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
QPHAROS Esquema 3: Object-Oriented API
For bioinformatics pipelines and enterprise users
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .api import design_drug, dock, predict_admet, screen_library
from .core.config import QPHAROSConfig
from .models import ADMETResult, DockingResult, DrugDesignResult


@dataclass
class AnalysisSession:
    """Represents an analysis session with results"""

    session_id: str
    started_at: datetime
    config: QPHAROSConfig
    results: List[Any]

    def add_result(self, result: Any):
        """Add result to session"""
        self.results.append(result)

    def get_hits(self, affinity_threshold: float = -7.0) -> List[DockingResult]:
        """Get all hits below affinity threshold"""
        hits = []
        for r in self.results:
            if isinstance(r, DockingResult):
                if r.binding_affinity and r.binding_affinity < affinity_threshold:
                    hits.append(r)
        return hits


class QPHAROSAnalyzer:
    """
    Object-oriented interface to QPHAROS.
    Perfect for integration into drug discovery pipelines.

    Example:
        >>> from qpharos import QPHAROSAnalyzer, QPHAROSConfig
        >>>
        >>> config = QPHAROSConfig(
        ...     backend='ibm_torino',
        ...     shots=2000,
        ...     api_key='bioql_xxx'
        ... )
        >>>
        >>> analyzer = QPHAROSAnalyzer(config)
        >>>
        >>> # Analyze single compound
        >>> result = analyzer.dock('CCO', '6B3J')
        >>>
        >>> # Screen library
        >>> hits = analyzer.screen(['CCO', 'CC(C)O', 'CCCO'], '6B3J')
        >>>
        >>> # Generate report
        >>> analyzer.save_report('results.json')
    """

    def __init__(self, config: Optional[QPHAROSConfig] = None):
        """
        Initialize QPHAROS Analyzer.

        Args:
            config: QPHAROSConfig object (if None, uses defaults)
        """
        self.config = config or QPHAROSConfig()
        self.session = AnalysisSession(
            session_id=f"qpharos_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            started_at=datetime.now(),
            config=self.config,
            results=[],
        )

    def dock(self, ligand: str, receptor: str, **kwargs) -> DockingResult:
        """
        Perform molecular docking.

        Args:
            ligand: SMILES string
            receptor: PDB ID
            **kwargs: Override config parameters

        Returns:
            DockingResult object
        """
        # Merge config with kwargs
        params = {
            "ligand": ligand,
            "receptor": receptor,
            "api_key": kwargs.get("api_key", self.config.api_key),
            "backend": kwargs.get("backend", self.config.backend),
            "shots": kwargs.get("shots", self.config.shots),
            "qec": kwargs.get("qec", self.config.qec_enabled),
        }

        result = dock(**params)
        self.session.add_result(result)
        return result

    def predict_admet(self, smiles: str, **kwargs) -> ADMETResult:
        """
        Predict ADMET properties.

        Args:
            smiles: SMILES string
            **kwargs: Override config parameters

        Returns:
            ADMETResult object
        """
        params = {
            "smiles": smiles,
            "api_key": kwargs.get("api_key", self.config.api_key),
            "backend": kwargs.get("backend", self.config.backend),
            "shots": kwargs.get("shots", int(self.config.shots * 0.75)),  # Fewer shots for ADMET
        }

        result = predict_admet(**params)
        self.session.add_result(result)
        return result

    def design(self, target_protein: str, **kwargs) -> DrugDesignResult:
        """
        Design novel drug candidates.

        Args:
            target_protein: PDB ID
            **kwargs: Override config parameters

        Returns:
            DrugDesignResult object
        """
        params = {
            "target_protein": target_protein,
            "api_key": kwargs.get("api_key", self.config.api_key),
            "backend": kwargs.get("backend", self.config.backend),
            "shots": kwargs.get("shots", int(self.config.shots * 1.5)),  # More shots for design
        }

        result = design_drug(**params)
        self.session.add_result(result)
        return result

    def screen(
        self, ligands: List[str], receptor: str, affinity_threshold: float = -7.0, **kwargs
    ) -> List[DockingResult]:
        """
        Screen library of ligands.

        Args:
            ligands: List of SMILES strings
            receptor: PDB ID
            affinity_threshold: Only return hits below this (kcal/mol)
            **kwargs: Override config parameters

        Returns:
            List of DockingResult objects (hits only)
        """
        params = {
            "ligands": ligands,
            "receptor": receptor,
            "api_key": kwargs.get("api_key", self.config.api_key),
            "backend": kwargs.get("backend", self.config.backend),
            "shots_per_ligand": kwargs.get("shots", int(self.config.shots * 0.5)),  # Fewer for HTS
        }

        results = screen_library(**params)

        # Filter hits
        hits = [
            r for r in results if r.binding_affinity and r.binding_affinity < affinity_threshold
        ]

        # Add to session
        for hit in hits:
            self.session.add_result(hit)

        return hits

    def full_pipeline(self, ligand: str, receptor: str) -> Dict[str, Any]:
        """
        Run complete drug discovery pipeline:
        1. Docking
        2. ADMET prediction
        3. Hit validation

        Args:
            ligand: SMILES string
            receptor: PDB ID

        Returns:
            dict with all results and recommendation
        """
        # Step 1: Docking
        dock_result = self.dock(ligand, receptor)

        # Step 2: ADMET if docking is promising
        admet_result = None
        if dock_result.binding_affinity and dock_result.binding_affinity < -6.0:
            admet_result = self.predict_admet(ligand)

        # Step 3: Generate recommendation
        recommendation = self._generate_recommendation(dock_result, admet_result)

        return {
            "ligand": ligand,
            "receptor": receptor,
            "docking": dock_result,
            "admet": admet_result,
            "recommendation": recommendation,
            "session_id": self.session.session_id,
        }

    def _generate_recommendation(self, dock: DockingResult, admet: Optional[ADMETResult]) -> str:
        """Generate recommendation based on results"""
        if not dock.success:
            return "Analysis failed - check inputs"

        affinity = dock.binding_affinity or 0.0

        if affinity < -8.0:
            if admet and admet.lipinski_pass and admet.qed_score and admet.qed_score > 0.6:
                return "🌟 Excellent lead - ready for optimization"
            elif admet and admet.lipinski_pass:
                return "✅ Strong binder - validate ADMET properties"
            else:
                return "⚠️  Strong binder but poor drug-likeness - consider modifications"
        elif affinity < -7.0:
            return "✓ Good binder - proceed to hit-to-lead"
        elif affinity < -6.0:
            return "→ Moderate binder - consider optimization"
        else:
            return "✗ Weak binder - not recommended"

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        total = len(self.session.results)
        docking = sum(1 for r in self.session.results if isinstance(r, DockingResult))
        admet = sum(1 for r in self.session.results if isinstance(r, ADMETResult))
        design = sum(1 for r in self.session.results if isinstance(r, DrugDesignResult))

        hits = self.session.get_hits()

        return {
            "session_id": self.session.session_id,
            "started_at": self.session.started_at.isoformat(),
            "total_analyses": total,
            "docking": docking,
            "admet": admet,
            "design": design,
            "hits": len(hits),
            "config": {
                "backend": self.config.backend,
                "shots": self.config.shots,
                "qec_enabled": self.config.qec_enabled,
            },
        }

    def save_report(self, filepath: str, format: str = "json"):
        """
        Save session results to file.

        Args:
            filepath: Output file path
            format: 'json' or 'text'
        """
        summary = self.get_session_summary()

        if format == "json":
            with open(filepath, "w") as f:
                json.dump(summary, f, indent=2)
        else:
            with open(filepath, "w") as f:
                f.write(f"QPHAROS Analysis Report\n")
                f.write(f"{'=' * 60}\n\n")
                f.write(f"Session ID: {summary['session_id']}\n")
                f.write(f"Started: {summary['started_at']}\n")
                f.write(f"Total Analyses: {summary['total_analyses']}\n")
                f.write(f"  - Docking: {summary['docking']}\n")
                f.write(f"  - ADMET: {summary['admet']}\n")
                f.write(f"  - Design: {summary['design']}\n")
                f.write(f"Hits: {summary['hits']}\n\n")
                f.write(f"Configuration:\n")
                f.write(f"  Backend: {summary['config']['backend']}\n")
                f.write(f"  Shots: {summary['config']['shots']}\n")
                f.write(f"  QEC: {summary['config']['qec_enabled']}\n")

    def get_hits(self, affinity_threshold: float = -7.0) -> List[DockingResult]:
        """Get all hits from current session"""
        return self.session.get_hits(affinity_threshold)

    def clear_session(self):
        """Clear current session and start new one"""
        self.session = AnalysisSession(
            session_id=f"qpharos_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            started_at=datetime.now(),
            config=self.config,
            results=[],
        )
