"use client";

import { FormEvent, useState } from "react";

type Explanation = {
  requirement: string;
  status: "met" | "not_met" | "not_stated";
  value: unknown;
  source: string | null;
};

type Result = {
  dataset: {
    dataset_id: string;
    title: string;
    url: string;
    repository: string;
    licence: string | null;
    doi: string | null;
    fields: Record<string, { value: unknown; status: string; source: string | null }>;
  };
  score: number;
  explanations: Explanation[];
};

type SearchResponse = {
  parsed: { semantic_query: string; filters: Record<string, unknown> };
  results: Result[];
  notice: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export default function Home() {
  const [query, setQuery] = useState("");
  const [filterText, setFilterText] = useState("");
  const [editing, setEditing] = useState(false);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResponse(null);
    try {
      let filters: Record<string, unknown> | undefined;
      if (editing && filterText.trim()) filters = JSON.parse(filterText);
      const result = await fetch(`${API_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, filters, limit: 10 }),
      });
      const payload = await result.json();
      if (!result.ok) throw new Error(payload.detail ?? "Search failed. Check that the API is running and indexed.");
      setResponse(payload);
      setFilterText(JSON.stringify(payload.parsed.filters, null, 2));
    } catch (cause) {
      setError(cause instanceof SyntaxError ? "Filters must be valid JSON." : String(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="NeuroData Finder home">
          <span className="brand-mark" aria-hidden="true">N</span>
          <span>NeuroData Finder</span>
        </a>
        <span className="scope-tag">OPENNEURO · MRI / fMRI</span>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow">PUBLIC DATASET DISCOVERY</p>
          <h1>Find the right dataset<br /><em>for your next study.</em></h1>
          <p className="intro">Describe what you need. Review the filters. See why each dataset may fit, with evidence from its metadata.</p>
        </div>
        <div className="index-note"><span className="pulse" />Metadata only<span className="note-divider">/</span>No data files hosted</div>
      </section>

      <section className="search-panel" aria-label="Dataset search">
        <form onSubmit={search}>
          <label className="field-label" htmlFor="query">What kind of dataset are you looking for?</label>
          <div className="query-row">
            <textarea
              id="query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              maxLength={2000}
              placeholder="e.g. Resting-state fMRI in adults over 60 with at least 100 participants"
              required
              rows={2}
            />
            <button type="submit" disabled={busy || !query.trim()}>{busy ? "Searching…" : "Find datasets"}<span aria-hidden="true">↗</span></button>
          </div>
          <div className="form-foot">
            <span>Try: “preprocessed visual working memory fMRI in healthy adults”</span>
            <button className="text-button" type="button" onClick={() => setEditing((value) => !value)}>
              {editing ? "Hide filter editor" : "Review filters"}
            </button>
          </div>
          {editing && (
            <div className="filter-editor">
              <label className="field-label" htmlFor="filters">Parsed filters · edit JSON before searching</label>
              <textarea
                id="filters"
                value={filterText}
                onChange={(event) => setFilterText(event.target.value)}
                rows={9}
                spellCheck={false}
                placeholder="Filters appear here after your first search."
              />
            </div>
          )}
        </form>
      </section>

      {error && <div className="error" role="alert">{error}</div>}
      {response && (
        <section className="results" aria-live="polite">
          <div className="results-heading">
            <div><p className="eyebrow">YOUR SEARCH</p><h2>{response.results.length} matching datasets</h2></div>
            <p>Ranked by metadata relevance<br /><span>Parsed filters can be edited above</span></p>
          </div>
          <div className="filter-summary">
            <span className="summary-label">ACTIVE FILTERS</span>
            {Object.entries(response.parsed.filters).filter(([, value]) => value !== null && value !== undefined && value !== false && !(Array.isArray(value) && value.length === 0)).map(([key, value]) => (
              <span className="filter-chip" key={key}>{key.replaceAll("_", " ")} <b>{Array.isArray(value) ? value.join(", ") : String(value)}</b></span>
            ))}
          </div>
          <div className="result-list">
            {response.results.map((item, index) => (
              <article className="result-card" key={item.dataset.dataset_id}>
                <div className="rank">{String(index + 1).padStart(2, "0")}</div>
                <div className="result-content">
                  <div className="result-meta"><span>{item.dataset.dataset_id}</span><span>{item.dataset.repository}</span></div>
                  <h3><a href={item.dataset.url} target="_blank" rel="noreferrer">{item.dataset.title}<span aria-hidden="true"> ↗</span></a></h3>
                  <div className="badges">
                    {item.dataset.licence && <span className="badge">Licence · {item.dataset.licence}</span>}
                    {item.dataset.doi && <span className="badge">DOI · {item.dataset.doi}</span>}
                  </div>
                  {item.explanations.length > 0 && (
                    <div className="explanations">
                      <p className="explain-title">REQUIREMENT CHECK</p>
                      {item.explanations.map((explanation) => (
                        <div className="explanation" key={explanation.requirement}>
                          <span className={`status status-${explanation.status}`} aria-label={explanation.status} />
                          <span className="requirement">{explanation.requirement}</span>
                          <span className={`status-word status-word-${explanation.status}`}>{explanation.status.replace("_", " ")}</span>
                          {explanation.source && <details><summary>Evidence</summary><blockquote>{explanation.source}</blockquote></details>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="score"><span>RANK SCORE</span>{item.score.toFixed(3)}</div>
              </article>
            ))}
          </div>
          <p className="notice">{response.notice}</p>
        </section>
      )}

      {!response && !error && <section className="empty-state"><span className="empty-icon">⌕</span><p>Start with a modality, population, task, age range, or sample size.</p></section>}
      <footer><span>NeuroData Finder</span><span>OpenNeuro metadata · Search suggestions only</span></footer>
    </main>
  );
}
