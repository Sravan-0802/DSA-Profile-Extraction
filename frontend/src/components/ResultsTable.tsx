import { orderColumns } from "../helpers";
import type { Row } from "../types";

// CodeChef scraping feature temporarily disabled — "CodeChef Profile" removed from link columns
const LINK_COLS = new Set([
  "Resume Link", "LinkedIn Link", "GitHub Link", "GitHub Profile", "LeetCode Profile",
  "Codeforces Profile", /* "CodeChef Profile", */ "HackerRank Profile", "Profile Used",
]);

function bandClass(band: string): string {
  return band === "Not Shortlisted" ? "NotShortlisted" : band;
}

function Cell({ col, value }: { col: string; value: unknown }) {
  const str = value === null || value === undefined ? "" : String(value);

  if (col === "Error" && str) return <td className="err">{str}</td>;
  if (col === "Priority Band" && str) {
    return (
      <td>
        <span className={`badge ${bandClass(str)}`}>{str}</span>
      </td>
    );
  }
  if (LINK_COLS.has(col) && str.startsWith("http")) {
    return (
      <td title={str}>
        <a href={str} target="_blank" rel="noreferrer">{str.replace(/^https?:\/\//, "")}</a>
      </td>
    );
  }
  return <td title={str}>{str}</td>;
}

export default function ResultsTable({ rows }: { rows: Row[] }) {
  if (!rows.length) return null;
  const columns = orderColumns(rows);

  return (
    <div className="table-scroll" style={{ maxHeight: 540, overflowY: "auto" }}>
      <table>
        <thead>
          <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => <Cell key={c} col={c} value={row[c]} />)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
