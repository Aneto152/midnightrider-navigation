/**
 * N2K Conversion: B&G Performance Data
 * PGN 130824 — Navico/B&G Proprietary
 * Displays on Vulcan 7, Zeus, Triton2
 */
module.exports = {
  title: 'B&G Performance Data (PGN 130824)',
  description: 'Sends polar performance, leeway and current to B&G displays',
  optionKey: 'bandgPerformance',
  keys: [
    'navigation.leeway',
    'environment.current.setTrue',
    'environment.current.drift',
    'performance.polarSpeed',
    'performance.polarSpeedRatio'
  ],
  resendPeriod: 1000,
  isBandG: true,
  callback: function(leeway, currentSet, currentDrift, polarSpeed, polarRatio) {
    if (leeway == null && currentSet == null && polarSpeed == null) return null
    return [{
      pgn: 130824,
      'Leeway': leeway || 0,
      'Current Set': currentSet || 0,
      'Current Drift': currentDrift || 0,
      'Polar Speed': polarSpeed || 0,
      'Polar Ratio': polarRatio || 0
    }]
  }
}
