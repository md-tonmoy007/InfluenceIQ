"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";

type ToastType = "success" | "info" | "error";

type ToastOptions = {
  type?: ToastType;
  duration?: number;
};

type ToastItem = {
  id: number;
  message: ReactNode;
  type: ToastType;
  duration: number;
  visible: boolean;
};

type ToastContextValue = {
  toast: (message: ReactNode, options?: ToastOptions) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}

export default function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [isPhone, setIsPhone] = useState(false);
  const nextId = useRef(0);
  const timers = useRef<number[]>([]);

  const toast = useCallback((message: ReactNode, options?: ToastOptions) => {
    const id = nextId.current++;
    const type = options?.type ?? "info";
    const duration = options?.duration ?? 3200;

    setToasts((prev) => [
      ...prev,
      { id, message, type, duration, visible: false },
    ]);

    requestAnimationFrame(() => {
      setToasts((prev) =>
        prev.map((item) =>
          item.id === id ? { ...item, visible: true } : item
        )
      );
    });

    const hideTimer = window.setTimeout(() => {
      setToasts((prev) =>
        prev.map((item) =>
          item.id === id ? { ...item, visible: false } : item
        )
      );
      const removeTimer = window.setTimeout(() => {
        setToasts((prev) => prev.filter((item) => item.id !== id));
      }, 350);
      timers.current.push(removeTimer);
    }, duration);

    timers.current.push(hideTimer);
  }, []);

  useEffect(() => {
    const activeTimers = timers.current;
    return () => {
      activeTimers.forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 640px)");
    const updatePhoneState = () => setIsPhone(mediaQuery.matches);
    updatePhoneState();
    mediaQuery.addEventListener("change", updatePhoneState);
    return () => mediaQuery.removeEventListener("change", updatePhoneState);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        id="iiq-toast-root"
        style={{
          position: "fixed",
          top: "80px",
          right: isPhone ? "14px" : "24px",
          left: isPhone ? "14px" : undefined,
          width: isPhone ? "auto" : undefined,
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          pointerEvents: "none",
        }}
      >
        {toasts.map((toastItem) => {
          const baseStyle = {
            pointerEvents: "auto" as const,
            background: "#0a0b10",
            color: "#fff",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "12px",
            padding: "12px 16px 12px 14px",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            fontSize: "13.5px",
            boxShadow: "0 24px 60px -16px rgba(10,11,16,0.45)",
            minWidth: "260px",
            maxWidth: "380px",
            opacity: toastItem.visible ? 1 : 0,
            transform: toastItem.visible
              ? "none"
              : "translateY(-8px) scale(.98)",
            transition: "all .3s cubic-bezier(.2,.8,.2,1)",
            fontFamily: "Geist,system-ui,sans-serif",
          };

          const accentBackground =
            toastItem.type === "success"
              ? "linear-gradient(135deg,oklch(0.65 0.13 155),oklch(0.78 0.15 215))"
              : toastItem.type === "error"
                ? "linear-gradient(135deg,oklch(0.62 0.22 28),oklch(0.68 0.18 18))"
                : "linear-gradient(135deg,oklch(0.58 0.22 285),oklch(0.74 0.18 30))";

          return (
            <div key={toastItem.id} style={baseStyle}>
              {toastItem.type === "success" ? (
                <span
                  style={{
                    width: "22px",
                    height: "22px",
                    borderRadius: "50%",
                    background: accentBackground,
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                  }}
                >
                  <svg
                    viewBox="0 0 16 12"
                    width="11"
                    height="9"
                    fill="none"
                    stroke="white"
                    strokeWidth="2.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M1 6 L6 11 L15 1" />
                  </svg>
                </span>
              ) : (
                <span
                  style={{
                    width: "22px",
                    height: "22px",
                    borderRadius: "50%",
                    background: accentBackground,
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                    color: "#fff",
                    fontFamily: "Instrument Serif,serif",
                    fontStyle: "italic",
                    fontSize: "14px",
                  }}
                >
                  {toastItem.type === "error" ? "!" : "*"}
                </span>
              )}
              <span style={{ flex: 1 }}>{toastItem.message}</span>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
