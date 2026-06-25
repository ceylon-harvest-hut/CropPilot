import { useEffect, useState } from "react";
import { ApiError } from "./api/client";
import { chunkText, commitChunks, getLabOptions, loadDocument } from "./api/lab";
import type {
  ChunkItem,
  ChunkResponse,
  CommitResponse,
  DocumentItem,
  LabOptions,
  LoadResponse,
} from "./api/types";

type Step = 1 | 2 | 3 | 4;

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

export default function LabPanel() {
  const [step, setStep] = useState<Step>(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [options, setOptions] = useState<LabOptions>({
    loaders: ["text"],
    chunkers: ["section", "recursive"],
    embedders: ["fast"],
  });

  // Step 1 inputs (preserved on back)
  const [sourceUri, setSourceUri] = useState("");
  const [cropName, setCropName] = useState("Pepper");
  const [selectedLoader, setSelectedLoader] = useState("text");

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
    if (step === 4) {
      setCommitResult(null);
      setStep(3);
    } else if (step === 3) {
      setStep(2);
    } else if (step === 2) {
      setStep(1);
    }
  }

  async function handleLoad() {
    setError(null);
    setLoading(true);
    try {
      const result = await loadDocument({ source_uri: sourceUri, loader: selectedLoader });
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

  async function handleCommit() {
    setError(null);
    setLoading(true);
    try {
      const result = await commitChunks({
        source_uri: loadResult!.source_uri,
        crop_name: cropName,
        chunks: reviewChunks,
        embedder: selectedEmbedder,
      });
      setCommitResult(result);
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
  }

  return (
    <section className="panel">
      <h2>Ingestion Lab</h2>
      <StepIndicator current={step} />

      {error && <p className="error">{error}</p>}

      {/* ── Step 1: Load ── */}
      {step === 1 && (
        <div className="lab-step-body">
          <h3 className="lab-step-title">Load Document</h3>
          <label>
            Source URI (server-side path)
            <input
              type="text"
              value={sourceUri}
              onChange={(e) => setSourceUri(e.target.value)}
              placeholder="/path/to/document.txt"
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
            <select value={selectedLoader} onChange={(e) => setSelectedLoader(e.target.value)}>
              {options.loaders.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </label>
          <div className="lab-step-actions">
            <span />
            <button type="button" onClick={handleLoad} disabled={loading || !sourceUri}>
              {loading ? "Loading…" : "Load →"}
            </button>
          </div>
        </div>
      )}

      {/* ── Step 2: Chunk ── */}
      {step === 2 && loadResult && (
        <div className="lab-step-body">
          <h3 className="lab-step-title">Chunk Document</h3>

          <details className="doc-preview-accordion">
            <summary>
              Loaded document — {loadResult.char_count.toLocaleString()} chars,{" "}
              {loadResult.line_count.toLocaleString()} lines ({documents.length} part{documents.length !== 1 ? "s" : ""})
            </summary>
            <div className="lab-result-card">
              <div className="lab-meta">
                <span><strong>Type:</strong> {loadResult.media_type}</span>
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

          <label>
            Chunker
            <select value={selectedChunker} onChange={(e) => setSelectedChunker(e.target.value)}>
              {options.chunkers.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
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
        </div>
      )}

      {/* ── Step 3: Review ── */}
      {step === 3 && chunkResult && (
        <div className="lab-step-body">
          <h3 className="lab-step-title">
            Review Chunks
            <span className="count"> ({reviewChunks.length} of {chunkResult.chunk_count})</span>
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
              onClick={() => { setError(null); setStep(4); }}
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
              <div className="lab-step-actions">
                <button type="button" className="btn-back" onClick={goBack}>← Back</button>
                <button type="button" onClick={handleCommit} disabled={loading}>
                  {loading ? "Saving…" : "Save to DB"}
                </button>
              </div>
            </>
          ) : (
            <div className="lab-result-card success">
              <p><strong>Saved successfully.</strong></p>
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
    </section>
  );
}
