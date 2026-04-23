/**
 * Signal K Plugin - Wave Height Calculator v2.1 (3-Axis)
 * 
 * Reads 3-axis acceleration (X, Y, Z) from WIT IMU
 * Calculates wave height using acceleration magnitude (not just Z-axis)
 * This accounts for boat heel - uses |a| = sqrt(ax² + ay² + az²)
 * 
 * Corrects for boat orientation (heel/pitch changes which axis carries gravity)
 * Based on maritime engineering formulas (DNV-GL, ISO 12649)
 */

module.exports = function(app) {
  const plugin = {};
  
  plugin.id = 'signalk-wave-height-imu';
  plugin.name = 'Wave Height Calculator (3-Axis IMU)';
  plugin.description = 'Calculate wave height from 3-axis acceleration magnitude (corrects for boat heel)';
  plugin.version = '2.1.0';

  plugin.schema = {
    type: 'object',
    title: 'Wave Height Configuration',
    properties: {
      windowSize: {
        type: 'number',
        title: 'Analysis Window Size (seconds)',
        default: 12,
        minimum: 5,
        maximum: 60,
        description: 'Time window for wave analysis (12s = 120 samples @ 10Hz)'
      },
      minFrequency: {
        type: 'number',
        title: 'Minimum Wave Frequency (Hz)',
        default: 0.04,
        minimum: 0.01,
        maximum: 0.5,
        description: 'Lowest frequency for wave detection (0.04 Hz = 25s period)'
      },
      maxFrequency: {
        type: 'number',
        title: 'Maximum Wave Frequency (Hz)',
        default: 0.3,
        minimum: 0.1,
        maximum: 1.0,
        description: 'Highest frequency for wave detection (0.3 Hz = 3.3s period)'
      },
      gravityOffset: {
        type: 'number',
        title: 'Gravity Offset (m/s²)',
        default: 9.81,
        minimum: 9.5,
        maximum: 10.0,
        description: 'Gravitational acceleration (for wave formula)'
      },
      methodType: {
        type: 'string',
        title: 'Calculation Method',
        enum: ['rms', 'peakToPeak', 'spectral', 'combined'],
        default: 'combined',
        description: 'Wave height calculation method (combined = average of all 3)'
      },
      debug: {
        type: 'boolean',
        title: 'Enable Debug Logging',
        default: false,
        description: 'Log detailed calculations'
      }
    }
  };

  plugin.start = function(options) {
    options = options || {};
    
    const windowSize = options.windowSize || 12;        // seconds
    const minFreq = options.minFrequency || 0.04;       // Hz
    const maxFreq = options.maxFrequency || 0.3;        // Hz
    const gravity = options.gravityOffset || 9.81;      // m/s²
    const methodType = options.methodType || 'combined';
    const debugMode = options.debug || false;

    const bufferSize = windowSize * 10;  // 10 Hz sampling rate
    let accelMagnitudeBuffer = [];       // Rolling buffer of |a| = sqrt(ax² + ay² + az²)
    let sampleCount = 0;
    let lastAnalysis = Date.now();

    app.debug('[Wave Height] Starting - 3-Axis Magnitude Mode');
    app.debug(`[Wave Height] Window: ${windowSize}s, Method: ${methodType}`);
    app.setPluginStatus(`Initializing (waiting for acceleration data)...`);

    // Subscribe to all 3 acceleration axes
    app.streambundle.getSelfStream('navigation.acceleration.x').onValue(function(accelX) {
      // Also need Y and Z, but we'll capture them in next subscription
    });

    app.streambundle.getSelfStream('navigation.acceleration.y').onValue(function(accelY) {
      // Also need X and Z
    });

    // Main subscription - trigger on Z axis updates, read all 3 axes
    app.streambundle.getSelfStream('navigation.acceleration.z').onValue(function(accelZ) {
      try {
        // Get current values of all 3 axes
        const selfData = app.getSelfData();
        const accelData = selfData?.navigation?.acceleration;
        
        if (!accelData) return;

        const ax = accelData.x?.value || 0;
        const ay = accelData.y?.value || 0;
        const az = accelData.z?.value || 0;

        // Calculate acceleration magnitude (3-axis)
        // This corrects for boat heel/pitch - the total acceleration stays consistent
        // even as the boat tilts
        const magnitude = Math.sqrt(ax * ax + ay * ay + az * az);

        // Remove gravity offset (when boat is level, |a| ≈ 9.81 m/s²)
        // Wave motion adds oscillation on top of gravity
        const waveAccel = magnitude - gravity;

        if (debugMode) {
          app.debug(`[Wave] ax=${ax.toFixed(2)} ay=${ay.toFixed(2)} az=${az.toFixed(2)} |a|=${magnitude.toFixed(2)} wave=${waveAccel.toFixed(3)}`);
        }

        accelMagnitudeBuffer.push(waveAccel);
        sampleCount++;

        // Keep only last N samples (rolling window)
        if (accelMagnitudeBuffer.length > bufferSize) {
          accelMagnitudeBuffer.shift();
        }

        // Update status
        if (sampleCount % 50 === 0) {
          app.setPluginStatus(`Analyzing (${accelMagnitudeBuffer.length}/${bufferSize} samples)`);
        }

        // Analyze every second
        const now = Date.now();
        if (now - lastAnalysis >= 1000 && accelMagnitudeBuffer.length >= bufferSize * 0.5) {
          const waveData = calculateWaveHeight();
          if (waveData) {
            injectWaveData(waveData);
          }
          lastAnalysis = now;
        }
      } catch (e) {
        app.debug(`[Wave Height] Error: ${e.message}`);
      }
    });

    /**
     * Calculate wave height using selected method
     */
    function calculateWaveHeight() {
      if (accelMagnitudeBuffer.length < bufferSize * 0.5) {
        return null;
      }

      const results = {};

      // Method 1: RMS-based calculation
      if (methodType === 'rms' || methodType === 'combined') {
        results.rms = calculateRmsWaveHeight();
      }

      // Method 2: Peak-to-Peak calculation
      if (methodType === 'peakToPeak' || methodType === 'combined') {
        results.peakToPeak = calculatePeakToPeakWaveHeight();
      }

      // Method 3: Spectral analysis (simplified)
      if (methodType === 'spectral' || methodType === 'combined') {
        results.spectral = calculateSpectralWaveHeight();
      }

      // Combine results
      const finalResult = combineResults(results, methodType);
      return finalResult;
    }

    /**
     * RMS-based wave height estimation
     * Formula: Hs ≈ 4 * sqrt(variance(accel)) / g
     * Based on Rayleigh distribution of wave heights
     */
    function calculateRmsWaveHeight() {
      if (accelMagnitudeBuffer.length === 0) return null;

      const mean = accelMagnitudeBuffer.reduce((a, b) => a + b, 0) / accelMagnitudeBuffer.length;
      const variance = accelMagnitudeBuffer.reduce((sum, x) => sum + (x - mean) ** 2, 0) / accelMagnitudeBuffer.length;
      const rmsAccel = Math.sqrt(variance);

      // Significant wave height (1/3 of largest waves)
      const significantHeight = (4 * rmsAccel) / gravity;
      
      // Mean wave height
      const meanHeight = significantHeight / 1.6;

      // Wave period (characteristic from RMS acceleration and gravity)
      const period = Math.sqrt((rmsAccel / gravity) * 50);

      return {
        method: 'rms',
        waveHeight: significantHeight,
        meanWaveHeight: meanHeight,
        period: period,
        rmsAccel: rmsAccel
      };
    }

    /**
     * Peak-to-Peak wave height estimation
     * Simpler but less accurate than RMS
     */
    function calculatePeakToPeakWaveHeight() {
      if (accelMagnitudeBuffer.length === 0) return null;

      const max = Math.max(...accelMagnitudeBuffer);
      const min = Math.min(...accelMagnitudeBuffer);
      const peakToPeak = max - min;

      // Approximate significant height from peak-to-peak
      const significantHeight = peakToPeak * 0.25;
      const meanHeight = significantHeight / 1.6;
      const period = Math.sqrt((peakToPeak / gravity) * 50);

      return {
        method: 'peakToPeak',
        waveHeight: significantHeight,
        meanWaveHeight: meanHeight,
        period: period,
        rmsAccel: peakToPeak / 4
      };
    }

    /**
     * Spectral analysis (simplified zero-crossing method)
     */
    function calculateSpectralWaveHeight() {
      if (accelMagnitudeBuffer.length < 10) return null;

      // Count zero crossings
      let zeroCrossings = 0;
      for (let i = 1; i < accelMagnitudeBuffer.length; i++) {
        if (accelMagnitudeBuffer[i-1] < 0 && accelMagnitudeBuffer[i] >= 0) {
          zeroCrossings++;
        }
      }

      // Estimate dominant frequency from zero-crossing rate
      const dt = 0.1;  // 10 Hz = 0.1s per sample
      const zeroCrossingFreq = (zeroCrossings / accelMagnitudeBuffer.length) * (1 / dt);
      const dominantFreq = Math.max(minFreq, Math.min(maxFreq, zeroCrossingFreq));

      // Wave period from frequency
      const period = 1 / dominantFreq;

      // RMS for this method
      const mean = accelMagnitudeBuffer.reduce((a, b) => a + b, 0) / accelMagnitudeBuffer.length;
      const variance = accelMagnitudeBuffer.reduce((sum, x) => sum + (x - mean) ** 2, 0) / accelMagnitudeBuffer.length;
      const rmsAccel = Math.sqrt(variance);

      const significantHeight = (4 * rmsAccel) / gravity;
      const meanHeight = significantHeight / 1.6;

      return {
        method: 'spectral',
        waveHeight: significantHeight,
        meanWaveHeight: meanHeight,
        period: period,
        dominantFrequency: dominantFreq,
        rmsAccel: rmsAccel
      };
    }

    /**
     * Combine multiple methods into single result
     */
    function combineResults(results, method) {
      if (method === 'combined') {
        const heights = Object.values(results)
          .map(r => r.waveHeight)
          .filter(h => h !== null && !isNaN(h) && h >= 0);

        if (heights.length === 0) return null;

        const avgHeight = heights.reduce((a, b) => a + b, 0) / heights.length;

        // Use RMS method's period and frequency if available
        const rmsData = results.rms || results.peakToPeak || results.spectral;

        return {
          method: 'combined (avg of RMS, P2P, spectral)',
          waveHeight: Math.max(0, avgHeight),
          meanWaveHeight: Math.max(0, avgHeight / 1.6),
          period: rmsData?.period || 0,
          dominantFrequency: results.spectral?.dominantFrequency || 0,
          rmsAccel: rmsData?.rmsAccel || 0
        };
      } else {
        return results[method] || null;
      }
    }

    /**
     * Inject wave height data into Signal K
     */
    function injectWaveData(waveData) {
      if (!waveData) return;

      const values = [
        {
          path: 'environment.wave.height',
          value: Math.max(0, waveData.waveHeight)
        },
        {
          path: 'environment.wave.meanWaveHeight',
          value: Math.max(0, waveData.meanWaveHeight)
        },
        {
          path: 'environment.wave.timeBetweenCrests',
          value: Math.max(0, waveData.period)
        },
        {
          path: 'environment.wave.dominantFrequency',
          value: Math.max(0, waveData.dominantFrequency)
        },
        {
          path: 'environment.wave.rmsAcceleration',
          value: Math.max(0, waveData.rmsAccel)
        }
      ];

      app.handleMessage(plugin.id, {
        context: 'vessels.' + app.selfId,
        updates: [{
          source: { label: plugin.id },
          timestamp: new Date().toISOString(),
          values: values
        }]
      });

      if (debugMode) {
        app.debug(`[Wave Height] Hs=${waveData.waveHeight.toFixed(2)}m Period=${waveData.period.toFixed(1)}s Freq=${waveData.dominantFrequency.toFixed(3)}Hz`);
      }
    }
  };

  plugin.stop = function() {
    app.debug('[Wave Height] Stopped');
    app.setPluginStatus('Stopped');
  };

  return plugin;
};
