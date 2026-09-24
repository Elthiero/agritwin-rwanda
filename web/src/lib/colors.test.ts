import { describe, expect, it } from 'vitest'
import { yieldGapColor } from './colors'

describe('yieldGapColor', () => {
  it('returns the first stop color at 0', () => {
    expect(yieldGapColor(0)).toBe('rgb(253, 231, 37)')
  })

  it('returns the last stop color at 100', () => {
    expect(yieldGapColor(100)).toBe('rgb(68, 1, 84)')
  })

  it('clamps out-of-range values', () => {
    expect(yieldGapColor(-10)).toBe(yieldGapColor(0))
    expect(yieldGapColor(150)).toBe(yieldGapColor(100))
  })
})
