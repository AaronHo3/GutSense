
import { useState } from 'react';
import { MessageSquare, Stethoscope, Send } from 'lucide-react';
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
    <div className="rounded-2xl p-4" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3 flex items-center gap-2 pb-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <MessageSquare className="w-3.5 h-3.5 text-blue-400" />
        Clinical Notes
      </h3>

      {allowAdd && (
        <div className="mb-4">
          <textarea
            className="w-full rounded-xl p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/30 text-slate-200 placeholder:text-slate-600"
            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}
            rows={3}
            placeholder="Add a clinical note or recommendation..."
            value={text}
            onChange={e => setText(e.target.value)}
          />
          <div className="flex items-center justify-between mt-2">
            <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer hover:text-slate-300 transition-colors">
              <input
                type="checkbox"
                checked={isRec}
                onChange={e => setIsRec(e.target.checked)}
                className="rounded accent-blue-500"
              />
              <Stethoscope className="w-3 h-3 text-blue-400" />
              Push as physician recommendation
            </label>
            <button
              onClick={handleSubmit}
              disabled={!text.trim() || submitting}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg disabled:opacity-50 hover:bg-blue-700 transition shadow-sm"
            >
              <Send className="w-3 h-3" />
              {submitting ? 'Sending...' : 'Add Note'}
            </button>
          </div>
        </div>
      )}

      <div className="space-y-2 max-h-60 overflow-y-auto">
        {notes.length === 0 && (
          <p className="text-xs text-slate-600 text-center py-4">No notes yet.</p>
        )}
        {notes.map(note => (
          <div
            key={note.id}
            className="p-3 rounded-xl text-sm"
            style={note.is_physician_recommendation
              ? { background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }
              : { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }
            }
          >
            {note.is_physician_recommendation && (
              <div className="flex items-center gap-1 text-xs text-blue-400 font-semibold mb-1.5">
                <Stethoscope className="w-3 h-3" />
                Physician Recommendation
              </div>
            )}
            <p className="text-slate-300 leading-relaxed">{note.note_text}</p>
            <p className="text-xs text-slate-500 mt-1.5">{relativeTime(note.created_at)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
