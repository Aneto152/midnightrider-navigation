/**
 * Signal K Loch Calibration Plugin
 * 
 * Objective:
 *   - Receive raw speed from loch (navigation.speedThroughWaterRaw)
 *   - Apply calibration (offset + factor or polynomial)
 *   - Output calibrated speed (navigation.speedThroughWater)
 *   - Optionally reinject to NMEA2000 bus
 * 
 * Calibration Methods:
 *   1. Linear: speedCalibrated = (speedRaw - offset) * factor
 *   2. Polynomial: speedCalibrated = a0 + a1*x + a2*x² + a3*x³
 *   3. None: passthrough (for testing)
 * 
 * Author: MidnightRider AI Coach
 * Date: 2026-04-21
 */

module.exports = function(app) {
  const debug = true;
  const UPDATE_INTERVAL = 1000; // 1 Hz (same as input)

  // Configuration (from plugin-config-data)
  let config = {
    enabled: true,
    debug: true,
    inputPath: 'navigation.speedThroughWaterRaw',
    outputPath: 'navigation.speedThroughWater',
    calibrationMethod: 'linear', // 'linear', 'polynomial', 'none'
    
    // Linear calibration
    linearCalibration: {
      offset: 0.0,    // Subtract this from raw (m/s)
      factor: 1.0     // Multiply by this
    },
    
    // Polynomial calibration (if method='polynomial')
    // speedCalibrated = c[0] + c[1]*x + c[2]*x² + c[3]*x³
    polynomialCalibration: {
      coefficients: [0.0, 1.0, 0.0, 0.0],
      order: 1  // Degree of polynomial (1=linear, 2=quadratic, etc)
    },
    
    // NMEA2000 output
    nmea2000: {
      enabled: false,  // Set to true when NMEA2000 output available
      deviceInstance: 0,
      sendRate: 1000   // ms
    },
    
    // Data smoothing & filtering
    smoothing: {
      enabled: true,
      windowSize: 5,   // Number of points for rolling average
      minSpeed: 0.0,   // Discard readings below this (m/s)
      maxSpeed: 10.0   // Discard readings above this (m/s)
    },
    
    // Statistics & validation
    statistics: {
      enabled: true,
      logInterval: 60000  // Log stats every 60 seconds
    }
  };

  // State variables
  let speedBuffer = [];
  let calibrationStats = {
    totalPoints: 0,
    filteredPoints: 0,
    minSpeedRaw: Infinity,
    maxSpeedRaw: -Infinity,
    minSpeedCalibrated: Infinity,
    maxSpeedCalibrated: -Infinity,
    averageRaw: 0,
    averageCalibrated: 0,
    lastUpdate: null,
    offsetFromGPS: 0  // Speed difference vs GPS (for validation)
  };

  /**
   * Load configuration from Signal K settings
   */
  function loadConfiguration() {
    try {
      if (app.pluginConfig && typeof app.pluginConfig === 'object') {
        Object.assign(config, app.pluginConfig);
        if (debug) app.debug('[Loch] Configuration loaded');
      }
    } catch (err) {
      app.error(`[Loch] Configuration error: ${err.message}`);
    }
  }

  /**
   * Apply linear calibration
   * formula: speedCalibrated = (speedRaw - offset) * factor
   */
  function applyLinearCalibration(speedRaw) {
    const { offset, factor } = config.linearCalibration;
    const speedCalibrated = (speedRaw - offset) * factor;
    return Math.max(0, speedCalibrated); // Never negative
  }

  /**
   * Apply polynomial calibration
   * formula: speedCalibrated = c[0] + c[1]*x + c[2]*x² + c[3]*x³ + ...
   */
  function applyPolynomialCalibration(speedRaw) {
    const { coefficients, order } = config.polynomialCalibration;
    let speedCalibrated = 0;
    
    for (let i = 0; i <= Math.min(order, coefficients.length - 1); i++) {
      speedCalibrated += coefficients[i] * Math.pow(speedRaw, i);
    }
    
    return Math.max(0, speedCalibrated); // Never negative
  }

  /**
   * Apply configured calibration method
   */
  function calibrateSpeed(speedRaw) {
    if (!config.enabled || config.calibrationMethod === 'none') {
      return speedRaw; // Passthrough
    }

    switch (config.calibrationMethod) {
      case 'linear':
        return applyLinearCalibration(speedRaw);
      case 'polynomial':
        return applyPolynomialCalibration(speedRaw);
      default:
        return speedRaw;
    }
  }

  /**
   * Smooth speed using rolling average
   */
  function smoothSpeed(speedRaw) {
    if (!config.smoothing.enabled) {
      return speedRaw;
    }

    speedBuffer.push(speedRaw);
    if (speedBuffer.length > config.smoothing.windowSize) {
      speedBuffer.shift();
    }

    const average = speedBuffer.reduce((a, b) => a + b, 0) / speedBuffer.length;
    return average;
  }

  /**
   * Validate speed reading
   */
  function isValidSpeed(speed) {
    if (!config.smoothing.enabled) return true;
    
    return speed >= config.smoothing.minSpeed && 
           speed <= config.smoothing.maxSpeed;
  }

  /**
   * Update statistics
   */
  function updateStatistics(speedRaw, speedCalibrated) {
    if (!config.statistics.enabled) return;

    calibrationStats.totalPoints++;
    calibrationStats.minSpeedRaw = Math.min(calibrationStats.minSpeedRaw, speedRaw);
    calibrationStats.maxSpeedRaw = Math.max(calibrationStats.maxSpeedRaw, speedRaw);
    calibrationStats.minSpeedCalibrated = Math.min(calibrationStats.minSpeedCalibrated, speedCalibrated);
    calibrationStats.maxSpeedCalibrated = Math.max(calibrationStats.maxSpeedCalibrated, speedCalibrated);

    // Update running averages
    const alpha = 0.1; // Exponential moving average factor
    calibrationStats.averageRaw = calibrationStats.averageRaw * (1 - alpha) + speedRaw * alpha;
    calibrationStats.averageCalibrated = calibrationStats.averageCalibrated * (1 - alpha) + speedCalibrated * alpha;
    calibrationStats.lastUpdate = new Date().toISOString();
  }

  /**
   * Log statistics periodically
   */
  function logStatistics() {
    if (!config.statistics.enabled) return;

    const offset = config.linearCalibration.offset;
    const factor = config.linearCalibration.factor;
    
    app.debug(`[Loch Stats] 
      Total: ${calibrationStats.totalPoints} points
      Raw: ${calibrationStats.minSpeedRaw.toFixed(2)} - ${calibrationStats.maxSpeedRaw.toFixed(2)} m/s
           avg ${calibrationStats.averageRaw.toFixed(2)} m/s
      Calibrated: ${calibrationStats.minSpeedCalibrated.toFixed(2)} - ${calibrationStats.maxSpeedCalibrated.toFixed(2)} m/s
                  avg ${calibrationStats.averageCalibrated.toFixed(2)} m/s
      Method: ${config.calibrationMethod} (offset: ${offset}, factor: ${factor})
      Last update: ${calibrationStats.lastUpdate}
    `);
  }

  /**
   * Main processing loop
   */
  function processLochData() {
    try {
      // Get raw speed from loch
      const speedRawData = app.getSelfPath(config.inputPath);
      if (!speedRawData || speedRawData.value === undefined) {
        return; // No data yet
      }

      const speedRaw = speedRawData.value;

      // Validate
      if (!isValidSpeed(speedRaw)) {
        if (debug) {
          app.debug(`[Loch] Speed ${speedRaw.toFixed(2)} m/s out of range [${config.smoothing.minSpeed}-${config.smoothing.maxSpeed}]`);
        }
        return;
      }

      // Smooth (optional)
      const speedSmoothed = smoothSpeed(speedRaw);

      // Calibrate
      const speedCalibrated = calibrateSpeed(speedSmoothed);

      // Update statistics
      updateStatistics(speedRaw, speedCalibrated);

      // Compare with GPS (optional validation)
      const gpsSpeed = app.getSelfPath('navigation.speedOverGround');
      if (gpsSpeed && gpsSpeed.value !== undefined) {
        calibrationStats.offsetFromGPS = speedCalibrated - gpsSpeed.value;
      }

      // Inject into Signal K
      app.handleMessage({
        updates: [{
          source: { label: 'loch-calibration', type: 'NMEA0183' },
          timestamp: new Date().toISOString(),
          values: [
            { 
              path: config.outputPath, 
              value: speedCalibrated 
            },
            { 
              path: 'navigation.speedThroughWaterSmoothed',
              value: speedSmoothed
            },
            {
              path: 'navigation.loch.calibrationOffset',
              value: calibrationStats.offsetFromGPS
            }
          ]
        }]
      });

      if (debug) {
        app.debug(`[Loch] Raw: ${speedRaw.toFixed(3)} → Smoothed: ${speedSmoothed.toFixed(3)} → Calibrated: ${speedCalibrated.toFixed(3)} m/s`);
      }

    } catch (err) {
      app.error(`[Loch] Processing error: ${err.message}`);
    }
  }

  /**
   * NMEA2000 output (stub for future implementation)
   */
  function sendNMEA2000(speedCalibrated) {
    if (!config.nmea2000.enabled) return;

    // TODO: Implement NMEA2000 PGN output
    // This requires:
    // 1. NMEA2000 bus access
    // 2. PGN 128267 (Water Speed) encoding
    // 3. Device instance and source addressing
    
    app.debug(`[Loch] NMEA2000 output not yet implemented (speed: ${speedCalibrated.toFixed(2)} m/s)`);
  }

  // Main timers
  let processingInterval = null;
  let statsInterval = null;

  return {
    start() {
      loadConfiguration();
      
      // Start main processing loop
      processingInterval = setInterval(processLochData, UPDATE_INTERVAL);
      
      // Start statistics logging
      if (config.statistics.enabled) {
        statsInterval = setInterval(logStatistics, config.statistics.logInterval);
      }

      app.debug('[Loch] Plugin started');
      app.debug(`[Loch] Input: ${config.inputPath}`);
      app.debug(`[Loch] Output: ${config.outputPath}`);
      app.debug(`[Loch] Method: ${config.calibrationMethod}`);
      if (config.calibrationMethod === 'linear') {
        app.debug(`[Loch] Linear: offset=${config.linearCalibration.offset}, factor=${config.linearCalibration.factor}`);
      }
    },

    stop() {
      if (processingInterval) clearInterval(processingInterval);
      if (statsInterval) clearInterval(statsInterval);
      app.debug('[Loch] Plugin stopped');
    },

    /**
     * API: Get current calibration
     */
    getCalibration() {
      return {
        method: config.calibrationMethod,
        linear: config.linearCalibration,
        polynomial: config.polynomialCalibration,
        statistics: calibrationStats
      };
    },

    /**
     * API: Update linear calibration dynamically
     * Usage: app.emit('loch-update-linear', { offset: 0.2, factor: 0.98 })
     */
    updateLinearCalibration(offset, factor) {
      config.linearCalibration.offset = offset;
      config.linearCalibration.factor = factor;
      app.debug(`[Loch] Linear calibration updated: offset=${offset}, factor=${factor}`);
    },

    /**
     * API: Update polynomial calibration dynamically
     */
    updatePolynomialCalibration(coefficients) {
      config.polynomialCalibration.coefficients = coefficients;
      app.debug(`[Loch] Polynomial calibration updated: ${coefficients.join(', ')}`);
    },

    /**
     * API: Reset statistics
     */
    resetStatistics() {
      calibrationStats = {
        totalPoints: 0,
        filteredPoints: 0,
        minSpeedRaw: Infinity,
        maxSpeedRaw: -Infinity,
        minSpeedCalibrated: Infinity,
        maxSpeedCalibrated: -Infinity,
        averageRaw: 0,
        averageCalibrated: 0,
        lastUpdate: null,
        offsetFromGPS: 0
      };
      app.debug('[Loch] Statistics reset');
    }
  };
};
