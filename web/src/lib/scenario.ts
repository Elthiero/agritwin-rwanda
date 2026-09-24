import type { ScenarioRow } from '../api/types'

export interface LeverState {
  improved_seed: boolean
  inorganic_fert: boolean
  organic_fert: boolean
  irrigated: boolean
}

export const DEFAULT_LEVERS: LeverState = {
  improved_seed: false,
  inorganic_fert: false,
  organic_fert: false,
  irrigated: false,
}

/** Picks the one precomputed lever-grid row matching this exact combination, out of the
 * 16 src/agritwin/models/scenario.py wrote for this district x crop. Client-side lookup
 * only: nothing here re-runs the model, matching CLAUDE.md rule 5 (model-based, not a
 * live simulation). */
export function findScenarioRow(
  rows: ScenarioRow[],
  levers: LeverState,
): ScenarioRow | undefined {
  return rows.find(
    (row) =>
      row.improved_seed === levers.improved_seed &&
      row.inorganic_fert === levers.inorganic_fert &&
      row.organic_fert === levers.organic_fert &&
      row.irrigated === levers.irrigated,
  )
}
