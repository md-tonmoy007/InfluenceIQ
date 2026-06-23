"use client";

import { useEffect, useState } from "react";
import {
  changePassword,
  getMe,
  updateProfile,
  type CurrentUser,
} from "@/lib/api";

export default function ProfileForm() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMessage, setProfileMessage] = useState<{
    type: "ok" | "err";
    text: string;
  } | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState<{
    type: "ok" | "err";
    text: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setName(me.name);
        setRole(me.role ?? "");
        setTimezone(me.timezone ?? "UTC");
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(
          err instanceof Error ? err.message : "Failed to load profile"
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const initials = (user?.name || user?.email || "?")
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 2) || "?";

  const onSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    setProfileMessage(null);
    try {
      const updated = await updateProfile({
        name: name.trim() || user?.name || "",
        role: role.trim() ? role.trim() : null,
        timezone: timezone || "UTC",
      });
      setUser(updated);
      setProfileMessage({ type: "ok", text: "Profile saved." });
      setName(updated.name);
      setRole(updated.role ?? "");
      setTimezone(updated.timezone ?? "UTC");
    } catch (err) {
      setProfileMessage({
        type: "err",
        text: err instanceof Error ? err.message : "Failed to save profile",
      });
    } finally {
      setSavingProfile(false);
    }
  };

  const onChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      setPasswordMessage({
        type: "err",
        text: "New password must be at least 8 characters.",
      });
      return;
    }
    setSavingPassword(true);
    setPasswordMessage(null);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordMessage({ type: "ok", text: "Password updated." });
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      setPasswordMessage({
        type: "err",
        text:
          err instanceof Error
            ? err.message
            : "Failed to change password",
      });
    } finally {
      setSavingPassword(false);
    }
  };

  if (loadError) {
    return (
      <section className="card" id="profile">
        <h2>Profile</h2>
        <p
          style={{
            color: "var(--warn-ink)",
            fontSize: "13px",
            margin: 0,
          }}
        >
          {loadError}
        </p>
      </section>
    );
  }

  if (!user) {
    return (
      <section className="card" id="profile">
        <h2>Profile</h2>
        <p className="desc">Loading your profile…</p>
      </section>
    );
  }

  return (
    <section className="card" id="profile">
      <h2>Profile</h2>
      <p className="desc">
        This is what teammates and creators see when you interact on
        InfluenceIQ.
      </p>
      <div className="avatar-row">
        <span className="av-big">{initials}</span>
        <a className="change-pic">Change photo</a>
      </div>
      <form onSubmit={onSaveProfile}>
        <div className="row">
          <div className="field">
            <label>Full name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={255}
            />
          </div>
          <div className="field">
            <label>Role</label>
            <input
              value={role}
              onChange={(e) => setRole(e.target.value)}
              maxLength={255}
              placeholder="e.g. Head of Growth"
            />
          </div>
        </div>
        <div className="row">
          <div className="field">
            <label>Work email</label>
            <input value={user.email} readOnly disabled />
          </div>
          <div className="field">
            <label>Timezone</label>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
            >
              <option value="UTC">UTC</option>
              <option value="America/Toronto">America/Toronto (EDT)</option>
              <option value="America/Los_Angeles">America/Los_Angeles</option>
              <option value="America/New_York">America/New_York</option>
              <option value="Europe/London">Europe/London</option>
              <option value="Europe/Berlin">Europe/Berlin</option>
              <option value="Asia/Dhaka">Asia/Dhaka</option>
              <option value="Asia/Kolkata">Asia/Kolkata</option>
              <option value="Asia/Tokyo">Asia/Tokyo</option>
              <option value="Asia/Singapore">Asia/Singapore</option>
            </select>
          </div>
        </div>
        {profileMessage && (
          <p
            className="msg"
            style={{
              color: profileMessage.type === "ok" ? "var(--good)" : "var(--warn-ink)",
              fontSize: "12.5px",
              margin: "0 0 12px",
            }}
          >
            {profileMessage.text}
          </p>
        )}
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            className="btn btn-primary btn-sm"
            type="submit"
            disabled={savingProfile}
          >
            {savingProfile ? "Saving…" : "Save profile"}
          </button>
        </div>
      </form>

      <div
        style={{
          marginTop: "24px",
          paddingTop: "18px",
          borderTop: "1px solid var(--line-soft)",
        }}
      >
        <div
          style={{
            fontSize: "11.5px",
            fontFamily: "'JetBrains Mono',monospace",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--muted)",
            marginBottom: "10px",
          }}
        >
          Password
        </div>
        <form onSubmit={onChangePassword}>
          <div className="row">
            <div className="field">
              <label>Current password</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <div className="field">
              <label>New password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                minLength={8}
              />
            </div>
          </div>
          {passwordMessage && (
            <p
              className="msg"
              style={{
                color:
                  passwordMessage.type === "ok"
                    ? "var(--good)"
                    : "var(--warn-ink)",
                fontSize: "12.5px",
                margin: "0 0 12px",
              }}
            >
              {passwordMessage.text}
            </p>
          )}
          <button
            className="btn btn-ghost btn-sm"
            type="submit"
            disabled={savingPassword || !currentPassword || !newPassword}
          >
            {savingPassword ? "Updating…" : "Update password"}
          </button>
        </form>
      </div>
    </section>
  );
}
