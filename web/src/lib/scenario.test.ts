import { describe, expect, it } from 'vitest'
import { DEFAULT_LEVERS, findScenarioRow } from './scenario'
import type { ScenarioRow } from '../api/types'

function row(overrides: Partial<ScenarioRow>): ScenarioRow {
  return {
    crop: 'maize',
    district_code: 11,
    improved_seed: false,
    inorganic_fert: false,
    organic_fert: false,
    irrigated: false,
    mean_yield_kg_ha: 1000,
    ci_low: 900,
    ci_high: 1100,
    n_plots: 50,
    reliability: 'ok',
    ...overrides,
  }
}

describe('findScenarioRow', () => {
  it('finds the row matching all four lever off', () => {
    const rows = [row({}), row({ improved_seed: true, mean_yield_kg_ha: 1200 })]
    expect(findScenarioRow(rows, DEFAULT_LEVERS)?.mean_yield_kg_ha).toBe(1000)
  })

  it('finds the row matching a specific lever combination', () => {
    const rows = [
      row({}),
      row({ improved_seed: true, irrigated: true, mean_yield_kg_ha: 1500 }),
    ]
    const result = findScenarioRow(rows, {
      ...DEFAULT_LEVERS,
      improved_seed: true,
      irrigated: true,
    })
    expect(result?.mean_yield_kg_ha).toBe(1500)
  })

  it('returns undefined when no row matches', () => {
    const rows = [row({})]
    expect(findScenarioRow(rows, { ...DEFAULT_LEVERS, improved_seed: true })).toBeUndefined()
  })
})
