/** Thin aliases over the OpenAPI-generated schema (see `npm run gen:types`,
 * src/api/schema.ts), kept under these existing flat names so the rest of the app
 * doesn't need to know the generated schema's own nesting. Regenerate schema.ts (a
 * real API instance must be running locally first) whenever api/app/schemas.py
 * changes; a stale schema.ts is a tsc error at the next build, not a silent drift,
 * since every type below is a direct alias, not a re-declaration. */

import type { components } from './schema'

export type Crop = components['schemas']['Crop']
export type Season = components['schemas']['Season']
export type Reliability = components['schemas']['Reliability']

export type YieldGapRow = components['schemas']['YieldGapRow']
export type DriverRow = components['schemas']['DriverRow']
export type DistrictInfo = components['schemas']['DistrictInfo']
export type YearlyYield = components['schemas']['YearlyYield']
export type YearlyGap = components['schemas']['YearlyGap']
export type DistrictProfile = components['schemas']['DistrictProfile']
export type ScenarioRow = components['schemas']['ScenarioRow']
export type NowcastRow = components['schemas']['NowcastRow']
export type NowcastCurveRow = components['schemas']['NowcastCurveRow']
export type BacktestRow = components['schemas']['BacktestRow']
export type KpiRow = components['schemas']['KpiRow']
export type MetaResponse = components['schemas']['MetaResponse']

/** Not part of api/app/schemas.py: these are GeoJSON Feature `properties`, from
 * /districts' GeoJSONResponse (a generic FeatureCollection in the OpenAPI schema,
 * so openapi-typescript can't derive this specific shape). Sourced from
 * src/agritwin/export/geo.py's actual output columns. */
export interface DistrictProperties {
  district_name: string
  gaul_district_code: number
  district_code: number
}
