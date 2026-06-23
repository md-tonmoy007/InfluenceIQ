"use client";

import { cloneElement, useEffect, useId, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, ReactElement } from "react";

import {
  addListItem,
  createSavedList,
  listSavedLists,
} from "@/lib/api";
import { useToast } from "./ToastProvider";

type ListOption = {
  id: string;
  name: string;
  isNew?: boolean;
};

type SaveToListPopoverProps = {
  children: ReactElement<{ onClick?: (event: ReactMouseEvent) => void }>;
  influencerId?: string;
  sourceCampaignId?: string | null;
  matchScoreSnapshot?: number | null;
};

export default function SaveToListPopover({
  children,
  influencerId,
  sourceCampaignId,
  matchScoreSnapshot,
}: SaveToListPopoverProps) {
  const { toast } = useToast();
  const popoverId = useId();
  const wrapperRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [lists, setLists] = useState<ListOption[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [showNewInput, setShowNewInput] = useState(false);
  const [newListName, setNewListName] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoading(true);
    listSavedLists()
      .then((summaries) => {
        if (active) {
          setLists(summaries.map((summary) => ({ id: summary.id, name: summary.name })));
        }
      })
      .catch((error) => {
        if (active) {
          toast(
            error instanceof Error ? error.message : "Unable to load saved lists.",
            { type: "error" }
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [open, toast]);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (wrapperRef.current && !wrapperRef.current.contains(target)) {
        setOpen(false);
      }
    };
    const handleExternalOpen = (event: Event) => {
      const detail = (event as CustomEvent).detail as string;
      if (detail && detail !== popoverId) {
        setOpen(false);
      }
    };
    document.addEventListener("click", handleClick);
    window.addEventListener("iiq-save-popover-open", handleExternalOpen);
    return () => {
      document.removeEventListener("click", handleClick);
      window.removeEventListener("iiq-save-popover-open", handleExternalOpen);
    };
  }, [popoverId]);

  useEffect(() => {
    if (showNewInput && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showNewInput]);

  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const toggleSelection = (id: string, checked: boolean) => {
    setSelected((prev) => {
      if (checked) return prev.includes(id) ? prev : [...prev, id];
      return prev.filter((item) => item !== item);
    });
  };

  const handleSave = async () => {
    if (!influencerId) {
      toast(
        "This creator isn't linked to an influencer record yet — saving isn't available.",
        { type: "info" }
      );
      return;
    }
    if (selected.length === 0) {
      toast("Pick a list first", { type: "info" });
      return;
    }
    setOpen(false);
    let addedCount = 0;
    let skippedCount = 0;
    for (const listId of selected) {
      try {
        const result = await addListItem(listId, {
          influencer_id: influencerId,
          source_campaign_id: sourceCampaignId ?? null,
          match_score_snapshot: matchScoreSnapshot ?? null,
        });
        addedCount += result.added.length;
        skippedCount += result.skipped.length;
      } catch (error) {
        toast(
          error instanceof Error ? error.message : "Unable to save creator to a list.",
          { type: "error" }
        );
      }
    }
    if (addedCount > 0) {
      toast(
        <span>
          Saved to{" "}
          <span style={{ fontFamily: "Instrument Serif,serif", fontStyle: "italic" }}>
            {lists.find((l) => l.id === selected[0])?.name ?? "list"}
          </span>{" "}
          ✓
        </span>,
        { type: "success" }
      );
    } else if (skippedCount > 0) {
      toast("This creator is already in the selected lists.", { type: "info" });
    }
    setSelected([]);
  };

  const handleAddList = async () => {
    const name = newListName.trim();
    if (!name) return;
    try {
      const created = await createSavedList({ name });
      const next: ListOption = { id: created.id, name, isNew: true };
      setLists((prev) => [...prev, next]);
      setSelected((prev) => (prev.includes(created.id) ? prev : [...prev, created.id]));
      setNewListName("");
      setShowNewInput(false);
    } catch (error) {
      toast(
        error instanceof Error ? error.message : "Unable to create list.",
        { type: "error" }
      );
    }
  };

  const trigger = (() => {
    const originalOnClick = children.props.onClick;
    return cloneElement(children, {
      onClick: (event: ReactMouseEvent) => {
        if (originalOnClick) originalOnClick(event);
        setOpen((prev) => {
          const next = !prev;
          if (next) {
            window.dispatchEvent(
              new CustomEvent("iiq-save-popover-open", { detail: popoverId })
            );
          }
          return next;
        });
      },
    });
  })();

  return (
    <div ref={wrapperRef} style={{ position: "relative" }}>
      {trigger}
      <div
        data-iiq-save-pop=""
        style={{
          position: "absolute",
          top: "calc(100% + 6px)",
          right: 0,
          width: "min(280px, calc(100vw - 28px))",
          background: "#fff",
          border: "1px solid #e6e3da",
          borderRadius: "12px",
          boxShadow: "0 24px 60px -22px rgba(15,17,22,0.28)",
          overflow: "hidden",
          display: open ? "block" : "none",
          zIndex: 200,
          fontFamily: "Geist,system-ui,sans-serif",
          textAlign: "left",
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <div
          style={{
            padding: "12px 14px 8px",
            fontSize: "11px",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "#6c6f7a",
            fontFamily: "JetBrains Mono,monospace",
            borderBottom: "1px solid #efece4",
          }}
        >
          Save to list
        </div>
        <div
          id="iiq-list-items"
          style={{ maxHeight: "200px", overflowY: "auto", padding: "6px 0" }}
        >
          {loading ? (
            <div
              style={{
                padding: "14px",
                fontSize: "12.5px",
                color: "var(--muted, #6c6f7a)",
              }}
            >
              Loading your lists…
            </div>
          ) : lists.length === 0 ? (
            <div
              style={{
                padding: "14px",
                fontSize: "12.5px",
                color: "var(--muted, #6c6f7a)",
              }}
            >
              You don&apos;t have any lists yet — create one below.
            </div>
          ) : (
            lists.map((list, index) => (
              <label
                key={list.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "8px 14px",
                  fontSize: "13px",
                  cursor: "pointer",
                  transition: "background .15s",
                  background: hoveredIndex === index ? "#f4f2ec" : "transparent",
                }}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                <input
                  type="checkbox"
                  data-list={list.name}
                  style={{ accentColor: "oklch(0.58 0.22 285)" }}
                  checked={selectedSet.has(list.id)}
                  onChange={(event) =>
                    toggleSelection(list.id, event.currentTarget.checked)
                  }
                />
                <span style={{ flex: 1 }}>{list.name}</span>
                {list.isNew ? (
                  <span
                    style={{
                      fontSize: "10px",
                      color: "oklch(0.32 0.18 285)",
                      fontFamily: "JetBrains Mono,monospace",
                    }}
                  >
                    NEW
                  </span>
                ) : null}
              </label>
            ))
          )}
        </div>
        <div
          id="iiq-new-list-row"
          style={{ borderTop: "1px solid #efece4", padding: "10px 14px" }}
        >
          <button
            id="iiq-new-list-btn"
            type="button"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "none",
              border: 0,
              color: "oklch(0.32 0.18 285)",
              fontSize: "13px",
              fontWeight: 500,
              cursor: "pointer",
              padding: 0,
              fontFamily: "inherit",
            }}
            onClick={() => setShowNewInput(true)}
          >
            <span
              style={{
                width: "18px",
                height: "18px",
                borderRadius: "50%",
                background:
                  "linear-gradient(135deg,oklch(0.58 0.22 285),oklch(0.74 0.18 30))",
                color: "#fff",
                display: "grid",
                placeItems: "center",
                fontSize: "13px",
                lineHeight: 1,
              }}
            >
              +
            </span>
            Create new list
          </button>
          <div
            id="iiq-new-list-input"
            style={{
              display: showNewInput ? "flex" : "none",
              gap: "6px",
              marginTop: "8px",
            }}
          >
            <input
              id="iiq-new-list-name"
              ref={inputRef}
              placeholder="List name"
              value={newListName}
              onChange={(event) => setNewListName(event.currentTarget.value)}
              style={{
                flex: 1,
                height: "32px",
                padding: "0 10px",
                border: "1px solid #e6e3da",
                borderRadius: "7px",
                fontSize: "13px",
                outline: "none",
                fontFamily: "inherit",
              }}
            />
            <button
              id="iiq-new-list-add"
              type="button"
              style={{
                height: "32px",
                padding: "0 12px",
                border: 0,
                borderRadius: "7px",
                background: "#0a0b10",
                color: "#fff",
                fontSize: "12px",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
              onClick={handleAddList}
            >
              Add
            </button>
          </div>
        </div>
        <div
          style={{
            borderTop: "1px solid #efece4",
            padding: "10px 14px",
            display: "flex",
            justifyContent: "flex-end",
            gap: "8px",
          }}
        >
          <button
            id="iiq-save-cancel"
            type="button"
            style={{
              height: "32px",
              padding: "0 12px",
              border: "1px solid #e6e3da",
              borderRadius: "8px",
              background: "#fff",
              fontSize: "12.5px",
              color: "#2a2e3a",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
            onClick={() => setOpen(false)}
          >
            Cancel
          </button>
          <button
            id="iiq-save-confirm"
            type="button"
            style={{
              height: "32px",
              padding: "0 14px",
              border: 0,
              borderRadius: "8px",
              background:
                "linear-gradient(180deg,oklch(0.58 0.22 285),oklch(0.50 0.22 285))",
              color: "#fff",
              fontSize: "12.5px",
              fontWeight: 500,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
            onClick={handleSave}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
