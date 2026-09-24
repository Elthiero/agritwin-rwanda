import { useTranslation } from 'react-i18next'

/** Reads the yield-gap choropleth: the gradient this map actually uses, plus what the
 * grey districts mean. Per web/CLAUDE.md UX rule 5, every map/chart needs a one-sentence
 * "what this shows" and a "how to read" explanation, not just an unlabeled color scale. */
export default function Legend() {
  const { t } = useTranslation()
  return (
    <div className="legend" aria-label="Map legend">
      <p className="legend-title">{t('map.legendTitle')}</p>
      <div className="legend-gradient" />
      <div className="legend-scale-labels">
        <span>{t('map.legendSmallGap')}</span>
        <span>{t('map.legendLargeGap')}</span>
      </div>
      <div className="legend-suppressed">
        <span className="legend-swatch" />
        <span>{t('map.legendSuppressed')}</span>
      </div>
    </div>
  )
}
