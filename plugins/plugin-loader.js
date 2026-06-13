/**
 * plugin-loader.js — Manual plugin initialization for SK 2.25.0
 * Required because SK doesn't auto-discover plugins in ~/.signalk/plugins
 * This file is required by SK at startup via settings.json configuration.
 */

module.exports = function(app) {
  console.log('[PluginLoader] Initializing custom plugins...');
  
  try {
    // Load Plugin 1: heading-true-calculator
    const headingTrueCalc = require('../plugins/signalk-heading-true-calculator/index.js');
    const p1Instance = headingTrueCalc(app);
    if (p1Instance && p1Instance.start) {
      p1Instance.start();
      console.log('[PluginLoader] ✅ signalk-heading-true-calculator loaded and started');
    }
  } catch (e) {
    console.error('[PluginLoader] ✗ Failed to load heading-true-calculator:', e.message);
  }
  
  try {
    // Load Plugin 2: j30-leeway
    const j30Leeway = require('../plugins/signalk-j30-leeway/index.js');
    const p2Instance = j30Leeway(app);
    if (p2Instance && p2Instance.start) {
      p2Instance.start();
      console.log('[PluginLoader] ✅ signalk-j30-leeway loaded and started');
    }
  } catch (e) {
    console.error('[PluginLoader] ✗ Failed to load j30-leeway:', e.message);
  }
  
  return {
    start: function() {
      console.log('[PluginLoader] Plugin loader started');
    },
    stop: function() {
      console.log('[PluginLoader] Plugin loader stopped');
    }
  };
};
