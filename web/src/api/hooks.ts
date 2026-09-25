import { useQuery } from '@tanstack/react-query'
import { apiGet } from './client'
import type {
  BacktestRow,
  Crop,
  DistrictProfile,
  DistrictProperties,
  MetaResponse,
  NowcastRow,
  ScenarioRow,
  Season,
  YieldGapRow,
} from './types'
import type { FeatureCollection, Geometry } from 'geojson'

export type DistrictCollection = FeatureCollection<Geometry, DistrictProperties>

export function useDistrictBoundaries() {
  return useQuery({
    queryKey: ['districts'],
    queryFn: () => apiGet<DistrictCollection>('/districts'),
    staleTime: Infinity,
  })
}

export function useYieldGap(crop: Crop, season: Season, year: number) {
  return useQuery({
    queryKey: ['yield-gap', crop, season, year],
    queryFn: () => apiGet<YieldGapRow[]>('/yield-gap', { crop, season, year }),
  })
}

export function useDistrictProfile(code: number, crop: Crop, season: Season) {
  return useQuery({
    queryKey: ['district-profile', code, crop, season],
    queryFn: () => apiGet<DistrictProfile>(`/districts/${code}/profile`, { crop, season }),
  })
}

export function useScenario(code: number, crop: Crop, season: Season) {
  return useQuery({
    queryKey: ['scenario', code, crop, season],
    queryFn: () => apiGet<ScenarioRow[]>(`/scenario/${code}`, { crop, season }),
  })
}

// The API returns all districts for one crop x season x year x lead, matching
// /yield-gap's shape; the caller filters to its own district, same as useYieldGap.
export function useNowcast(crop: Crop, season: Season, year: number, lead: number) {
  return useQuery({
    queryKey: ['nowcast', crop, season, year, lead],
    queryFn: () => apiGet<NowcastRow[]>('/nowcast', { crop, season, year, lead }),
  })
}

export function useBacktest(crop: Crop, season: Season) {
  return useQuery({
    queryKey: ['backtest', crop, season],
    queryFn: () => apiGet<BacktestRow[]>('/backtest', { crop, season }),
  })
}

export function useMeta() {
  return useQuery({
    queryKey: ['meta'],
    queryFn: () => apiGet<MetaResponse>('/meta'),
    staleTime: Infinity,
  })
}
