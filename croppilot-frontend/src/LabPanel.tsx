import { useEffect, useLayoutEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { ApiError } from "./api/client";
import { chunkText, checkSourceExists, commitChunks, getLabOptions, loadDocument } from "./api/lab";
import type {
  ChunkerOption,
  ChunkItem,
  ChunkResponse,
  CommitResponse,
  DocumentItem,
  LabOptions,
  LoadResponse,
  SourceExistsResponse,
  SourceType,
} from "./api/types";

type Step = 1 | 2 | 3 | 4;

interface PendingSelection {
  start: number;
  end: number;
  text: string;
  page: number;
}

/** Map each <pre> text node to its start offset in the combined document string. */
function buildPreTextIndex(root: HTMLElement): Map<Text, number> {
  const nodeOffsets = new Map<Text, number>();
  let offset = 0;
  const pres = root.querySelectorAll("pre");
  pres.forEach((pre, i) => {
    if (i > 0) offset += 2; // "\n\n" between parts
    const tn = pre.firstChild;
    if (tn?.nodeType === Node.TEXT_NODE) {
      nodeOffsets.set(tn as Text, offset);
      offset += tn.textContent?.length ?? 0;
    }
  });
  return nodeOffsets;
}

function textNodeOffset(
  nodeOffsets: Map<Text, number>,
  container: Node,
  offset: number,
): number | null {
  if (container.nodeType !== Node.TEXT_NODE) return null;
  const base = nodeOffsets.get(container as Text);
  if (base === undefined) return null;
  return base + offset;
}

function renderHighlightedText(
  text: string,
  globalStart: number,
  sel: PendingSelection | null,
  markRef?: RefObject<HTMLElement | null>,
): ReactNode {
  if (!sel) return text;

  const globalEnd = globalStart + text.length;
  if (sel.end <= globalStart || sel.start >= globalEnd) return text;

  const localStart = Math.max(0, sel.start - globalStart);
  const localEnd = Math.min(text.length, sel.end - globalStart);
  const attachRef = markRef && sel.start >= globalStart && sel.start < globalEnd;

  return (
    <>
      {text.slice(0, localStart)}
      <mark className="manual-selection-highlight" ref={attachRef ? markRef : undefined}>
        {text.slice(localStart, localEnd)}
      </mark>
      {text.slice(localEnd)}
    </>
  );
}

function StepIndicator({ current }: { current: Step }) {
  const labels: [Step, string][] = [
    [1, "Load"],
    [2, "Chunk"],
    [3, "Review"],
    [4, "Save"],
  ];
  return (
    <div className="stepper">
      {labels.map(([step, label], idx) => (
        <div key={step} className="stepper-item">
          <div
            className={[
              "stepper-circle",
              current > step ? "done" : "",
              current === step ? "active" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {step}
          </div>
          <span className={`stepper-label${current === step ? " active" : ""}`}>{label}</span>
          {idx < labels.length - 1 && (
            <div className={`stepper-line${current > step ? " done" : ""}`} />
          )}
        </div>
      ))}
    </div>
  );
}

// ── Manual Chunk Editor ──────────────────────────────────────────────────────

interface ManualChunkEditorProps {
  documents: DocumentItem[];
  reviewChunks: ChunkItem[];
  setReviewChunks: React.Dispatch<React.SetStateAction<ChunkItem[]>>;
  chunkers: ChunkerOption[];
  selectedChunker: string;
  onChunkerChange: (name: string) => void;
}

function ManualChunkEditor({
  documents,
  reviewChunks,
  setReviewChunks,
  chunkers,
  selectedChunker,
  onChunkerChange,
}: ManualChunkEditorProps) {
  const [pendingSelection, setPendingSelection] = useState<PendingSelection | null>(null);
  const [sectionName, setSectionName] = useState("");
  const [pageNumber, setPageNumber] = useState(0);
  const docRef = useRef<HTMLDivElement>(null);
  const docPanelRef = useRef<HTMLDivElement>(null);
  const highlightRef = useRef<HTMLElement>(null);
  const floaterRef = useRef<HTMLDivElement>(null);

  const multiPart = documents.length > 1;
  const fullText = documents.map((d) => d.text).join("\n\n");

  function updateFloaterPosition() {
    const mark = highlightRef.current;
    const panel = docPanelRef.current;
    const scrollEl = docRef.current;
    const floater = floaterRef.current;
    if (!mark || !panel || !scrollEl || !floater) return;

    const markRect = mark.getBoundingClientRect();
    const panelRect = panel.getBoundingClientRect();
    const scrollRect = scrollEl.getBoundingClientRect();
    const floaterW = floater.offsetWidth;
    const floaterH = floater.offsetHeight;
    const gap = 8;

    const spaceBelow = scrollRect.bottom - markRect.bottom;
    const spaceAbove = markRect.top - scrollRect.top;

    let top: number;
    if (spaceBelow >= floaterH + gap) {
      top = markRect.bottom - panelRect.top + gap;
    } else if (spaceAbove >= floaterH) {
      // Bottom of floater aligns with bottom of selection
      top = markRect.bottom - panelRect.top - floaterH;
    } else if (spaceAbove >= spaceBelow) {
      top = markRect.bottom - panelRect.top - floaterH;
    } else {
      top = markRect.bottom - panelRect.top + gap;
    }

    // Clamp within the visible document scroll viewport
    const viewTop = scrollRect.top - panelRect.top + gap;
    const viewBottom = scrollRect.bottom - panelRect.top - gap;
    top = Math.max(viewTop, Math.min(top, viewBottom - floaterH));

    let left = markRect.left - panelRect.left;
    left = Math.max(gap, Math.min(left, panel.clientWidth - floaterW - gap));

    floater.style.top = `${top}px`;
    floater.style.left = `${left}px`;

    // Nudge document scroll so the floater is fully visible
    requestAnimationFrame(() => {
      const floaterRect = floater.getBoundingClientRect();
      const currentScrollRect = scrollEl.getBoundingClientRect();
      if (floaterRect.bottom > currentScrollRect.bottom) {
        scrollEl.scrollTop += floaterRect.bottom - currentScrollRect.bottom + gap;
      } else if (floaterRect.top < currentScrollRect.top) {
        scrollEl.scrollTop -= currentScrollRect.top - floaterRect.top + gap;
      }
    });
  }

  useLayoutEffect(() => {
    if (!pendingSelection) return;
    updateFloaterPosition();
  }, [pendingSelection, sectionName]);

  useEffect(() => {
    if (!pendingSelection) return;

    const scrollEl = docRef.current;
    const onReposition = () => updateFloaterPosition();

    scrollEl?.addEventListener("scroll", onReposition);
    window.addEventListener("resize", onReposition);
    return () => {
      scrollEl?.removeEventListener("scroll", onReposition);
      window.removeEventListener("resize", onReposition);
    };
  }, [pendingSelection]);

  useEffect(() => {
    if (!pendingSelection) return;

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") clearPendingSelection();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [pendingSelection]);

  function clearPendingSelection() {
    setPendingSelection(null);
    window.getSelection()?.removeAllRanges();
  }

  function handleMouseUp() {
    if (!docRef.current) return;
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) return;

    const range = sel.getRangeAt(0);
    if (!docRef.current.contains(range.commonAncestorContainer)) return;

    const nodeOffsets = buildPreTextIndex(docRef.current);
    const start = textNodeOffset(nodeOffsets, range.startContainer, range.startOffset);
    const end = textNodeOffset(nodeOffsets, range.endContainer, range.endOffset);
    if (start === null || end === null || end <= start) return;

    const text = fullText.slice(start, end);
    if (!text.trim()) return;

    let page = 0;
    if (multiPart) {
      const partEls = docRef.current.querySelectorAll<HTMLElement>("[data-page]");
      for (const el of partEls) {
        if (el.contains(range.startContainer)) {
          page = parseInt(el.dataset.page ?? "0", 10);
          break;
        }
      }
    }

    setPendingSelection({ start, end, text, page });
    setPageNumber(page);
    setSectionName(`chunk_${reviewChunks.length + 1}`);
    sel.removeAllRanges();
  }

  function addChunk() {
    if (!pendingSelection?.text.trim()) return;
    const chunk: ChunkItem = {
      index: reviewChunks.length,
      text: pendingSelection.text,
      section_name: sectionName.trim() || `chunk_${reviewChunks.length + 1}`,
      page_number: pageNumber,
      char_count: pendingSelection.text.length,
    };
    setReviewChunks((prev) => [...prev, chunk]);
    clearPendingSelection();
  }

  function removeChunk(i: number) {
    setReviewChunks((prev) => prev.filter((_, idx) => idx !== i));
  }

  function renderDocumentBody(markRef?: RefObject<HTMLElement | null>) {
    if (multiPart) {
      let globalOffset = 0;
      return documents.map((doc, i) => {
        const page = typeof doc.metadata.page === "number" ? doc.metadata.page : i;
        const partStart = globalOffset;
        const content = renderHighlightedText(doc.text, partStart, pendingSelection, markRef);
        globalOffset += doc.text.length + (i < documents.length - 1 ? 2 : 0);
        return (
          <div key={i} data-page={page}>
            <div className="manual-doc-part-label">Part {i + 1}</div>
            <pre>{content}</pre>
          </div>
        );
      });
    }
    return <pre>{renderHighlightedText(fullText, 0, pendingSelection, markRef)}</pre>;
  }

  return (
    <>
      <div className="lab-toolbar">
        <div className="lab-toolbar-primary">
          <label className="lab-toolbar-field">
            <span className="lab-toolbar-label">Chunker</span>
            <select value={selectedChunker} onChange={(e) => onChunkerChange(e.target.value)}>
              {chunkers.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <p className="lab-toolbar-tip">
            Select text in the document. Enter a section name and click{" "}
            <strong>Add chunk</strong>. Created chunks appear on the right.
          </p>
        </div>
      </div>

      <div className="lab-workspace lab-workspace-2col">
        <main className="workspace-col workspace-document">
          <div
            ref={docPanelRef}
            className="workspace-panel workspace-panel-fill workspace-document-panel"
          >
            <div className="workspace-panel-header">Document</div>
            <div
              ref={docRef}
              className="manual-doc-text"
              onMouseUp={handleMouseUp}
            >
              {renderDocumentBody(highlightRef)}
            </div>

            {pendingSelection && (
              <div
                ref={floaterRef}
                className="selection-floater"
                onMouseDown={(e) => e.preventDefault()}
              >
                <span className="selection-popup-quote">
                  &ldquo;{pendingSelection.text.slice(0, 80)}
                  {pendingSelection.text.length > 80 ? "…" : ""}&rdquo;
                </span>
                <span className="selection-popup-chars">{pendingSelection.text.length} chars</span>
                <label className="lab-toolbar-field lab-toolbar-field-inline">
                  <span className="lab-toolbar-label">Section</span>
                  <input
                    type="text"
                    value={sectionName}
                    onChange={(e) => setSectionName(e.target.value)}
                    placeholder={`chunk_${reviewChunks.length + 1}`}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === "Enter") addChunk();
                      if (e.key === "Escape") clearPendingSelection();
                    }}
                  />
                </label>
                {multiPart && (
                  <label className="lab-toolbar-field lab-toolbar-field-inline">
                    <span className="lab-toolbar-label">Page</span>
                    <input
                      type="number"
                      value={pageNumber}
                      min={0}
                      onChange={(e) => setPageNumber(Number(e.target.value))}
                    />
                  </label>
                )}
                <div className="selection-floater-actions">
                  <button type="button" className="btn-back" onClick={clearPendingSelection}>
                    Cancel
                  </button>
                  <button type="button" onClick={addChunk}>
                    Add chunk
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>

        <aside className="workspace-col workspace-chunks">
          <div className="workspace-panel workspace-panel-fill">
            <div className="workspace-panel-header">
              Chunks <span className="count">({reviewChunks.length})</span>
            </div>
            {reviewChunks.length === 0 ? (
              <p className="empty manual-empty">No chunks yet. Select text in the document.</p>
            ) : (
              <div className="manual-chunk-list">
                {reviewChunks.map((chunk, i) => (
                  <div key={chunk.index} className="manual-chunk-item">
                    <div className="manual-chunk-card-top">
                      <div className="manual-chunk-card-title">
                        <span className="manual-chunk-num">#{i + 1}</span>
                        <em className="manual-chunk-section">{chunk.section_name}</em>
                      </div>
                      <button
                        type="button"
                        className="btn-remove manual-chunk-remove"
                        onClick={() => removeChunk(i)}
                        title="Remove chunk"
                        aria-label={`Remove chunk ${i + 1}`}
                      >
                        &times;
                      </button>
                    </div>
                    <span className="manual-chunk-chars">{chunk.char_count} chars</span>
                    <p className="manual-chunk-preview">
                      {chunk.text.slice(0, 110)}{chunk.text.length > 110 ? "…" : ""}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </>
  );
}

// ── Main Lab Panel ───────────────────────────────────────────────────────────

export default function LabPanel() {
  const [step, setStep] = useState<Step>(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [options, setOptions] = useState<LabOptions>({
    source_types: ["file", "web_url"],
    loaders: [],
    chunkers: [
      { name: "section", label: "Section headers" },
      { name: "recursive", label: "Recursive (size / overlap)" },
      { name: "dea_gov_lk", label: "DEA gov.lk crop page" },
      { name: "manual", label: "Manual selection" },
    ],
    embedders: ["fast"],
  });

  // Step 1 inputs (preserved on back)
  const [sourceUri, setSourceUri] = useState("");
  const [cropName, setCropName] = useState("Pepper");
  const [sourceType, setSourceType] = useState<SourceType | "">("");
  const [selectedLoader, setSelectedLoader] = useState("");

  // Step 2 inputs (preserved on back)
  const [selectedChunker, setSelectedChunker] = useState("section");
  const [chunkSize, setChunkSize] = useState(500);
  const [chunkOverlap, setChunkOverlap] = useState(50);

  // Pipeline results
  const [loadResult, setLoadResult] = useState<LoadResponse | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [chunkResult, setChunkResult] = useState<ChunkResponse | null>(null);
  const [reviewChunks, setReviewChunks] = useState<ChunkItem[]>([]);
  const [selectedEmbedder, setSelectedEmbedder] = useState("fast");
  const [commitResult, setCommitResult] = useState<CommitResponse | null>(null);
  const [existingSource, setExistingSource] = useState<SourceExistsResponse | null>(null);
  const [showReplaceConfirm, setShowReplaceConfirm] = useState(false);

  useEffect(() => {
    getLabOptions()
      .then(setOptions)
      .catch(() => {});
  }, []);

  function setErr(msg: unknown) {
    setError(msg instanceof ApiError ? msg.message : String(msg));
  }

  function goBack() {
    setError(null);
    setShowReplaceConfirm(false);
    setExistingSource(null);
    if (step === 4) {
      setCommitResult(null);
      setStep(3);
    } else if (step === 3) {
      setStep(2);
    } else if (step === 2) {
      setStep(1);
    }
  }

  const availableLoaders = sourceType
    ? options.loaders.filter((loader) => loader.source_types.includes(sourceType))
    : [];

  function handleSourceTypeChange(nextType: SourceType | "") {
    setSourceType(nextType);
    setSelectedLoader("");
    setError(null);
  }

  function handleChunkerChange(name: string) {
    setSelectedChunker(name);
    // Clear any existing chunks/result when switching strategy
    setReviewChunks([]);
    setChunkResult(null);
  }

  async function handleLoad() {
    if (!sourceType || !selectedLoader) return;
    setError(null);
    setLoading(true);
    try {
      const result = await loadDocument({
        source_uri: sourceUri,
        source_type: sourceType,
        loader: selectedLoader,
      });
      setLoadResult(result);
      setDocuments(result.documents);
      setChunkResult(null);
      setReviewChunks([]);
      setCommitResult(null);
      setStep(2);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleChunk() {
    if (!loadResult) return;
    setError(null);
    setLoading(true);
    try {
      const result = await chunkText({
        documents,
        crop_name: cropName,
        chunker: selectedChunker,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      });
      setChunkResult(result);
      setReviewChunks(result.chunks);
      setCommitResult(null);
      setStep(3);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  }

  function removeChunk(i: number) {
    setReviewChunks((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function handleCommit(replaceExisting = false) {
    if (!loadResult) return;
    setError(null);
    setLoading(true);
    try {
      if (!replaceExisting) {
        const existsInfo = await checkSourceExists(loadResult.source_uri);
        if (existsInfo.exists) {
          setExistingSource(existsInfo);
          setShowReplaceConfirm(true);
          return;
        }
      }

      const result = await commitChunks({
        source_uri: loadResult.source_uri,
        crop_name: cropName,
        chunks: reviewChunks,
        embedder: selectedEmbedder,
        replace_existing: replaceExisting,
      });
      setCommitResult(result);
      setShowReplaceConfirm(false);
      setExistingSource(null);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  }

  function handleStartOver() {
    setStep(1);
    setError(null);
    setLoadResult(null);
    setDocuments([]);
    setChunkResult(null);
    setReviewChunks([]);
    setCommitResult(null);
    setExistingSource(null);
    setShowReplaceConfirm(false);
  }

  const isManual = selectedChunker === "manual";

  return (
    <div className="lab-shell">
      <div className={`lab-stepper-strip${step === 2 && isManual ? " lab-stepper-strip-workspace" : ""}`}>
        <div className="lab-stepper-row">
          {step === 2 && isManual ? (
            <button type="button" className="btn-back lab-stepper-nav" onClick={goBack}>
              ← Back
            </button>
          ) : (
            <span className="lab-stepper-nav-spacer" aria-hidden="true" />
          )}
          <StepIndicator current={step} />
          {step === 2 && isManual ? (
            <button
              type="button"
              className="lab-stepper-nav lab-stepper-next"
              onClick={() => { setError(null); setStep(3); }}
              disabled={reviewChunks.length === 0}
            >
              Review ({reviewChunks.length}) →
            </button>
          ) : (
            <span className="lab-stepper-nav-spacer" aria-hidden="true" />
          )}
        </div>
      </div>

      {error && <p className="error lab-error">{error}</p>}

      <div className="lab-content">
      {/* ── Step 1: Load ── */}
      {step === 1 && (
        <div className="lab-step-body">
          <h3 className="lab-step-title">Load Document</h3>
          <label>
            Source type
            <select
              value={sourceType}
              onChange={(e) => handleSourceTypeChange(e.target.value as SourceType | "")}
            >
              <option value="">Select source type…</option>
              {options.source_types.map((type) => (
                <option key={type} value={type}>
                  {type === "file" ? "File" : "Web URL"}
                </option>
              ))}
            </select>
          </label>
          <label>
            Source URI
            <input
              type="text"
              value={sourceUri}
              onChange={(e) => setSourceUri(e.target.value)}
              placeholder={
                sourceType === "web_url"
                  ? "https://example.com/crop-guide"
                  : "/path/to/document.txt"
              }
            />
          </label>
          <label>
            Crop name
            <input
              type="text"
              value={cropName}
              onChange={(e) => setCropName(e.target.value)}
            />
          </label>
          <label>
            Loader
            <select
              value={selectedLoader}
              onChange={(e) => setSelectedLoader(e.target.value)}
              disabled={!sourceType}
            >
              <option value="">
                {sourceType ? "Select loader…" : "Choose source type first"}
              </option>
              {availableLoaders.map((loader) => (
                <option key={loader.name} value={loader.name}>
                  {loader.label}
                </option>
              ))}
            </select>
          </label>
          <div className="lab-step-actions">
            <span />
            <button
              type="button"
              onClick={handleLoad}
              disabled={loading || !sourceUri || !sourceType || !selectedLoader}
            >
              {loading ? "Loading…" : "Load →"}
            </button>
          </div>
        </div>
      )}

      {/* ── Step 2: Chunk ── */}
      {step === 2 && loadResult && (
        <div className="lab-step-body">
          {isManual ? (
            <ManualChunkEditor
              documents={documents}
              reviewChunks={reviewChunks}
              setReviewChunks={setReviewChunks}
              chunkers={options.chunkers}
              selectedChunker={selectedChunker}
              onChunkerChange={handleChunkerChange}
            />
          ) : (
            <>
              <h3 className="lab-step-title">Chunk Document</h3>

              <label>
                Chunker
                <select value={selectedChunker} onChange={(e) => handleChunkerChange(e.target.value)}>
                  {options.chunkers.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </label>

              <details className="doc-preview-accordion">
                <summary>
                  Loaded document — {loadResult.char_count.toLocaleString()} chars,{" "}
                  {loadResult.line_count.toLocaleString()} lines ({documents.length} part{documents.length !== 1 ? "s" : ""})
                </summary>
                <div className="lab-result-card">
                  <div className="lab-meta">
                    <span><strong>Type:</strong> {loadResult.media_type}</span>
                    <span><strong>Source kind:</strong> {loadResult.source_type}</span>
                    <span><strong>Loader:</strong> {loadResult.loader}</span>
                    <span><strong>Source:</strong> {loadResult.source_uri}</span>
                  </div>
                  <textarea
                    className="lab-text-preview"
                    readOnly
                    value={documents.map((d) => d.text).join("\n\n")}
                    rows={12}
                  />
                </div>
              </details>

              {selectedChunker === "recursive" && (
                <div className="lab-row">
                  <label>
                    Chunk size
                    <input
                      type="number"
                      value={chunkSize}
                      min={50}
                      max={4000}
                      onChange={(e) => setChunkSize(Number(e.target.value))}
                    />
                  </label>
                  <label>
                    Overlap
                    <input
                      type="number"
                      value={chunkOverlap}
                      min={0}
                      max={500}
                      onChange={(e) => setChunkOverlap(Number(e.target.value))}
                    />
                  </label>
                </div>
              )}

              <div className="lab-step-actions">
                <button type="button" className="btn-back" onClick={goBack}>← Back</button>
                <button type="button" onClick={handleChunk} disabled={loading}>
                  {loading ? "Chunking…" : "Chunk →"}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Step 3: Review ── */}
      {step === 3 && (chunkResult !== null || isManual) && (
        <div className="lab-step-body">
          <h3 className="lab-step-title">
            Review Chunks
            {chunkResult
              ? <span className="count"> ({reviewChunks.length} of {chunkResult.chunk_count})</span>
              : <span className="count"> ({reviewChunks.length})</span>
            }
          </h3>
          <p className="lab-hint">Expand any chunk to read it. Remove chunks you don't want to save.</p>

          <div className="chunk-accordion-list">
            {reviewChunks.length === 0 ? (
              <p className="empty">All chunks removed. Go back to re-chunk.</p>
            ) : (
              reviewChunks.map((chunk, i) => (
                <details key={chunk.index} className="chunk-accordion">
                  <summary>
                    <span className="chunk-meta">
                      #{i + 1} &middot; <em>{chunk.section_name}</em> &middot; {chunk.char_count} chars
                    </span>
                  </summary>
                  <div className="chunk-accordion-body">
                    <p className="chunk-text">{chunk.text}</p>
                    <button
                      type="button"
                      className="btn-remove"
                      onClick={() => removeChunk(i)}
                    >
                      Remove chunk
                    </button>
                  </div>
                </details>
              ))
            )}
          </div>

          <div className="lab-step-actions">
            <button type="button" className="btn-back" onClick={goBack}>← Back</button>
            <button
              type="button"
              onClick={() => { setError(null); setShowReplaceConfirm(false); setExistingSource(null); setStep(4); }}
              disabled={reviewChunks.length === 0}
            >
              Proceed to Save →
            </button>
          </div>
        </div>
      )}

      {/* ── Step 4: Save ── */}
      {step === 4 && (
        <div className="lab-step-body">
          <h3 className="lab-step-title">Save to Database</h3>

          {!commitResult ? (
            <>
              <label>
                Embedder
                <select
                  value={selectedEmbedder}
                  onChange={(e) => setSelectedEmbedder(e.target.value)}
                >
                  {options.embedders.map((e) => (
                    <option key={e} value={e}>{e}</option>
                  ))}
                </select>
              </label>
              <div className="lab-result-card">
                <div className="lab-meta">
                  <span><strong>Chunks:</strong> {reviewChunks.length}</span>
                  <span><strong>Crop:</strong> {cropName}</span>
                  <span><strong>Source:</strong> {loadResult?.source_uri}</span>
                </div>
              </div>

              {showReplaceConfirm && existingSource?.exists && (
                <div className="lab-replace-warning">
                  <p>
                    <strong>This source is already ingested.</strong>{" "}
                    It has {existingSource.chunk_count ?? 0} stored chunk
                    {(existingSource.chunk_count ?? 0) !== 1 ? "s" : ""}
                    {existingSource.crop_names.length > 0 && (
                      <> (crops: {existingSource.crop_names.join(", ")})</>
                    )}
                    . Saving will delete the existing vectors and replace them with your
                    current {reviewChunks.length} chunk{reviewChunks.length !== 1 ? "s" : ""}.
                  </p>
                  <div className="lab-replace-actions">
                    <button
                      type="button"
                      className="btn-back"
                      onClick={() => { setShowReplaceConfirm(false); setExistingSource(null); }}
                      disabled={loading}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="btn-danger"
                      onClick={() => handleCommit(true)}
                      disabled={loading}
                    >
                      {loading ? "Replacing…" : "Replace and save"}
                    </button>
                  </div>
                </div>
              )}

              <div className="lab-step-actions">
                <button type="button" className="btn-back" onClick={goBack}>← Back</button>
                {!showReplaceConfirm && (
                  <button type="button" onClick={() => handleCommit(false)} disabled={loading}>
                    {loading ? "Saving…" : "Save to DB"}
                  </button>
                )}
              </div>
            </>
          ) : (
            <div className="lab-result-card success">
              <p>
                <strong>
                  {commitResult.replaced ? "Replaced successfully." : "Saved successfully."}
                </strong>
              </p>
              {commitResult.replaced && (
                <p className="lab-hint">
                  Replaced {commitResult.previous_chunk_count} existing chunk
                  {commitResult.previous_chunk_count !== 1 ? "s" : ""} with{" "}
                  {commitResult.chunk_count} new chunk
                  {commitResult.chunk_count !== 1 ? "s" : ""}.
                </p>
              )}
              <div className="lab-meta">
                <span><strong>Source ID:</strong> {commitResult.source_id}</span>
                <span><strong>Chunks saved:</strong> {commitResult.chunk_count}</span>
                <span><strong>Status:</strong> {commitResult.status}</span>
              </div>
              <button type="button" className="btn-back" onClick={handleStartOver}>
                Start over
              </button>
            </div>
          )}
        </div>
      )}
      </div>
    </div>
  );
}
