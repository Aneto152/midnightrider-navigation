# Status: Astronomical Plugin Deployment - 2026-04-20

## What We've Done
- ✅ Created signalk-astronomical-direct.js plugin (sends directly to InfluxDB)
- ✅ Copied plugin to Docker container
- ✅ Installed npm dependencies (suncalc, axios) in container
- ✅ Created config file with InfluxDB credentials
- ✅ Restarted Signal K multiple times
- ✅ Test showed manual InfluxDB POST works (HTTP 204)

## Current Problem
- ❌ Plugin is not executing or sending data
- ❌ No logs from plugin in Signal K logs
- ❌ No environment.* data in InfluxDB

## Architecture Issue
Signal K loads plugins from npm packages in `/home/node/.signalk/node_modules/`, not from `/home/node/.signalk/plugins/`

We installed the plugin as an npm package but it still doesn't load/execute.

## Root Causes to Investigate
1. Plugin module export format might be wrong
2. Signal K plugin discovery system might not recognize it
3. Plugin.start() might have an error that's silently caught
4. Package.json signalk-plugin-id format might be incorrect

## Next Steps
Option 1: Debug why plugin isn't recognized
Option 2: Use Option A (Signal K schema registration) instead
Option 3: Create ultra-simple minimal plugin to test plugin system

## Files
- Plugin: /home/aneto/docker/signalk/plugins/signalk-astronomical-direct.js
- Config: /home/node/.signalk/plugin-config-data/@aneto-signalk-astronomical-direct.json
- Package: @aneto/signalk-astronomical-direct (installed via npm)

## Commit
Last code: signalk-astronomical-direct.js with direct InfluxDB sends
