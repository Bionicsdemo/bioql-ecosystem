import React from 'react';
import {
  C, mono, cardBox, mutedText, th, td, CardHeader, SectionHeader, StatTile, StatRow, Chip, fmt,
} from './cardKit';

// ──────────────────────────────────────────────────────────────────────────
// Macrociclos peptídicos.
//
// La tarjeta enseña primero lo que puede ir mal en silencio, porque en este
// pipeline los fallos no lanzan excepción: un anillo que no cerró sigue siendo
// un péptido lineal que calcula descriptores igual, y un ensemble que no
// convergió significa que el confórmero bioactivo pudo no estar nunca en la
// caja. Por eso la contabilidad de población y la convergencia salen arriba, no
// en una nota al pie.
//
// Regla que manda sobre el diseño de esta card: un escenario que no corrió NO
// se oculta. Se enseña con su razón, en amarillo, antes que cualquier número
// bonito. El hueco silencioso — la etapa que desaparece del informe como si
// nunca se hubiera pedido — es exactamente el fallo que este proyecto persigue.
// Y un valor ausente se pinta '—', nunca 0: un cero es una medida, un guion es
// la falta de ella.
//
// El orden es una PRIORIZACIÓN para ensayo. No se dockea salvo que llegue
// estructura, y los scores de docking de macrociclos correlacionan mal con
// afinidad medida incluso cuando se calculan.
// MOLEVERA / BIOQL
// ──────────────────────────────────────────────────────────────────────────

// ---- tipos del resultado ------------------------------------------------

type Maybe<T> = T | null | undefined;

/** Patrón que repite todo el pipeline: o hay dato, o hay razón. Nunca ninguno. */
interface Disponible {
  available?: boolean;
  reason?: string;
  reason_en?: string;
}

interface Descriptors {
  mw?: number; clogp?: number; hbd?: number; hba?: number;
  tpsa?: number; rotb?: number; n_heavy?: number; csp3?: number;
}

interface QuantumGate {
  modality?: string;
  quantum_relevant?: boolean;
  applies?: boolean;
  moieties?: { warheads?: string[]; metal_chelators?: string[] };
  quantum?: Maybe<string>;
  verdict?: string;
}

interface CandidateQuantum {
  applies?: boolean;
  reasons?: string[];
  places?: string[];
  gate?: QuantumGate;
  verdict?: string;
}

interface SynthBackends {
  rdkit?: boolean; sa_score?: boolean; np_score?: boolean;
  scscore?: boolean; aizynthfinder?: boolean; aizynth_configured?: boolean;
}

interface Synthesis extends Disponible {
  backends?: SynthBackends;
  sa_score?: Maybe<number>;
  np_score?: Maybe<number>;
  sc_score?: Maybe<number>;
  wall_seconds?: number;
  sa_interpretation_es?: string;
  sa_interpretation_en?: string;
  route?: Disponible;
  note_es?: string;
  note_en?: string;
  sequence?: string;
}

interface Composite {
  score?: Maybe<number>;
  weights?: Record<string, number>;
  components?: Record<string, Maybe<number>>;
  components_missing?: string[];
  renormalised_over?: number;
  note_es?: string;
  note_en?: string;
}

interface Candidate {
  rank: number;
  sequence: string;
  smiles?: string;
  cyclization?: string;
  ring_size: number | null;
  content_hash?: string;
  bro5_ok: boolean;
  bro5_violations: number;
  descriptors?: Descriptors;
  liabilities: number;
  n_conformers: number | null;
  ensemble_converged: boolean | null;
  quantum?: CandidateQuantum;
  synthesis?: Synthesis;
  composite?: Composite;
}

// Lo que el cuántico miró de verdad. No es la molécula: es el trozo que decide
// el cierre, recortado y capado, y la card lo dice porque un lector que vea
// "SQD" sin esto se creerá que se calculó el macrociclo entero.
interface Cluster {
  index?: number;
  anchor?: string; anchor_en?: string;
  why?: string; why_en?: string;
  atom_indices?: number[];
  available?: boolean;
  n_heavy_region?: number;
  n_caps?: number;
  charge?: number;
  n_electrons?: number;
}

interface Region {
  available?: boolean;
  anchor?: string; anchor_en?: string;
  why?: string; why_en?: string;
  n_heavy_region?: number;
  n_heavy_molecule?: number;
  n_heavy_in_clusters?: number;
  n_caps?: number;
  n_absorbed_to_repair_boundary?: number;
  charge?: number;
  n_electrons?: number;
  n_clusters?: number;
  n_clusters_rejected?: number;
  coverage?: number;
  n_coupling_bonds?: number;
  coupling_bonds?: number[][];
  radius_bonds?: number;
  disjoint?: boolean;
  caveat?: string; caveat_en?: string;
  clusters?: Cluster[];
}

/** Una energía por confórmero. `below_floor` es la que importa: por debajo del
 *  suelo diferencial el orden no es distinguible del ruido del método. */
interface QEnergy {
  conformer_id?: number;
  delta_ev?: number;
  method?: string;
  reference_id?: number;
  below_floor?: boolean;
  note?: string;
}

interface PerCluster {
  cluster?: number;
  anchor?: string; anchor_en?: string;
  n_heavy_region?: number;
  n_electrons?: number;
  method_used?: string;
  error?: Maybe<string>;
  deltas_ev?: number[];
  n_significant?: number;
}

interface QuantumResult {
  sequence: string;
  region?: Region;
  method_requested?: string;
  method_used?: string;
  reference_conformer?: number;
  unit?: string;
  differential_floor_ev?: number;
  energies?: QEnergy[];
  per_cluster?: PerCluster[];
  degradations?: string[];
  absolute_energies_emitted?: boolean;
  n_significant?: number;
  n_total?: number;
  n_clusters_used?: number;
  n_clusters_failed?: number;
  clusters_failed?: unknown[];
  coverage?: number;
  n_coupling_bonds?: number;
  wall_seconds?: number;
  honest_note?: string;
  honest_note_en?: string;
  n_conformers_quantum?: number;
  error?: string;
}

interface Budget {
  planned?: { gpu?: number; quantum?: number };
  achieved?: { gpu?: number; quantum?: number };
  seconds?: { gpu?: number; quantum?: number };
  candidates_skipped_by_triage?: number;
  candidates_sent_to_quantum?: number;
  deviation_from_target?: number;
  quantum_eligible_but_not_run?: number;
  note_es?: string;
  note_en?: string;
}

interface RingBucket { total?: number; failed?: number; failure_rate?: number }

interface StageBuild {
  requested?: number; built?: number; dropped?: number;
  drops?: Array<{ sequence?: string; reason?: string }>;
  note_es?: string; note_en?: string;
}

interface StageConformers {
  n_conformers_requested?: number;
  population?: {
    ok?: boolean; n_in?: number; n_out?: number; n_dropped?: number;
    dropped_without_reason?: number; reasons?: string[]; note?: string;
  };
  failure_by_ring?: {
    by_cyclization_and_ring?: Record<string, RingBucket>;
    worst?: RingBucket & { key?: string };
  };
  convergence?: { n_with_curve?: number; n_not_converged?: number; note_es?: string; note_en?: string };
  note_es?: string; note_en?: string;
}

interface StageProperties {
  space_es?: string; space_en?: string; why_es?: string; why_en?: string;
  n_within_bro5?: number; n_total?: number;
}

interface StageTriage {
  n_eligible?: number; n_classical_suffices?: number; places?: string[];
  note_es?: string; note_en?: string; budget?: Budget;
}

interface StageQuantumRun {
  requested?: boolean; n_eligible?: number; n_run?: number; n_skipped?: number;
  skipped?: Array<{ sequence: string; reason: string }>;
  conformer_plan?: Array<{ sequence?: string; n_conformers?: number; n_geometries?: number; calibrated?: boolean }>;
  seconds_per_geometry?: Maybe<number>;
  results?: QuantumResult[];
  differential_floor_ev?: number;
  note_es?: string; note_en?: string;
}

interface StageRank {
  ordered_by?: string;
  not_a_potency_prediction_es?: string;
  not_a_potency_prediction_en?: string;
}

interface StageAdmet extends Disponible {
  engine?: string;
  wall_seconds?: number;
  note_es?: string; note_en?: string;
}

interface StageSynthesis {
  n_scored?: number;
  per_candidate?: Synthesis[];
  note_es?: string; note_en?: string;
}

interface SpeciesTox {
  species?: string;
  noael_mg_kg?: Maybe<number>;
  loael_mg_kg?: Maybe<number>;
  hed_mg_kg?: Maybe<number>;
  therapeutic_index?: Maybe<number>;
  therapeutic_index_note?: string;
  quantum_scaling_factor?: Maybe<number>;
  km_factor?: Maybe<number>;
  safety_margin?: Maybe<number>;
  safety_classification?: string;
  noael_estimated?: boolean;
  noael_disclaimer?: string;
}

interface CypEntry {
  species?: string;
  cyp_comparison?: Record<string, {
    species_activity?: number; human_activity?: number;
    ratio?: number; interpretation?: string;
  }>;
  overall_similarity?: number;
}

interface StageToxicology extends Disponible {
  module?: string;
  version?: string;
  smiles?: string;
  species_tested?: string[];
  molecular_features?: {
    mw?: number; logp?: number; tpsa?: number; hba?: number; hbd?: number;
    rotatable_bonds?: number; aromatic_rings?: number; heavy_atoms?: number; sp3_fraction?: number;
  };
  quantum_scaling?: {
    method?: string;
    is_real_hardware?: boolean;
    ibm_job_ids?: string[];
    scaling_factors?: Record<string, number>;
    species_detail?: Record<string, { body_weight_kg?: number; allometric_exponent?: number }>;
    n_species?: number;
    quantum_hardware?: boolean;
    honest_note?: string;
  };
  species_toxicology?: SpeciesTox[];
  cyp_comparison?: CypEntry[];
  allometric_summary?: {
    noaels_mg_kg?: Record<string, number>;
    heds_mg_kg?: Record<string, number>;
    most_sensitive_species?: string;
    most_conservative_hed?: Maybe<number>;
    recommended_starting_dose_mg_kg?: Maybe<number>;
    note?: string;
  };
  safety_assessment?: {
    human_predicted_noael?: Maybe<number>;
    human_therapeutic_index?: Maybe<number>;
    human_safety_class?: string;
    species_concordance?: {
      concordant?: Maybe<boolean>;
      classifications?: Record<string, string>;
      n_unique_classes?: Maybe<number>;
      note?: string;
    };
  };
  summary?: {
    n_species?: number; most_sensitive_species?: string;
    recommended_starting_dose?: Maybe<number>; human_safety_class?: string;
    quantum_hardware?: boolean; ibm_job_ids?: string[]; elapsed_seconds?: number;
  };
  wall_seconds?: number;
  note_es?: string; note_en?: string;
}

interface Validation {
  validated?: boolean;
  benchmark?: string;
  metrics?: {
    pearson_r?: number; primary_metric?: string; rmse?: number;
    rmse_units?: string; spearman?: number;
  };
  n?: number;
  source?: string;
  is_real?: boolean;
  partial?: boolean;
  timestamp?: string;
  badge?: string;
}

interface StagePk extends Disponible {
  engine?: string;
  validation?: Validation;
  clearance?: {
    smiles?: string;
    engine?: string;
    validation?: Validation;
    ivive_math?: {
      ivive_math_ok?: boolean; low_cl_limit_ok?: boolean; high_cl_limit_ok?: boolean;
      monotonic?: boolean; bounded_by_Qh?: boolean;
    };
    cl_int_invitro?: {
      smiles?: string; engine?: string; validation?: Validation;
      model_available?: boolean; clearance_log10?: number;
      clearance_uL_min_10e6cells?: number;
    };
    fraction_unbound?: { fu?: number; ppb_percent?: number; source?: string };
    ivive?: {
      cl_int_invitro_uL_min_10e6cells?: number; cl_int_whole_L_per_h?: number;
      fu_blood?: number; cl_hepatic_L_per_h?: number; hepatic_extraction_ratio?: number;
      blood_flow_limited?: boolean; model?: string;
      physiology?: { HPGL_10e6_per_g?: number; liver_g?: number; Q_hepatic_L_h?: number };
    };
    cl_hepatic_L_per_h?: number;
    hepatic_extraction_ratio?: number;
  };
  fraction_unbound?: Maybe<number>;
  cl_hepatic_L_per_h?: Maybe<number>;
  dose_mg?: Maybe<number>;
  profile?: Disponible;
  wall_seconds?: number;
  note_es?: string; note_en?: string;
}

interface PoseAtom { e?: string; p?: number[]; r?: number }

interface StageDocking {
  requested?: boolean;
  target_structure?: Disponible & {
    pdb_id?: string; source?: string; resolved_from?: string;
    receptor_chain?: string; chains_in_file?: string[];
    n_atoms_receptor?: number; n_atoms_dropped_other_chains?: number;
    n_hetatm_dropped?: number; prepared_es?: string; prepared_en?: string;
    n_site_reference_atoms?: number; wall_seconds?: number;
  };
  docking?: Disponible & {
    engine?: string; n_poses?: number; top_pose_sdf?: string; wall_seconds?: number;
    caveat_es?: string; caveat_en?: string;
    ligand_atoms?: PoseAtom[];
    complex_handoff?: {
      receptor_pdb?: string; ligand_sdf?: string; confidence?: Maybe<number>;
      source?: string; note?: string;
    };
    pocket_check?: Disponible & {
      cutoff_angstrom?: number; n_pose_atoms?: number; n_within_cutoff?: number;
      fraction_within_site?: number; centroid_separation_angstrom?: number;
      min_distance_angstrom?: number; max_distance_angstrom?: number;
      lands_in_site?: boolean; note_es?: string; note_en?: string;
    };
    sequence?: string;
  };
  affinity?: Disponible & { removed_scorer?: string; removed_scorer_en?: string };
  note_es?: string; note_en?: string;
}

interface StageComposite {
  weights?: Record<string, number>;
  scored?: Array<{ sequence?: string; score?: Maybe<number>; missing?: string[] }>;
  note_es?: string; note_en?: string;
}

interface Stages {
  '1_build'?: StageBuild;
  '2_conformers'?: StageConformers;
  '3_properties'?: StageProperties;
  '4_quantum_triage'?: StageTriage;
  '4b_quantum_run'?: StageQuantumRun;
  '5_rank'?: StageRank;
  '6_admet'?: StageAdmet;
  '7_synthesis'?: StageSynthesis;
  '8_toxicology'?: StageToxicology;
  '9_pharmacokinetics'?: StagePk;
  '10_docking'?: StageDocking;
  '11_composite_score'?: StageComposite;
}

interface Props {
  data: {
    pipeline?: string;
    status?: string;
    timestamp?: string;
    target?: string;
    indication?: string;
    cyclization?: string;
    quantum_backend?: string;
    stages?: Stages;
    candidates?: Candidate[];
    best_candidate?: Candidate;
    target_structure_pdb?: string;
    docking_pose_atoms?: PoseAtom[];
    elapsed_s?: number;
    _pipeline_session_id?: string;
    compute_budget?: Budget;
    disclaimer_es?: string;
    disclaimer_en?: string;
  };
}

// ---- primitivas locales, construidas sólo con tokens del kit -------------

/** Un booleano ausente no es 'no'. Por eso hay tres salidas, no dos. */
const sn = (v: Maybe<boolean>): string => (v === true ? 'sí' : v === false ? 'no' : '—');

/** Formatea con unidad sólo si hay valor; si no hay, el guion va solo y sin unidad,
 *  porque "— mg/kg" sugiere una medida de cero y no la hay. */
const unidad = (v: Maybe<number>, u: string): string =>
  v === null || v === undefined ? '—' : `${fmt(v)} ${u}`;

const pct = (v: Maybe<number>): string =>
  v === null || v === undefined ? '—' : `${Math.round(v * 100)}%`;

/** Bloque plegable. <details> nativo para que el contenido exista en el DOM y
 *  sea buscable aunque esté cerrado: plegar no es esconder. */
function Bloque({ titulo, resumen, abierto, children }: {
  titulo: string; resumen?: React.ReactNode; abierto?: boolean; children: React.ReactNode;
}) {
  return (
    <details open={abierto} style={{
      border: `1px solid ${C.line}`, borderRadius: 9, background: C.bg,
      padding: '7px 10px', marginTop: 8,
    }}>
      <summary style={{
        cursor: 'pointer', fontWeight: 700, color: C.primary, fontSize: 11.5,
        textTransform: 'uppercase', letterSpacing: 0.5,
      }}>
        {titulo}
        {resumen !== undefined && (
          <span style={{
            marginLeft: 8, color: C.muted, fontSize: 11, fontWeight: 500,
            textTransform: 'none', letterSpacing: 0, fontFamily: mono,
          }}>{resumen}</span>
        )}
      </summary>
      <div style={{ paddingTop: 8 }}>{children}</div>
    </details>
  );
}

/** Nota del pipeline. El castellano se lee; el inglés original queda a un clic
 *  para poder contrastar la traducción sin duplicar el muro de texto. */
function Nota({ es, en, aviso }: { es?: string; en?: string; aviso?: boolean }) {
  if (!es && !en) return null;
  return (
    <div style={{
      ...mutedText, borderLeft: `2px solid ${aviso ? C.amber : C.line}`,
      paddingLeft: 8, marginTop: 6,
    }}>
      {es || en}
      {es && en && (
        <details style={{ marginTop: 3 }}>
          <summary style={{ cursor: 'pointer', color: C.muted, fontSize: 10, fontFamily: mono }}>en</summary>
          <div style={{ marginTop: 3 }}>{en}</div>
        </details>
      )}
    </div>
  );
}

/** Etapa que no corrió. Va en amarillo y con la razón textual del backend:
 *  sin la razón, un `available: false` se lee como "no aplicaba", y casi nunca
 *  es eso — hoy suele ser infraestructura caída. */
function Ausente({ que, reason, reason_en, extra }: {
  que: string; reason?: string; reason_en?: string; extra?: React.ReactNode;
}) {
  return (
    <div style={{
      border: '1px solid #FCD34D', background: C.amberBg, borderRadius: 9,
      padding: '9px 11px', marginTop: 8,
    }}>
      <div style={{ fontWeight: 700, color: C.amber, fontSize: 12 }}>{que} · no disponible</div>
      <div style={{ ...mutedText, color: C.amber, fontFamily: mono, fontSize: 11 }}>
        {reason || 'el backend no registró razón — eso también es un fallo que hay que ver'}
      </div>
      {reason_en && (
        <details style={{ marginTop: 3 }}>
          <summary style={{ cursor: 'pointer', color: C.amber, fontSize: 10, fontFamily: mono }}>en</summary>
          <div style={{ ...mutedText, color: C.amber }}>{reason_en}</div>
        </details>
      )}
      {extra}
    </div>
  );
}

/** Tabla clave/valor. Todos los valores en mono para poder compararlos en vertical. */
function KV({ filas }: { filas: Array<[string, React.ReactNode]> }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
      <tbody>
        {filas.map(([k, v], i) => (
          <tr key={i}>
            <td style={{ ...td, color: C.muted, width: '48%' }}>{k}</td>
            <td style={{ ...td, fontFamily: mono }}>{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Badge de validación de un modelo. `is_real: false` o `partial: true` cambian
 *  el color: un modelo validado a medias no debe leerse igual que uno validado. */
function BadgeValidacion({ v, titulo }: { v?: Validation; titulo: string }) {
  if (!v) return null;
  const m = v.metrics || {};
  const bien = v.validated === true && v.is_real === true && v.partial !== true;
  return (
    <div style={{ marginTop: 6 }}>
      <Chip
        tone={bien ? 'ok' : v.validated ? 'warn' : 'bad'}
        text={`${titulo}: ${v.validated ? 'validado' : 'sin validar'}${v.partial ? ' (parcial)' : ''}${v.is_real === false ? ' (no real)' : ''}`}
      />
      <KV filas={[
        ['benchmark', v.benchmark || '—'],
        ['fuente (source)', v.source || '—'],
        ['métrica primaria (primary_metric)', m.primary_metric || '—'],
        ['spearman', fmt(m.spearman)],
        ['pearson_r', fmt(m.pearson_r)],
        ['rmse', m.rmse === undefined ? '—' : `${fmt(m.rmse)} ${m.rmse_units || ''}`.trim()],
        ['n', fmt(v.n)],
        ['fecha (timestamp)', v.timestamp || '—'],
        ['badge', v.badge || '—'],
      ]} />
    </div>
  );
}

// ---- componente ---------------------------------------------------------

export function MacrocycleCard({ data }: Props) {
  const cands = data.candidates || [];
  const stages: Stages = data.stages || {};
  const build = stages['1_build'] || {};
  const conf = stages['2_conformers'] || {};
  const props3 = stages['3_properties'] || {};
  const triage = stages['4_quantum_triage'] || {};
  const qrun = stages['4b_quantum_run'] || {};
  const rank = stages['5_rank'] || {};
  const admet = stages['6_admet'] || {};
  const synth = stages['7_synthesis'] || {};
  const tox = stages['8_toxicology'] || {};
  const pk = stages['9_pharmacokinetics'] || {};
  const dock = stages['10_docking'] || {};
  const comp = stages['11_composite_score'] || {};

  const pop = conf.population || {};
  const cvg = conf.convergence || {};
  const budget = data.compute_budget || triage.budget || {};
  const best = data.best_candidate;

  const noConverged = cvg.n_not_converged ?? 0;
  const withCurve = cvg.n_with_curve ?? 0;
  const worst = conf.failure_by_ring?.worst;
  const porAnillo = conf.failure_by_ring?.by_cyclization_and_ring || {};

  const ts = dock.target_structure;
  const dk = dock.docking;
  const pocket = dk?.pocket_check;
  const poseAtoms = data.docking_pose_atoms || [];
  const pdbChars = (data.target_structure_pdb || '').length;

  return (
    <div style={cardBox}>
      <CardHeader
        title={`Macrociclos · ${data.target || 'sin target'}`}
        badge={data.cyclization
          ? <span style={{ fontFamily: mono, fontSize: 11 }}>{String(data.cyclization).replace(/_/g, '-')}</span>
          : undefined}
      />

      {/* Procedencia de la corrida: sin esto dos cards idénticas son
          indistinguibles, y hace falta poder decir CUÁL se está mirando. */}
      <div style={{ ...mutedText, fontFamily: mono }}>
        {data.pipeline || 'macrocycle_design'} · estado: {data.status || '—'}
        {' · '}{data.timestamp || 'sin fecha'}
        {' · '}{unidad(data.elapsed_s, 's')}
        {data.indication ? ` · indicación: ${data.indication}` : ' · indicación: —'}
        {data._pipeline_session_id ? ` · sesión ${data._pipeline_session_id}` : ''}
      </div>
      <div style={{ ...mutedText, marginTop: 2 }}>
        backend cuántico: <b style={{ fontFamily: mono }}>{data.quantum_backend || '—'}</b>
      </div>

      {/* ────────── Lo que puede fallar en silencio, primero ────────── */}
      <SectionHeader>Integridad de la corrida</SectionHeader>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(130px,1fr))', gap: 8, marginBottom: 12 }}>
        <StatTile label="anillos cerrados" value={`${build.built ?? '—'} / ${build.requested ?? '—'}`} accent={(build.dropped ?? 0) > 0} />
        <StatTile label="población conservada" value={sn(pop.ok)} accent={pop.ok === false} />
        <StatTile label="ensembles sin converger" value={`${noConverged} / ${withCurve}`} accent={noConverged > 0} />
        <StatTile label="dentro de bRo5" value={`${props3.n_within_bro5 ?? '—'} / ${props3.n_total ?? '—'}`} />
      </div>

      {noConverged > 0 && (
        <div style={{ ...mutedText, borderLeft: `2px solid ${C.amber}`, paddingLeft: 8, marginBottom: 12 }}>
          {cvg.note_es ||
            `${noConverged} ensemble(s) seguían aportando confórmeros nuevos al parar de muestrear:
             su confórmero bioactivo puede no haber estado en la caja, y ese orden no es definitivo.`}
          {cvg.note_en && (
            <details style={{ marginTop: 3 }}>
              <summary style={{ cursor: 'pointer', color: C.muted, fontSize: 10, fontFamily: mono }}>en</summary>
              <div style={{ marginTop: 3 }}>{cvg.note_en}</div>
            </details>
          )}
        </div>
      )}

      <Bloque titulo="Construcción del anillo" resumen={`${build.built ?? '—'}/${build.requested ?? '—'} · ${build.dropped ?? 0} descartados`}>
        <KV filas={[
          ['pedidos (requested)', fmt(build.requested)],
          ['construidos (built)', fmt(build.built)],
          ['descartados (dropped)', fmt(build.dropped)],
        ]} />
        {(build.drops || []).length > 0 ? (
          <div style={{ marginTop: 6 }}>
            {(build.drops || []).map((d, i) => (
              <div key={i} style={{ ...mutedText, color: C.amber }}>
                <span style={{ fontFamily: mono }}>{d.sequence || '?'}</span> · {d.reason || 'sin razón'}
              </div>
            ))}
          </div>
        ) : (
          <div style={mutedText}>drops: ninguno — no se cayó ningún candidato en la construcción.</div>
        )}
        <Nota es={build.note_es} en={build.note_en} />
      </Bloque>

      <Bloque titulo="Confórmeros" resumen={`${conf.n_conformers_requested ?? '—'} pedidos por candidato`}>
        <KV filas={[
          ['confórmeros pedidos (n_conformers_requested)', fmt(conf.n_conformers_requested)],
          ['población: entran (n_in)', fmt(pop.n_in)],
          ['población: salen (n_out)', fmt(pop.n_out)],
          ['población: caídos (n_dropped)', fmt(pop.n_dropped)],
          ['caídos sin razón (dropped_without_reason)', fmt(pop.dropped_without_reason)],
          ['razones de caída (reasons)', (pop.reasons || []).length ? (pop.reasons || []).join('; ') : 'ninguna'],
          ['nota de población (note)', pop.note || '—'],
          ['ensembles con curva (n_with_curve)', fmt(withCurve)],
          ['ensembles sin converger (n_not_converged)', fmt(cvg.n_not_converged)],
        ]} />
        {/* El embebido no falla al azar: falla por tamaño de anillo. Enseñar el
            desglose es lo que permite saber si el fallo es del método o del anillo. */}
        <div style={{ ...mutedText, marginTop: 8, fontWeight: 700 }}>Fallo de embebido por anillo</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr><th style={th}>ciclación/anillo</th><th style={th}>total</th><th style={th}>failed</th><th style={th}>failure_rate</th></tr>
          </thead>
          <tbody>
            {Object.entries(porAnillo).map(([k, b]) => (
              <tr key={k}>
                <td style={{ ...td, fontFamily: mono }}>{k}</td>
                <td style={td}>{fmt(b.total)}</td>
                <td style={td}>{fmt(b.failed)}</td>
                <td style={td}>{pct(b.failure_rate)}</td>
              </tr>
            ))}
            {Object.keys(porAnillo).length === 0 && (
              <tr><td style={td} colSpan={4}>— sin desglose registrado</td></tr>
            )}
          </tbody>
        </table>
        {worst && (
          <div style={mutedText}>
            peor combinación (worst): <b style={{ fontFamily: mono }}>{worst.key || '—'}</b>
            {' · '}{fmt(worst.failed)} de {fmt(worst.total)} ({pct(worst.failure_rate)})
          </div>
        )}
        <Nota es={conf.note_es} en={conf.note_en} />
      </Bloque>

      {/* ────────── Espacio de propiedades ────────── */}
      <SectionHeader>Espacio de propiedades</SectionHeader>
      <div style={{ ...mutedText, marginBottom: 4 }}>
        Se juzga en <b>{props3.space_es || props3.space_en || '—'}</b>:
        {' '}{props3.n_within_bro5 ?? '—'} de {props3.n_total ?? '—'} candidatos caen dentro.
      </div>
      <Nota es={props3.why_es} en={props3.why_en} />
      {props3.space_en && (
        <div style={{ ...mutedText, fontSize: 10 }}>space_en: {props3.space_en}</div>
      )}

      {/* ────────── Dónde se usó cuántico, y dónde no ────────── */}
      <SectionHeader>Cuántico</SectionHeader>
      <div style={{ ...mutedText, marginBottom: 8 }}>
        {triage.n_eligible ?? 0} de {(triage.n_eligible ?? 0) + (triage.n_classical_suffices ?? 0)} candidatos
        lo necesitaban{triage.places?.length ? ` (${triage.places.join(' + ')})` : ''};{' '}
        {qrun.n_run ?? 0} se corrieron.
        {budget.achieved && (
          <> Reparto: <b style={{ fontFamily: mono }}>{pct(budget.achieved.gpu)} GPU</b>
          {' / '}<b style={{ fontFamily: mono }}>{pct(budget.achieved.quantum)} cuántico</b>.</>
        )}
      </div>
      <Nota es={triage.note_es} en={triage.note_en} />

      {/* El 0% cuántico no es lo mismo si el triaje dijo "no hace falta" que si
          dijo "hacía falta y no se corrió". La segunda es la que hay que ver. */}
      {(budget.quantum_eligible_but_not_run ?? 0) > 0 && (
        <div style={{ ...mutedText, borderLeft: `2px solid ${C.amber}`, paddingLeft: 8, marginTop: 6 }}>
          {budget.quantum_eligible_but_not_run} candidato(s) elegibles para cuántico
          NO se ejecutaron: el {pct(budget.achieved?.quantum)} de cuántico no significa
          que sobrara, significa que no se gastó.
        </div>
      )}
      <Nota es={budget.note_es} en={budget.note_en} aviso={(budget.quantum_eligible_but_not_run ?? 0) > 0} />

      <Bloque titulo="Presupuesto de cómputo" resumen={`${pct(budget.achieved?.gpu)} GPU / ${pct(budget.achieved?.quantum)} Q`}>
        <KV filas={[
          ['planeado GPU / cuántico (planned)', `${pct(budget.planned?.gpu)} / ${pct(budget.planned?.quantum)}`],
          ['conseguido GPU / cuántico (achieved)', `${pct(budget.achieved?.gpu)} / ${pct(budget.achieved?.quantum)}`],
          ['segundos GPU / cuántico (seconds)', `${unidad(budget.seconds?.gpu, 's')} / ${unidad(budget.seconds?.quantum, 's')}`],
          ['saltados por triaje (candidates_skipped_by_triage)', fmt(budget.candidates_skipped_by_triage)],
          ['enviados a cuántico (candidates_sent_to_quantum)', fmt(budget.candidates_sent_to_quantum)],
          ['elegibles no ejecutados (quantum_eligible_but_not_run)', fmt(budget.quantum_eligible_but_not_run)],
          ['desvío del objetivo (deviation_from_target)', fmt(budget.deviation_from_target)],
        ]} />
      </Bloque>

      <Bloque
        titulo="Ejecución cuántica"
        resumen={`pedida: ${sn(qrun.requested)} · ${qrun.n_run ?? 0} corridos / ${qrun.n_skipped ?? 0} saltados`}
      >
        <KV filas={[
          ['pedida (requested)', sn(qrun.requested)],
          ['elegibles (n_eligible)', fmt(qrun.n_eligible)],
          ['corridos (n_run)', fmt(qrun.n_run)],
          ['saltados (n_skipped)', fmt(qrun.n_skipped)],
          ['segundos por geometría (seconds_per_geometry)', unidad(qrun.seconds_per_geometry, 's')],
          ['suelo diferencial (differential_floor_ev)', unidad(qrun.differential_floor_ev, 'eV')],
          ['plan de confórmeros (conformer_plan)',
            (qrun.conformer_plan || []).length
              ? (qrun.conformer_plan || []).map((p) => `${p.sequence || '?'}: ${p.n_geometries ?? '—'}`).join(' · ')
              : '— sin plan (no se pidió ejecución)'],
        ]} />

        {/* La región: sin esto, "SQD" se lee como si se hubiera calculado la
            molécula entera, y no es lo que pasó. */}
        {(qrun.results || []).length > 0 ? (
          <div style={{ ...mutedText, marginTop: 8 }}>
            {(qrun.results || []).map((rr) => {
              const g = rr.region || {};
              return (
                <div key={rr.sequence} style={{ marginBottom: 4 }}>
                  <span style={{ fontFamily: mono }}>{rr.sequence}</span>
                  {g.n_heavy_region != null && (
                    <> · región de <b>{g.n_heavy_region}</b> de {g.n_heavy_molecule} átomos pesados,
                    anclada en <b>{g.anchor}</b>, {g.n_caps} enlaces capados
                    {g.n_absorbed_to_repair_boundary != null && <>, {g.n_absorbed_to_repair_boundary} átomos absorbidos para cerrar el borde</>}
                    {g.why && <> — {g.why}</>}</>
                  )}
                  {rr.error
                    ? <span style={{ color: C.amber }}> · sin energías: {rr.error}</span>
                    : <> · {rr.n_significant} de {rr.n_total} confórmeros se separan del de referencia</>}
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ ...mutedText, marginTop: 8 }}>
            results: vacío — no se calculó ninguna energía cuántica en esta corrida.
          </div>
        )}
        {(qrun.skipped || []).map((sk) => (
          <div key={sk.sequence} style={{ ...mutedText, color: C.amber }}>
            <span style={{ fontFamily: mono }}>{sk.sequence}</span> · saltado: {sk.reason}
          </div>
        ))}
        <Nota es={qrun.note_es} en={qrun.note_en} />
      </Bloque>

      {/* ────────── El orden ────────── */}
      <SectionHeader>Priorización</SectionHeader>
      {rank.ordered_by && (
        <div style={{ ...mutedText, marginBottom: 6 }}>
          Ordenado por (ordered_by): <b>{rank.ordered_by}</b>
        </div>
      )}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              <th style={th}>#</th><th style={th}>secuencia</th><th style={th}>anillo</th>
              <th style={th}>MW</th><th style={th}>bRo5</th><th style={th}>confs</th>
              <th style={th}>riesgos</th><th style={th}>SA</th><th style={th}>score</th><th style={th}>Q</th>
            </tr>
          </thead>
          <tbody>
            {cands.slice(0, 10).map((c) => (
              <tr key={c.rank}>
                <td style={td}>{c.rank}</td>
                <td style={{ ...td, fontFamily: mono }}>{c.sequence}</td>
                <td style={td}>{c.ring_size ?? '—'}</td>
                <td style={td}>{c.descriptors?.mw ?? '—'}</td>
                <td style={{ ...td, color: c.bro5_ok ? C.ok : C.amber }}>
                  {c.bro5_ok ? 'ok' : `${c.bro5_violations} fuera`}
                </td>
                <td style={td}>
                  {c.n_conformers ?? '—'}
                  {c.ensemble_converged === false && <span title="el ensemble no había convergido"> ·no conv</span>}
                </td>
                <td style={td}>{c.liabilities}</td>
                <td style={td}>{fmt(c.synthesis?.sa_score)}</td>
                <td style={{ ...td, fontFamily: mono }}>{fmt(c.composite?.score)}</td>
                <td style={{ ...td, fontFamily: mono }}>{c.quantum?.places?.join('+') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Nota es={rank.not_a_potency_prediction_es} en={rank.not_a_potency_prediction_en} aviso />

      {/* Ficha completa por candidato: descriptores, veredicto del gate y
          composite. Va plegado porque son ~30 campos por molécula. */}
      {cands.map((c) => {
        const d = c.descriptors || {};
        const g = c.quantum?.gate || {};
        const cp = c.composite || {};
        return (
          <Bloque key={`cand-${c.rank}`} titulo={`#${c.rank} · ${c.sequence}`} resumen={`MW ${fmt(d.mw)} · ${c.cyclization || '—'}`}>
            <KV filas={[
              ['ciclación (cyclization)', c.cyclization || '—'],
              ['tamaño de anillo (ring_size)', c.ring_size ?? '—'],
              ['hash de contenido (content_hash)', c.content_hash || '—'],
              ['MW / clogp', `${fmt(d.mw)} / ${fmt(d.clogp)}`],
              ['hbd / hba', `${fmt(d.hbd)} / ${fmt(d.hba)}`],
              ['tpsa / rotb', `${fmt(d.tpsa)} / ${fmt(d.rotb)}`],
              ['átomos pesados (n_heavy) / csp3', `${fmt(d.n_heavy)} / ${fmt(d.csp3)}`],
              ['bRo5', c.bro5_ok ? 'dentro' : `${c.bro5_violations} violaciones`],
              ['liabilities de secuencia', fmt(c.liabilities)],
              ['confórmeros / convergió', `${c.n_conformers ?? '—'} / ${sn(c.ensemble_converged)}`],
            ]} />
            <details style={{ marginTop: 6 }}>
              <summary style={{ cursor: 'pointer', color: C.muted, fontSize: 10.5, fontFamily: mono }}>smiles</summary>
              <div style={{ ...mutedText, fontFamily: mono, wordBreak: 'break-all' }}>{c.smiles || '—'}</div>
            </details>

            <div style={{ ...mutedText, marginTop: 8, fontWeight: 700 }}>Gate cuántico</div>
            <KV filas={[
              ['aplica (applies)', sn(c.quantum?.applies)],
              ['sitios (places)', c.quantum?.places?.join(' + ') || '—'],
              ['modalidad (modality)', g.modality || '—'],
              ['relevante para cuántico (quantum_relevant)', sn(g.quantum_relevant)],
              ['gate.applies', sn(g.applies)],
              ['warheads', (g.moieties?.warheads || []).length ? (g.moieties?.warheads || []).join(', ') : 'ninguno'],
              ['metal_chelators', (g.moieties?.metal_chelators || []).length ? (g.moieties?.metal_chelators || []).join(', ') : 'ninguno'],
              ['gate.quantum', g.quantum ?? '—'],
              ['veredicto del gate (gate.verdict)', g.verdict || '—'],
              ['veredicto (verdict)', c.quantum?.verdict || '—'],
            ]} />
            {(c.quantum?.reasons || []).map((r, i) => (
              <div key={i} style={mutedText}>· {r}</div>
            ))}

            {/* El composite: peso a peso y componente a componente. Un score
                cuyos pesos no se ven no se puede discutir, sólo creer. */}
            <div style={{ ...mutedText, marginTop: 8, fontWeight: 700 }}>Score compuesto</div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr><th style={th}>componente</th><th style={th}>peso</th><th style={th}>valor</th></tr>
              </thead>
              <tbody>
                {Object.entries(cp.weights || {}).map(([k, w]) => {
                  const val = (cp.components || {})[k];
                  const falta = val === null || val === undefined;
                  return (
                    <tr key={k}>
                      <td style={td}>{k}</td>
                      <td style={{ ...td, fontFamily: mono }}>{fmt(w)}</td>
                      <td style={{ ...td, fontFamily: mono, color: falta ? C.amber : C.ink }}>
                        {falta ? '— no medido' : fmt(val)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <KV filas={[
              ['score', fmt(cp.score)],
              ['componentes ausentes (components_missing)',
                (cp.components_missing || []).length ? (cp.components_missing || []).join(', ') : 'ninguno'],
              ['renormalizado sobre (renormalised_over)', fmt(cp.renormalised_over)],
            ]} />
            <Nota es={cp.note_es} en={cp.note_en} />
          </Bloque>
        );
      })}

      {best && (
        <div style={{ ...mutedText, marginTop: 6 }}>
          Mejor candidato (best_candidate): <b style={{ fontFamily: mono }}>{best.sequence}</b>
          {' · '}rank {best.rank}{' · '}score {fmt(best.composite?.score)}.
          Es el mismo objeto que encabeza la tabla, repetido por el backend para consumo directo.
        </div>
      )}

      {/* ────────── ADMET ────────── */}
      <SectionHeader>ADMET</SectionHeader>
      {admet.available === false ? (
        <Ausente
          que="ADMET"
          reason={admet.reason}
          extra={
            <div style={{ ...mutedText, color: C.amber, marginTop: 4 }}>
              motor (engine): {admet.engine || '—'} · tiempo gastado antes de fallar: {unidad(admet.wall_seconds, 's')}.
              Ningún campo ADMET de esta corrida es cero: simplemente no existe.
            </div>
          }
        />
      ) : (
        <>
          <KV filas={[
            ['disponible (available)', sn(admet.available)],
            ['motor (engine)', admet.engine || '—'],
            ['tiempo (wall_seconds)', unidad(admet.wall_seconds, 's')],
          ]} />
          <Nota es={admet.note_es} en={admet.note_en} />
        </>
      )}

      {/* ────────── Síntesis ────────── */}
      <SectionHeader>Síntesis</SectionHeader>
      <Bloque titulo="Accesibilidad sintética" resumen={`${synth.n_scored ?? 0} puntuados`} abierto={false}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr>
                <th style={th}>secuencia</th><th style={th}>sa_score</th><th style={th}>np_score</th>
                <th style={th}>sc_score</th><th style={th}>lectura</th><th style={th}>s</th>
              </tr>
            </thead>
            <tbody>
              {(synth.per_candidate || []).map((s, i) => (
                <tr key={i}>
                  <td style={{ ...td, fontFamily: mono }}>{s.sequence || '—'}</td>
                  <td style={td}>{fmt(s.sa_score)}</td>
                  <td style={td}>{fmt(s.np_score)}</td>
                  {/* sc_score viene null porque SCScore no está cargado: '—', no 0. */}
                  <td style={{ ...td, color: s.sc_score == null ? C.amber : C.ink }}>{fmt(s.sc_score)}</td>
                  <td style={td}>{s.sa_interpretation_es || s.sa_interpretation_en || '—'}</td>
                  <td style={td}>{fmt(s.wall_seconds)}</td>
                </tr>
              ))}
              {(synth.per_candidate || []).length === 0 && (
                <tr><td style={td} colSpan={6}>— sin puntuación de síntesis</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {/* Qué motor respondió de verdad: un sa_score de RDKit y una ruta de
            AiZynthFinder no son la misma clase de evidencia. */}
        {(synth.per_candidate || []).slice(0, 1).map((s, i) => {
          const b = s.backends || {};
          return (
            <div key={i} style={{ marginTop: 6 }}>
              <div style={{ ...mutedText, fontWeight: 700 }}>Motores (backends)</div>
              <div>
                <Chip tone={b.rdkit ? 'ok' : 'bad'} text={`rdkit ${sn(b.rdkit)}`} />
                <Chip tone={b.sa_score ? 'ok' : 'bad'} text={`sa_score ${sn(b.sa_score)}`} />
                <Chip tone={b.np_score ? 'ok' : 'bad'} text={`np_score ${sn(b.np_score)}`} />
                <Chip tone={b.scscore ? 'ok' : 'bad'} text={`scscore ${sn(b.scscore)}`} />
                <Chip tone={b.aizynthfinder ? 'ok' : 'bad'} text={`aizynthfinder ${sn(b.aizynthfinder)}`} />
                <Chip tone={b.aizynth_configured ? 'ok' : 'bad'} text={`aizynth_configured ${sn(b.aizynth_configured)}`} />
              </div>
              <KV filas={[
                ['disponible (available)', sn(s.available)],
                ['interpretación en (sa_interpretation_en)', s.sa_interpretation_en || '—'],
              ]} />
              {s.route?.available === false && (
                <Ausente que="Ruta sintética" reason={s.route.reason} reason_en={s.route.reason_en} />
              )}
              <Nota es={s.note_es} en={s.note_en} />
            </div>
          );
        })}
        <Nota es={synth.note_es} en={synth.note_en} />
      </Bloque>

      {/* ────────── Toxicología ────────── */}
      <SectionHeader>Toxicología</SectionHeader>
      {tox.available === false ? (
        <Ausente que="Toxicología" reason={tox.reason} reason_en={tox.reason_en} />
      ) : (
        <>
          <StatRow>
            <StatTile label="especie más sensible" value={tox.allometric_summary?.most_sensitive_species || tox.summary?.most_sensitive_species || '—'} />
            <StatTile label="HED más conservador" value={unidad(tox.allometric_summary?.most_conservative_hed, 'mg/kg')} />
            <StatTile
              label="dosis de inicio"
              value={unidad(tox.allometric_summary?.recommended_starting_dose_mg_kg ?? tox.summary?.recommended_starting_dose, 'mg/kg')}
              accent
            />
            <StatTile label="clase de seguridad humana" value={tox.safety_assessment?.human_safety_class || tox.summary?.human_safety_class || '—'} />
          </StatRow>

          <Bloque titulo="Toxicología por especie" resumen={`${tox.species_tested?.length ?? tox.summary?.n_species ?? 0} especies`}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr>
                    <th style={th}>species</th><th style={th}>noael_mg_kg</th><th style={th}>loael_mg_kg</th>
                    <th style={th}>hed_mg_kg</th><th style={th}>km_factor</th>
                    <th style={th}>factor de escalado</th><th style={th}>therapeutic_index</th>
                    <th style={th}>safety_margin</th><th style={th}>clasificación</th>
                  </tr>
                </thead>
                <tbody>
                  {(tox.species_toxicology || []).map((s, i) => (
                    <tr key={i}>
                      <td style={{ ...td, fontFamily: mono }}>{s.species || '—'}</td>
                      <td style={td}>{fmt(s.noael_mg_kg)}{s.noael_estimated ? '*' : ''}</td>
                      <td style={td}>{fmt(s.loael_mg_kg)}</td>
                      <td style={td}>{fmt(s.hed_mg_kg)}</td>
                      <td style={td}>{fmt(s.km_factor)}</td>
                      <td style={td}>{fmt(s.quantum_scaling_factor)}</td>
                      {/* TI y margen llegan null cuando no hay dosis eficaz: no se
                          rellenan con 0, se enseñan vacíos con su nota. */}
                      <td style={{ ...td, color: s.therapeutic_index == null ? C.amber : C.ink }} title={s.therapeutic_index_note}>
                        {fmt(s.therapeutic_index)}
                      </td>
                      <td style={{ ...td, color: s.safety_margin == null ? C.amber : C.ink }}>{fmt(s.safety_margin)}</td>
                      <td style={td}>{s.safety_classification || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {(tox.species_toxicology || []).slice(0, 1).map((s, i) => (
              <div key={i} style={mutedText}>
                {s.therapeutic_index_note && <div>therapeutic_index_note: {s.therapeutic_index_note}</div>}
                {s.noael_estimated && <div>* noael_estimated — {s.noael_disclaimer || 'estimación heurística in-silico'}</div>}
              </div>
            ))}
          </Bloque>

          <Bloque titulo="Escalado alométrico" resumen={tox.quantum_scaling?.quantum_hardware ? 'hardware cuántico' : 'clásico'}>
            <KV filas={[
              ['método (method)', tox.quantum_scaling?.method || '—'],
              ['hardware real (is_real_hardware)', sn(tox.quantum_scaling?.is_real_hardware)],
              ['hardware cuántico (quantum_hardware)', sn(tox.quantum_scaling?.quantum_hardware)],
              ['jobs IBM (ibm_job_ids)',
                (tox.quantum_scaling?.ibm_job_ids || []).length
                  ? (tox.quantum_scaling?.ibm_job_ids || []).join(', ')
                  : 'ninguno — no se ejecutó en hardware'],
              ['nº de especies (n_species)', fmt(tox.quantum_scaling?.n_species ?? tox.summary?.n_species)],
              ['especies probadas (species_tested)', (tox.species_tested || []).join(', ') || '—'],
            ]} />
            {/* Las especies son claves dinámicas del backend (rat, dog, monkey…),
                así que se recorren en vez de escribirse una a una. */}
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, marginTop: 6 }}>
              <thead>
                <tr>
                  <th style={th}>especie</th><th style={th}>body_weight_kg</th>
                  <th style={th}>allometric_exponent</th><th style={th}>scaling_factors</th>
                  <th style={th}>noaels_mg_kg</th><th style={th}>heds_mg_kg</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(tox.quantum_scaling?.species_detail || {}).map(([sp, det]) => (
                  <tr key={sp}>
                    <td style={{ ...td, fontFamily: mono }}>{sp}</td>
                    <td style={td}>{fmt(det.body_weight_kg)}</td>
                    <td style={td}>{fmt(det.allometric_exponent)}</td>
                    <td style={td}>{fmt((tox.quantum_scaling?.scaling_factors || {})[sp])}</td>
                    <td style={td}>{fmt((tox.allometric_summary?.noaels_mg_kg || {})[sp])}</td>
                    <td style={td}>{fmt((tox.allometric_summary?.heds_mg_kg || {})[sp])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Nota es={tox.allometric_summary?.note} />
            <Nota es={tox.quantum_scaling?.honest_note} aviso />
          </Bloque>

          <Bloque titulo="CYP: especie frente a humano" resumen={`similitud ${fmt((tox.cyp_comparison || [])[0]?.overall_similarity)}`}>
            {(tox.cyp_comparison || []).map((e, i) => (
              <div key={i} style={{ marginTop: i ? 10 : 0 }}>
                <div style={{ ...mutedText, fontWeight: 700 }}>
                  {e.species || '—'} · similitud global (overall_similarity): {fmt(e.overall_similarity)}
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr>
                      <th style={th}>CYP</th><th style={th}>species_activity</th>
                      <th style={th}>human_activity</th><th style={th}>ratio</th><th style={th}>interpretation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(e.cyp_comparison || {}).map(([iso, v]) => (
                      <tr key={iso}>
                        <td style={{ ...td, fontFamily: mono }}>{iso.toUpperCase()}</td>
                        <td style={td}>{fmt(v.species_activity)}</td>
                        <td style={td}>{fmt(v.human_activity)}</td>
                        <td style={td}>{fmt(v.ratio)}</td>
                        <td style={td}>{v.interpretation || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </Bloque>

          <Bloque titulo="Evaluación de seguridad" resumen={tox.safety_assessment?.human_safety_class || '—'}>
            <KV filas={[
              ['NOAEL humano predicho (human_predicted_noael)', fmt(tox.safety_assessment?.human_predicted_noael)],
              ['índice terapéutico humano (human_therapeutic_index)', fmt(tox.safety_assessment?.human_therapeutic_index)],
              ['clase (human_safety_class)', tox.safety_assessment?.human_safety_class || '—'],
              ['concordancia entre especies (concordant)', sn(tox.safety_assessment?.species_concordance?.concordant)],
              ['clases distintas (n_unique_classes)', fmt(tox.safety_assessment?.species_concordance?.n_unique_classes)],
              ['clasificaciones', Object.entries(tox.safety_assessment?.species_concordance?.classifications || {})
                .map(([sp, cl]) => `${sp}: ${cl}`).join(' · ') || '—'],
            ]} />
            <Nota es={tox.safety_assessment?.species_concordance?.note} />
          </Bloque>

          <Bloque titulo="Descriptores y procedencia (tox)" resumen={`${tox.module || '—'} v${tox.version || '—'}`}>
            <KV filas={[
              ['módulo (module) / versión (version)', `${tox.module || '—'} / ${tox.version || '—'}`],
              ['mw / logp', `${fmt(tox.molecular_features?.mw)} / ${fmt(tox.molecular_features?.logp)}`],
              ['tpsa', fmt(tox.molecular_features?.tpsa)],
              ['hba / hbd', `${fmt(tox.molecular_features?.hba)} / ${fmt(tox.molecular_features?.hbd)}`],
              ['rotatable_bonds / aromatic_rings', `${fmt(tox.molecular_features?.rotatable_bonds)} / ${fmt(tox.molecular_features?.aromatic_rings)}`],
              ['heavy_atoms / sp3_fraction', `${fmt(tox.molecular_features?.heavy_atoms)} / ${fmt(tox.molecular_features?.sp3_fraction)}`],
              ['disponible (available)', sn(tox.available)],
              ['tiempo (wall_seconds)', unidad(tox.wall_seconds, 's')],
              ['tiempo interno (elapsed_seconds)', unidad(tox.summary?.elapsed_seconds, 's')],
              ['jobs IBM del resumen (summary.ibm_job_ids)',
                (tox.summary?.ibm_job_ids || []).length ? (tox.summary?.ibm_job_ids || []).join(', ') : 'ninguno'],
              ['hardware cuántico (summary.quantum_hardware)', sn(tox.summary?.quantum_hardware)],
            ]} />
            <details style={{ marginTop: 6 }}>
              <summary style={{ cursor: 'pointer', color: C.muted, fontSize: 10.5, fontFamily: mono }}>smiles evaluado</summary>
              <div style={{ ...mutedText, fontFamily: mono, wordBreak: 'break-all' }}>{tox.smiles || '—'}</div>
            </details>
          </Bloque>
          <Nota es={tox.note_es} en={tox.note_en} />
        </>
      )}

      {/* ────────── Farmacocinética ────────── */}
      <SectionHeader>Farmacocinética</SectionHeader>
      {pk.available === false ? (
        <Ausente que="Farmacocinética" reason={pk.reason} reason_en={pk.reason_en} />
      ) : (
        <>
          <StatRow>
            <StatTile label="CL hepático" value={unidad(pk.cl_hepatic_L_per_h ?? pk.clearance?.cl_hepatic_L_per_h, 'L/h')} />
            <StatTile label="fracción libre (fu)" value={fmt(pk.fraction_unbound ?? pk.clearance?.fraction_unbound?.fu)} />
            <StatTile label="ratio de extracción" value={fmt(pk.clearance?.hepatic_extraction_ratio)} />
            <StatTile label="dosis (dose_mg)" value={unidad(pk.dose_mg, 'mg')} />
          </StatRow>

          <Bloque titulo="Aclaramiento e IVIVE" resumen={pk.engine || pk.clearance?.engine || '—'}>
            <KV filas={[
              ['motor (engine)', pk.engine || pk.clearance?.engine || '—'],
              ['CL int in vitro (clearance_uL_min_10e6cells)', unidad(pk.clearance?.cl_int_invitro?.clearance_uL_min_10e6cells, 'µL/min/10⁶cél')],
              ['CL int log10 (clearance_log10)', fmt(pk.clearance?.cl_int_invitro?.clearance_log10)],
              ['modelo cargado (model_available)', sn(pk.clearance?.cl_int_invitro?.model_available)],
              ['fu', fmt(pk.clearance?.fraction_unbound?.fu)],
              ['unión a proteína (ppb_percent)', unidad(pk.clearance?.fraction_unbound?.ppb_percent, '%')],
              ['origen de fu (source)', pk.clearance?.fraction_unbound?.source || '—'],
              ['modelo IVIVE (model)', pk.clearance?.ivive?.model || '—'],
              ['CL int entera (cl_int_whole_L_per_h)', unidad(pk.clearance?.ivive?.cl_int_whole_L_per_h, 'L/h')],
              ['CL int in vitro (cl_int_invitro_uL_min_10e6cells)', fmt(pk.clearance?.ivive?.cl_int_invitro_uL_min_10e6cells)],
              ['fu en sangre (fu_blood)', fmt(pk.clearance?.ivive?.fu_blood)],
              ['CL hepático (cl_hepatic_L_per_h)', unidad(pk.clearance?.ivive?.cl_hepatic_L_per_h, 'L/h')],
              ['ratio de extracción (hepatic_extraction_ratio)', fmt(pk.clearance?.ivive?.hepatic_extraction_ratio)],
              ['limitado por flujo (blood_flow_limited)', sn(pk.clearance?.ivive?.blood_flow_limited)],
              ['fisiología HPGL_10e6_per_g', fmt(pk.clearance?.ivive?.physiology?.HPGL_10e6_per_g)],
              ['fisiología liver_g', unidad(pk.clearance?.ivive?.physiology?.liver_g, 'g')],
              ['fisiología Q_hepatic_L_h', unidad(pk.clearance?.ivive?.physiology?.Q_hepatic_L_h, 'L/h')],
            ]} />
            {/* Comprobaciones del propio modelo: si la matemática del IVIVE no
                cumple sus límites, el número de arriba no vale nada. */}
            <div style={{ ...mutedText, marginTop: 6, fontWeight: 700 }}>Comprobaciones del IVIVE</div>
            <div>
              <Chip tone={pk.clearance?.ivive_math?.ivive_math_ok ? 'ok' : 'bad'} text={`ivive_math_ok ${sn(pk.clearance?.ivive_math?.ivive_math_ok)}`} />
              <Chip tone={pk.clearance?.ivive_math?.low_cl_limit_ok ? 'ok' : 'bad'} text={`low_cl_limit_ok ${sn(pk.clearance?.ivive_math?.low_cl_limit_ok)}`} />
              <Chip tone={pk.clearance?.ivive_math?.high_cl_limit_ok ? 'ok' : 'bad'} text={`high_cl_limit_ok ${sn(pk.clearance?.ivive_math?.high_cl_limit_ok)}`} />
              <Chip tone={pk.clearance?.ivive_math?.monotonic ? 'ok' : 'bad'} text={`monotonic ${sn(pk.clearance?.ivive_math?.monotonic)}`} />
              <Chip tone={pk.clearance?.ivive_math?.bounded_by_Qh ? 'ok' : 'bad'} text={`bounded_by_Qh ${sn(pk.clearance?.ivive_math?.bounded_by_Qh)}`} />
            </div>
            <details style={{ marginTop: 6 }}>
              <summary style={{ cursor: 'pointer', color: C.muted, fontSize: 10.5, fontFamily: mono }}>smiles evaluado</summary>
              <div style={{ ...mutedText, fontFamily: mono, wordBreak: 'break-all' }}>
                {pk.clearance?.smiles || pk.clearance?.cl_int_invitro?.smiles || '—'}
              </div>
            </details>
          </Bloque>

          <Bloque titulo="Validación del modelo PK" resumen={pk.validation?.badge || '—'}>
            <BadgeValidacion v={pk.validation} titulo="etapa" />
            <BadgeValidacion v={pk.clearance?.validation} titulo="aclaramiento" />
            <BadgeValidacion v={pk.clearance?.cl_int_invitro?.validation} titulo="CL int in vitro" />
            <div style={{ ...mutedText, marginTop: 4 }}>
              motor del CL int (engine): {pk.clearance?.cl_int_invitro?.engine || '—'}
            </div>
          </Bloque>

          {/* El perfil concentración-tiempo falta. Dibujar una curva plana sería
              inventarse una PK, así que se dice qué falta y por qué. */}
          {pk.profile?.available === false
            ? <Ausente que="Perfil concentración–tiempo" reason={pk.profile.reason} reason_en={pk.profile.reason_en} />
            : <div style={mutedText}>perfil (profile.available): {sn(pk.profile?.available)}</div>}

          <div style={{ ...mutedText, marginTop: 4 }}>
            disponible (available): {sn(pk.available)} · tiempo (wall_seconds): {unidad(pk.wall_seconds, 's')}
          </div>
          <Nota es={pk.note_es} en={pk.note_en} />
        </>
      )}

      {/* ────────── Docking ────────── */}
      <SectionHeader>Docking</SectionHeader>
      <div style={{ ...mutedText, marginBottom: 4 }}>pedido (requested): {sn(dock.requested)}</div>

      {ts?.available === false ? (
        <Ausente que="Estructura del target" reason={ts.reason} reason_en={ts.reason_en} />
      ) : (
        <Bloque titulo="Estructura del receptor" resumen={`${ts?.pdb_id || '—'} · cadena ${ts?.receptor_chain || '—'}`}>
          <KV filas={[
            ['PDB (pdb_id)', ts?.pdb_id || '—'],
            ['origen (source) / resuelto desde (resolved_from)', `${ts?.source || '—'} · ${ts?.resolved_from || '—'}`],
            ['cadena del receptor (receptor_chain)', ts?.receptor_chain || '—'],
            ['cadenas en el fichero (chains_in_file)', (ts?.chains_in_file || []).join(', ') || '—'],
            ['átomos del receptor (n_atoms_receptor)', fmt(ts?.n_atoms_receptor)],
            ['átomos descartados de otras cadenas (n_atoms_dropped_other_chains)', fmt(ts?.n_atoms_dropped_other_chains)],
            ['HETATM descartados (n_hetatm_dropped)', fmt(ts?.n_hetatm_dropped)],
            ['átomos de referencia del sitio (n_site_reference_atoms)', fmt(ts?.n_site_reference_atoms)],
            ['tiempo (wall_seconds)', unidad(ts?.wall_seconds, 's')],
          ]} />
          <Nota es={ts?.prepared_es} en={ts?.prepared_en} />
          {/* El PDB entero son ~95 KB de texto: no cabe en un chat y no se lee.
              Se resume y la geometría se consulta en el informe. */}
          <div style={{ ...mutedText, marginTop: 4 }}>
            target_structure_pdb: {pdbChars ? `${Math.round(pdbChars / 1024)} KB de texto PDB` : 'no adjunto'} —
            la geometría completa no se pinta aquí; vive en el informe.
          </div>
        </Bloque>
      )}

      {dk?.available === false ? (
        <Ausente que="Docking" reason={dk.reason} reason_en={dk.reason_en} />
      ) : (
        <Bloque titulo="Pose y comprobación de bolsillo" resumen={`${dk?.engine || '—'} · ${dk?.n_poses ?? '—'} poses`}>
          <KV filas={[
            ['motor (engine)', dk?.engine || '—'],
            ['poses (n_poses)', fmt(dk?.n_poses)],
            ['secuencia dockeada (sequence)', dk?.sequence || '—'],
            ['tiempo (wall_seconds)', unidad(dk?.wall_seconds, 's')],
          ]} />
          {pocket?.available === false ? (
            <Ausente que="Comprobación de bolsillo" reason={pocket.reason} reason_en={pocket.reason_en} />
          ) : (
            <>
              <div style={{ ...mutedText, marginTop: 6, fontWeight: 700 }}>
                ¿cae en el sitio? (lands_in_site): {sn(pocket?.lands_in_site)}
              </div>
              <KV filas={[
                ['corte (cutoff_angstrom)', unidad(pocket?.cutoff_angstrom, 'Å')],
                ['átomos de la pose (n_pose_atoms)', fmt(pocket?.n_pose_atoms)],
                ['dentro del corte (n_within_cutoff)', fmt(pocket?.n_within_cutoff)],
                ['fracción dentro del sitio (fraction_within_site)', pct(pocket?.fraction_within_site)],
                ['separación de centroides (centroid_separation_angstrom)', unidad(pocket?.centroid_separation_angstrom, 'Å')],
                ['distancia mín. (min_distance_angstrom)', unidad(pocket?.min_distance_angstrom, 'Å')],
                ['distancia máx. (max_distance_angstrom)', unidad(pocket?.max_distance_angstrom, 'Å')],
              ]} />
              <Nota es={pocket?.note_es} en={pocket?.note_en} />
            </>
          )}
          <Nota es={dk?.caveat_es} en={dk?.caveat_en} aviso />
          {/* Ni el SDF de la pose ni las 64 coordenadas entran en la card: se
              resumen y se dejan para el informe y el visor 3D. */}
          <div style={{ ...mutedText, marginTop: 4 }}>
            geometría: {(dk?.ligand_atoms || poseAtoms).length || 0} átomos de ligando
            {(dk?.ligand_atoms || poseAtoms)[0]?.e
              ? ` (primero: elemento ${(dk?.ligand_atoms || poseAtoms)[0].e}, radio ${fmt((dk?.ligand_atoms || poseAtoms)[0].r)} Å)`
              : ''};
            {' '}docking_pose_atoms lleva {poseAtoms.length} coordenadas.
            El SDF de la mejor pose (top_pose_sdf) ocupa {(dk?.top_pose_sdf || '').length} caracteres
            y no se pinta aquí: la geometría vive en el informe.
          </div>
          <KV filas={[
            ['handoff: origen (source)', dk?.complex_handoff?.source || '—'],
            ['handoff: confianza (confidence)', fmt(dk?.complex_handoff?.confidence)],
            ['handoff: receptor_pdb', dk?.complex_handoff?.receptor_pdb ? `${Math.round((dk.complex_handoff.receptor_pdb || '').length / 1024)} KB` : '—'],
            ['handoff: ligand_sdf', dk?.complex_handoff?.ligand_sdf ? `${(dk.complex_handoff.ligand_sdf || '').length} caracteres` : '—'],
            ['handoff: nota (note)', dk?.complex_handoff?.note || '—'],
          ]} />
        </Bloque>
      )}

      {/* La afinidad NO se calculó, y eso es una decisión, no un hueco. */}
      {dock.affinity?.available === false ? (
        <Ausente
          que="Afinidad (ΔG)"
          reason={dock.affinity.reason}
          reason_en={dock.affinity.reason_en}
          extra={
            <div style={{ ...mutedText, color: C.amber, marginTop: 4 }}>
              scorer retirado (removed_scorer): {dock.affinity.removed_scorer || '—'}
              {dock.affinity.removed_scorer_en && (
                <details style={{ marginTop: 3 }}>
                  <summary style={{ cursor: 'pointer', color: C.amber, fontSize: 10, fontFamily: mono }}>en</summary>
                  <div>{dock.affinity.removed_scorer_en}</div>
                </details>
              )}
            </div>
          }
        />
      ) : (
        <div style={mutedText}>afinidad (affinity.available): {sn(dock.affinity?.available)}</div>
      )}
      <Nota es={dock.note_es} en={dock.note_en} />

      {/* ────────── Score compuesto global ────────── */}
      <SectionHeader>Score compuesto</SectionHeader>
      <div>
        {Object.entries(comp.weights || {}).map(([k, w]) => (
          <Chip key={k} text={`${k} ${fmt(w)}`} />
        ))}
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, marginTop: 6 }}>
        <thead>
          <tr><th style={th}>secuencia</th><th style={th}>score</th><th style={th}>componentes ausentes (missing)</th></tr>
        </thead>
        <tbody>
          {(comp.scored || []).map((s, i) => (
            <tr key={i}>
              <td style={{ ...td, fontFamily: mono }}>{s.sequence || '—'}</td>
              <td style={{ ...td, fontFamily: mono }}>{fmt(s.score)}</td>
              <td style={{ ...td, color: (s.missing || []).length ? C.amber : C.ink }}>
                {(s.missing || []).join(', ') || 'ninguno'}
              </td>
            </tr>
          ))}
          {(comp.scored || []).length === 0 && (
            <tr><td style={td} colSpan={3}>— sin score compuesto</td></tr>
          )}
        </tbody>
      </table>
      <Nota es={comp.note_es} en={comp.note_en} />

      <div style={{ ...mutedText, marginTop: 10, fontStyle: 'italic' }}>
        {data.disclaimer_es ||
          'Priorización in-silico para ensayo, no predicción de potencia.'}
        {data.disclaimer_en && (
          <details style={{ marginTop: 3 }}>
            <summary style={{ cursor: 'pointer', color: C.muted, fontSize: 10, fontFamily: mono }}>en</summary>
            <div style={{ marginTop: 3 }}>{data.disclaimer_en}</div>
          </details>
        )}
      </div>
    </div>
  );
}

export default MacrocycleCard;
