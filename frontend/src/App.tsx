import { useEffect, useRef, useState } from "react";
import { buildDownloadUrl, createJob, getConfig, getJob } from "./api";
import Login, { clearAuth, isAuthenticated } from "./components/Login";
import ResultsTable from "./components/ResultsTable";
import type { AppConfig, JobStatus } from "./types";

export default function App() {
  const [authed, setAuthed] = useState(() => isAuthenticated());
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [configError, setConfigError] = useState("");

  const [concurrency, setConcurrency] = useState(8);
  const [inputMethod, setInputMethod] = useState<"text" | "csv">("text");
  const [pastedText, setPastedText] = useState("");
  const [csvFile, setCsvFile] = useState<File | null>(null);

  const [job, setJob] = useState<JobStatus | null>(null);
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    if (!authed) return;
    getConfig()
      .then((c) => {
        setConfig(c);
        setConcurrency(c.default_concurrency);
      })
      .catch(() => setConfigError("Could not reach the backend at /api. Is the server running?"));
  }, [authed]);

  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") return;
    pollRef.current = window.setInterval(async () => {
      try {
        const updated = await getJob(job.id);
        setJob(updated);
      } catch {
        /* keep last state */
      }
    }, 1500);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [job?.id, job?.status]);

  const canSubmit =
    !submitting && (inputMethod === "text" ? pastedText.trim().length > 0 : csvFile !== null);

  async function handleSubmit() {
    setSubmitError("");
    setSubmitting(true);
    try {
      const { job_id } = await createJob({
        mode: "dsa",
        analysisType: "All Data",
        shortlistingMode: "Priority Wise (P1 / P2 / P3 Bands)",
        userRequirements: "",
        githubSkills: "",
        companyName: "",
        concurrency,
        inputMethod,
        pastedText,
        csvFile,
      });
      const initial = await getJob(job_id);
      setJob(initial);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Failed to start job");
    } finally {
      setSubmitting(false);
    }
  }

  function handleLogout() {
    clearAuth();
    setAuthed(false);
    setJob(null);
  }

  const liveRows = job?.live_results ?? [];
  const isDone = job?.status === "completed" || job?.status === "failed";

  if (!authed) {
    return <Login onSuccess={() => setAuthed(true)} />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>DSA Profile Extraction</h1>
          <p className="sub">
            {/* CodeChef scraping feature temporarily disabled — CodeChef removed from description */}
            Paste user IDs with LeetCode / Codeforces profile URLs to get solved counts — React ·
            FastAPI
          </p>
        </div>
        <button type="button" className="btn-ghost" onClick={handleLogout}>
          Sign out
        </button>
      </header>

      {configError && <div className="error-box">{configError}</div>}

      <div className="panel">
        <h2>1 · Input</h2>
        <div className="seg" style={{ marginBottom: 14 }}>
          <button className={inputMethod === "text" ? "active" : ""} onClick={() => setInputMethod("text")}>
            Paste text
          </button>
          <button className={inputMethod === "csv" ? "active" : ""} onClick={() => setInputMethod("csv")}>
            Upload CSV
          </button>
        </div>
        {inputMethod === "text" ? (
          <div className="field">
            <label>
              Profile table{" "}
              <span className="hint">
                {/* CodeChef scraping feature temporarily disabled — code_chef_profile_url_link column hidden from hint */}
                — include header row: user_id, leetcode_profile_url_link, codeforces_profile_link
              </span>
            </label>
            <textarea
              value={pastedText}
              placeholder={
                /* CodeChef scraping feature temporarily disabled — CodeChef column removed from placeholder */
                "user_id\tleetcode_profile_url_link\tcodeforces_profile_link\n" +
                "uid-1\thttps://leetcode.com/u/alice/\thttps://codeforces.com/profile/alice\n" +
                "uid-2\thttps://leetcode.com/u/bob/\t-"
              }
              onChange={(e) => setPastedText(e.target.value)}
            />
          </div>
        ) : (
          <div className="field">
            <label>
              CSV file{" "}
              <span className="hint">
                {/* CodeChef scraping feature temporarily disabled — codechef column removed from CSV hint */}
                — columns: user_id + leetcode / codeforces profile URL columns
              </span>
            </label>
            <input
              type="file"
              accept=".csv,.tsv,.txt"
              onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
            />
          </div>
        )}
      </div>

      <div className="panel">
        <h2>2 · Run</h2>
        <p className="hint" style={{ marginBottom: 14 }}>
          {/* CodeChef scraping feature temporarily disabled — CodeChef removed from run description */}
          Pulls LeetCode / Codeforces metrics (solved counts, Medium/Hard, ratings, recent activity
          where publicly available). Download results as CSV when the run finishes. No AI key required.
        </p>

        <div className="field">
          <label>Concurrency: {concurrency}</label>
          <input
            type="range"
            min={1}
            max={config?.max_concurrency ?? 20}
            value={concurrency}
            onChange={(e) => setConcurrency(Number(e.target.value))}
            style={{ width: "100%" }}
          />
        </div>

        {submitError && (
          <div className="error-box" style={{ marginTop: 14 }}>
            {submitError}
          </div>
        )}

        <button className="primary" style={{ marginTop: 16 }} disabled={!canSubmit} onClick={handleSubmit}>
          {submitting ? "Starting…" : "Start analysis"}
        </button>
      </div>

      {job && (
        <div className="panel">
          <div className="status-line">
            <span className={`dot ${job.status}`} />
            <strong>{job.status.toUpperCase()}</strong>
            <span>
              · {job.completed} / {job.total} processed
            </span>
            {job.file_name && <span>· {job.file_name}</span>}
          </div>
          <div className="progress-wrap">
            <div className="progress-bar" style={{ width: `${Math.round(job.progress * 100)}%` }} />
          </div>

          {job.errors.length > 0 && (
            <div className="warn-box" style={{ marginTop: 12 }}>
              {job.errors.length} row error(s): {job.errors.slice(0, 3).join("; ")}
              {job.errors.length > 3 ? "…" : ""}
            </div>
          )}

          {isDone && (
            <div className="toolbar" style={{ marginTop: 14 }}>
              <span className="hint">Showing {liveRows.length} rows</span>
              <a className="btn-ghost" href={buildDownloadUrl(job.id)}>
                ⬇ Download CSV
              </a>
            </div>
          )}
        </div>
      )}

      {liveRows.length > 0 && (
        <div className="panel">
          <h2>Results</h2>
          <ResultsTable rows={liveRows} />
        </div>
      )}
    </div>
  );
}
