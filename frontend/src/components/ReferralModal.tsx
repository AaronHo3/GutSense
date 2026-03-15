
import { useState } from 'react';
import { X, Copy, Send, Loader2, CheckCircle2, FileText } from 'lucide-react';
import { api } from '../api/endpoints';

interface Props {
  patientId: number;
  patientName: string;
  onClose: () => void;
  onSent: () => void;
}

export function ReferralModal({ patientId, patientName, onClose, onSent }: Props) {
  const [letter, setLetter] = useState('');
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  const generate = async () => {
    setGenerating(true);
    setError('');
    try {
      const result = await api.generateReferral(patientId);
      setLetter(result.letter);
    } catch {
      setError('Failed to generate referral. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const copy = async () => {
    await navigator.clipboard.writeText(letter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const send = async () => {
    setSending(true);
    try {
      await api.sendReferral(patientId, letter);
      setSent(true);
      setTimeout(() => { onSent(); onClose(); }, 1800);
    } catch {
      setError('Failed to send referral.');
      setSending(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="w-full max-w-2xl rounded-2xl flex flex-col"
        style={{
          background: '#0f172a',
          border: '1px solid rgba(255,255,255,0.12)',
          maxHeight: '90vh',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-400" />
            <h2 className="text-sm font-semibold text-white">GI Referral — {patientName}</h2>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {!letter && !generating && (
            <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
              <FileText className="w-10 h-10 text-slate-600" />
              <p className="text-slate-400 text-sm">
                Auto-generate a formal GI referral letter based on this patient's latest biomarker results and risk assessment.
              </p>
              <button
                onClick={generate}
                className="mt-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition"
                style={{ background: 'linear-gradient(135deg, #3b82f6, #6366f1)' }}
              >
                Generate Referral Letter
              </button>
            </div>
          )}

          {generating && (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
              <p className="text-slate-400 text-sm">Generating referral letter...</p>
            </div>
          )}

          {letter && !generating && (
            <textarea
              value={letter}
              onChange={e => setLetter(e.target.value)}
              className="w-full text-xs font-mono text-slate-200 bg-transparent resize-none outline-none leading-relaxed"
              style={{ minHeight: '420px' }}
              spellCheck={false}
            />
          )}

          {error && (
            <p className="mt-3 text-xs text-red-400 text-center">{error}</p>
          )}
        </div>

        {/* Footer */}
        {letter && !generating && (
          <div
            className="flex items-center justify-between px-5 py-3 gap-3"
            style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}
          >
            <button
              onClick={generate}
              className="text-xs text-slate-500 hover:text-slate-300 transition"
            >
              Regenerate
            </button>
            <div className="flex items-center gap-2">
              <button
                onClick={copy}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs text-slate-300 hover:text-white transition"
                style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
              >
                {copied
                  ? <><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Copied</>
                  : <><Copy className="w-3.5 h-3.5" /> Copy</>}
              </button>
              <button
                onClick={send}
                disabled={sending || sent}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white transition disabled:opacity-60"
                style={{ background: sent ? '#10b981' : 'linear-gradient(135deg, #3b82f6, #6366f1)' }}
              >
                {sent
                  ? <><CheckCircle2 className="w-3.5 h-3.5" /> Sent</>
                  : sending
                    ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Sending...</>
                    : <><Send className="w-3.5 h-3.5" /> Quick Send</>}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
