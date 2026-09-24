import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useDistrictBoundaries, useYieldGap } from '../api/hooks'
import type { Crop, Season, YieldGapRow } from '../api/types'
import { RELIABILITY_GREY, yieldGapColor } from '../lib/colors'
import { formatKgHa, formatPercent } from '../lib/format'
import { CROPS, CROP_LABELS, MAX_YEAR, MIN_YEAR, SEASONS } from '../lib/constants'
import Legend from '../components/Legend'

interface SelectedDistrict {
  code: number
  name: string
  row: YieldGapRow | null
}

export default function MapPage() {
  const [crop, setCrop] = useState<Crop>('beans')
  const [season, setSeason] = useState<Season>('B')
  const [year, setYear] = useState(2025)
  const [selected, setSelected] = useState<SelectedDistrict | null>(null)

  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const [mapReady, setMapReady] = useState(false)

  const boundaries = useDistrictBoundaries()
  const yieldGap = useYieldGap(crop, season, year)

  const byDistrict = useMemo(() => {
    const rows = new Map<number, YieldGapRow>()
    for (const row of yieldGap.data ?? []) {
      rows.set(row.district_code, row)
    }
    return rows
  }, [yieldGap.data])

  useEffect(() => {
    if (!mapContainer.current) return
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      // A plain background, not an external tile style: web/CLAUDE.md is explicit that
      // no basemap tiles are required, and district polygons carry all the information
      // this map needs to show.
      style: {
        version: 8,
        sources: {},
        layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#dde1d1' } }],
      },
      center: [29.9, -1.95],
      zoom: 8,
      attributionControl: false,
    })
    map.current.on('load', () => setMapReady(true))
    return () => {
      map.current?.remove()
      map.current = null
    }
  }, [])

  useEffect(() => {
    if (!mapReady || !map.current || !boundaries.data) return
    const m = map.current

    const withColor = {
      ...boundaries.data,
      features: boundaries.data.features.map((f) => {
        const row = byDistrict.get(f.properties.district_code)
        const color =
          row && row.reliability !== 'suppressed' && row.yield_gap_pct != null
            ? yieldGapColor(row.yield_gap_pct)
            : RELIABILITY_GREY
        return { ...f, properties: { ...f.properties, fillColor: color } }
      }),
    }

    if (m.getSource('districts')) {
      const source = m.getSource('districts') as maplibregl.GeoJSONSource
      source.setData(withColor)
      return
    }

    m.addSource('districts', { type: 'geojson', data: withColor })
    m.addLayer({
      id: 'districts-fill',
      type: 'fill',
      source: 'districts',
      paint: { 'fill-color': ['get', 'fillColor'], 'fill-opacity': 0.8 },
    })
    m.addLayer({
      id: 'districts-outline',
      type: 'line',
      source: 'districts',
      paint: { 'line-color': '#f6f6f0', 'line-width': 1 },
    })

    m.on('mousemove', 'districts-fill', () => {
      m.getCanvas().style.cursor = 'pointer'
    })
    m.on('mouseleave', 'districts-fill', () => {
      m.getCanvas().style.cursor = ''
    })
    m.on('click', 'districts-fill', (e) => {
      const feature = e.features?.[0]
      if (!feature) return
      const code = feature.properties?.district_code as number
      const name = (feature.properties?.district_name as string) ?? `District ${code}`
      setSelected({ code, name, row: byDistrict.get(code) ?? null })
    })
  }, [mapReady, boundaries.data, byDistrict])

  const loading = boundaries.isLoading || yieldGap.isLoading
  const error = boundaries.error || yieldGap.error

  return (
    <div className="shell">
      <header className="masthead">
        <h1>AgriTwin Rwanda</h1>
        <p>Actual yield versus the modeled attainable yield, by district.</p>
      </header>

      <div className="controls" role="toolbar" aria-label="Filters">
        <div className="control-group">
          <span className="control-label" id="crop-label">
            Crop
          </span>
          <div className="tab-set" role="group" aria-labelledby="crop-label">
            {CROPS.map((c) => (
              <button
                key={c}
                type="button"
                aria-pressed={crop === c}
                onClick={() => setCrop(c)}
              >
                {CROP_LABELS[c]}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <span className="control-label" id="season-label">
            Season
          </span>
          <div className="tab-set" role="group" aria-labelledby="season-label">
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
          <span className="control-label" id="year-label">
            Year
          </span>
          <div className="stepper" role="group" aria-labelledby="year-label">
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

      {loading && <p className="status-line">Loading district data…</p>}
      {error && (
        <p className="status-line error">
          Could not load this view: {error instanceof Error ? error.message : String(error)}
        </p>
      )}

      <div className="map-area">
        <div ref={mapContainer} className="map" />
        <Legend />

        {selected && (
          <div className="district-panel" role="dialog" aria-label={`${selected.name} detail`}>
            <div className="district-panel-header">
              <h2>{selected.name}</h2>
              <button
                type="button"
                className="district-panel-close"
                aria-label="Close district detail"
                onClick={() => setSelected(null)}
              >
                ✕
              </button>
            </div>

            {selected.row ? (
              <>
                <dl>
                  <dt>Actual yield</dt>
                  <dd>{formatKgHa(selected.row.actual_yield_kg_ha)}</dd>
                  <dt>Attainable yield</dt>
                  <dd>{formatKgHa(selected.row.attainable_yield_kg_ha)}</dd>
                  <dt>Yield gap</dt>
                  <dd>{formatPercent(selected.row.yield_gap_pct)}</dd>
                </dl>
                {selected.row.reliability !== 'ok' && (
                  <p className="reliability-note">
                    Reliability: {selected.row.reliability.replace(/_/g, ' ')}. Too few
                    surveyed plots for a precise estimate.
                  </p>
                )}
              </>
            ) : (
              <p className="district-panel-hint">
                No data for {CROP_LABELS[crop].toLowerCase()} in Season {season} {year} here.
              </p>
            )}
            <Link
              className="district-panel-link"
              to={`/districts/${selected.code}?crop=${crop}&season=${season}&year=${year}`}
            >
              View full district profile
            </Link>
          </div>
        )}
      </div>

      <footer className="footer-strip">
        AgriTwin Rwanda. NISR 2026 Big Data Hackathon. Not official NISR statistics.
      </footer>
    </div>
  )
}
