import { useEffect, useMemo, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useDistrictBoundaries, useYieldGap } from '../api/hooks'
import type { Crop, Season, YieldGapRow } from '../api/types'
import { RELIABILITY_GREY, yieldGapColor } from '../lib/colors'
import { NISR_TO_GAUL } from '../lib/districtCrosswalk'
import { formatKgHa, formatPercent } from '../lib/format'

const CROPS: Crop[] = ['maize', 'beans', 'irish_potato', 'sorghum']
const SEASONS: Season[] = ['A', 'B']

export default function MapPage() {
  const [crop, setCrop] = useState<Crop>('beans')
  const [season, setSeason] = useState<Season>('B')
  const [year, setYear] = useState(2025)
  const [hovered, setHovered] = useState<YieldGapRow | null>(null)

  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const [mapReady, setMapReady] = useState(false)

  const boundaries = useDistrictBoundaries()
  const yieldGap = useYieldGap(crop, season, year)

  const byDistrict = useMemo(() => {
    const rows = new Map<number, YieldGapRow>()
    for (const row of yieldGap.data ?? []) {
      const gaulCode = NISR_TO_GAUL[row.district_code]
      if (gaulCode != null) rows.set(gaulCode, row)
    }
    return rows
  }, [yieldGap.data])

  useEffect(() => {
    if (!mapContainer.current) return
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: [29.9, -1.95],
      zoom: 8,
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
        const row = byDistrict.get(f.properties.gaul_district_code)
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
      paint: { 'fill-color': ['get', 'fillColor'], 'fill-opacity': 0.75 },
    })
    m.addLayer({
      id: 'districts-outline',
      type: 'line',
      source: 'districts',
      paint: { 'line-color': '#333', 'line-width': 1 },
    })

    m.on('mousemove', 'districts-fill', (e) => {
      const feature = e.features?.[0]
      if (!feature) return
      const code = feature.properties?.gaul_district_code as number
      setHovered(byDistrict.get(code) ?? null)
      m.getCanvas().style.cursor = 'pointer'
    })
    m.on('mouseleave', 'districts-fill', () => {
      setHovered(null)
      m.getCanvas().style.cursor = ''
    })
  }, [mapReady, boundaries.data, byDistrict])

  const loading = boundaries.isLoading || yieldGap.isLoading
  const error = boundaries.error || yieldGap.error

  return (
    <div className="map-page">
      <div className="filter-bar" role="toolbar" aria-label="Filters">
        <label>
          Crop
          <select value={crop} onChange={(e) => setCrop(e.target.value as Crop)}>
            {CROPS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label>
          Season
          <select value={season} onChange={(e) => setSeason(e.target.value as Season)}>
            {SEASONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          Year
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            min={2019}
            max={2025}
          />
        </label>
      </div>

      <p className="model-badge">Model-based estimate, not official statistics</p>

      {loading && <p>Loading...</p>}
      {error && <p className="error">Error: {error instanceof Error ? error.message : String(error)}</p>}

      <div ref={mapContainer} className="map" />

      {hovered && (
        <div className="district-tooltip">
          <strong>District {hovered.district_code}</strong>
          <div>Actual yield: {formatKgHa(hovered.actual_yield_kg_ha)}</div>
          <div>Attainable yield: {formatKgHa(hovered.attainable_yield_kg_ha)}</div>
          <div>Yield gap: {formatPercent(hovered.yield_gap_pct)}</div>
          {hovered.reliability !== 'ok' && (
            <div className="reliability-note">Reliability: {hovered.reliability.replace(/_/g, ' ')}</div>
          )}
        </div>
      )}
    </div>
  )
}
