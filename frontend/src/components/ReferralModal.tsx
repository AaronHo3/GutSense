
import { useState } from 'react';
import { X, Copy, Send, Loader2, CheckCircle2 } from 'lucide-react';
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
      style={{ background: 'rgba(27,26,23,0.45)', backdropFilter: 'blur(4px)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="w-full max-w-2xl flex flex-col"
        style={{ background: 'var(--surface)', border: '1px solid var(--line2)', borderRadius: 6, maxHeight: '90vh' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5" style={{ borderBottom: '1px solid var(--line)' }}>
          <div>
            <span className="eyebrow">GI Referral Letter</span>
            <h2 className="font-serif text-ink mt-1.5" style={{ fontSize: '1.375rem', fontWeight: 440 }}>{patientName}</h2>
          </div>
          <button onClick={onClose} className="text-faint hover:text-ink transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {!letter && !generating && (
            <div className="flex flex-col items-center justify-center py-12 gap-4 text-center">
              <p className="text-muted" style={{ fontSize: '0.9375rem', lineHeight: 1.55, maxWidth: 420 }}>
                Auto-generate a formal GI referral letter from this patient's latest biomarker results and risk assessment.
              </p>
              <button
                onClick={generate}
                className="px-5 py-2.5 font-mono uppercase text-paper transition"
                style={{ background: 'var(--ink)', borderRadius: 4, fontSize: '0.6875rem', letterSpacing: '0.08em' }}
              >
                Generate Referral Letter
              </button>
            </div>
          )}

          {generating && (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 className="w-6 h-6 text-muted animate-spin" />
              <p className="eyebrow">Generating referral letter…</p>
            </div>
          )}

          {letter && !generating && (
            <textarea
              value={letter}
              onChange={e => setLetter(e.target.value)}
              className="w-full font-mono text-ink bg-transparent resize-none outline-none"
              style={{ minHeight: '420px', fontSize: '0.8125rem', lineHeight: 1.7 }}
              spellCheck={false}
            />
          )}

          {error && (
            <p className="mt-3 text-center" style={{ color: '#9E2B25', fontSize: '0.8125rem' }}>{error}</p>
          )}
        </div>

        {/* Footer */}
        {letter && !generating && (
          <div className="flex items-center justify-between px-6 py-4 gap-3" style={{ borderTop: '1px solid var(--line)' }}>
            <button onClick={generate} className="eyebrow hover:text-ink transition">
              Regenerate
            </button>
            <div className="flex items-center gap-2.5">
              <button
                onClick={copy}
                className="flex items-center gap-2 px-3 py-2 font-mono uppercase text-muted hover:text-ink transition"
                style={{ border: '1px solid var(--line2)', borderRadius: 4, fontSize: '0.6875rem', letterSpacing: '0.08em' }}
              >
                {copied
                  ? <><CheckCircle2 className="w-3.5 h-3.5" style={{ color: '#2F6B4F' }} /> Copied</>
                  : <><Copy className="w-3.5 h-3.5" /> Copy</>}
              </button>
              <button
                onClick={send}
                disabled={sending || sent}
                className="flex items-center gap-2 px-4 py-2 font-mono uppercase text-paper transition disabled:opacity-60"
                style={{ background: sent ? '#2F6B4F' : 'var(--ink)', borderRadius: 4, fontSize: '0.6875rem', letterSpacing: '0.08em' }}
              >
                {sent
                  ? <><CheckCircle2 className="w-3.5 h-3.5" /> Sent</>
                  : sending
                    ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Sending…</>
                    : <><Send className="w-3.5 h-3.5" /> Quick Send</>}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
