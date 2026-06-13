'use strict';
/**
 * @file signalk-current-calculator.js
 * @version 1.0.1
 * @license MIT
 * CHANGELOG
 * v1.0.1 — Fix: app.subscriptionManager undefined in SK 2.25.0.
 * Replaced with setInterval + app.getSelfPath().
 * v1.0.0 — Initial release
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
  function ensureDirs(){try{fs.mkdirSync(LOG_BASE+'/services',{recursive:true});fs.mkdirSync(LOG_BASE+'/debug',{recursive:true});}catch(_){}}
  function rotateIfNeeded(f){try{if(fs.existsSync(f)&&fs.statSync(f).size>MAX_BYTES)fs.renameSync(f,f+'.1');}catch(_){}}
  function svcLog(level,msg){try{ensureDirs();rotateIfNeeded(LOG_SVC);fs.appendFileSync(LOG_SVC,'['+new Date().toISOString()+'] ['+level+'] [current-calc] '+msg+'\n');}catch(_){}}
  function flowLog(msg){try{rotateIfNeeded(LOG_FLOW);fs.appendFileSync(LOG_FLOW,'['+new Date().toISOString()+'] [FLOW] '+msg+'\n');}catch(_){}}

  let pollTimer=null, heartbeatTimer=null;
  let smoothN=null, smoothE=null;
  let stats={derived:0,skipped:0,errors:0};

  const plugin={
    id:PLUGIN_ID,
    name:'Water Current Calculator (Set & Drift)',
    description:'environment.current.setTrue+drift from CTW/STW vs COG/SOG. CTW=HT+leeway.',
    version:'1.0.1',
    schema:{type:'object',title:'Water Current Calculator',properties:{
      minSOG: {type:'number', title:'Min SOG m/s', default:0.3, minimum:0, maximum:2.0 },
      minSTW: {type:'number', title:'Min STW m/s', default:0.3, minimum:0, maximum:2.0 },
      maxDataAgeSecs:{type:'number', title:'Max input age s', default:10, minimum:2, maximum:60 },
      smoothingAlpha:{type:'number', title:'EMA alpha', default:0.7, minimum:0, maximum:0.95},
      maxCurrentKts: {type:'number', title:'Max current kts', default:5, minimum:1, maximum:10 },
      pollMs: {type:'number', title:'Poll interval ms', default:1000,minimum:200, maximum:5000},
      debug: {type:'boolean',title:'Debug logging', default:false}
    }}
  };

  plugin.start=function(options){
    var cfg=Object.assign({minSOG:0.3,minSTW:0.3,maxDataAgeSecs:10,smoothingAlpha:0.7,maxCurrentKts:5,pollMs:1000,debug:false},options||{});
    cfg.minSOG =Math.max(0, Math.min(2.0, Number(cfg.minSOG) ||0.3));
    cfg.minSTW =Math.max(0, Math.min(2.0, Number(cfg.minSTW) ||0.3));
    cfg.maxDataAgeSecs=Math.max(2, Math.min(60, Number(cfg.maxDataAgeSecs)||10));
    cfg.smoothingAlpha=Math.max(0, Math.min(0.95,Number(cfg.smoothingAlpha)||0.7));
    cfg.maxCurrentKts =Math.max(1, Math.min(10, Number(cfg.maxCurrentKts) ||5));
    cfg.pollMs =Math.max(200,Math.min(5000,Number(cfg.pollMs) ||1000));
    smoothN=null; smoothE=null;
    stats={derived:0,skipped:0,errors:0};

    svcLog('INFO','STARTUP: '+PLUGIN_ID+' v1.0.1');
    svcLog('INFO','CONFIG: alpha='+cfg.smoothingAlpha+' maxCurrent='+cfg.maxCurrentKts+'kts pollMs='+cfg.pollMs);
    if(app.setPluginStatus) app.setPluginStatus('Polling HT+STW+COG+SOG @ '+cfg.pollMs+'ms');

    pollTimer=setInterval(function(){
      try{
        var maxAgeMs=cfg.maxDataAgeSecs*1000;
        var now=Date.now();
        function getVal(path){
          var o=app.getSelfPath(path);
          if(!o||o.value==null) return null;
          if(o.timestamp&&(now-new Date(o.timestamp).getTime())>maxAgeMs) return null;
          return o.value;
        }
        var ht =getVal('navigation.headingTrue');
        var stw=getVal('navigation.speedThroughWater');
        var cog=getVal('navigation.courseOverGroundTrue');
        var sog=getVal('navigation.speedOverGround');
        var lwy=getVal('performance.leewayAngle');
        if(ht==null||stw==null||cog==null||sog==null){stats.skipped++;return;}
        if(!isFinite(ht)||!isFinite(stw)||!isFinite(cog)||!isFinite(sog)){stats.errors++;return;}
        if(sog<cfg.minSOG||stw<cfg.minSTW){stats.skipped++;return;}

        var leeway=(lwy!=null&&isFinite(lwy)&&Math.abs(lwy)<Math.PI/4)?lwy:0;
        var ctw=ht+leeway;
        var rawN=sog*Math.cos(cog)-stw*Math.cos(ctw);
        var rawE=sog*Math.sin(cog)-stw*Math.sin(ctw);
        if(smoothN==null){smoothN=rawN;smoothE=rawE;}
        else{var a=cfg.smoothingAlpha;smoothN=a*smoothN+(1-a)*rawN;smoothE=a*smoothE+(1-a)*rawE;}

        var drift=Math.sqrt(smoothN*smoothN+smoothE*smoothE);
        var setRad=((Math.atan2(smoothE,smoothN)%TWO_PI)+TWO_PI)%TWO_PI;
        if(drift*MS_TO_KTS>cfg.maxCurrentKts){stats.skipped++;return;}
        if(!isFinite(drift)||!isFinite(setRad)){stats.errors++;return;}

        app.handleMessage(PLUGIN_ID,{updates:[{
          source:{label:PLUGIN_ID,type:'derived'},
          timestamp:new Date().toISOString(),
          values:[{path:'environment.current.setTrue',value:setRad},
            {path:'environment.current.drift',value:drift}]
        }]});
        stats.derived++;
        var sD=(setRad*RAD_TO_DEG).toFixed(1),dK=(drift*MS_TO_KTS).toFixed(2);
        if(cfg.debug) svcLog('DEBUG','set='+sD+'deg drift='+dK+'kts n='+stats.derived);
        flowLog('NavCalc→SK: set='+sD+'degT drift='+dK+'kts ['+PLUGIN_ID+']');
        if(app.setPluginStatus) app.setPluginStatus('Set='+sD+'degT Drift='+dK+'kts | n='+stats.derived);
      }catch(e){stats.errors++;svcLog('ERROR','poll: '+e.message);}
    },cfg.pollMs);

    heartbeatTimer=setInterval(function(){
      var dk=smoothN!=null?(Math.sqrt(smoothN*smoothN+smoothE*smoothE)*MS_TO_KTS).toFixed(2)+'kts':'N/A';
      svcLog('DEBUG','HEARTBEAT: derived='+stats.derived+' skip='+stats.skipped+' drift='+dk);
    },5*60*1000);
    svcLog('INFO','STARTUP: complete');
  };

  plugin.stop=function(){
    svcLog('INFO','SHUTDOWN: '+JSON.stringify(stats));
    if(pollTimer){clearInterval(pollTimer);pollTimer=null;}
    if(heartbeatTimer){clearInterval(heartbeatTimer);heartbeatTimer=null;}
    smoothN=null;smoothE=null;
    svcLog('INFO','SHUTDOWN: complete');
  };

  return plugin;
};
