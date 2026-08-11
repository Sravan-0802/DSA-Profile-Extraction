import type { FilterState } from "../types";

const BANDS = ["P1", "P2", "P3", "Not Shortlisted"];

interface Props {
  filters: FilterState;
  onChange: (f: FilterState) => void;
  showShortlistFilters: boolean;
}

function RangeRow({
  label, value, onChange,
}: { label: string; value: [number, number]; onChange: (v: [number, number]) => void }) {
  return (
    <div>
      <div className="range-label"><span>{label}</span><span>{value[0]} – {value[1]}</span></div>
      <div style={{ display: "flex", gap: 8 }}>
        <input type="range" min={0} max={100} value={value[0]}
          onChange={(e) => onChange([Number(e.target.value), value[1]])} style={{ flex: 1 }} />
        <input type="range" min={0} max={100} value={value[1]}
          onChange={(e) => onChange([value[0], Number(e.target.value)])} style={{ flex: 1 }} />
      </div>
    </div>
  );
}

export default function Filters({ filters, onChange, showShortlistFilters }: Props) {
  const set = (patch: Partial<FilterState>) => onChange({ ...filters, ...patch });

  return (
    <div className="panel">
      <h2>Filters</h2>

      <div className="field">
        <label>Search <span className="hint">(skills, remarks, project titles, name)</span></label>
        <input type="text" value={filters.search} placeholder="e.g. react, aws…"
          onChange={(e) => set({ search: e.target.value })} />
      </div>

      {showShortlistFilters && (
        <div className="field">
          <label>Priority Band</label>
          <div className="chips">
            {BANDS.map((b) => {
              const on = filters.priorityBands.includes(b);
              return (
                <span key={b} className={`chip ${on ? "on" : ""}`}
                  onClick={() => set({
                    priorityBands: on
                      ? filters.priorityBands.filter((x) => x !== b)
                      : [...filters.priorityBands, b],
                  })}>
                  {b}
                </span>
              );
            })}
          </div>
        </div>
      )}

      <div className="filters-grid">
        {showShortlistFilters && (
          <>
            <RangeRow label="Overall" value={filters.overall} onChange={(v) => set({ overall: v })} />
            <RangeRow label="Skills" value={filters.skills} onChange={(v) => set({ skills: v })} />
            <RangeRow label="Experience" value={filters.experience} onChange={(v) => set({ experience: v })} />
            <RangeRow label="Projects" value={filters.projects} onChange={(v) => set({ projects: v })} />
            <RangeRow label="Other" value={filters.other} onChange={(v) => set({ other: v })} />
          </>
        )}
        <div>
          <label className="checkbox">
            <input type="checkbox" checked={filters.onlyInternal}
              onChange={(e) => set({ onlyInternal: e.target.checked })} />
            Has internal projects
          </label>
          <label className="checkbox" style={{ marginTop: 8 }}>
            <input type="checkbox" checked={filters.onlyExternal}
              onChange={(e) => set({ onlyExternal: e.target.checked })} />
            Has external projects
          </label>
        </div>
      </div>
    </div>
  );
}
