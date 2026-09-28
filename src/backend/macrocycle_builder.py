"""
Construcción de macrociclos peptídicos: secuencia -> estructura química real.

Por qué existe este módulo. Todo el repo convierte secuencia en molécula con
`Chem.MolFromSequence`, que solo sabe de péptidos LINEALES de L-aminoácidos
canónicos. No puede expresar un macrociclo, ni una N-metilación, ni un
D-aminoácido, ni Aib, que son exactamente las cuatro cosas de las que vive la
química de macrociclos. Y lo que había de ciclación en el backend era papel:
`mutation_operators.py` declara `'lactam_cyclization'` en un diccionario sin
SMARTS que lo implemente, y `iterative_optimizer.py` con `strategy == "staple"`
no hace un staple -- inserta una K y una E en la cadena de texto.

Así que aquí se construye la molécula átomo a átomo desde plantillas de residuo,
y el cierre del anillo es un enlace de verdad, comprobado.

LA INVARIANTE GEOMÉTRICA, medida y no supuesta
----------------------------------------------
En el orden de átomos del esqueleto peptídico -- N, CA, cadena lateral, C(=O) --
la etiqueta `@@` es la configuración L y `@` es la D:

    N[C@@H](C)C(=O)O   -> CIP S   = L-Ala
    N[C@H](C)C(=O)O    -> CIP R   = D-Ala

El CIP **no** es constante entre residuos: L-Cys sale R porque el azufre gana
prioridad, mientras L-Ala, L-Ser y L-Thr salen S. Por eso la configuración se
declara por geometría (la etiqueta en un orden fijo) y el CIP se *registra* como
consecuencia, en vez de afirmarse. Verificado contra Ala/Ser/Cys/Thr; el test
`test_macrocycle_builder.py` lo vuelve a comprobar en cada corrida.

Numeración de cierres: las cadenas laterales aromáticas (Phe, Trp, His, Tyr) ya
usan los dígitos 1-3, así que los cierres del macrociclo van con `%90` y arriba y
no pueden colisionar.

MOLEVERA / BIOQL
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    _RDKIT = True
except Exception:  # pragma: no cover - RDKit es obligatorio en el venv del backend
    _RDKIT = False


# ── residuos ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ResidueTemplate:
    """Un residuo tal como entra en la cadena.

    `side` es la cadena lateral colgada de CA. `achiral` marca los que no tienen
    centro en CA (Gly, Aib). `ring_to_n` marca los que cierran sobre el propio N
    del esqueleto (Pro), que se escriben distinto.
    """

    code: str
    name: str
    side: str
    achiral: bool = False
    ring_to_n: bool = False
    # átomos de la cadena lateral que pueden anclar un cierre, por tipo
    anchors: Dict[str, str] = field(default_factory=dict)


# Los 20 canónicos. La cadena lateral se escribe tal cual cuelga de CA.
_NATURAL: Dict[str, Tuple[str, str]] = {
    "A": ("Ala", "C"),
    "R": ("Arg", "CCCNC(=N)N"),
    "N": ("Asn", "CC(=O)N"),
    "D": ("Asp", "CC(=O)O"),
    "C": ("Cys", "CS"),
    "E": ("Glu", "CCC(=O)O"),
    "Q": ("Gln", "CCC(=O)N"),
    "G": ("Gly", ""),
    "H": ("His", "Cc1c[nH]cn1"),
    "I": ("Ile", "[C@@H](C)CC"),
    "L": ("Leu", "CC(C)C"),
    "K": ("Lys", "CCCCN"),
    "M": ("Met", "CCSC"),
    "F": ("Phe", "Cc1ccccc1"),
    "P": ("Pro", "CCC"),
    "S": ("Ser", "CO"),
    "T": ("Thr", "[C@@H](C)O"),
    "W": ("Trp", "Cc1c[nH]c2ccccc12"),
    "Y": ("Tyr", "Cc1ccc(O)cc1"),
    "V": ("Val", "C(C)C"),
}

# Anclas de cierre por residuo: qué átomo de la cadena lateral puede formar el
# enlace, y de qué tipo. Se usa para lactamas laterales, disulfuros y tioéteres.
_ANCHORS: Dict[str, Dict[str, str]] = {
    "K": {"amine": "CCCCN"},  # NZ
    "C": {"thiol": "CS"},  # SG
    "D": {"acid": "CC(=O)O"},  # OD
    "E": {"acid": "CCC(=O)O"},  # OE
}

RESIDUES: Dict[str, ResidueTemplate] = {}
for _c, (_n, _s) in _NATURAL.items():
    RESIDUES[_c] = ResidueTemplate(
        code=_c,
        name=_n,
        side=_s,
        achiral=(_c == "G"),
        ring_to_n=(_c == "P"),
        anchors=_ANCHORS.get(_c, {}),
    )

# No naturales de uso corriente en macrociclos.
RESIDUES["Aib"] = ResidueTemplate(code="Aib", name="Aib", side="C", achiral=True)


@dataclass
class Residue:
    """Un residuo colocado en la cadena, con su estereoquímica y N-metilación."""

    code: str
    chirality: str = "L"  # "L" | "D" | "none"
    n_methyl: bool = False

    def template(self) -> ResidueTemplate:
        t = RESIDUES.get(self.code)
        if t is None:
            raise KeyError(f"residuo no conocido: {self.code!r}")
        return t


def parse_sequence(seq: str) -> List[Residue]:
    """Lee una secuencia con anotación.

        "ACDK"              -> cuatro L
        "A-D:F-K"           -> el prefijo `D:` marca D-aminoácido
        "A-NMe:F-K"         -> `NMe:` marca N-metilación
        "A-Aib-K"           -> código de tres letras para no naturales
        "A-D:NMe:F-K"       -> combinables

    Los residuos se separan por `-` cuando hay anotación; una cadena sin `-` se
    lee como una letra por residuo.
    """
    seq = (seq or "").strip()
    if not seq:
        return []
    if "-" not in seq and ":" not in seq:
        return [Residue(code=ch) for ch in seq if not ch.isspace()]
    out: List[Residue] = []
    for tok in seq.split("-"):
        tok = tok.strip()
        if not tok:
            continue
        chir, nme = "L", False
        while ":" in tok:
            pre, tok = tok.split(":", 1)
            pre = pre.strip().upper()
            if pre == "D":
                chir = "D"
            elif pre in ("NME", "N-ME", "NMETHYL"):
                nme = True
            else:
                raise ValueError(f"prefijo de residuo no conocido: {pre!r}")
        t = RESIDUES.get(tok)
        if t is None:
            raise KeyError(f"residuo no conocido: {tok!r}")
        out.append(Residue(code=tok, chirality="none" if t.achiral else chir, n_methyl=nme))
    return out


# ── escritura del esqueleto ───────────────────────────────────────────────────
def _residue_smiles(r: Residue, *, n_open: str = "", c_close: str = "") -> str:
    """Un residuo en SMILES: N, CA (+lateral), carbonilo.

    `n_open` y `c_close` son dígitos de cierre de anillo que se pegan al N o al
    carbono del carbonilo cuando ese residuo participa en la ciclación.
    """
    t = r.template()

    if t.ring_to_n:  # prolina: la lateral vuelve al N
        if r.n_methyl:
            raise ValueError("la prolina no admite N-metilación: su N ya está sustituido")
        tag = "@@" if r.chirality != "D" else "@"
        return f"N{n_open}9{t.side}[C{tag}H]9C{c_close}(=O)"

    n_part = f"N{n_open}(C)" if r.n_methyl else f"N{n_open}"

    if t.achiral:
        if t.code == "G":
            return f"{n_part}C{'' if not t.side else t.side}C{c_close}(=O)"
        # Aib y análogos: CA con dos sustituyentes iguales, sin centro
        return f"{n_part}C({t.side})({t.side})C{c_close}(=O)"

    tag = "@@" if r.chirality != "D" else "@"
    return f"{n_part}[C{tag}H]({t.side})C{c_close}(=O)"


CYCLIZATIONS = ("head_to_tail", "sidechain_to_tail", "disulfide", "thioether")


@dataclass
class MacrocycleSpec:
    """Lo que sale del constructor, con todo lo necesario para poder comprobarlo."""

    smiles: str
    sequence: str
    residues: List[Residue]
    cyclization: str
    ring_size: Optional[int] = None
    ring_atoms: List[int] = field(default_factory=list)
    stereo: List[Dict[str, Any]] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "smiles": self.smiles,
            "sequence": self.sequence,
            "cyclization": self.cyclization,
            "ring_size": self.ring_size,
            "ring_atoms": self.ring_atoms,
            "stereo": self.stereo,
            "provenance": self.provenance,
            "content_hash": self.content_hash,
        }


def build_linear(residues: List[Residue]) -> str:
    """Péptido lineal, N-terminal libre y C-terminal ácido."""
    if not residues:
        raise ValueError("no se recibió ningún residuo")
    return "".join(_residue_smiles(r) for r in residues) + "O"


def build_macrocycle(
    sequence: str,
    cyclization: str = "head_to_tail",
    *,
    anchor_i: Optional[int] = None,
    anchor_j: Optional[int] = None,
) -> MacrocycleSpec:
    """Construye el macrociclo y devuelve su especificación comprobable.

    `anchor_i`/`anchor_j` son índices de residuo (base 0) para las ciclaciones
    que no son head-to-tail: el par de cisteínas del disulfuro, o la lisina que
    forma la lactama con el C-terminal.
    """
    if cyclization not in CYCLIZATIONS:
        raise ValueError(f"ciclación no conocida: {cyclization!r}; conocidas: {CYCLIZATIONS}")
    residues = parse_sequence(sequence)
    if len(residues) < 2:
        raise ValueError("un macrociclo necesita al menos 2 residuos")

    if cyclization == "head_to_tail":
        parts = [
            _residue_smiles(
                r, n_open="%90" if i == 0 else "", c_close="%90" if i == len(residues) - 1 else ""
            )
            for i, r in enumerate(residues)
        ]
        smiles = "".join(parts)
    elif cyclization == "disulfide":
        i, j = _pick_pair(residues, "C", anchor_i, anchor_j, "disulfuro")
        smiles = _with_side_closure(residues, {i: ("thiol", "%90"), j: ("thiol", "%90")})
    elif cyclization == "thioether":
        i, j = _pick_pair(residues, "C", anchor_i, anchor_j, "tioéter")
        # puente -S-CH2-C(=O)- entre las dos laterales
        smiles = _with_side_closure(residues, {i: ("thiol", "%90"), j: ("thiol_ch2co", "%90")})
    else:  # sidechain_to_tail: lactama lisina -> C-terminal
        i = _pick_single(residues, "K", anchor_i, "lactama lateral")
        parts = []
        for k, r in enumerate(residues):
            if k == i:
                parts.append(_side_anchored(r, "amine", "%90"))
            elif k == len(residues) - 1:
                parts.append(_residue_smiles(r, c_close="%90"))
            else:
                parts.append(_residue_smiles(r))
        smiles = "".join(parts)

    spec = MacrocycleSpec(
        smiles=smiles,
        sequence=sequence,
        residues=residues,
        cyclization=cyclization,
        provenance={"builder": "macrocycle_builder", "version": 1},
    )
    _annotate(spec)
    return spec


def _pick_pair(residues, code, i, j, what) -> Tuple[int, int]:
    if i is not None and j is not None:
        for k in (i, j):
            if residues[k].code != code:
                raise ValueError(f"{what}: el residuo {k} es {residues[k].code}, no {code}")
        return int(i), int(j)
    found = [k for k, r in enumerate(residues) if r.code == code]
    if len(found) < 2:
        raise ValueError(f"{what}: hacen falta dos {code} en la secuencia y hay {len(found)}")
    if len(found) > 2:
        raise ValueError(
            f"{what}: hay {len(found)} {code} en la secuencia; indica cuáles con "
            f"anchor_i/anchor_j en vez de dejarlo a la suerte"
        )
    return found[0], found[1]


def _pick_single(residues, code, i, what) -> int:
    if i is not None:
        if residues[i].code != code:
            raise ValueError(f"{what}: el residuo {i} es {residues[i].code}, no {code}")
        return int(i)
    found = [k for k, r in enumerate(residues) if r.code == code]
    if not found:
        raise ValueError(f"{what}: no hay ningún {code} en la secuencia")
    if len(found) > 1:
        raise ValueError(f"{what}: hay {len(found)} {code}; indica cuál con anchor_i")
    return found[0]


def _side_anchored(r: Residue, kind: str, digit: str) -> str:
    """El residuo con el dígito de cierre pegado al átomo de su cadena lateral."""
    t = r.template()
    if kind == "amine":  # NZ de lisina
        side = t.side[:-1] + f"N{digit}"
    elif kind == "thiol":  # SG de cisteína
        side = t.side[:-1] + f"S{digit}"
    elif kind == "thiol_ch2co":  # SG que además lleva el puente CH2-CO
        side = t.side[:-1] + f"SCC{digit}(=O)"
    else:
        raise ValueError(f"ancla no conocida: {kind!r}")
    tag = "@@" if r.chirality != "D" else "@"
    n_part = "N(C)" if r.n_methyl else "N"
    if t.achiral:
        return f"{n_part}C({side})C(=O)"
    return f"{n_part}[C{tag}H]({side})C(=O)"


def _with_side_closure(residues: List[Residue], closures: Dict[int, Tuple[str, str]]) -> str:
    parts = []
    for k, r in enumerate(residues):
        if k in closures:
            kind, digit = closures[k]
            parts.append(_side_anchored(r, kind, digit))
        else:
            parts.append(_residue_smiles(r))
    return "".join(parts) + "O"


# ── comprobación: el anillo existe y la estereoquímica es la pedida ───────────
def _annotate(spec: MacrocycleSpec) -> None:
    """Rellena ring_size, ring_atoms, stereo y el hash, leyéndolos de la molécula."""
    if not _RDKIT:
        return
    mol = Chem.MolFromSmiles(spec.smiles)
    if mol is None:
        return
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)
    ri = mol.GetRingInfo()
    # el macrociclo es el anillo más grande; las laterales aromáticas son de 5-6
    rings = [r for r in ri.AtomRings() if len(r) > 8]
    if rings:
        big = max(rings, key=len)
        spec.ring_size = len(big)
        spec.ring_atoms = sorted(big)
    spec.stereo = [
        {"atom": a.GetIdx(), "cip": a.GetPropsAsDict().get("_CIPCode")}
        for a in mol.GetAtoms()
        if a.HasProp("_CIPCode")
    ]
    spec.content_hash = hashlib.sha256(
        (Chem.MolToSmiles(mol) + "|" + spec.cyclization).encode()
    ).hexdigest()[:16]


def verify_ring(spec: MacrocycleSpec) -> Dict[str, Any]:
    """¿Existe de verdad el macrociclo?  (modo de fallo F-1)

    Un SMILES cuyo cierre RDKit sanea deja un péptido LINEAL que sigue
    calculando descriptores, dockeando y puntuando como si fuera un macrociclo.
    Aquí se comprueba contra la molécula, no contra la intención.
    """
    if not _RDKIT:
        return {"ok": False, "reason": "RDKit no disponible"}
    mol = Chem.MolFromSmiles(spec.smiles)
    if mol is None:
        return {"ok": False, "reason": "el SMILES no es una molécula válida"}
    rings = [r for r in mol.GetRingInfo().AtomRings() if len(r) > 8]
    if not rings:
        return {
            "ok": False,
            "reason": "no hay ningún anillo de más de 8 átomos: el ciclo no cerró",
            "n_rings": mol.GetRingInfo().NumRings(),
        }
    big = max(rings, key=len)
    n_res = len(spec.residues)
    esperado = 3 * n_res if spec.cyclization == "head_to_tail" else None
    out: Dict[str, Any] = {
        "ok": True,
        "ring_size": len(big),
        "n_macrocycles": len(rings),
        "n_residues": n_res,
    }
    if esperado is not None:
        out["expected_ring_size"] = esperado
        out["ok"] = len(big) == esperado
        if not out["ok"]:
            out["reason"] = (
                f"el anillo mide {len(big)} átomos y un head-to-tail de {n_res} "
                f"residuos tiene que medir {esperado} (N, CA y C por residuo)"
            )
    return out


def verify_stereo(spec: MacrocycleSpec) -> Dict[str, Any]:
    """¿Sobrevivió la estereoquímica?  (modo de fallo F-2)

    Cuenta los centros declarados por la secuencia y los compara con los que la
    molécula realmente tiene asignados. Un D-aminoácido que vuelve como L es otra
    molécula, y ningún número del pipeline lo delata.
    """
    if not _RDKIT:
        return {"ok": False, "reason": "RDKit no disponible"}
    mol = Chem.MolFromSmiles(spec.smiles)
    if mol is None:
        return {"ok": False, "reason": "el SMILES no es una molécula válida"}
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)
    asignados = sum(1 for a in mol.GetAtoms() if a.HasProp("_CIPCode"))
    sin_asignar = (
        len(Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False))
        - asignados
    )
    # un centro por residuo quiral, más los que trae la propia cadena lateral
    esperados = sum(1 for r in spec.residues if not r.template().achiral)
    return {
        "ok": sin_asignar == 0 and asignados >= esperados,
        "declared_centers": esperados,
        "assigned_centers": asignados,
        "unassigned_centers": sin_asignar,
        "reason": (
            ""
            if sin_asignar == 0 and asignados >= esperados
            else f"{sin_asignar} centro(s) sin asignar y {asignados} asignados frente a "
            f"{esperados} residuos quirales declarados"
        ),
    }


def roundtrip_stereo(spec: MacrocycleSpec) -> Dict[str, Any]:
    """El viaje completo SMILES -> mol -> SDF -> mol, que es donde se pierde.

    Es el paso que el pipeline hará de todos modos al embeber en 3D y escribir
    poses, así que se comprueba aquí antes de que nadie construya nada encima.
    """
    if not _RDKIT:
        return {"ok": False, "reason": "RDKit no disponible"}
    m1 = Chem.MolFromSmiles(spec.smiles)
    if m1 is None:
        return {"ok": False, "reason": "el SMILES no es una molécula válida"}
    Chem.AssignStereochemistry(m1, cleanIt=True, force=True)
    antes = {
        a.GetIdx(): a.GetPropsAsDict().get("_CIPCode")
        for a in m1.GetAtoms()
        if a.HasProp("_CIPCode")
    }

    sdf = Chem.MolToMolBlock(m1)
    m2 = Chem.MolFromMolBlock(sdf)
    if m2 is None:
        return {"ok": False, "reason": "el bloque SDF no se pudo releer"}
    Chem.AssignStereochemistry(m2, cleanIt=True, force=True)
    despues = {
        a.GetIdx(): a.GetPropsAsDict().get("_CIPCode")
        for a in m2.GetAtoms()
        if a.HasProp("_CIPCode")
    }

    cambiados = [i for i in antes if antes.get(i) != despues.get(i)]
    return {
        "ok": not cambiados and len(antes) == len(despues),
        "centers_before": len(antes),
        "centers_after": len(despues),
        "changed": cambiados,
        "reason": (
            "" if not cambiados else f"{len(cambiados)} centro(s) cambiaron de CIP en el round-trip"
        ),
    }


def build_and_verify(sequence: str, cyclization: str = "head_to_tail", **kw) -> Dict[str, Any]:
    """Construye y devuelve la especificación junto a las tres comprobaciones.

    Nada aguas abajo debería aceptar un macrociclo cuyo `ring.ok` sea falso: eso
    es un péptido lineal con una etiqueta equivocada.
    """
    spec = build_macrocycle(sequence, cyclization, **kw)
    return {
        "spec": spec.to_dict(),
        "ring": verify_ring(spec),
        "stereo": verify_stereo(spec),
        "roundtrip": roundtrip_stereo(spec),
    }


# MOLEVERA / BIOQL
