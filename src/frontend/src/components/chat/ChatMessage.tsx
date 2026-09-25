import { downloadJSON } from "@/utils/export";
import { DockingAnimation3D } from "@/components/visualizations/DockingAnimation3D";
import ValidationBanner from "@/components/chat/ValidationBanner";
import InsightCard from "@/components/chat/InsightCard";
import ProvenancePanel from "@/components/panels/ProvenancePanel";
import { ProvenanceBadge, extractProvenance } from "@/components/common/ProvenanceBadge";
import ClinicalValidationPanel from "@/components/panels/ClinicalValidationPanel";
import MolecularRelationshipGraph from "@/components/visualizations/MolecularRelationshipGraph";
import { ProtenixConfidencePanel } from "@/components/visualizations/ProtenixConfidencePanel";
import { ADMETRadarChart } from "@/components/visualizations/ADMETRadarChart";
import { InteractiveMoleculeViewer } from "@/components/visualizations/InteractiveMoleculeViewer";
import { RaymolOpenButton } from "@/components/visualizations/RaymolOpenButton";
import { openInBioqlViz } from "@/stores/vizStore";
import { PipelineResultsChart } from "@/components/visualizations/PipelineResultsChart";
import { useState, useMemo } from 'react';
import { cn } from '@/utils/cn';
import { ToolExecutionCard } from './ToolExecutionCard';
import { InteractiveReportLink } from './InteractiveReportLink';
import { MoleculePreview } from './MoleculePreview';
import { PipelineVisualization } from './PipelineVisualization';
import { QuantumCellViz } from './QuantumCellViz';
import { VisualizationResult } from '@/services/VisualizationOrchestrator';
import { ToolCall } from '@/services/ClaudeService';
// ── NEW calculation cards (additive; each renders null when its data is absent) ──
import FEPResultsCard from './FEPResultsCard';
import RBFECorrectionCard from './RBFECorrectionCard';
import DiffDockCard from './DiffDockCard';
import GenMolCard from './GenMolCard';
import BinderDesignCard from './BinderDesignCard';
import CrisprOfftargetCard from './CrisprOfftargetCard';
import MetabolismCard from './MetabolismCard';
import NmrSpectrumCard from './NmrSpectrumCard';
import MsmsSpectrumCard from './MsmsSpectrumCard';
import TrustBadgesCard from './TrustBadgesCard';
import QuantumChemBoundaryCard from './QuantumChemBoundaryCard';
import QDiffVisionCard from './QDiffVisionCard';
import SelectivityCard from './SelectivityCard';
import TranslationalSafetyCard from './TranslationalSafetyCard';
import RepliconCard from './RepliconCard';
import { RegulatoryActivityCard, CARDS_EMBEDDING_REGULATORY } from './RegulatoryActivityCard';
import { entriesForPipeline } from '../../services/cardRegistry';
import RejuvenationTherapyCard from './RejuvenationTherapyCard';
import VeterinaryCard from './VeterinaryCard';
import VeterinaryDiscoveryCard from './VeterinaryDiscoveryCard';
import VeterinaryAntibodyProgramCard from './VeterinaryAntibodyProgramCard';
import VeterinaryAntibodyEvidenceCard from './VeterinaryAntibodyEvidenceCard';
import VeterinaryAntibodyGatesCard from './VeterinaryAntibodyGatesCard';
import MoleveraVeterinaryAntibodyDesignCard from './MoleveraVeterinaryAntibodyDesignCard';
import MoleveraVeterinaryDrugProductCard from './MoleveraVeterinaryDrugProductCard';
import MoleveraVeterinaryQuantumCard from './MoleveraVeterinaryQuantumCard';
import DueDiligenceCard from './DueDiligenceCard';
import BioNeMoAugCard from './BioNeMoAugCard';
import AntibodyBenchmarkCard from './AntibodyBenchmarkCard';
import PDCDesignCard from './PDCDesignCard';
import ADARSensorCard from './ADARSensorCard';
import InterimAnalysisCard from './InterimAnalysisCard';
import { QuantumCellCard } from './QuantumCellCard';
import AuditPanel from './AuditPanel';
import QuantumSteeredDesignCard from './QuantumSteeredDesignCard';
import QuantumBiologicDesignCard from './QuantumBiologicDesignCard';
import BioQLGQECard from './BioQLGQECard';
import ActiveCudaQReviewCard from './ActiveCudaQReviewCard';
import GenerativeModelCard from './GenerativeModelCard';
import ConsistencyAuditCard from './ConsistencyAuditCard';
import StructuralReviewCard from './StructuralReviewCard';
import ResultContractCard from './ResultContractCard';
import NirCycleCard from './NirCycleCard';
import NirProteinCard from './NirProteinCard';
import NirEvolveCard from './NirEvolveCard';
import NirDeliverableCard from './NirDeliverableCard';
import MhsDevicePanel from './MhsDevicePanel';
import MhsAssayCard from './MhsAssayCard';
import CrisprTherapeuticCard from './CrisprTherapeuticCard';
import {
  User,
  Zap,
  Copy,
  Check,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  MoreHorizontal,
  ChevronDown,
  ChevronUp,
  Eye,
  Shield,
  Pill,
  Activity,
  FlaskConical,
  Atom,
  Beaker,
  Dna,
  Download,
  FileText,
  Loader2,
} from 'lucide-react';

// Safely coerce a "risk"/label field that may be a string, null, number, or an
// honest-value dict ({value, null_reason, label}) into a display string. The
// de-fabrication turned several tox/admet/pharm fields from plain strings into
// null or HonestValue OBJECTS; rendering an object directly (or calling
// .toLowerCase on it) crashed the whole message tree (black screen). Use this
// everywhere a legacy renderer assumed a string risk value.
function riskStr(v: any): string | null {
  if (v === null || v === undefined) return null;
  if (typeof v === 'string') return v.trim() || null;
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  if (typeof v === 'object') {
    const x = v.value ?? v.null_reason ?? v.label ?? v.text;
    return x === null || x === undefined ? null : String(x);
  }
  return String(v);
}
function isLowRisk(v: any): boolean {
  const s = riskStr(v);
  return !!s && s.toLowerCase() === 'low';
}

// Null-safe numeric accessor. A value may be a number, null/undefined, or an
// honest-value dict ({value, null_reason}). Returns a display string, never an
// object (rendering an object as a React child crashes the tree). For honest
// nulls it returns "N/A" optionally suffixed with the null_reason.
function numOrNA(v: any, decimals: number = 2, suffix: string = ''): string {
  if (v === null || v === undefined) return 'N/A';
  if (typeof v === 'object') {
    const inner = v.value ?? v.val;
    if (inner === null || inner === undefined) {
      const reason = v.null_reason ?? v.reason ?? v.disclaimer;
      return reason ? `N/A — ${String(reason)}` : 'N/A';
    }
    const n = Number(inner);
    return isNaN(n) ? 'N/A' : `${n.toFixed(decimals)}${suffix}`;
  }
  const n = Number(v);
  return isNaN(n) ? 'N/A' : `${n.toFixed(decimals)}${suffix}`;
}

// Honest renderer for a SCIENTIFIC scalar where a literal 0 is almost certainly
// a missing/uncomputed value (e.g. Kd nM, ΔG kcal/mol, humanization score) and
// must NOT be shown as a real "0.0000". Returns a real formatted number when the
// value is a genuine non-zero measurement, otherwise "N/A — <reason>".
function sciNumOrNA(v: any, decimals: number, naReason: string, suffix: string = ''): string {
  let inner: any = v;
  if (v !== null && typeof v === 'object') {
    inner = v.value ?? v.val;
    if (inner === null || inner === undefined) {
      const reason = v.null_reason ?? v.reason ?? v.disclaimer ?? naReason;
      return `N/A — ${String(reason)}`;
    }
  }
  if (inner === null || inner === undefined) return `N/A — ${naReason}`;
  const n = Number(inner);
  if (isNaN(n) || n === 0) return `N/A — ${naReason}`;
  return `${n.toFixed(decimals)}${suffix}`;
}

// Collect honest-null endpoints ({value:null, null_reason}) from a (possibly
// nested) section dict so a renderer can show "field: N/A — reason" rather than
// letting a truthiness gate silently drop the field (making a partial result
// look complete). Returns [prettyLabel, reason] pairs.
function collectHonestNulls(obj: any, maxDepth: number = 3): Array<[string, string]> {
  const out: Array<[string, string]> = [];
  const walk = (o: any, depth: number) => {
    if (!o || typeof o !== 'object' || Array.isArray(o) || depth > maxDepth) return;
    for (const [k, v] of Object.entries(o)) {
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        const hv = v as any;
        if ('value' in hv && (hv.value === null || hv.value === undefined) && ('null_reason' in hv || 'reason' in hv || 'disclaimer' in hv)) {
          const reason = hv.null_reason ?? hv.reason ?? hv.disclaimer ?? 'not computed';
          out.push([k.replace(/_/g, ' '), String(reason)]);
        } else if (!('value' in hv)) {
          walk(hv, depth + 1);
        }
      }
    }
  };
  walk(obj, 0);
  return out;
}

// Render a compact list of honest-null endpoints as "label: N/A — reason" rows.
function HonestNullNotes({ items }: { items: Array<[string, string]> }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mt-2 pt-2 border-t border-dark-700/50 space-y-0.5">
      {items.slice(0, 8).map(([label, reason], i) => (
        <div key={i} className="text-[10px] text-gray-500">
          <span className="capitalize">{label}</span>: <span className="italic">N/A &mdash; {reason}</span>
        </div>
      ))}
    </div>
  );
}

// ── Explicit-card helpers ──────────────────────────────────────────────
// GOAL: every scientific metric shown must be EXPLICIT — (1) value+units,
// (2) one-line plain meaning, (3) HOW it was computed (method + provenance).
// The backend follows a HonestValue contract: a field may arrive as an object
// {value, units, method, provenance, disclaimer, null_reason} OR have sibling
// *_method / *_provenance / *_note keys. These helpers RENDER that context as
// small muted lines under each value, falling back to a correct static label
// of what the metric is when the data carries no method/provenance.

// Pull HonestValue context (method / provenance / units / disclaimer / note)
// off a value object, OR off the parent object via sibling keys
// (<base>_method, <base>_provenance, <base>_units, <base>_note). Never
// fabricates — only surfaces what the data already carries.
function hvMeta(v: any, parent?: any, base?: string): {
  method?: string; provenance?: string; units?: string; disclaimer?: string; note?: string;
} {
  const out: { method?: string; provenance?: string; units?: string; disclaimer?: string; note?: string } = {};
  const take = (x: any) => (x === null || x === undefined || x === '') ? undefined : String(x);
  if (v && typeof v === 'object') {
    out.method = take(v.method);
    out.provenance = take(v.provenance ?? v.source);
    out.units = take(v.units ?? v.unit);
    out.disclaimer = take(v.disclaimer);
    out.note = take(v.note ?? v.null_reason);
  }
  if (parent && typeof parent === 'object' && base) {
    out.method = out.method ?? take(parent[`${base}_method`]);
    out.provenance = out.provenance ?? take(parent[`${base}_provenance`] ?? parent[`${base}_source`]);
    out.units = out.units ?? take(parent[`${base}_units`] ?? parent[`${base}_unit`]);
    out.disclaimer = out.disclaimer ?? take(parent[`${base}_disclaimer`]);
    out.note = out.note ?? take(parent[`${base}_note`]);
  }
  return out;
}

// Render the explicit detail block under a metric value:
//   meaning  → one-line plain-English label of WHAT the metric is
//   units    → only when not already in the value string
//   Method:  → HOW it was computed (from data, else nothing)
//   Source:  → engine / DB provenance (from data, else nothing)
//   note/disclaimer → honest caveats already on the value
// `meaning` is a correct STATIC fallback used only as the plain meaning; method
// and source are NEVER fabricated — they render only when the data supplies them.
function MetricMeta({ meaning, meta, className }: {
  meaning?: string;
  meta?: { method?: string; provenance?: string; units?: string; disclaimer?: string; note?: string };
  className?: string;
}) {
  const m = meta || {};
  if (!meaning && !m.method && !m.provenance && !m.units && !m.disclaimer && !m.note) return null;
  return (
    <div className={cn('mt-0.5 space-y-0.5 text-left', className)}>
      {meaning && <div className="text-[9px] text-gray-500 leading-tight">{meaning}</div>}
      {m.units && <div className="text-[9px] text-gray-400 leading-tight">Units: {m.units}</div>}
      {m.method && <div className="text-[9px] text-gray-500 leading-tight">Method: {m.method}</div>}
      {m.provenance && <div className="text-[9px] text-gray-400 leading-tight">Source: {m.provenance}</div>}
      {m.note && <div className="text-[9px] text-gray-400 italic leading-tight">{m.note}</div>}
      {m.disclaimer && <div className="text-[9px] text-gray-400 italic leading-tight">{m.disclaimer}</div>}
    </div>
  );
}

interface MoleculeData {
  id: string;
  name: string;
  smiles: string;
  score?: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  molecules?: MoleculeData[];
  visualizations?: VisualizationResult[];
}

interface ChatMessageProps {
  message: Message;
}

// Helper: deep-search an object for a key
function deepFind(obj: any, key: string, maxDepth: number = 5): any {
  if (!obj || typeof obj !== 'object' || maxDepth <= 0) return undefined;
  if (key in obj) return obj[key];
  for (const v of Object.values(obj)) {
    const found = deepFind(v, key, maxDepth - 1);
    if (found !== undefined) return found;
  }
  return undefined;
}

// Helper: safe number formatting
function safeNum(v: any, decimals: number = 2): string {
  const n = Number(v);
  return isNaN(n) ? 'N/A' : n.toFixed(decimals);
}

// Smart percent: handles both 0-1 (fractional) and 0-100 (already percent) values
// Unwrap a HonestValue-style object ({value, null_reason, ...}) to a plain
// number-or-null. An honest-null ({value:null}) becomes null (→ "N/A"), never a
// fabricated 0. Plain numbers/strings pass through. This prevents the clinical
// PoS render bug where an honest-null OBJECT is truthy and asPercent(obj) → NaN.
function hvNum(v: any): number | null {
  if (v == null) return null;
  if (typeof v === 'object') {
    if ('value' in v) {
      const inner = (v as any).value;
      return inner == null ? null : Number(inner);
    }
    return null;
  }
  const n = Number(v);
  return isNaN(n) ? null : n;
}

function asPercent(v: any, decimals: number = 0): string {
  const n = Number(v);
  if (isNaN(n)) return 'N/A';
  const pct = n > 1 ? n : n * 100;
  return pct.toFixed(decimals);
}

// Determine color for a score
function scoreColor(v: number, max: number = 1): string {
  if (v == null || isNaN(v)) return 'text-gray-400';
  const norm = max > 1 ? v / max : v;
  if (norm >= 0.7) return 'text-emerald-400';
  if (norm >= 0.4) return 'text-yellow-400';
  return 'text-red-400';
}

function scoreBg(v: number, max: number = 1): string {
  if (v == null || isNaN(v)) return 'bg-dark-700 border-dark-600';
  const norm = max > 1 ? v / max : v;
  if (norm >= 0.7) return 'bg-emerald-500/10 border-emerald-500/20';
  if (norm >= 0.4) return 'bg-yellow-500/10 border-yellow-500/20';
  return 'bg-red-500/10 border-red-500/20';
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const [showToolDetails, setShowToolDetails] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);
  const [reportStatus, setReportStatus] = useState<'idle' | 'generating' | 'done' | 'error'>('idle');
  const [activeMol3dIdx, setActiveMol3dIdx] = useState(0);
  const [qcVizData, setQcVizData] = useState<any>(null); // Quantum Cell animated window
  const [activeClinicalPhase, setActiveClinicalPhase] = useState<'overview' | 'phase1' | 'phase2' | 'phase3' | 'biologics'>('overview');

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  // The pipeline result this message carries, if any: the first completed tool
  // output that parses as an object. The interactive report is built from it.
  const reportResult = useMemo<Record<string, any> | null>(() => {
    for (const tool of message.toolCalls || []) {
      if (tool.status !== 'completed' || !tool.output) continue;
      let data: any = tool.output;
      if (typeof data === 'string') {
        try { data = JSON.parse(data); } catch { continue; }
      }
      if (data && typeof data === 'object' && !Array.isArray(data)) return data;
    }
    return null;
  }, [message.toolCalls]);
  const reportSessionId = String(
    (reportResult as any)?.session_id || (reportResult as any)?.result?.session_id || ''
  ) || undefined;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ── Download Full Report (PDF + figures + data) ──
  const handleDownloadReport = async (format: 'pdf' | 'json' | 'zip' = 'pdf') => {
    if (reportStatus === 'generating') return;
    setReportStatus('generating');
    try {
      // Collect raw tool output for the report generator
      let pipelineResult: any = null;
      if (message.toolCalls) {
        for (const tool of message.toolCalls) {
          if (tool.status === 'completed' && tool.output) {
            let data = tool.output;
            if (typeof data === 'string') {
              try { data = JSON.parse(data); } catch { continue; }
            }
            if (data && typeof data === 'object') {
              pipelineResult = data;
              break;
            }
          }
        }
      }
      if (!pipelineResult) {
        setReportStatus('error');
        setTimeout(() => setReportStatus('idle'), 3000);
        return;
      }
      const resp = await fetch('/api/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pipeline_result: pipelineResult,
          report_type: 'full',
          format: format,
          branding: 'spectrix',
        }),
      });
      if (!resp.ok) throw new Error(`Report generation failed: ${resp.status}`);
      const result = await resp.json();
      // Download the PDF if available
      const pdfUrl = result.pdf_url || result.pdf_path;
      const sessionId = result.session_id;
      let downloaded = false;
      if (pdfUrl && sessionId) {
        const dlUrl = pdfUrl.startsWith('/') ? pdfUrl : `/api/reports/download/${sessionId}/${pdfUrl}`;
        try {
          const pdfResp = await fetch(dlUrl);
          if (pdfResp.ok) {
            const blob = await pdfResp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `BioQL_Report_${sessionId}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            downloaded = true;
          }
        } catch { /* PDF fetch failed, will fallback */ }
      }
      // Fallback: download pipeline result as JSON when PDF is unavailable
      if (!downloaded) {
        downloadJSON(pipelineResult, `BioQL_Report_${sessionId || Date.now()}`);
      }
      setReportStatus('done');
      setTimeout(() => setReportStatus('idle'), 4000);
    } catch (err) {
      console.error('Report download error:', err);
      setReportStatus('error');
      setTimeout(() => setReportStatus('idle'), 4000);
    }
  };

  const formatTime = (date: Date | string) => {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (!(d instanceof Date) || isNaN(d.getTime())) return '';
    return d.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Parse markdown-like content
  const renderContent = (content: string) => {
    const parts = content.split(/(^```[\s\S]*?```)/gm);

    return parts.map((part, index) => {
      if (part.startsWith('```')) {
        const match = part.match(/```(\w+)?\n?([\s\S]*?)```/);
        if (match) {
          const [, lang, code] = match;
          return (
            <div key={index} className="my-4 rounded-lg overflow-hidden border border-dark-700">
              <div className="flex items-center justify-between px-3 py-2 bg-dark-800 border-b border-dark-700">
                <span className="text-xs text-gray-400">{lang || 'code'}</span>
                <button
                  onClick={() => navigator.clipboard.writeText(code.trim())}
                  className="text-xs text-gray-400 hover:text-white transition-colors cursor-pointer rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                >
                  Copy
                </button>
              </div>
              <pre className="p-4 bg-dark-900 overflow-x-auto">
                <code className="text-sm text-gray-300 font-mono">{code.trim()}</code>
              </pre>
            </div>
          );
        }
      }

      return (
        <div key={index} className="prose prose-invert prose-sm max-w-none">
          {part.split('\n').map((line, lineIndex) => {
            if (line.startsWith('### ')) {
              return (
                <h3 key={lineIndex} className="text-base font-semibold text-white mt-4 mb-2">
                  {line.slice(4)}
                </h3>
              );
            }
            if (line.startsWith('## ')) {
              return (
                <h2 key={lineIndex} className="text-lg font-semibold text-white mt-5 mb-3">
                  {line.slice(3)}
                </h2>
              );
            }

            if (line.match(/^\d+\.\s/)) {
              return (
                <div key={lineIndex} className="flex gap-2 my-1">
                  <span className="text-quantum-400 font-medium">{line.match(/^\d+/)?.[0]}.</span>
                  <span>{line.replace(/^\d+\.\s/, '')}</span>
                </div>
              );
            }
            if (line.startsWith('- ')) {
              return (
                <div key={lineIndex} className="flex gap-2 my-1">
                  <span className="text-molecular-400">&bull;</span>
                  <span>{line.slice(2)}</span>
                </div>
              );
            }

            if (line.startsWith('|') && line.endsWith('|') && line.includes('---')) return null; // Only drop separator rows

            const escaped = line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            const boldParsed = escaped.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>');

            if (!line.trim()) return <br key={lineIndex} />;

            return (
              <p
                key={lineIndex}
                className="my-1 text-gray-300"
                dangerouslySetInnerHTML={{ __html: boldParsed }}
              />
            );
          })}
        </div>
      );
    });
  };

  // ═══════════════════════════════════════════════════════════════
  // EXTRACT ALL PIPELINE DATA FROM TOOL OUTPUTS
  // This is the KEY function that makes results show in the chat
  // ═══════════════════════════════════════════════════════════════
  const extractPipelineData = () => {
    if (!message.toolCalls) return null;

    let enrichment: Record<string, any> = {};
    let hasSomething = false;

    for (const tool of message.toolCalls) {
      if (tool.status !== 'completed' || !tool.output) continue;

      let data: any = tool.output;
      if (typeof data === 'string') {
        try { data = JSON.parse(data); } catch { continue; }
      }

      // Navigate into nested result objects
      const root = data?.result || data;
      if (!root || typeof root !== 'object') continue;
      const discovery = root?.discovery || {};
      const isAntibodyPipeline = String(tool.name || '').includes('antibody')
        || String(root?.pipeline || '').toLowerCase().includes('antibody');

      // --- Protenix structure data ---
      const protenixStage = root?.stages?.['7b_protenix_structure']
        || root?.stages?.structure_prediction?.predictions?.[0]
        || root?.analyses?.protenix_structure
        || root?.best_candidate?.analyses?.protenix_structure
        || root?.best_candidate?.protenix_structure
        || root?.candidates?.[0]?.analyses?.protenix_structure
        || root?.candidates?.[0]?.protenix_structure
        || deepFind(root, 'protenix_structure')
        || root?.protenix
        || null;
      if (protenixStage && !protenixStage.error && (protenixStage.confidence || protenixStage.iptm != null)) {
        enrichment.protenix = {
          confidence: protenixStage.confidence || {
            plddt: protenixStage.plddt,
            ptm: protenixStage.ptm,
            iptm: protenixStage.iptm,
            ranking_score: protenixStage.ranking_score,
          },
          all_samples: protenixStage.all_samples || root.all_samples,
          per_residue_plddt: protenixStage.per_residue_plddt || root.per_residue_plddt,
          prediction_time_seconds: protenixStage.prediction_time_seconds,
          model_used: protenixStage.model_used,
          gpu: protenixStage.gpu,
          structure_cif: protenixStage.structure_cif || root.structure_cif,
          job_id: protenixStage.job_id,
        };
        hasSomething = true;
      }

      // --- 3D structure + docking data ---
      const mol3d = root?.mol_3d || root?.stages?.['10_3d_structure']?.mol_block || root?.best_candidate?.mol_3d || root?.candidates?.[0]?.mol_3d;
      if (mol3d) {
        enrichment.mol3d = mol3d;
        hasSomething = true;
      }
      const dockingData = root?.stages?.['9_docking'] || root?.stages?.['6_docking']
        || root?.docking
        || root?.best_candidate?.analyses?.docking
        || root?.best_candidate?.docking
        || root?.candidates?.[0]?.analyses?.docking
        || root?.candidates?.[0]?.docking
        || root?.analyses?.docking;
      if (dockingData && typeof dockingData === 'object' && (dockingData.status === 'completed' || dockingData.binding_affinity_kcal != null || dockingData.poses != null || dockingData.poses_generated != null)) {
        enrichment.docking = dockingData;
        hasSomething = true;
      } else if (isAntibodyPipeline) {
        const affinityCandidate = root?.best_candidate || root?.candidates?.[0] || {};
        const kd = affinityCandidate?.kd_nM || affinityCandidate?.kd_nm || affinityCandidate?.scores?.kd_nm || root?.stages?.binding_affinity?.kd_estimates_nm?.[0];
        const bindingEnergy = affinityCandidate?.binding_affinity_kcal || affinityCandidate?.scores?.binding_energy || root?.stages?.binding_affinity?.binding_energies?.[0];
        if (kd != null || bindingEnergy != null) {
          enrichment.docking = {
            status: 'completed',
            method: 'antibody_vqe_binding_affinity',
            pdb_id: root?.pdb_id || root?.metadata?.pdb_id || root?.stages?.target_analysis?.pdb_id,
            kd_nM: kd,
            binding_affinity_kcal: bindingEnergy,
            poses_generated: root?.stages?.structure_prediction?.predictions?.length,
          };
          hasSomething = true;
        }
      }

      // --- ADMET data ---
      // Check all pipeline layouts: custom_molecule stages, top-level, candidate analyses, then deepFind
      // deepFind can match scoring.admet (just weights) instead of real ADMET — check for absorption key
      const _rawAdmet = root?.stages?.['2_admet']?.data
        || root?.admet
        || root?.analyses?.admet
        || root?.best_candidate?.analyses?.admet
        || root?.best_candidate?.admet
        || root?.candidates?.[0]?.analyses?.admet
        || root?.candidates?.[0]?.admet;
      // Only fall back to deepFind if nothing found, and validate it has real ADMET categories
      let admetData = _rawAdmet;
      if (!admetData) {
        const _deep = deepFind(root, 'admet');
        // Validate: real ADMET data has absorption/distribution/metabolism keys, not just score/weight
        if (_deep && typeof _deep === 'object' && ('absorption' in _deep || 'distribution' in _deep || 'metabolism' in _deep || 'parameters_count' in _deep)) {
          admetData = _deep;
        }
      }
      if (admetData && typeof admetData === 'object' && !admetData.error) {
        enrichment.admet = admetData;
        hasSomething = true;
      }

      // --- Candidates with scoring ---
      let candidates = root?.candidates || discovery?.candidates || [];
      // Unwrap candidates_generated nested structure
      if (!Array.isArray(candidates) || candidates.length === 0) {
        const cg = root?.candidates_generated || discovery?.candidates_generated || {};
        const unwrapped = [
          ...(Array.isArray(cg.small_molecules) ? cg.small_molecules : []),
          ...(Array.isArray(cg.peptides) ? cg.peptides : []),
          ...(Array.isArray(cg.nanobodies) ? cg.nanobodies : []),
        ];
        if (unwrapped.length > 0) candidates = unwrapped;
      }
      if (Array.isArray(candidates) && candidates.length > 0) {
        enrichment.candidates = candidates;
        hasSomething = true;
      }

      // --- Composite score ---
      const topCandidateForScore = root?.best_candidate || root?.best_candidate_full || (Array.isArray(candidates) ? candidates[0] : null);
      const compositeScore = root?.composite_score ?? topCandidateForScore?.composite_score ?? topCandidateForScore?.score ?? topCandidateForScore?.scores?.composite_score;
      if (compositeScore != null) {
        enrichment.compositeScore = compositeScore;
        enrichment.drugClass = root?.stages?.['11_scoring']?.drug_candidate_class
          || root?.stages?.['8_scoring']?.drug_candidate_class
          || root?.drug_candidate_class
          || topCandidateForScore?.drug_candidate_class
          || topCandidateForScore?.compound_class
          // No backend-provided class: derive a UI-only heuristic label and mark
          // it as such so it is never mistaken for a computed classification.
          || (compositeScore >= 0.75 ? 'Excellent (UI-derived)' : compositeScore >= 0.50 ? 'Good (UI-derived)' : compositeScore >= 0.25 ? 'Moderate (UI-derived)' : 'Poor (UI-derived)');
        hasSomething = true;
      }

      // --- Toxicology data ---
      const toxData = root?.stages?.['3_toxicology']?.data
        || root?.toxicology
        || root?.toxicology_study
        || root?.admet?.toxicology
        || root?.analyses?.toxicology
        || root?.best_candidate?.analyses?.toxicology
        || root?.best_candidate?.toxicology
        || root?.best_candidate?.admet?.toxicology
        || root?.candidates?.[0]?.analyses?.toxicology
        || root?.candidates?.[0]?.toxicology
        || root?.candidates?.[0]?.admet?.toxicology
        || discovery?.toxicology
        || root?.stages?.['7_toxicology']?.data
        || (root?.acute_toxicity ? root : null)
        || (root?.ada_risk ? root : null);
      if (toxData && typeof toxData === 'object' && (toxData.acute_toxicity || toxData.organ_toxicity || toxData.genotoxicity || toxData.ada_risk || toxData.overall_safety || toxData.cytokine_release_risk)) {
        enrichment.toxicology = toxData;
        hasSomething = true;
      }

      // --- Pharmacology data ---
      const pharmData = root?.stages?.['4_pharmacology']?.data
        || root?.pharmacology
        || root?.pharmacology_study
        || root?.analyses?.pharmacology
        || root?.best_candidate?.analyses?.pharmacology
        || root?.best_candidate?.pharmacology
        || root?.candidates?.[0]?.analyses?.pharmacology
        || root?.candidates?.[0]?.pharmacology
        || discovery?.pharmacology
        || (root?.pharmacokinetics ? root : null);
      if (pharmData && typeof pharmData === 'object' && (pharmData.pharmacokinetics || pharmData.pharmacodynamics)) {
        enrichment.pharmacology = pharmData;
        hasSomething = true;
      } else if (isAntibodyPipeline) {
        const pkCandidate = root?.best_candidate || root?.candidates?.[0] || {};
        const admet = pkCandidate?.admet || root?.admet || {};
        const halfLife = admet?.excretion?.half_life_days || pkCandidate?.half_life || pkCandidate?.half_life_days;
        if (halfLife != null || admet?.administration_route) {
          enrichment.pharmacology = {
            status: 'completed',
            target: root?.target,
            mechanism: 'antibody antigen binding and biologics PK/PD',
            pharmacokinetics: {
              administration: admet?.administration_route || 'IV/SC',
              half_life_days: halfLife,
              clearance_ml_day_kg: admet?.metabolism?.clearance_ml_day_kg,
              sc_bioavailability_pct: admet?.absorption?.sc_bioavailability_pct,
            },
            pharmacodynamics: {
              kd_nM: pkCandidate?.kd_nM || pkCandidate?.kd_nm || pkCandidate?.scores?.kd_nm,
              clinical_success_probability: pkCandidate?.clinical_success_prob || pkCandidate?.scores?.clinical_success_prob,
            },
          };
          hasSomething = true;
        }
      }

      // --- Clinical trial data ---
      const clinicalData = root?.stages?.['5_clinical_trial']?.data
        || root?.stages?.clinical_trial_simulation?.trials?.[0]
        || root?.clinical_trial
        || root?.clinical_trials
        || root?.analyses?.clinical_trial
        || root?.best_candidate?.analyses?.clinical_trial
        || root?.best_candidate?.clinical_trial
        || root?.candidates?.[0]?.analyses?.clinical_trial
        || root?.candidates?.[0]?.clinical_trial
        || (root?.phase_I ? root : null)
        || (root?.phase_1 ? root : null);
      if (clinicalData && typeof clinicalData === 'object' && (clinicalData.phase_I || clinicalData.phase_1 || clinicalData.phase_II || clinicalData.phase_2 || clinicalData.phase_III || clinicalData.phase_3 || clinicalData.development_summary)) {
        enrichment.clinical = clinicalData;
        hasSomething = true;
      }

      // --- Legacy enrichment fields ---
      if (root.validation) enrichment.validation = root.validation;
      if (root.provenance || root.best_candidate_full?.provenance) {
        enrichment.provenance = root.provenance || root.best_candidate_full?.provenance;
        hasSomething = true;
      }
      if (root.insights || root.best_candidate_full?.insights) {
        enrichment.insights = root.insights || root.best_candidate_full?.insights;
        hasSomething = true;
      }
      if (root.scoring_methodology) enrichment.scoringMethodology = root.scoring_methodology;
      const scoreBd = root.best_candidate_full?.score_breakdown || root.score_breakdown;
      if (scoreBd) { enrichment.scoreBreakdown = scoreBd; hasSomething = true; }
      if (root.molecular_relationships || root.best_candidate_full?.molecular_relationships) {
        enrichment.molecularRelationships = root.molecular_relationships || root.best_candidate_full?.molecular_relationships;
        hasSomething = true;
      }
      if (root.external_validation) { enrichment.externalValidation = root.external_validation; hasSomething = true; }
      if (root.low_confidence_warning) enrichment.lowConfidenceWarning = root.low_confidence_warning;

      // --- Best candidate (for SMILES display) ---
      const bestCandidate = root?.best_candidate || root?.best_candidate_full || (candidates[0] || null);
      if (bestCandidate?.smiles || bestCandidate?.sequence || bestCandidate?.vh_sequence || bestCandidate?.cdr_h3) {
        enrichment.bestCandidate = bestCandidate;
        hasSomething = true;
      }

      // --- IBM Job IDs ---
      const jobIds = root?.ibm_job_ids || root?.best_candidate?.ibm_job_ids || deepFind(root, 'ibm_job_ids');
      if (Array.isArray(jobIds) && jobIds.length > 0) {
        enrichment.ibmJobIds = jobIds;
        hasSomething = true;
      }

      // --- Iterative optimization results ---
      const optData = root?.optimization;
      if (optData && typeof optData === 'object' && optData.mode === 'iterative_quantum_optimization') {
        enrichment.optimization = optData;
        hasSomething = true;
      }

      // --- Pipeline stages summary ---
      if (root?.stages && typeof root.stages === 'object') {
        enrichment.stagesSummary = Object.entries(root.stages).map(([key, val]: [string, any]) => ({
          name: val?.stage || key,
          // No status reported by the backend: use an explicit 'not reported'
          // sentinel rather than the ambiguous 'unknown' placeholder.
          status: val?.status || 'not_reported',
        }));
        hasSomething = true;
      }

      // --- Protenix enrichment in tox/pharm/clinical ---
      for (const section of ['toxicology', 'pharmacology', 'clinical']) {
        const sectionData = enrichment[section];
        if (sectionData?.protenix_structure && !enrichment.protenix) {
          const ps = sectionData.protenix_structure;
          enrichment.protenixEnrichment = {
            iptm: ps.iptm,
            ptm: ps.ptm,
            plddt: ps.plddt,
            binding_confidence: ps.binding_confidence || ps.binding_pose_quality || ps.structure_supports_clinical,
          };
          hasSomething = true;
        }
      }

      // --- Biomolecules (therapeutic_peptides, antibody_fragments, enzyme_mimetics) ---
      const biomolecules = root?.biomolecules || root?.result?.biomolecules;
      if (biomolecules && typeof biomolecules === 'object') {
        const bioData: Record<string, any> = {};
        for (const [key, val] of Object.entries(biomolecules) as [string, any][]) {
          if (val && typeof val === 'object' && Array.isArray(val.candidates) && val.candidates.length > 0) {
            bioData[key] = val;
          }
        }
        if (Object.keys(bioData).length > 0) {
          enrichment.biomolecules = bioData;
          enrichment.biomoleculesTarget = root?.target || biomolecules?.target;
          enrichment.biomoleculesBackend = root?.quantum_backend || root?.hardware;
          enrichment.biomoleculesTotalTime = root?.total_time_seconds;
          hasSomething = true;
        }
      }

      // --- Quantum Cell Validation (Molevera) ---
      const qcellData = root?.quantum_cell_validation
        || root?.result?.quantum_cell_validation
        || root?.cell_simulation
        || root?.result?.cell_simulation;
      if (qcellData && typeof qcellData === 'object' && qcellData.success !== false) {
        enrichment.quantumCell = qcellData;
        hasSomething = true;
      }
      // Quantum Cell inline toxicology
      const qcellTox = root?.quantum_cell_toxicology || root?.result?.quantum_cell_toxicology;
      if (qcellTox && typeof qcellTox === 'object' && qcellTox.success !== false) {
        enrichment.quantumCellTox = qcellTox;
        hasSomething = true;
      }
      // Quantum Cell inline pharmacology
      const qcellPharm = root?.quantum_cell_pharmacology || root?.result?.quantum_cell_pharmacology;
      if (qcellPharm && typeof qcellPharm === 'object' && qcellPharm.success !== false) {
        enrichment.quantumCellPharm = qcellPharm;
        hasSomething = true;
      }

      // --- Pipeline images (molecule_2d, admet_radar, toxicity_heatmap, etc.) ---
      const rawImages = root?.images || root?.visualizations?.images || discovery?.images;
      if (Array.isArray(rawImages) && rawImages.length > 0) {
        const validImages = rawImages.filter((img: any) => img && img.image);
        if (validImages.length > 0) {
          enrichment.pipelineImages = validImages;
          hasSomething = true;
        }
      }

      // --- Universal visualization envelope (backend _attach_visualizations) ---
      // Emitted by ALL pipelines: antibody / peptide / small-molecule / mRNA.
      const vizEnvelope = root?.visualization || data?.visualization;
      if (vizEnvelope && typeof vizEnvelope === 'object' && !enrichment.visualization) {
        enrichment.visualization = vizEnvelope;
        hasSomething = true;
      }

      // --- Q-DiffVision (direct tool or automatic nested pipeline stage) ---
      const qdiffvision = root?.pipeline === 'qdiffvision_v1'
        ? root
        : (root?.qdiffvision || deepFind(root, 'qdiffvision'));
      if (qdiffvision && typeof qdiffvision === 'object' && !enrichment.qdiffvision) {
        enrichment.qdiffvision = qdiffvision;
        hasSomething = true;
      }

      // --- 3D structure (PDB) for the molecule viewer (mRNA/peptide/antibody) ---
      // The human antibody engine stores its folded lead under
      // stages.chai1_structure.pdb (NOT structure_3d), so include chai1_structure
      // as a source — otherwise the designed antibody never renders and only the
      // separately-fetched antigen shows.
      const _chai = deepFind(root, 'chai1_structure');
      const _struct = root?.structure_3d || root?.mol_3d || deepFind(root, 'structure_3d') || _chai;
      const _pdb = _struct?.pdb || _struct?.pdb_data || root?.pdb_data || root?.complex_pdb
        || root?.stages?.['2_structure_prediction']?.complex_pdb;
      if (!enrichment.structure3dPdb && typeof _pdb === 'string' && _pdb.includes('ATOM')) {
        enrichment.structure3dPdb = _pdb;
        enrichment.structure3dMeta = { plddt: _struct?.plddt, length_aa: _struct?.length_aa, method: _struct?.method || _struct?.structure_backend };
        hasSomething = true;
      }

      // --- COMPLEX structure (real protein+partner pose: peptide:receptor OR
      // antibody:antigen). chai1_structure with is_complex is the antibody-antigen
      // complex the human engine folds. ---
      const _cx = root?.complex_structure_3d || deepFind(root, 'complex_structure_3d')
        || (_chai && _chai.is_complex && typeof _chai.pdb === 'string' && _chai.pdb.includes('ATOM') ? _chai : null);
      if (!enrichment.complexPdb && typeof _cx?.pdb === 'string' && _cx.pdb.includes('ATOM')) {
        enrichment.complexPdb = _cx.pdb;
        enrichment.complexMeta = { iptm: _cx.iptm, receptor: _cx.receptor, chains: _cx.chains || _cx.chains_folded, note: _cx.note };
        hasSomething = true;
      }

      // --- Receptor binding panel (peptide:receptor complex ipTM = real "docking") ---
      const _rp = deepFind(root, 'receptor_panel');
      if (!enrichment.receptorPanel && _rp && typeof _rp === 'object' && !Array.isArray(_rp)) {
        enrichment.receptorPanel = _rp;
        hasSomething = true;
      }

      // ── NEW calculation cards extraction (additive, defensive; cards no-op when absent) ──
      try {
        if (!enrichment.fep) {
          const _fep = deepFind(root, 'fep_rbfe_alchemical') || deepFind(root, 'fep_rbfe');
          if (_fep && typeof _fep === 'object') { enrichment.fep = _fep; hasSomething = true; }
        }
        if (!enrichment.diffdock) {
          const _dd = (root && (root as any).engine === 'diffdock-l-nim') ? root
            : (root && (root as any).docking && (root as any).docking.engine === 'diffdock-l-nim') ? (root as any).docking
            : (deepFind(root, 'diffdock') || null);
          if (_dd && typeof _dd === 'object') { enrichment.diffdock = _dd; hasSomething = true; }
        }
        if (!enrichment.genmol) {
          const _topology = deepFind(root, 'topology_generation');
          const _gm = deepFind(root, 'generative_genmol') || deepFind(root, 'genmol')
            || (_topology?.executed && Array.isArray(_topology?.candidates)
              ? { ..._topology, molecules: _topology.candidates, n: _topology.candidates.length,
                  source: _topology.provenance || _topology.engine }
              : null);
          if (_gm && typeof _gm === 'object') { enrichment.genmol = _gm; hasSomething = true; }
        }
        if (!enrichment.binder) {
          const _bd = deepFind(root, 'denovo_scaffold') || deepFind(root, 'denovo_binder_design');
          if (_bd && typeof _bd === 'object') { enrichment.binder = _bd; hasSomething = true; }
        }
        if (!enrichment.crispr) {
          if (deepFind(root, 'offtarget') || deepFind(root, 'guides')) { enrichment.crispr = root; hasSomething = true; }
        }
        if (!enrichment.metabolism) {
          const _som = deepFind(root, 'site_of_metabolism');
          const _cl = deepFind(root, 'pk_clearance');
          const _hl = deepFind(root, 'pk_half_life');
          if (_som || _cl || _hl) { enrichment.metabolism = { site_of_metabolism: _som, pk_clearance: _cl, pk_half_life: _hl }; hasSomething = true; }
        }
        if (!enrichment.qchem) {
          const _qc = deepFind(root, 'quantum_chem_advantage_boundary');
          if (_qc && typeof _qc === 'object') { enrichment.qchem = _qc; hasSomething = true; }
        }
        if (!enrichment.nmrSpectrum) {
          const _nmr = root?.nmr_spectrum || deepFind(root, 'nmr_spectrum');
          if (_nmr && typeof _nmr === 'object' && (_nmr.spectrum_1h || _nmr.per_residue)) {
            enrichment.nmrSpectrum = _nmr; hasSomething = true;
          }
        }
        if (!enrichment.msmsSpectrum) {
          const _ms = root?.msms_spectrum || deepFind(root, 'msms_spectrum');
          if (_ms && typeof _ms === 'object' && _ms.predicted_spectrum) {
            enrichment.msmsSpectrum = _ms; hasSomething = true;
          }
        }
        if (!enrichment.trustBadges) {
          const _badges: any[] = [];
          const _walk = (o: any, d: number) => {
            if (!o || typeof o !== 'object' || d <= 0) return;
            if (Array.isArray(o)) { o.forEach((x) => _walk(x, d - 1)); return; }
            const hasStatusBanner = ('status' in o) && Array.isArray((o as any).messages);
            const looksTrust = (('validated' in o) || ('component' in o) || ('badge' in o)) && !hasStatusBanner;
            if (looksTrust) _badges.push(o);
            Object.values(o).forEach((v) => _walk(v, d - 1));
          };
          _walk(root, 5);
          if (_badges.length) { enrichment.trustBadges = _badges; hasSomething = true; }
        }
        if (!enrichment.selectivity) {
          // selectivity_panel engine output: profile_compound / build_selectivity_matrix
          // (also accepts the quantum-proxy selectivity_profiler shape). deepFind for
          // 'selectivity_panel' first, then a bare 'selectivity' fallback.
          const _sel = deepFind(root, 'selectivity_panel') || deepFind(root, 'selectivity');
          if (
            _sel && typeof _sel === 'object' &&
            (
              // Shape A: profile_compound
              (_sel as any).selectivity_score != null ||
              (_sel as any).n_tested != null ||
              ((_sel as any).targets && typeof (_sel as any).targets === 'object' && !Array.isArray((_sel as any).targets)) ||
              // Shape B: build_selectivity_matrix
              ((_sel as any).matrix && Array.isArray((_sel as any).compounds) && Array.isArray((_sel as any).targets)) ||
              // Shape C: quantum-proxy
              (Array.isArray((_sel as any).off_targets) && (_sel as any).primary_target)
            )
          ) { enrichment.selectivity = _sel; hasSomething = true; }
        }
        // ── Translational safety + functional engagement (additive; emitted by the
        //    small-molecule enrichment in _run_custom_molecule). Consolidated into one card. ──
        if (!enrichment.translational) {
          const _sa = deepFind(root, 'structural_alerts');
          const _dose = deepFind(root, 'dose_response_model');
          const _pgx = deepFind(root, 'pharmacogenomics');
          const _func = deepFind(root, 'functional_engagement');
          if (_sa || _dose || _pgx || _func) {
            enrichment.translational = {
              structuralAlerts: _sa || null,
              doseResponse: _dose || null,
              pgx: _pgx || null,
              functional: _func || null,
            };
            hasSomething = true;
          }
        }
        // ── Rejuvenation therapy designer (emitted by /api/aging/design). ──
        // Se reconoce por el nombre del diseñador o por la puerta de mecanismo,
        // que existe en LOS DOS caminos (ejecutado y cortado).
        if (!enrichment.rejuvenation) {
          const isRejuv = root?.designer === 'therapy_designer'
            || root?.stopped_at_gate === true
            || (root?.gate?.recommended_route?.key && root?.gate?.disease_id);
          if (isRejuv) {
            enrichment.rejuvenation = root;
            hasSomething = true;
          }
        }
        // ── Viral replicon workbench (additive; emitted by replicon_pipeline). ──
        if (!enrichment.replicon) {
          const isReplicon = root?.pipeline === 'replicon_workbench_v1'
            || (deepFind(root, 'replicon_design') && (deepFind(root, 'genome') || root?.virus_query))
            || deepFind(root, 'compute_stack')?.architecture === 'hybrid quantum + LLM + ML';
          if (isReplicon) {
            enrichment.replicon = root?.pipeline === 'replicon_workbench_v1'
              ? root
              : {
                  genome: deepFind(root, 'genome'),
                  replicon_design: deepFind(root, 'replicon_design'),
                  antiviral_discovery: deepFind(root, 'antiviral_discovery'),
                  compute_stack: deepFind(root, 'compute_stack'),
                  llm_analysis: deepFind(root, 'llm_analysis'),
                  summary: deepFind(root, 'summary'),
                  virus_query: root?.virus_query,
                  branch: root?.branch,
                };
            hasSomething = true;
          }
        }
        // ── MOLEVERA / BIOQL veterinary antibody DRUG DESIGN. ──
        // This mirrors the human antibody discovery pipeline while preserving
        // animal framework, antigen, product and species-immunogenicity truth.
        if (!enrichment.moleveraVeterinaryAntibodyDesign) {
          const nestedDesign = deepFind(root, 'molevera_veterinary_antibody_design');
          const isDesign = root?.pipeline === 'molevera_veterinary_antibody_design_v1'
            || nestedDesign?.pipeline === 'molevera_veterinary_antibody_design_v1';
          if (isDesign) {
            enrichment.moleveraVeterinaryAntibodyDesign = root?.pipeline === 'molevera_veterinary_antibody_design_v1'
              ? root
              : nestedDesign;
            hasSomething = true;
          }
        }
        // ── Configuration-driven veterinary-antibody RESEARCH program. ──
        // Keep the full root contract so the three cards jointly render every
        // configured source, record, target, gate, phase, action, and artifact.
        if (!enrichment.veterinaryAntibodyProgram) {
          const nestedProgram = deepFind(root, 'veterinary_antibody_program');
          const isProgram = root?.pipeline === 'veterinary_antibody_program_v1'
            || nestedProgram?.pipeline === 'veterinary_antibody_program_v1';
          if (isProgram) {
            enrichment.veterinaryAntibodyProgram = root?.pipeline === 'veterinary_antibody_program_v1'
              ? root
              : nestedProgram;
            hasSomething = true;
          }
        }
        // ── Veterinary drug study (additive; emitted by veterinary_pipeline.py). ──
        if (!enrichment.veterinary) {
          const isDiscoveryVet = root?.pipeline === 'veterinary_discovery_v1' || root?.mode === 'discovery';
          const isVet = !isDiscoveryVet && (
            root?.pipeline === 'veterinary_v1'
            || (root?.study_type === 'VETERINARY' && deepFind(root, 'per_species'))
            || (deepFind(root, 'per_species') && deepFind(root, 'veterinary_assessment')));
          if (isVet) {
            enrichment.veterinary = root?.pipeline === 'veterinary_v1'
              ? root
              : (deepFind(root, 'veterinary_assessment') ? { ...deepFind(root, 'veterinary_assessment'), pipeline: 'veterinary_v1' } : root);
            hasSomething = true;
          }
        }
        // ── Veterinary drug DISCOVERY (additive; emitted by veterinary_discovery.py). ──
        if (!enrichment.veterinaryDiscovery) {
          const isVetD = root?.pipeline === 'veterinary_discovery_v1'
            || (root?.study_type === 'VETERINARY' && root?.mode === 'discovery')
            || deepFind(root, 'veterinary_discovery');
          if (isVetD) {
            enrichment.veterinaryDiscovery = root?.pipeline === 'veterinary_discovery_v1'
              ? root
              : (deepFind(root, 'veterinary_discovery') || root);
            hasSomething = true;
          }
        }
        // ── Quantum biologic design (additive): antibody CDR-H3 QAOA, peptide QAOA +
        //    SQD, end-to-end biologic dock+quantum, or the quantum_core_optimization graft. ──
        if (!enrichment.quantumBiologic) {
          const p = root?.pipeline;
          if (p === 'quantum_antibody_cdr_qaoa_v1'
              || p === 'quantum_peptide_design_complete_v1'
              || p === 'endtoend_biologic_complete_v1') {
            enrichment.quantumBiologic = root;
            hasSomething = true;
          } else {
            // grafted annotation inside a replicon/mRNA de-novo peptide result
            const qco = deepFind(root, 'quantum_core_optimization');
            if (qco && qco.quantum_optimized_core) {
              enrichment.quantumBiologic = qco;
              hasSomething = true;
            }
          }
        }
        // ── Trained generative model provenance (ESM-2 / IgLM). ──
        if (!enrichment.generativeModel) {
          const trained = deepFind(root, 'trained_generator');
          const iglm = deepFind(root, 'iglm_proposer');
          if (trained || iglm) {
            enrichment.generativeModel = {
              trained_generator: trained,
              iglm_proposer: iglm,
            };
            hasSomething = true;
          }
        }
        if (!enrichment.consistencyAudit) {
          const consistency = deepFind(root, 'consistency_audit');
          if (consistency) {
            enrichment.consistencyAudit = consistency;
            hasSomething = true;
          }
        }
        // ── Revisión estructural: "¿se puede druggar, y dónde?" (/api/structure/review).
        // Se reconoce por el marcador `pipeline` que emite el backend, no por
        // heurística de forma: así nunca se captura el payload de otro pipeline.
        // ── Contrato de resultado transversal (bioql_result_card_v1). Cualquier
        // pipeline que lo emita se pinta con la MISMA tarjeta, sin logica por pipeline.
        if (!enrichment.resultContract) {
          const isCard = (o: any) => o && typeof o === 'object'
            && o.card === 'bioql_result_card_v1';
          const rc = isCard(root) ? root
            : (isCard(root?.result_card) ? root.result_card : null);
          if (rc) { enrichment.resultContract = rc; hasSomething = true; }
        }
        // ── AlphaGenome: capa reguladora universal.
        // Todo pipeline pasado por alphagenome_regulatory.attach() emite la
        // MISMA clave `regulatory`, asi que una sola deteccion cubre a todos,
        // incluidos los que no tienen tarjeta propia.
        if (!enrichment.regulatory) {
          const rg = (root && typeof root === 'object' && (root as any).regulatory)
            || deepFind(root, 'regulatory');
          if (rg && typeof rg === 'object' && ('available' in rg)) {
            enrichment.regulatory = rg;
            // Remember which pipeline produced it, so the render step can ask
            // cardRegistry whether a dedicated card already draws the section.
            enrichment.regulatoryPipeline =
              (root as any)?.pipeline || (root as any)?.module || null;
            hasSomething = true;
          }
        }
        // Pipeline terapeutico CRISPR: detectado por forma.
        if (!enrichment.crisprTherapeutic) {
          const isCt = (o: any) => o && typeof o === 'object'
            && o.module === 'crispr_therapeutic_pipeline';
          const cand = isCt(root) ? root : (isCt(root?.crispr_therapeutic) ? root.crispr_therapeutic : null);
          if (cand) { enrichment.crisprTherapeutic = cand; hasSomething = true; }
        }
        // Bucle de ensayo MHS: detectado por forma.
        if (!enrichment.mhsAssay) {
          const isAs = (o: any) => o && typeof o === 'object'
            && o.module === 'mhs_assay_engine';
          const cand = isAs(root) ? root : (isAs(root?.assay) ? root.assay : null);
          if (cand) { enrichment.mhsAssay = cand; hasSomething = true; }
        }
        // Panel de equipos MHS: detectado por forma. Va VISIBLE en el chat.
        if (!enrichment.mhsDevices) {
          const isMhs = (o: any) => o && typeof o === 'object'
            && o.module === 'mhs_device_layer';
          const cand = isMhs(root) ? root : (isMhs(root?.devices_panel) ? root.devices_panel : null);
          if (cand) { enrichment.mhsDevices = cand; hasSomething = true; }
        }
        // Entregable NIR (proteina construida + mRNA): detectado por forma.
        if (!enrichment.nirDeliverable) {
          const isDel = (o: any) => o && typeof o === 'object' && o.module === 'nir_deliverable';
          const cand = isDel(root) ? root : (isDel(root?.deliverable) ? root.deliverable : null);
          if (cand) { enrichment.nirDeliverable = cand; hasSomething = true; }
        }
        // Bucle evolutivo NIR: detectado por forma.
        if (!enrichment.nirEvolve) {
          const isEv = (o: any) => o && typeof o === 'object' && o.module === 'nir_evolve';
          const cand = isEv(root) ? root : (isEv(root?.evolve) ? root.evolve : null);
          if (cand) { enrichment.nirEvolve = cand; hasSomething = true; }
        }
        // Motor de proteina NIR: se detecta por forma, nunca por texto del prompt.
        if (!enrichment.nirProtein) {
          const isEng = (o: any) => o && typeof o === 'object'
            && o.engine === 'nir_protein_engine_v1';
          const cand = isEng(root) ? root : (isEng(root?.nir_engine) ? root.nir_engine : null);
          if (cand) { enrichment.nirProtein = cand; hasSomething = true; }
        }
        // Ciclo NIR: se detecta por forma, nunca por texto del prompt.
        if (!enrichment.nirCycle) {
          const isNir = (o: any) => o && typeof o === 'object'
            && o.program === 'nir_photosensitizer';
          const cand = isNir(root) ? root : (isNir(root?.nir_cycle) ? root.nir_cycle : null);
          if (cand) { enrichment.nirCycle = cand; hasSomething = true; }
        }
        if (!enrichment.structuralReview) {
          const isReview = (o: any) => o && typeof o === 'object'
            && o.pipeline === 'bioql_structural_review_v1';
          const cand = isReview(root) ? root
            : (isReview(root?.structural_review) ? root.structural_review : null);
          if (cand && (Array.isArray(cand.sites) || cand.verdict || cand.error)) {
            enrichment.structuralReview = cand;
            hasSomething = true;
          }
        }
        // ── BIOQL-GQE: local Qwen/vMLX ground-state circuit generation,
        // independently evaluated against the physical FCI reference. ──
        if (!enrichment.bioqlGqe && root?.pipeline === 'bioql_gqe_v1') {
          enrichment.bioqlGqe = root;
          hasSomething = true;
        }
        // ── Due-diligence bundle (additive; emitted by due_diligence_report.py). ──
        if (!enrichment.dueDiligence) {
          if (root?.report === 'due_diligence_report') {
            enrichment.dueDiligence = root;
            hasSomething = true;
          }
        }
        // ── BioNeMo augmentation extraction (additive, defensive; card no-ops when absent) ──
        // MSA depth: live bionemo_msa output OR validation_registry "msa_folding_uplift".
        // Single-cell: live bionemo_singlecell output OR validation_registry "quantum_cell_singlecell_xcheck".
        if (!enrichment.bionemoAug) {
          const _msa = deepFind(root, 'bionemo_msa') || deepFind(root, 'msa_folding_uplift') || null;
          const _sc  = deepFind(root, 'bionemo_singlecell') || deepFind(root, 'quantum_cell_singlecell_xcheck') || null;
          if ((_msa && typeof _msa === 'object') || (_sc && typeof _sc === 'object')) {
            enrichment.bionemoAug = { msa: _msa, singlecell: _sc };
            hasSomething = true;
          }
        }
        if (!enrichment.antibodyBench) {
          const _ab: any = {};
          for (const _k of ['biophi_humanness','abbibench_zeroshot','abbind_ddg','abag_interaction','flab_developability','denovo_binder_design']) {
            const _v = deepFind(root, _k);
            if (_v && typeof _v === 'object') _ab[_k] = _v;
          }
          if (Object.keys(_ab).length) { enrichment.antibodyBench = _ab; hasSomething = true; }
        }
        // ── Post-hoc audit block (additive; emitted alongside any pipeline result). ──
        if (!enrichment.audit) {
          if (root?.audit) { enrichment.audit = root.audit; hasSomething = true; }
        }
        // ── PDC (peptide-drug conjugate) design (additive; emitted by
        //    pdc_conjugate_design.py's design_pdc()/recommend_pdc()). ──
        if (!enrichment.pdcDesign) {
          const _pdc = deepFind(root, 'ranked_combinations') ? root : deepFind(root, 'top_recommendation');
          const _hasPdcShape = _pdc && typeof _pdc === 'object' &&
            (Array.isArray((_pdc as any).ranked_combinations) ||
             ((_pdc as any).payload && (_pdc as any).linker));
          if (_hasPdcShape) { enrichment.pdcDesign = _pdc; hasSomething = true; }
        }
        // ── ADAR editing sensor/switch design (additive; emitted by
        //    adar_sensor_design.py's design_adar_switch()). ──
        if (!enrichment.adarSensor) {
          const _adar = deepFind(root, 'ranked_sites');
          if (Array.isArray(_adar) && _adar.length && _adar[0]?.switch_type) {
            enrichment.adarSensor = root;
            hasSomething = true;
          }
        }
        // ── Interim-analysis trial value decomposition (additive; emitted by
        //    decision_gonogo.interim_analysis_value()). ──
        if (!enrichment.interimAnalysis) {
          const _ia = deepFind(root, 'time_to_market_value') ? root : deepFind(root, 'interim_analysis');
          const _hasIaShape = _ia && typeof _ia === 'object' &&
            ((_ia as any).time_to_market_value || (_ia as any).salvage_value);
          if (_hasIaShape) { enrichment.interimAnalysis = _ia; hasSomething = true; }
        }
        // ── Quantum-Steered Developable Design (QSDD; additive; emitted by
        //    property_steered_design.as_card() -> quantum_steered_design). ──
        if (!enrichment.quantumSteered) {
          const _qsd = deepFind(root, 'quantum_steered_design');
          if (_qsd && typeof _qsd === 'object' &&
              (Array.isArray((_qsd as any).pareto_front) || Array.isArray((_qsd as any).trajectory))) {
            enrichment.quantumSteered = _qsd;
            hasSomething = true;
          }
        }
        if (!enrichment.activeCudaqReview) {
          const _activeCudaq = deepFind(root, 'active_cudaq_review');
          if (_activeCudaq && typeof _activeCudaq === 'object' && (_activeCudaq as any).review_id) {
            enrichment.activeCudaqReview = _activeCudaq;
            hasSomething = true;
          }
        }
      } catch (_e) { /* defensive: never break extraction */ }
    }

    return hasSomething ? enrichment : null;
  };

  // Memoized: extractPipelineData does JSON.parse + recursive deepFind() walks
  // over every tool-call output (large for docking/replicon/mRNA results).
  // Unmemoized, it re-ran on EVERY render of this message — including
  // re-renders triggered by unrelated streaming-text updates on OTHER
  // messages — repeatedly re-parsing the same large payload. message is
  // referentially stable across those unrelated re-renders (only the message
  // actually being streamed gets a new object), so keying on it here skips
  // the re-parse entirely for settled messages.
  const pipelineData = useMemo(
    () => (isAssistant ? extractPipelineData() : null),
    [isAssistant, message]
  );

  // Does a dedicated card already draw the AlphaGenome section for this
  // pipeline? Asked of cardRegistry rather than hard-coded here, so adding a
  // card to CARDS_EMBEDDING_REGULATORY is the only edit needed.
  const regulatoryAlreadyEmbedded = useMemo(() => {
    const p = (pipelineData as any)?.regulatoryPipeline;
    const viaRegistry = entriesForPipeline(p)
      .some(e => CARDS_EMBEDDING_REGULATORY.has(e.cardComponent));
    // Belt and braces: these enrichment keys mount an embedding card directly.
    const viaEnrichment = !!(pipelineData?.crispr || pipelineData?.replicon
      || pipelineData?.rejuvenation || pipelineData?.crisprTherapeutic);
    return viaRegistry || viaEnrichment;
  }, [pipelineData]);

  // ═══════════════════════════════════════
  // RENDER: Toxicology inline card
  // ═══════════════════════════════════════
  const renderToxicology = (tox: any) => {
    if (!tox) return null;
    const acute = tox.acute_toxicity || {};
    const organ = tox.organ_toxicity || {};
    const geno = tox.genotoxicity || {};
    const special = tox.special_toxicity || {};
    const overallScore = tox.overall_score;

    return (
      <div className="p-3 rounded-xl border border-red-500/20 bg-gradient-to-br from-red-500/5 via-transparent to-orange-500/5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-red-400" />
            <h4 className="text-sm font-semibold text-red-400">Toxicology Assessment</h4>
          </div>
          {overallScore != null && (
            <span className={cn('text-xs font-bold px-2 py-0.5 rounded-full border', scoreBg(overallScore), scoreColor(overallScore))}>
              Safety: {asPercent(overallScore)}%
            </span>
          )}
        </div>
        {/* Explicit meaning of the overall Safety badge */}
        {overallScore != null && (
          <MetricMeta
            className="mb-2"
            meaning="Overall safety score (0–100%): aggregate of acute, organ, genotoxicity & special-tox endpoints; higher = safer."
            meta={hvMeta(tox.overall_score, tox, 'overall_score')}
          />
        )}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          {(acute.ld50_mg_kg ?? tox.ld50_predicted) && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">LD50</div>
              <div className="text-white font-bold">{safeNum(acute.ld50_mg_kg ?? tox.ld50_predicted, 1)} mg/kg</div>
              <div className="text-gray-400 text-[10px]">{acute.toxicity_class || acute.ghs_class || ''}</div>
              <MetricMeta
                meaning="Median lethal dose, oral rat (mg/kg). Higher = less acutely toxic; GHS class shown below."
                meta={hvMeta(acute.ld50_mg_kg ?? tox.ld50_predicted, acute, 'ld50_mg_kg')}
              />
            </div>
          )}
          {geno.ames_test && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Ames Test</div>
              <div className={cn('font-bold', geno.ames_test === 'Negative' ? 'text-emerald-400' : 'text-red-400')}>{riskStr(geno.ames_test)}</div>
              <MetricMeta
                meaning="Bacterial reverse-mutation mutagenicity assay; Negative = not predicted mutagenic."
                meta={hvMeta(geno.ames_test, geno, 'ames_test')}
              />
            </div>
          )}
          {organ.hepatotoxicity && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Hepatotox</div>
              <div className={cn('font-bold', organ.hepatotoxicity === 'Low' ? 'text-emerald-400' : 'text-yellow-400')}>{riskStr(organ.hepatotoxicity)}</div>
              <MetricMeta
                meaning="Predicted liver-injury (DILI) risk class; Low = preferred."
                meta={hvMeta(organ.hepatotoxicity, organ, 'hepatotoxicity')}
              />
            </div>
          )}
          {organ.cardiotoxicity && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Cardiotox</div>
              <div className={cn('font-bold', organ.cardiotoxicity === 'Low' ? 'text-emerald-400' : 'text-yellow-400')}>{riskStr(organ.cardiotoxicity)}</div>
              <MetricMeta
                meaning="Predicted cardiac-toxicity risk class (incl. hERG/QT liability); Low = preferred."
                meta={hvMeta(organ.cardiotoxicity, organ, 'cardiotoxicity')}
              />
            </div>
          )}
          {organ.nephrotoxicity && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Nephrotox</div>
              <div className={cn('font-bold', organ.nephrotoxicity === 'Low' ? 'text-emerald-400' : 'text-yellow-400')}>{riskStr(organ.nephrotoxicity)}</div>
              <MetricMeta
                meaning="Predicted kidney-toxicity risk class; Low = preferred."
                meta={hvMeta(organ.nephrotoxicity, organ, 'nephrotoxicity')}
              />
            </div>
          )}
          {(tox.herg_risk ?? tox.hERG_risk) && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">hERG Risk</div>
              <div className={cn('font-bold', (tox.herg_risk ?? tox.hERG_risk) === 'Low' ? 'text-emerald-400' : 'text-yellow-400')}>{riskStr(tox.herg_risk ?? tox.hERG_risk)}</div>
              <MetricMeta
                meaning="hERG K+ channel blockade liability (QT-prolongation / arrhythmia risk); Low = preferred."
                meta={hvMeta(tox.herg_risk ?? tox.hERG_risk, tox, 'herg_risk')}
              />
            </div>
          )}
          {riskStr(tox.immunotoxicity_risk) && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Immunotox</div>
              <div className={cn('font-bold', isLowRisk(tox.immunotoxicity_risk) ? 'text-emerald-400' : 'text-yellow-400')}>{riskStr(tox.immunotoxicity_risk)}</div>
              <MetricMeta
                meaning="Predicted immunotoxicity risk (immune-system perturbation); Low = preferred."
                meta={hvMeta(tox.immunotoxicity_risk, tox, 'immunotoxicity_risk')}
              />
            </div>
          )}
          {/* Biologics/Antibody Tox Fields */}
          {riskStr(tox.ada_risk) && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">ADA Risk</div>
              <div className={cn('font-bold', isLowRisk(tox.ada_risk) ? 'text-emerald-400' : 'text-yellow-400')}>{riskStr(tox.ada_risk)}</div>
              <MetricMeta
                meaning="Anti-drug-antibody (immunogenicity) risk for a biologic; Low = preferred."
                meta={hvMeta(tox.ada_risk, tox, 'ada_risk')}
              />
            </div>
          )}
          {riskStr(tox.cytokine_release_risk) && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">CRS Risk</div>
              <div className={cn('font-bold', isLowRisk(tox.cytokine_release_risk) ? 'text-emerald-400' : 'text-yellow-400')}>{riskStr(tox.cytokine_release_risk)}</div>
              <MetricMeta
                meaning="Cytokine-release-syndrome risk (systemic immune activation) for a biologic; Low = preferred."
                meta={hvMeta(tox.cytokine_release_risk, tox, 'cytokine_release_risk')}
              />
            </div>
          )}
          {riskStr(tox.infusion_reaction_risk) && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Infusion Rxn</div>
              <div className={cn('font-bold', isLowRisk(tox.infusion_reaction_risk) ? 'text-emerald-400' : 'text-yellow-400')}>{riskStr(tox.infusion_reaction_risk)}</div>
              <MetricMeta
                meaning="Infusion-reaction risk on IV/SC administration of a biologic; Low = preferred."
                meta={hvMeta(tox.infusion_reaction_risk, tox, 'infusion_reaction_risk')}
              />
            </div>
          )}
          {riskStr(tox.hepatotoxicity_risk) && !organ.hepatotoxicity && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Hepatotox</div>
              <div className={cn('font-bold', isLowRisk(tox.hepatotoxicity_risk) ? 'text-emerald-400' : 'text-yellow-400')}>{riskStr(tox.hepatotoxicity_risk)}</div>
              <MetricMeta
                meaning="Predicted liver-injury (DILI) risk class; Low = preferred."
                meta={hvMeta(tox.hepatotoxicity_risk, tox, 'hepatotoxicity_risk')}
              />
            </div>
          )}
        </div>
        {/* Honest-null tox endpoints: surface their reason instead of silently
            dropping them, so a partial assessment isn't shown as complete. */}
        <HonestNullNotes items={collectHonestNulls(tox)} />
        {/* Engine / method provenance for the whole toxicology assessment */}
        {(tox.method || tox.engine || tox.provenance || tox.source || tox.model) && (
          <div className="mt-2 pt-2 border-t border-dark-700/50 space-y-0.5">
            {(tox.method || tox.model) && <div className="text-[10px] text-gray-500">Method: {riskStr(tox.method) || riskStr(tox.model)}</div>}
            {(tox.engine || tox.provenance || tox.source) && <div className="text-[10px] text-gray-400">Source: {riskStr(tox.engine) || riskStr(tox.provenance) || riskStr(tox.source)}</div>}
          </div>
        )}
        {tox.quantum_backend && (
          <div className="mt-2 text-[10px] text-gray-400">Quantum backend: {riskStr(tox.quantum_backend)}</div>
        )}
      </div>
    );
  };

  // ═══════════════════════════════════════
  // RENDER: Pharmacology inline card
  // ═══════════════════════════════════════
  const renderPharmacology = (pharm: any) => {
    if (!pharm) return null;
    const pk = pharm.pharmacokinetics || {};
    const pd = pharm.pharmacodynamics || {};
    const abs = pk.absorption || {};
    const dist = pk.distribution || {};
    const exc = pk.excretion || {};
    const overallScore = pharm.overall_score;

    // Binding block — values may be honest-null (VQE ordinal proxy, not a chip Kd).
    const binding = pharm.binding || {};
    const hasRealAffinity = binding.binding_affinity_kcal != null || binding.kd_nM != null || binding.kd_nm != null;
    const kdVal = binding.kd_nM ?? binding.kd_nm;
    const vqeOrdinal = binding.vqe_relative_ordinal;
    const kdDisclaimer = binding.kd_disclaimer;
    const hasBinding = Object.keys(binding).length > 0;

    // Mechanism / target — may be plain strings, null, or honest-value dicts.
    const mechanismStr = riskStr(pd.mechanism) || riskStr(pharm.mechanism);
    const targetStr = riskStr(pharm.target) || riskStr(pharm.target?.name) || riskStr(pharm.target?.gene);

    return (
      <div className="p-3 rounded-xl border border-blue-500/20 bg-gradient-to-br from-blue-500/5 via-transparent to-indigo-500/5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Pill className="w-4 h-4 text-blue-400" />
            <h4 className="text-sm font-semibold text-blue-400">Pharmacology (PK/PD)</h4>
          </div>
          {overallScore != null && (
            <span className={cn('text-xs font-bold px-2 py-0.5 rounded-full border', scoreBg(overallScore), scoreColor(overallScore))}>
              PK/PD: {asPercent(overallScore)}%
            </span>
          )}
        </div>
        {/* Explicit meaning of the PK/PD badge */}
        {overallScore != null && (
          <MetricMeta
            className="mb-2"
            meaning="Aggregate PK/PD favorability score (0–100%): combines absorption, distribution, metabolism, excretion & target engagement; higher = more drug-like exposure."
            meta={hvMeta(pharm.overall_score, pharm, 'overall_score')}
          />
        )}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          {abs.bioavailability_percent != null && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Bioavailability</div>
              <div className="text-white font-bold">{safeNum(abs.bioavailability_percent, 1)}%</div>
              <MetricMeta
                meaning="Oral bioavailability (F, %): fraction of dose reaching systemic circulation. Higher = better oral exposure."
                meta={hvMeta(abs.bioavailability_percent, abs, 'bioavailability_percent')}
              />
            </div>
          )}
          {exc.half_life_hours != null && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Half-life</div>
              <div className="text-white font-bold">{safeNum(exc.half_life_hours, 1)}h</div>
              <MetricMeta
                meaning="Elimination half-life t½ (hours): time for plasma concentration to halve; drives dosing frequency."
                meta={hvMeta(exc.half_life_hours, exc, 'half_life_hours')}
              />
            </div>
          )}
          {dist.protein_binding_percent != null && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Protein Binding</div>
              <div className="text-white font-bold">{safeNum(dist.protein_binding_percent, 1)}%</div>
              <MetricMeta
                meaning="Plasma-protein binding (% bound): only the unbound fraction is pharmacologically active."
                meta={hvMeta(dist.protein_binding_percent, dist, 'protein_binding_percent')}
              />
            </div>
          )}
          {pd.potency_nm != null && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Potency</div>
              <div className="text-white font-bold">{safeNum(pd.potency_nm, 1)} nM</div>
              <MetricMeta
                meaning="Pharmacodynamic potency (nM, e.g. IC50/EC50): lower = more potent at the target."
                meta={hvMeta(pd.potency_nm, pd, 'potency_nm')}
              />
            </div>
          )}
          {(abs.tmax?.value ?? pharm.tmax) != null && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Tmax</div>
              <div className="text-white font-bold">{safeNum(abs.tmax?.value ?? pharm.tmax, 1)}h</div>
              <MetricMeta
                meaning="Time to peak plasma concentration Tmax (hours): how fast absorption peaks."
                meta={hvMeta(abs.tmax ?? pharm.tmax, abs, 'tmax')}
              />
            </div>
          )}
          {(abs.cmax?.value ?? pharm.cmax) != null && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Cmax</div>
              <div className="text-white font-bold">{safeNum(abs.cmax?.value ?? pharm.cmax, 1)} ng/mL</div>
              <MetricMeta
                meaning="Peak plasma concentration Cmax (ng/mL): maximum exposure after a dose."
                meta={hvMeta(abs.cmax ?? pharm.cmax, abs, 'cmax')}
              />
            </div>
          )}
          {(abs.auc?.value ?? pharm.auc) != null && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">AUC</div>
              <div className="text-white font-bold">{safeNum(abs.auc?.value ?? pharm.auc, 1)} ng*h/mL</div>
              <MetricMeta
                meaning="Area under the curve AUC (ng·h/mL): total systemic drug exposure over time."
                meta={hvMeta(abs.auc ?? pharm.auc, abs, 'auc')}
              />
            </div>
          )}
          {(dist.vd_L_kg ?? dist.vd?.value ?? pharm.vd) != null && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Vd</div>
              <div className="text-white font-bold">{safeNum(dist.vd_L_kg ?? dist.vd?.value ?? pharm.vd, 2)} L/kg</div>
              <MetricMeta
                meaning="Volume of distribution Vd (L/kg): apparent tissue distribution; high = extensive tissue uptake."
                meta={hvMeta(dist.vd_L_kg ?? dist.vd ?? pharm.vd, dist, 'vd_L_kg')}
              />
            </div>
          )}
          {(exc.clearance_ml_min_kg ?? pharm.clearance) != null && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">Clearance</div>
              <div className="text-white font-bold">{safeNum(exc.clearance_ml_min_kg ?? pharm.clearance, 1)} mL/min/kg</div>
              <MetricMeta
                meaning="Systemic clearance CL (mL/min/kg): rate of drug elimination from plasma."
                meta={hvMeta(exc.clearance_ml_min_kg ?? pharm.clearance, exc, 'clearance_ml_min_kg')}
              />
            </div>
          )}
          {(dist.BBB_penetration ?? pharm.bbb_penetration ?? pharm.bbb) != null && (
            <div className="p-2 bg-dark-700 rounded-lg text-center">
              <div className="text-gray-500">BBB</div>
              <div className={cn('font-bold', (dist.BBB_penetration ?? pharm.bbb_penetration ?? pharm.bbb) === 'Yes' ? 'text-emerald-400' : 'text-yellow-400')}>{riskStr(dist.BBB_penetration ?? pharm.bbb_penetration ?? pharm.bbb)}</div>
              <MetricMeta
                meaning="Blood-brain-barrier penetration (Yes/No): whether the drug is predicted to reach the CNS."
                meta={hvMeta(dist.BBB_penetration ?? pharm.bbb_penetration ?? pharm.bbb, dist, 'BBB_penetration')}
              />
            </div>
          )}
        </div>
        {/* Binding / affinity — honest even when chip Kd is null */}
        {hasBinding && (
          <div className="mt-3 pt-2 border-t border-blue-500/10">
            <div className="text-[11px] text-blue-400 font-semibold mb-1">Binding</div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
              <div className="p-2 bg-dark-700 rounded-lg text-center">
                <div className="text-gray-500">Kd</div>
                <div className={cn('font-bold font-mono', hasRealAffinity ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{hasRealAffinity ? `${numOrNA(kdVal, 1)} nM` : 'N/A — affinity from VQE ordinal only (not a measured Kd)'}</div>
                <MetricMeta
                  meaning="Equilibrium dissociation constant Kd (nM): drug-target binding affinity. Lower = tighter binding."
                  meta={hvMeta(kdVal, binding, 'kd_nM')}
                />
              </div>
              {binding.affinity_rank != null && (
                <div className="p-2 bg-dark-700 rounded-lg text-center">
                  <div className="text-gray-500">Affinity rank</div>
                  <div className="text-white font-bold font-mono">#{numOrNA(binding.affinity_rank, 0)}</div>
                  <MetricMeta
                    meaning="Relative binding-affinity rank among candidates (#1 = strongest predicted binder)."
                    meta={hvMeta(binding.affinity_rank, binding, 'affinity_rank')}
                  />
                </div>
              )}
              {vqeOrdinal != null && (
                <div className="p-2 bg-dark-700 rounded-lg text-center">
                  <div className="text-gray-500">VQE ranking ordinal (not a measured Kd)</div>
                  <div className="text-cyan-400 font-bold font-mono">{numOrNA(vqeOrdinal, 4)}</div>
                  <MetricMeta
                    meaning="VQE variational energy ordinal: a quantum relative-ranking proxy for binding strength, NOT a physical Kd."
                    meta={hvMeta(vqeOrdinal, binding, 'vqe_relative_ordinal')}
                  />
                </div>
              )}
            </div>
            {!hasRealAffinity && kdDisclaimer && (
              <div className="mt-1 text-[10px] text-gray-500 italic">{riskStr(kdDisclaimer)}</div>
            )}
          </div>
        )}
        {(mechanismStr || targetStr) && (
          <div className="mt-2 space-y-0.5">
            {mechanismStr && (
              <div className="text-xs text-gray-500">Mechanism: <span className="text-gray-300">{mechanismStr}</span></div>
            )}
            {targetStr && (
              <div className="text-xs text-gray-500">Target: <span className="text-gray-300">{targetStr}</span></div>
            )}
          </div>
        )}
        {/* Honest-null PK/PD endpoints (e.g. oral bioavailability / BBB N/A for a
            biologic): surface the reason rather than dropping the field. */}
        <HonestNullNotes items={collectHonestNulls(pharm)} />
        {/* Engine / method provenance for the PK/PD assessment */}
        {(pharm.method || pharm.engine || pharm.provenance || pharm.source || pharm.model) && (
          <div className="mt-2 pt-2 border-t border-blue-500/10 space-y-0.5">
            {(pharm.method || pharm.model) && <div className="text-[10px] text-gray-500">Method: {riskStr(pharm.method) || riskStr(pharm.model)}</div>}
            {(pharm.engine || pharm.provenance || pharm.source) && <div className="text-[10px] text-gray-400">Source: {riskStr(pharm.engine) || riskStr(pharm.provenance) || riskStr(pharm.source)}</div>}
          </div>
        )}
        {pharm.quantum_backend && (
          <div className="mt-2 text-[10px] text-gray-400">Quantum backend: {riskStr(pharm.quantum_backend)}</div>
        )}
      </div>
    );
  };

  // ═══════════════════════════════════════
  // RENDER: Clinical Trial inline card
  // ═══════════════════════════════════════
  const renderClinicalTrial = (clinical: any) => {
    if (!clinical) return null;
    const p1 = clinical.phase_I || clinical.phase_1 || {};
    const p2 = clinical.phase_II || clinical.phase_2 || {};
    const p3 = clinical.phase_III || clinical.phase_3 || {};
    const reg = clinical.regulatory || clinical.development_summary || {};
    const overallScore = clinical.overall_score;
    const biologics = clinical.biologics_specific || {};

    // Real calibrated clinical-risk model output (clinical_risk.model.predict),
    // resolved regardless of nesting (clinical_risk / clinical_trial / top-level).
    const _crBlock = clinical.clinical_risk || deepFind(clinical, 'clinical_risk')
      || clinical.clinical_trial || deepFind(clinical, 'clinical_trial') || clinical;
    const crField = (k: string) => (_crBlock && _crBlock[k]) || deepFind(clinical, k) || null;
    const crP1 = crField('phase_1_to_2');
    const crP2 = crField('phase_2_to_3');
    const crP3 = crField('phase_3_to_approval');
    const crCum = crField('cumulative_approval');
    const crContext = (_crBlock && _crBlock.context) || deepFind(clinical, 'context') || null;
    const crUnavailReason = (_crBlock && _crBlock.available === false)
      ? (_crBlock.reason || 'clinical-risk model not available for this cohort') : null;
    // Renders a real model PoS field (value + CI90 + method + provenance) or honest N/A.
    const renderPoS = (label: string, field: any) => {
      const v = hvNum(field);
      const ci = field && Array.isArray(field.ci90) ? field.ci90 : null;
      return (
        <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 space-y-1">
          <div className="font-semibold text-gray-300 text-xs">{label} — Calibrated Probability of Success</div>
          {v == null ? (
            <div className="text-[11px] italic text-gray-500">N/A — {field?.null_reason || crUnavailReason || 'not computed for this cohort'}</div>
          ) : (
            <div className="space-y-0.5">
              <div className="text-2xl font-bold text-emerald-400">{asPercent(v)}%
                {ci && <span className="text-[10px] font-normal text-gray-500 ml-1.5">90% CI [{asPercent(ci[0])}–{asPercent(ci[1])}%]</span>}
              </div>
              {field.method && <div className="text-[10px] text-gray-500">Method: {field.method}</div>}
              {field.provenance && <div className="text-[10px] text-gray-400">Source: {field.provenance}</div>}
              {field.disclaimer && <div className="text-[9px] text-gray-400 italic pt-1 border-t border-dark-700/50">{field.disclaimer}</div>}
            </div>
          )}
        </div>
      );
    };
    // Real CT.gov / published base-rate context line (no fabrication).
    const renderCrContext = () => crContext ? (
      <div className="text-[9px] text-gray-400 pt-1">
        Cohort base rate: {crContext.base_rate != null ? `${asPercent(crContext.base_rate)}%` : 'N/A'}
        {crContext.n_reference != null && ` · n=${crContext.n_reference} (${crContext.source || 'cohort'})`}
        {crContext.published_source && ` · ${crContext.published_source}`}
      </div>
    ) : null;

    // Trial-design fields: bind ONLY to real backend values; no hardcoded
    // per-modality template fallbacks. A missing field renders "N/A — not computed".
    const p1Design = p1.design ?? null;
    const p1Objective = p1.objective ?? null;
    const p1Population = p1.population ?? null;
    const p1Administration = p1.administration ?? null;
    const p1SampleSize = p1.sample_size ?? null;
    const p1Duration = p1.duration_months ?? null;

    // Dose values (starting/recommended/MTD) and DLT probability are NOT
    // predicted by any engine for a de-novo candidate. Bind only to real backend
    // values; otherwise render "N/A — not simulated" rather than fabricating
    // per-modality constants.
    const p1StartingDose = p1.starting_dose ?? null;
    const p1RecommendedDose = p1.recommended_dose ?? null;
    const p1Mtd = p1.mtd ?? null;
    const p1DltProb = p1.dlt_probability != null ? p1.dlt_probability : null;

    // Phase II design fields: real backend values only, no template fallbacks.
    const p2Design = p2.design ?? null;
    const p2Objective = p2.objective ?? null;
    const p2Population = p2.population ?? null;
    const p2PrimaryEndpoint = p2.primary_endpoint ?? null;
    const p2SampleSize = p2.sample_size ?? null;
    const p2Duration = p2.duration_months ?? null;
    // Receptor occupancy / therapeutic index: real backend values only, else N/A.
    const p2Occupancy = p2.efficacy_prediction?.receptor_occupancy ?? null;
    const p2Ti = p2.efficacy_prediction?.therapeutic_index ?? null;
    // Dose arms: real backend cohorts only — guarded by Array.isArray so a null hides.
    const p2DoseArms = p2.dose_arms ?? null;

    // Phase III design fields: real backend values only, no template fallbacks.
    const p3Design = p3.design ?? null;
    const p3Objective = p3.objective ?? null;
    const p3Population = p3.population ?? null;
    const p3PrimaryEndpoint = p3.primary_endpoint ?? null;
    const p3SampleSize = p3.sample_size ?? null;
    const p3Duration = p3.duration_months ?? null;
    // Power / significance level are trial-DESIGN ASSUMPTIONS (inputs), not
    // computed results. Bind only to backend values; no hardcoded 0.90 / 0.05.
    const p3Power = p3.statistical_power != null ? p3.statistical_power : null;
    const p3Alpha = p3.alpha != null ? p3.alpha : null;

    // CMC / manufacturing fields: real backend values only, no template fallbacks.
    const biologicsMfg = biologics.manufacturing ?? null;
    const biologicsForm = biologics.formulation ?? null;
    const biologicsCold = biologics.cold_chain ?? null;
    const biologicsImm = biologics.immunogenicity_monitoring ?? null;

    // Pathway: backend value only — no rule-based default fabrication.
    const regPathway = reg.pathway ?? null;

    const formatDose = (doseObj: any) => {
      if (doseObj == null) return 'N/A — not simulated';
      if (typeof doseObj === 'object') {
        if (doseObj.value == null) return 'N/A — not simulated';
        return `${doseObj.value} ${doseObj.unit || 'mg'}`;
      }
      return `${doseObj} mg`;
    };

    return (
      <div className="p-3.5 rounded-xl border border-purple-500/20 bg-gradient-to-br from-purple-500/5 via-transparent to-violet-500/5 space-y-3.5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-purple-400" />
            <h4 className="text-sm font-semibold text-purple-400">Clinical Trial Simulation Dashboard</h4>
          </div>
          {(() => {
            // Unwrap honest-null objects so a {value:null} clinical PoS renders
            // "N/A — model not available", never a fabricated 0% or "N/AN/A%".
            // Prefer the real calibrated cumulative-approval probability.
            const approval = hvNum(crCum) ?? hvNum(overallScore);
            if (approval == null) {
              return (
                <span className="text-xs font-bold px-2 py-0.5 rounded-full border bg-dark-700 border-dark-600 text-gray-400">
                  Overall Approval: N/A — model not available
                </span>
              );
            }
            return (
              <span className={cn('text-xs font-bold px-2 py-0.5 rounded-full border', scoreBg(approval), scoreColor(approval))}>
                Overall Approval: {asPercent(approval)}%
              </span>
            );
          })()}
        </div>

        {/* Tab Buttons */}
        <div className="flex flex-wrap gap-1 border-b border-dark-700/50 pb-2">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'phase1', label: 'Phase I (Safety)' },
            { id: 'phase2', label: 'Phase II (Efficacy)' },
            { id: 'phase3', label: 'Phase III (Pivotal)' },
            { id: 'biologics', label: 'Regulatory & BLA' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveClinicalPhase(tab.id as any)}
              className={cn(
                "px-2.5 py-0.5 text-[10px] font-semibold rounded-full transition-all duration-200 border cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400",
                activeClinicalPhase === tab.id
                  ? "bg-purple-500/20 text-purple-300 border-purple-500/40"
                  : "bg-dark-700 text-gray-400 border-dark-600 hover:bg-dark-600 hover:text-gray-300"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeClinicalPhase === 'overview' && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              {(() => {
                // Phase-transition probabilities of success: bind ONLY to real
                // backend values (clinical_risk.model.predict outputs surfaced on
                // the clinical/phase dicts). No hardcoded 0.80/0.60/0.61 fallback —
                // a missing value shows "N/A — not computed", never a literal.
                // hvNum unwraps HonestValue objects ({value:null} → null → "N/A")
                // so an honest-null PoS never renders as a fabricated number.
                const p1Pos = hvNum(crP1);
                const p2Pos = hvNum(crP2);
                const p3Pos = hvNum(crP3);
                const fdaPos = hvNum(crCum);
                const posCell = (label: string, sub: string, v: any, field?: any) => (
                  <div className="p-2.5 bg-dark-700 rounded-lg text-center border border-dark-600/40">
                    <div className="text-gray-500 mb-0.5">{label}</div>
                    <div className={cn('font-bold text-white', v != null ? 'text-xl' : 'text-[11px] italic text-gray-500')}>
                      {v != null ? `${asPercent(v)}%` : 'N/A — not computed'}
                    </div>
                    <div className="text-gray-400 text-[10px]">{sub}</div>
                    {v != null && (
                      <MetricMeta
                        meaning="Calibrated probability of success for this phase transition (%); from a clinical-risk model, not a guarantee."
                        meta={hvMeta(field)}
                      />
                    )}
                  </div>
                );
                return (
                  <>
                    {posCell('Phase I', 'FIH Safety', p1Pos, crP1)}
                    {posCell('Phase II', 'Proof of Concept', p2Pos, crP2)}
                    {posCell('Phase III', 'Confirmatory', p3Pos, crP3)}
                    <div className="p-2.5 bg-purple-500/20 border border-purple-500/30 rounded-lg text-center">
                      <div className="text-purple-400 mb-0.5 font-medium">FDA Registration</div>
                      <div className={cn('font-bold text-purple-300', fdaPos != null ? 'text-xl' : 'text-[11px] italic')}>
                        {fdaPos != null ? `${asPercent(fdaPos)}%` : 'N/A — not computed'}
                      </div>
                      <div className="text-purple-500/60 text-[10px]">{regPathway || 'Pathway: N/A — not specified'}</div>
                      {fdaPos != null && (
                        <MetricMeta
                          meaning="Cumulative probability of FDA approval (%) = product of all phase-transition probabilities."
                          meta={hvMeta(crCum)}
                        />
                      )}
                    </div>
                  </>
                );
              })()}
            </div>
            {renderCrContext()}

            {/* Regulatory Timeline Details */}
            <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 text-[11px] space-y-2">
              <div className="font-semibold text-gray-300 text-xs">Projected Development Timeline & Costs</div>
              <div className="text-[9px] text-gray-500 leading-tight">
                Estimated regulatory pathway, time-to-approval (years), and capitalized development cost (USD millions) for this candidate.
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <div>
                  <span className="text-gray-500 block">Regulatory Pathway</span>
                  {/* Pathway: backend value only — no rule-based fabrication. */}
                  <span className={cn('font-semibold', regPathway != null ? 'text-emerald-400' : 'text-gray-500 italic text-[10px]')}>{regPathway || 'N/A — not computed'}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Est. Time to Approval</span>
                  <span className={cn('font-semibold', (reg.time_to_approval_years != null || reg.estimated_timeline_months != null) ? 'text-white' : 'text-gray-500 italic')}>
                    {reg.time_to_approval_years != null ? `${reg.time_to_approval_years} Years`
                      : reg.estimated_timeline_months != null ? `${(reg.estimated_timeline_months / 12).toFixed(1)} Years`
                      : 'N/A — not computed'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block">Est. Development Cost</span>
                  <span className={cn('font-semibold', reg.estimated_cost_M_usd != null ? 'text-white' : 'text-gray-500 italic')}>
                    {reg.estimated_cost_M_usd != null ? `$${reg.estimated_cost_M_usd}M USD` : 'N/A — not computed'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block">Clinically Viable</span>
                  <span className="text-purple-400 font-semibold">{clinical.clinical_viable !== false ? 'Yes' : 'No'}</span>
                </div>
              </div>
              {(clinical.method || clinical.provenance || clinical.source) && (
                <div className="pt-1 border-t border-dark-700/50 space-y-0.5">
                  {clinical.method && <div className="text-[10px] text-gray-400">Simulation Method: {riskStr(clinical.method)}</div>}
                  {(clinical.provenance || clinical.source) && <div className="text-[10px] text-gray-400">Source: {riskStr(clinical.provenance) || riskStr(clinical.source)}</div>}
                </div>
              )}
            </div>
          </div>
        )}

        {activeClinicalPhase === 'phase1' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
            {/* Real calibrated Phase I → II probability of success (clinical_risk model) */}
            <div className="space-y-2">
              {renderPoS('Phase I → II', crP1)}
              {renderCrContext()}
              {(p1Design || p1Objective || p1Population || p1Administration) && (
                <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 space-y-2">
                  <div className="font-semibold text-gray-300 text-xs">Phase I Study Design</div>
                  <div className="space-y-1.5">
                    <div><span className="text-gray-500">Design: </span><span className="text-white">{p1Design || 'N/A — not computed'}</span></div>
                    <div><span className="text-gray-500">Objective: </span><span className="text-white">{p1Objective || 'N/A — not computed'}</span></div>
                    <div><span className="text-gray-500">Population: </span><span className="text-white">{p1Population || 'N/A — not computed'}</span></div>
                    <div><span className="text-gray-500">Administration: </span><span className="text-white">{p1Administration || 'N/A — not computed'}</span></div>
                  </div>
                </div>
              )}
            </div>

            {/* Calculations and Cohorts */}
            <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 space-y-2">
              <div className="font-semibold text-gray-300 text-xs">Dosing & Cohorts</div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-gray-500 block">Sample Size</span>
                  <span className={cn('font-semibold font-mono', p1SampleSize != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{p1SampleSize != null ? p1SampleSize : 'N/A — not computed'}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Duration</span>
                  <span className={cn('font-semibold font-mono', p1Duration != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{p1Duration != null ? `${p1Duration} Months` : 'N/A — not computed'}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Starting Dose</span>
                  <span className="text-white font-semibold font-mono">{formatDose(p1StartingDose)}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Recommended Dose</span>
                  <span className="text-white font-semibold font-mono">{formatDose(p1RecommendedDose)}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Max Tolerated Dose (MTD)</span>
                  <span className="text-white font-semibold font-mono">{formatDose(p1Mtd)}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Dose-Limiting Tox (DLT)</span>
                  <span className={cn('font-semibold font-mono', p1DltProb != null ? 'text-emerald-400' : 'text-gray-500 italic text-[10px]')}>{p1DltProb != null ? `${(p1DltProb * 100).toFixed(1)}%` : 'N/A — not simulated'}</span>
                </div>
              </div>
            </div>

            {/* Safety & Adverse Events — bound to the real toxicology engine when
                present; never fabricated AE rates. Per-patient adverse-event
                incidence is not predicted for a de-novo candidate. */}
            <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 space-y-2">
              <div className="font-semibold text-gray-300 text-xs">Safety Profile</div>
              {(() => {
                const tox = pipelineData?.toxicology;
                const herg = riskStr(tox?.herg_risk ?? tox?.hERG_risk);
                const immuno = riskStr(tox?.immunotoxicity_risk);
                const hepato = riskStr(tox?.organ_toxicity?.hepatotoxicity ?? tox?.hepatotoxicity_risk);
                const rows: Array<[string, string | null]> = [
                  ['hERG / Cardiotox Risk', herg],
                  ['Immunotoxicity Risk', immuno],
                  ['Hepatotoxicity Risk', hepato],
                ];
                const anyReal = rows.some(([, v]) => v != null);
                return (
                  <div className="space-y-1 text-gray-400">
                    {rows.map(([label, v]) => (
                      <div key={label} className="flex justify-between">
                        <span>{label}:</span>
                        <span className={cn('font-semibold', v == null ? 'text-gray-500 italic text-[10px]' : (v.toLowerCase() === 'low' ? 'text-emerald-400' : 'text-yellow-400'))}>
                          {v ?? 'N/A — not predicted'}
                        </span>
                      </div>
                    ))}
                    <div className="text-[9px] text-gray-400 pt-1 border-t border-dark-700/50">
                      {anyReal
                        ? 'Risk classes from the real toxicology (ADMET QSAR) engine. Per-patient adverse-event rates are not predicted for a de-novo candidate.'
                        : 'N/A — adverse-event profile not predicted for a de-novo candidate (no toxicology engine output).'}
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>
        )}

        {activeClinicalPhase === 'phase2' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
            {/* Real calibrated Phase II → III probability of success (clinical_risk model) */}
            <div className="space-y-2">
              {renderPoS('Phase II → III', crP2)}
              {renderCrContext()}
              {(p2Design || p2Objective || p2Population || p2PrimaryEndpoint) && (
                <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 space-y-2">
                  <div className="font-semibold text-gray-300 text-xs">Phase II Trial Design</div>
                  <div className="space-y-1.5">
                    <div><span className="text-gray-500">Design: </span><span className="text-white">{p2Design || 'N/A — not computed'}</span></div>
                    <div><span className="text-gray-500">Objective: </span><span className="text-white">{p2Objective || 'N/A — not computed'}</span></div>
                    <div><span className="text-gray-500">Population: </span><span className="text-white">{p2Population || 'N/A — not computed'}</span></div>
                    <div><span className="text-gray-500">Primary Endpoint: </span><span className="text-white">{p2PrimaryEndpoint || 'N/A — not computed'}</span></div>
                  </div>
                </div>
              )}
            </div>

            {/* Dosing Arms & Efficacy Calculations */}
            <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 space-y-2">
              <div className="font-semibold text-gray-300 text-xs">Efficacy & Cohort Calculations</div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-gray-500 block">Sample Size</span>
                  <span className={cn('font-semibold font-mono', p2SampleSize != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{p2SampleSize != null ? p2SampleSize : 'N/A — not computed'}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Duration</span>
                  <span className={cn('font-semibold font-mono', p2Duration != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{p2Duration != null ? `${p2Duration} Months` : 'N/A — not computed'}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Target Occupancy</span>
                  <span className={cn('font-semibold font-mono', p2Occupancy != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{p2Occupancy != null ? p2Occupancy : 'N/A — not computed'}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Therapeutic Index (TI)</span>
                  <span className={cn('font-semibold font-mono', p2Ti != null ? 'text-emerald-400' : 'text-gray-500 italic text-[10px]')}>{p2Ti != null ? `${p2Ti}x` : 'N/A — not computed'}</span>
                </div>
              </div>

              {/* Dose Arms */}
              {Array.isArray(p2DoseArms) && p2DoseArms.length > 0 && (
                <div className="pt-2 border-t border-dark-700/50">
                  <span className="text-gray-500 block mb-1">Dosing Arm Cohorts</span>
                  <div className="flex gap-1.5 flex-wrap">
                    {p2DoseArms.map((arm: any, i: number) => (
                      <span key={i} className="px-2 py-0.5 bg-dark-700 rounded border border-dark-600 text-[10px] font-mono text-white">
                        {arm.label || `Arm ${i+1}`}: {arm.dose ?? 'N/A'} {arm.unit || 'mg'}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Efficacy Results — clinical efficacy (ORR/CR/PR/SD/DOR) is NOT
                predicted for a de-novo candidate by any engine. Bind to real
                backend efficacy_prediction values when present; otherwise N/A.
                No hardcoded efficacy constants. */}
            <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 space-y-2">
              <div className="font-semibold text-gray-300 text-xs">Efficacy Results</div>
              {(() => {
                const ep = p2.efficacy_prediction || {};
                const rows: Array<[string, any, string]> = [
                  ['Expected ORR', ep.orr ?? ep.objective_response_rate, '%'],
                  ['Complete Response (CR)', ep.cr ?? ep.complete_response, '%'],
                  ['Partial Response (PR)', ep.pr ?? ep.partial_response, '%'],
                  ['Stable Disease (SD)', ep.sd ?? ep.stable_disease, '%'],
                  ['Med. Response DOR', ep.dor_months ?? ep.duration_of_response_months, ' Months'],
                ];
                const anyReal = rows.some(([, v]) => v != null);
                return (
                  <div className="space-y-1 text-gray-400">
                    {rows.map(([label, v, unit]) => (
                      <div key={label} className="flex justify-between">
                        <span>{label}:</span>
                        <span className={cn('font-semibold', v != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>
                          {v != null ? `${safeNum(v, 1)}${unit}` : 'N/A — not predicted'}
                        </span>
                      </div>
                    ))}
                    {!anyReal && (
                      <div className="text-[9px] text-gray-400 pt-1 border-t border-dark-700/50">
                        N/A — clinical efficacy (ORR/PFS) is not predicted for a de-novo candidate.
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          </div>
        )}

        {activeClinicalPhase === 'phase3' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
            {/* Real calibrated Phase III → Approval probability of success (clinical_risk model) */}
            <div className="space-y-2">
              {renderPoS('Phase III → Approval', crP3)}
              {renderCrContext()}
              {(p3Design || p3Objective || p3Population || p3PrimaryEndpoint) && (
                <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 space-y-2">
                  <div className="font-semibold text-gray-300 text-xs">Phase III Pivotal Study</div>
                  <div className="space-y-1.5">
                    <div><span className="text-gray-500">Design: </span><span className="text-white">{p3Design || 'N/A — not computed'}</span></div>
                    <div><span className="text-gray-500">Objective: </span><span className="text-white">{p3Objective || 'N/A — not computed'}</span></div>
                    <div><span className="text-gray-500">Population: </span><span className="text-white">{p3Population || 'N/A — not computed'}</span></div>
                    <div><span className="text-gray-500">Primary Endpoint: </span><span className="text-white">{p3PrimaryEndpoint || 'N/A — not computed'}</span></div>
                  </div>
                </div>
              )}
            </div>

            {/* Statistical Rigor */}
            <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 text-[11px] space-y-2">
              <div className="font-semibold text-gray-300 text-xs">Statistical Rigor & Population</div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-gray-500 block">Sample Size</span>
                  <span className={cn('font-semibold font-mono', p3SampleSize != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{p3SampleSize != null ? p3SampleSize : 'N/A — not computed'}</span>
                  <div className="text-[9px] text-gray-400 leading-tight">Total enrolled patients (N) for the pivotal trial.</div>
                </div>
                <div>
                  <span className="text-gray-500 block">Duration</span>
                  <span className={cn('font-semibold font-mono', p3Duration != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{p3Duration != null ? `${p3Duration} Months` : 'N/A — not computed'}</span>
                  <div className="text-[9px] text-gray-400 leading-tight">Planned trial duration (months).</div>
                </div>
                <div>
                  <span className="text-gray-500 block">Statistical Power (1-β)</span>
                  <span className={cn('font-semibold font-mono', p3Power != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{p3Power != null ? `${(p3Power * 100).toFixed(0)}%` : 'N/A — not computed'}</span>
                  <div className="text-[9px] text-gray-400 leading-tight">Probability of detecting a true effect (1−β); design assumption, typically ≥80%.</div>
                </div>
                <div>
                  <span className="text-gray-500 block">Significance Level (α)</span>
                  <span className={cn('font-semibold font-mono', p3Alpha != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{p3Alpha != null ? p3Alpha : 'N/A — not computed'}</span>
                  <div className="text-[9px] text-gray-400 leading-tight">False-positive rate threshold (α); design assumption, typically 0.05.</div>
                </div>
              </div>
            </div>

            {/* Statistical Results — projected PFS/HR/p-value and an outcome
                verdict are NOT simulated for a de-novo candidate. Bind only to
                real backend statistical_results; otherwise N/A. No hardcoded
                positive p-value or "SUCCESS" verdict. */}
            <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 space-y-2">
              <div className="font-semibold text-gray-300 text-xs">Projected Statistical Efficacy</div>
              {(() => {
                const sr = p3.statistical_results || p3.efficacy_prediction || {};
                const pfsActive = sr.pfs_active_months ?? sr.median_pfs_active;
                const pfsControl = sr.pfs_control_months ?? sr.median_pfs_control;
                const hr = sr.hazard_ratio;
                const hrCi = sr.hazard_ratio_ci95 || sr.hr_ci95;
                const pVal = sr.p_value;
                const verdict = riskStr(sr.outcome) ?? riskStr(sr.verdict);
                const anyReal = [pfsActive, pfsControl, hr, pVal, verdict].some((v) => v != null);
                const naCls = 'text-gray-500 italic text-[10px]';
                if (!anyReal) {
                  return (
                    <p className="text-[11px] text-gray-500 italic leading-snug">
                      N/A — Phase III statistical efficacy (PFS / hazard ratio / p-value) is not simulated for a de-novo candidate.
                    </p>
                  );
                }
                return (
                  <div className="space-y-1 text-gray-400">
                    <div className="flex justify-between"><span>Med. PFS (Active):</span><span className={cn('font-semibold', pfsActive != null ? 'text-white' : naCls)}>{pfsActive != null ? `${safeNum(pfsActive, 1)} Months` : 'N/A'}</span></div>
                    <div className="flex justify-between"><span>Med. PFS (SOC/Placebo):</span><span className={cn('font-semibold', pfsControl != null ? 'text-white' : naCls)}>{pfsControl != null ? `${safeNum(pfsControl, 1)} Months` : 'N/A'}</span></div>
                    <div className="flex justify-between"><span>Hazard Ratio (HR):</span><span className={cn('font-semibold', hr != null ? 'text-emerald-400' : naCls)}>{hr != null ? `${safeNum(hr, 2)}${Array.isArray(hrCi) ? ` (95% CI: ${safeNum(hrCi[0], 2)}-${safeNum(hrCi[1], 2)})` : ''}` : 'N/A'}</span></div>
                    <div className="flex justify-between"><span>p-value:</span><span className={cn('font-semibold', pVal != null ? 'text-emerald-400' : naCls)}>{pVal != null ? safeNum(pVal, 4) : 'N/A'}</span></div>
                    <div className="flex justify-between"><span>Outcome Summary:</span><span className={cn('font-semibold', verdict != null ? 'text-purple-400' : naCls)}>{verdict ?? 'N/A — not simulated'}</span></div>
                  </div>
                );
              })()}
            </div>
          </div>
        )}

        {activeClinicalPhase === 'biologics' && (
          <div className="p-2.5 rounded-lg bg-dark-800 border border-dark-700/50 text-[11px] space-y-2.5">
            <div className="font-semibold text-gray-300 text-xs">CMC / Manufacturing</div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              <div>
                <span className="text-gray-500 block">Manufacturing Class</span>
                <span className={cn('font-semibold', biologicsMfg != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{biologicsMfg || 'N/A — not computed'}</span>
              </div>
              <div>
                <span className="text-gray-500 block">Formulation Type</span>
                <span className={cn('font-semibold', biologicsForm != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{biologicsForm || 'N/A — not computed'}</span>
              </div>
              <div>
                <span className="text-gray-500 block">Cold Chain Storage</span>
                <span className={cn('font-semibold', biologicsCold != null ? 'text-white' : 'text-gray-500 italic text-[10px]')}>{biologicsCold || 'N/A — not computed'}</span>
              </div>
              <div>
                <span className="text-gray-500 block">Immunogenicity Monitoring</span>
                <span className={cn('font-semibold', biologicsImm != null ? 'text-emerald-400' : 'text-gray-500 italic text-[10px]')}>{biologicsImm || 'N/A — not computed'}</span>
              </div>
            </div>
            <div className="text-[10px] text-gray-500 border-t border-dark-700/50 pt-2">
              Note: Peptides are regulated as biologics under the FDA Center for Drug Evaluation and Research (CDER). Approval requires a Biologics License Application (BLA).
            </div>
          </div>
        )}
      </div>
    );
  };

  // ═══════════════════════════════════════
  // RENDER: Biomolecules (peptides, antibodies, enzymes)
  // ═══════════════════════════════════════
  const renderBiomolecules = (bio: Record<string, any>, target?: string, backend?: string, totalTime?: number) => {
    if (!bio) return null;

    const sectionMeta: Record<string, { label: string; icon: typeof Dna; color: string; borderColor: string; gradientFrom: string }> = {
      therapeutic_peptides: { label: 'Therapeutic Peptides', icon: Dna, color: 'text-emerald-400', borderColor: 'border-emerald-500/20', gradientFrom: 'from-emerald-500/5' },
      antibody_fragments: { label: 'Antibody Fragments (Nanobodies)', icon: Shield, color: 'text-cyan-400', borderColor: 'border-cyan-500/20', gradientFrom: 'from-cyan-500/5' },
      enzyme_mimetics: { label: 'Enzyme Mimetics', icon: FlaskConical, color: 'text-amber-400', borderColor: 'border-amber-500/20', gradientFrom: 'from-amber-500/5' },
    };

    return (
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Atom className="w-4 h-4 text-purple-400" />
            <h4 className="text-sm font-semibold text-purple-400">Quantum Biomolecule Discovery</h4>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-gray-500">
            {target && <span>Target: <span className="text-white font-medium">{target}</span></span>}
            {backend && <span className="text-purple-400">{backend}</span>}
            {totalTime != null && <span>{safeNum(totalTime, 1)}s</span>}
          </div>
        </div>

        {Object.entries(bio).map(([key, section]) => {
          const meta = sectionMeta[key] || { label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()), icon: Beaker, color: 'text-gray-400', borderColor: 'border-dark-600', gradientFrom: 'from-dark-700/5' };
          const Icon = meta.icon;
          const candidates = section.candidates || [];
          if (candidates.length === 0) return null;

          return (
            <div key={key} className={cn('rounded-xl border bg-gradient-to-br via-transparent to-transparent p-3', meta.borderColor, meta.gradientFrom)}>
              <div className="flex items-center gap-2 mb-1">
                <Icon className={cn('w-4 h-4', meta.color)} />
                <h5 className={cn('text-sm font-semibold', meta.color)}>{meta.label}</h5>
                <span className="text-[10px] text-gray-500 ml-auto">{candidates.length} candidates</span>
              </div>
              {/* One-line legend of what the per-candidate metrics mean */}
              <div className="text-[9px] text-gray-500 mb-2 leading-tight">
                QOpt = quantum-optimization score (higher = better) · MW = molecular weight (Da/kDa) ·
                Interaction = predicted target-interaction score (0–1) · Hydrophobic = hydrophobic-residue ratio ·
                Net Charge = sequence net charge at pH 7 · Developability = manufacturability/stability (0–1).
                {(section.method || section.engine || section.provenance || section.source) && (
                  <> {' '}Source: {riskStr(section.method) || riskStr(section.engine) || riskStr(section.provenance) || riskStr(section.source)}.</>
                )}
              </div>

              <div className="space-y-2">
                {candidates.map((c: any, idx: number) => {
                  const kdNm = c.predicted_binding_kd_nm ?? c.binding_kd_nm ?? c.kd_nm;
                  const kdColor = kdNm != null ? (kdNm < 50 ? 'text-emerald-400' : kdNm < 500 ? 'text-yellow-400' : 'text-red-400') : 'text-gray-400';
                  const interScore = c.target_interaction_score;
                  const interColor = interScore != null ? (interScore > 0.7 ? 'text-emerald-400' : interScore > 0.4 ? 'text-yellow-400' : 'text-red-400') : 'text-gray-400';

                  return (
                    <div key={c.candidate_id || idx} className="bg-dark-800/60 border border-dark-700 rounded-lg p-2.5">
                      {/* Candidate header */}
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-gray-300">Candidate #{c.candidate_id || idx + 1}</span>
                        {c.quantum_optimization_score != null && (
                          <span className="text-[10px] text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded-full border border-purple-500/20">
                            QOpt: {safeNum(c.quantum_optimization_score, 2)}
                          </span>
                        )}
                      </div>

                      {/* Sequence */}
                      {(c.sequence || c.full_sequence) && (
                        <div className="mb-2">
                          <code className="text-[11px] font-mono text-quantum-300 bg-dark-900/50 px-2 py-1 rounded block overflow-x-auto whitespace-nowrap">
                            {c.sequence || c.full_sequence}
                          </code>
                          <div className="text-[10px] text-gray-400 mt-0.5">Length: {c.length || (c.sequence || c.full_sequence)?.length} aa</div>
                        </div>
                      )}

                      {/* Metrics grid */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-1.5 text-xs">
                        {kdNm != null && (
                          <div className="p-1.5 bg-dark-700/50 rounded text-center">
                            <div className="text-gray-500 text-[10px]">Binding Kd</div>
                            <div className={cn('font-bold font-mono', kdColor)}>{safeNum(kdNm, 1)} nM</div>
                            <MetricMeta
                              meaning="Predicted dissociation constant Kd (nM): target-binding affinity; lower = tighter."
                              meta={hvMeta(c.predicted_binding_kd_nm ?? c.binding_kd_nm ?? c.kd_nm, c, 'predicted_binding_kd_nm')}
                            />
                          </div>
                        )}
                        {c.molecular_weight_da != null && (
                          <div className="p-1.5 bg-dark-700/50 rounded text-center">
                            <div className="text-gray-500 text-[10px]">MW</div>
                            <div className="text-white font-bold font-mono">{safeNum(c.molecular_weight_da, 0)} Da</div>
                          </div>
                        )}
                        {c.molecular_weight_kda != null && (
                          <div className="p-1.5 bg-dark-700/50 rounded text-center">
                            <div className="text-gray-500 text-[10px]">MW</div>
                            <div className="text-white font-bold font-mono">{safeNum(c.molecular_weight_kda, 1)} kDa</div>
                          </div>
                        )}
                        {interScore != null && (
                          <div className="p-1.5 bg-dark-700/50 rounded text-center">
                            <div className="text-gray-500 text-[10px]">Interaction</div>
                            <div className={cn('font-bold font-mono', interColor)}>{safeNum(interScore, 3)}</div>
                          </div>
                        )}
                        {c.hydrophobic_ratio != null && (
                          <div className="p-1.5 bg-dark-700/50 rounded text-center">
                            <div className="text-gray-500 text-[10px]">Hydrophobic</div>
                            <div className="text-white font-bold font-mono">{asPercent(c.hydrophobic_ratio)}%</div>
                          </div>
                        )}
                        {c.net_charge != null && (
                          <div className="p-1.5 bg-dark-700/50 rounded text-center">
                            <div className="text-gray-500 text-[10px]">Net Charge</div>
                            <div className="text-white font-bold font-mono">{c.net_charge > 0 ? '+' : ''}{c.net_charge}</div>
                          </div>
                        )}
                        {c.binding_motif_used && (
                          <div className="p-1.5 bg-dark-700/50 rounded text-center">
                            <div className="text-gray-500 text-[10px]">Motif</div>
                            <div className="text-cyan-300 font-bold font-mono text-[11px]">{c.binding_motif_used}</div>
                          </div>
                        )}
                        {c.active_site_motif && (
                          <div className="p-1.5 bg-dark-700/50 rounded text-center">
                            <div className="text-gray-500 text-[10px]">Active Site</div>
                            <div className="text-amber-300 font-bold font-mono text-[11px]">{c.active_site_motif}</div>
                          </div>
                        )}
                        {c.substrate_specificity && (
                          <div className="p-1.5 bg-dark-700/50 rounded text-center">
                            <div className="text-gray-500 text-[10px]">Substrate</div>
                            <div className="text-amber-300 font-bold font-mono text-[11px]">{c.substrate_specificity}</div>
                          </div>
                        )}
                        {c.predicted_catalytic_efficiency != null && (
                          <div className="p-1.5 bg-dark-700/50 rounded text-center">
                            <div className="text-gray-500 text-[10px]">Cat. Eff.</div>
                            <div className="text-white font-bold font-mono">{safeNum(c.predicted_catalytic_efficiency, 3)}</div>
                          </div>
                        )}
                        {c.developability_score != null && (
                          <div className="p-1.5 bg-dark-700/50 rounded text-center">
                            <div className="text-gray-500 text-[10px]">Developability</div>
                            <div className={cn('font-bold font-mono', scoreColor(c.developability_score))}>{safeNum(c.developability_score, 2)}</div>
                          </div>
                        )}
                      </div>

                      {/* CDR regions for antibody fragments */}
                      {(c.cdr1 || c.cdr2 || c.cdr3) && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {c.cdr1 && <span className="text-[10px] bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 rounded px-1.5 py-0.5 font-mono">CDR1: {c.cdr1}</span>}
                          {c.cdr2 && <span className="text-[10px] bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 rounded px-1.5 py-0.5 font-mono">CDR2: {c.cdr2}</span>}
                          {c.cdr3 && <span className="text-[10px] bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 rounded px-1.5 py-0.5 font-mono">CDR3: {c.cdr3}</span>}
                        </div>
                      )}

                      {/* Catalytic residues for enzyme mimetics */}
                      {c.catalytic_residues && Array.isArray(c.catalytic_residues) && (
                        <div className="mt-2 flex items-center gap-1.5">
                          <span className="text-[10px] text-gray-500">Catalytic:</span>
                          {c.catalytic_residues.map((r: string, ri: number) => (
                            <span key={ri} className="text-[10px] bg-amber-500/10 text-amber-300 border border-amber-500/20 rounded px-1.5 py-0.5 font-mono">{r}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // ═══════════════════════════════════════
  // RENDER: Iterative Optimization Convergence
  // ═══════════════════════════════════════
  const renderOptimizationConvergence = (opt: any) => {
    if (!opt) return null;
    const iterations = opt.iterations || [];
    const goalsDetail = opt.goals_detail || [];
    const bestVar = opt.best_variant || {};
    const allMet = opt.goals_achieved;
    // Do NOT coerce a missing convergence to 0 ("0% converged" reads as a real
    // measurement). Keep it null and render "N/A" in the badge.
    const convergence = opt.convergence ?? null;

    return (
      <div className={cn(
        'rounded-xl border p-3',
        allMet
          ? 'border-emerald-500/30 bg-gradient-to-br from-emerald-500/5 via-transparent to-teal-500/5'
          : 'border-amber-500/30 bg-gradient-to-br from-amber-500/5 via-transparent to-orange-500/5'
      )}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Zap className={cn('w-4 h-4', allMet ? 'text-emerald-400' : 'text-amber-400')} />
            <h4 className={cn('text-sm font-semibold', allMet ? 'text-emerald-400' : 'text-amber-400')}>
              Iterative Quantum Optimization
            </h4>
          </div>
          <span className={cn(
            'text-xs font-bold px-2 py-0.5 rounded-full border',
            allMet
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
          )}>
            {allMet ? 'CONVERGED' : convergence != null ? `${asPercent(convergence)}% converged` : 'N/A — convergence not reported'}
          </span>
        </div>

        {/* Iteration progress */}
        {iterations.length > 1 && (
          <div className="mb-3">
            <div className="text-[10px] text-gray-500 mb-1">{iterations.length} iterations completed</div>
            <div className="flex items-center gap-1">
              {iterations.map((it: any, idx: number) => {
                const itConv = it.convergence ?? 0;
                const bgColor = itConv >= 1 ? 'bg-emerald-500' : itConv >= 0.5 ? 'bg-yellow-500' : 'bg-red-500';
                return (
                  <div key={idx} className="flex-1 flex flex-col items-center gap-0.5">
                    <div className={cn('h-2 w-full rounded-full', bgColor)} style={{ opacity: 0.3 + itConv * 0.7 }} />
                    <span className="text-[9px] text-gray-400">#{it.iteration}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Goals detail */}
        {goalsDetail.length > 0 && (
          <div className="space-y-1 mb-3">
            {goalsDetail.map((g: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between text-xs py-1 px-2 bg-dark-800/50 rounded">
                <div className="flex items-center gap-2">
                  <span className={cn('w-2 h-2 rounded-full', g.passed ? 'bg-emerald-500' : 'bg-red-500')} />
                  <span className="text-gray-400">{g.goal}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={cn('font-mono font-bold', g.passed ? 'text-emerald-400' : 'text-red-400')}>
                    {g.value != null ? safeNum(g.value, 2) : 'N/A'}
                  </span>
                  <span className="text-gray-400">{g.op}</span>
                  <span className="text-gray-400 font-mono">{g.target}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Best variant properties */}
        {bestVar.properties && Object.keys(bestVar.properties).length > 0 && (
          <>
          <div className="text-[9px] text-gray-500 mb-1 leading-tight">
            Best-variant properties from the iterative quantum-optimization loop. Binding = ΔG (kcal/mol, more negative = stronger) ·
            Oral Bioavail. = % dose systemically available · Half-Life = elimination t½ (h) · PPB = plasma-protein binding % ·
            Stability = predicted stability (0–1) · Immunogenicity = predicted risk (0–1, lower = safer).
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-1.5 text-xs">
            {bestVar.properties.binding_affinity_kcal != null && (
              <div className="p-1.5 bg-dark-700/50 rounded text-center">
                <div className="text-gray-500 text-[10px]">Binding</div>
                <div className="text-cyan-400 font-bold font-mono">{safeNum(bestVar.properties.binding_affinity_kcal, 2)} kcal</div>
              </div>
            )}
            {bestVar.properties.oral_bioavailability_pct != null && (
              <div className="p-1.5 bg-dark-700/50 rounded text-center">
                <div className="text-gray-500 text-[10px]">Oral Bioavail.</div>
                <div className="text-white font-bold font-mono">{safeNum(bestVar.properties.oral_bioavailability_pct, 1)}%</div>
              </div>
            )}
            {bestVar.properties.half_life_hours != null && (
              <div className="p-1.5 bg-dark-700/50 rounded text-center">
                <div className="text-gray-500 text-[10px]">Half-Life</div>
                <div className="text-white font-bold font-mono">{safeNum(bestVar.properties.half_life_hours, 1)}h</div>
              </div>
            )}
            {bestVar.properties.plasma_protein_binding_pct != null && (
              <div className="p-1.5 bg-dark-700/50 rounded text-center">
                <div className="text-gray-500 text-[10px]">PPB</div>
                <div className="text-white font-bold font-mono">{safeNum(bestVar.properties.plasma_protein_binding_pct, 1)}%</div>
              </div>
            )}
            {bestVar.properties.stability_score != null && (
              <div className="p-1.5 bg-dark-700/50 rounded text-center">
                <div className="text-gray-500 text-[10px]">Stability</div>
                <div className={cn('font-bold font-mono', scoreColor(bestVar.properties.stability_score))}>{safeNum(bestVar.properties.stability_score, 3)}</div>
              </div>
            )}
            {bestVar.properties.immunogenicity_risk != null && (
              <div className="p-1.5 bg-dark-700/50 rounded text-center">
                <div className="text-gray-500 text-[10px]">Immunogenicity</div>
                <div className={cn('font-bold font-mono', bestVar.properties.immunogenicity_risk < 0.3 ? 'text-emerald-400' : 'text-yellow-400')}>{safeNum(bestVar.properties.immunogenicity_risk, 3)}</div>
              </div>
            )}
          </div>
          </>
        )}

        {bestVar.sequence && (
          <div className="mt-2">
            <code className="text-[11px] font-mono text-quantum-300 bg-dark-900/50 px-2 py-1 rounded block overflow-x-auto whitespace-nowrap">
              {bestVar.sequence}
            </code>
          </div>
        )}
      </div>
    );
  };

  // ═══════════════════════════════════════
  // RENDER: ADMET summary card
  // ═══════════════════════════════════════
  const renderADMETSummary = (admet: any) => {
    if (!admet) return null;
    const categories = ['absorption', 'distribution', 'metabolism', 'excretion', 'toxicity'] as const;
    const labels: Record<string, string> = { absorption: 'A', distribution: 'D', metabolism: 'M', excretion: 'E', toxicity: 'T' };
    const colors: Record<string, string> = { absorption: 'text-green-400', distribution: 'text-blue-400', metabolism: 'text-yellow-400', excretion: 'text-orange-400', toxicity: 'text-red-400' };
    // Count only endpoints with a non-null value (honest-null {value:null}
    // endpoints must not inflate the parameter count / coverage claim).
    const countPopulated = (catData: any): number => {
      if (!catData || typeof catData !== 'object') return 0;
      return Object.values(catData).filter((v: any) => {
        if (v === null || v === undefined) return false;
        if (typeof v === 'object' && 'value' in v) return (v as any).value !== null && (v as any).value !== undefined;
        return true;
      }).length;
    };
    const paramCount = admet.parameters_count || ['absorption', 'distribution', 'metabolism', 'excretion', 'toxicity'].reduce((sum: number, key: string) => sum + countPopulated(admet[key]), 0);

    return (
      <div className="p-3 rounded-xl border border-green-500/20 bg-gradient-to-br from-green-500/5 via-transparent to-emerald-500/5">
        <div className="flex items-center gap-2 mb-1">
          <FlaskConical className="w-4 h-4 text-green-400" />
          <h4 className="text-sm font-semibold text-green-400">
            ADMET Profile {paramCount > 0 ? `(${paramCount} parameters)` : ''}
          </h4>
        </div>
        <div className="text-[9px] text-gray-500 mb-2 leading-tight">
          ADMET = Absorption, Distribution, Metabolism, Excretion, Toxicity — the pharmacokinetic/safety profile.
          Each tile counts the populated (non-null) endpoints in that category.
          {(admet.method || admet.engine || admet.provenance || admet.source) && (
            <> {' '}Method: {riskStr(admet.method) || riskStr(admet.engine) || riskStr(admet.provenance) || riskStr(admet.source)}.</>
          )}
        </div>
        <div className="grid grid-cols-5 gap-2 text-xs">
          {categories.map(cat => {
            const catData = admet[cat];
            const count = countPopulated(catData);
            return (
              <div key={cat} className="text-center p-2 bg-dark-700 rounded-lg">
                <div className={cn(colors[cat], 'text-lg font-bold mb-0.5')}>{labels[cat]}</div>
                <div className="text-white text-sm font-medium">{count}</div>
                <div className="text-gray-400 text-[10px] capitalize">{cat}</div>
                <div className="text-gray-400 text-[9px]">endpoints</div>
              </div>
            );
          })}
        </div>
        {/* Expanded detail for each ADMET category */}
        {categories.map(cat => {
          const catData = admet[cat];
          if (!catData || typeof catData !== 'object' || Object.keys(catData).length === 0) return null;
          return (
            <div key={cat} className="mt-2">
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">{cat}</div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-1">
                {Object.entries(catData).filter(([k]) => !k.endsWith('_detail')).slice(0, 30).map(([key, value]) => {
                  // Surface per-endpoint method/provenance/units when the value is
                  // a HonestValue object (or has sibling *_method keys on catData).
                  const endpointMeta = hvMeta(value, catData, key);
                  return (
                  <div key={key} className="text-[11px] bg-dark-700 rounded px-2 py-1">
                    <span className="text-gray-500">{key.replace(/_/g, ' ')}: </span>
                    <span className="text-white">{typeof value === 'number' ? safeNum(value, 3) : (typeof value === 'object' && value !== null ? ('value' in value ? ((value as any).value === null || (value as any).value === undefined ? `N/A${(value as any).null_reason ? ' — ' + (value as any).null_reason : ''}` : `${typeof (value as any).value === 'number' ? safeNum((value as any).value, 3) : (value as any).value}${(value as any).unit ? ' ' + (value as any).unit : ''}`) : ((value as any).label || (value as any).result || (value as any).null_reason || Object.entries(value as Record<string,unknown>).slice(0, 3).map(([k, v]) => `${k}:${typeof v === 'object' && v !== null ? ((v as any).label ?? (v as any).value ?? (v as any).null_reason ?? 'N/A') : (v ?? 'N/A')}`).join(', ') || 'N/A')) : String(value ?? 'N/A'))}</span>
                    {(endpointMeta.method || endpointMeta.provenance) && (
                      <MetricMeta meta={{ method: endpointMeta.method, provenance: endpointMeta.provenance }} />
                    )}
                  </div>
                  );
                })}
                {/* Un-truncated to 30 endpoints/category (was 9); remainder is shown
                    as an honest hidden-count, never silently dropped. */}
                {Object.entries(catData).filter(([k]) => !k.endsWith('_detail')).length > 30 && (
                  <div className="text-[11px] bg-dark-700 rounded px-2 py-1 text-gray-500 italic">
                    +{Object.entries(catData).filter(([k]) => !k.endsWith('_detail')).length - 30} more endpoints (open Raw JSON for the full list)
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // ═══════════════════════════════════════
  // RENDER: Best Candidate summary
  // ═══════════════════════════════════════
  const renderBestCandidate = (candidate: any, compositeScore: any, drugClass: any) => {
    if (!candidate) return null;
    return (
      <div className="p-3 rounded-xl border border-amber-500/20 bg-gradient-to-br from-amber-500/5 via-transparent to-yellow-500/5">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Atom className="w-4 h-4 text-amber-400" />
            <h4 className="text-sm font-semibold text-amber-400">{candidate.name || 'Best Candidate'}</h4>
          </div>
          {compositeScore != null && (
            <span className={cn('text-xs font-bold px-2 py-1 rounded-full border', scoreBg(compositeScore), scoreColor(compositeScore))}>
              Score: {sciNumOrNA(compositeScore, 4, 'composite score not computed')} &mdash; {drugClass || ''}
            </span>
          )}
        </div>
        {compositeScore != null && (
          <MetricMeta
            className="mb-2"
            meaning="Composite drug-likeness score (0–1): weighted blend of binding, ADMET, toxicity & developability; higher = stronger overall candidate. Class label is a banded interpretation of this score."
            meta={hvMeta(compositeScore)}
          />
        )}
        {candidate.smiles && (
          <div className="text-xs bg-dark-700 rounded-lg px-3 py-2 font-mono text-molecular-300 break-all">
            {candidate.smiles}
          </div>
        )}
        {candidate.smiles && (
          <div className="text-[9px] text-gray-400 mt-0.5">SMILES — canonical chemical structure string of the candidate molecule.</div>
        )}
        {!candidate.smiles && (candidate.sequence || candidate.vh_sequence || candidate.cdr_h3) && (
          <div className="text-xs bg-dark-700 rounded-lg px-3 py-2 font-mono text-molecular-300 break-all">
            {candidate.sequence || candidate.vh_sequence || candidate.cdr_h3}
          </div>
        )}
        {!candidate.smiles && (candidate.sequence || candidate.vh_sequence || candidate.cdr_h3) && (
          <div className="text-[9px] text-gray-400 mt-0.5">Amino-acid sequence (single-letter) of the candidate biomolecule — full sequence, not truncated.</div>
        )}
        {(candidate.kd_nM || candidate.kd_nm || candidate.scores?.kd_nm || candidate.binding_affinity_kcal || candidate.scores?.binding_energy) && (
          <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px]">
            <div className="bg-dark-700 rounded px-2 py-1">
              <span className="text-gray-500">KD nM: </span>
              <span className="text-cyan-300 font-mono">{sciNumOrNA(candidate.kd_nM ?? candidate.kd_nm ?? candidate.scores?.kd_nm, 4, 'affinity not computed (VQE ordinal only)')}</span>
              <MetricMeta
                meaning="Dissociation constant Kd (nM): binding affinity to target; lower = tighter."
                meta={hvMeta(candidate.kd_nM ?? candidate.kd_nm ?? candidate.scores?.kd_nm, candidate, 'kd_nM')}
              />
            </div>
            <div className="bg-dark-700 rounded px-2 py-1">
              <span className="text-gray-500">Binding ΔG (kcal/mol): </span>
              <span className="text-cyan-300 font-mono">{sciNumOrNA(candidate.binding_affinity_kcal ?? candidate.scores?.binding_energy, 4, 'binding free energy not computed')}</span>
              <MetricMeta
                meaning="Binding free energy ΔG (kcal/mol): more negative = stronger binding (e.g. MM-GBSA / docking score)."
                meta={hvMeta(candidate.binding_affinity_kcal ?? candidate.scores?.binding_energy, candidate, 'binding_affinity_kcal')}
              />
            </div>
            <div className="bg-dark-700 rounded px-2 py-1">
              <span className="text-gray-500">Humanization: </span>
              <span className="text-white font-mono">{sciNumOrNA(candidate.humanization_score ?? candidate.scores?.humanization_score, 3, 'not computed for this modality')}</span>
              <MetricMeta
                meaning="Humanization score (0–1, antibodies): similarity to human germline; higher = lower immunogenicity risk."
                meta={hvMeta(candidate.humanization_score ?? candidate.scores?.humanization_score, candidate, 'humanization_score')}
              />
            </div>
            <div className="bg-dark-700 rounded px-2 py-1">
              <span className="text-gray-500">Developability: </span>
              <span className="text-white font-mono">{sciNumOrNA(candidate.developability_score ?? candidate.developability?.developability_score ?? candidate.scores?.developability_score, 3, 'not computed for this modality')}</span>
              <MetricMeta
                meaning="Developability score (0–1): manufacturability/stability/solubility liabilities combined; higher = easier to develop."
                meta={hvMeta(candidate.developability_score ?? candidate.developability?.developability_score ?? candidate.scores?.developability_score, candidate, 'developability_score')}
              />
            </div>
          </div>
        )}
        {candidate.target && (
          <div className="mt-1.5 text-xs text-gray-500">Target: <span className="text-white">{typeof candidate.target === "object" ? ((candidate.target as any)?.name || (candidate.target as any)?.gene || "N/A — target not specified") : candidate.target}</span></div>
        )}
      </div>
    );
  };

  // ═══════════════════════════════════════
  // RENDER: IBM Job IDs
  // ═══════════════════════════════════════
  const renderJobIds = (ids: string[]) => {
    if (!ids || ids.length === 0) return null;
    return (
      <div className="p-2 rounded-lg border border-purple-500/10 bg-purple-500/5">
        <div className="flex items-center gap-2 mb-1 justify-between flex-wrap">
          <span className="flex items-center gap-2">
            <Zap className="w-3 h-3 text-purple-400" />
            <span className="text-xs font-medium text-purple-400">IBM Quantum: {ids.length} job{ids.length !== 1 ? 's' : ''} executed</span>
          </span>
          <ProvenanceBadge provenance={extractProvenance({ ibm_job_ids: ids })!} />
        </div>
        <div className="text-[9px] text-gray-500 mb-1 leading-tight">IBM Quantum Runtime job IDs — provenance handles to retrieve the raw quantum results on IBM Cloud.</div>
        <div className="flex flex-wrap gap-1">
          {/* Show up to 32 job IDs (was 8) so the run is fully traceable; only a
              pathological count is summarized with an honest hidden-count. */}
          {ids.slice(0, 32).map((id, i) => (
            <span key={i} className="text-[10px] font-mono px-1.5 py-0.5 bg-dark-700 text-gray-400 rounded">{id}</span>
          ))}
          {ids.length > 32 && (
            <span className="text-[10px] px-1.5 py-0.5 text-gray-500">+{ids.length - 32} more (open Raw JSON for all {ids.length})</span>
          )}
        </div>
      </div>
    );
  };

  // ═══════════════════════════════════════
  // RENDER: Pipeline stages indicator
  // ═══════════════════════════════════════
  const renderStagesSummary = (stages: Array<{name: string; status: string}>) => {
    if (!stages || stages.length === 0) return null;
    return (
      <div className="flex items-center gap-1 flex-wrap">
        <span className="text-xs text-gray-500 mr-1">Pipeline:</span>
        {stages.map((s, i) => (
          <span key={i} title={s.status === 'not_reported' ? 'status not reported' : s.status} className={cn(
            'text-[10px] px-2 py-0.5 rounded-full border',
            s.status === 'completed' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
            s.status === 'error' ? 'bg-red-500/10 border-red-500/20 text-red-400' :
            'bg-dark-700 border-dark-600 text-gray-400'
          )}>
            {s.name}{s.status === 'not_reported' ? ' (status not reported)' : ''}
          </span>
        ))}
      </div>
    );
  };

  // ═══════════════════════════════════════
  // RENDER: Protenix enrichment badge
  // ═══════════════════════════════════════
  // ═══════════════════════════════════════
  // RENDER: Quantum Cell Simulation (Molevera)
  // ═══════════════════════════════════════
  const renderQuantumCell = (qcell: any) => {
    if (!qcell || qcell.available === false) return null;

    // Extract data from validations (Molevera format)
    const validations = qcell.validations || {};
    const bioActivity = validations.biological_activity || {};
    const genomics = validations.genomics || {};
    const metabolic = validations.metabolic_route || {};
    const toxDomain = validations.toxicology || {};
    const pharmDomain = validations.pharmacology || {};

    const domainScores = qcell.domain_scores || {};
    const recommendation = qcell.recommendation;
    const cellType = qcell.cell_type || 'hepatocyte';
    const elapsed = qcell.elapsed_s;

    // Genes from validations
    const genesOn = bioActivity.genes_turned_on || genomics.genes_turned_on || [];
    const genesOff = bioActivity.genes_turned_off || genomics.genes_turned_off || [];
    const geneStates = genomics.gene_states || {};

    // Metabolic data
    const activeReactions = metabolic.active_reactions || [];
    const blockedReactions = metabolic.blocked_reactions || [];
    const disruptionScore = metabolic.metabolic_disruption_score;

    // Energy & stability
    const energyChange = bioActivity.energy_change;
    const networkStability = genomics.network_stability;

    // Toxicity markers
    const toxMarkers = toxDomain.toxicity_markers || qcell.toxicity_markers || {};

    const qScoreColor = (v: number | null) => v == null ? 'text-gray-500' : v > 0.7 ? 'text-green-400' : v > 0.4 ? 'text-yellow-400' : 'text-red-400';
    const qScoreBg = (v: number | null) => v == null ? 'bg-dark-700 border-dark-600' : v > 0.7 ? 'bg-green-500/10 border-green-500/20' : v > 0.4 ? 'bg-yellow-500/10 border-yellow-500/20' : 'bg-red-500/10 border-red-500/20';

    return (
      <div className="p-3 rounded-xl border border-violet-500/20 bg-gradient-to-br from-violet-500/5 via-transparent to-purple-500/5">
        {qcVizData && <QuantumCellViz data={qcVizData} onClose={() => setQcVizData(null)} />}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Atom className="w-4 h-4 text-violet-400" />
            <span className="text-sm font-semibold text-violet-300">Quantum Cell Simulation</span>
            <span className="text-[10px] text-gray-500 ml-1">{cellType} | Molevera</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setQcVizData({ quantum_cell_validation: qcell })}
              className="flex items-center gap-1 px-2 py-0.5 rounded-md border border-violet-500/40 bg-violet-500/10 text-violet-200 text-[10px] font-medium hover:bg-violet-500/20 transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400"
            >
              🔬 Ver animación
            </button>
            {elapsed != null && <span className="text-[10px] text-gray-400">{safeNum(elapsed, 0)}s</span>}
            {recommendation && (
              <span className={cn('px-2 py-0.5 rounded-full text-[10px] font-semibold border',
                recommendation === 'proceed' ? 'bg-green-500/10 border-green-500/20 text-green-400' :
                'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'
              )}>
                {recommendation.toUpperCase()}
              </span>
            )}
          </div>
        </div>

        {/* ── Tangential Validation: de-novo molecule validated by concordance with
            known agonists + real downstream network (replaces "UNVALIDATED"). Explicit
            calculations shown. ── */}
        {qcell.tangential_validation && (() => {
          const tv = qcell.tangential_validation;
          const mol = tv.molecule_concordance || {};
          const pert = tv.perturbation_concordance || {};
          const pct = (x: any) => (x == null ? null : `${(x * 100).toFixed(1)}%`);
          // Mechanism-aware: agonist concordance is only meaningful for agonist-modulated
          // targets. For a binder/inhibitor target (e.g. PCSK9) there is no agonist
          // reference by design — surface that so an N/A reads as "not applicable", not "failed".
          const agonistNA = mol.value == null && /agonist/i.test(String(mol.null_reason || tv.overall_concordance_na_reason || ''));
          // Real independent-model corroboration already computed (Geneformer cross-check).
          const gx = qcell.geneformer_xcheck || {};
          const gxConc = (gx.available && typeof gx.concordance === 'number') ? gx.concordance : null;
          return (
            <div className="mb-3 p-2.5 rounded-lg border border-emerald-500/25 bg-emerald-500/5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-emerald-300">Tangential Validation — de-novo molecule</span>
                {tv.overall_concordance != null && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
                    Overall concordance {pct(tv.overall_concordance)}
                  </span>
                )}
              </div>
              <div className="text-[10px] text-gray-400 mb-2 italic">{tv.validation_status}</div>

              {/* Molecule concordance — sequence identity vs known agonists (with calc) */}
              <div className="mb-2">
                <div className="flex justify-between text-[11px]">
                  <span className="text-gray-300 font-medium">Molecule concordance vs known agonists</span>
                  <span className={cn('font-bold', mol.value != null ? 'text-emerald-400' : 'text-gray-500 italic text-[10px]')}>
                    {mol.value != null ? pct(mol.value) : 'N/A'}
                  </span>
                </div>
                {mol.value != null ? (
                  <>
                    <div className="text-[10px] text-gray-400">{mol.provenance}</div>
                    <div className="text-[9px] text-gray-400">Method: {mol.method}</div>
                    {Array.isArray(mol.all_matches) && mol.all_matches.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {mol.all_matches.map((m: any, i: number) => (
                          <span key={i} className="px-1.5 py-0.5 rounded bg-dark-700 border border-dark-600 text-[9px] font-mono text-gray-300">
                            {m.agonist}: {m.identity_pct}% ({m.aligned_len}aa)
                          </span>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-[10px] text-gray-500 italic">N/A — {mol.null_reason}</div>
                )}
              </div>

              {/* Per-receptor concordance — triple-agonist validated vs EACH receptor's agonist */}
              {tv.per_receptor_concordance && Object.keys(tv.per_receptor_concordance).length > 1 && (
                <div className="mb-2">
                  <div className="text-[10px] text-gray-300 font-medium mb-0.5">Per-receptor concordance (multi-target)</div>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(tv.per_receptor_concordance).map(([rec, r]: [string, any], i: number) => (
                      <span key={i} className={cn('px-2 py-0.5 rounded-md border text-[10px] font-mono',
                        r?.value != null ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-300' : 'bg-dark-700 border-dark-600 text-gray-500')}>
                        {rec}: {r?.value != null ? `${(r.value * 100).toFixed(1)}%` : 'N/A'}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Perturbation concordance — vs real downstream network (with calc) */}
              <div className="mb-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-gray-300 font-medium">Perturbation concordance vs real network</span>
                  <span className={cn('font-bold', pert.value != null ? 'text-emerald-400' : 'text-gray-500 italic text-[10px]')}>
                    {pert.value != null ? pct(pert.value) : 'N/A'}
                  </span>
                </div>
                <div className="text-[10px] text-gray-400">{pert.value != null ? pert.provenance : `N/A — ${pert.null_reason || 'not computed'}`}</div>
                {Array.isArray(pert.sources) && pert.sources.length > 0 && (
                  <div className="text-[9px] text-gray-400">Data sources: {pert.sources.join(', ')}</div>
                )}
                {pert.lincs && <div className="text-[9px] text-gray-400">{pert.lincs}</div>}
                {pert.value === 0 && pert.disclaimer && (
                  <div className="text-[9px] text-gray-500 italic mt-0.5">{pert.disclaimer}</div>
                )}
              </div>

              {/* Mechanism-aware note: agonist concordance N/A is BY DESIGN for a
                  non-agonist target, not a pipeline failure. */}
              {agonistNA && (
                <div className="mb-1.5 px-2 py-1 rounded bg-blue-500/5 border border-blue-500/20">
                  <span className="text-[9px] text-blue-300">
                    Mechanism note: this target is not agonist-modulated, so sequence concordance vs known
                    <em> agonists</em> is not applicable (N/A by mechanism, not a failed measurement).
                    The independent-model cross-check below is the primary tangential signal here.
                  </span>
                </div>
              )}

              {/* Real independent-model corroboration — Geneformer cross-check (already computed) */}
              {gxConc != null && (
                <div className="mb-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-gray-300 font-medium">Independent-model cross-check (Geneformer)</span>
                    <span className="font-bold text-emerald-400">{pct(gxConc)}</span>
                  </div>
                  <div className="text-[10px] text-gray-400">
                    Corroboration between two independent models (quantum-cell ↔ Geneformer){gx.cell_type ? ` in ${gx.cell_type}` : ''}.
                    {gx.concordance_detail?.interpretation ? ` ${gx.concordance_detail.interpretation}` : ''}
                  </div>
                </div>
              )}

              {mol.disclaimer && (
                <div className="text-[9px] text-gray-400 pt-1 border-t border-dark-700/40 mt-1">{mol.disclaimer}</div>
              )}
            </div>
          );
        })()}

        {/* Domain scores bars */}
        {Object.keys(domainScores).length > 0 && (
          <div className="mb-3">
            <div className="text-[9px] text-gray-500 mb-1 leading-tight">Per-domain concordance/health scores (0–100%) from the Molevera quantum-cell simulation; higher = better. Source: Molevera Quantum Cell (AerSimulator).</div>
            <div className="space-y-1">
              {Object.entries(domainScores).map(([key, val]: [string, any]) => (
                <div key={key} className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-400 w-28 truncate">{key.replace(/_/g, ' ')}</span>
                  <div className="flex-1 h-1.5 bg-dark-700 rounded-full overflow-hidden">
                    {val != null ? (
                      <div
                        className={cn('h-full rounded-full transition-all', val > 0.7 ? 'bg-green-500' : val > 0.4 ? 'bg-yellow-500' : 'bg-red-500')}
                        style={{ width: `${Math.min(val * 100, 100)}%` }}
                      />
                    ) : (
                      <div className="h-full bg-gray-600 rounded-full" style={{ width: '0%' }} />
                    )}
                  </div>
                  <span className={cn('text-[10px] font-mono', qScoreColor(val))}>{val != null ? `${(val * 100).toFixed(0)}%` : 'N/A'}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Key metrics grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mb-3 text-xs">
          {energyChange != null && (
            <div className="p-1.5 bg-dark-700/50 rounded text-center">
              <div className="text-gray-500 text-[10px]">Energy</div>
              <div className={cn('font-bold font-mono', energyChange < 0 ? 'text-green-400' : 'text-red-400')}>{safeNum(energyChange, 3)}</div>
              <MetricMeta
                meaning="Simulated cell-state energy change (a.u.): negative = the perturbed network relaxes to a more stable state."
                meta={hvMeta(energyChange, bioActivity, 'energy_change')}
              />
            </div>
          )}
          {networkStability != null && (
            <div className={cn('p-1.5 rounded text-center', qScoreBg(networkStability))}>
              <div className="text-gray-500 text-[10px]">Network Stability</div>
              <div className={cn('font-bold font-mono', qScoreColor(networkStability))}>{asPercent(networkStability)}%</div>
              <MetricMeta
                meaning="Gene-regulatory network stability (0–100%): how robustly the network settles after perturbation; higher = more stable."
                meta={hvMeta(networkStability, genomics, 'network_stability')}
              />
            </div>
          )}
          {disruptionScore != null && (
            <div className={cn('p-1.5 rounded text-center', disruptionScore < 0.2 ? 'bg-green-500/10 border-green-500/20' : 'bg-yellow-500/10 border-yellow-500/20')}>
              <div className="text-gray-500 text-[10px]">Metabolic Disruption</div>
              <div className={cn('font-bold font-mono', disruptionScore < 0.2 ? 'text-green-400' : 'text-yellow-400')}>{asPercent(disruptionScore)}%</div>
              <MetricMeta
                meaning="Metabolic disruption (0–100%): fraction of flux/reactions perturbed by the compound; lower = safer metabolic profile."
                meta={hvMeta(disruptionScore, metabolic, 'metabolic_disruption_score')}
              />
            </div>
          )}
          {activeReactions.length > 0 && (
            <div className="p-1.5 bg-dark-700/50 rounded text-center">
              <div className="text-gray-500 text-[10px]">Active Reactions</div>
              <div className="text-white font-bold">{activeReactions.length}/{activeReactions.length + blockedReactions.length}</div>
              <MetricMeta meaning="Active vs total metabolic reactions in the simulated cell (active / total)." />
            </div>
          )}
        </div>

        {/* Gene states */}
        {Object.keys(geneStates).length > 0 && (
          <div className="mb-2">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Gene Regulatory Network</div>
            <div className="flex flex-wrap gap-1">
              {Object.entries(geneStates).map(([gene, active]: [string, any]) => (
                <span key={gene} className={cn('px-1.5 py-0.5 rounded text-[10px] font-mono border',
                  active ? 'bg-green-500/10 border-green-500/20 text-green-400' : 'bg-dark-700 border-dark-600 text-gray-500'
                )}>
                  {active ? '●' : '○'} {gene}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Genes ON/OFF — full lists (was capped at 5); show all up-regulated /
            down-regulated genes, with an honest hidden-count only past 60. */}
        {(genesOn.length > 0 || genesOff.length > 0) && Object.keys(geneStates).length === 0 && (
          <div className="mb-2">
            <div className="text-[9px] text-gray-500 mb-1 leading-tight">Genes turned ON (▲ up-regulated) / OFF (▼ down-regulated) by the perturbation in the simulated gene-regulatory network.</div>
            <div className="flex gap-3 text-[10px] flex-wrap">
              {genesOn.length > 0 && (
                <div className="flex items-start gap-1">
                  <span className="text-green-400">&#9650;</span>
                  <span className="text-gray-400">
                    {genesOn.slice(0, 60).join(', ')}
                    {genesOn.length > 60 && <span className="italic text-gray-400"> +{genesOn.length - 60} more</span>}
                    <span className="text-gray-400"> ({genesOn.length} total)</span>
                  </span>
                </div>
              )}
              {genesOff.length > 0 && (
                <div className="flex items-start gap-1">
                  <span className="text-red-400">&#9660;</span>
                  <span className="text-gray-400">
                    {genesOff.slice(0, 60).join(', ')}
                    {genesOff.length > 60 && <span className="italic text-gray-400"> +{genesOff.length - 60} more</span>}
                    <span className="text-gray-400"> ({genesOff.length} total)</span>
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Blocked reactions */}
        {blockedReactions.length > 0 && (
          <div className="mb-2">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Blocked Metabolic Reactions</div>
            <div className="flex flex-wrap gap-1">
              {blockedReactions.map((r: string) => (
                <span key={r} className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-red-500/10 border border-red-500/20 text-red-400">{r}</span>
              ))}
            </div>
          </div>
        )}

        {/* Toxicity markers */}
        {Object.keys(toxMarkers).length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {Object.entries(toxMarkers).map(([name, val]: [string, any]) => (
              <span key={name} className={cn('px-1.5 py-0.5 rounded text-[10px] border',
                Number(val) > 0.5 ? 'bg-red-500/10 border-red-500/20 text-red-400' :
                Number(val) > 0.2 ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400' :
                'bg-green-500/10 border-green-500/20 text-green-400'
              )}>
                {name.replace(/_/g, ' ')}: {(Number(val) * 100).toFixed(0)}%
              </span>
            ))}
          </div>
        )}

        {/* Honest-null quantum-cell metrics: surface their reason so a partial
            simulation isn't shown as a complete one. */}
        <HonestNullNotes items={collectHonestNulls(validations)} />

        {/* Engine badge */}
        <div className="mt-2 flex items-center gap-2 text-[9px] text-gray-500">
          <span>Engine: Molevera Quantum Cell</span>
          <span>|</span>
          <span>Backend: AerSimulator (Qiskit)</span>
          {qcell.elapsed_s && <><span>|</span><span>{qcell.elapsed_s}s</span></>}
        </div>
      </div>
    );
  };

  const renderProtenixEnrichment = (pe: any) => {
    if (!pe) return null;
    return (
      <div className="p-2 rounded-lg border border-cyan-500/20 bg-cyan-500/5 text-xs">
        <div className="flex items-center gap-3 flex-wrap">
          <Atom className="w-4 h-4 text-cyan-400" />
          <span className="text-cyan-400 font-medium">Structure Prediction</span>
          {pe.iptm != null && <span className="text-white">iPTM: <strong>{safeNum(pe.iptm, 3)}</strong></span>}
          {pe.plddt != null && <span className="text-white">pLDDT: <strong>{safeNum(pe.plddt, 1)}</strong></span>}
          {pe.binding_confidence && (
            <span className={cn('px-1.5 py-0.5 rounded-full text-[10px] font-medium border',
              String(pe.binding_confidence) === 'High' || pe.binding_confidence === true ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
              String(pe.binding_confidence) === 'Moderate' ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400' :
              'bg-red-500/10 border-red-500/20 text-red-400'
            )}>{typeof pe.binding_confidence === 'boolean' ? (pe.binding_confidence ? 'Confident' : 'Low') : riskStr(pe.binding_confidence)}</span>
          )}
        </div>
        {/* Explicit meaning of each structure-confidence metric */}
        <div className="mt-1 space-y-0.5">
          {pe.iptm != null && <div className="text-[9px] text-gray-500 leading-tight">iPTM — interface predicted TM-score (0–1): complex-interface confidence; higher = more reliable binding pose.</div>}
          {pe.plddt != null && <div className="text-[9px] text-gray-500 leading-tight">pLDDT — per-residue confidence (0–100): structure reliability; &gt;70 confident, &gt;90 very high.</div>}
          {pe.binding_confidence != null && <div className="text-[9px] text-gray-500 leading-tight">Binding confidence — overall qualitative reliability of the predicted bound complex.</div>}
          <div className="text-[9px] text-gray-400 leading-tight">Source: ESMFold2 / Protenix structure prediction.</div>
        </div>
      </div>
    );
  };

  return (
    <div
      className={cn(
        'group flex gap-4',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full shrink-0 flex items-center justify-center',
          isUser
            ? 'bg-dark-700'
            : 'bg-gradient-to-br from-quantum-500 to-quantum-700'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-gray-300" />
        ) : (
          <Zap className="w-4 h-4 text-dark-950" />
        )}
      </div>

      {/* Message Content */}
      <div className={cn('flex-1 max-w-[85%]', isUser && 'flex flex-col items-end')}>
        {/* Role & Time */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-gray-400">
            {isUser ? 'You' : 'Quantum Bio'}
          </span>
          <span className="text-xs text-gray-500">{formatTime(message.timestamp)}</span>
        </div>

        {/* Message Bubble */}
        <div
          className={cn(
            'rounded-2xl px-4 py-3',
            isUser
              ? 'bg-quantum-500/20 text-gray-100 rounded-tr-md'
              : 'bg-dark-800 text-gray-200 rounded-tl-md border border-dark-700'
          )}
        >
          {renderContent(message.content)}
        </div>

        {/* Tool Calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-3 w-full">
            <button
              onClick={() => setShowToolDetails(!showToolDetails)}
              className="flex items-center gap-2 text-xs text-gray-400 hover:text-gray-200 mb-2 transition-colors cursor-pointer rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              {showToolDetails ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
              {message.toolCalls.length} tool{message.toolCalls.length > 1 ? 's' : ''} used
            </button>

            {showToolDetails && (
              <div className="space-y-2">
                {message.toolCalls.map((tool) => (
                  <ToolExecutionCard key={tool.id} tool={tool} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Molecule Previews */}
        {message.molecules && message.molecules.length > 0 && (
          <div className="mt-3 flex gap-2 flex-wrap">
            {message.molecules.map((mol) => (
              <MoleculePreview key={mol.id} molecule={mol} />
            ))}
          </div>
        )}

        {/* Automatic Visualizations */}
        {message.visualizations && message.visualizations.length > 0 && (
          <div className="mt-3 w-full">
            <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
              <Eye className="w-3 h-3" />
              <span>{message.visualizations.length} visualization{message.visualizations.length > 1 ? 's' : ''} generated</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3" style={{gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))"}}>
              {message.visualizations.map((viz, idx) => (
                <div
                  key={viz.id}
                  className="bg-dark-900 border border-dark-700 rounded-lg overflow-hidden"
                >
                  <div className="p-2 bg-dark-800 border-b border-dark-700 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        viz.success ? "bg-green-500" : "bg-red-500"
                      )} />
                      <span className="text-xs text-gray-400">
                        {viz.type === 'docking_3d' ? 'DOCKING 3D' : (viz.type || 'VIZ').toUpperCase()} &bull; {viz.renderTime != null && viz.renderTime > 0 ? `${viz.renderTime}ms` : 'N/A'}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">#{idx + 1}</span>
                  </div>

                  {viz.success && viz.type === 'docking_3d' && viz.dockingData ? (
                    <DockingAnimation3D
                      proteinPdb={viz.dockingData.protein_pdb}
                      ligandSdf={viz.dockingData.ligand_sdf}
                      bindingSite={viz.dockingData.binding_site}
                      targetName={viz.dockingData.target_name}
                      smiles={viz.dockingData.smiles}
                      pdbId={viz.dockingData.pdb_id}
                      bindingAffinity={viz.dockingData.binding_affinity}
                    />
                  ) : viz.success && viz.image ? (
                    <div className="relative aspect-square bg-dark-950">
                      <img
                        src={viz.image}
                        alt={`Visualization ${idx + 1}`}
                        className="w-full h-full object-contain"
                      />
                    </div>
                  ) : (
                    <div className="p-4 text-center text-sm text-gray-500">
                      {viz.error || 'Rendering in progress...'}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════
            PIPELINE RESULTS - ALL VISUALIZATIONS IN THE CHAT
            ═══════════════════════════════════════════════════════════ */}
        {pipelineData && (
          <div className="mt-4 w-full space-y-3">
            {/* Universal visualization envelope — card + 3D viewer + charts +
                downloads. Works for ALL pipelines (antibody/peptide/small-mol/mRNA). */}
            {pipelineData.visualization && (
              <PipelineVisualization viz={pipelineData.visualization} />
            )}
            {pipelineData.qdiffvision && <QDiffVisionCard data={pipelineData.qdiffvision} />}

            {/* 3D molecular structure (folded peptide/protein) — real PDB viewer.
                Suppressed for the veterinary-antibody result: its card renders the
                SAME 273 KB complex with a chain legend, so rendering it again here
                (plus the identical complexPdb below) stacked 3-4 WebGL scenes of the
                same structure and froze the UI. */}
            {pipelineData.structure3dPdb && !pipelineData.moleveraVeterinaryAntibodyDesign && (
              <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-2">
                <div className="flex items-center gap-2 mb-1 px-1 flex-wrap">
                  <span className="text-xs font-semibold text-cyan-300">Predicted 3D Structure</span>
                  {pipelineData.structure3dMeta?.plddt != null && (
                    <span className="text-[9px] text-gray-500">pLDDT {safeNum(pipelineData.structure3dMeta.plddt, 0)} (per-residue confidence 0–100)
                      {pipelineData.structure3dMeta?.length_aa ? ` · ${pipelineData.structure3dMeta.length_aa} aa` : ''}</span>
                  )}
                  <button
                    onClick={() => openInBioqlViz(pipelineData.structure3dPdb, 'structure', 'pdb')}
                    title="Open this structure in BioQL-Viz (Mol* viewer: alignment, measurements, liabilities)"
                    className="ml-1 px-2 py-0.5 text-[10px] font-semibold rounded-full border border-indigo-500/40 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 cursor-pointer transition-colors"
                  >
                    Open in BioQL-Viz
                  </button>
                  <RaymolOpenButton
                    pdbData={pipelineData.structure3dPdb}
                    objectName="predicted_structure"
                    title="Predicted 3D Structure"
                  />
                </div>
                <InteractiveMoleculeViewer
                  pdbData={pipelineData.structure3dPdb}
                  posterImage={(pipelineData.pipelineImages?.find((im: any) =>
                    /structure|protein|complex|fold|3d/i.test(String(im?.type || '') + ' ' + String(im?.title || '')))?.image)
                    || pipelineData.pipelineImages?.[0]?.image}
                  title="Predicted Structure (ESMFold2 / Chai-1)"
                  height="340px"
                />
              </div>
            )}

            {/* Peptide:receptor COMPLEX — real protein+ligand docking structure.
                Also suppressed for the veterinary-antibody result (its card owns the
                labelled complex viewer) to avoid duplicate heavy WebGL scenes. */}
            {pipelineData.complexPdb && !pipelineData.moleveraVeterinaryAntibodyDesign && (
              <div className="rounded-xl border border-fuchsia-500/20 bg-fuchsia-500/5 p-2">
                <div className="flex items-center gap-2 mb-1 px-1 flex-wrap">
                  <span className="text-xs font-semibold text-fuchsia-300">Predicted Complex Structure — peptide : receptor docking</span>
                  {pipelineData.complexMeta?.iptm != null && (
                    <span className="text-[9px] text-gray-500">interface ipTM {safeNum(pipelineData.complexMeta.iptm, 3)} (binding-pose confidence 0–1)
                      {pipelineData.complexMeta?.receptor ? ` · ${pipelineData.complexMeta.receptor} + agonist` : ''}</span>
                  )}
                  <button
                    onClick={() => openInBioqlViz(pipelineData.complexPdb, pipelineData.complexMeta?.receptor ? `${pipelineData.complexMeta.receptor}_complex` : 'complex', 'pdb')}
                    title="Open this docked complex in BioQL-Viz (Mol* viewer: alignment, measurements, liabilities) — receptor + ligand together"
                    className="ml-1 px-2 py-0.5 text-[10px] font-semibold rounded-full border border-indigo-500/40 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 cursor-pointer transition-colors"
                  >
                    Open in BioQL-Viz
                  </button>
                  <RaymolOpenButton
                    pdbData={pipelineData.complexPdb}
                    objectName={pipelineData.complexMeta?.receptor ? `${pipelineData.complexMeta.receptor}_complex` : 'complex'}
                    title="Peptide:Receptor Complex"
                  />
                </div>
                <InteractiveMoleculeViewer
                  pdbData={pipelineData.complexPdb}
                  title="Peptide:Receptor Complex (docking pose)"
                  height="380px"
                />
                {pipelineData.complexMeta?.note && (
                  <div className="text-[9px] text-gray-400 mt-1 px-1">{pipelineData.complexMeta.note}</div>
                )}
              </div>
            )}

            {/* Receptor binding panel — peptide:receptor complex ipTM = real "docking" for a biologic */}
            {pipelineData.receptorPanel && Object.keys(pipelineData.receptorPanel).length > 0 && (
              <div className="rounded-xl border border-teal-500/20 bg-teal-500/5 p-2.5">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-teal-300">Receptor Binding (complex docking)</span>
                  <span className="text-[9px] text-gray-500">ipTM — interface predicted TM-score (0–1), ESMFold2/Protenix complex confidence</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {Object.entries(pipelineData.receptorPanel).map(([rec, rv]: [string, any], i: number) => {
                    const ipt = (rv && typeof rv === 'object') ? (rv.mean_iptm ?? rv.iptm ?? rv.value) : rv;
                    const n = typeof ipt === 'number' ? ipt : null;
                    return (
                      <div key={i} className="p-2 rounded-lg bg-dark-700 border border-dark-600/40 text-center">
                        <div className="text-[10px] text-gray-400">{rec}</div>
                        <div className={cn('text-lg font-bold', n != null ? (n > 0.55 ? 'text-emerald-400' : n > 0.4 ? 'text-yellow-400' : 'text-gray-300') : 'text-gray-500 italic text-[11px]')}>
                          {n != null ? safeNum(n, 3) : 'N/A'}
                        </div>
                        <div className="text-[9px] text-gray-400">ipTM</div>
                      </div>
                    );
                  })}
                </div>
                <div className="text-[9px] text-gray-400 mt-1.5">Method: peptide:receptor complex folded per receptor (ESMFold2/Protenix); ipTM is the binding-pose confidence — the real docking signal for a peptide/antibody biologic (BioHNet small-molecule docking N/A: no small-molecule ligand).</div>
              </div>
            )}

            {/* Pipeline stages indicator */}
            {pipelineData.stagesSummary && renderStagesSummary(pipelineData.stagesSummary)}

            {/* Best Candidate */}
            {renderBestCandidate(pipelineData.bestCandidate, pipelineData.compositeScore, pipelineData.drugClass)}

            {/* Composite Scoring Chart (recharts) */}
            {pipelineData.candidates && pipelineData.candidates.length > 0 && (
              <PipelineResultsChart candidates={pipelineData.candidates} />
            )}

            {/* Protenix Structure Prediction (recharts + framer-motion) */}
            {pipelineData.protenix && (
              <ProtenixConfidencePanel data={pipelineData.protenix} />
            )}

            {/* Protenix enrichment badge (from tox/pharm/clinical) */}
            {pipelineData.protenixEnrichment && renderProtenixEnrichment(pipelineData.protenixEnrichment)}

            {/* ADMET Radar Chart (recharts) */}
            {pipelineData.admet && (
              <ADMETRadarChart admetData={pipelineData.admet} />
            )}

            {/* ADMET Summary Table */}
            {pipelineData.admet && renderADMETSummary(pipelineData.admet)}

            {/* Docking Summary */}
            {pipelineData.docking && (() => {
              const dk = pipelineData.docking;
              // AutoDock Vina is a SMALL-MOLECULE engine. Antibody-antigen is
              // protein-protein, so binding_affinity_kcal is honestly null —
              // never show "AutoDock Vina ... ? kcal/mol" in that case.
              const vinaScore = dk.binding_affinity_kcal ?? dk.affinity;
              const hasRealVina = typeof vinaScore === 'number' && !isNaN(vinaScore);
              const iptm = dk.interface_confidence_iptm ?? dk.iptm ?? dk.interface_iptm;
              const methodStr = riskStr(dk.method);
              const poses = dk.poses_generated ?? dk.poses;
              return (
                <div className="bg-dark-800 border border-dark-600 rounded-lg p-3 mt-2">
                  <div className="text-xs text-green-400 font-semibold mb-1">
                    {hasRealVina
                      ? 'Molecular Docking (AutoDock Vina)'
                      : `Interface Assessment${methodStr ? ` (${methodStr})` : ' (structure-interface confidence)'}`}
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-[11px]">
                    <div>
                      <span className="text-gray-500">PDB: </span><span className="text-white">{riskStr(dk.pdb_id) || 'N/A'}</span>
                      <div className="text-[9px] text-gray-400 leading-tight">RCSB PDB structure ID used as the docking/interface receptor.</div>
                    </div>
                    {hasRealVina ? (
                      <div>
                        <span className="text-gray-500">Affinity: </span><span className="text-cyan-400 font-mono">{safeNum(vinaScore, 2)} kcal/mol</span>
                        <MetricMeta
                          meaning="Predicted binding free energy (kcal/mol); more negative = stronger binding."
                          meta={hvMeta(dk.binding_affinity_kcal ?? dk.affinity, dk, 'binding_affinity_kcal')}
                        />
                        {!(dk.binding_affinity_kcal_method || dk.binding_affinity_kcal_provenance || dk.method) && (
                          <div className="text-[9px] text-gray-400 leading-tight">Method: AutoDock Vina (small-molecule docking).</div>
                        )}
                      </div>
                    ) : (
                      <div><span className="text-gray-500">Affinity: </span><span className="text-gray-300">N/A — antibody-antigen interface (use interface ipTM / MM-GBSA, not ligand docking)</span></div>
                    )}
                    {!hasRealVina && iptm != null && (
                      <div>
                        <span className="text-gray-500">Interface ipTM: </span><span className="text-cyan-400 font-mono">{numOrNA(iptm, 3)}</span>
                        <MetricMeta
                          meaning="Interface predicted TM-score (0–1): confidence in the predicted protein-protein interface (ESMFold2/Protenix); higher = better."
                          meta={hvMeta(dk.interface_confidence_iptm ?? dk.iptm ?? dk.interface_iptm, dk, 'iptm')}
                        />
                      </div>
                    )}
                    {poses != null && (
                      <div>
                        <span className="text-gray-500">Poses: </span><span className="text-white">{numOrNA(poses, 0)}</span>
                        <div className="text-[9px] text-gray-400 leading-tight">Number of binding poses / structure samples generated and ranked.</div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* 3D Structure Viewer */}
            {pipelineData.mol3d && (Array.isArray(pipelineData.mol3d) ? pipelineData.mol3d.length > 0 : !!pipelineData.mol3d.protein_pdb) && (
              <div className="mt-3 bg-dark-900 border border-dark-700 rounded-lg overflow-hidden">
                <div className="p-2 bg-dark-800 border-b border-dark-700 flex flex-col md:flex-row md:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider">3D MOLECULAR STRUCTURE</span>
                    <button
                      onClick={() => {
                        const m = Array.isArray(pipelineData.mol3d)
                          ? pipelineData.mol3d[activeMol3dIdx] || pipelineData.mol3d[0]
                          : pipelineData.mol3d;
                        const pdb = m?.protein_pdb || m?.pdb;
                        if (!pdb) return;
                        openInBioqlViz(pdb, m.target_name || m.pdb_id || 'structure', 'pdb');
                      }}
                      title="Open this structure in BioQL-Viz (Mol* viewer: alignment, measurements, liabilities)"
                      className="ml-1 px-2 py-0.5 text-[10px] font-semibold rounded-full border border-indigo-500/40 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 cursor-pointer transition-colors"
                    >
                      Open in BioQL-Viz
                    </button>
                    {(() => {
                      const m = Array.isArray(pipelineData.mol3d)
                        ? pipelineData.mol3d[activeMol3dIdx] || pipelineData.mol3d[0]
                        : pipelineData.mol3d;
                      const pdb = m?.protein_pdb || m?.pdb;
                      if (!pdb) return null;
                      return (
                        <RaymolOpenButton
                          pdbData={pdb}
                          objectName={m.target_name || m.pdb_id || 'structure'}
                          title="3D Molecular Structure"
                        />
                      );
                    })()}
                  </div>
                  {Array.isArray(pipelineData.mol3d) && pipelineData.mol3d.length > 1 && (
                    <div className="flex flex-wrap gap-1">
                      {pipelineData.mol3d.map((item: any, idx: number) => {
                        const isSelected = idx === activeMol3dIdx;
                        return (
                          <button
                            key={idx}
                            onClick={() => setActiveMol3dIdx(idx)}
                            className={cn(
                              "px-2.5 py-0.5 text-[10px] font-semibold rounded-full transition-all duration-200 border cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400",
                              isSelected
                                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                                : "bg-dark-700 text-gray-400 border-dark-600 hover:bg-dark-600 hover:text-gray-300"
                            )}
                          >
                            {item.target_name || `Target ${idx + 1}`}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
                {(() => {
                  const activeMol = Array.isArray(pipelineData.mol3d)
                    ? pipelineData.mol3d[activeMol3dIdx] || pipelineData.mol3d[0]
                    : pipelineData.mol3d;
                  if (!activeMol || !activeMol.protein_pdb) return null;
                  // Protein-only structures (e.g. a replicon enzyme active site
                  // with no docked ligand) render in the plain protein viewer —
                  // NOT the docking animation, which would draw a stray binding
                  // sphere at the origin and hang on "Loading docking complex".
                  // Heuristic covers results generated before the protein_only flag.
                  const isBiologicOrAntibody = pipelineData.drugClass === 'Antibody' || pipelineData.drugClass === 'Nanobody' || !!pipelineData.quantumBiologic || !!activeMol.ligand_sdf_null_reason || activeMol.is_antibody;
                  const isProteinOnly = activeMol.protein_only
                    || isBiologicOrAntibody
                    || (!activeMol.ligand_sdf && !activeMol.smiles && !activeMol.peptide_sequence
                        && !(pipelineData.bestCandidate && pipelineData.bestCandidate.smiles)
                        && (activeMol.kind || activeMol.role));
                  if (isProteinOnly) {
                    // Real interactive viewer: hover tooltips, click-to-inspect
                    // (measured cross-chain contacts + pLDDT), full measure mode
                    // (distance/angle/dihedral), Kabsch structural comparison,
                    // render-style toggle, and automatic ligand/HETATM styling —
                    // this covers the replicon's computed docking (Boltz-2
                    // protein:ligand AND Chai-1 protein:protein) since those
                    // entries carry their ligand/second chain already embedded
                    // in protein_pdb (ligand_sdf/smiles are null), landing here.
                    return (
                      <InteractiveMoleculeViewer
                        pdbData={activeMol.protein_pdb}
                        pdbId={activeMol.pdb_id}
                        title={activeMol.target_name + (activeMol.role ? ` — ${activeMol.role}` : '')}
                        bindingSite={activeMol.binding_site}
                        highlightResidues={activeMol.highlight_residues}
                      />
                    );
                  }
                  return (
                    <DockingAnimation3D
                      proteinPdb={activeMol.protein_pdb}
                      ligandSdf={activeMol.protein_only ? undefined : activeMol.ligand_sdf}
                      bindingSite={activeMol.protein_only ? undefined : activeMol.binding_site}
                      targetName={activeMol.target_name || (pipelineData.bestCandidate && pipelineData.bestCandidate.target)}
                      smiles={activeMol.protein_only ? undefined : (activeMol.smiles || activeMol.peptide_sequence || (pipelineData.bestCandidate && pipelineData.bestCandidate.smiles))}
                      pdbId={activeMol.pdb_id}
                      // ipTM (0-1 interface confidence) must never be passed as
                      // bindingAffinity (kcal/mol) — it's rendered separately
                      // below with an honest "ipTM ... (interface confidence)" label.
                      bindingAffinity={activeMol.protein_only ? undefined : (activeMol.binding_affinity || (pipelineData.docking && pipelineData.docking.binding_affinity_kcal))}
                      interfaceConfidenceIptm={activeMol.protein_only ? undefined : (activeMol.interface_confidence_iptm ?? activeMol.iptm)}
                    />
                  );
                })()}
              </div>
            )}

            {/* Iterative Optimization Convergence */}
            {pipelineData.optimization && renderOptimizationConvergence(pipelineData.optimization)}

            {/* Toxicology */}
            {pipelineData.toxicology && renderToxicology(pipelineData.toxicology)}

            {/* Pharmacology */}
            {pipelineData.pharmacology && renderPharmacology(pipelineData.pharmacology)}

            {/* Clinical Trial */}
            {pipelineData.clinical && renderClinicalTrial(pipelineData.clinical)}

            {/* Quantum Cell Simulation (Molevera) — dedicated card (additive).
                The standalone QuantumCellCard renders the FULL whole-sim result
                (Modal A100 / CUDA-Q provenance, VQE energies, GRN states, domain
                scores, cross-checks) and honestly surfaces available:false reasons.
                Tox/Pharm variants keep the legacy renderQuantumCell surface. */}
            {pipelineData.quantumCell && <QuantumCellCard qcell={pipelineData.quantumCell} />}
            {pipelineData.quantumCellTox && renderQuantumCell(pipelineData.quantumCellTox)}
            {pipelineData.quantumCellPharm && renderQuantumCell(pipelineData.quantumCellPharm)}

            {/* Biomolecules (Therapeutic Peptides, Antibody Fragments, Enzyme Mimetics) */}
            {pipelineData.biomolecules && renderBiomolecules(
              pipelineData.biomolecules,
              pipelineData.biomoleculesTarget,
              pipelineData.biomoleculesBackend,
              pipelineData.biomoleculesTotalTime,
            )}

            {/* Pipeline Images (2D molecules, ADMET radar, toxicity heatmap) */}
            {pipelineData.pipelineImages && pipelineData.pipelineImages.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                  <Eye className="w-3.5 h-3.5" />
                  Visualizations ({pipelineData.pipelineImages.length})
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {pipelineData.pipelineImages.map((img: any, idx: number) => (
                    <div key={idx} className="bg-dark-800/50 border border-dark-700 rounded-lg overflow-hidden">
                      {img.title && (
                        <div className="px-3 py-1.5 border-b border-dark-700 flex items-center justify-between">
                          <span className="text-xs font-medium text-gray-300">{img.title}</span>
                          <span className="text-[10px] text-gray-500 uppercase">{img.type?.replace(/_/g, ' ')}</span>
                        </div>
                      )}
                      <img
                        src={img.image}
                        alt={img.title || `Visualization ${idx + 1}`}
                        className="w-full h-auto"
                        loading="lazy"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* IBM Quantum Job IDs */}
            {pipelineData.ibmJobIds && renderJobIds(pipelineData.ibmJobIds)}

            {/* ═══ DOWNLOAD FULL REPORT ═══ */}
            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={() => handleDownloadReport('pdf')}
                disabled={reportStatus === 'generating'}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer",
                  "border shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400",
                  reportStatus === 'generating'
                    ? "bg-dark-700 border-dark-600 text-gray-400 cursor-wait"
                    : reportStatus === 'done'
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"
                    : reportStatus === 'error'
                    ? "bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20"
                    : "bg-gradient-to-r from-teal-500/10 to-cyan-500/10 border-teal-500/30 text-teal-300 hover:from-teal-500/20 hover:to-cyan-500/20 hover:border-teal-400/50 hover:shadow-teal-500/10"
                )}
              >
                {reportStatus === 'generating' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : reportStatus === 'done' ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <FileText className="w-4 h-4" />
                )}
                {reportStatus === 'generating' ? 'Generating Report...'
                  : reportStatus === 'done' ? 'Report Downloaded'
                  : reportStatus === 'error' ? 'Generation Failed — Retry'
                  : 'Download Full Report (PDF)'}
              </button>
              <button
                onClick={() => {
                  const toolData = message.toolCalls?.find(t => t.output);
                  if (toolData?.output) downloadJSON(toolData.output, "BioQL_data_" + Date.now());
                }}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border border-dark-600 text-gray-400 hover:text-gray-300 hover:border-dark-500 hover:bg-dark-700/50 transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                <Download className="w-3.5 h-3.5" />
                Raw JSON
              </button>
            </div>

            {/* Validation Banner */}
            {pipelineData.validation && (
              <ValidationBanner validation={pipelineData.validation} />
            )}

            {/* Low Confidence Warning */}
            {pipelineData.lowConfidenceWarning && (
              <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <p className="text-sm text-yellow-300">{pipelineData.lowConfidenceWarning}</p>
              </div>
            )}

            {/* Score Breakdown (legacy) */}
            {pipelineData.scoreBreakdown && !pipelineData.candidates?.length && (
              <div className="p-3 bg-dark-800 border border-dark-700 rounded-lg">
                <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Score Breakdown</h4>
                <div className="grid grid-cols-4 gap-2">
                  {Object.entries(pipelineData.scoreBreakdown).map(([key, val]: [string, any]) => {
                    // A docking row whose weight was redistributed to 0 (common for
                    // peptides: too large for Vina) is N/A, not a real 0.0 contribution.
                    const weightZeroed = typeof val === 'object' && val != null && Number(val.weight) === 0;
                    const naRedistributed = weightZeroed && key.toLowerCase() === 'docking';
                    return (
                      <div key={key} className="text-center">
                        {/* Do not coerce a null sub-score to 0; show 'N/A'. */}
                        <div className={cn('font-bold', naRedistributed ? 'text-gray-500 text-[11px] italic' : 'text-lg text-white')}>
                          {naRedistributed ? 'N/A — Vina N/A (peptide)' : (typeof val === 'object' && val != null ? numOrNA(val.weighted ?? val.score, 2) : numOrNA(val, 2))}
                        </div>
                        <div className="text-xs text-gray-500 capitalize">{key}</div>
                        {typeof val === 'object' && val != null && val.weight != null && (
                          <div className="text-xs text-gray-400">{naRedistributed ? 'weight redistributed' : `w: ${safeNum(Number(val.weight) * 100, 0)}%`}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
                {pipelineData.scoringMethodology?.weight_justification && (
                  <p className="text-xs text-gray-500 mt-2 italic">
                    Weights: {pipelineData.scoringMethodology.weight_justification}
                  </p>
                )}
              </div>
            )}

            {/* Insights */}
            {pipelineData.insights && Array.isArray(pipelineData.insights) && pipelineData.insights.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Emergent Insights</h4>
                <InsightCard insights={pipelineData.insights} />
              </div>
            )}

            {/* ── NEW calculation cards (additive; each no-ops when its data is absent) ── */}
            {pipelineData.fep && <FEPResultsCard data={pipelineData.fep} />}
            {pipelineData.rbfe && <RBFECorrectionCard data={pipelineData.rbfe} />}
            {pipelineData.diffdock && <DiffDockCard data={pipelineData.diffdock} />}
            {pipelineData.genmol && <GenMolCard data={pipelineData.genmol} />}
            {pipelineData.binder && <BinderDesignCard data={pipelineData.binder} />}
            {pipelineData.crispr && <CrisprOfftargetCard data={pipelineData.crispr} />}
            {pipelineData.metabolism && <MetabolismCard data={pipelineData.metabolism} />}
            {pipelineData.nmrSpectrum && <NmrSpectrumCard data={pipelineData.nmrSpectrum} />}
            {pipelineData.msmsSpectrum && <MsmsSpectrumCard data={pipelineData.msmsSpectrum} />}
            {pipelineData.qchem && <QuantumChemBoundaryCard data={pipelineData.qchem} />}
            {pipelineData.trustBadges && <TrustBadgesCard data={pipelineData.trustBadges} />}
            {pipelineData.selectivity && <SelectivityCard data={pipelineData.selectivity} />}
            {pipelineData.translational && <TranslationalSafetyCard data={pipelineData.translational} />}

            {pipelineData.replicon && <RepliconCard data={pipelineData.replicon} />}
            {pipelineData.rejuvenation && <RejuvenationTherapyCard data={pipelineData.rejuvenation} />}
            {pipelineData.veterinaryAntibodyProgram && <VeterinaryAntibodyProgramCard data={pipelineData.veterinaryAntibodyProgram} />}
            {pipelineData.veterinaryAntibodyProgram && <VeterinaryAntibodyEvidenceCard data={pipelineData.veterinaryAntibodyProgram} />}
            {pipelineData.veterinaryAntibodyProgram && <VeterinaryAntibodyGatesCard data={pipelineData.veterinaryAntibodyProgram} />}
            {pipelineData.moleveraVeterinaryAntibodyDesign && <MoleveraVeterinaryAntibodyDesignCard data={pipelineData.moleveraVeterinaryAntibodyDesign} />}
            {pipelineData.moleveraVeterinaryAntibodyDesign && <MoleveraVeterinaryDrugProductCard data={pipelineData.moleveraVeterinaryAntibodyDesign} />}
            {pipelineData.moleveraVeterinaryAntibodyDesign && <MoleveraVeterinaryQuantumCard data={pipelineData.moleveraVeterinaryAntibodyDesign} />}
            {pipelineData.quantumBiologic && <QuantumBiologicDesignCard data={pipelineData.quantumBiologic} />}
            {pipelineData.bioqlGqe && <BioQLGQECard data={pipelineData.bioqlGqe} />}
            {pipelineData.activeCudaqReview && <ActiveCudaQReviewCard data={pipelineData.activeCudaqReview} />}
            {pipelineData.generativeModel && <GenerativeModelCard data={pipelineData.generativeModel} />}
            {pipelineData.consistencyAudit && <ConsistencyAuditCard data={pipelineData.consistencyAudit} />}
            {pipelineData.structuralReview && <StructuralReviewCard data={pipelineData.structuralReview} />}
            {pipelineData.resultContract && <ResultContractCard data={pipelineData.resultContract} />}
            {pipelineData.nirCycle && <NirCycleCard data={pipelineData.nirCycle} />}
            {pipelineData.nirProtein && <NirProteinCard data={pipelineData.nirProtein} />}
            {pipelineData.nirEvolve && <NirEvolveCard data={pipelineData.nirEvolve} />}
            {pipelineData.nirDeliverable && <NirDeliverableCard data={pipelineData.nirDeliverable} />}
            {pipelineData.mhsDevices && <MhsDevicePanel data={pipelineData.mhsDevices} />}
            {pipelineData.mhsAssay && <MhsAssayCard data={pipelineData.mhsAssay} />}
            {pipelineData.crisprTherapeutic && <CrisprTherapeuticCard data={pipelineData.crisprTherapeutic} />}

            {/* AlphaGenome universal: solo si ninguna tarjeta dedicada la pinta
                ya por dentro, para no duplicar la seccion. */}
            {pipelineData.regulatory && !regulatoryAlreadyEmbedded
              && <RegulatoryActivityCard reg={pipelineData.regulatory} />}
            {pipelineData.veterinary && <VeterinaryCard data={pipelineData.veterinary} />}
            {pipelineData.veterinaryDiscovery && <VeterinaryDiscoveryCard data={pipelineData.veterinaryDiscovery} />}
            {pipelineData.dueDiligence && <DueDiligenceCard data={pipelineData.dueDiligence} />}
            {pipelineData.bionemoAug && <BioNeMoAugCard data={pipelineData.bionemoAug} />}
            {pipelineData.antibodyBench && <AntibodyBenchmarkCard data={pipelineData.antibodyBench} />}
            {pipelineData.pdcDesign && <PDCDesignCard data={pipelineData.pdcDesign} />}
            {pipelineData.adarSensor && <ADARSensorCard data={pipelineData.adarSensor} />}
            {pipelineData.interimAnalysis && <InterimAnalysisCard data={pipelineData.interimAnalysis} />}
            {pipelineData.quantumSteered && <QuantumSteeredDesignCard data={pipelineData.quantumSteered} />}
            {pipelineData.audit && <AuditPanel data={pipelineData.audit} />}

            {/* Molecular Relationships */}
            {pipelineData.molecularRelationships && (
              <MolecularRelationshipGraph relationships={pipelineData.molecularRelationships} />
            )}

            {/* Provenance */}
            {pipelineData.provenance && (
              <ProvenancePanel provenance={pipelineData.provenance} />
            )}

            {/* Clinical Validation */}
            {pipelineData.externalValidation && (
              <ClinicalValidationPanel externalValidation={pipelineData.externalValidation} />
            )}
          </div>
        )}

        {/* Interactive report — the run explained in 3D, built from its own result */}
        {isAssistant && <InteractiveReportLink result={reportResult} sessionId={reportSessionId} />}

        {/* Actions */}
        {isAssistant && (
          <div className="flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="h-9 w-9 flex items-center justify-center hover:bg-dark-700 rounded transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              title="Copy"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-molecular-400" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-gray-400" />
              )}
            </button>
            <button
              onClick={() => {}}
              className="h-9 w-9 flex items-center justify-center hover:bg-dark-700 rounded transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              title="Regenerate"
            >
              <RefreshCw className="w-3.5 h-3.5 text-gray-400" />
            </button>
            <button
              onClick={() => {
                const toolData = message.toolCalls?.find(t => t.output);
                if (toolData?.output) downloadJSON(toolData.output, "bioql_export_" + Date.now());
              }}
              className="h-9 w-9 flex items-center justify-center hover:bg-dark-700 rounded transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              title="Export JSON"
            >
              <Download className="w-3.5 h-3.5 text-gray-400" />
            </button>
            <div className="w-px h-4 bg-dark-700 mx-1" />
            <button
              onClick={() => setFeedback(feedback === 'up' ? null : 'up')}
              title="Good response"
              aria-label="Good response"
              className={cn(
                'h-9 w-9 flex items-center justify-center hover:bg-dark-700 rounded transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-molecular-400',
                feedback === 'up' && 'bg-molecular-500/20'
              )}
            >
              <ThumbsUp
                className={cn(
                  'w-3.5 h-3.5',
                  feedback === 'up' ? 'text-molecular-400' : 'text-gray-400'
                )}
              />
            </button>
            <button
              onClick={() => setFeedback(feedback === 'down' ? null : 'down')}
              title="Bad response"
              aria-label="Bad response"
              className={cn(
                'h-9 w-9 flex items-center justify-center hover:bg-dark-700 rounded transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-alert-error',
                feedback === 'down' && 'bg-alert-error/20'
              )}
            >
              <ThumbsDown
                className={cn(
                  'w-3.5 h-3.5',
                  feedback === 'down' ? 'text-alert-error' : 'text-gray-400'
                )}
              />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
