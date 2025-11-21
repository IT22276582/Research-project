"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { ToastMessage, ToastKind, Toasts } from "./Toast";

type ToastContextValue = {
  addToast: (message: string, type?: ToastKind) => void;
  dismissToast: (id: string) => void;
};

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback(
    (message: string, type: ToastKind = "info") => {
      const id = `${Date.now()}-${Math.random()}`;
      setToasts((prev) => [...prev, { id, type, message }].slice(-5));
      // Auto-dismiss after 5 seconds
      setTimeout(() => dismissToast(id), 5000);
    },
    [dismissToast],
  );

  const value = useMemo(
    () => ({
      addToast,
      dismissToast,
    }),
    [addToast, dismissToast],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <Toasts toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
}

export function useToasts() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToasts must be used within a ToastProvider");
  }
  return ctx;
}
