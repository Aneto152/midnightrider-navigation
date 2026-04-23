/**
 * Signal K Current Calculator Plugin
 * 
 * Objective:
 *   - Calculate water current (velocity + direction) from GPS data
 *   - Inputs:
 *     • navigation.speedOverGround (GPS speed)
 *     • navigation.courseOverGroundTrue (GPS course)
 *     • navigation.speedThroughWater (calibrated loch speed)
 *     • navigation.headingTrue (boat heading)
 *   - Outputs:
 *     • environment.water.currentSpeed (m/s)
 *     • environment.water.currentDirection (rad, true)
 *     • navigation.performance.leeway (lateral drift)
 * 
 * Theory:
 *   GPS shows actual track over ground (SOG, COG)
 *   Loch shows water speed along boat heading (STW, heading)
 *   Difference = current effect
 *
 *   Vector decomposition:
 *   GPS_velocity = STW_velocity + Current_velocity
 *   Therefore:
 *   Current = GPS - STW (vector subtraction)
 *
 * Math:
 *   1. Convert heading/STW to velocity components (boat frame)
 *   2. Convert COG/SOG to velocity components (earth frame)
 *   3. Subtract: Current = SOG - STW (vector)
 *   4. Calculate magnitude (speed) and direction
 *   5. Calculate leeway (lateral drift angle)
 *
 * Author: MidnightRider AI Coach
 * Date: 2026-04-21
 */

module.exports = function(app) {
  const debug = true;
  const UPDATE_INTERVAL = 1000; // 1 Hz (match input rate)

  // Configuration
  let config = {
    enabled: true,
    debug: true,
    updateInterval: UPDATE_INTERVAL,
    
    // Input paths
    inputs: {
      sog: 'navigation.speedOverGround',           // GPS speed (m/s)
      cog: 'navigation.courseOverGroundTrue',      // GPS course (rad)
      stw: 'navigation.speedThroughWater',         // Loch speed calibrated (m/s)
      heading: 'navigation.headingTrue'            // Boat heading (rad)
    },
    
    // Output paths
    outputs: {
      currentSpeed: 'environment.water.currentSpeed',
      currentDirection: 'environment.water.currentDirection',
      currentDirectionTrue: 'environment.water.currentDirectionTrue',
      leeway: 'navigation.performance.leeway',
      driftAngle: 'navigation.performance.driftAngle'
    },
    
    // Filtering & validation
    validation: {
      minSOG: 0.5,              // Ignore if SOG < 0.5 m/s (too slow)
      maxCurrentSpeed: 3.0,     // Reject if current > 3 m/s (error check)
      minSTW: 0.1,              // Ignore if STW < 0.1 m/s
      gpsPrecision: 2.5         // GPS uncertainty (m/s), ignore small currents
    },
    
    // Smoothing
    smoothing: {
      enabled: true,
      windowSize: 10,           // Points for rolling average (10 sec at 1 Hz)
      method: 'exponential'     // 'simple' or 'exponential'
    },
    
    // Statistics
    statistics: {
      enabled: true,
      logInterval: 60000        // Log every 60 seconds
    }
  };

  // State variables
  let speedBuffer = [];
  let directionBuffer = [];
  let stats = {
    totalPoints: 0,
    validPoints: 0,
    filteredPoints: 0,
    minCurrentSpeed: Infinity,
    maxCurrentSpeed: 0,
    averageCurrentSpeed: 0,
    minLeeway: Infinity,
    maxLeeway: 0,
    averageLeeway: 0,
    lastUpdate: null
  };

  /**
   * Load configuration from Signal K settings
   */
  function loadConfiguration() {
    try {
      if (app.pluginConfig && typeof app.pluginConfig === 'object') {
        Object.assign(config, app.pluginConfig);
        if (debug) app.debug('[Current] Configuration loaded');
      }
    } catch (err) {
      app.error(`[Current] Configuration error: ${err.message}`);
    }
  }

  /**
   * Convert polar (magnitude, angle) to cartesian (x, y)
   * angle in radians (0 = east, π/2 = north)
   */
  function polarToCartesian(magnitude, angle) {
    return {
      x: magnitude * Math.cos(angle),
      y: magnitude * Math.sin(angle)
    };
  }

  /**
   * Convert cartesian (x, y) to polar (magnitude, angle)
   */
  function cartesianToPolar(x, y) {
    const magnitude = Math.sqrt(x * x + y * y);
    let angle = Math.atan2(y, x);
    
    // Normalize to 0-2π
    if (angle < 0) angle += 2 * Math.PI;
    
    return { magnitude, angle };
  }

  /**
   * Normalize angle to 0-2π range
   */
  function normalizeAngle(angle) {
    let normalized = angle;
    while (normalized < 0) normalized += 2 * Math.PI;
    while (normalized >= 2 * Math.PI) normalized -= 2 * Math.PI;
    return normalized;
  }

  /**
   * Calculate angle difference (smallest arc)
   */
  function angleDifference(angle1, angle2) {
    let diff = angle2 - angle1;
    while (diff > Math.PI) diff -= 2 * Math.PI;
    while (diff < -Math.PI) diff += 2 * Math.PI;
    return diff;
  }

  /**
   * Calculate current from GPS and loch data
   * 
   * Vector diagram:
   *   GPS_velocity = STW_velocity + Current_velocity
   *   Current = GPS - STW
   */
  function calculateCurrent(sog, cog, stw, heading) {
    // Validate inputs
    if (sog < config.validation.minSOG || stw < config.validation.minSTW) {
      return null; // Not enough speed for reliable calculation
    }

    // Step 1: Convert STW + heading to velocity vector (boat moving through water)
    // Boat velocity relative to water, in earth frame
    const stwVector = polarToCartesian(stw, heading);

    // Step 2: Convert SOG + COG to velocity vector (boat moving over ground)
    // Actual velocity relative to earth
    const sogVector = polarToCartesian(sog, cog);

    // Step 3: Calculate current vector (difference)
    // Current = SOG - STW
    const currentVector = {
      x: sogVector.x - stwVector.x,
      y: sogVector.y - stwVector.y
    };

    // Step 4: Convert back to polar form
    const current = cartesianToPolar(currentVector.x, currentVector.y);
    const currentSpeed = current.magnitude;
    const currentDirection = current.angle;

    // Step 5: Calculate leeway (lateral drift)
    // Angle between heading and COG
    const leeway = angleDifference(heading, cog);

    // Validation
    if (currentSpeed > config.validation.maxCurrentSpeed) {
      if (debug) {
        app.debug(`[Current] Ignoring unrealistic current: ${currentSpeed.toFixed(3)} m/s`);
      }
      return null;
    }

    // Return result even for small currents (useful for testing)
    return {
      speed: currentSpeed,
      direction: currentDirection,
      leeway: leeway,
      valid: true
    };
  }

  /**
   * Apply smoothing to current value
   */
  function smoothCurrent(currentSpeed, currentDirection) {
    // Add to buffers
    speedBuffer.push(currentSpeed);
    directionBuffer.push(currentDirection);

    // Keep buffer at max size
    if (speedBuffer.length > config.smoothing.windowSize) {
      speedBuffer.shift();
      directionBuffer.shift();
    }

    // Simple average for speed
    const smoothedSpeed = speedBuffer.reduce((a, b) => a + b, 0) / speedBuffer.length;

    // Mean direction (circular mean for angles)
    let sumX = 0, sumY = 0;
    directionBuffer.forEach(angle => {
      sumX += Math.cos(angle);
      sumY += Math.sin(angle);
    });
    const smoothedDirection = Math.atan2(
      sumY / directionBuffer.length,
      sumX / directionBuffer.length
    );

    return {
      speed: smoothedSpeed,
      direction: normalizeAngle(smoothedDirection)
    };
  }

  /**
   * Update statistics
   */
  function updateStatistics(currentSpeed, leeway) {
    stats.totalPoints++;
    stats.validPoints++;
    stats.minCurrentSpeed = Math.min(stats.minCurrentSpeed, currentSpeed);
    stats.maxCurrentSpeed = Math.max(stats.maxCurrentSpeed, currentSpeed);
    stats.minLeeway = Math.min(stats.minLeeway, leeway);
    stats.maxLeeway = Math.max(stats.maxLeeway, leeway);

    // Running averages (exponential moving average)
    const alpha = 0.1;
    stats.averageCurrentSpeed = stats.averageCurrentSpeed * (1 - alpha) + currentSpeed * alpha;
    stats.averageLeeway = stats.averageLeeway * (1 - alpha) + leeway * alpha;
    stats.lastUpdate = new Date().toISOString();
  }

  /**
   * Log statistics periodically
   */
  function logStatistics() {
    if (!config.statistics.enabled) return;

    app.debug(`[Current Stats]
      Total: ${stats.totalPoints} | Valid: ${stats.validPoints} | Filtered: ${stats.filteredPoints}
      Speed: ${stats.minCurrentSpeed.toFixed(3)} - ${stats.maxCurrentSpeed.toFixed(3)} m/s
             avg ${stats.averageCurrentSpeed.toFixed(3)} m/s
      Leeway: ${(stats.minLeeway * 180 / Math.PI).toFixed(1)}° - ${(stats.maxLeeway * 180 / Math.PI).toFixed(1)}°
              avg ${(stats.averageLeeway * 180 / Math.PI).toFixed(1)}°
      Last: ${stats.lastUpdate}
    `);
  }

  /**
   * Main processing loop
   */
  function processCurrent() {
    try {
      // Get required inputs
      const sogData = app.getSelfPath(config.inputs.sog);
      const cogData = app.getSelfPath(config.inputs.cog);
      const stwData = app.getSelfPath(config.inputs.stw);
      const headingData = app.getSelfPath(config.inputs.heading);

      // Check if all data available
      if (!sogData || !cogData || !stwData || !headingData ||
          sogData.value === undefined || cogData.value === undefined ||
          stwData.value === undefined || headingData.value === undefined) {
        return; // Not enough data yet
      }

      const sog = sogData.value;
      const cog = cogData.value;
      const stw = stwData.value;
      const heading = headingData.value;

      // Calculate current
      const current = calculateCurrent(sog, cog, stw, heading);
      if (!current) {
        stats.filteredPoints++;
        return; // Failed validation
      }

      // Apply smoothing if enabled
      let smoothed = current;
      if (config.smoothing.enabled) {
        smoothed = smoothCurrent(current.speed, current.direction);
      }

      // Update statistics
      updateStatistics(smoothed.speed, current.leeway);

      // Inject into Signal K
      app.handleMessage({
        updates: [{
          source: { label: 'current-calculator', type: 'NMEA0183' },
          timestamp: new Date().toISOString(),
          values: [
            { 
              path: config.outputs.currentSpeed, 
              value: smoothed.speed 
            },
            { 
              path: config.outputs.currentDirection, 
              value: smoothed.direction 
            },
            { 
              path: config.outputs.currentDirectionTrue, 
              value: smoothed.direction 
            },
            { 
              path: config.outputs.leeway, 
              value: current.leeway 
            },
            { 
              path: config.outputs.driftAngle, 
              value: current.leeway 
            }
          ]
        }]
      });

      if (debug) {
        const speedKn = smoothed.speed / 0.51444; // m/s to knots
        const dirDeg = smoothed.direction * 180 / Math.PI;
        const leewayDeg = current.leeway * 180 / Math.PI;
        app.debug(`[Current] Speed: ${speedKn.toFixed(2)} kn (${smoothed.speed.toFixed(3)} m/s) | Dir: ${dirDeg.toFixed(1)}° | Leeway: ${leewayDeg.toFixed(1)}°`);
      }

    } catch (err) {
      app.error(`[Current] Processing error: ${err.message}`);
    }
  }

  // Main timer
  let processingInterval = null;
  let statsInterval = null;

  return {
    start() {
      loadConfiguration();
      
      // Start processing loop
      processingInterval = setInterval(processCurrent, config.updateInterval);
      
      // Start statistics logging
      if (config.statistics.enabled) {
        statsInterval = setInterval(logStatistics, config.statistics.logInterval);
      }

      app.debug('[Current] Plugin started');
      app.debug(`[Current] Inputs: SOG=${config.inputs.sog}, STW=${config.inputs.stw}, Heading=${config.inputs.heading}`);
      app.debug(`[Current] Outputs: Speed=${config.outputs.currentSpeed}, Direction=${config.outputs.currentDirection}`);
      app.debug(`[Current] Min SOG threshold: ${config.validation.minSOG} m/s`);
    },

    stop() {
      if (processingInterval) clearInterval(processingInterval);
      if (statsInterval) clearInterval(statsInterval);
      app.debug('[Current] Plugin stopped');
    },

    /**
     * API: Get current statistics
     */
    getStatistics() {
      return {
        stats: stats,
        config: {
          method: 'vector subtraction',
          inputs: config.inputs,
          validation: config.validation
        }
      };
    },

    /**
     * API: Reset statistics
     */
    resetStatistics() {
      stats = {
        totalPoints: 0,
        validPoints: 0,
        filteredPoints: 0,
        minCurrentSpeed: Infinity,
        maxCurrentSpeed: 0,
        averageCurrentSpeed: 0,
        minLeeway: Infinity,
        maxLeeway: 0,
        averageLeeway: 0,
        lastUpdate: null
      };
      speedBuffer = [];
      directionBuffer = [];
      app.debug('[Current] Statistics reset');
    },

    /**
     * API: Get current calculation for specific inputs (testing)
     */
    calculateTestCurrent(sog, cog, stw, heading) {
      return calculateCurrent(sog, cog, stw, heading);
    }
  };
};
