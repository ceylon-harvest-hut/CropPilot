import { useState } from "react";
import { ApiError } from "./api/client";
import { listChunks, listCrops, listSources } from "./api/debug";
import { askQuestion } from "./api/inference";
import { ingestDocument } from "./api/ingestion";
import type {
  AskResponse,
  ChunkListResponse,
  CropListResponse,
  IngestResponse,
  SourceListResponse,
  StoredChunk,
} from "./api/types";
import LabPanel from "./LabPanel";
import "./App.css";

type ActiveTab = "lab" | "ingest" | "ask" | "debug";

const DEBUG_PAGE_SIZE = 20;

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status.toLowerCase()}`}>{status}</span>;
}

interface PaginationBarProps {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (offset: number) => void;
  disabled?: boolean;
}

function PaginationBar({ total, limit, offset, onPageChange, disabled = false }: PaginationBarProps) {
  if (total === 0) {
    return null;
  }

  const start = offset + 1;
  const end = Math.min(offset + limit, total);
  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;

  return (
    <div className="debug-pagination">
      <span className="debug-pagination-info">
        Showing {start}–{end} of {total}
      </span>
      <div className="debug-pagination-controls">
        <button
          type="button"
          className="debug-pagination-btn"
          disabled={disabled || !hasPrev}
          onClick={() => onPageChange(offset - limit)}
        >
          Previous
        </button>
        <button
          type="button"
          className="debug-pagination-btn"
          disabled={disabled || !hasNext}
          onClick={() => onPageChange(offset + limit)}
        >
          Next
        </button>
      </div>
    </div>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("lab");

  // Ingest state
  const [sourceUri, setSourceUri] = useState("");
  const [cropName, setCropName] = useState("Pepper");
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);

  // Ask state
  const [question, setQuestion] = useState("What are pepper varieties?");
  const [askCrop, setAskCrop] = useState("Pepper");
  const [askResult, setAskResult] = useState<AskResponse | null>(null);

  // Debug state
  const [debugCropFilter, setDebugCropFilter] = useState("");
  const [debugSourceFilter, setDebugSourceFilter] = useState("");
  const [chunksData, setChunksData] = useState<ChunkListResponse | null>(null);
  const [sourcesData, setSourcesData] = useState<SourceListResponse | null>(null);
  const [cropsData, setCropsData] = useState<CropListResponse | null>(null);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<"ingest" | "ask" | "debug" | null>(null);

  async function handleIngest() {
    setError(null);
    setLoading("ingest");
    try {
      const result = await ingestDocument({ source_uri: sourceUri, crop_name: cropName });
      setIngestResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ingest failed");
    } finally {
      setLoading(null);
    }
  }

  async function handleAsk() {
    setError(null);
    setLoading("ask");
    try {
      const result = await askQuestion({ question, crop_name: askCrop || null });
      setAskResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ask failed");
    } finally {
      setLoading(null);
    }
  }

  async function loadChunksPage(offset: number) {
    const chunks = await listChunks({
      crop_name: debugCropFilter || undefined,
      source_uri: debugSourceFilter || undefined,
      limit: DEBUG_PAGE_SIZE,
      offset,
    });
    setChunksData(chunks);
    setSelectedChunkId(null);
  }

  async function loadSourcesPage(offset: number) {
    const sources = await listSources({
      crop_name: debugCropFilter || undefined,
      limit: DEBUG_PAGE_SIZE,
      offset,
    });
    setSourcesData(sources);
  }

  async function handleDebugLoad() {
    setError(null);
    setLoading("debug");
    try {
      const [chunks, sources, crops] = await Promise.all([
        listChunks({
          crop_name: debugCropFilter || undefined,
          source_uri: debugSourceFilter || undefined,
          limit: DEBUG_PAGE_SIZE,
          offset: 0,
        }),
        listSources({
          crop_name: debugCropFilter || undefined,
          limit: DEBUG_PAGE_SIZE,
          offset: 0,
        }),
        listCrops(),
      ]);
      setChunksData(chunks);
      setSourcesData(sources);
      setCropsData(crops);
      setSelectedChunkId(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Debug load failed");
    } finally {
      setLoading(null);
    }
  }

  async function handleChunkPageChange(newOffset: number) {
    setError(null);
    setLoading("debug");
    try {
      await loadChunksPage(newOffset);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load chunks");
    } finally {
      setLoading(null);
    }
  }

  async function handleSourcePageChange(newOffset: number) {
    setError(null);
    setLoading("debug");
    try {
      await loadSourcesPage(newOffset);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load sources");
    } finally {
      setLoading(null);
    }
  }

  const selectedChunk: StoredChunk | null =
    chunksData?.chunks.find((c) => c.chunk_id === selectedChunkId) ?? null;

  return (
    <main className={`app${activeTab === "lab" ? " app-lab" : ""}${activeTab === "debug" ? " app-debug" : ""}`}>
      <header className="app-navbar">
        <h1 className="app-logo">CropPilot</h1>
        <nav className="tabs">
          {(["lab", "ingest", "ask", "debug"] as ActiveTab[]).map((tab) => (
            <button
              key={tab}
              type="button"
              className={`tab-btn${activeTab === tab ? " active" : ""}`}
              onClick={() => { setActiveTab(tab); setError(null); }}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </header>

      {error && activeTab !== "lab" && activeTab !== "debug" && (
        <p className="error app-error">{error}</p>
      )}

      {activeTab === "lab" && <LabPanel />}

      {activeTab === "ingest" && (
        <section className="panel app-content-panel">
          <h2>Ingest Document</h2>
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
          <button type="button" onClick={handleIngest} disabled={loading !== null || !sourceUri}>
            {loading === "ingest" ? "Ingesting…" : "Ingest"}
          </button>
          {ingestResult && (
            <pre className="result">{JSON.stringify(ingestResult, null, 2)}</pre>
          )}
        </section>
      )}

      {activeTab === "ask" && (
        <section className="panel app-content-panel">
          <h2>Ask a Question</h2>
          <label>
            Crop name (optional filter)
            <input
              type="text"
              value={askCrop}
              onChange={(e) => setAskCrop(e.target.value)}
              placeholder="e.g. Pepper"
            />
          </label>
          <label>
            Question
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={3}
            />
          </label>
          <button type="button" onClick={handleAsk} disabled={loading !== null || !question}>
            {loading === "ask" ? "Asking…" : "Ask"}
          </button>
          {askResult && (
            <div className="result">
              <p className="answer">{askResult.answer}</p>
              {askResult.sources.length > 0 && (
                <ul className="sources">
                  {askResult.sources.map((source) => (
                    <li key={source.chunk_id}>
                      <strong>{source.section_name}</strong>
                      <p>{source.text_preview}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </section>
      )}

      {activeTab === "debug" && (
        <>
          <div className="debug-toolbar">
            <div className="debug-toolbar-fields">
              <label className="debug-toolbar-field">
                <span className="debug-toolbar-label">Crop</span>
                <input
                  type="text"
                  value={debugCropFilter}
                  onChange={(e) => setDebugCropFilter(e.target.value)}
                  placeholder="e.g. Pepper"
                />
              </label>
              <label className="debug-toolbar-field">
                <span className="debug-toolbar-label">Source URI</span>
                <input
                  type="text"
                  value={debugSourceFilter}
                  onChange={(e) => setDebugSourceFilter(e.target.value)}
                  placeholder="e.g. pepper.txt"
                />
              </label>
            </div>
            <button
              type="button"
              className="debug-apply-btn"
              onClick={handleDebugLoad}
              disabled={loading === "debug"}
            >
              <span className="debug-apply-icon" aria-hidden="true">↻</span>
              {loading === "debug" ? "Loading…" : "Apply Filters"}
            </button>
          </div>

          {error && <p className="error debug-error">{error}</p>}

          <section className="debug-explorer">
            <aside className="debug-explorer-sidebar">
              <div className="debug-card">
                <header className="debug-card-header">
                  <h3>Crops</h3>
                  {cropsData && <span className="debug-card-count">{cropsData.total}</span>}
                </header>
                <div className="debug-card-body">
                  {!cropsData ? (
                    <p className="debug-placeholder">Apply filters to load crops.</p>
                  ) : cropsData.crops.length === 0 ? (
                    <p className="empty">No crops found.</p>
                  ) : (
                    <table className="debug-table debug-table-compact">
                      <thead>
                        <tr><th>ID</th><th>Name</th><th>Botanical</th></tr>
                      </thead>
                      <tbody>
                        {cropsData.crops.map((c) => (
                          <tr key={c.crop_id}>
                            <td>{c.crop_id}</td>
                            <td>{c.name}</td>
                            <td>{c.botanical_name ?? <em className="muted">—</em>}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              <div className="debug-card">
                <header className="debug-card-header">
                  <h3>Sources</h3>
                  {sourcesData && <span className="debug-card-count">{sourcesData.total}</span>}
                </header>
                <div className="debug-card-body">
                  {!sourcesData ? (
                    <p className="debug-placeholder">Apply filters to load sources.</p>
                  ) : sourcesData.sources.length === 0 ? (
                    <p className="empty">No sources found.</p>
                  ) : (
                    <>
                      <div className="debug-table-scroll">
                        <table className="debug-table debug-table-compact">
                          <thead>
                            <tr><th>ID</th><th>Origin URL</th><th>Status</th><th>Crops</th></tr>
                          </thead>
                          <tbody>
                            {sourcesData.sources.map((s) => (
                              <tr key={s.source_id}>
                                <td>{s.source_id}</td>
                                <td className="monospace">{s.origin_url}</td>
                                <td><StatusBadge status={s.status} /></td>
                                <td>{s.crop_names.join(", ")}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <PaginationBar
                        total={sourcesData.total}
                        limit={sourcesData.limit}
                        offset={sourcesData.offset}
                        onPageChange={handleSourcePageChange}
                        disabled={loading === "debug"}
                      />
                    </>
                  )}
                </div>
              </div>
            </aside>

            <div className="debug-explorer-main">
              <div className="debug-card debug-chunks-card">
                <header className="debug-card-header">
                  <h3>Chunks</h3>
                  {chunksData && <span className="debug-card-count">{chunksData.total}</span>}
                </header>

                {!chunksData ? (
                  <p className="debug-placeholder debug-chunks-placeholder">
                    Apply filters to explore indexed chunks.
                  </p>
                ) : chunksData.chunks.length === 0 ? (
                  <p className="empty debug-chunks-placeholder">No chunks found.</p>
                ) : (
                  <>
                    <div className="debug-chunks-table-wrap">
                      <table className="debug-table debug-chunks-table">
                        <thead>
                          <tr><th>ID</th><th>Crop</th><th>Section</th><th>Pg</th></tr>
                        </thead>
                        <tbody>
                          {chunksData.chunks.map((c) => (
                            <tr
                              key={c.chunk_id}
                              className={selectedChunkId === c.chunk_id ? "debug-row-selected" : ""}
                              onClick={() => setSelectedChunkId(c.chunk_id)}
                            >
                              <td className="debug-chunk-id" title={c.chunk_id}>
                                {c.chunk_id.slice(0, 8)}…
                              </td>
                              <td>{c.crop_tag}</td>
                              <td>{c.section_name}</td>
                              <td>{c.page_number}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <PaginationBar
                      total={chunksData.total}
                      limit={chunksData.limit}
                      offset={chunksData.offset}
                      onPageChange={handleChunkPageChange}
                      disabled={loading === "debug"}
                    />

                    <div className="debug-chunk-detail">
                      <header className="debug-chunk-detail-header">
                        <span className="debug-chunk-detail-title">Chunk Preview</span>
                        {selectedChunk && (
                          <span className="debug-chunk-detail-meta">
                            {selectedChunk.crop_tag} · {selectedChunk.section_name} · pg {selectedChunk.page_number}
                          </span>
                        )}
                      </header>
                      {selectedChunk ? (
                        <pre className="debug-chunk-detail-text">{selectedChunk.text_preview}</pre>
                      ) : (
                        <p className="debug-placeholder">Select a chunk row to view its text.</p>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          </section>
        </>
      )}
    </main>
  );
}

export default App;
