import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { staticGet } from './staticFallback'

const FILES: Record<string, unknown> = {
  'meta.json': { crops: ['maize'], data_version: '2026.10.0' },
  'districts.geojson': {
    features: [
      { properties: { district_code: 11, district_name: 'Nyarugenge' } },
      { properties: { district_code: 12, district_name: 'Gasabo' } },
    ],
  },
  'yield_gap.json': [
    { district_code: 11, crop: 'maize', season: 'A', year: 2024, yield_gap_pct: 20 },
    { district_code: 11, crop: 'beans', season: 'A', year: 2024, yield_gap_pct: 30 },
    { district_code: 12, crop: 'maize', season: 'A', year: 2024, yield_gap_pct: 40 },
  ],
  'district_yield.json': [
    { geo_level: 'district', geo_code: '11.0', crop: 'maize', season: 'A', year: 2023, yield_kg_ha: 900 },
    { geo_level: 'district', geo_code: '11.0', crop: 'maize', season: 'A', year: 2024, yield_kg_ha: 950 },
    { geo_level: 'national', geo_code: 'RWA', crop: 'maize', season: 'A', year: 2024, yield_kg_ha: 1000 },
  ],
  'drivers_by_district.json': [
    { district_code: 11, crop: 'maize', feature: 'improved_seed', mean_abs_shap: 0.3 },
    { district_code: 11, crop: 'maize', feature: 'soil_ph', mean_abs_shap: 0.1 },
  ],
  'district_zones.json': [
    { nisr_district_code: 11, zone_id: 0 },
    { nisr_district_code: 12, zone_id: 0 },
  ],
  'scenario.json': [
    { district_code: 11, crop: 'maize', improved_seed: true, mean_yield_kg_ha: 1200 },
    { district_code: 12, crop: 'maize', improved_seed: true, mean_yield_kg_ha: 1100 },
  ],
}

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const file = url.replace('/static-data/', '')
      if (!(file in FILES)) return { ok: false } as Response
      return { ok: true, json: async () => FILES[file] } as Response
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('staticGet', () => {
  it('returns the whole file for /meta with no filtering', async () => {
    const result = await staticGet('/meta')
    expect(result).toEqual(FILES['meta.json'])
  })

  it('filters /yield-gap by crop, season and year', async () => {
    const result = await staticGet<{ district_code: number }[]>('/yield-gap', {
      crop: 'maize',
      season: 'A',
      year: 2024,
    })
    expect(result.map((r) => r.district_code)).toEqual([11, 12])
  })

  it('filters /scenario/{code} by district and crop', async () => {
    const result = await staticGet<{ district_code: number }[]>('/scenario/11', { crop: 'maize' })
    expect(result).toHaveLength(1)
    expect(result[0].district_code).toBe(11)
  })

  it('composes /districts/{code}/profile from four files like the API does', async () => {
    const result = await staticGet<{
      district_name: string
      yield_trend: { year: number }[]
      top_drivers: { feature: string }[]
      peer_districts: { district_code: number }[]
    }>('/districts/11/profile', { crop: 'maize', season: 'A' })

    expect(result.district_name).toBe('Nyarugenge')
    expect(result.yield_trend.map((r) => r.year)).toEqual([2023, 2024])
    expect(result.top_drivers[0].feature).toBe('improved_seed')
    expect(result.peer_districts).toEqual([{ district_code: 12, district_name: 'Gasabo' }])
  })

  it('throws for a path with no offline mirror', async () => {
    await expect(staticGet('/briefs/11.pdf')).rejects.toThrow()
  })
})
