"use client";

export type ToastKind = "info" | "success" | "error";

export type ToastMessage = {
  id: string;
  type: ToastKind;
  message: string;
};

const toneMap: Record<ToastKind, { bg: string; dot: string; icon: string; label: string }> = {
  info: { bg: "bg-slate-800/90 border-slate-700", dot: "bg-cyan-400", icon: "ℹ️", label: "Info" },
  success: { bg: "bg-emerald-800/90 border-emerald-600/60", dot: "bg-emerald-300", icon: "✓", label: "Success" },
  error: { bg: "bg-rose-900/90 border-rose-600/60", dot: "bg-rose-300", icon: "!", label: "Error" },
};

export function Toasts({
  toasts,
  onDismiss,
}: {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}) {
  if (!toasts.length) return null;
  return (
    <div
      className="pointer-events-none fixed right-4 top-4 z-50 flex w-full max-w-md flex-col gap-3 sm:right-6 sm:top-6"
      role="region"
      aria-live="assertive"
      aria-label="Notifications"
      style={{
        right: 'clamp(1rem, 2vw, 1.5rem)',
        top: 'clamp(1rem, 2vw, 1.5rem)',
        maxWidth: 'min(90vw, 28rem)',
        gap: 'clamp(0.5rem, 1vw, 0.75rem)'
      }}
    >
      {toasts.map((toast) => {
        const tone = toneMap[toast.type];
        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start gap-3 rounded-2xl border shadow-xl backdrop-blur transition transform duration-150 ease-out hover:translate-y-0.5 ${tone.bg}`}
            role="status"
            aria-label={`${tone.label} notification`}
            style={{
              padding: 'clamp(0.75rem, 1.5vw, 1rem) clamp(1rem, 2vw, 1.25rem)',
              gap: 'clamp(0.5rem, 1vw, 0.75rem)',
              borderRadius: 'clamp(0.75rem, 1.5vw, 1rem)',
              fontSize: 'clamp(0.875rem, 1vw, 0.9375rem)',
              lineHeight: '1.5',
              minWidth: 'clamp(280px, 80vw, 320px)',
              maxWidth: '100%'
            }}
          >
            <span
              className={`rounded-full ${tone.dot}`}
              aria-hidden
              style={{
                width: 'clamp(0.625rem, 1vw, 0.75rem)',
                height: 'clamp(0.625rem, 1vw, 0.75rem)',
                marginTop: 'clamp(0.125rem, 0.5vw, 0.25rem)',
                flexShrink: 0
              }}
            />
            <div
              aria-hidden
              style={{
                fontSize: 'clamp(1rem, 1.25vw, 1.125rem)',
                marginTop: 'clamp(0.125rem, 0.5vw, 0.25rem)',
                lineHeight: '1',
                flexShrink: 0
              }}
            >
              {tone.icon}
            </div>
            <div
              className="flex-1 leading-relaxed"
              style={{
                color: '#f8fafc',
                wordBreak: 'break-word',
                overflowWrap: 'break-word'
              }}
            >
              {toast.message}
            </div>
            <button
              type="button"
              onClick={() => onDismiss(toast.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onDismiss(toast.id);
                }
              }}
              className="transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/60 rounded"
              aria-label="Close notification"
              style={{
                color: '#cbd5e1',
                fontSize: 'clamp(1rem, 1.5vw, 1.25rem)',
                minWidth: 'clamp(2rem, 3vw, 2.5rem)',
                minHeight: 'clamp(2rem, 3vw, 2.5rem)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: '0.375rem',
                flexShrink: 0,
                touchAction: 'manipulation'
              }}
            >
              ×
            </button>
          </div>
        );
      })}
    </div>
  );
}
