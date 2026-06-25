import { useState } from "react";
import { ApiError } from "./api/client";
import { askQuestion } from "./api/inference";
import { ingestDocument } from "./api/ingestion";
import type { AskResponse, IngestResponse } from "./api/types";
import "./App.css";

function App() {
  const [sourceUri, setSourceUri] = useState("");
  const [cropName, setCropName] = useState("Pepper");
  const [question, setQuestion] = useState("What are pepper varieties?");
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);
  const [askResult, setAskResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<"ingest" | "ask" | null>(null);

  async function handleIngest() {
    setError(null);
    setLoading("ingest");
    try {
      const result = await ingestDocument({
        source_uri: sourceUri,
        crop_name: cropName,
      });
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
        crop_name: cropName || null,
      });
      setAskResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ask failed");
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

      {error && <p className="error">{error}</p>}

      <section className="panel">
        <h2>Ingest</h2>
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
          <pre className="result">
            {JSON.stringify(ingestResult, null, 2)}
          </pre>
        )}
      </section>

      <section className="panel">
        <h2>Ask</h2>
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
    </main>
  );
}

export default App;
