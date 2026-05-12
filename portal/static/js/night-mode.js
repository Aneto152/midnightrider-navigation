/* MidnightRider — Night Mode Controller
 * Persists preference in localStorage
 * Works on iPad Safari, no framework required
 */

(function() {
  'use strict';

  var STORAGE_KEY = 'midnightrider-night-mode';
  var COCKPIT_KEY = 'midnightrider-cockpit-mode';

  function applyMode() {
    var nightOn = localStorage.getItem(STORAGE_KEY) === 'on';
    var cockpitOn = localStorage.getItem(COCKPIT_KEY) === 'on';

    if (nightOn) { document.body.classList.add('night-mode'); }
    else { document.body.classList.remove('night-mode'); }

    if (cockpitOn) { document.body.classList.add('cockpit-mode'); }
    else { document.body.classList.remove('cockpit-mode'); }

    updateToggleIcon();
  }

  function toggleNight() {
    var isOn = document.body.classList.toggle('night-mode');
    localStorage.setItem(STORAGE_KEY, isOn ? 'on' : 'off');
    updateToggleIcon();
  }

  function updateToggleIcon() {
    var btn = document.getElementById('night-toggle');
    if (!btn) return;
    var isNight = document.body.classList.contains('night-mode');
    btn.textContent = isNight ? '☀️' : '🌙';
    btn.title = isNight ? 'Switch to Day Mode' : 'Switch to Night Mode';
    btn.setAttribute('aria-label', btn.title);
  }

  function injectToggleButton() {
    if (document.getElementById('night-toggle')) return;
    var btn = document.createElement('button');
    btn.id = 'night-toggle';
    btn.setAttribute('aria-label', 'Toggle Night Mode');
    btn.addEventListener('click', toggleNight);
    // Touch-friendly: prevent double-tap zoom on iPad
    btn.addEventListener('touchend', function(e) {
      e.preventDefault();
      toggleNight();
    });
    document.body.appendChild(btn);
    updateToggleIcon();
  }

  // Apply immediately to avoid flash of wrong theme
  // (runs before DOM is fully ready to prevent white flash)
  if (localStorage.getItem(STORAGE_KEY) === 'on') {
    document.documentElement.style.backgroundColor = '#0d0d0d';
  }

  // Full initialization once DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      applyMode();
      injectToggleButton();
    });
  } else {
    applyMode();
    injectToggleButton();
  }

  // Keyboard shortcut: 'N' toggles night mode (useful when connected to keyboard)
  document.addEventListener('keydown', function(e) {
    if (e.key === 'n' || e.key === 'N') {
      if (!['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
        toggleNight();
      }
    }
  });

  // Expose globally for console debugging
  window.MidnightRider = window.MidnightRider || {};
  window.MidnightRider.toggleNight = toggleNight;
  window.MidnightRider.applyMode = applyMode;

})();
