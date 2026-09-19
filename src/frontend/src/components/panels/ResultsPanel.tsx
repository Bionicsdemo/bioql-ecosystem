/**
 * ResultsPanel - Displays real pipeline results in a table format
 * Stores results in localStorage for persistence across sessions
 * Supports: Candidates, Toxicology, Pharmacology, Clinical Trials, ADMET
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Table,
  Download,
  Trash2,
  ChevronDown,
  ChevronRight,
  ArrowUpDown,
  CheckCircle,
  XCircle,
  Clock,
  Beaker,
  Shield,
  Pill,
  Activity,
  FlaskConical,
  Dna,
  Microscope,
  Image,
} from 'lucide-react';
import { ProtenixConfidencePanel } from '../visualizations/ProtenixConfidencePanel';
import { ProvenanceBadge, extractProvenance } from '../common/ProvenanceBadge';
import { ADMETRadarChart } from '../visualizations/ADMETRadarChart';
import { PipelineResultsChart } from '../visualizations/PipelineResultsChart';
import { idbGetJson, idbSetJson } from '@/utils/idbPersist';

// UUID helper for browser compatibility
const generateUUID = (): string => {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
  } catch (e) { }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

// Interfaces
export interface DrugCandidate {
  id: string;
  smiles: string;
  name?: string;
  mw: number;
  logp: number;
  hbd: number;
  hba: number;
  tpsa: number;
  lipinski_pass: boolean;
  affinity: number | null;
  selected: boolean;
  composite_score?: number;
  score_breakdown?: Record<string, any>;
  drug_candidate_class?: string;
}

export interface ToxicologyData {
  overall_safety: string;
  ld50_predicted?: number;
  herg_risk?: string;
  ames_mutagenicity?: string;
  hepatotoxicity_risk?: string;
  cardiotoxicity_risk?: string;
  nephrotoxicity_risk?: string;
  immunotoxicity_risk?: string;
  proceed_to_clinical?: boolean;
  overall_score?: number;
  quantum_algorithms_used?: string[];
  ibm_job_ids?: string[];
}

export interface PharmacologyData {
  bioavailability?: number;
  half_life_hours?: number;
  volume_distribution?: number;
  clearance?: number;
  bbb_penetration?: string;
  mechanism_of_action?: string;
  target_engagement?: number;
  dose_response_ec50?: number;
  overall_score?: number;
  quantum_algorithms_used?: string[];
  ibm_job_ids?: string[];
}

export interface ClinicalTrialData {
  phase1_success_probability?: number;
  phase2_success_probability?: number;
  phase3_success_probability?: number;
  overall_approval_probability?: number;
  estimated_timeline_months?: number;
  recommended_dose_mg?: number;
  patient_population?: string;
  overall_success?: string;
  quantum_algorithms_used?: string[];
  ibm_job_ids?: string[];
}

export interface ADMETData {
  parameters_count?: number;
  absorption?: Record<string, any>;
  distribution?: Record<string, any>;
  metabolism?: Record<string, any>;
  excretion?: Record<string, any>;
  toxicity?: Record<string, any>;
  radar_summary?: Record<string, number>;
  quantum_algorithms_used?: string[];
  ibm_job_ids?: string[];
}

export interface PipelineResult {
  id: string;
  timestamp: Date;
  target: string;
  pdb_id: string;
  backend: string;
  status: 'completed' | 'failed' | 'partial';
  candidates: DrugCandidate[];
  execution_time: number;
  error?: string;
  toxicology?: ToxicologyData;
  pharmacology?: PharmacologyData;
  clinical_trial?: ClinicalTrialData;
  admet?: ADMETData;
  protenix_structure?: any;
  alphagenomic_data?: any;
  complexa_binders?: any;
  pipeline_stages?: string[];
  images?: Array<{type: string; title: string; image: string; format: string; width: number; height: number}>;
}

// Results store singleton for cross-component access
// Keep the most recent N pipeline results. IndexedDB has a large quota
// (hundreds of MB), so this cap exists only to bound growth — not to fit a
// ~5MB localStorage budget. Full dossiers (candidates, structures, images,
// viz) are persisted intact.
const MAX_STORED_RESULTS = 30;

class ResultsStore {
  private results: PipelineResult[] = [];
  private listeners: Set<() => void> = new Set();
  private storageKey = 'bioql_pipeline_results';
  // Resolves once the initial async load from IndexedDB has completed.
  public ready: Promise<void>;

  constructor() {
    this.ready = this.loadFromStorage();
  }

  private async loadFromStorage(): Promise<void> {
    try {
      // idbGetJson also performs the one-time localStorage -> IndexedDB
      // migration for this key, so legacy history is preserved.
      const parsed = await idbGetJson<any[]>(this.storageKey);
      if (Array.isArray(parsed)) {
        this.results = parsed.map((r: any) => ({
          ...r,
          timestamp: new Date(r.timestamp),
        }));
        this.notifyListeners();
      }
    } catch (e) {
      console.error('Failed to load results from storage:', e);
    }
  }

  private saveToStorage() {
    // Persist full result objects to IndexedDB (large quota). We only convert
    // the Date timestamp to an ISO string for JSON-safety; no lossy compaction.
    const payload = this.results.slice(0, MAX_STORED_RESULTS).map((r) => ({
      ...r,
      timestamp: r.timestamp.toISOString(),
    }));
    // Fire-and-forget; persistence failures are non-fatal (in-memory remains).
    void idbSetJson(this.storageKey, payload).then((ok) => {
      if (!ok) {
        console.warn('[ResultsStore] Could not persist pipeline results to IndexedDB. Results remain in memory for this session.');
      }
    });
  }

  addResult(result: Omit<PipelineResult, 'id' | 'timestamp'>) {
    const newResult: PipelineResult = {
      ...result,
      id: generateUUID(),
      timestamp: new Date(),
    };
    this.results.unshift(newResult);
    if (this.results.length > MAX_STORED_RESULTS) {
      this.results = this.results.slice(0, MAX_STORED_RESULTS);
    }
    this.saveToStorage();
    this.notifyListeners();
    return newResult;
  }

  getResults(): PipelineResult[] {
    return [...this.results];
  }

  deleteResult(id: string) {
    this.results = this.results.filter(r => r.id !== id);
    this.saveToStorage();
    this.notifyListeners();
  }

  clearAll() {
    this.results = [];
    this.saveToStorage();
    this.notifyListeners();
  }

  /** Persist in-memory results using compact quota-safe serialization. */
  persistToStorage() {
    this.saveToStorage();
  }

  subscribe(listener: () => void) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notifyListeners() {
    this.listeners.forEach(l => l());
  }
}

export const resultsStore = new ResultsStore();
// Auto-recover molecular properties from SMILES using backend RDKit
async function rehydrateCandidates(store: ResultsStore) {
  const results = store.getResults();
  const needsEnrichment: { resultId: string; smiles: string[] }[] = [];

  for (const r of results) {
    const missing = r.candidates.filter(
      (c) => c.smiles && c.smiles.length > 0 && ((c.mw == null || c.mw === 0) || c.affinity == null)
    );
    if (missing.length > 0) {
      needsEnrichment.push({
        resultId: r.id,
        smiles: missing.map((c) => c.smiles),
      });
    }
  }

  if (needsEnrichment.length === 0) return;

  // Collect all unique SMILES
  const allSmiles = [...new Set(needsEnrichment.flatMap((e) => e.smiles))];
  if (allSmiles.length === 0) return;

  console.log(`[RECOVERY] Enriching ${allSmiles.length} candidates with molecular properties...`);

  try {
    const res = await fetch('/api/molecular/properties', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ smiles: allSmiles }),
      signal: AbortSignal.timeout(30000),
    });
    if (!res.ok) {
      console.warn('[RECOVERY] Backend returned', res.status);
      return;
    }
    const data = await res.json();
    const propsMap: Record<string, any> = {};
    if (data.results && Array.isArray(data.results)) {
      for (const p of data.results) {
        if (p.valid && p.smiles) {
          propsMap[p.smiles] = p;
        }
      }
    }

    if (Object.keys(propsMap).length === 0) return;

    // Update stored results
    let updated = false;
    const currentResults = store.getResults();
    for (const r of currentResults) {
      for (const c of r.candidates) {
        const p = propsMap[c.smiles];
        if (p) {
          // Recover molecular properties if missing
          if (c.mw == null || c.mw === 0) {
            c.mw = p.mw;
            c.logp = p.logp;
            c.hbd = p.hbd;
            c.hba = p.hba;
            c.tpsa = p.tpsa;
            c.lipinski_pass = p.lipinski_pass;
            updated = true;
          }
          // Recover affinity estimate independently
          if (c.affinity == null && p.estimated_affinity_kcal_mol != null) {
            c.affinity = p.estimated_affinity_kcal_mol;
            updated = true;
          }
        }
      }
    }

    if (updated) {
      store['results'] = currentResults.map((r: PipelineResult) => ({
        ...r,
        timestamp: r.timestamp instanceof Date ? r.timestamp : new Date(r.timestamp),
      }));
      store.persistToStorage();
      store['notifyListeners']();
      console.log(`[RECOVERY] Successfully enriched ${Object.keys(propsMap).length} candidates`);
    }
  } catch (e) {
    console.warn('[RECOVERY] Failed to fetch properties:', e);
  }
}



// Sort options
type SortField = 'timestamp' | 'target' | 'affinity' | 'candidates';
type SortDirection = 'asc' | 'desc';

// Helper to count pipeline data sections present
const getPipelineBadges = (result: PipelineResult): { label: string; color: string }[] => {
  const badges: { label: string; color: string }[] = [];
  if (result.candidates.length > 0) badges.push({ label: 'Candidates', color: 'bg-molecular-500/20 text-molecular-400' });
  if (result.toxicology) badges.push({ label: 'Toxicology', color: 'bg-red-500/20 text-red-400' });
  if (result.pharmacology) badges.push({ label: 'Pharmacology', color: 'bg-blue-500/20 text-blue-400' });
  if (result.clinical_trial) badges.push({ label: 'Clinical Trial', color: 'bg-purple-500/20 text-purple-400' });
  if (result.admet) badges.push({ label: 'ADMET', color: 'bg-green-500/20 text-green-400' });
  if (result.alphagenomic_data) badges.push({ label: 'AlphaGenomics', color: 'bg-cyan-500/20 text-cyan-400' });
  if (result.complexa_binders) badges.push({ label: 'Complexa', color: 'bg-amber-500/20 text-amber-400' });
  if (result.images && result.images.length > 0) badges.push({ label: 'Images', color: 'bg-indigo-500/20 text-indigo-400' });
  return badges;
};

// Safety risk color helper
const riskColor = (risk?: string): string => {
  if (!risk) return 'text-gray-400';
  const lower = risk.toLowerCase();
  if (lower === 'low' || lower === 'negative' || lower === 'safe' || lower === 'minimal') return 'text-green-400';
  if (lower === 'moderate' || lower === 'medium' || lower === 'caution') return 'text-yellow-400';
  if (lower === 'high' || lower === 'positive' || lower === 'danger' || lower === 'critical') return 'text-red-400';
  return 'text-white';
};

const riskBadgeColor = (risk?: string): string => {
  if (!risk) return 'bg-gray-500/20 text-gray-400';
  const lower = risk.toLowerCase();
  if (lower === 'low' || lower === 'negative' || lower === 'safe' || lower === 'minimal') return 'bg-green-500/20 text-green-400';
  if (lower === 'moderate' || lower === 'medium' || lower === 'caution') return 'bg-yellow-500/20 text-yellow-400';
  if (lower === 'high' || lower === 'positive' || lower === 'danger' || lower === 'critical') return 'bg-red-500/20 text-red-400';
  return 'bg-gray-500/20 text-white';
};


// Safe number formatting - handles undefined, null, NaN, strings
const safeNum = (v: unknown, decimals = 2, fallback = 'N/A'): string => {
  if (v == null) return fallback;
  const n = typeof v === 'string' ? parseFloat(v) : Number(v);
  if (isNaN(n) || !isFinite(n)) return fallback;
  return n.toFixed(decimals);
};

const safeNumber = (v: unknown, fallback = 0): number => {
  if (v == null) return fallback;
  const n = typeof v === 'string' ? parseFloat(v) : Number(v);
  if (isNaN(n) || !isFinite(n)) return fallback;
  return n;
};

// Smart percent display - handles both 0-1 fractional and 0-100 percent inputs
// Values > 1 are treated as already-percent (e.g. 85 for 85%)
// Values <= 1 are treated as fractional (e.g. 0.85 -> 85%)
const asPercent = (v: unknown, decimals = 0): string => {
  const n = safeNumber(v);
  if (n === 0) return '0';
  const pct = n > 1 ? n : n * 100;
  return pct.toFixed(decimals);
};

// Safe ISO string for dates (prevents RangeError on Invalid Date)
const safeISOString = (d: Date): string => {
  try { return d.toISOString(); } catch { return new Date().toISOString(); }
};

const targetLabel = (target: unknown): string => {
  if (!target) return 'Unknown';
  if (typeof target === 'object') {
    const t = target as any;
    return String(t.name || t.target || t.target_name || t.gene || 'Unknown');
  }
  return String(target);
};

const ResultsPanel: React.FC = () => {
  const [results, setResults] = useState<PipelineResult[]>([]);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [sortField, setSortField] = useState<SortField>('timestamp');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  useEffect(() => {
    setResults(resultsStore.getResults());
    const unsubscribe = resultsStore.subscribe(() => {
      setResults(resultsStore.getResults());
    });
    // Auto-recover missing molecular properties from SMILES
    rehydrateCandidates(resultsStore);
    return () => { unsubscribe(); };
  }, []);

  const toggleExpand = (id: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedResults = [...results].sort((a, b) => {
    let comparison = 0;
    switch (sortField) {
      case 'timestamp':
        comparison = a.timestamp.getTime() - b.timestamp.getTime();
        break;
      case 'target':
        comparison = String((a.target as any)?.name || String(a.target || "")).localeCompare(String((b.target as any)?.name || String(b.target || "")));
        break;
      case 'affinity':
        const aAff = safeNumber(a.candidates.filter(c => c.affinity != null && !isNaN(Number(c.affinity))).sort((x, y) => safeNumber(x.affinity) - safeNumber(y.affinity))[0]?.affinity);
        const bAff = safeNumber(b.candidates.filter(c => c.affinity != null && !isNaN(Number(c.affinity))).sort((x, y) => safeNumber(x.affinity) - safeNumber(y.affinity))[0]?.affinity);
        comparison = aAff - bAff;
        break;
      case 'candidates':
        comparison = a.candidates.length - b.candidates.length;
        break;
    }
    return sortDirection === 'asc' ? comparison : -comparison;
  });

  const exportToCSV = (result: PipelineResult) => {
    const headers = ['ID', 'SMILES', 'MW', 'LogP', 'HBD', 'HBA', 'TPSA', 'Lipinski', 'Affinity (kcal/mol)'];
    const rows = result.candidates.map(c => [
      c.id,
      c.smiles,
      safeNum(c.mw, 2),
      safeNum(c.logp, 2),
      c.hbd,
      c.hba,
      safeNum(c.tpsa, 2),
      c.lipinski_pass === true ? 'PASS' : c.lipinski_pass === false ? 'FAIL' : 'N/A',
      safeNum(c.affinity, 2),
    ]);

    const csvLines: string[] = [
      '# BioQL Pipeline Results',
      '# Target: ' + targetLabel(result.target),
      '# PDB: ' + result.pdb_id,
      '# Date: ' + safeISOString(result.timestamp),
      '# Status: ' + result.status,
      '',
      headers.join(','),
      ...rows.map(r => r.join(',')),
    ];

    // Add toxicology data if present
    if (result.toxicology) {
      csvLines.push('', '# --- Toxicology ---');
      csvLines.push('Overall Safety,' + result.toxicology.overall_safety);
      if (result.toxicology.ld50_predicted) csvLines.push('LD50 (mg/kg),' + result.toxicology.ld50_predicted);
      if (result.toxicology.herg_risk) csvLines.push('hERG Risk,' + result.toxicology.herg_risk);
      if (result.toxicology.ames_mutagenicity) csvLines.push('AMES,' + result.toxicology.ames_mutagenicity);
      if (result.toxicology.hepatotoxicity_risk) csvLines.push('Hepatotoxicity,' + result.toxicology.hepatotoxicity_risk);
      if (result.toxicology.cardiotoxicity_risk) csvLines.push('Cardiotoxicity,' + result.toxicology.cardiotoxicity_risk);
      if (result.toxicology.nephrotoxicity_risk) csvLines.push('Nephrotoxicity,' + result.toxicology.nephrotoxicity_risk);
      if (result.toxicology.immunotoxicity_risk) csvLines.push('Immunotoxicity,' + result.toxicology.immunotoxicity_risk);
    }

    // Add pharmacology data if present
    if (result.pharmacology) {
      csvLines.push('', '# --- Pharmacology ---');
      if (result.pharmacology.bioavailability != null) csvLines.push('Bioavailability,' + asPercent(result.pharmacology.bioavailability, 1) + '%');
      if (result.pharmacology.half_life_hours != null) csvLines.push('Half-life (h),' + result.pharmacology.half_life_hours);
      if (result.pharmacology.volume_distribution != null) csvLines.push('Vd (L/kg),' + result.pharmacology.volume_distribution);
      if (result.pharmacology.clearance != null) csvLines.push('Clearance (mL/min),' + result.pharmacology.clearance);
      if (result.pharmacology.bbb_penetration) csvLines.push('BBB Penetration,' + result.pharmacology.bbb_penetration);
    }

    // Add clinical trial data if present
    if (result.clinical_trial) {
      csvLines.push('', '# --- Clinical Trial Simulation ---');
      if (result.clinical_trial.phase1_success_probability != null) csvLines.push('Phase I Success,' + asPercent(result.clinical_trial.phase1_success_probability, 1) + '%');
      if (result.clinical_trial.phase2_success_probability != null) csvLines.push('Phase II Success,' + asPercent(result.clinical_trial.phase2_success_probability, 1) + '%');
      if (result.clinical_trial.phase3_success_probability != null) csvLines.push('Phase III Success,' + asPercent(result.clinical_trial.phase3_success_probability, 1) + '%');
      if (result.clinical_trial.overall_approval_probability != null) csvLines.push('Overall Approval,' + asPercent(result.clinical_trial.overall_approval_probability, 1) + '%');
    }

    const csvContent = csvLines.join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'BioQL_Results_' + targetLabel(result.target).replace(/\s+/g, '_') + '_' + safeISOString(result.timestamp).split('T')[0] + '.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const exportAllToCSV = () => {
    if (results.length === 0) return;

    const allRows: string[] = [
      '# BioQL Pipeline Results - All Sessions',
      '# Exported: ' + new Date().toISOString(),
      '',
    ];

    results.forEach(result => {
      allRows.push('# --- ' + result.target + ' (' + result.pdb_id + ') ---');
      allRows.push('# Date: ' + safeISOString(result.timestamp));
      allRows.push('Target,PDB,ID,SMILES,MW,LogP,HBD,HBA,TPSA,Lipinski,Affinity');
      result.candidates.forEach(c => {
        allRows.push([
          result.target,
          result.pdb_id,
          c.id,
          '"' + c.smiles + '"',
          safeNum(c.mw, 2),
          safeNum(c.logp, 2),
          c.hbd,
          c.hba,
          safeNum(c.tpsa, 2),
          c.lipinski_pass === true ? 'PASS' : c.lipinski_pass === false ? 'FAIL' : 'N/A',
          safeNum(c.affinity, 2),
        ].join(','));
      });
      allRows.push('');
    });

    const blob = new Blob([allRows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'BioQL_All_Results_' + new Date().toISOString().split('T')[0] + '.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getBestAffinity = (candidates: DrugCandidate[]): string => {
    const withAffinity = candidates.filter(c => c.affinity != null && !isNaN(Number(c.affinity)));
    if (withAffinity.length === 0) return 'N/A';
    const best = Math.min(...withAffinity.map(c => Number(c.affinity)));
    if (isNaN(best) || !isFinite(best)) return 'N/A';
    return best.toFixed(2) + ' kcal/mol';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'partial':
        return <Clock className="w-4 h-4 text-yellow-400" />;
      default:
        return <Beaker className="w-4 h-4 text-gray-400" />;
    }
  };

  if (results.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-400 p-8">
        <Table className="w-16 h-16 mb-4 opacity-50" />
        <h3 className="text-lg font-semibold mb-2">No Results Yet</h3>
        <p className="text-sm text-center max-w-md">
          Run a drug discovery pipeline from the Chat or Undruggable panel.
          Results will be saved here automatically.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-dark-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-dark-600">
        <div className="flex items-center gap-2">
          <Table className="w-5 h-5 text-molecular-400" />
          <h2 className="text-lg font-semibold text-white">Pipeline Results</h2>
          <span className="text-sm text-gray-400">({results.length} sessions)</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportAllToCSV}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-molecular-500/20 text-molecular-400 rounded hover:bg-molecular-500/30 transition"
          >
            <Download className="w-4 h-4" />
            Export All
          </button>
          <button
            onClick={() => {
              if (confirm('Clear all results? This cannot be undone.')) {
                resultsStore.clearAll();
              }
            }}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition"
          >
            <Trash2 className="w-4 h-4" />
            Clear
          </button>
        </div>
      </div>

      {/* Sort controls */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-dark-700 text-sm">
        <span className="text-gray-400">Sort by:</span>
        {(['timestamp', 'target', 'affinity', 'candidates'] as SortField[]).map(field => (
          <button
            key={field}
            onClick={() => handleSort(field)}
            className={'flex items-center gap-1 px-2 py-1 rounded ' + (sortField === field ? 'bg-molecular-500/20 text-molecular-400' : 'text-gray-400 hover:text-white')}
          >
            {field.charAt(0).toUpperCase() + field.slice(1)}
            {sortField === field && (
              <ArrowUpDown className={'w-3 h-3 ' + (sortDirection === 'desc' ? 'rotate-180' : '')} />
            )}
          </button>
        ))}
      </div>

      {/* Results list */}
      <div className="flex-1 overflow-y-auto">
        {sortedResults.map(result => (
          <div key={result.id} className="border-b border-dark-700">
            {/* Result header row */}
            <div
              className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-dark-800 transition"
              onClick={() => toggleExpand(result.id)}
            >
              {expandedRows.has(result.id) ? (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-400" />
              )}

              {getStatusIcon(result.status)}

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-white truncate">{typeof result.target === "object" ? ((result.target as any)?.name || "Unknown") : result.target}</span>
                  <span className="text-xs text-gray-500 bg-dark-700 px-2 py-0.5 rounded">{result.pdb_id}</span>
                </div>
                <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-2">
                  <span>{formatDate(result.timestamp)} &bull; {result.backend}</span>
                  {/* Pipeline stage badges */}
                  {getPipelineBadges(result).map((badge, i) => (
                    <span key={i} className={'text-[10px] px-1.5 py-0.5 rounded ' + badge.color}>
                      {badge.label}
                    </span>
                  ))}
                </div>
              </div>

              <div className="text-right">
                <div className="text-sm text-molecular-400">{result.candidates.length} candidates</div>
                <div className="text-xs text-gray-500">Best: {getBestAffinity(result.candidates)}</div>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  exportToCSV(result);
                }}
                className="p-2 text-gray-400 hover:text-molecular-400 transition"
                title="Export to CSV"
              >
                <Download className="w-4 h-4" />
              </button>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  resultsStore.deleteResult(result.id);
                }}
                className="p-2 text-gray-400 hover:text-red-400 transition"
                title="Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            {/* Expanded detail section */}
            {expandedRows.has(result.id) && (
              <div className="bg-dark-800 px-4 py-3">
                {/* Candidates table */}
                {result.candidates.length > 0 && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-400 border-b border-dark-600">
                          <th className="pb-2 pr-4">ID</th>
                          <th className="pb-2 pr-4">SMILES</th>
                          <th className="pb-2 pr-4 text-right">MW</th>
                          <th className="pb-2 pr-4 text-right">LogP</th>
                          <th className="pb-2 pr-4 text-right">HBD</th>
                          <th className="pb-2 pr-4 text-right">HBA</th>
                          <th className="pb-2 pr-4 text-center">Lipinski</th>
                          <th className="pb-2 text-right">Affinity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.candidates
                          .slice()
                          .sort((a, b) => safeNumber(a.affinity) - safeNumber(b.affinity))
                          .map((candidate, idx) => (
                            <tr
                              key={candidate.id}
                              className={'border-b border-dark-700 ' + (idx === 0 && candidate.affinity != null && !isNaN(Number(candidate.affinity)) ? 'bg-molecular-500/10' : '')}
                            >
                              <td className="py-2 pr-4 font-mono text-xs text-gray-300">{candidate.id}</td>
                              <td className="py-2 pr-4 font-mono text-xs text-gray-300" title={candidate.smiles}>
                                <div className="max-w-sm overflow-x-auto whitespace-nowrap scrollbar-thin">{candidate.smiles}</div>
                              </td>
                              <td className="py-2 pr-4 text-right text-gray-300">{safeNum(candidate.mw, 1)}</td>
                              <td className="py-2 pr-4 text-right text-gray-300">{safeNum(candidate.logp, 2)}</td>
                              <td className="py-2 pr-4 text-right text-gray-300">{candidate.hbd != null ? candidate.hbd : <span className="text-gray-600">-</span>}</td>
                              <td className="py-2 pr-4 text-right text-gray-300">{candidate.hba != null ? candidate.hba : <span className="text-gray-600">-</span>}</td>
                              <td className="py-2 pr-4 text-center">
                                {candidate.lipinski_pass === true ? (
                                  <span className="text-green-400">PASS</span>
                                ) : candidate.lipinski_pass === false ? (
                                  <span className="text-red-400">FAIL</span>
                                ) : (
                                  <span className="text-gray-500">-</span>
                                )}
                              </td>
                              <td className={'py-2 text-right font-medium ' + (candidate.affinity != null && !isNaN(Number(candidate.affinity)) && Number(candidate.affinity) < -7 ? 'text-green-400' : candidate.affinity != null && !isNaN(Number(candidate.affinity)) ? 'text-yellow-400' : 'text-gray-500')}>
                                {safeNum(candidate.affinity, 2)}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Toxicology Section */}
                {result.toxicology && (() => {
                  const td: any = result.toxicology;
                  const ames = td.ames_mutagenicity || td.genotoxicity?.ames?.result || td.genotoxicity?.ames_mutagenicity?.result || '';
                  const hepato = td.hepatotoxicity_risk || td.organ_toxicity?.hepatotoxicity?.risk || td.organ_specific?.hepatotoxicity?.risk || '';
                  const cardio = td.cardiotoxicity_risk || td.organ_toxicity?.cardiotoxicity?.risk || td.organ_specific?.cardiotoxicity?.risk || '';
                  const nephro = td.nephrotoxicity_risk || td.organ_toxicity?.nephrotoxicity?.risk || td.organ_specific?.nephrotoxicity?.risk || '';
                  const immuno = td.immunotoxicity_risk || td.immunogenicity?.risk || '';
                  return (
                  <div className="mt-4 p-3 bg-red-500/5 border border-red-500/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <Shield className="w-4 h-4 text-red-400" />
                      <h4 className="text-sm font-semibold text-red-400">Toxicology Study</h4>
                      <span className={'ml-auto text-xs px-2 py-0.5 rounded ' + riskBadgeColor(td.overall_safety)}>
                        {td.overall_safety}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                      {td.ld50_predicted != null && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">LD50 (predicted)</div>
                          <div className="text-white font-medium">{td.ld50_predicted} mg/kg</div>
                        </div>
                      )}
                      {td.herg_risk && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">hERG Risk</div>
                          <div className={riskColor(td.herg_risk) + ' font-medium'}>{td.herg_risk}</div>
                        </div>
                      )}
                      {ames && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">AMES Mutagenicity</div>
                          <div className={riskColor(ames) + ' font-medium'}>{ames}</div>
                        </div>
                      )}
                      {hepato && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">Hepatotoxicity</div>
                          <div className={riskColor(hepato) + ' font-medium'}>{hepato}</div>
                        </div>
                      )}
                      {cardio && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">Cardiotoxicity</div>
                          <div className={riskColor(cardio) + ' font-medium'}>{cardio}</div>
                        </div>
                      )}
                      {nephro && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">Nephrotoxicity</div>
                          <div className={riskColor(nephro) + ' font-medium'}>{nephro}</div>
                        </div>
                      )}
                      {immuno && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">Immunotoxicity</div>
                          <div className={riskColor(immuno) + ' font-medium'}>{immuno}</div>
                        </div>
                      )}
                    </div>
                    {td.quantum_algorithms_used && td.quantum_algorithms_used.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {td.quantum_algorithms_used.map((alg: string, i: number) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 bg-red-500/10 text-red-400/70 rounded">{alg}</span>
                        ))}
                      </div>
                    )}
                    {td.ibm_job_ids && td.ibm_job_ids.length > 0 && (
                      <div className="mt-2 text-xs text-gray-500">
                        <div className="flex items-center justify-between flex-wrap gap-1">
                          <span>IBM Quantum: {td.ibm_job_ids.length} job{td.ibm_job_ids.length !== 1 ? 's' : ''} executed</span>
                          <ProvenanceBadge provenance={extractProvenance({ ibm_job_ids: td.ibm_job_ids })!} />
                        </div>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {td.ibm_job_ids.map((jobId: string, i: number) => (
                            <a key={i} href={`https://quantum.ibm.com/jobs/${jobId}`} target="_blank" rel="noopener noreferrer" className="text-[10px] px-1.5 py-0.5 bg-quantum-500/10 text-quantum-400 hover:text-quantum-300 hover:bg-quantum-500/20 rounded font-mono transition-colors">{jobId}</a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  ); })()}

                {/* Pharmacology Section */}
                {result.pharmacology && (
                  <div className="mt-4 p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <Pill className="w-4 h-4 text-blue-400" />
                      <h4 className="text-sm font-semibold text-blue-400">Pharmacology Study</h4>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                      {result.pharmacology.bioavailability != null && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">Bioavailability (F%)</div>
                          <div className="text-white font-medium">{asPercent(result.pharmacology.bioavailability, 1)}%</div>
                        </div>
                      )}
                      {result.pharmacology.half_life_hours != null && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">Half-life</div>
                          <div className="text-white font-medium">{safeNum(result.pharmacology.half_life_hours, 1)} hours</div>
                        </div>
                      )}
                      {result.pharmacology.volume_distribution != null && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">Volume of Distribution</div>
                          <div className="text-white font-medium">{safeNum(result.pharmacology.volume_distribution, 2)} L/kg</div>
                        </div>
                      )}
                      {result.pharmacology.clearance != null && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">Clearance</div>
                          <div className="text-white font-medium">{safeNum(result.pharmacology.clearance, 1)} mL/min</div>
                        </div>
                      )}
                      {result.pharmacology.bbb_penetration && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">BBB Penetration</div>
                          <div className={String(result.pharmacology.bbb_penetration).toLowerCase() === 'yes' ? 'text-green-400 font-medium' : 'text-yellow-400 font-medium'}>
                            {result.pharmacology.bbb_penetration}
                          </div>
                        </div>
                      )}
                      {result.pharmacology.target_engagement != null && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">Target Engagement</div>
                          <div className="text-white font-medium">{asPercent(result.pharmacology.target_engagement, 1)}%</div>
                        </div>
                      )}
                      {result.pharmacology.dose_response_ec50 != null && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">EC50</div>
                          <div className="text-white font-medium">{safeNum(result.pharmacology.dose_response_ec50, 2)} nM</div>
                        </div>
                      )}
                    </div>
                    {result.pharmacology.mechanism_of_action && (
                      <div className="mt-2 text-xs bg-dark-700 rounded p-2">
                        <span className="text-gray-500">Mechanism of Action: </span>
                        <span className="text-white">{result.pharmacology.mechanism_of_action}</span>
                      </div>
                    )}
                    {result.pharmacology.quantum_algorithms_used && result.pharmacology.quantum_algorithms_used.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {result.pharmacology.quantum_algorithms_used.map((alg, i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 bg-blue-500/10 text-blue-400/70 rounded">{alg}</span>
                        ))}
                      </div>
                    )}
                    {result.pharmacology.ibm_job_ids && result.pharmacology.ibm_job_ids.length > 0 && (
                      <div className="mt-2 text-xs text-gray-500">
                        <div className="flex items-center justify-between flex-wrap gap-1">
                          <span>IBM Quantum: {result.pharmacology.ibm_job_ids.length} job{result.pharmacology.ibm_job_ids.length !== 1 ? 's' : ''} executed</span>
                          <ProvenanceBadge provenance={extractProvenance({ ibm_job_ids: result.pharmacology.ibm_job_ids })!} />
                        </div>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {result.pharmacology.ibm_job_ids.map((jobId, i) => (
                            <a key={i} href={`https://quantum.ibm.com/jobs/${jobId}`} target="_blank" rel="noopener noreferrer" className="text-[10px] px-1.5 py-0.5 bg-quantum-500/10 text-quantum-400 hover:text-quantum-300 hover:bg-quantum-500/20 rounded font-mono transition-colors">{jobId}</a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Clinical Trial Simulation Section */}
                {result.clinical_trial && (
                  <div className="mt-4 p-3 bg-purple-500/5 border border-purple-500/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <Activity className="w-4 h-4 text-purple-400" />
                      <h4 className="text-sm font-semibold text-purple-400">Clinical Trial Simulation</h4>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                      {result.clinical_trial.phase1_success_probability != null && (
                        <div className="text-center p-3 bg-dark-700 rounded-lg">
                          <div className="text-gray-500 mb-1">Phase I</div>
                          <div className="text-2xl font-bold text-white">{asPercent(result.clinical_trial.phase1_success_probability)}%</div>
                          <div className="text-gray-600 text-[10px] mt-0.5">Safety &amp; Tolerability</div>
                        </div>
                      )}
                      {result.clinical_trial.phase2_success_probability != null && (
                        <div className="text-center p-3 bg-dark-700 rounded-lg">
                          <div className="text-gray-500 mb-1">Phase II</div>
                          <div className="text-2xl font-bold text-white">{asPercent(result.clinical_trial.phase2_success_probability)}%</div>
                          <div className="text-gray-600 text-[10px] mt-0.5">Efficacy Signals</div>
                        </div>
                      )}
                      {result.clinical_trial.phase3_success_probability != null && (
                        <div className="text-center p-3 bg-dark-700 rounded-lg">
                          <div className="text-gray-500 mb-1">Phase III</div>
                          <div className="text-2xl font-bold text-white">{asPercent(result.clinical_trial.phase3_success_probability)}%</div>
                          <div className="text-gray-600 text-[10px] mt-0.5">Confirmatory</div>
                        </div>
                      )}
                      {result.clinical_trial.overall_approval_probability != null && (
                        <div className="text-center p-3 bg-purple-500/20 rounded-lg border border-purple-500/30">
                          <div className="text-purple-400 mb-1 font-medium">Approval</div>
                          <div className="text-2xl font-bold text-purple-300">{asPercent(result.clinical_trial.overall_approval_probability)}%</div>
                          <div className="text-purple-500/60 text-[10px] mt-0.5">Overall Probability</div>
                        </div>
                      )}
                    </div>
                    <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                      {result.clinical_trial.estimated_timeline_months != null && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">Estimated Timeline</div>
                          <div className="text-white font-medium">{result.clinical_trial.estimated_timeline_months} months</div>
                        </div>
                      )}
                      {result.clinical_trial.recommended_dose_mg != null && (() => {
                        const rd: any = result.clinical_trial.recommended_dose_mg;
                        const val = (typeof rd === 'object' && rd !== null) ? (rd.value ?? rd.recommended_dose ?? rd.mtd ?? rd.dose) : rd;
                        return val != null ? (
                          <div className="bg-dark-700 rounded p-2">
                            <div className="text-gray-500 mb-0.5">Recommended Dose</div>
                            <div className="text-white font-medium">{val} mg</div>
                          </div>
                        ) : null;
                      })()}
                      {result.clinical_trial.patient_population && (
                        <div className="bg-dark-700 rounded p-2">
                          <div className="text-gray-500 mb-0.5">Patient Population</div>
                          <div className="text-white font-medium">{result.clinical_trial.patient_population}</div>
                        </div>
                      )}
                    </div>
                    {result.clinical_trial.quantum_algorithms_used && result.clinical_trial.quantum_algorithms_used.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {result.clinical_trial.quantum_algorithms_used.map((alg, i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 bg-purple-500/10 text-purple-400/70 rounded">{alg}</span>
                        ))}
                      </div>
                    )}
                    {result.clinical_trial.ibm_job_ids && result.clinical_trial.ibm_job_ids.length > 0 && (
                      <div className="mt-2 text-xs text-gray-500">
                        <div className="flex items-center justify-between flex-wrap gap-1">
                          <span>IBM Quantum: {result.clinical_trial.ibm_job_ids.length} job{result.clinical_trial.ibm_job_ids.length !== 1 ? 's' : ''} executed</span>
                          <ProvenanceBadge provenance={extractProvenance({ ibm_job_ids: result.clinical_trial.ibm_job_ids })!} />
                        </div>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {result.clinical_trial.ibm_job_ids.map((jobId, i) => (
                            <a key={i} href={`https://quantum.ibm.com/jobs/${jobId}`} target="_blank" rel="noopener noreferrer" className="text-[10px] px-1.5 py-0.5 bg-quantum-500/10 text-quantum-400 hover:text-quantum-300 hover:bg-quantum-500/20 rounded font-mono transition-colors">{jobId}</a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* ADMET Section */}
                {result.admet && (
                  <div className="mt-4 p-3 bg-green-500/5 border border-green-500/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <FlaskConical className="w-4 h-4 text-green-400" />
                      <h4 className="text-sm font-semibold text-green-400">
                        ADMET Profile
                        {result.admet.parameters_count ? ' (' + result.admet.parameters_count + ' parameters)' : ''}
                      </h4>
                    </div>
                    <div className="grid grid-cols-5 gap-2 text-xs">
                      {(['absorption', 'distribution', 'metabolism', 'excretion', 'toxicity'] as const).map(category => {
                        const categoryData = result.admet?.[category] as Record<string, any> | undefined;
                        const paramCount = categoryData ? Object.keys(categoryData).length : 0;
                        const categoryLabels: Record<string, string> = {
                          absorption: 'A',
                          distribution: 'D',
                          metabolism: 'M',
                          excretion: 'E',
                          toxicity: 'T',
                        };
                        const categoryColors: Record<string, string> = {
                          absorption: 'text-green-400',
                          distribution: 'text-blue-400',
                          metabolism: 'text-yellow-400',
                          excretion: 'text-orange-400',
                          toxicity: 'text-red-400',
                        };
                        return (
                          <div key={category} className="text-center p-2 bg-dark-700 rounded-lg">
                            <div className={categoryColors[category] + ' text-lg font-bold mb-0.5'}>{categoryLabels[category]}</div>
                            <div className="text-white text-sm font-medium">{paramCount}</div>
                            <div className="text-gray-600 text-[10px] capitalize">{category}</div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Expandable detail for each ADMET category */}
                    {(['absorption', 'distribution', 'metabolism', 'excretion', 'toxicity'] as const).map(category => {
                      const categoryData = result.admet?.[category] as Record<string, any> | undefined;
                      if (!categoryData || Object.keys(categoryData).length === 0) return null;
                      return (
                        <div key={category} className="mt-2">
                          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">{category}</div>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-1">
                            {Object.entries(categoryData).slice(0, 9).map(([key, value]) => (
                              <div key={key} className="text-[11px] bg-dark-700 rounded px-2 py-1">
                                <span className="text-gray-500">{key.replace(/_/g, ' ')}: </span>
                                <span className="text-white">{typeof value === 'number' ? safeNum(value, 3) : String(value ?? 'N/A')}</span>
                              </div>
                            ))}
                            {Object.keys(categoryData).length > 9 && (
                              <div className="text-[11px] bg-dark-700 rounded px-2 py-1 text-gray-500 italic">
                                +{Object.keys(categoryData).length - 9} more parameters
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}

                    {result.admet.quantum_algorithms_used && result.admet.quantum_algorithms_used.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {result.admet.quantum_algorithms_used.map((alg, i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 bg-green-500/10 text-green-400/70 rounded">{alg}</span>
                        ))}
                      </div>
                    )}
                    {result.admet.ibm_job_ids && result.admet.ibm_job_ids.length > 0 && (
                      <div className="mt-2 text-xs text-gray-500">
                        <div className="flex items-center justify-between flex-wrap gap-1">
                          <span>IBM Quantum: {result.admet.ibm_job_ids.length} job{result.admet.ibm_job_ids.length !== 1 ? 's' : ''} executed</span>
                          <ProvenanceBadge provenance={extractProvenance({ ibm_job_ids: result.admet.ibm_job_ids })!} />
                        </div>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {result.admet.ibm_job_ids.map((jobId, i) => (
                            <a key={i} href={`https://quantum.ibm.com/jobs/${jobId}`} target="_blank" rel="noopener noreferrer" className="text-[10px] px-1.5 py-0.5 bg-quantum-500/10 text-quantum-400 hover:text-quantum-300 hover:bg-quantum-500/20 rounded font-mono transition-colors">{jobId}</a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}


                {/* Molecular Visualizations Section */}
                {result.images && result.images.length > 0 && (
                  <div className="mt-4 p-3 bg-indigo-500/5 border border-indigo-500/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <Image className="w-4 h-4 text-indigo-400" />
                      <h4 className="text-sm font-semibold text-indigo-400">Molecular Visualizations</h4>
                      <span className="ml-auto text-xs px-2 py-0.5 bg-indigo-500/20 text-indigo-300 rounded">
                        {result.images.length} image{result.images.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {result.images.map((img, idx) => (
                        <div key={idx} className="bg-slate-800/50 border border-slate-700/50 rounded-lg overflow-hidden">
                          <div className="px-3 py-2 border-b border-slate-700/50">
                            <span className="text-xs font-medium text-gray-300">{img.title || ('Image ' + (idx + 1))}</span>
                            {img.type && (
                              <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-indigo-500/10 text-indigo-400/70 rounded">{img.type}</span>
                            )}
                          </div>
                          <div className="p-2 flex items-center justify-center bg-slate-900/50">
                            <img
                              src={img.image}
                              alt={img.title || ('Visualization ' + (idx + 1))}
                              style={{ maxWidth: '100%', height: 'auto' }}
                              className="rounded"
                              loading="lazy"
                            />
                          </div>
                          {(img.width > 0 || img.height > 0) && (
                            <div className="px-3 py-1 text-[10px] text-gray-600 text-right">
                              {img.width}&times;{img.height}px
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Protenix Structure Prediction */}
                {result.protenix_structure && (
                  <ProtenixConfidencePanel
                    data={(() => {
                      const d = result.protenix_structure;
                      // Normalize flat enrichment format {iptm, ptm, plddt} to expected {confidence: {...}}
                      if (d && d.iptm !== undefined && !d.confidence) {
                        return { confidence: { iptm: d.iptm, ptm: d.ptm, plddt: d.plddt, ranking_score: d.ranking_score }, ...d };
                      }
                      // Ensure ranking_score propagates into confidence from all possible locations
                      if (d?.confidence && d.confidence.ranking_score == null) {
                        const rs = d.ranking_score
                          ?? d.all_samples?.[0]?.ranking_score
                          ?? d.confidence?.ranking_score;
                        if (rs != null) d.confidence.ranking_score = rs;
                      }
                      return d;
                    })()}
                    title="Protenix Structure Prediction"
                  />
                )}

                {/* AlphaGenomics Gene Expression Section */}
                {(() => {
                  const agData = result.alphagenomic_data
                    || (result as any).alphagenomic
                    || (result as any).stages?.alphagenomic
                    || (result as any).stages?.alphagenomic_data;
                  if (!agData) return null;
                  const predictions = agData.predictions || agData.gene_expression || agData.results || [];
                  const variants = agData.variant_effects || agData.variants || [];
                  const targetGene = agData.gene || agData.target_gene || result.target || '';
                  return (
                    <div className="mt-4 p-3 bg-cyan-500/5 border border-cyan-500/20 rounded-lg">
                      <div className="flex items-center gap-2 mb-3">
                        <Dna className="w-4 h-4 text-cyan-400" />
                        <h4 className="text-sm font-semibold text-cyan-400">AlphaGenomics Gene Expression</h4>
                        {targetGene && (
                          <span className="ml-auto text-xs px-2 py-0.5 bg-cyan-500/20 text-cyan-300 rounded">
                            {targetGene}
                          </span>
                        )}
                      </div>

                      {/* Gene Expression Predictions */}
                      {Array.isArray(predictions) && predictions.length > 0 && (
                        <div className="mb-3">
                          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Expression Predictions</div>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                            {predictions.slice(0, 9).map((pred: any, i: number) => (
                              <div key={i} className="bg-dark-700 rounded p-2">
                                <div className="text-gray-500 mb-0.5">{pred.tissue || pred.cell_type || pred.sample || ('Tissue ' + (i + 1))}</div>
                                <div className="flex items-center justify-between">
                                  <span className="text-white font-medium">
                                    {pred.expression_level != null ? safeNum(pred.expression_level, 2)
                                      : pred.expression != null ? safeNum(pred.expression, 2)
                                      : pred.score != null ? safeNum(pred.score, 2)
                                      : pred.value != null ? safeNum(pred.value, 2) : 'N/A'}
                                  </span>
                                  {(pred.confidence != null || pred.confidence_score != null) && (
                                    <span className={'text-[10px] px-1.5 py-0.5 rounded ' + (
                                      safeNumber(pred.confidence || pred.confidence_score) > 0.8
                                        ? 'bg-green-500/20 text-green-400'
                                        : safeNumber(pred.confidence || pred.confidence_score) > 0.5
                                        ? 'bg-yellow-500/20 text-yellow-400'
                                        : 'bg-red-500/20 text-red-400'
                                    )}>
                                      {asPercent(pred.confidence || pred.confidence_score)}% conf
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                            {predictions.length > 9 && (
                              <div className="bg-dark-700 rounded p-2 text-gray-500 italic flex items-center justify-center">
                                +{predictions.length - 9} more tissues
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Non-array predictions (object format) */}
                      {!Array.isArray(predictions) && typeof predictions === 'object' && Object.keys(predictions).length > 0 && (
                        <div className="mb-3">
                          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Expression Data</div>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                            {Object.entries(predictions).slice(0, 9).map(([key, val]: [string, any]) => (
                              <div key={key} className="bg-dark-700 rounded p-2">
                                <div className="text-gray-500 mb-0.5">{key.replace(/_/g, ' ')}</div>
                                <div className="text-white font-medium">
                                  {typeof val === 'number' ? safeNum(val, 3) : String(val ?? 'N/A')}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Variant Effects */}
                      {Array.isArray(variants) && variants.length > 0 && (
                        <div>
                          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Variant Effects</div>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                            {variants.slice(0, 6).map((v: any, i: number) => (
                              <div key={i} className="bg-dark-700 rounded p-2">
                                <div className="text-gray-500 mb-0.5 font-mono">{v.variant || v.mutation || v.rsid || ('Variant ' + (i + 1))}</div>
                                <div className={'font-medium ' + (
                                  (v.impact || v.effect || '').toLowerCase() === 'high' ? 'text-red-400'
                                  : (v.impact || v.effect || '').toLowerCase() === 'moderate' ? 'text-yellow-400'
                                  : 'text-green-400'
                                )}>
                                  {v.impact || v.effect || v.pathogenicity || 'Unknown'}
                                </div>
                                {v.score != null && (
                                  <div className="text-gray-500 text-[10px]">Score: {safeNum(v.score, 3)}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Summary fields */}
                      {(agData.expression_summary || agData.druggability_score != null || agData.tissue_specificity) && (
                        <div className="mt-2 grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                          {agData.druggability_score != null && (
                            <div className="bg-dark-700 rounded p-2">
                              <div className="text-gray-500 mb-0.5">Druggability Score</div>
                              <div className="text-cyan-400 font-medium">{safeNum(agData.druggability_score, 2)}</div>
                            </div>
                          )}
                          {agData.tissue_specificity && (
                            <div className="bg-dark-700 rounded p-2">
                              <div className="text-gray-500 mb-0.5">Tissue Specificity</div>
                              <div className="text-white font-medium">{String(agData.tissue_specificity)}</div>
                            </div>
                          )}
                          {agData.expression_summary && (
                            <div className="bg-dark-700 rounded p-2">
                              <div className="text-gray-500 mb-0.5">Expression Summary</div>
                              <div className="text-white font-medium">{String(agData.expression_summary)}</div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Proteina-Complexa Binder Design Section */}
                {(() => {
                  const cxData = result.complexa_binders
                    || (result as any).complexa
                    || (result as any).stages?.complexa
                    || (result as any).stages?.complexa_binders;
                  if (!cxData) return null;
                  const binders = cxData.binders || cxData.designs || cxData.results || (Array.isArray(cxData) ? cxData : []);
                  const pipeline = cxData.pipeline || cxData.design_pipeline || '';
                  const targetPdb = cxData.target_pdb_id || cxData.target_pdb || '';
                  const numDesigns = binders.length || cxData.num_designs || cxData.total_designs || 0;

                  // Find top binder by total_reward
                  const topBinder = Array.isArray(binders) && binders.length > 0
                    ? binders.reduce((best: any, b: any) => {
                        const bReward = safeNumber(b.total_reward || b.reward || b.scores?.total_reward);
                        const bestReward = safeNumber(best?.total_reward || best?.reward || best?.scores?.total_reward, -999);
                        return bReward > bestReward ? b : best;
                      }, binders[0])
                    : null;

                  return (
                    <div className="mt-4 p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
                      <div className="flex items-center gap-2 mb-3">
                        <Microscope className="w-4 h-4 text-amber-400" />
                        <h4 className="text-sm font-semibold text-amber-400">Complexa Binder Design</h4>
                        <div className="ml-auto flex items-center gap-2">
                          {pipeline && (
                            <span className="text-xs px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded capitalize">
                              {String(pipeline).replace(/_/g, ' ')}
                            </span>
                          )}
                          {numDesigns > 0 && (
                            <span className="text-xs px-2 py-0.5 bg-dark-700 text-gray-300 rounded">
                              {numDesigns} design{numDesigns !== 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Target info */}
                      {targetPdb && (
                        <div className="mb-2 text-xs text-gray-500">
                          Target PDB: <span className="text-white font-mono">{targetPdb}</span>
                          {cxData.target_chain && <span className="ml-2">Chain: <span className="text-white">{cxData.target_chain}</span></span>}
                        </div>
                      )}

                      {/* Top Binder Highlight */}
                      {topBinder && (
                        <div className="mb-3 p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                          <div className="text-[10px] text-amber-400 uppercase tracking-wider mb-1.5 font-semibold">Top Binder</div>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                            {(topBinder.af2folding_i_pae != null || topBinder.ipae != null || topBinder.i_pae != null) && (
                              <div className="bg-dark-700 rounded p-2 text-center">
                                {/* iPAE is an error in Angstroms, so the 10/20 cutoffs
                                    below are Angstrom thresholds. An ipTM (0-1,
                                    higher better) placed here would pass every
                                    threshold silently, which it did. */}
                                <div className="text-gray-500 mb-0.5">iPAE (Å)</div>
                                <div className={'text-lg font-bold ' + (
                                  safeNumber(topBinder.af2folding_i_pae || topBinder.ipae || topBinder.i_pae || topBinder.scores?.ipAE) < 10
                                    ? 'text-green-400'
                                    : safeNumber(topBinder.af2folding_i_pae || topBinder.ipae || topBinder.i_pae || topBinder.scores?.ipAE) < 20
                                    ? 'text-yellow-400'
                                    : 'text-red-400'
                                )}>
                                  {safeNum(topBinder.af2folding_i_pae || topBinder.ipae || topBinder.i_pae || topBinder.scores?.ipAE, 1)}
                                </div>
                                <div className="text-gray-600 text-[10px]">Lower = better</div>
                              </div>
                            )}
                            {(topBinder.af2folding_plddt != null || topBinder.plddt != null) && (
                              <div className="bg-dark-700 rounded p-2 text-center">
                                <div className="text-gray-500 mb-0.5">pLDDT</div>
                                <div className={'text-lg font-bold ' + (
                                  safeNumber(topBinder.af2folding_plddt || topBinder.plddt || topBinder.scores?.pLDDT) > 80
                                    ? 'text-green-400'
                                    : safeNumber(topBinder.af2folding_plddt || topBinder.plddt || topBinder.scores?.pLDDT) > 60
                                    ? 'text-yellow-400'
                                    : 'text-red-400'
                                )}>
                                  {safeNum(topBinder.af2folding_plddt || topBinder.plddt || topBinder.scores?.pLDDT, 1)}
                                </div>
                                <div className="text-gray-600 text-[10px]">Higher = better</div>
                              </div>
                            )}
                            {(topBinder.af2folding_rmsd != null || topBinder.rmsd != null) && (
                              <div className="bg-dark-700 rounded p-2 text-center">
                                <div className="text-gray-500 mb-0.5">RMSD</div>
                                <div className="text-lg font-bold text-white">
                                  {safeNum(topBinder.af2folding_rmsd || topBinder.rmsd || topBinder.scores?.RMSD, 2)}
                                </div>
                                <div className="text-gray-600 text-[10px]">Angstroms</div>
                              </div>
                            )}
                            {(topBinder.total_reward != null || topBinder.reward != null) && (
                              <div className="bg-amber-500/20 rounded p-2 text-center border border-amber-500/30">
                                <div className="text-amber-400 mb-0.5 font-medium">Reward</div>
                                <div className="text-lg font-bold text-amber-300">
                                  {safeNum(topBinder.total_reward || topBinder.reward || topBinder.scores?.total_reward, 3)}
                                </div>
                                <div className="text-amber-500/60 text-[10px]">Higher = better</div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* All Binders Table */}
                      {Array.isArray(binders) && binders.length > 1 && (
                        <div>
                          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">All Designs</div>
                          <div className="overflow-x-auto">
                            <table className="w-full text-xs">
                              <thead>
                                <tr className="text-left text-gray-500 border-b border-dark-600">
                                  <th className="pb-1.5 pr-3">#</th>
                                  <th className="pb-1.5 pr-3 text-right">iPAE</th>
                                  <th className="pb-1.5 pr-3 text-right">pLDDT</th>
                                  <th className="pb-1.5 pr-3 text-right">RMSD</th>
                                  <th className="pb-1.5 pr-3 text-right">Reward</th>
                                  <th className="pb-1.5 pr-3 text-right">H-bonds</th>
                                  <th className="pb-1.5 text-center">Secondary Structure</th>
                                </tr>
                              </thead>
                              <tbody>
                                {binders.slice(0, 10).map((b: any, idx: number) => {
                                  const isTop = b === topBinder;
                                  return (
                                    <tr key={idx} className={'border-b border-dark-700 ' + (isTop ? 'bg-amber-500/10' : '')}>
                                      <td className="py-1.5 pr-3 text-gray-400">{idx + 1}</td>
                                      <td className="py-1.5 pr-3 text-right text-gray-300">
                                        {safeNum(b.af2folding_i_pae || b.ipae || b.i_pae || b.scores?.ipAE || b.scores?.af2folding_i_pae, 1, '-')}
                                      </td>
                                      <td className="py-1.5 pr-3 text-right text-gray-300">
                                        {safeNum(b.af2folding_plddt || b.plddt || b.scores?.pLDDT || b.scores?.af2folding_plddt, 1, '-')}
                                      </td>
                                      <td className="py-1.5 pr-3 text-right text-gray-300">
                                        {safeNum(b.af2folding_rmsd || b.rmsd || b.scores?.RMSD || b.scores?.af2folding_rmsd, 2, '-')}
                                      </td>
                                      <td className={'py-1.5 pr-3 text-right font-medium ' + (isTop ? 'text-amber-400' : 'text-gray-300')}>
                                        {safeNum(b.total_reward || b.reward || b.scores?.total_reward, 3, '-')}
                                      </td>
                                      <td className="py-1.5 pr-3 text-right text-gray-300">
                                        {b.hbond_count != null || b.h_bonds != null ? String(b.hbond_count ?? b.h_bonds) : '-'}
                                      </td>
                                      <td className="py-1.5 text-center">
                                        {(b.secondary_structure || b.ss_composition) ? (
                                          <span className="text-gray-400">
                                            {(() => {
                                              const ss = b.secondary_structure || b.ss_composition || {};
                                              const alpha = ss.alpha_pct || ss.helix_pct || ss.alpha;
                                              const beta = ss.beta_pct || ss.sheet_pct || ss.beta;
                                              const coil = ss.coil_pct || ss.loop_pct || ss.coil;
                                              const parts: string[] = [];
                                              if (alpha != null) parts.push('H:' + safeNum(alpha, 0) + '%');
                                              if (beta != null) parts.push('E:' + safeNum(beta, 0) + '%');
                                              if (coil != null) parts.push('C:' + safeNum(coil, 0) + '%');
                                              return parts.length > 0 ? parts.join(' ') : '-';
                                            })()}
                                          </span>
                                        ) : '-'}
                                      </td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                            {binders.length > 10 && (
                              <div className="text-xs text-gray-500 mt-1 italic">+{binders.length - 10} more designs</div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Single binder secondary structure + h-bonds (when only 1 binder) */}
                      {topBinder && (!Array.isArray(binders) || binders.length <= 1) && (
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs mt-2">
                          {topBinder.hbond_count != null && (
                            <div className="bg-dark-700 rounded p-2">
                              <div className="text-gray-500 mb-0.5">H-bond Count</div>
                              <div className="text-white font-medium">{topBinder.hbond_count}</div>
                            </div>
                          )}
                          {(topBinder.secondary_structure || topBinder.ss_composition) && (() => {
                            const ss = topBinder.secondary_structure || topBinder.ss_composition || {};
                            const alpha = ss.alpha_pct || ss.helix_pct || ss.alpha;
                            const beta = ss.beta_pct || ss.sheet_pct || ss.beta;
                            const coil = ss.coil_pct || ss.loop_pct || ss.coil;
                            return (
                              <>
                                {alpha != null && (
                                  <div className="bg-dark-700 rounded p-2">
                                    <div className="text-gray-500 mb-0.5">Alpha Helix</div>
                                    <div className="text-white font-medium">{safeNum(alpha, 1)}%</div>
                                  </div>
                                )}
                                {beta != null && (
                                  <div className="bg-dark-700 rounded p-2">
                                    <div className="text-gray-500 mb-0.5">Beta Sheet</div>
                                    <div className="text-white font-medium">{safeNum(beta, 1)}%</div>
                                  </div>
                                )}
                                {coil != null && (
                                  <div className="bg-dark-700 rounded p-2">
                                    <div className="text-gray-500 mb-0.5">Coil/Loop</div>
                                    <div className="text-white font-medium">{safeNum(coil, 1)}%</div>
                                  </div>
                                )}
                              </>
                            );
                          })()}
                          {topBinder.binder_length != null && (
                            <div className="bg-dark-700 rounded p-2">
                              <div className="text-gray-500 mb-0.5">Binder Length</div>
                              <div className="text-white font-medium">{topBinder.binder_length} aa</div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Job info */}
                      {cxData.job_id && (
                        <div className="mt-2 text-xs text-gray-500">
                          Complexa Job: <span className="font-mono text-gray-400">{cxData.job_id}</span>
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* ADMET Radar (if ADMET data is available) */}
                {result.admet && (
                  <ADMETRadarChart admetData={result.admet} />
                )}

                {/* Composite Scoring Chart */}
                {result.candidates && result.candidates.length > 0 && (
                  <PipelineResultsChart candidates={result.candidates} />
                )}

                {/* Pipeline stages indicator */}
                {result.pipeline_stages && result.pipeline_stages.length > 0 && (
                  <div className="mt-3 flex items-center gap-1 flex-wrap">
                    <span className="text-xs text-gray-500 mr-1">Stages:</span>
                    {result.pipeline_stages.map((stage, i) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 bg-dark-700 text-gray-400 rounded-full border border-dark-600">
                        {stage}
                      </span>
                    ))}
                  </div>
                )}

                {result.error && (
                  <div className="mt-3 p-2 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
                    Error: {result.error}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ResultsPanel;
