# CPU Temperature Plugin - Work in Progress

**Date:** 2026-04-22 16:14 EDT  
**Status:** ⚠️ WIP - Plugin loads but data path needs fixing

## What Works

✅ Plugin file created: `/home/aneto/.signalk/plugins/signalk-rpi-cpu-temp.js`
✅ Module installed in npm: `~/.signalk/node_modules/signalk-rpi-cpu-temp/`
✅ Config added to `settings.json`
✅ Plugin loads (visible in Signal K startup)
✅ Temperature reading works (execSync vcgencmd works)

## Current Issue

When plugin is active, `/signalk/v1/api/vessels/self` returns empty or incomplete data.
Likely cause: Delta message structure is invalid or path is wrong.

## Solution

Need to debug:
1. The delta message format
2. Correct Signal K path for environment.system.cpu.temperature
3. Ensure values are properly serialized

## Alternative: Direct Bash Script

For now, can monitor temp outside Signal K:

```bash
vcgencmd measure_temp
# Or watch it:
watch -n 5 "vcgencmd measure_temp"
```

## Future Work

Once path issue fixed:
- Display CPU temp in Grafana
- Set alerts for high temp (>80°C)
- Display on iPad cockpit
- Track temperature trends over time

