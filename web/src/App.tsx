import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { FeatureCollection, Geometry } from 'geojson'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

interface DistrictProperties {
  district_name: string
  gaul_district_code: number
}

type DistrictCollection = FeatureCollection<Geometry, DistrictProperties>

export default function App() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [districtCount, setDistrictCount] = useState(0)

  useEffect(() => {
    if (!mapContainer.current) return

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: [29.5, -2],
      zoom: 7,
    })

    map.current.on('load', async () => {
      try {
        const response = await fetch(`${API_BASE}/districts`)
        const data: DistrictCollection = await response.json()
        setDistrictCount(data.features.length)

        map.current!.addSource('districts', {
          type: 'geojson',
          data,
        })

        map.current!.addLayer({
          id: 'districts-fill',
          type: 'fill',
          source: 'districts',
          paint: {
            'fill-color': '#088',
            'fill-opacity': 0.4,
          },
        })

        map.current!.addLayer({
          id: 'districts-outline',
          type: 'line',
          source: 'districts',
          paint: {
            'line-color': '#088',
            'line-width': 2,
          },
        })

        setLoading(false)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load districts')
        setLoading(false)
      }
    })

    return () => {
      map.current?.remove()
    }
  }, [])

  return (
    <div className="App">
      <header className="header">
        <h1>AgriTwin Rwanda - Districts Map</h1>
        {loading && <p>Loading...</p>}
        {error && <p className="error">Error: {error}</p>}
        {!loading && !error && <p>Showing {districtCount} districts</p>}
      </header>
      <div ref={mapContainer} className="map" />
    </div>
  )
}
