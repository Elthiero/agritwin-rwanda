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
  district_code: number
}

export interface DriverRow {
  crop: Crop
  district_code: number | null
  feature: string
  mean_abs_shap: number
  direction: string
  n_plots: number | null
  reliability: Reliability | null
}

export interface DistrictInfo {
  district_code: number
  district_name: string
}

export interface YearlyYield {
  year: number
  yield_kg_ha: number
  yield_kg_ha_ci_low: number | null
  yield_kg_ha_ci_high: number | null
  reliability: Reliability
}

export interface YearlyGap {
  year: number
  actual_yield_kg_ha: number
  attainable_yield_kg_ha: number | null
  yield_gap_kg_ha: number | null
  yield_gap_pct: number | null
  reliability: Reliability
}

export interface DistrictProfile {
  district_code: number
  district_name: string
  crop: Crop
  yield_trend: YearlyYield[]
  gap_trend: YearlyGap[]
  top_drivers: DriverRow[]
  peer_districts: DistrictInfo[]
}

export interface ScenarioRow {
  crop: Crop
  district_code: number
  improved_seed: boolean
  inorganic_fert: boolean
  organic_fert: boolean
  irrigated: boolean
  mean_yield_kg_ha: number
  ci_low: number
  ci_high: number
  n_plots: number
  reliability: Reliability
}

export interface BacktestRow {
  crop: Crop
  lead_months: number
  model: string
  mape_pct: number
  mape_std_across_years: number
  mae_kg_ha: number
  n_years_tested: number
}

export interface MetaResponse {
  crops: Crop[]
  seasons: Season[]
  years: number[]
  districts: DistrictInfo[]
  data_version: string
  last_updated: string | null
}

export interface NowcastRow {
  district_code: number
  crop: Crop
  season: Season
  year: number
  lead_months: number
  model: string
  predicted_yield_kg_ha: number
  ci_low: number
  ci_high: number
  actual_yield_kg_ha: number | null
  is_backtest: boolean
  reliability: Reliability
}
