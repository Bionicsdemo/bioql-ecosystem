import { useEffect, useRef, useState } from 'react';
import { Sparkles, Loader2, ExternalLink, AlertCircle } from 'lucide-react';

// ──────────────────────────────────────────────────────────────────────────
// The interactive report for a finished pipeline run.
//
// It appears at the END of the assistant's answer: the backend turns the run's
// own result JSON into a page with a 3D scene per stage (PyMOL meshes, the
// transcript base by base, the quantum register) and a narration whose every
// number is read from that JSON. Building it costs no model call, so this is
// requested once per message and the link is then kept.
//
// A pipeline with no artifact model yet answers 422; that is not an error worth
// showing, it simply means this run has no report, so nothing is rendered.
// MOLEVERA / BIOQL
// ──────────────────────────────────────────────────────────────────────────

interface Props {
  result: Record<string, any> | null;
  sessionId?: string;
}

interface Built {
  url: string;
  title: string;
  chapters: { id: string; beats: number; status: string }[];
  coverage: { leaves: number; annex: number };
  checks: { id: string; ok: boolean }[];
  meshes: Record<string, { residues: number; kind: string }>;
  elapsed_s: number;
}

export function InteractiveReportLink({ result, sessionId }: Props) {
  const [state, setState] = useState<'idle' | 'building' | 'done' | 'none' | 'error'>('idle');
  const [built, setBuilt] = useState<Built | null>(null);
  const [error, setError] = useState('');
  const asked = useRef(false);

  useEffect(() => {
    if (asked.current || !result || typeof result !== 'object') return;
    asked.current = true;
    let alive = true;
    (async () => {
      setState('building');
      try {
        const res = await fetch('/api/report/interactive', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ result, session_id: sessionId }),
        });
        const json = await res.json().catch(() => ({}));
        if (!alive) return;
        if (res.status === 422) { setState('none'); return; }       // no model for this pipeline
        if (!res.ok || !json?.success) {
          setError(String(json?.error || `HTTP ${res.status}`));
          setState('error');
          return;
        }
        setBuilt(json as Built);
        setState('done');
      } catch (e: any) {
        if (!alive) return;
        setError(e?.message || 'request failed');
        setState('error');
      }
    })();
    return () => { alive = false; };
  }, [result, sessionId]);

  if (state === 'idle' || state === 'none') return null;

  if (state === 'building') {
    return (
      <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
        <Loader2 className="w-3.5 h-3.5 animate-spin text-violet-400" />
        Generando el informe interactivo (3D + explicación de cada dato)…
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className="mt-3 flex items-start gap-2 text-xs text-amber-400/90">
        <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
        <span>No se pudo generar el informe interactivo: {error}</span>
      </div>
    );
  }

  const b = built!;
  const beats = b.chapters.reduce((n, c) => n + c.beats, 0);
  const gaps = b.chapters.filter(c => c.status === 'gap').length;
  const failed = b.checks.filter(c => !c.ok).length;
  const meshes = Object.keys(b.meshes).length;

  return (
    <a
      href={b.url}
      target="_blank"
      rel="noopener noreferrer"
      className="mt-3 flex items-start gap-3 rounded-lg border border-violet-500/30 bg-violet-500/5 px-3 py-2.5
                 hover:bg-violet-500/10 hover:border-violet-500/50 transition-colors group cursor-pointer
                 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400"
      title="Se abre en una pestaña nueva"
    >
      <Sparkles className="w-4 h-4 text-violet-400 mt-0.5 shrink-0" />
      <span className="flex-1 min-w-0">
        <span className="block text-sm text-violet-200 font-medium">
          Informe interactivo: {b.title}
        </span>
        <span className="block text-[11px] text-gray-400 mt-0.5">
          {b.chapters.length} capítulos · {beats} frases · {b.coverage.leaves.toLocaleString('es')} valores del
          resultado{b.coverage.annex > 0 ? ` (${b.coverage.annex} en el anexo)` : ''}
          {meshes > 0 ? ` · ${meshes} estructura${meshes > 1 ? 's' : ''} en 3D` : ''}
          {gaps > 0 ? ` · ${gaps} etapa${gaps > 1 ? 's' : ''} sin medir` : ''}
          {failed > 0 ? ` · ${failed} comprobación${failed > 1 ? 'es' : ''} que no cuadra` : ''}
        </span>
      </span>
      <ExternalLink className="w-3.5 h-3.5 text-gray-500 group-hover:text-violet-300 transition-colors shrink-0 mt-0.5" />
    </a>
  );
}
