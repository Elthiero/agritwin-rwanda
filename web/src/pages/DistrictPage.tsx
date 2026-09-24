import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { API_BASE } from '../api/client'
import { useDistrictProfile, useNowcast, useScenario } from '../api/hooks'
import type { Crop, Season } from '../api/types'
import { CROPS, CROP_LABELS, LEAD_MONTHS, MAX_YEAR, MIN_YEAR, SEASONS } from '../lib/constants'
import { formatKgHa, formatPercent } from '../lib/format'
import { DEFAULT_LEVERS, findScenarioRow, type LeverState } from '../lib/scenario'
import './DistrictPage.css'

const LEVER_LABELS: Record<keyof LeverState, string> = {
  improved_seed: 'Improved seed',
  inorganic_fert: 'Inorganic fertilizer',
  organic_fert: 'Organic fertilizer',
  irrigated: 'Irrigation',
}

function isCrop(value: string | null): value is Crop {
  return CROPS.includes(value as Crop)
}

function isSeason(value: string | null): value is Season {
  return SEASONS.includes(value as Season)
}

export default function DistrictPage() {
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
        <p className="status-line error">Invalid district code.</p>
      </div>
    )
  }

  return (
    <div className="district-page">
      <header className="masthead">
        <div>
          <Link className="back-link" to="/">
            ← Back to map
          </Link>
          <h1>{profile.data?.district_name ?? `District ${districtCode}`}</h1>
        </div>
      </header>

      <div className="controls" role="toolbar" aria-label="Filters">
        <div className="control-group">
          <span className="control-label" id="dp-crop-label">
            Crop
          </span>
          <div className="tab-set" role="group" aria-labelledby="dp-crop-label">
            {CROPS.map((c) => (
              <button key={c} type="button" aria-pressed={crop === c} onClick={() => setCrop(c)}>
                {CROP_LABELS[c]}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <span className="control-label" id="dp-season-label">
            Season
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
            Year
          </span>
          <div className="stepper" role="group" aria-labelledby="dp-year-label">
            <button
              type="button"
              aria-label="Previous year"
              disabled={year <= MIN_YEAR}
              onClick={() => setYear((y) => Math.max(MIN_YEAR, y - 1))}
            >
              −
            </button>
            <span className="year-value">{year}</span>
            <button
              type="button"
              aria-label="Next year"
              disabled={year >= MAX_YEAR}
              onClick={() => setYear((y) => Math.min(MAX_YEAR, y + 1))}
            >
              +
            </button>
          </div>
        </div>
      </div>

      <p className="model-badge">Model-based estimate, not official statistics</p>

      {loading && <p className="status-line">Loading district profile…</p>}
      {error && (
        <p className="status-line error">
          Could not load this district: {error instanceof Error ? error.message : String(error)}
        </p>
      )}

      {profile.data && (
        <div className="district-grid">
          <section className="card">
            <h2>Yield trend</h2>
            <p className="card-caption">
              Weighted district-level actual yield for {CROP_LABELS[crop].toLowerCase()}, Season{' '}
              {season}, by year.
            </p>
            {profile.data.yield_trend.length === 0 ? (
              <p className="card-empty">No years with usable data for this crop and season.</p>
            ) : (
              <table className="trend-table">
                <thead>
                  <tr>
                    <th>Year</th>
                    <th>Yield</th>
                    <th>Reliability</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.data.yield_trend.map((row) => (
                    <tr key={row.year}>
                      <td>{row.year}</td>
                      <td>{formatKgHa(row.yield_kg_ha)}</td>
                      <td className={row.reliability !== 'ok' ? 'reliability-flag' : undefined}>
                        {row.reliability.replace(/_/g, ' ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="card">
            <h2>Yield gap trend</h2>
            <p className="card-caption">
              Actual yield versus modeled attainable yield: how much room this district has to
              close the gap.
            </p>
            {profile.data.gap_trend.length === 0 ? (
              <p className="card-empty">No years with a computed gap for this crop and season.</p>
            ) : (
              <table className="trend-table">
                <thead>
                  <tr>
                    <th>Year</th>
                    <th>Gap</th>
                    <th>Reliability</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.data.gap_trend.map((row) => (
                    <tr key={row.year}>
                      <td>{row.year}</td>
                      <td>{formatPercent(row.yield_gap_pct)}</td>
                      <td className={row.reliability !== 'ok' ? 'reliability-flag' : undefined}>
                        {row.reliability.replace(/_/g, ' ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="card">
            <h2>Top associated practices</h2>
            <p className="card-caption">
              SHAP-based associations from the driver model, not causal effects (per project
              rule: "associated with", never "causes" or "increases yield by").
            </p>
            {profile.data.top_drivers.length === 0 ? (
              <p className="card-empty">Not enough data to rank drivers for this district.</p>
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
            <h2>Early yield estimate</h2>
            <p className="card-caption">
              A leave-one-year-out backtest prediction, {lead} months into the season, not a live
              in-season forecast: every row served today is historical hold-out data.
            </p>
            <div className="lead-picker" role="group" aria-label="Lead time">
              {LEAD_MONTHS.map((m) => (
                <button key={m} type="button" aria-pressed={lead === m} onClick={() => setLead(m)}>
                  {m} mo
                </button>
              ))}
            </div>
            {nowcast.isLoading && <p className="card-empty">Loading…</p>}
            {!nowcast.isLoading && !nowcastRow && (
              <p className="card-empty">
                No early estimate for {CROP_LABELS[crop].toLowerCase()} in Season {season} {year}{' '}
                at this lead time.
              </p>
            )}
            {nowcastRow && (
              <>
                <dl>
                  <dt>Predicted yield</dt>
                  <dd>{formatKgHa(nowcastRow.predicted_yield_kg_ha)}</dd>
                  <dt>Interval</dt>
                  <dd>
                    {formatKgHa(nowcastRow.ci_low)} to {formatKgHa(nowcastRow.ci_high)}
                  </dd>
                  <dt>Actual (once surveyed)</dt>
                  <dd>{formatKgHa(nowcastRow.actual_yield_kg_ha)}</dd>
                </dl>
                <p className="card-note">
                  Model used: {nowcastRow.model.replace(/_/g, ' ')}, chosen because it had the
                  lowest backtest error for this crop and lead time — often the simple
                  district-average baseline, not a fancier model. See the methodology page for
                  the full honest comparison.
                </p>
              </>
            )}
          </section>

          <section className="card">
            <h2>Scenario explorer</h2>
            <p className="card-caption">
              Model-based estimate of mean yield under a hypothetical combination of practices,
              not a simulation of a real intervention.
            </p>
            <div className="lever-toggles">
              {(Object.keys(LEVER_LABELS) as (keyof LeverState)[]).map((key) => (
                <label key={key} className="lever-toggle">
                  <input
                    type="checkbox"
                    checked={levers[key]}
                    onChange={(e) => setLevers((l) => ({ ...l, [key]: e.target.checked }))}
                  />
                  {LEVER_LABELS[key]}
                </label>
              ))}
            </div>
            {scenario.isLoading && <p className="card-empty">Loading…</p>}
            {!scenario.isLoading && !scenarioRow && (
              <p className="card-empty">No scenario data for this district and crop.</p>
            )}
            {scenarioRow && (
              <dl>
                <dt>Predicted mean yield</dt>
                <dd>{formatKgHa(scenarioRow.mean_yield_kg_ha)}</dd>
                <dt>Interval</dt>
                <dd>
                  {formatKgHa(scenarioRow.ci_low)} to {formatKgHa(scenarioRow.ci_high)}
                </dd>
              </dl>
            )}
          </section>

          <section className="card">
            <h2>Peer districts</h2>
            <p className="card-caption">
              Same modeled agro-ecological zone (a k-means grouping, since no real AEZ layer is
              configured in this project).
            </p>
            {profile.data.peer_districts.length === 0 ? (
              <p className="card-empty">No peer districts found.</p>
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
            <h2>District brief</h2>
            <p className="card-caption">
              A one-page PDF covering all 4 MVP crops for this district, generated ahead of time.
            </p>
            <a
              className="brief-link"
              href={`${API_BASE}/briefs/${districtCode}.pdf`}
              target="_blank"
              rel="noreferrer"
            >
              Download PDF brief
            </a>
          </section>
        </div>
      )}

      <footer className="footer-strip">
        AgriTwin Rwanda. NISR 2026 Big Data Hackathon. Not official NISR statistics.
      </footer>
    </div>
  )
}
