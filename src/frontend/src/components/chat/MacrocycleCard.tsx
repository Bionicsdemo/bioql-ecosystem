import React from 'react';
import { C, mono, cardBox, mutedText, th, td, CardHeader, SectionHeader, StatTile } from './cardKit';

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
// El orden es una PRIORIZACIÓN para ensayo. No se dockea salvo que llegue
// estructura, y los scores de docking de macrociclos correlacionan mal con
// afinidad medida incluso cuando se calculan.
// MOLEVERA / BIOQL
// ──────────────────────────────────────────────────────────────────────────

interface Candidate {
  rank: number;
  sequence: string;
  cyclization: string;
  ring_size: number | null;
  bro5_ok: boolean;
  bro5_violations: number;
  liabilities: number;
  n_conformers: number | null;
  ensemble_converged: boolean | null;
  descriptors?: Record<string, number>;
  quantum?: { applies: boolean; places: string[] };
}

interface Props {
  data: {
    target?: string;
    cyclization?: string;
    candidates?: Candidate[];
    stages?: Record<string, any>;
    compute_budget?: any;
    disclaimer_es?: string;
    disclaimer_en?: string;
  };
}

export function MacrocycleCard({ data }: Props) {
  const cands = data.candidates || [];
  const build = data.stages?.['1_build'] || {};
  const conf = data.stages?.['2_conformers'] || {};
  const triage = data.stages?.['4_quantum_triage'] || {};
  const qrun = data.stages?.['4b_quantum_run'] || {};
  const pop = conf.population || {};
  const budget = data.compute_budget || {};

  const noConverged = (conf.convergence || {}).n_not_converged ?? 0;
  const withCurve = (conf.convergence || {}).n_with_curve ?? 0;

  return (
    <div style={cardBox}>
      <CardHeader
        title={`Macrociclos · ${data.target || 'sin target'}`}
        badge={data.cyclization ? <span style={{ fontFamily: mono, fontSize: 11 }}>{String(data.cyclization).replace(/_/g, '-')}</span> : undefined}
      />

      {/* Lo que puede fallar en silencio, primero */}
      <SectionHeader>Integridad de la corrida</SectionHeader>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(130px,1fr))', gap: 8, marginBottom: 12 }}>
        <StatTile label="anillos cerrados" value={`${build.built ?? '—'} / ${build.requested ?? '—'}`} />
        <StatTile label="población conservada" value={pop.ok === true ? 'sí' : pop.ok === false ? 'NO' : '—'} accent={pop.ok === false} />
        <StatTile label="ensembles sin converger" value={`${noConverged} / ${withCurve}`} accent={noConverged > 0} />
        <StatTile label="dentro de bRo5" value={`${(data.stages?.['3_properties'] || {}).n_within_bro5 ?? '—'} / ${(data.stages?.['3_properties'] || {}).n_total ?? '—'}`} />
      </div>

      {noConverged > 0 && (
        <div style={{ ...mutedText, borderLeft: `2px solid ${C.amber}`, paddingLeft: 8, marginBottom: 12 }}>
          {noConverged} ensemble(s) seguían aportando confórmeros nuevos al parar de muestrear:
          su confórmero bioactivo puede no haber estado en la caja, y ese orden no es definitivo.
        </div>
      )}

      {/* Dónde se usó cuántico, y dónde no */}
      <SectionHeader>Cuántico</SectionHeader>
      <div style={{ ...mutedText, marginBottom: 8 }}>
        {triage.n_eligible ?? 0} de {(triage.n_eligible ?? 0) + (triage.n_classical_suffices ?? 0)} candidatos
        lo necesitaban{triage.places?.length ? ` (${triage.places.join(' + ')})` : ''};{' '}
        {qrun.n_run ?? 0} se corrieron.
        {budget.achieved && (
          <> Reparto: <b style={{ fontFamily: mono }}>{Math.round((budget.achieved.gpu ?? 0) * 100)}% GPU</b>
          {' / '}<b style={{ fontFamily: mono }}>{Math.round((budget.achieved.quantum ?? 0) * 100)}% cuántico</b>.</>
        )}
      </div>
      {budget.note_es && <div style={{ ...mutedText, marginBottom: 12 }}>{budget.note_es}</div>}

      {/* El orden */}
      <SectionHeader>Priorización</SectionHeader>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              <th style={th}>#</th><th style={th}>secuencia</th><th style={th}>anillo</th>
              <th style={th}>MW</th><th style={th}>bRo5</th><th style={th}>confs</th>
              <th style={th}>riesgos</th><th style={th}>Q</th>
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
                <td style={{ ...td, fontFamily: mono }}>{c.quantum?.places?.join('+') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ ...mutedText, marginTop: 10, fontStyle: 'italic' }}>
        {data.disclaimer_es ||
          'Priorización in-silico para ensayo, no predicción de potencia.'}
      </div>
    </div>
  );
}

export default MacrocycleCard;
