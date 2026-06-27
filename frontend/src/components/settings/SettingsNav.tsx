'use client';

import React, { useEffect, useState } from 'react';

type NavItem = {
  id: string;
  label: string;
  color?: string;
};

const navItems: NavItem[] = [
  { id: 'profile', label: 'Profile' },
  { id: 'brand', label: 'Brand' },
  { id: 'billing', label: 'Plan & Billing' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'api', label: 'API & Integrations' },
  { id: 'danger', label: 'Danger zone', color: 'var(--warn-ink)' },
];

export default function SettingsNav() {
  const [activeId, setActiveId] = useState('profile');

  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (hash && navItems.some((item) => item.id === hash)) {
      requestAnimationFrame(() => {
        const el = document.getElementById(hash);
        if (el) {
          const topbarHeight = 64;
          const padding = 24;
          const offset = el.getBoundingClientRect().top + window.scrollY - topbarHeight - padding;
          window.scrollTo({ top: offset, behavior: 'smooth' });
          setActiveId(hash);
        }
      });
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      {
        rootMargin: '-100px 0px -70% 0px',
        threshold: 0,
      }
    );

    navItems.forEach((item) => {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    const el = document.getElementById(id);
    if (el) {
      const topbarHeight = 64; // from CSS
      const padding = 24;
      const offset = el.getBoundingClientRect().top + window.scrollY - topbarHeight - padding;
      window.scrollTo({ top: offset, behavior: 'smooth' });
    }
  };

  return (
    <nav className="sub-nav">
      {navItems.map((item) => (
        <a
          key={item.id}
          href={`#${item.id}`}
          className={activeId === item.id ? 'active' : ''}
          style={item.color ? { color: item.color } : {}}
          onClick={(e) => handleClick(e, item.id)}
        >
          {item.label}
        </a>
      ))}
    </nav>
  );
}
