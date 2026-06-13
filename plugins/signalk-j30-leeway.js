'use strict';
/**
 * @file signalk-j30-leeway.js
 * @version 1.0.2
 * @license MIT
 * CHANGELOG
 * v1.0.2 — Fix: app.subscriptionManager undefined in SK 2.25.0.
 * Replaced with setInterval + app.getSelfPath().
 * v1.0.1 — plugin.stop outside plugin.start
 */
const fs = require('fs');
const PLUGIN_ID = 'signalk-j30-leeway';
const LOG_BASE = '/home/aneto/midnightrider-navigation/logs';
const LOG_SVC = LOG_BASE + '/services/j30-leeway-calc.log';
const LOG_FLOW = LOG_BASE + '/debug/data-flow.log';
const MAX_BYTES = 5 * 1024 * 1024;
const MS_TO_KTS = 1 / 0.5144;
const DEG_TO_RAD = Math.PI / 180;

module.exports = function(app) {
  function ensureDirs(){try{fs.mkdirSync(LOG_BASE+'/services',{recursive:true});fs.mkdirSync(LOG_BASE+'/debug',{recursive:true});}catch(_){}}
  function rotateIfNeeded(f){try{if(fs.existsSync(f)&&fs.statSync(f).size>MAX_BYTES)fs.renameSync(f,f+'.1');}catch(_){}}
  function svcLog(level,msg){try{ensureDirs();rotateIfNeeded(LOG_SVC);fs.appendFileSync(LOG_SVC,'['+new Date().toISOString()+'] ['+level+'] [j30-leeway-calc] '+msg+'\n');}catch(_){}}
  function flowLog(msg){try{rotateIfNeeded(LOG_FLOW);fs.appendFileSync(LOG_FLOW,'['+new Date().toISOString()+'] [FLOW] '+msg+'\n');}catch(_){}}

  let pollTimer=null, heartbeatTimer=null;
  let stats={derived:0,skipped:0,errors:0};

  const plugin={
    id:PLUGIN_ID,
    name:'J/30 Leeway Calculator',
    description:'Leeway(deg)=K×|Heel(deg)|/STW(kts)². K=12. SOG fallback when no log.',
    version:'1.0.2',
    schema:{type:'object',title:'J/30 Leeway Calculator',properties:{
      leewayFactor: {type:'number', title:'K (J/30: 10-14)', default:12, minimum:5, maximum:25 },
      minSpeed: {type:'number', title:'Min speed kts', default:0.5, minimum:0.1, maximum:3.0 },
      maxLeeway: {type:'number', title:'Max leeway deg', default:15, minimum:5, maximum:30 },
      minHeel: {type:'number', title:'Min heel deg', default:1.0, minimum:0.5, maximum:5.0 },
      leewaySign: {type:'number', title:'Sign (-1 or +1)', default:-1, enum:[-1,1] },
      maxRollAgeSecs:{type:'number', title:'Max roll age s', default:5, minimum:1, maximum:30 },
      pollMs: {type:'number', title:'Poll interval ms', default:500, minimum:100,maximum:2000},
      debug: {type:'boolean',title:'Debug logging', default:false}
    }}
  };

  plugin.start=function(options){
    var cfg=Object.assign({leewayFactor:12,minSpeed:0.5,maxLeeway:15,minHeel:1.0,leewaySign:-1,maxRollAgeSecs:5,pollMs:500,debug:false},options||{});
    cfg.leewayFactor =Math.max(5, Math.min(25, Number(cfg.leewayFactor) ||12));
    cfg.minSpeed =Math.max(0.1,Math.min(3.0, Number(cfg.minSpeed) ||0.5));
    cfg.maxLeeway =Math.max(5, Math.min(30, Number(cfg.maxLeeway) ||15));
    cfg.minHeel =Math.max(0.5,Math.min(5.0, Number(cfg.minHeel) ||1.0));
    cfg.maxRollAgeSecs=Math.max(1, Math.min(30, Number(cfg.maxRollAgeSecs)||5));
    cfg.pollMs =Math.max(100,Math.min(2000,Number(cfg.pollMs) ||500));
    cfg.leewaySign =(cfg.leewaySign===1)?1:-1;
    stats={derived:0,skipped:0,errors:0};

    svcLog('INFO','STARTUP: '+PLUGIN_ID+' v1.0.2');
    svcLog('INFO','CONFIG: K='+cfg.leewayFactor+' minSpeed='+cfg.minSpeed+'kts pollMs='+cfg.pollMs);
    if(app.setPluginStatus) app.setPluginStatus('Polling roll+speed @ '+cfg.pollMs+'ms');

    pollTimer=setInterval(function(){
      try{
        var now=Date.now();
        var rollObj=app.getSelfPath('navigation.attitude.roll');
        if(!rollObj||rollObj.value==null){stats.skipped++;return;}
        var roll=rollObj.value;
        var rollAge=rollObj.timestamp?(now-new Date(rollObj.timestamp).getTime())/1000:0;
        if(rollAge>cfg.maxRollAgeSecs){stats.skipped++;return;}
        if(!isFinite(roll)||isNaN(roll)||Math.abs(roll)>Math.PI){stats.errors++;return;}

        var speedKts=0,speedSrc='none';
        var stwObj=app.getSelfPath('navigation.speedThroughWater');
        var sogObj=app.getSelfPath('navigation.speedOverGround');
        if(stwObj&&stwObj.value!=null&&isFinite(stwObj.value)&&stwObj.value>=0){
          speedKts=stwObj.value*MS_TO_KTS; speedSrc='STW';
        }else if(sogObj&&sogObj.value!=null&&isFinite(sogObj.value)&&sogObj.value>=0){
          speedKts=sogObj.value*MS_TO_KTS; speedSrc='SOG';
        }

        var heelDeg=roll*180/Math.PI;
        var lwyRad=0;
        if(speedKts>=cfg.minSpeed&&Math.abs(heelDeg)>=cfg.minHeel){
          var lwyDeg=Math.min(cfg.leewayFactor*Math.abs(heelDeg)/(speedKts*speedKts),cfg.maxLeeway);
          lwyRad=cfg.leewaySign*(roll>=0?1:-1)*lwyDeg*DEG_TO_RAD;
        }
        if(!isFinite(lwyRad)){stats.errors++;return;}

        app.handleMessage(PLUGIN_ID,{updates:[{
          source:{label:PLUGIN_ID,type:'derived'},
          timestamp:new Date().toISOString(),
          values:[{path:'performance.leewayAngle',value:lwyRad}]
        }]});
        stats.derived++;
        var lD=(lwyRad*180/Math.PI).toFixed(1);
        if(cfg.debug) svcLog('DEBUG','leeway='+lD+'deg Heel='+heelDeg.toFixed(1)+' Spd='+speedKts.toFixed(2)+'kts('+speedSrc+')');
        flowLog('J30→SK: leeway='+lD+'deg ['+PLUGIN_ID+']');
        if(app.setPluginStatus) app.setPluginStatus('Leeway='+lD+'deg pub='+stats.derived);
      }catch(e){stats.errors++;svcLog('ERROR','poll: '+e.message);}
    },cfg.pollMs);

    heartbeatTimer=setInterval(function(){
      svcLog('DEBUG','HEARTBEAT: derived='+stats.derived+' skip='+stats.skipped+' err='+stats.errors);
    },5*60*1000);
    svcLog('INFO','STARTUP: complete');
  };

  plugin.stop=function(){
    svcLog('INFO','SHUTDOWN: '+JSON.stringify(stats));
    if(pollTimer){clearInterval(pollTimer);pollTimer=null;}
    if(heartbeatTimer){clearInterval(heartbeatTimer);heartbeatTimer=null;}
    svcLog('INFO','SHUTDOWN: complete');
  };

  return plugin;
};
