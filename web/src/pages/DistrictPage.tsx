import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { API_BASE } from '../api/client'
import { useDistrictProfile, useNowcast, useScenario } from '../api/hooks'
import type { Crop, Season } from '../api/types'
import { CROPS, LEAD_MONTHS, MAX_YEAR, MIN_YEAR, SEASONS } from '../lib/constants'
import { formatKgHa, formatPercent } from '../lib/format'
import { DEFAULT_LEVERS, findScenarioRow, type LeverState } from '../lib/scenario'
import LanguageSwitcher from '../components/LanguageSwitcher'
import './DistrictPage.css'

const LEVER_KEYS = Object.keys(DEFAULT_LEVERS) as (keyof LeverState)[]

function isCrop(value: string | null): value is Crop {
  return CROPS.includes(value as Crop)
}

function isSeason(value: string | null): value is Season {
  return SEASONS.includes(value as Season)
}

export default function DistrictPage() {
  const { t } = useTranslation()
  const { code } = useParams<{ code: string }>()
  const districtCode = Number(code)
  const [searchParams] = useSearchParams()

  const paramCrop = searchParams.get('crop')
  const paramSeason = searchParams.get('season')
  const paramYear = Number(searchParams.get('year'))

  const [crop, setCrop] = useState<Crop>(isCrop(paramCrop) ? paramCrop : 'maize')
  const [season, setSeason] = useState<Season>(isSeason(paramSeason) ? paramSeason : 'A')
  const [year, setYear] = useState(
    paramYear >= MIN_YEAR && paramYear <= MAX_YEAR ? paramYear : MAX_YEAR,
  )
  const [lead, setLead] = useState(3)
  const [levers, setLevers] = useState<LeverState>(DEFAULT_LEVERS)

  const profile = useDistrictProfile(districtCode, crop, season)
  const scenario = useScenario(districtCode, crop, season)
  const nowcast = useNowcast(crop, season, year, lead)

  const scenarioRow = useMemo(
    () => findScenarioRow(scenario.data ?? [], levers),
    [scenario.data, levers],
  )
  const nowcastRow = useMemo(
    () => (nowcast.data ?? []).find((row) => row.district_code === districtCode),
    [nowcast.data, districtCode],
  )

  const loading = profile.isLoading
  const error = profile.error

  if (!Number.isFinite(districtCode)) {
    return (
      <div className="district-page">
        <p className="status-line error">{t('district.invalidCode')}</p>
      </div>
    )
  }

  return (
    <div className="district-page">
      <header className="masthead">
        <div className="masthead-title">
          <Link className="back-link" to="/">
            {t('app.backToMap')}
          </Link>
          <h1>{profile.data?.district_name ?? `District ${districtCode}`}</h1>
        </div>
        <LanguageSwitcher />
      </header>

      <div className="controls" role="toolbar" aria-label="Filters">
        <div className="control-group">
          <span className="control-label" id="dp-crop-label">
            {t('controls.crop')}
          </span>
          <div className="tab-set" role="group" aria-labelledby="dp-crop-label">
            {CROPS.map((c) => (
              <button key={c} type="button" aria-pressed={crop === c} onClick={() => setCrop(c)}>
                {t(`crop.${c}`)}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <span className="control-label" id="dp-season-label">
            {t('controls.season')}
          </span>
          <div className="tab-set" role="group" aria-labelledby="dp-season-label">
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

        <div className="control-group">
          <span className="control-label" id="dp-year-label">
            {t('controls.year')}
          </span>
          <div className="stepper" role="group" aria-labelledby="dp-year-label">
            <button
              type="button"
              aria-label={t('controls.previousYear')}
              disabled={year <= MIN_YEAR}
              onClick={() => setYear((y) => Math.max(MIN_YEAR, y - 1))}
            >
              −
            </button>
            <span className="year-value">{year}</span>
            <button
              type="button"
              aria-label={t('controls.nextYear')}
              disabled={year >= MAX_YEAR}
              onClick={() => setYear((y) => Math.min(MAX_YEAR, y + 1))}
            >
              +
            </button>
          </div>
        </div>
      </div>

      <p className="model-badge">{t('app.modelBadge')}</p>

      {loading && <p className="status-line">{t('district.loading')}</p>}
      {error && (
        <p className="status-line error">
          {t('district.error', {
            message: error instanceof Error ? error.message : String(error),
          })}
        </p>
      )}

      {profile.data && (
        <div className="district-grid">
          <section className="card">
            <h2>{t('district.yieldTrendTitle')}</h2>
            <p className="card-caption">
              {t('district.yieldTrendCaption', { crop: t(`crop.${crop}`), season })}
            </p>
            {profile.data.yield_trend.length === 0 ? (
              <p className="card-empty">{t('district.yieldTrendEmpty')}</p>
            ) : (
              <table className="trend-table">
                <thead>
                  <tr>
                    <th>{t('district.columnYear')}</th>
                    <th>{t('district.columnYield')}</th>
                    <th>{t('district.columnReliability')}</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.data.yield_trend.map((row) => (
                    <tr key={row.year}>
                      <td>{row.year}</td>
                      <td>{formatKgHa(row.yield_kg_ha)}</td>
                      <td className={row.reliability !== 'ok' ? 'reliability-flag' : undefined}>
                        {t(`reliability.${row.reliability}`)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="card">
            <h2>{t('district.gapTrendTitle')}</h2>
            <p className="card-caption">{t('district.gapTrendCaption')}</p>
            {profile.data.gap_trend.length === 0 ? (
              <p className="card-empty">{t('district.gapTrendEmpty')}</p>
            ) : (
              <table className="trend-table">
                <thead>
                  <tr>
                    <th>{t('district.columnYear')}</th>
                    <th>{t('district.columnGap')}</th>
                    <th>{t('district.columnReliability')}</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.data.gap_trend.map((row) => (
                    <tr key={row.year}>
                      <td>{row.year}</td>
                      <td>{formatPercent(row.yield_gap_pct)}</td>
                      <td className={row.reliability !== 'ok' ? 'reliability-flag' : undefined}>
                        {t(`reliability.${row.reliability}`)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="card">
            <h2>{t('district.driversTitle')}</h2>
            <p className="card-caption">{t('district.driversCaption')}</p>
            {profile.data.top_drivers.length === 0 ? (
              <p className="card-empty">{t('district.driversEmpty')}</p>
            ) : (
              <ul className="driver-list">
                {profile.data.top_drivers.map((driver) => (
                  <li key={driver.feature}>
                    <span className="driver-feature">{driver.feature.replace(/_/g, ' ')}</span>
                    <span className={`driver-direction driver-${driver.direction}`}>
                      {driver.direction}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <h2>{t('district.nowcastTitle')}</h2>
            <p className="card-caption">{t('district.nowcastCaption', { lead })}</p>
            <div className="lead-picker" role="group" aria-label={t('controls.leadTime')}>
              {LEAD_MONTHS.map((m) => (
                <button key={m} type="button" aria-pressed={lead === m} onClick={() => setLead(m)}>
                  {m} mo
                </button>
              ))}
            </div>
            {nowcast.isLoading && <p className="card-empty">{t('district.nowcastLoading')}</p>}
            {!nowcast.isLoading && !nowcastRow && (
              <p className="card-empty">
                {t('district.nowcastEmpty', { crop: t(`crop.${crop}`), season, year })}
              </p>
            )}
            {nowcastRow && (
              <>
                <dl>
                  <dt>{t('district.predictedYield')}</dt>
                  <dd>{formatKgHa(nowcastRow.predicted_yield_kg_ha)}</dd>
                  <dt>{t('district.interval')}</dt>
                  <dd>
                    {t('district.intervalRange', {
                      low: formatKgHa(nowcastRow.ci_low),
                      high: formatKgHa(nowcastRow.ci_high),
                    })}
                  </dd>
                  <dt>{t('district.actualOnceSurveyed')}</dt>
                  <dd>{formatKgHa(nowcastRow.actual_yield_kg_ha)}</dd>
                </dl>
                <p className="card-note">
                  {t('district.modelUsedNote', { model: nowcastRow.model.replace(/_/g, ' ') })}
                </p>
              </>
            )}
          </section>

          <section className="card">
            <h2>{t('district.scenarioTitle')}</h2>
            <p className="card-caption">{t('district.scenarioCaption')}</p>
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
            {scenario.isLoading && <p className="card-empty">{t('district.scenarioLoading')}</p>}
            {!scenario.isLoading && !scenarioRow && (
              <p className="card-empty">{t('district.scenarioEmpty')}</p>
            )}
            {scenarioRow && (
              <dl>
                <dt>{t('district.predictedMeanYield')}</dt>
                <dd>{formatKgHa(scenarioRow.mean_yield_kg_ha)}</dd>
                <dt>{t('district.interval')}</dt>
                <dd>
                  {t('district.intervalRange', {
                    low: formatKgHa(scenarioRow.ci_low),
                    high: formatKgHa(scenarioRow.ci_high),
                  })}
                </dd>
              </dl>
            )}
          </section>

          <section className="card">
            <h2>{t('district.peersTitle')}</h2>
            <p className="card-caption">{t('district.peersCaption')}</p>
            {profile.data.peer_districts.length === 0 ? (
              <p className="card-empty">{t('district.peersEmpty')}</p>
            ) : (
              <ul className="peer-list">
                {profile.data.peer_districts.map((peer) => (
                  <li key={peer.district_code}>
                    <Link
                      to={`/districts/${peer.district_code}?crop=${crop}&season=${season}&year=${year}`}
                    >
                      {peer.district_name}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <h2>{t('district.briefTitle')}</h2>
            <p className="card-caption">{t('district.briefCaption')}</p>
            <a
              className="brief-link"
              href={`${API_BASE}/briefs/${districtCode}.pdf`}
              target="_blank"
              rel="noreferrer"
            >
              {t('district.downloadBrief')}
            </a>
          </section>
        </div>
      )}

      <footer className="footer-strip">{t('app.footer')}</footer>
    </div>
  )
}
