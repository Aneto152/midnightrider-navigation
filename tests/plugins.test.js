'use strict';
/**
 * @file test-plugins.js
 * Unit tests for P1 (heading), P2 (leeway J/30), P4 (true wind).
 * Run: npm test
 */

const RAD = Math.PI / 180;
const KTS = 0.5144;
const near = (a, b, eps) => Math.abs(a - b) < (eps || 0.01);

const { _computeHeadingTrue } = require('../plugins/signalk-heading-true-calculator');
const { _computeLeeway } = require('../plugins/signalk-j30-leeway');
const { _computeTrueWind } = require('../plugins/signalk-truewind-calculator');

// ─── P1: True Heading ─────────────────────────────────────────
describe('P1 computeHeadingTrue', () => {
  test('Larchmont NY: HM=0deg, var=-12.8deg => HT=347.2deg', () => {
    const ht = _computeHeadingTrue(0, -12.8 * RAD);
    expect(near(ht * 180 / Math.PI, 347.2, 0.1)).toBe(true);
  });

  test('Wrap: HM=350deg + var=+20deg => HT=10deg', () => {
    const ht = _computeHeadingTrue(350 * RAD, 20 * RAD);
    expect(near(ht * 180 / Math.PI, 10.0, 0.1)).toBe(true);
  });

  test('Zero variation: HT = HM', () => {
    expect(near(_computeHeadingTrue(1.5, 0), 1.5)).toBe(true);
  });

  test('Result always in [0, 2pi] for all headings', () => {
    for (let d = 0; d < 360; d += 15) {
      const ht = _computeHeadingTrue(d * RAD, -15 * RAD);
      expect(ht).toBeGreaterThanOrEqual(0);
      expect(ht).toBeLessThan(2 * Math.PI);
    }
  });

  test('Rejects NaN', () => {
    expect(_computeHeadingTrue(NaN, 0)).toBeNull();
  });

  test('Rejects Infinity', () => {
    expect(_computeHeadingTrue(Infinity, 0)).toBeNull();
  });

  test('Rejects null', () => {
    expect(_computeHeadingTrue(null, 0)).toBeNull();
  });

  test('HM=0, var=0 => HT=0', () => {
    expect(near(_computeHeadingTrue(0, 0), 0)).toBe(true);
  });
});

// ─── P2: J/30 Leeway ─────────────────────────────────────────
describe('P2 computeLeeway J/30', () => {
  const cfg = { leewayFactor: 12, minSpeed: 0.5, maxLeeway: 15, minHeel: 1.0, leewaySign: -1 };

  test('K=12, heel=15deg, V=6kts => 5.0deg', () => {
    const lwy = _computeLeeway(15 * RAD, 6, cfg);
    expect(near(Math.abs(lwy) * 180 / Math.PI, 5.0, 0.1)).toBe(true);
  });

  test('K=12, heel=8deg, V=4kts => 6.0deg', () => {
    const lwy = _computeLeeway(8 * RAD, 4, cfg);
    expect(near(Math.abs(lwy) * 180 / Math.PI, 6.0, 0.1)).toBe(true);
  });

  test('heel < minHeel => 0', () => {
    expect(_computeLeeway(0.5 * RAD, 6, cfg)).toBe(0);
  });

  test('speed < minSpeed => 0', () => {
    expect(_computeLeeway(15 * RAD, 0.3, cfg)).toBe(0);
  });

  test('Capped at maxLeeway=15deg', () => {
    const lwy = _computeLeeway(45 * RAD, 3, cfg);
    expect(near(Math.abs(lwy) * 180 / Math.PI, 15.0, 0.1)).toBe(true);
  });

  test('Positive heel, leewaySign=-1 => negative result', () => {
    expect(_computeLeeway(10 * RAD, 5, cfg)).toBeLessThan(0);
  });

  test('Negative heel => positive result', () => {
    expect(_computeLeeway(-10 * RAD, 5, cfg)).toBeGreaterThan(0);
  });

  test('Symmetry: |lwy(+heel)| = |lwy(-heel)|', () => {
    const a = _computeLeeway(10 * RAD, 5, cfg);
    const b = _computeLeeway(-10 * RAD, 5, cfg);
    expect(near(Math.abs(a), Math.abs(b))).toBe(true);
  });

  test('Rejects null roll', () => {
    expect(_computeLeeway(null, 5, cfg)).toBeNull();
  });

  test('Custom K=14 (upper J/30 range)', () => {
    const c = { ...cfg, leewayFactor: 14 };
    const lwy = _computeLeeway(15 * RAD, 6, c);
    expect(near(Math.abs(lwy) * 180 / Math.PI, 14 * 15 / 36, 0.1)).toBe(true);
  });
});

// ─── P4: True Wind Vector Math ────────────────────────────────
describe('P4 computeTrueWind (vector math)', () => {
  test('Stationary: TWS=AWS, TWD=90deg (wind from E)', () => {
    const r = _computeTrueWind(90 * RAD, 10 * KTS, 0, 0, 0);
    expect(near(r.tws / KTS, 10.0, 0.1)).toBe(true);
    expect(near(r.twd * 180 / Math.PI, 90.0, 0.5)).toBe(true);
  });

  test('Dead upwind: TWS = AWS - SOG (15-6=9kts)', () => {
    const r = _computeTrueWind(0, 15 * KTS, 0, 6 * KTS, 0);
    expect(near(r.tws / KTS, 9.0, 0.1)).toBe(true);
    expect(near(r.twd * 180 / Math.PI, 0, 0.5)).toBe(true);
  });

  test('Dead downwind: TWS = AWS + SOG (4+6=10kts)', () => {
    const r = _computeTrueWind(Math.PI, 4 * KTS, 0, 6 * KTS, 0);
    expect(near(r.tws / KTS, 10.0, 0.1)).toBe(true);
    expect(near(r.twd * 180 / Math.PI, 180, 0.5)).toBe(true);
  });

  test('TWD always in [0, 2pi]', () => {
    for (let h = 0; h < 360; h += 45) {
      for (let a = -170; a <= 170; a += 85) {
        const r = _computeTrueWind(a * RAD, 10 * KTS, h * RAD, 5 * KTS, h * RAD);
        if (r) {
          expect(r.twd).toBeGreaterThanOrEqual(0);
          expect(r.twd).toBeLessThan(2 * Math.PI);
        }
      }
    }
  });

  test('TWA always in [-pi, +pi]', () => {
    for (let h = 0; h < 360; h += 45) {
      for (let a = -170; a <= 170; a += 85) {
        const r = _computeTrueWind(a * RAD, 10 * KTS, h * RAD, 5 * KTS, h * RAD);
        if (r) {
          expect(r.twa).toBeGreaterThanOrEqual(-Math.PI - 0.001);
          expect(r.twa).toBeLessThanOrEqual(Math.PI + 0.001);
        }
      }
    }
  });

  test('AWS out of range => null', () => {
    expect(_computeTrueWind(0, 70, 0, 5, 0)).toBeNull();
  });

  test('Null input => null', () => {
    expect(_computeTrueWind(null, 10, 0, 5, 0)).toBeNull();
  });

  test('NaN input => null', () => {
    expect(_computeTrueWind(NaN, 10, 0, 5, 0)).toBeNull();
  });

  test('Returns object with twd, tws, twa keys', () => {
    const r = _computeTrueWind(45 * RAD, 10 * KTS, 0, 5 * KTS, 0);
    expect(r).toHaveProperty('twd');
    expect(r).toHaveProperty('tws');
    expect(r).toHaveProperty('twa');
  });
});
