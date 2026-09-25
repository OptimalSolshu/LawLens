import { useVirtualizer } from "@tanstack/react-virtual";
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

export interface RowState {
  selected: boolean;
  /** Keyboard cursor (only while the list has focus). */
  active: boolean;
}

interface Props<T> {
  items: T[];
  getKey: (item: T) => string;
  renderItem: (item: T, state: RowState) => ReactNode;
  onSelect: (item: T) => void;
  label: string;
  selectedKey?: string | null;
  estimateSize?: number;
  /** Fixed height class, so the page does not shift as the list changes. */
  className?: string;
}

/** Virtualized listbox: arrow keys, Home/End, PageUp/PageDown, Enter to select. */
export function VirtualList<T>({
  items,
  getKey,
  renderItem,
  onSelect,
  label,
  selectedKey = null,
  estimateSize = 48,
  className = "h-80",
}: Props<T>) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const idBase = useId();
  const [active, setActive] = useState(-1);
  const [focused, setFocused] = useState(false);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => estimateSize,
    getItemKey: (i) => getKey(items[i]),
    overscan: 10,
  });

  useEffect(() => {
    setActive((a) => Math.min(a, items.length - 1));
  }, [items.length]);

  const moveTo = (i: number) => {
    if (items.length === 0) return;
    const next = Math.max(0, Math.min(items.length - 1, i));
    setActive(next);
    virtualizer.scrollToIndex(next, { align: "auto" });
  };

  const onKeyDown = (e: KeyboardEvent) => {
    const page = 10;
    const keys: Record<string, () => void> = {
      ArrowDown: () => moveTo(active + 1),
      ArrowUp: () => moveTo(active - 1),
      Home: () => moveTo(0),
      End: () => moveTo(items.length - 1),
      PageDown: () => moveTo(active + page),
      PageUp: () => moveTo(active - page),
      Enter: () => active >= 0 && onSelect(items[active]),
      " ": () => active >= 0 && onSelect(items[active]),
    };
    if (keys[e.key]) {
      e.preventDefault();
      keys[e.key]();
    }
  };

  const onFocus = () => {
    setFocused(true);
    if (active < 0) {
      const sel = items.findIndex((it) => getKey(it) === selectedKey);
      moveTo(sel >= 0 ? sel : 0);
    }
  };

  return (
    <div
      ref={scrollRef}
      role="listbox"
      tabIndex={0}
      aria-label={label}
      aria-activedescendant={focused && active >= 0 ? `${idBase}-${active}` : undefined}
      onKeyDown={onKeyDown}
      onFocus={onFocus}
      onBlur={() => setFocused(false)}
      className={`overflow-auto border border-line bg-white ${className}`}
    >
      <div role="presentation" className="relative w-full" style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((row) => {
          const item = items[row.index];
          const selected = getKey(item) === selectedKey;
          return (
            <div
              key={row.key}
              id={`${idBase}-${row.index}`}
              role="option"
              aria-selected={selected}
              data-index={row.index}
              ref={virtualizer.measureElement}
              onClick={() => {
                setActive(row.index);
                onSelect(item);
              }}
              className="absolute left-0 top-0 w-full cursor-pointer"
              style={{ transform: `translateY(${row.start}px)` }}
            >
              {renderItem(item, { selected, active: focused && row.index === active })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Shared row chrome: accent left border when selected, gray when under the keyboard cursor. */
export function rowClass({ selected, active }: RowState): string {
  return [
    "border-b border-l-[3px] border-b-line px-3 py-2",
    selected ? "border-l-accent" : "border-l-transparent",
    active ? "bg-hover" : "hover:bg-hover",
  ].join(" ");
}
