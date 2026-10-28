import { describe, expect, it } from 'vitest'
import { clockShiftAt, countryAt, parseGrid } from '../maps/countries'

// Three squares of 1000 m west to east: Germany (5), the square between (the export gives it the nearest's,
// Germany), Finland (23); a square with none near; and their time zones.
const grid = parseGrid({
  cell: 1000,
  x: -1000,
  z: 0,
  width: 4,
  height: 1,
  cells: '05051700',
  baseZone: 120,
  zones: { '5': 120, '23': 180, '10': 60 },
})!

describe('the clock where the truck is', () => {
  it("reads the map export's grid", () => {
    expect(grid.cells).toEqual(new Uint8Array([5, 5, 23, 0]))
    expect(parseGrid({ cell: 1000, x: 0, z: 0, width: 2, height: 1, cells: '05' })).toBeNull()
    expect(parseGrid(null)).toBeNull()
  })

  it("finds the country of the truck's square", () => {
    expect(countryAt(grid, -500, 500)).toBe(5)
    expect(countryAt(grid, 1500, 500)).toBe(23)
    expect(countryAt(grid, 500, 500)).toBe(5)
    // None near, and off the grid: none.
    expect(countryAt(grid, 2500, 500)).toBe(0)
    expect(countryAt(grid, 90_000, 500)).toBe(0)
    expect(countryAt(grid, -1500, 500)).toBe(0)
  })

  it("runs an hour on in Finland, as the game's clock, and as the game's time in central Europe", () => {
    expect(clockShiftAt(grid, 1500, 500)).toBe(60)
    expect(clockShiftAt(grid, -500, 500)).toBe(0)
    // Off the grid, or a country without a zone: the game's time.
    expect(clockShiftAt(grid, 90_000, 500)).toBe(0)
  })

  it("uses ATS's MDT economy clock instead of the ETS2 CEST clock", () => {
    const states = parseGrid({
      cell: 1000,
      x: 0,
      z: 0,
      width: 3,
      height: 1,
      cells: '010712',
      zones: { '1': -420, '7': -360, '18': -300 },
      baseZone: -360,
    })!
    expect(clockShiftAt(states, 500, 500)).toBe(-60)
    expect(clockShiftAt(states, 1500, 500)).toBe(0)
    expect(clockShiftAt(states, 2500, 500)).toBe(60)
    expect(clockShiftAt(states, 90_000, 500)).toBe(0)
  })

  it('puts the sampled North Platte SDK clock one hour ahead when local time zones are enabled', () => {
    const northPlatte = parseGrid({
      cell: 1000,
      x: -20000,
      z: -12000,
      width: 1,
      height: 1,
      cells: '12',
      zones: { '18': -300 },
      baseZone: -360,
    })!
    const sdkTime = 18438 // Actual read-only sample: day 12, 19:18 in the economy's MDT.
    expect(sdkTime + clockShiftAt(northPlatte, -19361.21513, -11433.91423)).toBe(18498) // 20:18 CDT.
  })

  it('honours an exported economy baseline supplied by another game or map mod', () => {
    const changedEconomy = parseGrid({
      cell: 1000,
      x: 0,
      z: 0,
      width: 1,
      height: 1,
      cells: '12',
      zones: { '18': -300 },
      baseZone: -420,
    })!
    expect(clockShiftAt(changedEconomy, 500, 500)).toBe(120)
  })

  it('does not guess an economy baseline for an old or incomplete country export', () => {
    const oldExport = parseGrid({
      cell: 1000,
      x: 0,
      z: 0,
      width: 1,
      height: 1,
      cells: '12',
      zones: { '18': -300 },
    })!
    expect(clockShiftAt(oldExport, 500, 500)).toBe(0)
  })
})
