import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMeta, useScenario } from '../api/hooks'
import type { Crop, Season } from '../api/types'
import { CROPS, SEASONS } from '../lib/constants'
import { formatKgHa } from '../lib/format'
import { DEFAULT_LEVERS, findScenarioRow, type LeverState } from '../lib/scenario'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SiteNav from '../components/SiteNav'
import '../styles/shared.css'

const LEVER_KEYS = Object.keys(DEFAULT_LEVERS) as (keyof LeverState)[]

export default function ScenarioPage() {
  const { t } = useTranslation()
  const meta = useMeta()
  const [crop, setCrop] = useState<Crop>('maize')
  const [season, setSeason] = useState<Season>('A')
  const [districtCode, setDistrictCode] = useState<number | null>(null)
  const [levers, setLevers] = useState<LeverState>(DEFAULT_LEVERS)

  const districts = meta.data?.districts ?? []
  const activeDistrict = districtCode ?? districts[0]?.district_code ?? null

  const scenario = useScenario(activeDistrict ?? 0, crop, season)

  const selectedRow = useMemo(
    () => findScenarioRow(scenario.data ?? [], levers),
    [scenario.data, levers],
  )
  const allRows = useMemo(
    () => [...(scenario.data ?? [])].sort((a, b) => b.mean_yield_kg_ha - a.mean_yield_kg_ha),
    [scenario.data],
  )

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-title">
          <h1>{t('scenario.title')}</h1>
          <p>{t('scenario.tagline')}</p>
        </div>
        <LanguageSwitcher />
      </header>
      <SiteNav />

      <div className="controls" role="toolbar" aria-label="Filters">
        <div className="control-group">
          <span className="control-label" id="sc-district-label">
            {t('scenario.district')}
          </span>
          <select
            aria-labelledby="sc-district-label"
            value={activeDistrict ?? ''}
            onChange={(e) => setDistrictCode(Number(e.target.value))}
          >
            {districts.map((d) => (
              <option key={d.district_code} value={d.district_code}>
                {d.district_name}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <span className="control-label" id="sc-crop-label">
            {t('controls.crop')}
          </span>
          <div className="tab-set" role="group" aria-labelledby="sc-crop-label">
            {CROPS.map((c) => (
              <button key={c} type="button" aria-pressed={crop === c} onClick={() => setCrop(c)}>
                {t(`crop.${c}`)}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <span className="control-label" id="sc-season-label">
            {t('controls.season')}
          </span>
          <div className="tab-set" role="group" aria-labelledby="sc-season-label">
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

      {scenario.isLoading && <p className="status-line">{t('scenario.loading')}</p>}
      {scenario.error && (
        <p className="status-line error">
          {t('scenario.error', {
            message: scenario.error instanceof Error ? scenario.error.message : String(scenario.error),
          })}
        </p>
      )}

      <div className="page-grid">
        <section className="card">
          <h2>{t('scenario.pickTitle')}</h2>
          <p className="card-caption">{t('scenario.pickCaption')}</p>
          <div className="lever-toggles">
            {LEVER_KEYS.map((key) => (
              <label key={key} className="lever-toggle">
                <input
                  type="checkbox"
                  checked={levers[key]}
                  onChange={(e) => setLevers((l) => ({ ...l, [key]: e.target.checked }))}
                />
                {t(`lever.${key}`)}
              </label>
            ))}
          </div>
          {!scenario.isLoading && !selectedRow && (
            <p className="card-empty">{t('scenario.pickEmpty')}</p>
          )}
          {selectedRow && (
            <dl>
              <dt>{t('district.predictedMeanYield')}</dt>
              <dd>{formatKgHa(selectedRow.mean_yield_kg_ha)}</dd>
              <dt>{t('district.interval')}</dt>
              <dd>
                {t('district.intervalRange', {
                  low: formatKgHa(selectedRow.ci_low),
                  high: formatKgHa(selectedRow.ci_high),
                })}
              </dd>
            </dl>
          )}
        </section>

        <section className="card">
          <h2>{t('scenario.allCombosTitle')}</h2>
          <p className="card-caption">{t('scenario.allCombosCaption')}</p>
          {allRows.length === 0 && !scenario.isLoading ? (
            <p className="card-empty">{t('scenario.pickEmpty')}</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  {LEVER_KEYS.map((key) => (
                    <th key={key}>{t(`lever.${key}`)}</th>
                  ))}
                  <th>{t('district.predictedMeanYield')}</th>
                </tr>
              </thead>
              <tbody>
                {allRows.map((row) => {
                  const isSelected =
                    row.improved_seed === levers.improved_seed &&
                    row.inorganic_fert === levers.inorganic_fert &&
                    row.organic_fert === levers.organic_fert &&
                    row.irrigated === levers.irrigated
                  return (
                    <tr
                      key={`${row.improved_seed}-${row.inorganic_fert}-${row.organic_fert}-${row.irrigated}`}
                      className={isSelected ? 'winner' : undefined}
                    >
                      {LEVER_KEYS.map((key) => (
                        <td key={key}>{row[key] ? t('scenario.yes') : t('scenario.no')}</td>
                      ))}
                      <td>{formatKgHa(row.mean_yield_kg_ha)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </section>
      </div>

      <div className="page-content">
        <h2>{t('scenario.disclaimerTitle')}</h2>
        <p>{t('scenario.disclaimerBody')}</p>
      </div>

      <footer className="footer-strip">{t('app.footer')}</footer>
    </div>
  )
}
