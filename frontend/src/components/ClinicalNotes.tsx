
import { useState } from 'react';
import type { ClinicalNote } from '../types';

interface Props {
  notes: ClinicalNote[];
  onAdd?: (text: string, isRecommendation: boolean) => Promise<void>;
  allowAdd?: boolean;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function ClinicalNotes({ notes, onAdd, allowAdd = false }: Props) {
  const [text, setText] = useState('');
  const [isRec, setIsRec] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!text.trim() || !onAdd) return;
    setSubmitting(true);
    await onAdd(text.trim(), isRec);
    setText('');
    setSubmitting(false);
  };

  return (
    <div className="card p-6">
      <span className="eyebrow">Clinical Notes</span>

      {allowAdd && (
        <div className="mt-4 mb-5">
          <textarea
            className="w-full p-3 resize-none focus:outline-none text-ink placeholder:text-faint"
            style={{ background: 'var(--paper)', border: '1px solid var(--line2)', borderRadius: 4, fontSize: '0.875rem' }}
            rows={3}
            placeholder="Add a clinical note or recommendation…"
            value={text}
            onChange={e => setText(e.target.value)}
          />
          <div className="flex items-center justify-between mt-2.5">
            <label className="flex items-center gap-2 text-muted cursor-pointer hover:text-ink transition-colors" style={{ fontSize: '0.8125rem' }}>
              <input
                type="checkbox"
                checked={isRec}
                onChange={e => setIsRec(e.target.checked)}
                style={{ accentColor: '#1B1A17' }}
              />
              Push as physician recommendation
            </label>
            <button
              onClick={handleSubmit}
              disabled={!text.trim() || submitting}
              className="px-4 py-1.5 text-paper disabled:opacity-40 transition font-mono uppercase"
              style={{ background: 'var(--ink)', borderRadius: 4, fontSize: '0.6875rem', letterSpacing: '0.08em' }}
            >
              {submitting ? 'Sending…' : 'Add Note'}
            </button>
          </div>
        </div>
      )}

      <div className="mt-4 space-y-0 max-h-72 overflow-y-auto">
        {notes.length === 0 && (
          <p className="text-faint text-center py-6" style={{ fontSize: '0.8125rem' }}>No notes yet.</p>
        )}
        {notes.map(note => (
          <div key={note.id} className="py-3.5" style={{ borderTop: '1px solid var(--line)' }}>
            {note.is_physician_recommendation && (
              <div className="font-mono uppercase mb-1.5" style={{ color: '#9E2B25', fontSize: '0.625rem', letterSpacing: '0.12em' }}>
                Physician Recommendation
              </div>
            )}
            <p className="text-ink" style={{ fontSize: '0.9375rem', lineHeight: 1.55 }}>{note.note_text}</p>
            <p className="font-mono text-faint mt-2" style={{ fontSize: '0.6875rem' }}>{relativeTime(note.created_at)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
