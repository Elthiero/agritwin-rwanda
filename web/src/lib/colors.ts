/** Viridis-ish 5-stop sequential scale. Low gap (good) = light/yellow, high gap (bad) = dark/purple.
 * Per web/CLAUDE.md UX rule 4: sequential scale, never red/green alone. */
const STOPS: Array<[number, [number, number, number]]> = [
  [0, [253, 231, 37]],
  [25, [94, 201, 98]],
  [50, [33, 145, 140]],
  [75, [59, 82, 139]],
  [100, [68, 1, 84]],
]

export const RELIABILITY_GREY = '#c7c7c7'

export function yieldGapColor(pct: number): string {
  const clamped = Math.max(0, Math.min(100, pct))
  let lo = STOPS[0]
  let hi = STOPS[STOPS.length - 1]
  for (let i = 0; i < STOPS.length - 1; i++) {
    if (clamped >= STOPS[i][0] && clamped <= STOPS[i + 1][0]) {
      lo = STOPS[i]
      hi = STOPS[i + 1]
      break
    }
  }
  const [loPct, loRgb] = lo
  const [hiPct, hiRgb] = hi
  const t = hiPct === loPct ? 0 : (clamped - loPct) / (hiPct - loPct)
  const rgb = loRgb.map((c, i) => Math.round(c + t * (hiRgb[i] - c)))
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`
}
