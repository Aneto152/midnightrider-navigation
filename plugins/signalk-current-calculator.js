'use strict';

/**
 * @file signalk-current-calculator.js
 * @version 1.0.0
 * @author MidnightRider J/30 — OpenClaw
 * @license MIT
 * @since 2026-06-13
 *
 * PURPOSE
 * Computes water current set and drift from vector difference:
 * ground track (COG/SOG) minus water track (CTW/STW).
 *
 * FORMULA
 * CTW = headingTrue + leewayAngle
 * currentNorth = SOG×cos(COG) − STW×cos(CTW)
 * currentEast = SOG×sin(COG) − STW×sin(CTW)
 * currentDrift = √(N² + E²)
 * currentSet = atan2(E, N) normalised [0, 2π)
 * EMA smoothing on N/E components (configurable alpha, default 0.7)
 *
 * NOTE — SK 2.25.0 STRUCTURE REQUIREMENT
 * plugin.stop is defined OUTSIDE plugin.start (see PLUGIN-DEVELOPMENT-GUIDE.md).
 * unsubscribes[] and all state are at module scope.
 */

const fs = require('fs');

const PLUGIN_ID = 'signalk-current-calculator';
const LOG_BASE = '/home/aneto/midnightrider-navigation/logs';
const LOG_SVC = LOG_BASE + '/services/current-calc.log';
const LOG_FLOW = LOG_BASE + '/debug/data-flow.log';
const MAX_BYTES = 5 * 1024 * 1024;
const MS_TO_KTS = 1 / 0.5144;
const RAD_TO_DEG = 180 / Math.PI;
const TWO_PI = 2 * Math.PI;

module.exports = function(app) {

  function ensureDirs() {
    try {
      fs.mkdirSync(LOG_BASE + '/services', { recursive: true });
      fs.mkdirSync(LOG_BASE + '/debug', { recursive: true });
    } catch (_) {}
  }
  function rotateIfNeeded(f) {
    try { if (fs.existsSync(f) && fs.statSync(f).size > MAX_BYTES) fs.renameSync(f, f+'.1'); }
    catch (_) {}
  }
  function svcLog(level, msg) {
    try {
      ensureDirs(); rotateIfNeeded(LOG_SVC);
      fs.appendFileSync(LOG_SVC,
        '['+new Date().toISOString()+'] ['+level+'] [current-calc] '+msg+'\n');
    } catch (_) {}
  }
  function flowLog(msg) {
    try {
      rotateIfNeeded(LOG_FLOW);
      fs.appendFileSync(LOG_FLOW, '['+new Date().toISOString()+'] [FLOW] '+msg+'\n');
    } catch (_) {}
  }

  // ── Module-scope state (guide section 1: MUST be here) ───────────────────
  let unsubscribes = [];
  let heartbeatTimer = null;
  let stats = { derived: 0, skipped: 0, errors: 0 };
  let ht=null, stw=null, cog=null, sog=null;
  let htTs=0, stwTs=0, cogTs=0, sogTs=0;
  let lwy=0, lwyTs=0;
  let smoothN=null, smoothE=null;

  const plugin = {
    id: PLUGIN_ID,
    name: 'Water Current Calculator (Set & Drift)',
    description: 'Computes environment.current.setTrue and .drift from ' +
      'CTW/STW vs COG/SOG vector difference. leewayAngle optional.',
    version: '1.0.0',
    schema: {
      type: 'object', title: 'Water Current Calculator',
      properties: {
        minSOG: { type:'number', title:'Min SOG m/s', default:0.3, minimum:0, maximum:2.0 },
        minSTW: { type:'number', title:'Min STW m/s', default:0.3, minimum:0, maximum:2.0 },
        maxDataAgeSecs: { type:'number', title:'Max input age s', default:10, minimum:2, maximum:60 },
        smoothingAlpha: { type:'number', title:'EMA alpha 0–0.95', default:0.7, minimum:0, maximum:0.95 },
        maxCurrentKts: { type:'number', title:'Max current cap kts', default:5, minimum:1, maximum:10 },
        debug: { type:'boolean', title:'Debug logging', default:false }
      }
    }
  };

  plugin.start = function(options) {
    const cfg = Object.assign(
      { minSOG:0.3, minSTW:0.3, maxDataAgeSecs:10, smoothingAlpha:0.7, maxCurrentKts:5, debug:false },
      options || {}
    );
    cfg.minSOG = Math.max(0, Math.min(2.0, Number(cfg.minSOG) || 0.3));
    cfg.minSTW = Math.max(0, Math.min(2.0, Number(cfg.minSTW) || 0.3));
    cfg.maxDataAgeSecs = Math.max(2, Math.min(60, Number(cfg.maxDataAgeSecs) || 10));
    cfg.smoothingAlpha = Math.max(0, Math.min(0.95, Number(cfg.smoothingAlpha) || 0.7));
    cfg.maxCurrentKts = Math.max(1, Math.min(10, Number(cfg.maxCurrentKts) || 5));

    unsubscribes=[]; ht=null; stw=null; cog=null; sog=null;
    lwy=0; htTs=0; stwTs=0; cogTs=0; sogTs=0; lwyTs=0;
    smoothN=null; smoothE=null;
    stats={derived:0,skipped:0,errors:0};

    svcLog('INFO','STARTUP: '+PLUGIN_ID+' v1.0.0');
    svcLog('INFO','CONFIG: minSOG='+cfg.minSOG+' minSTW='+cfg.minSTW
      +' maxAge='+cfg.maxDataAgeSecs+'s alpha='+cfg.smoothingAlpha
      +' maxCurrent='+cfg.maxCurrentKts+'kts');

    app.subscriptionManager.subscribe(
      { context:'vessels.self', subscribe:[
        {path:'navigation.headingTrue', period:500, policy:'ideal',minPeriod:200},
        {path:'navigation.speedThroughWater', period:1000, policy:'ideal',minPeriod:500},
        {path:'navigation.courseOverGroundTrue', period:1000, policy:'ideal',minPeriod:500},
        {path:'navigation.speedOverGround', period:1000, policy:'ideal',minPeriod:500},
        {path:'performance.leewayAngle', period:1000, policy:'ideal',minPeriod:500}
      ]},
      unsubscribes,
      function(err){stats.errors++;svcLog('ERROR','subscribe: '+err);},
      function(delta){
        try {
          var now=Date.now()/1000;
          if(!delta.updates)return;
          delta.updates.forEach(function(u){
            if(!u.values)return;
            u.values.forEach(function(pv){
              if(pv.value==null)return;
              switch(pv.path){
                case 'navigation.headingTrue': ht =pv.value;htTs =now;break;
                case 'navigation.speedThroughWater': stw=pv.value;stwTs=now;break;
                case 'navigation.courseOverGroundTrue': cog=pv.value;cogTs=now;break;
                case 'navigation.speedOverGround': sog=pv.value;sogTs=now;break;
                case 'performance.leewayAngle': lwy=pv.value;lwyTs=now;break;
              }
            });
          });
          if(sog!==null)compute(now,cfg);
        } catch(e){stats.errors++;svcLog('ERROR','delta: '+e.message);}
      }
    );

    svcLog('INFO','DEPENDENCY_CHECK: headingTrue+STW+COG+SOG+leewayAngle(opt)');
    if(app.setPluginStatus)app.setPluginStatus('Waiting for headingTrue+STW+COG+SOG');
    heartbeatTimer=setInterval(function(){
      var dk=smoothN!==null?(Math.sqrt(smoothN*smoothN+smoothE*smoothE)*MS_TO_KTS).toFixed(2)+'kts':'N/A';
      svcLog('DEBUG','HEARTBEAT: derived='+stats.derived+' skip='+stats.skipped+' err='+stats.errors+' drift='+dk);
    },5*60*1000);
    svcLog('INFO','STARTUP: complete');
  };

  // ── plugin.stop OUTSIDE plugin.start (guide section 1: MANDATORY) ────────
  plugin.stop=function(){
    svcLog('INFO','SHUTDOWN: stats='+JSON.stringify(stats));
    if(heartbeatTimer){clearInterval(heartbeatTimer);heartbeatTimer=null;}
    unsubscribes.forEach(function(u){try{u();}catch(_){}});
    unsubscribes=[];smoothN=null;smoothE=null;
    svcLog('INFO','SHUTDOWN: complete');
  };

  function compute(nowSec,cfg){
    var maxAge=cfg.maxDataAgeSecs;
    if(ht===null||(nowSec-htTs)>maxAge){stats.skipped++;return;}
    if(stw===null||(nowSec-stwTs)>maxAge){stats.skipped++;return;}
    if(cog===null||(nowSec-cogTs)>maxAge){stats.skipped++;return;}
    if(sog===null||(nowSec-sogTs)>maxAge){stats.skipped++;return;}

    if(!isFinite(ht)||isNaN(ht)){stats.errors++;return;}
    if(!isFinite(stw)||isNaN(stw)||stw<0||stw>30){stats.errors++;return;}
    if(!isFinite(cog)||isNaN(cog)){stats.errors++;return;}
    if(!isFinite(sog)||isNaN(sog)||sog<0||sog>30){stats.errors++;return;}

    var leeway=0;
    if(isFinite(lwy)&&!isNaN(lwy)&&Math.abs(lwy)<Math.PI/4)leeway=lwy;

    if(sog<cfg.minSOG){stats.skipped++;return;}
    if(stw<cfg.minSTW){stats.skipped++;return;}

    var ctw=ht+leeway;
    var rawN=sog*Math.cos(cog)-stw*Math.cos(ctw);
    var rawE=sog*Math.sin(cog)-stw*Math.sin(ctw);

    if(smoothN===null){smoothN=rawN;smoothE=rawE;}
    else{var a=cfg.smoothingAlpha;smoothN=a*smoothN+(1-a)*rawN;smoothE=a*smoothE+(1-a)*rawE;}

    var drift=Math.sqrt(smoothN*smoothN+smoothE*smoothE);
    var setRad=((Math.atan2(smoothE,smoothN)%TWO_PI)+TWO_PI)%TWO_PI;

    if(drift*MS_TO_KTS>cfg.maxCurrentKts){
      svcLog('WARN','drift='+(drift*MS_TO_KTS).toFixed(2)+'kts > cap → discard');
      stats.skipped++;return;
    }
    if(!isFinite(drift)||!isFinite(setRad)){stats.errors++;return;}

    app.handleMessage(PLUGIN_ID,{
      updates:[{source:{label:PLUGIN_ID,type:'derived'},timestamp:new Date().toISOString(),
        values:[{path:'environment.current.setTrue',value:setRad},
          {path:'environment.current.drift',value:drift}]}]
    });
    stats.derived++;

    var setDeg=(setRad*RAD_TO_DEG).toFixed(1);
    var driftKts=(drift*MS_TO_KTS).toFixed(2);
    if(cfg.debug)
      svcLog('DEBUG','DATA_OUT: set='+setDeg+'degT drift='+driftKts+'kts n='+stats.derived);
    flowLog('NavCalc→SK: set='+setDeg+'degT drift='+driftKts+'kts'
      +' CTW='+((ht+leeway)*RAD_TO_DEG).toFixed(1)+'deg ['+PLUGIN_ID+']');
    if(app.setPluginStatus)
      app.setPluginStatus('Set='+setDeg+'degT Drift='+driftKts+'kts | n='+stats.derived);
  }

  return plugin;
};
