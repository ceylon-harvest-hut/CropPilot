import { useEffect, useMemo, useState } from "react";
import { ApiError } from "./api/client";
import { getGraphCropDetail, listGraphCrops } from "./api/graphDebug";
import type { GraphCropDetailResponse, GraphCropListResponse, GraphCropNode } from "./api/types";

function isWebUrl(uri: string): boolean {
  return uri.startsWith("http://") || uri.startsWith("https://");
}

function SourceUriLabel({ uri }: { uri: string }) {
  if (isWebUrl(uri)) {
    return (
      <a href={uri} target="_blank" rel="noreferrer" className="monospace">
        {uri}
      </a>
    );
  }
  return <span className="monospace">{uri}</span>;
}

function formatScalar(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  return String(value);
}

interface ScalarField {
  label: string;
  value: string | number | null | undefined;
}

function scalarFields(node: GraphCropNode): ScalarField[] {
  return [
    { label: "Manifest crop name", value: node.manifest_crop_name },
    { label: "Scientific name", value: node.scientific_name },
    { label: "Altitude (m)", value: formatRange(node.altitude_min_m, node.altitude_max_m) },
    { label: "Temperature (°C)", value: formatRange(node.temp_min_c, node.temp_max_c) },
    { label: "Rainfall (mm)", value: formatRange(node.rainfall_min_mm, node.rainfall_max_mm) },
    { label: "pH", value: formatRange(node.ph_min, node.ph_max) },
    { label: "Pit length (cm)", value: node.pit_length_cm },
    { label: "Pit width (cm)", value: node.pit_width_cm },
    { label: "Row distance (cm)", value: node.row_distance_cm },
    { label: "Plant distance (cm)", value: node.plant_distance_cm },
    { label: "Expected harvest (kg/ha)", value: node.expected_harvest_kg_per_ha },
    { label: "Days to maturity", value: node.days_to_maturity },
    { label: "Nursery period (days)", value: node.nursery_period_days },
    { label: "Seed amount per ha", value: node.seed_amount_per_ha },
    { label: "Seed metric type", value: node.seed_metric_type },
  ];
}

function formatRange(min: number | null, max: number | null): string | null {
  if (min === null && max === null) {
    return null;
  }
  if (min !== null && max !== null) {
    return `${min} – ${max}`;
  }
  return String(min ?? max);
}

function TagList({ items, emptyLabel }: { items: string[]; emptyLabel: string }) {
  if (items.length === 0) {
    return <p className="empty">{emptyLabel}</p>;
  }
  return (
    <ul className="graph-debug-tag-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function CropNodeCard({ node }: { node: GraphCropNode }) {
  return (
    <article className="debug-card graph-debug-node-card">
      <header className="debug-card-header">
        <h3>
          <SourceUriLabel uri={node.source_uri} />
        </h3>
      </header>
      <div className="debug-card-body">
        <dl className="graph-debug-props">
          {scalarFields(node).map((field) => (
            <div key={field.label} className="graph-debug-prop-row">
              <dt>{field.label}</dt>
              <dd>{formatScalar(field.value)}</dd>
            </div>
          ))}
        </dl>

        <section className="graph-debug-rel-section">
          <h4>Growing areas</h4>
          <TagList items={node.growing_areas} emptyLabel="No growing areas." />
        </section>

        <section className="graph-debug-rel-section">
          <h4>Seasons</h4>
          <TagList items={node.growing_seasons} emptyLabel="No seasons." />
        </section>

        <section className="graph-debug-rel-section">
          <h4>Varieties</h4>
          <TagList items={node.varieties} emptyLabel="No varieties." />
        </section>

        <section className="graph-debug-rel-section">
          <h4>Soil types</h4>
          <TagList items={node.soil_types} emptyLabel="No soil types." />
        </section>

        <section className="graph-debug-rel-section">
          <h4>Fertilizers</h4>
          {node.fertilizer_schedule.length === 0 ? (
            <p className="empty">No fertilizer schedule.</p>
          ) : (
            <table className="debug-table debug-table-compact">
              <thead>
                <tr>
                  <th>Fertilizer</th>
                  <th>Start (wk)</th>
                  <th>Repeats</th>
                  <th>Interval (wk)</th>
                  <th>Qty (kg/ha)</th>
                </tr>
              </thead>
              <tbody>
                {node.fertilizer_schedule.map((item) => (
                  <tr key={item.fertilizer}>
                    <td>{item.fertilizer}</td>
                    <td>{formatScalar(item.apply_start_weeks_after_planting)}</td>
                    <td>{formatScalar(item.repeat_count)}</td>
                    <td>{formatScalar(item.repeat_interval_weeks)}</td>
                    <td>{formatScalar(item.quantity_kg_per_ha)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="graph-debug-rel-section">
          <h4>Pests</h4>
          {node.pests.length === 0 ? (
            <p className="empty">No pests.</p>
          ) : (
            <table className="debug-table debug-table-compact">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Impact</th>
                  <th>Solution</th>
                </tr>
              </thead>
              <tbody>
                {node.pests.map((pest) => (
                  <tr key={pest.name}>
                    <td>{pest.name}</td>
                    <td>{formatScalar(pest.impact)}</td>
                    <td>{formatScalar(pest.solution)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="graph-debug-rel-section">
          <h4>Diseases</h4>
          {node.diseases.length === 0 ? (
            <p className="empty">No diseases.</p>
          ) : (
            <table className="debug-table debug-table-compact">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Causal agent</th>
                  <th>Impact</th>
                  <th>Solution</th>
                </tr>
              </thead>
              <tbody>
                {node.diseases.map((disease) => (
                  <tr key={disease.name}>
                    <td>{disease.name}</td>
                    <td>{formatScalar(disease.causal_agent)}</td>
                    <td>{formatScalar(disease.impact)}</td>
                    <td>{formatScalar(disease.solution)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </article>
  );
}

export default function GraphDebugPanel() {
  const [cropList, setCropList] = useState<GraphCropListResponse | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [detail, setDetail] = useState<GraphCropDetailResponse | null>(null);
  const [search, setSearch] = useState("");
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setListLoading(true);
    setError(null);
    listGraphCrops()
      .then((data) => {
        if (!cancelled) {
          setCropList(data);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load graph crops");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setListLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedName) {
      setDetail(null);
      return;
    }

    let cancelled = false;
    setDetailLoading(true);
    setError(null);
    getGraphCropDetail(selectedName)
      .then((data) => {
        if (!cancelled) {
          setDetail(data);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setDetail(null);
          setError(err instanceof ApiError ? err.message : "Failed to load crop detail");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setDetailLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedName]);

  const filteredCrops = useMemo(() => {
    if (!cropList) {
      return [];
    }
    const query = search.trim().toLowerCase();
    if (!query) {
      return cropList.crops;
    }
    return cropList.crops.filter((crop) => crop.name.toLowerCase().includes(query));
  }, [cropList, search]);

  return (
    <>
      {error && <p className="error debug-error">{error}</p>}

      <section className="debug-explorer">
        <aside className="debug-explorer-sidebar">
          <div className="debug-card">
            <header className="debug-card-header">
              <h3>Graph crops</h3>
              {cropList && <span className="debug-card-count">{cropList.total}</span>}
            </header>
            <div className="debug-card-body">
              <label className="graph-debug-search">
                <span className="debug-toolbar-label">Search</span>
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Filter by name…"
                  disabled={listLoading}
                />
              </label>
              {listLoading ? (
                <p className="debug-placeholder">Loading crops…</p>
              ) : filteredCrops.length === 0 ? (
                <p className="empty">No crops found.</p>
              ) : (
                <ul className="graph-debug-crop-list">
                  {filteredCrops.map((crop) => (
                    <li key={crop.name}>
                      <button
                        type="button"
                        className={`graph-debug-crop-btn${
                          selectedName === crop.name ? " graph-debug-crop-btn-active" : ""
                        }`}
                        onClick={() => setSelectedName(crop.name)}
                      >
                        <span>{crop.name}</span>
                        {crop.node_count > 1 && (
                          <span className="graph-debug-node-badge">{crop.node_count}</span>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </aside>

        <div className="debug-explorer-main">
          {!selectedName ? (
            <div className="debug-card">
              <p className="debug-placeholder">Select a crop to view graph knowledge.</p>
            </div>
          ) : detailLoading ? (
            <div className="debug-card">
              <p className="debug-placeholder">Loading {selectedName}…</p>
            </div>
          ) : !detail || detail.nodes.length === 0 ? (
            <div className="debug-card">
              <p className="empty">No graph nodes found for {selectedName}.</p>
            </div>
          ) : (
            detail.nodes.map((node) => <CropNodeCard key={node.source_uri} node={node} />)
          )}
        </div>
      </section>
    </>
  );
}
