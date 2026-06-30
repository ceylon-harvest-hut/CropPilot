import { useEffect, useState } from "react";
import { ApiError } from "./api/client";
import { listIndexedCrops } from "./api/crops";
import { listChunks, listCrops, listSources } from "./api/debug";
import { askQuestion, listAskTemplates } from "./api/inference";
import { askAgent } from "./api/agent";
import { ingestDocument } from "./api/ingestion";
import type {
  AskAgentResponse,
  AskResponse,
  AskTemplateName,
  ChunkListResponse,
  CropItem,
  CropListResponse,
  IngestResponse,
  PromptTemplateOption,
  SourceListResponse,
  StoredChunk,
} from "./api/types";
import CropSearchSelect from "./components/CropSearchSelect";
import LabPanel from "./LabPanel";
import "./App.css";

type ActiveTab = "lab" | "ingest" | "ask" | "ask-agent" | "debug";

const TAB_LABELS: Record<ActiveTab, string> = {
  lab: "Lab",
  ingest: "Ingest",
  ask: "Ask",
  "ask-agent": "Ask Agent",
  debug: "Debug",
};

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
  const [question, setQuestion] = useState("");
  const [askCrop, setAskCrop] = useState("");
  const [askCrops, setAskCrops] = useState<CropItem[]>([]);
  const [askTemplate, setAskTemplate] = useState<AskTemplateName>("context_only");
  const [askTemplates, setAskTemplates] = useState<PromptTemplateOption[]>([]);
  const [askResult, setAskResult] = useState<AskResponse | null>(null);

  // Ask Agent state
  const [agentQuestion, setAgentQuestion] = useState("");
  const [agentResult, setAgentResult] = useState<AskAgentResponse | null>(null);

  useEffect(() => {
    if (activeTab !== "ask") {
      return;
    }
    Promise.all([
      listAskTemplates(),
      listIndexedCrops(),
    ])
      .then(([templates, crops]) => {
        setAskTemplates(templates.templates);
        setAskTemplate(templates.default_template);
        setAskCrops(crops.crops);
      })
      .catch(() => {
        setAskTemplates([
          {
            name: "context_only",
            label: "Source documents only",
            description: "Answer strictly from retrieved source documents.",
          },
          {
            name: "hybrid",
            label: "Documents + general knowledge",
            description: "Combine source documents with general agronomic knowledge.",
          },
        ]);
      });
  }, [activeTab]);

  // Debug state
  const [debugCropFilter, setDebugCropFilter] = useState("");
  const [debugSourceFilter, setDebugSourceFilter] = useState("");
  const [chunksData, setChunksData] = useState<ChunkListResponse | null>(null);
  const [sourcesData, setSourcesData] = useState<SourceListResponse | null>(null);
  const [cropsData, setCropsData] = useState<CropListResponse | null>(null);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<"ingest" | "ask" | "ask-agent" | "debug" | null>(null);

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
      const result = await askQuestion({
        question,
        crop_name: askCrop,
        template: askTemplate,
      });
      setAskResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ask failed");
    } finally {
      setLoading(null);
    }
  }

  async function handleAskAgent() {
    setError(null);
    setLoading("ask-agent");
    try {
      const result = await askAgent({ question: agentQuestion });
      setAgentResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ask agent failed");
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
          {(["lab", "ingest", "ask", "ask-agent", "debug"] as ActiveTab[]).map((tab) => (
            <button
              key={tab}
              type="button"
              className={`tab-btn${activeTab === tab ? " active" : ""}`}
              onClick={() => { setActiveTab(tab); setError(null); }}
            >
              {TAB_LABELS[tab]}
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
            Answer mode
            <select
              value={askTemplate}
              onChange={(e) => setAskTemplate(e.target.value as AskTemplateName)}
            >
              {askTemplates.map((option) => (
                <option key={option.name} value={option.name}>
                  {option.label}
                </option>
              ))}
            </select>
            {askTemplates.find((option) => option.name === askTemplate)?.description && (
              <span className="field-hint">
                {askTemplates.find((option) => option.name === askTemplate)?.description}
              </span>
            )}
          </label>
          <label>
            Crop
            <CropSearchSelect
              crops={askCrops}
              value={askCrop}
              onChange={setAskCrop}
              disabled={loading !== null}
              placeholder={askCrops.length === 0 ? "Loading crops…" : "Search crops…"}
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
          <button type="button" onClick={handleAsk} disabled={loading !== null || !question.trim() || !askCrop}>
            {loading === "ask" ? "Asking…" : "Ask"}
          </button>
          {askResult && (
            <div className="result ask-result">
              <div className="ask-answer-block">
                <h3 className="ask-result-heading">Answer</h3>
                <p className="answer">{askResult.answer}</p>
              </div>
              {askResult.references.length > 0 && (
                <div className="ask-references-block">
                  <h3 className="ask-result-heading">References</h3>
                  <ul className="ask-references">
                    {askResult.references.map((ref) => (
                      <li key={ref.source_uri} className="ask-reference-item">
                        <strong className="ask-reference-title">{ref.title}</strong>
                        {ref.source_type === "web_url" ? (
                          <a
                            className="ask-reference-uri"
                            href={ref.source_uri}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {ref.source_uri}
                          </a>
                        ) : (
                          <p className="ask-reference-uri monospace">{ref.source_uri}</p>
                        )}
                        <p className="ask-reference-excerpt">{ref.excerpt}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {activeTab === "ask-agent" && (
        <section className="panel app-content-panel">
          <h2>Ask Agent</h2>
          <p className="field-hint">
            Graph agent with Neo4j tools. Ask in any language; the agent infers the crop from your question.
          </p>
          <label>
            Question
            <textarea
              value={agentQuestion}
              onChange={(e) => setAgentQuestion(e.target.value)}
              rows={4}
              placeholder="e.g. I have 0.5 hectare. How many Cabbage plants can I fit?"
            />
          </label>
          <button
            type="button"
            onClick={handleAskAgent}
            disabled={loading !== null || !agentQuestion.trim()}
          >
            {loading === "ask-agent" ? "Thinking…" : "Ask Agent"}
          </button>
          {agentResult && (
            <div className="result ask-result">
              <div className="ask-answer-block">
                <h3 className="ask-result-heading">Answer</h3>
                <p className="answer">{agentResult.answer}</p>
              </div>
              {agentResult.tools_used.length > 0 && (
                <div className="ask-tools-block">
                  <h3 className="ask-result-heading">Tools Used</h3>
                  <ul className="ask-tools-list">
                    {agentResult.tools_used.map((tool, index) => (
                      <li key={`${tool.name}-${index}`} className="ask-tool-item">
                        <strong className="ask-tool-name">{tool.name}</strong>
                        <pre className="ask-tool-detail monospace">
                          {JSON.stringify(tool.arguments, null, 2)}
                        </pre>
                        <p className="ask-tool-result">{tool.result}</p>
                      </li>
                    ))}
                  </ul>
                </div>
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
