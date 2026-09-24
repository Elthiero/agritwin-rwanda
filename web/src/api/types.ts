/** Hand-written to match api/app/schemas.py's response models. Not yet generated from
 * OpenAPI (web/CLAUDE.md's documented `npm run gen:types` script doesn't exist yet);
 * a known stopgap, not a permanent choice. */

export type Crop = 'maize' | 'beans' | 'irish_potato' | 'sorghum'
export type Season = 'A' | 'B'
export type Reliability = 'ok' | 'use_with_caution' | 'suppressed'

export interface YieldGapRow {
  district_code: number
  crop: Crop
  season: Season
  year: number
  actual_yield_kg_ha: number
  actual_yield_kg_ha_ci_low: number | null
  actual_yield_kg_ha_ci_high: number | null
  attainable_yield_kg_ha: number | null
  yield_gap_kg_ha: number | null
  yield_gap_pct: number | null
  n_plots: number
  reliability: Reliability
}

export interface DistrictProperties {
  district_name: string
  gaul_district_code: number
}
