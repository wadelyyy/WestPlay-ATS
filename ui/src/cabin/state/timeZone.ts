import { type CountryGrid, clockShiftAt, parseGrid } from '../maps/countries'
import { loadMapData, onMapChange } from '../maps/mapData'
import { useLive } from './store'

/**
 * The clock where the truck is, while the player's profile has the game's time zones on
 * (Options › Gameplay › Time zones, its `g_time_zones`). Off, no geographic shift is applied. On, the
 * country's time zone is compared with the mounted economy's `default_time_zone`; ATS and ETS2 use
 * different reference zones, and mods may replace them. Both zones come from the map export
 * (`countries.json` beside the tiles). Every cab clock adds the resulting `clockShift` through
 * shared/host.ts `cabClock`, separately from the Convoy server's time offset.
 * Country secondary timezone rectangles are not represented by this grid yet.
 */

/** Each grid (by its file's address), loaded once. */
const grids = new Map<string, Promise<CountryGrid | null>>()

function loadGrid(url: string): Promise<CountryGrid | null> {
  let grid = grids.get(url)
  if (!grid) {
    grid = fetch(url)
      .then((response) => (response.ok ? response.json() : null))
      .then(parseGrid)
      .catch(() => null)
    grids.set(url, grid)
  }
  return grid
}

/** Keeps the cab's clock on the truck's country's time as it drives, from now on. Returns the function that
 * stops it. */
export function followTimeZone(): () => void {
  // The map's grid (`null`: none yet, or a map without one), and the file it's from. The host tells the
  // page its map, the profile's option and the truck's place in any order: the shift is worked out again
  // as each comes.
  let grid: CountryGrid | null = null
  let gridFrom: string | null | undefined
  const apply = () => {
    const { timeZones, telemetry, clockShift } = useLive.getState()
    const shift = timeZones && grid && telemetry ? clockShiftAt(grid, telemetry.x, telemetry.z) : 0
    // Set only when it changes: setting it calls this again.
    if (shift !== clockShift) useLive.setState({ clockShift: shift })
  }
  const followMap = async () => {
    const map = await loadMapData()
    const from = map?.countries ?? null
    if (from === gridFrom) return
    gridFrom = from
    const loaded = from ? await loadGrid(from) : null
    // Another map meanwhile: its own load sets it.
    if (gridFrom !== from) return
    grid = loaded
    apply()
  }
  const stopLive = useLive.subscribe(apply)
  const stopMap = onMapChange(() => void followMap())
  void followMap()
  return () => {
    stopLive()
    stopMap()
    useLive.setState({ clockShift: 0 })
  }
}
