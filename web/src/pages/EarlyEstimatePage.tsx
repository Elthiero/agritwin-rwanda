import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useBacktest } from '../api/hooks'
import type { BacktestRow, Crop, Season } from '../api/types'
import { CROPS, SEASONS } from '../lib/constants'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SiteNav from '../components/SiteNav'
import '../styles/shared.css'

const MODEL_ORDER = ['baseline_district_mean', 'baseline_last_year', 'ridge', 'lgbm']

export default function EarlyEstimatePage() {
  const { t } = useTranslation()
  const [crop, setCrop] = useState<Crop>('maize')
  const [season, setSeason] = useState<Season>('A')

  const backtest = useBacktest(crop, season)

  const byLead = useMemo(() => {
    const groups = new Map<number, BacktestRow[]>()
    for (const row of backtest.data ?? []) {
      const list = groups.get(row.lead_months) ?? []
      list.push(row)
      groups.set(row.lead_months, list)
    }
    return [...groups.entries()].sort(([a], [b]) => a - b)
  }, [backtest.data])

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-title">
          <h1>{t('earlyEstimate.title')}</h1>
          <p>{t('earlyEstimate.tagline')}</p>
        </div>
        <LanguageSwitcher />
      </header>
      <SiteNav />

      <div className="controls" role="toolbar" aria-label="Filters">
        <div className="control-group">
          <span className="control-label" id="ee-crop-label">
            {t('controls.crop')}
          </span>
          <div className="tab-set" role="group" aria-labelledby="ee-crop-label">
            {CROPS.map((c) => (
              <button key={c} type="button" aria-pressed={crop === c} onClick={() => setCrop(c)}>
                {t(`crop.${c}`)}
              </button>
            ))}
          </div>
        </div>
        <div className="control-group">
          <span className="control-label" id="ee-season-label">
            {t('controls.season')}
          </span>
          <div className="tab-set" role="group" aria-labelledby="ee-season-label">
            {SEASONS.map((s) => (
              <button
                key={s}
                type="button"
                aria-pressed={season === s}
                onClick={() => setSeason(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      <p className="model-badge">{t('app.modelBadge')}</p>

      {backtest.isLoading && <p className="status-line">{t('earlyEstimate.loading')}</p>}
      {backtest.error && (
        <p className="status-line error">
          {t('earlyEstimate.error', {
            message: backtest.error instanceof Error ? backtest.error.message : String(backtest.error),
          })}
        </p>
      )}

      <div className="page-grid">
        {byLead.length === 0 && !backtest.isLoading && (
          <section className="card">
            <p className="card-empty">{t('earlyEstimate.empty')}</p>
          </section>
        )}

        {byLead.map(([lead, rows]) => {
          const sorted = [...rows].sort(
            (a, b) => MODEL_ORDER.indexOf(a.model) - MODEL_ORDER.indexOf(b.model),
          )
          const bestMape = Math.min(...sorted.map((r) => r.mape_pct))
          return (
            <section className="card" key={lead}>
              <h2>{t('earlyEstimate.leadTitle', { lead })}</h2>
              <p className="card-caption">{t('earlyEstimate.leadCaption')}</p>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>{t('earlyEstimate.columnModel')}</th>
                    <th>{t('earlyEstimate.columnMape')}</th>
                    <th>{t('earlyEstimate.columnMapeStd')}</th>
                    <th>{t('earlyEstimate.columnMae')}</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((row) => (
                    <tr key={row.model} className={row.mape_pct === bestMape ? 'winner' : undefined}>
                      <td>{t(`earlyEstimate.model.${row.model}`)}</td>
                      <td>{row.mape_pct.toFixed(1)}%</td>
                      <td>±{row.mape_std_across_years.toFixed(1)}pp</td>
                      <td>{Math.round(row.mae_kg_ha).toLocaleString()} kg/ha</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="card-note">
                {t('earlyEstimate.yearsNote', { n: sorted[0]?.n_years_tested ?? 0 })}
              </p>
            </section>
          )
        })}
      </div>

      <div className="page-content">
        <h2>{t('earlyEstimate.honestyTitle')}</h2>
        <p>{t('earlyEstimate.honestyBody1')}</p>
        <p>{t('earlyEstimate.honestyBody2')}</p>
      </div>

      <footer className="footer-strip">{t('app.footer')}</footer>
    </div>
  )
}
