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
} from "./api/types";
import LabPanel from "./LabPanel";
import "./App.css";

type ActiveTab = "lab" | "ingest" | "ask" | "debug";

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status.toLowerCase()}`}>{status}</span>;
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

  async function handleDebugLoad() {
    setError(null);
    setLoading("debug");
    try {
      const [chunks, sources, crops] = await Promise.all([
        listChunks({ crop_name: debugCropFilter || undefined, source_uri: debugSourceFilter || undefined, limit: 50 }),
        listSources({ crop_name: debugCropFilter || undefined }),
        listCrops(),
      ]);
      setChunksData(chunks);
      setSourcesData(sources);
      setCropsData(crops);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Debug load failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="app">
      <header>
        <h1>CropPilot</h1>
        <p>Ingest crop knowledge and ask questions via RAG.</p>
      </header>

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

      {error && <p className="error">{error}</p>}

      {activeTab === "lab" && <LabPanel />}

      {activeTab === "ingest" && (
        <section className="panel">
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
        <section className="panel">
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
        <section className="panel">
          <h2>Debug: Database Contents</h2>
          <div className="debug-filters">
            <label>
              Filter by crop name
              <input
                type="text"
                value={debugCropFilter}
                onChange={(e) => setDebugCropFilter(e.target.value)}
                placeholder="e.g. Pepper"
              />
            </label>
            <label>
              Filter chunks by source URI
              <input
                type="text"
                value={debugSourceFilter}
                onChange={(e) => setDebugSourceFilter(e.target.value)}
                placeholder="e.g. pepper.txt"
              />
            </label>
          </div>
          <button type="button" onClick={handleDebugLoad} disabled={loading === "debug"}>
            {loading === "debug" ? "Loading…" : "Load"}
          </button>

          {cropsData && (
            <div className="debug-section">
              <h3>Crops <span className="count">({cropsData.total})</span></h3>
              {cropsData.crops.length === 0 ? (
                <p className="empty">No crops found.</p>
              ) : (
                <table className="debug-table">
                  <thead>
                    <tr><th>ID</th><th>Name</th><th>Botanical Name</th></tr>
                  </thead>
                  <tbody>
                    {cropsData.crops.map((c) => (
                      <tr key={c.crop_id}>
                        <td>{c.crop_id}</td>
                        <td>{c.name}</td>
                        <td>{c.botanical_name ?? <em>—</em>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {sourcesData && (
            <div className="debug-section">
              <h3>Sources <span className="count">({sourcesData.total})</span></h3>
              {sourcesData.sources.length === 0 ? (
                <p className="empty">No sources found.</p>
              ) : (
                <table className="debug-table">
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
              )}
            </div>
          )}

          {chunksData && (
            <div className="debug-section">
              <h3>Chunks <span className="count">({chunksData.total} total)</span></h3>
              {chunksData.chunks.length === 0 ? (
                <p className="empty">No chunks found.</p>
              ) : (
                <table className="debug-table">
                  <thead>
                    <tr><th>ID</th><th>Crop</th><th>Section</th><th>Pg</th><th>Preview</th></tr>
                  </thead>
                  <tbody>
                    {chunksData.chunks.map((c) => (
                      <tr key={c.chunk_id}>
                        <td className="monospace">{c.chunk_id.slice(0, 8)}…</td>
                        <td>{c.crop_tag}</td>
                        <td>{c.section_name}</td>
                        <td>{c.page_number}</td>
                        <td className="preview">{c.text_preview}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </section>
      )}
    </main>
  );
}

export default App;
