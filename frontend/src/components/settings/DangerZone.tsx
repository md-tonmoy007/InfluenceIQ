"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { clearTokens } from "@/lib/auth";
import { deleteAccount } from "@/lib/api";

export default function DangerZone() {
  const router = useRouter();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [typedEmail, setTypedEmail] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = () => {
    setError(null);
    setTypedEmail("");
    setConfirmOpen(true);
  };

  const close = () => {
    if (deleting) return;
    setConfirmOpen(false);
    setTypedEmail("");
    setError(null);
  };

  const onDelete = async () => {
    setDeleting(true);
    setError(null);
    try {
      await deleteAccount();
      // Drop in-memory tokens and bounce to /login. The
      // soft-deleted user will be rejected by /api/auth/login
      // (and by get_current_user on every subsequent request).
      clearTokens();
      setConfirmOpen(false);
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      } else {
        router.push("/login");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to delete account"
      );
      setDeleting(false);
    }
  };

  return (
    <section className="card danger" id="danger">
      <h2>Delete account</h2>
      <p className="desc" style={{ color: "var(--warn-ink)", opacity: 0.8 }}>
        Permanently delete your account and all associated briefs, lists
        and search history. This cannot be undone.
      </p>
      <button
        className="btn btn-ghost btn-sm"
        style={{
          borderColor: "color-mix(in oklab,var(--warn),white 60%)",
          color: "var(--warn-ink)",
        }}
        type="button"
        onClick={open}
      >
        Delete account
      </button>

      {confirmOpen && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            marginTop: "16px",
            padding: "14px",
            border: "1px solid color-mix(in oklab,var(--warn),white 70%)",
            borderRadius: "10px",
            background: "var(--warn-soft)",
          }}
        >
          <p
            style={{
              margin: "0 0 8px",
              fontSize: "13px",
              color: "var(--warn-ink)",
            }}
          >
            Type your email to confirm. The account will be soft-deleted
            and you will not be able to sign in again.
          </p>
          <input
            type="email"
            value={typedEmail}
            onChange={(e) => setTypedEmail(e.target.value)}
            placeholder="you@example.com"
            style={{
              width: "100%",
              height: "36px",
              padding: "0 10px",
              border: "1px solid var(--line)",
              borderRadius: "8px",
              fontSize: "13px",
              marginBottom: "10px",
              fontFamily: "inherit",
            }}
          />
          {error && (
            <p
              style={{
                margin: "0 0 8px",
                color: "var(--warn-ink)",
                fontSize: "12.5px",
              }}
            >
              {error}
            </p>
          )}
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              className="btn btn-ghost btn-sm"
              type="button"
              onClick={close}
              disabled={deleting}
            >
              Cancel
            </button>
            <button
              className="btn btn-sm"
              type="button"
              onClick={() => void onDelete()}
              disabled={deleting || !typedEmail}
              style={{
                background: "var(--warn-ink)",
                color: "#fff",
                border: "1px solid var(--warn-ink)",
              }}
            >
              {deleting ? "Deleting…" : "Delete my account"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
