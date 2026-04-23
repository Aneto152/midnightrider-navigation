/**
 * Signal K Plugin - Performance Polars Analysis
 * 
 * Injecte J/30 polaires dans Signal K et calcule:
 * - polarSpeed: vitesse théorique pour conditions actuelles
 * - polarSpeedRatio: efficacité (speed actual / target)
 * - velocityMadeGood: VMG
 * - targetSpeed: vitesse cible optimale
 * - targetAngle: angle optimal
 * 
 * @author Aneto (MidnightRider J/30)
 * @version 1.0.0
 * @license MIT
 */

const j30Polars = require('./j30-polars-data.json');

module.exports = function(app) {
  let plugin = {
    id: 'signalk-performance-polars',
    name: 'Performance Polars Analysis',
    description: 'Calculate performance metrics against J/30 polars',
    version: '1.0.0',
    
    schema: {
      type: 'object',
      title: 'Performance Polars Configuration',
      required: [],
      properties: {
        enabled: {
          type: 'boolean',
          title: 'Enable Plugin',
          default: true
        },
        debug: {
          type: 'boolean',
          title: 'Debug Logging',
          default: false
        },
        updateInterval: {
          type: 'number',
          title: 'Update Interval (ms)',
          description: 'How often to calculate performance metrics',
          default: 1000
        }
      }
    }
  };

  plugin.start = function(options, restartPlugin) {
    const debug = options.debug || false;
    const updateInterval = options.updateInterval || 1000;

    app.debug('[Polars] Plugin started');
    app.debug(`[Polars] Update interval: ${updateInterval}ms`);

    // Initialize performance object in Signal K
    if (!app.signalk.self.navigation) {
      app.signalk.self.navigation = {};
    }
    if (!app.signalk.self.navigation.performance) {
      app.signalk.self.navigation.performance = {};
    }

    // Load polars into Signal K
    const polarUUID = 'j30-production-2024';
    app.signalk.self.navigation.performance.polars = {
      [polarUUID]: j30Polars
    };
    app.signalk.self.navigation.performance.activePolar = polarUUID;
    app.signalk.self.navigation.performance.activePolarData = j30Polars;

    if (debug) {
      app.debug(`[Polars] Loaded J/30 polars: ${j30Polars.name}`);
      app.debug(`[Polars] Wind speeds: ${j30Polars.windData.map(w => w.trueWindSpeed).join(', ')}`);
    }

    // Calculate metrics every updateInterval ms
    const calcInterval = setInterval(() => {
      calculatePerformanceMetrics();
    }, updateInterval);

    // Also calculate on startup
    calculatePerformanceMetrics();

    function calculatePerformanceMetrics() {
      try {
        // Get current values from Signal K
        const stw = app.getSelfPath('navigation.speedThroughWater.value');
        const tws = app.getSelfPath('environment.wind.speedTrue.value');
        const twa = app.getSelfPath('environment.wind.angleTrueWater.value');
        const heading = app.getSelfPath('navigation.headingTrue.value');
        const cog = app.getSelfPath('navigation.courseOverGround.value');
        const sog = app.getSelfPath('navigation.speedOverGround.value');

        // Skip if missing required values
        if (stw === undefined || stw === null || 
            tws === undefined || tws === null || 
            twa === undefined || twa === null) {
          return;
        }

        // Convert Wind Speed from m/s to knots
        const twsKnots = tws * 1.94384;
        const stwKnots = stw * 1.94384;

        if (debug && Math.random() < 0.1) { // Log 10% of updates
          app.debug(`[Polars] STW: ${stwKnots.toFixed(2)}kt, TWS: ${twsKnots.toFixed(2)}kt, TWA: ${(twa * 180 / Math.PI).toFixed(1)}°`);
        }

        // Find polar speed for current conditions
        const polarSpeed = interpolatePolarSpeed(twsKnots, twa, j30Polars);
        const polarSpeedMs = polarSpeed / 1.94384; // Convert back to m/s for Signal K

        // Calculate efficiency
        const efficiency = polarSpeed > 0 ? stwKnots / polarSpeed : 0;

        // Calculate VMG (Velocity Made Good)
        // VMG = STW * cos(TWA)
        // Positive = upwind, negative = downwind
        const vmg = stwKnots * Math.cos(twa);

        // Find optimal angle and speed for current wind
        const optimal = findOptimalAngle(twsKnots, j30Polars);

        // Build updates array
        const updates = [
          {
            path: 'navigation.performance.polarSpeed',
            value: polarSpeedMs,
            timestamp: new Date().toISOString()
          },
          {
            path: 'navigation.performance.polarSpeedRatio',
            value: Math.round(efficiency * 10000) / 10000, // 4 decimal places
            timestamp: new Date().toISOString()
          },
          {
            path: 'navigation.performance.velocityMadeGood',
            value: vmg / 1.94384, // Convert to m/s
            timestamp: new Date().toISOString()
          },
          {
            path: 'navigation.performance.targetSpeed',
            value: optimal.speed / 1.94384, // Convert to m/s
            timestamp: new Date().toISOString()
          },
          {
            path: 'navigation.performance.targetAngle',
            value: optimal.angle,
            timestamp: new Date().toISOString()
          }
        ];

        // Send updates to Signal K
        app.handleMessage(null, {
          updates: [{
            source: { label: 'performance-polars' },
            timestamp: new Date().toISOString(),
            values: updates
          }]
        });

      } catch (err) {
        app.error(`[Polars] Error calculating metrics: ${err.message}`);
        if (debug) {
          app.debug(`[Polars] Stack: ${err.stack}`);
        }
      }
    }

    function interpolatePolarSpeed(twsKnots, twaDegrees, polarTable) {
      // Convert TWA from radians to degrees for lookup
      const twaDegreesVal = Math.abs(twaDegrees * 180 / Math.PI);

      // Find two nearest wind speeds
      let windData1 = null;
      let windData2 = null;
      let windSpeed1 = 0;
      let windSpeed2 = 0;

      for (let i = 0; i < polarTable.windData.length - 1; i++) {
        if (polarTable.windData[i].trueWindSpeed <= twsKnots &&
            polarTable.windData[i + 1].trueWindSpeed >= twsKnots) {
          windData1 = polarTable.windData[i];
          windData2 = polarTable.windData[i + 1];
          windSpeed1 = windData1.trueWindSpeed;
          windSpeed2 = windData2.trueWindSpeed;
          break;
        }
      }

      // If exact wind speed match, use that
      if (!windData1 || !windData2) {
        const exactWind = polarTable.windData.reduce((prev, curr) => {
          return Math.abs(curr.trueWindSpeed - twsKnots) < 
                 Math.abs(prev.trueWindSpeed - twsKnots) ? curr : prev;
        });
        windData1 = exactWind;
        windData2 = exactWind;
        windSpeed1 = windSpeed2 = exactWind.trueWindSpeed;
      }

      // Find speed at TWA from both wind data
      let speed1 = getSpeedAtAngle(twaDegreesVal, windData1);
      let speed2 = getSpeedAtAngle(twaDegreesVal, windData2);

      // Linear interpolate between wind speeds
      let polarSpeed;
      if (windSpeed1 === windSpeed2) {
        polarSpeed = speed1;
      } else {
        const windRatio = (twsKnots - windSpeed1) / (windSpeed2 - windSpeed1);
        polarSpeed = speed1 + windRatio * (speed2 - speed1);
      }

      return Math.abs(polarSpeed);
    }

    function getSpeedAtAngle(angleInDegrees, windData) {
      // Find two nearest angles in angleData
      const angleInRadians = angleInDegrees * Math.PI / 180;
      
      let angle1 = null;
      let angle2 = null;
      let speed1 = 0;
      let speed2 = 0;

      for (let i = 0; i < windData.angleData.length - 1; i++) {
        if (windData.angleData[i][0] <= angleInRadians &&
            windData.angleData[i + 1][0] >= angleInRadians) {
          angle1 = windData.angleData[i];
          angle2 = windData.angleData[i + 1];
          break;
        }
      }

      // If exact match, use that
      if (!angle1 || !angle2) {
        const exactAngle = windData.angleData.reduce((prev, curr) => {
          return Math.abs(curr[0] - angleInRadians) < 
                 Math.abs(prev[0] - angleInRadians) ? curr : prev;
        });
        return exactAngle[1];
      }

      // Linear interpolate between angles
      const angleRatio = (angleInRadians - angle1[0]) / (angle2[0] - angle1[0]);
      return angle1[1] + angleRatio * (angle2[1] - angle1[1]);
    }

    function findOptimalAngle(twsKnots, polarTable) {
      // Find best VMG angle for current wind
      let bestVMG = 0;
      let bestAngle = 0;
      let bestSpeed = 0;

      // Get closest wind speed data
      const windData = polarTable.windData.reduce((prev, curr) => {
        return Math.abs(curr.trueWindSpeed - twsKnots) < 
               Math.abs(prev.trueWindSpeed - twsKnots) ? curr : prev;
      });

      // Check all angles
      for (let i = 0; i < windData.angleData.length; i++) {
        const angle = windData.angleData[i][0];
        const speed = windData.angleData[i][1];
        
        // Only consider upwind angles (0 to PI)
        if (angle <= Math.PI) {
          const vmg = speed * Math.cos(angle);
          
          if (vmg > bestVMG) {
            bestVMG = vmg;
            bestAngle = angle;
            bestSpeed = speed;
          }
        }
      }

      return {
        angle: bestAngle,
        speed: bestSpeed,
        vmg: bestVMG
      };
    }

    plugin.stop = function() {
      clearInterval(calcInterval);
      app.debug('[Polars] Plugin stopped');
    };

    return plugin;
  };

  return plugin;
};
