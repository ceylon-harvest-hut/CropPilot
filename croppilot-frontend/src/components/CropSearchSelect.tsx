import { useEffect, useRef, useState } from "react";
import type { CropItem } from "../api/types";

interface CropSearchSelectProps {
  crops: CropItem[];
  value: string;
  onChange: (name: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function CropSearchSelect({
  crops,
  value,
  onChange,
  disabled = false,
  placeholder = "Search crops…",
}: CropSearchSelectProps) {
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Keep the text input in sync when the parent resets value externally
  useEffect(() => {
    setQuery(value);
  }, [value]);

  const filtered =
    query.trim() === "" || query === value
      ? crops
      : crops.filter((c) => {
          const q = query.toLowerCase();
          return (
            c.name.toLowerCase().includes(q) ||
            (c.botanical_name?.toLowerCase().includes(q) ?? false)
          );
        });

  function handleSelect(name: string) {
    onChange(name);
    setQuery(name);
    setOpen(false);
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    setQuery(e.target.value);
    onChange(""); // clear selection while typing
    setOpen(true);
  }

  function handleBlur(e: React.FocusEvent<HTMLDivElement>) {
    // Only close if focus leaves the whole container
    if (!containerRef.current?.contains(e.relatedTarget as Node)) {
      setOpen(false);
      // If nothing selected and query is not an exact match, reset
      if (!crops.find((c) => c.name === value)) {
        setQuery(value);
      }
    }
  }

  return (
    <div
      className="crop-search-select"
      ref={containerRef}
      onBlur={handleBlur}
    >
      <input
        type="text"
        className="crop-search-select__input"
        value={query}
        onChange={handleInputChange}
        onFocus={() => setOpen(true)}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        aria-haspopup="listbox"
        aria-expanded={open}
      />
      {open && filtered.length > 0 && (
        <ul className="crop-search-select__dropdown" role="listbox">
          {filtered.map((crop) => (
            <li
              key={crop.crop_id}
              className={`crop-search-select__option${crop.name === value ? " crop-search-select__option--selected" : ""}`}
              role="option"
              aria-selected={crop.name === value}
              onMouseDown={(e) => {
                // Use mousedown so blur doesn't fire before click
                e.preventDefault();
                handleSelect(crop.name);
              }}
            >
              <span className="crop-search-select__name">{crop.name}</span>
              {crop.botanical_name && (
                <span className="crop-search-select__botanical">
                  {crop.botanical_name}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
      {open && filtered.length === 0 && (
        <div className="crop-search-select__empty">No crops match</div>
      )}
    </div>
  );
}
