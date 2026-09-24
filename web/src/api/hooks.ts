import { useQuery } from '@tanstack/react-query'
import { apiGet } from './client'
import type { Crop, DistrictProperties, Season, YieldGapRow } from './types'
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
