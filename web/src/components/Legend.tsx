/** Reads the yield-gap choropleth: the gradient this map actually uses, plus what the
 * grey districts mean. Per web/CLAUDE.md UX rule 5, every map/chart needs a one-sentence
 * "what this shows" and a "how to read" explanation, not just an unlabeled color scale. */
export default function Legend() {
  return (
    <div className="legend" aria-label="Map legend">
      <p className="legend-title">Yield gap: actual vs. attainable</p>
      <div className="legend-gradient" />
      <div className="legend-scale-labels">
        <span>Small gap</span>
        <span>Large gap</span>
      </div>
      <div className="legend-suppressed">
        <span className="legend-swatch" />
        <span>Grey: too few surveyed plots to report reliably</span>
      </div>
    </div>
  )
}
