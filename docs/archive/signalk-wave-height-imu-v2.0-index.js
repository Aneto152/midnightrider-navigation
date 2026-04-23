/**
 * Signal K Plugin - Wave Height Calculator v2.0
 * 
 * Reads vertical acceleration (Z-axis) from WIT IMU
 * Calculates significant wave height and spectral parameters
 * Based on maritime engineering formulas (DNV-GL, ISO 12649)
 */

module.exports = function(app) {
  const plugin = {};
  
  plugin.id = 'signalk-wave-height-imu';
  plugin.name = 'Wave Height Calculator (IMU)';
  plugin.description = 'Calculate wave height from vertical acceleration (Z-axis) of 9-axis IMU';
  plugin.version = '2.0.0';

  plugin.schema = {
    type: 'object',
    title: 'Wave Height Configuration',
    properties: {
      windowSize: {
        type: 'number',
        title: 'Analysis Window Size (seconds)',
        default: 10,
        minimum: 5,
        maximum: 60,
        description: 'Time window for wave analysis (10-20s typical)'
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
        description: 'Subtract gravity from Z-axis for wave motion only'
      },
      methodType: {
        type: 'string',
        title: 'Calculation Method',
        enum: ['rms', 'peakToPeak', 'spectral', 'combined'],
        default: 'combined',
        description: 'rms=RMS acceleration, peakToPeak=Peak-to-peak, spectral=FFT-based, combined=average of methods'
      },
      debug: {
        type: 'boolean',
        title: 'Debug Logging',
        default: false,
        description: 'Enable detailed debug output'
      }
    }
  };

  plugin.start = function(options) {
    options = options || {};
    
    const windowSize = options.windowSize || 10;  // seconds
    const minFreq = options.minFrequency || 0.04;
    const maxFreq = options.maxFrequency || 0.3;
    const gravityOffset = options.gravityOffset || 9.81;
    const methodType = options.methodType || 'combined';
    const debug = options.debug || false;

    // Frequency of IMU updates (10 Hz default)
    const imuFrequency = 10;
    const bufferSize = windowSize * imuFrequency;  // e.g., 100 samples for 10s window @ 10Hz

    let accelZBuffer = [];
    let sampleCount = 0;
    let lastAnalysis = Date.now();

    app.debug(`[Wave Height] Started with window=${windowSize}s, method=${methodType}`);
    app.setPluginStatus(`Monitoring acceleration for wave height`);

    /**
     * Subscribe to acceleration.z from WIT IMU
     */
    app.streambundle.getSelfStream('navigation.acceleration.z').onValue(accelZ => {
      if (accelZ === null || accelZ === undefined) {
        return;
      }

      // Remove gravity component (Z-axis typically includes ~9.81 m/s² downward)
      const waveAccel = accelZ - gravityOffset;

      accelZBuffer.push(waveAccel);
      sampleCount++;

      // Keep only last N samples (rolling window)
      if (accelZBuffer.length > bufferSize) {
        accelZBuffer.shift();
      }

      // Analyze every second
      const now = Date.now();
      if (now - lastAnalysis >= 1000 && accelZBuffer.length >= bufferSize * 0.5) {
        const waveData = calculateWaveHeight();
        if (waveData) {
          injectWaveData(waveData);
        }
        lastAnalysis = now;
      }
    });

    /**
     * Calculate wave height using selected method
     */
    function calculateWaveHeight() {
      if (accelZBuffer.length < bufferSize * 0.5) {
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
      if (accelZBuffer.length === 0) return null;

      const mean = accelZBuffer.reduce((a, b) => a + b, 0) / accelZBuffer.length;
      const variance = accelZBuffer.reduce((sum, x) => sum + (x - mean) ** 2, 0) / accelZBuffer.length;
      const rmsAccel = Math.sqrt(variance);

      // Significant wave height (1/3 of largest waves)
      const significantHeight = (4 * rmsAccel) / 9.81;
      
      // Mean wave height
      const meanHeight = significantHeight / 1.6;

      // Wave period (characteristic from RMS acceleration and gravity)
      const period = Math.sqrt((rmsAccel / 9.81) * 50);  // Approximation

      return {
        method: 'rms',
        waveHeight: significantHeight,
        meanWaveHeight: meanHeight,
        period: period,
        rmsAccel: rmsAccel
      };
    }

    /**
     * Peak-to-Peak based calculation
     * Simple but less accurate method
     */
    function calculatePeakToPeakWaveHeight() {
      if (accelZBuffer.length === 0) return null;

      const maxAccel = Math.max(...accelZBuffer);
      const minAccel = Math.min(...accelZBuffer);
      const peakToPeak = maxAccel - minAccel;

      // Typical factor for vertical acceleration to wave height
      const waveHeight = peakToPeak * 0.25;  // ~0.25m per 1m/s² acceleration

      return {
        method: 'peakToPeak',
        waveHeight: waveHeight,
        peakToPeak: peakToPeak
      };
    }

    /**
     * Spectral analysis (simplified - no FFT)
     * Estimates dominant frequency from zero-crossing rate
     */
    function calculateSpectralWaveHeight() {
      if (accelZBuffer.length < 10) return null;

      // Count zero crossings
      let zeroCrossings = 0;
      for (let i = 1; i < accelZBuffer.length; i++) {
        if ((accelZBuffer[i - 1] >= 0 && accelZBuffer[i] < 0) ||
            (accelZBuffer[i - 1] < 0 && accelZBuffer[i] >= 0)) {
          zeroCrossings++;
        }
      }

      // Dominant frequency from zero-crossing rate
      const timeSpan = accelZBuffer.length / imuFrequency;
      const dominantFreq = zeroCrossings / (2 * timeSpan);

      // Clamp to expected wave frequency range
      const freq = Math.max(minFreq, Math.min(maxFreq, dominantFreq));

      // Period from frequency
      const period = 1 / freq;

      // Wave height from RMS and period (Jonswap spectrum approximation)
      const rmsAccel = Math.sqrt(
        accelZBuffer.reduce((sum, x) => sum + x * x, 0) / accelZBuffer.length
      );
      const waveHeight = (rmsAccel / 9.81) * period * period * 2.5;

      return {
        method: 'spectral',
        waveHeight: waveHeight,
        dominantFreq: freq,
        period: period,
        zeroCrossings: zeroCrossings
      };
    }

    /**
     * Combine multiple methods
     */
    function combineResults(results, method) {
      if (method === 'combined' && Object.keys(results).length > 1) {
        const heights = Object.values(results).map(r => r.waveHeight || 0);
        const avgHeight = heights.reduce((a, b) => a + b, 0) / heights.length;
        
        return {
          method: 'combined',
          waveHeight: avgHeight,
          methods: results,
          sampleCount: accelZBuffer.length
        };
      } else {
        return {
          ...results[Object.keys(results)[0]],
          sampleCount: accelZBuffer.length
        };
      }
    }

    /**
     * Inject wave data into Signal K
     */
    function injectWaveData(waveData) {
      const now = new Date().toISOString();

      const values = [
        { path: 'environment.wave.height', value: Math.max(0, waveData.waveHeight) }
      ];

      // Add optional fields if available
      if (waveData.meanWaveHeight !== undefined) {
        values.push({ path: 'environment.wave.meanWaveHeight', value: Math.max(0, waveData.meanWaveHeight) });
      }
      if (waveData.period !== undefined) {
        values.push({ path: 'environment.wave.timeBetweenCrests', value: Math.max(0, waveData.period) });
      }
      if (waveData.dominantFreq !== undefined) {
        values.push({ path: 'environment.wave.dominantFrequency', value: waveData.dominantFreq });
      }
      if (waveData.rmsAccel !== undefined) {
        values.push({ path: 'environment.wave.rmsAcceleration', value: waveData.rmsAccel });
      }

      const delta = {
        context: 'vessels.' + app.selfId,
        updates: [{
          source: { label: 'signalk-wave-height-imu' },
          timestamp: now,
          values: values
        }]
      };

      try {
        app.handleMessage(plugin.id, delta);

        if (debug && sampleCount % 100 === 0) {
          app.debug(
            `[Wave Height] H=${waveData.waveHeight.toFixed(2)}m | ` +
            (waveData.period ? `T=${waveData.period.toFixed(1)}s | ` : '') +
            `samples=${accelZBuffer.length}`
          );
        }
      } catch (e) {
        app.debug(`[Wave Height] Injection error: ${e.message}`);
      }
    }

    /**
     * Stop plugin
     */
    plugin.stop = function() {
      app.debug('[Wave Height] Stopped');
      app.setPluginStatus('Stopped');
    };

    return plugin;
  };

  return plugin;
};
