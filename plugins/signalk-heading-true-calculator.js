'use strict';
/**
 * @file signalk-heading-true-calculator.js
 * @version 1.0.3
 * @license MIT
 * CHANGELOG
 * v1.0.3 — Fix: app.subscriptionManager undefined in SK 2.25.0.
 * Replaced with setInterval + app.getSelfPath() — robust pattern.
 * v1.0.2 — plugin.stop outside plugin.start
 */
const fs = require('fs');
const PLUGIN_ID = 'signalk-heading-true-calculator';
const LOG_BASE = '/home/aneto/midnightrider-navigation/logs';
const LOG_SVC = LOG_BASE + '/services/heading-true-calc.log';
const LOG_FLOW = LOG_BASE + '/debug/data-flow.log';
const MAX_BYTES = 5 * 1024 * 1024;
const TWO_PI = 2 * Math.PI;

module.exports = function(app) {
  function ensureDirs(){try{fs.mkdirSync(LOG_BASE+'/services',{recursive:true});fs.mkdirSync(LOG_BASE+'/debug',{recursive:true});}catch(_){}}
  function rotateIfNeeded(f){try{if(fs.existsSync(f)&&fs.statSync(f).size>MAX_BYTES)fs.renameSync(f,f+'.1');}catch(_){}}
  function svcLog(level,msg){try{ensureDirs();rotateIfNeeded(LOG_SVC);fs.appendFileSync(LOG_SVC,'['+new Date().toISOString()+'] ['+level+'] [heading-true-calc] '+msg+'\n');}catch(_){}}
  function flowLog(msg){try{rotateIfNeeded(LOG_FLOW);fs.appendFileSync(LOG_FLOW,'['+new Date().toISOString()+'] [FLOW] '+msg+'\n');}catch(_){}}

  let pollTimer=null, heartbeatTimer=null;
  let stats={derived:0,skipped:0,errors:0};

  const plugin={
    id:PLUGIN_ID,
    name:'True Heading Calculator (Magnetic + Variation)',
    description:'Derives navigation.headingTrue from headingMagnetic + magneticVariation.',
    version:'1.0.3',
    schema:{type:'object',title:'True Heading Calculator',properties:{
      debug: {type:'boolean',title:'Debug logging', default:false},
      staleSecs: {type:'number', title:'External headingTrue stale(s)', default:10, minimum:1, maximum:300},
      maxHMAgeSecs:{type:'number', title:'Max headingMagnetic age(s)', default:5, minimum:1, maximum:60 },
      pollMs: {type:'number', title:'Poll interval ms', default:500,minimum:100,maximum:2000}
    }}
  };

  plugin.start=function(options){
    var cfg=Object.assign({debug:false,staleSecs:10,maxHMAgeSecs:5,pollMs:500},options||{});
    cfg.staleSecs =Math.max(1, Math.min(300, Number(cfg.staleSecs) ||10));
    cfg.maxHMAgeSecs=Math.max(1, Math.min(60, Number(cfg.maxHMAgeSecs)||5));
    cfg.pollMs =Math.max(100,Math.min(2000,Number(cfg.pollMs) ||500));
    stats={derived:0,skipped:0,errors:0};

    svcLog('INFO','STARTUP: '+PLUGIN_ID+' v1.0.3');
    svcLog('INFO','CONFIG: pollMs='+cfg.pollMs+' staleSecs='+cfg.staleSecs);
    svcLog('INFO','PATTERN: setInterval+getSelfPath (subscriptionManager removed)');
    if(app.setPluginStatus) app.setPluginStatus('Polling headingMagnetic @ '+cfg.pollMs+'ms');

    pollTimer=setInterval(function(){
      try{
        var now=Date.now();
        var hmObj=app.getSelfPath('navigation.headingMagnetic');
        if(!hmObj||hmObj.value==null){stats.skipped++;return;}
        var hm=hmObj.value;
        var hmAge=hmObj.timestamp?(now-new Date(hmObj.timestamp).getTime())/1000:0;
        if(hmAge>cfg.maxHMAgeSecs){stats.skipped++;return;}
        if(!isFinite(hm)||isNaN(hm)||Math.abs(hm)>4*Math.PI){stats.errors++;return;}

        var variation=0;
        var mvObj=app.getSelfPath('navigation.magneticVariation');
        if(mvObj&&mvObj.value!=null&&isFinite(mvObj.value)&&!isNaN(mvObj.value))
          variation=Math.max(-Math.PI,Math.min(Math.PI,mvObj.value));

        var htObj=app.getSelfPath('navigation.headingTrue');
        if(htObj&&htObj.value!=null){
          var src=(htObj.source&&htObj.source.label)?htObj.source.label:'';
          if(src!==PLUGIN_ID){
            var age=htObj.timestamp?(now-new Date(htObj.timestamp).getTime())/1000:Infinity;
            if(age<cfg.staleSecs){stats.skipped++;return;}
          }
        }

        var ht=(((hm+variation)%TWO_PI)+TWO_PI)%TWO_PI;
        if(!isFinite(ht)){stats.errors++;return;}

        app.handleMessage(PLUGIN_ID,{updates:[{
          source:{label:PLUGIN_ID,type:'derived'},
          timestamp:new Date().toISOString(),
          values:[{path:'navigation.headingTrue',value:ht}]
        }]});
        stats.derived++;
        var htD=(ht*180/Math.PI).toFixed(1),hmD=(hm*180/Math.PI).toFixed(1),vD=(variation*180/Math.PI).toFixed(2);
        if(cfg.debug) svcLog('DEBUG','HT='+htD+'deg HM='+hmD+'deg Var='+vD+'deg n='+stats.derived);
        flowLog('Compass→SK: headingTrue='+htD+'deg ['+PLUGIN_ID+']');
        if(app.setPluginStatus) app.setPluginStatus('HT='+htD+'deg pub='+stats.derived+' skip='+stats.skipped);
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
