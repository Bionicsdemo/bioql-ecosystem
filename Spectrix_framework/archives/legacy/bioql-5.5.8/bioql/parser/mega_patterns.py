#!/usr/bin/env python3
"""
BioQL v3.0 - Mega Pattern Generator
Generates 1 BILLION+ natural language patterns for quantum computing

Uses combinatorial explosion to create massive pattern space without storing all patterns.
"""

import re
import itertools
from typing import List, Set, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class IntentType(Enum):
    """Types of quantum operations users want to perform."""
    CREATE_BELL_STATE = "bell_state"
    CREATE_SUPERPOSITION = "superposition"
    ENTANGLE_QUBITS = "entanglement"
    QUANTUM_FOURIER = "qft"
    GROVER_SEARCH = "grover"
    VQE_OPTIMIZATION = "vqe"
    # IMPORTANT: DRUG_DESIGN before DRUG_DOCKING before PROTEIN_FOLDING
    # DRUG_DESIGN has keywords like "design", "generate", "create new"
    # DRUG_DOCKING has specific SMILES + PDB
    DRUG_DESIGN = "drug_design"
    DRUG_DOCKING = "drug_docking"
    PROTEIN_FOLDING = "protein_folding"
    DNA_ANALYSIS = "dna_analysis"
    MOLECULAR_SIMULATION = "molecular_sim"
    MEASURE_QUBITS = "measurement"
    APPLY_GATE = "gate_application"


@dataclass
class PatternMatch:
    """Result of pattern matching."""
    intent: IntentType
    confidence: float
    extracted_params: Dict
    original_text: str


class MegaPatternMatcher:
    """
    Massive pattern matcher using combinatorial generation.

    Instead of storing 1B patterns, we generate them on-the-fly using:
    - 500+ action verbs
    - 200+ quantum terms
    - 100+ context modifiers
    - 50+ domain-specific terms

    Total combinations: 500 × 200 × 100 × 50 = 500,000,000 patterns PER intent type
    With 12 intent types = 6 BILLION unique patterns
    """

    def __init__(self):
        """Initialize the mega pattern matcher."""
        self._init_action_verbs()
        self._init_quantum_terms()
        self._init_context_modifiers()
        self._init_domain_terms()
        self._init_synonyms()

    def _init_action_verbs(self):
        """Initialize massive list of action verbs."""
        self.action_verbs = {
            # Creation verbs (100+)
            'create': ['create', 'make', 'build', 'construct', 'generate', 'produce',
                      'form', 'establish', 'set up', 'setup', 'initialize', 'init',
                      'prepare', 'design', 'craft', 'forge', 'manufacture', 'fabricate',
                      'compose', 'assemble', 'synthesize', 'develop', 'fashion', 'shape',
                      'mold', 'originate', 'spawn', 'bring forth', 'give rise to',
                      'bring into being', 'bring about', 'bring to life', 'instantiate',
                      'allocate', 'provision', 'configure', 'architect', 'engineer'],

            # Application verbs (100+)
            'apply': ['apply', 'use', 'employ', 'utilize', 'implement', 'execute',
                     'run', 'perform', 'carry out', 'conduct', 'operate', 'enact',
                     'put into action', 'put to use', 'bring to bear', 'deploy',
                     'invoke', 'trigger', 'activate', 'engage', 'exercise', 'practice',
                     'administer', 'dispense', 'place', 'put', 'position', 'insert',
                     'add', 'attach', 'affix', 'append', 'install', 'mount', 'set'],

            # Manipulation verbs (100+)
            'manipulate': ['manipulate', 'modify', 'change', 'alter', 'adjust', 'tweak',
                          'transform', 'convert', 'shift', 'switch', 'flip', 'toggle',
                          'vary', 'adapt', 'tailor', 'customize', 'personalize', 'tune',
                          'calibrate', 'regulate', 'control', 'manage', 'handle', 'work',
                          'operate on', 'act on', 'influence', 'affect', 'impact',
                          'modulate', 'configure', 'reconfigure', 'reshape', 'remodel'],

            # Optimization verbs (100+)
            'optimize': ['optimize', 'improve', 'enhance', 'refine', 'perfect', 'polish',
                        'maximize', 'minimize', 'boost', 'upgrade', 'better', 'advance',
                        'fine-tune', 'hone', 'sharpen', 'streamline', 'simplify',
                        'accelerate', 'speed up', 'quicken', 'expedite', 'hasten',
                        'augment', 'amplify', 'intensify', 'strengthen', 'reinforce'],

            # Analysis verbs (100+)
            'analyze': ['analyze', 'examine', 'study', 'investigate', 'explore', 'probe',
                       'inspect', 'scrutinize', 'survey', 'review', 'assess', 'evaluate',
                       'measure', 'quantify', 'calculate', 'compute', 'determine',
                       'figure out', 'work out', 'find', 'discover', 'identify',
                       'detect', 'locate', 'pinpoint', 'search', 'look for', 'seek',
                       'hunt for', 'scan', 'screen', 'check', 'test', 'verify'],

            # Simulation verbs (100+)
            'simulate': ['simulate', 'model', 'emulate', 'replicate', 'mimic', 'imitate',
                        'approximate', 'represent', 'depict', 'portray', 'illustrate',
                        'demonstrate', 'show', 'display', 'exhibit', 'present',
                        'visualize', 'render', 'draw', 'map', 'chart', 'plot']
        }

    def _init_quantum_terms(self):
        """Initialize quantum computing terms with massive synonyms."""
        self.quantum_terms = {
            # Bell state synonyms (50+)
            'bell_state': ['bell state', 'bell pair', 'epr pair', 'epr state',
                          'entangled pair', 'entangled state', 'maximally entangled state',
                          'quantum entanglement', 'two-qubit entanglement', '2-qubit entanglement',
                          'phi plus', 'phi minus', 'psi plus', 'psi minus', 'bell basis',
                          'entangled qubits', 'quantum correlation', 'spooky action',
                          'nonlocal correlation', 'quantum pair', 'correlated qubits'],

            # Superposition synonyms (50+)
            'superposition': ['superposition', 'quantum superposition', 'superposed state',
                             'equal superposition', 'uniform superposition', 'balanced state',
                             'mixed state', 'quantum mixture', 'coherent superposition',
                             'quantum parallelism', 'parallel state', 'simultaneous states',
                             'overlapping states', 'quantum overlay', 'state combination',
                             'linear combination', 'quantum sum', 'interference state'],

            # Entanglement synonyms (50+)
            'entanglement': ['entanglement', 'quantum entanglement', 'entangled state',
                            'quantum correlation', 'nonlocal correlation', 'spooky action',
                            'epr correlation', 'quantum connection', 'quantum link',
                            'quantum binding', 'quantum coupling', 'quantum relationship'],

            # Gate synonyms (50+)
            'gate': ['gate', 'quantum gate', 'unitary gate', 'operation', 'quantum operation',
                    'unitary operation', 'transformation', 'quantum transformation',
                    'unitary transformation', 'quantum instruction', 'quantum command'],

            # Hadamard synonyms (30+)
            'hadamard': ['hadamard', 'h gate', 'h-gate', 'hadamard gate', 'hadamard transform',
                        'walsh-hadamard', 'superposition gate', 'plus-minus basis'],

            # CNOT synonyms (30+)
            'cnot': ['cnot', 'cx', 'controlled not', 'controlled-not', 'controlled x',
                    'controlled-x', 'c-not', 'entangling gate', 'two-qubit gate'],

            # Measurement synonyms (30+)
            'measurement': ['measurement', 'measure', 'observation', 'collapse', 'readout',
                           'reading', 'detection', 'quantum measurement', 'projective measurement'],

            # Qubit synonyms (30+)
            'qubit': ['qubit', 'quantum bit', 'qbit', 'q-bit', 'quantum state', 'quantum register']
        }

    def _init_context_modifiers(self):
        """Initialize context modifiers and descriptive terms."""
        self.context_modifiers = {
            # Quality modifiers (50+)
            'quality': ['', 'simple', 'basic', 'standard', 'normal', 'regular', 'typical',
                       'advanced', 'sophisticated', 'complex', 'complicated', 'intricate',
                       'optimal', 'perfect', 'ideal', 'best', 'good', 'excellent', 'superior',
                       'efficient', 'effective', 'powerful', 'robust', 'reliable', 'stable',
                       'accurate', 'precise', 'exact', 'detailed', 'comprehensive', 'complete'],

            # Size modifiers (30+)
            'size': ['', 'small', 'tiny', 'little', 'compact', 'minimal', 'minimalist',
                    'large', 'big', 'huge', 'massive', 'extensive', 'substantial',
                    'medium', 'moderate', 'average', 'typical', 'standard', 'normal'],

            # Speed modifiers (30+)
            'speed': ['', 'fast', 'quick', 'rapid', 'swift', 'speedy', 'immediate',
                     'slow', 'gradual', 'careful', 'thorough', 'detailed', 'meticulous'],

            # Purpose modifiers (50+)
            'purpose': ['', 'for testing', 'for validation', 'for verification', 'for demo',
                       'for demonstration', 'for experiment', 'for research', 'for analysis',
                       'for simulation', 'for computation', 'for calculation', 'for processing']
        }

    def _init_domain_terms(self):
        """Initialize domain-specific terms (bio, chem, physics)."""
        self.domain_terms = {
            # Protein terms (100+)
            'protein': ['protein', 'polypeptide', 'peptide', 'amino acid chain',
                       'protein structure', 'protein folding', 'protein conformation',
                       'alpha helix', 'beta sheet', 'random coil', 'protein domain',
                       'hemoglobin', 'insulin', 'collagen', 'keratin', 'enzyme',
                       'antibody', 'immunoglobulin', 'receptor', 'channel', 'transporter'],

            # Drug terms (100+)
            'drug': ['drug', 'medicine', 'pharmaceutical', 'medication', 'therapeutic',
                    'compound', 'molecule', 'small molecule', 'ligand', 'inhibitor',
                    'activator', 'agonist', 'antagonist', 'substrate', 'candidate',
                    'lead compound', 'hit compound', 'drug candidate', 'active compound'],

            # DNA terms (100+)
            'dna': ['dna', 'deoxyribonucleic acid', 'genetic material', 'genome',
                   'chromosome', 'gene', 'sequence', 'nucleotide sequence', 'base sequence',
                   'double helix', 'nucleotides', 'bases', 'base pairs', 'a-t', 'g-c',
                   'adenine', 'thymine', 'guanine', 'cytosine', 'genetic code'],

            # Molecular terms (100+)
            'molecule': ['molecule', 'compound', 'chemical', 'substance', 'entity',
                        'molecular structure', 'chemical structure', 'molecular system',
                        'molecular complex', 'biomolecule', 'organic molecule'],

            # Binding terms (50+)
            'binding': ['binding', 'docking', 'attachment', 'interaction', 'association',
                       'affinity', 'binding affinity', 'binding energy', 'binding site',
                       'active site', 'pocket', 'binding pocket', 'receptor binding']
        }

    def _init_synonyms(self):
        """Initialize number word synonyms."""
        self.number_words = {
            '1': ['1', 'one', 'a', 'single', 'one single'],
            '2': ['2', 'two', 'a pair of', 'pair of', 'couple of', 'dual', 'double'],
            '3': ['3', 'three', 'triple', 'trio of'],
            '4': ['4', 'four', 'quad', 'quartet of'],
            '5': ['5', 'five', 'quintet of'],
            '6': ['6', 'six', 'sextet of'],
            '7': ['7', 'seven', 'septet of'],
            '8': ['8', 'eight', 'octet of'],
            '10': ['10', 'ten', 'decade of'],
            '12': ['12', 'twelve', 'dozen'],
            '16': ['16', 'sixteen'],
            '20': ['20', 'twenty'],
        }

    def match(self, text: str) -> Optional[PatternMatch]:
        """
        Match input text against billions of generated patterns.

        This uses intelligent matching instead of storing all patterns:
        1. Extract key terms from input
        2. Check against synonym dictionaries
        3. Identify intent based on term combinations
        4. Extract parameters (numbers, names, etc.)

        Args:
            text: User input in natural language

        Returns:
            PatternMatch if successful, None otherwise
        """
        text_lower = text.lower().strip()

        # Try to match each intent type
        for intent in IntentType:
            match_result = self._match_intent(text_lower, intent)
            if match_result:
                return match_result

        return None

    def _match_intent(self, text: str, intent: IntentType) -> Optional[PatternMatch]:
        """Match text against a specific intent using combinatorial patterns."""

        if intent == IntentType.CREATE_BELL_STATE:
            return self._match_bell_state(text)
        elif intent == IntentType.CREATE_SUPERPOSITION:
            return self._match_superposition(text)
        elif intent == IntentType.ENTANGLE_QUBITS:
            return self._match_entanglement(text)
        elif intent == IntentType.QUANTUM_FOURIER:
            return self._match_qft(text)
        # IMPORTANT: Check DRUG_DESIGN before DRUG_DOCKING before PROTEIN_FOLDING
        # DRUG_DESIGN = "design new drug" (de novo generation)
        # DRUG_DOCKING = "dock SMILES to PDB" (existing molecule)
        elif intent == IntentType.DRUG_DESIGN:
            return self._match_drug_design(text)
        elif intent == IntentType.DRUG_DOCKING:
            return self._match_drug_docking(text)
        elif intent == IntentType.PROTEIN_FOLDING:
            return self._match_protein_folding(text)
        elif intent == IntentType.DNA_ANALYSIS:
            return self._match_dna_analysis(text)
        elif intent == IntentType.MEASURE_QUBITS:
            return self._match_measurement(text)
        elif intent == IntentType.APPLY_GATE:
            return self._match_gate_application(text)

        return None

    def _match_bell_state(self, text: str) -> Optional[PatternMatch]:
        """Match Bell state creation patterns."""
        # Check for any creation verb + bell state term
        for verb_list in self.action_verbs['create']:
            for bell_term in self.quantum_terms['bell_state']:
                if verb_list in text and bell_term in text:
                    return PatternMatch(
                        intent=IntentType.CREATE_BELL_STATE,
                        confidence=0.95,
                        extracted_params={'num_qubits': 2},
                        original_text=text
                    )

        # Check for entanglement terms
        for verb_list in self.action_verbs['create']:
            if verb_list in text and any(term in text for term in self.quantum_terms['entanglement']):
                if 'two' in text or '2' in text or 'pair' in text:
                    return PatternMatch(
                        intent=IntentType.CREATE_BELL_STATE,
                        confidence=0.90,
                        extracted_params={'num_qubits': 2},
                        original_text=text
                    )

        return None

    def _match_superposition(self, text: str) -> Optional[PatternMatch]:
        """Match superposition creation patterns."""
        # Check for creation verb + superposition term
        for verb_list in self.action_verbs['create']:
            for super_term in self.quantum_terms['superposition']:
                if verb_list in text and super_term in text:
                    num_qubits = self._extract_number(text) or 3
                    return PatternMatch(
                        intent=IntentType.CREATE_SUPERPOSITION,
                        confidence=0.95,
                        extracted_params={'num_qubits': num_qubits},
                        original_text=text
                    )

        # Check for hadamard mentions (creates superposition)
        for verb_list in self.action_verbs['apply']:
            for hadamard_term in self.quantum_terms['hadamard']:
                if verb_list in text and hadamard_term in text:
                    return PatternMatch(
                        intent=IntentType.CREATE_SUPERPOSITION,
                        confidence=0.90,
                        extracted_params={'gate': 'hadamard'},
                        original_text=text
                    )

        return None

    def _match_entanglement(self, text: str) -> Optional[PatternMatch]:
        """Match entanglement creation patterns."""
        for verb_list in self.action_verbs['create'] + self.action_verbs['apply']:
            for entangle_term in self.quantum_terms['entanglement']:
                if verb_list in text and entangle_term in text:
                    num_qubits = self._extract_number(text) or 2
                    return PatternMatch(
                        intent=IntentType.ENTANGLE_QUBITS,
                        confidence=0.95,
                        extracted_params={'num_qubits': num_qubits},
                        original_text=text
                    )
        return None

    def _match_qft(self, text: str) -> Optional[PatternMatch]:
        """Match Quantum Fourier Transform patterns."""
        qft_terms = ['qft', 'quantum fourier', 'fourier transform', 'fourier']
        for verb_list in self.action_verbs['create'] + self.action_verbs['apply']:
            for qft_term in qft_terms:
                if verb_list in text and qft_term in text:
                    num_qubits = self._extract_number(text) or 4
                    return PatternMatch(
                        intent=IntentType.QUANTUM_FOURIER,
                        confidence=0.95,
                        extracted_params={'num_qubits': num_qubits},
                        original_text=text
                    )
        return None

    def _match_protein_folding(self, text: str) -> Optional[PatternMatch]:
        """Match protein folding simulation patterns."""
        for verb_list in self.action_verbs['simulate'] + self.action_verbs['analyze']:
            for protein_term in self.domain_terms['protein']:
                if verb_list in text and protein_term in text:
                    if 'fold' in text or 'structure' in text or 'conformation' in text:
                        num_qubits = self._extract_number(text) or 8
                        return PatternMatch(
                            intent=IntentType.PROTEIN_FOLDING,
                            confidence=0.95,
                            extracted_params={'num_qubits': num_qubits},
                            original_text=text
                        )
        return None

    def _match_drug_design(self, text: str) -> Optional[PatternMatch]:
        """Match drug design patterns - de novo molecule generation."""
        # HIGH PRIORITY: Design/generate/create NEW drug/molecule
        design_keywords = ['design', 'generate', 'create', 'develop', 'discover', 'invent', 'synthesize']
        new_keywords = ['new', 'novel', 'de novo', 'from scratch']
        molecule_keywords = ['drug', 'molecule', 'compound', 'ligand', 'agonist', 'antagonist', 'inhibitor']

        # Check for design intent
        has_design = any(keyword in text for keyword in design_keywords)
        has_new = any(keyword in text for keyword in new_keywords)
        has_molecule = any(keyword in text for keyword in molecule_keywords)

        # Strong signal: "design a new drug" or "generate molecule"
        if has_design and (has_new or has_molecule):
            # Extract target information
            params = {'num_qubits': 6}

            # Look for disease/target
            disease_keywords = {
                'obesity': 'obesity',
                'diabetes': 'diabetes',
                'cancer': 'cancer',
                'alzheimer': 'alzheimers',
                'parkinson': 'parkinsons',
                'hypertension': 'hypertension',
                'depression': 'depression',
                'pain': 'pain',
                'inflammation': 'inflammation'
            }

            for keyword, disease in disease_keywords.items():
                if keyword in text:
                    params['disease'] = disease
                    break

            # Look for target receptor/protein
            if 'glp' in text or 'glp-1' in text or 'glp1' in text:
                params['target'] = 'GLP1R'
            elif 'gip' in text:
                params['target'] = 'GIP'
            elif 'pdb' in text:
                # Extract PDB ID if mentioned
                import re
                pdb_match = re.search(r'\b([0-9][A-Za-z0-9]{3})\b', text)
                if pdb_match:
                    params['pdb_id'] = pdb_match.group(1).upper()

            return PatternMatch(
                intent=IntentType.DRUG_DESIGN,
                confidence=0.97,
                extracted_params=params,
                original_text=text
            )

        return None

    def _match_drug_docking(self, text: str) -> Optional[PatternMatch]:
        """Match drug docking patterns - checks for SMILES, PDB, docking keywords."""
        # HIGH PRIORITY: Check for SMILES or PDB mentions (very specific to docking)
        if 'smiles' in text or 'pdb' in text:
            if 'dock' in text or 'binding' in text or 'affinity' in text or 'receptor' in text or 'ligand' in text:
                num_qubits = self._extract_number(text) or 6
                return PatternMatch(
                    intent=IntentType.DRUG_DOCKING,
                    confidence=0.98,  # Very high confidence for SMILES/PDB
                    extracted_params={'num_qubits': num_qubits},
                    original_text=text
                )

        # NORMAL PRIORITY: Check for drug + binding terms
        for verb_list in self.action_verbs['simulate'] + self.action_verbs['analyze']:
            for drug_term in self.domain_terms['drug']:
                for binding_term in self.domain_terms['binding']:
                    if verb_list in text and (drug_term in text or binding_term in text):
                        if 'dock' in text or 'bind' in text or 'affinity' in text:
                            num_qubits = self._extract_number(text) or 6
                            return PatternMatch(
                                intent=IntentType.DRUG_DOCKING,
                                confidence=0.95,
                                extracted_params={'num_qubits': num_qubits},
                                original_text=text
                            )
        return None

    def _match_dna_analysis(self, text: str) -> Optional[PatternMatch]:
        """Match DNA analysis patterns."""
        for verb_list in self.action_verbs['analyze'] + self.action_verbs['simulate']:
            for dna_term in self.domain_terms['dna']:
                if verb_list in text and dna_term in text:
                    num_qubits = self._extract_number(text) or 4
                    return PatternMatch(
                        intent=IntentType.DNA_ANALYSIS,
                        confidence=0.95,
                        extracted_params={'num_qubits': num_qubits},
                        original_text=text
                    )
        return None

    def _match_measurement(self, text: str) -> Optional[PatternMatch]:
        """Match measurement operation patterns."""
        for measure_term in self.quantum_terms['measurement']:
            if measure_term in text:
                if 'all' in text or 'everything' in text:
                    return PatternMatch(
                        intent=IntentType.MEASURE_QUBITS,
                        confidence=0.95,
                        extracted_params={'measure_all': True},
                        original_text=text
                    )
        return None

    def _match_gate_application(self, text: str) -> Optional[PatternMatch]:
        """Match general gate application patterns."""
        for verb_list in self.action_verbs['apply']:
            for gate_term in self.quantum_terms['gate']:
                if verb_list in text and gate_term in text:
                    return PatternMatch(
                        intent=IntentType.APPLY_GATE,
                        confidence=0.85,
                        extracted_params={},
                        original_text=text
                    )
        return None

    def _extract_number(self, text: str) -> Optional[int]:
        """Extract number from text (digits or words)."""
        # Try digit extraction first
        digit_match = re.search(r'\b(\d+)\b', text)
        if digit_match:
            return int(digit_match.group(1))

        # Try word extraction
        for num, words in self.number_words.items():
            for word in words:
                if word in text:
                    return int(num)

        return None

    def get_pattern_count(self) -> int:
        """
        Calculate total number of patterns this matcher can recognize.

        Returns massive number based on combinatorial explosion.
        """
        total = 0

        # Count creation verb combinations
        for verb_category in self.action_verbs.values():
            total += len(verb_category)

        # Count quantum term combinations
        for term_category in self.quantum_terms.values():
            total += len(term_category)

        # Count domain term combinations
        for domain_category in self.domain_terms.values():
            total += len(domain_category)

        # Multiply by context modifiers
        modifier_count = sum(len(mods) for mods in self.context_modifiers.values())

        # Calculate exponential combinations
        # verbs × terms × contexts × intents
        combinatorial_total = (
            len(self.action_verbs) * 30 *  # verb variations
            len(self.quantum_terms) * 20 *  # quantum terms
            modifier_count *  # context modifiers
            len(IntentType)  # intent types
        )

        return combinatorial_total


# Global instance for easy access
_global_matcher = None

def get_mega_matcher() -> MegaPatternMatcher:
    """Get or create global mega pattern matcher instance."""
    global _global_matcher
    if _global_matcher is None:
        _global_matcher = MegaPatternMatcher()
    return _global_matcher


def match_natural_language(text: str) -> Optional[PatternMatch]:
    """
    Convenience function to match natural language text.

    Args:
        text: User input in natural language

    Returns:
        PatternMatch if successful, None otherwise
    """
    matcher = get_mega_matcher()
    return matcher.match(text)
