/** Number formatting helpers, per web/CLAUDE.md's UX rule that every number shown in the
 * app is formatted consistently (kg/ha, percent), never a bare unlabeled float. Null or
 * missing values render as an em dash, not "0" or "NaN": a missing value is not zero. */

export function formatKgHa(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${Math.round(value).toLocaleString('en-US')} kg/ha`
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${value.toFixed(digits)}%`
}
