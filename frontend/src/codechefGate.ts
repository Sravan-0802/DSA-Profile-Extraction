/**
 * CodeChef scraping feature temporarily disabled.
 * Helpers that keep CodeChef out of the frontend submit/display path
 * without deleting backend scraping code (re-enable later by removing call sites).
 */

const CODECHEF_HEADER_RE = /code[_\s-]?chef/i;
const CODECHEF_URL_RE = /codechef\.com/i;

/** True for result/header names that belong to the disabled CodeChef feature. */
export function isCodechefColumn(name: string): boolean {
  return name.startsWith("CodeChef") || CODECHEF_HEADER_RE.test(name);
}

function stripCodechefColumns(text: string): string {
  const lines = text.split(/\r?\n/);
  if (!lines.length) return text;

  const first = lines.find((ln) => ln.trim()) ?? "";
  const delim = first.includes("\t") ? "\t" : ",";
  const headerCells = first.split(delim).map((c) => c.trim());
  const dropIdx = new Set<number>();
  headerCells.forEach((h, i) => {
    if (isCodechefColumn(h)) dropIdx.add(i);
  });

  return lines
    .map((line) => {
      if (!line.trim()) return line;
      const parts = line.split(delim);
      const kept = parts
        .map((cell, i) => (dropIdx.has(i) ? null : cell))
        .filter((c): c is string => c !== null)
        // Also blank any leftover CodeChef profile URLs pasted in the wrong column.
        .map((cell) => (CODECHEF_URL_RE.test(cell) ? "" : cell));
      return kept.join(delim);
    })
    .join("\n");
}

/** Remove CodeChef columns / URLs from pasted profile tables before POST /api/jobs. */
export function stripCodechefFromPaste(text: string): string {
  return stripCodechefColumns(text);
}

/** Remove CodeChef columns / URLs from an uploaded CSV/TSV before POST /api/jobs. */
export async function stripCodechefFromCsvFile(file: File): Promise<File> {
  const raw = await file.text();
  const cleaned = stripCodechefColumns(raw);
  return new File([cleaned], file.name, { type: file.type || "text/csv" });
}
