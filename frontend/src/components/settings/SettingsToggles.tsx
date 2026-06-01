'use client';

import React, { useState } from 'react';

type ToggleItem = {
  id: string;
  title: string;
  description: string;
  initialValue: boolean;
};

const notificationToggles: ToggleItem[] = [
  { id: 'shortlist', title: 'Shortlist ready', description: 'When matching finishes for a submitted brief', initialValue: true },
  { id: 'reply', title: 'Creator replied', description: 'When a contacted creator accepts or declines', initialValue: true },
  { id: 'digest', title: 'Weekly digest', description: 'Top creators trending in your niche', initialValue: false },
  { id: 'updates', title: 'Product updates', description: 'New features, occasional only', initialValue: true },
];

export default function SettingsToggles() {
  const [toggles, setToggles] = useState(notificationToggles);

  const handleToggle = (id: string) => {
    setToggles(toggles.map((t) => (t.id === id ? { ...t, initialValue: !t.initialValue } : t)));
  };

  return (
    <section className="card" id="notifications">
      <h2>Notifications</h2>
      <p className="desc">Choose how InfluenceIQ pings you when something happens.</p>
      {toggles.map((t) => (
        <div key={t.id} className="toggle-row">
          <div className="lhs">
            {t.title}
            <div className="desc">{t.description}</div>
          </div>
          <span className={`sw ${t.initialValue ? 'on' : ''}`} onClick={() => handleToggle(t.id)}></span>
        </div>
      ))}
    </section>
  );
}
