import { describe, expect, it } from 'vitest'
import { formatKgHa, formatPercent } from './format'

describe('formatKgHa', () => {
  it('formats a positive number with thousands separator and unit', () => {
    expect(formatKgHa(1400)).toBe('1,400 kg/ha')
  })

  it('rounds to the nearest whole number', () => {
    expect(formatKgHa(899.6)).toBe('900 kg/ha')
  })

  it('renders null and undefined as an em dash, not 0', () => {
    expect(formatKgHa(null)).toBe('—')
    expect(formatKgHa(undefined)).toBe('—')
  })

  it('renders NaN as an em dash, not "NaN kg/ha"', () => {
    expect(formatKgHa(NaN)).toBe('—')
  })
})

describe('formatPercent', () => {
  it('formats with one decimal by default', () => {
    expect(formatPercent(7.7)).toBe('7.7%')
  })

  it('respects a custom digit count', () => {
    expect(formatPercent(7.666, 2)).toBe('7.67%')
  })

  it('renders null as an em dash, not 0%', () => {
    expect(formatPercent(null)).toBe('—')
  })
})
