# InfluxDB - le dernier souffle de chaque mesure

**Chantier** : influx-dernier-souffle-v1
**Base** : 47a4f7d28709f27208bb3fb36eeca39e32ba51a4
**Horodatage** : 20260922T011302Z
**Verdict** : `LIEN_MUET`

Le tir a blanc du 2026-09-21 a mesure une chose et une seule : dans la
fenetre de 60 s finissant a `2026-09-21T22:43:36Z`, aucune ligne
`navigation.position` / `lat` / `self="true"`. Il n a pas dit pourquoi.
Trois causes tenaient dans ce meme silence : plus rien n est ecrit ; on
ecrit encore mais sans l etiquette `self` - le defaut trouve la veille sur
l attitude du cockpit ; on ecrit encore sous un autre nom.

Ce constat ne repare rien. Il donne une empreinte a la panne.

## Le dernier souffle de chaque mesure

```
  mesure                                                   dernier point A NOUS  dernier point, tous   source  self     notre silence
  notifications.server.newVersion                          2026-09-15T01:53:27.614Z 2026-09-15T01:53:27.614Z signalk-server true     7.0 j     muette
  electrical.batteries.calypso.percent                     2026-09-07T14:36:24.135Z 2026-09-07T14:36:24.135Z Calypso.XX true     14.4 j    muette
  environment.current.drift                                2026-09-07T14:36:24.2Z 2026-09-07T14:36:24.2Z signalk-current-calculator.XX true     14.4 j    muette
  environment.current.setTrue                              2026-09-07T14:36:24.2Z 2026-09-07T14:36:24.2Z signalk-current-calculator.XX true     14.4 j    muette
  environment.depth.belowTransducer                        2026-09-07T14:36:24.063Z 2026-09-07T14:36:24.063Z N2K.35  true     14.4 j    muette
  environment.outside.pressure                             2026-09-07T14:36:24.151Z 2026-09-07T14:36:24.151Z N2K.116 true     14.4 j    muette
  environment.outside.temperature                          2026-09-07T14:36:24.135Z 2026-09-07T14:36:24.135Z Calypso.XX true     14.4 j    muette
  environment.water.temperature                            2026-09-07T14:36:24.206Z 2026-09-07T14:36:24.206Z N2K.35  true     14.4 j    muette
  environment.wind.angleApparent                           2026-09-07T14:36:24.135Z 2026-09-07T14:36:24.135Z Calypso.XX true     14.4 j    muette
  environment.wind.angleTrueGround                         2026-09-07T14:36:24.134Z 2026-09-07T14:36:24.134Z signalk-truewind-calculator.XX true     14.4 j    muette
  environment.wind.angleTrueWater                          2026-09-07T14:36:24.134Z 2026-09-07T14:36:24.134Z signalk-truewind-calculator.XX true     14.4 j    muette
  environment.wind.directionTrue                           2026-09-07T14:36:24.134Z 2026-09-07T14:36:24.134Z signalk-truewind-calculator.XX true     14.4 j    muette
  environment.wind.speedApparent                           2026-09-07T14:36:24.135Z 2026-09-07T14:36:24.135Z Calypso.XX true     14.4 j    muette
  environment.wind.speedOverGround                         2026-09-07T14:36:24.134Z 2026-09-07T14:36:24.134Z signalk-truewind-calculator.XX true     14.4 j    muette
  environment.wind.speedTrue                               2026-09-07T14:36:24.134Z 2026-09-07T14:36:24.134Z signalk-truewind-calculator.XX true     14.4 j    muette
  navigation.acceleration.x                                2026-09-07T14:36:24.281Z 2026-09-07T14:36:24.281Z Calypso.XX true     14.4 j    muette
  navigation.acceleration.y                                2026-09-07T14:36:24.281Z 2026-09-07T14:36:24.281Z Calypso.XX true     14.4 j    muette
  navigation.acceleration.z                                2026-09-07T14:36:24.281Z 2026-09-07T14:36:24.281Z Calypso.XX true     14.4 j    muette
  navigation.attitude.pitch                                2026-09-07T14:36:24.201Z 2026-09-07T14:36:24.201Z N2K.35  (absent) 14.4 j    muette
  navigation.attitude.roll                                 2026-09-07T14:36:24.201Z 2026-09-07T14:36:24.201Z N2K.35  (absent) 14.4 j    muette
  navigation.courseOverGroundTrue                          2026-09-07T14:36:24.201Z 2026-09-07T14:36:24.297Z N2K.0   (absent) 14.4 j    muette
  navigation.headingMagnetic                               2026-09-07T14:36:24.043Z 2026-09-07T14:36:24.043Z Calypso.XX true     14.4 j    muette
  navigation.headingTrue                                   2026-09-07T14:36:24.042Z 2026-09-07T14:36:24.295Z N2K.0   (absent) 14.4 j    muette
  navigation.log                                           2026-09-07T14:36:24.222Z 2026-09-07T14:36:24.222Z N2K.35  true     14.4 j    muette
  navigation.magneticVariation                             2026-09-07T14:36:24.098Z 2026-09-07T14:36:24.098Z N2K.5   true     14.4 j    muette
  navigation.position                                      2026-09-07T14:36:24.199Z 2026-09-07T14:36:24.298Z N2K.0   (absent) 14.4 j    muette
  navigation.rateOfTurn                                    2026-09-07T14:36:24.281Z 2026-09-07T14:36:24.295Z N2K.0   (absent) 14.4 j    muette
  navigation.speedOverGround                               2026-09-07T14:36:24.2Z 2026-09-07T14:36:24.297Z N2K.0   (absent) 14.4 j    muette
  navigation.speedThroughWater                             2026-09-07T14:36:24.214Z 2026-09-07T14:36:24.214Z N2K.35  true     14.4 j    muette
  navigation.speedThroughWaterReferenceType                2026-09-07T14:36:24.214Z 2026-09-07T14:36:24.214Z N2K.35  true     14.4 j    muette
  navigation.trip.log                                      2026-09-07T14:36:24.222Z 2026-09-07T14:36:24.222Z N2K.35  true     14.4 j    muette
  performance.leewayAngle                                  2026-09-07T14:36:24.041Z 2026-09-07T14:36:24.041Z signalk-j30-leeway.XX true     14.4 j    muette
  sensors.wit.magneticField.x                              2026-09-07T14:36:24.191Z 2026-09-07T14:36:24.191Z Calypso.XX true     14.4 j    muette
  sensors.wit.magneticField.y                              2026-09-07T14:36:24.191Z 2026-09-07T14:36:24.191Z Calypso.XX true     14.4 j    muette
  sensors.wit.magneticField.z                              2026-09-07T14:36:24.191Z 2026-09-07T14:36:24.191Z Calypso.XX true     14.4 j    muette
  sensors.wit.quaternion.w                                 2026-09-07T14:36:24.043Z 2026-09-07T14:36:24.043Z Calypso.XX true     14.4 j    muette
  sensors.wit.quaternion.x                                 2026-09-07T14:36:24.043Z 2026-09-07T14:36:24.043Z Calypso.XX true     14.4 j    muette
  sensors.wit.quaternion.y                                 2026-09-07T14:36:24.043Z 2026-09-07T14:36:24.043Z Calypso.XX true     14.4 j    muette
  sensors.wit.quaternion.z                                 2026-09-07T14:36:24.043Z 2026-09-07T14:36:24.043Z Calypso.XX true     14.4 j    muette
  sensors.wit.temperature                                  2026-09-07T14:36:24.191Z 2026-09-07T14:36:24.191Z Calypso.XX true     14.4 j    muette
  navigation.course.calcValues.bearingMagnetic             2026-09-07T14:36:23.93Z 2026-09-07T14:36:23.93Z course-provider true     14.4 j    muette
  navigation.course.calcValues.bearingTrackMagnetic        2026-09-07T14:36:23.929Z 2026-09-07T14:36:23.929Z course-provider true     14.4 j    muette
  navigation.course.calcValues.bearingTrackTrue            2026-09-07T14:36:23.929Z 2026-09-07T14:36:23.929Z course-provider true     14.4 j    muette
  navigation.course.calcValues.bearingTrue                 2026-09-07T14:36:23.93Z 2026-09-07T14:36:23.93Z course-provider true     14.4 j    muette
  navigation.course.calcValues.calcMethod                  2026-09-07T14:36:23.929Z 2026-09-07T14:36:23.929Z course-provider true     14.4 j    muette
  navigation.course.calcValues.crossTrackError             2026-09-07T14:36:23.93Z 2026-09-07T14:36:23.93Z course-provider true     14.4 j    muette
  navigation.course.calcValues.distance                    2026-09-07T14:36:23.93Z 2026-09-07T14:36:23.93Z course-provider true     14.4 j    muette
  navigation.course.calcValues.estimatedTimeOfArrival      2026-09-07T14:36:23.93Z 2026-09-07T14:36:23.93Z course-provider true     14.4 j    muette
  navigation.course.calcValues.previousPoint.distance      2026-09-07T14:36:23.93Z 2026-09-07T14:36:23.93Z course-provider true     14.4 j    muette
  navigation.course.calcValues.timeToGo                    2026-09-07T14:36:23.93Z 2026-09-07T14:36:23.93Z course-provider true     14.4 j    muette
  navigation.course.calcValues.velocityMadeGood            2026-09-07T14:36:23.93Z 2026-09-07T14:36:23.93Z course-provider true     14.4 j    muette
  navigation.courseRhumbline.nextPoint.position            2026-09-07T14:36:23.802Z 2026-09-07T14:36:23.802Z N2K.5   true     14.4 j    muette
  navigation.currentRoute.name                             2026-09-07T14:36:23.252Z 2026-09-07T14:36:23.252Z N2K.5   true     14.4 j    muette
  navigation.currentRoute.waypoints                        2026-09-07T14:36:23.252Z 2026-09-07T14:36:23.252Z N2K.5   true     14.4 j    muette
  navigation.datetime                                      2026-09-07T14:36:23.797Z 2026-09-07T14:36:23.797Z N2K.1   true     14.4 j    muette
  navigation.gnss.antennaAltitude                          2026-09-07T14:36:23.452Z 2026-09-07T14:36:23.452Z N2K.1   true     14.4 j    muette
  navigation.gnss.geoidalSeparation                        2026-09-07T14:36:23.453Z 2026-09-07T14:36:23.453Z N2K.1   true     14.4 j    muette
  navigation.gnss.horizontalDilution                       2026-09-07T14:36:23.453Z 2026-09-07T14:36:23.453Z N2K.1   true     14.4 j    muette
  navigation.gnss.integrity                                2026-09-07T14:36:23.453Z 2026-09-07T14:36:23.453Z N2K.1   true     14.4 j    muette
  navigation.gnss.methodQuality                            2026-09-07T14:36:23.453Z 2026-09-07T14:36:23.453Z N2K.1   true     14.4 j    muette
  navigation.gnss.positionDilution                         2026-09-07T14:36:23.453Z 2026-09-07T14:36:23.453Z N2K.1   true     14.4 j    muette
  navigation.gnss.satellites                               2026-09-07T14:36:23.453Z 2026-09-07T14:36:23.453Z N2K.1   true     14.4 j    muette
  navigation.gnss.satellitesInView                         2026-09-07T14:36:23.647Z 2026-09-07T14:36:23.647Z N2K.1   true     14.4 j    muette
  navigation.gnss.type                                     2026-09-07T14:36:23.453Z 2026-09-07T14:36:23.453Z N2K.1   true     14.4 j    muette
  performance.velocityMadeGoodToWaypoint                   2026-09-07T14:36:23.93Z 2026-09-07T14:36:23.93Z course-provider true     14.4 j    muette
  notifications.ais.unknown113                             2026-09-07T14:36:04.069Z 2026-09-07T14:36:04.069Z N2K.0   true     14.4 j    muette
  electrical.displays.navico.default.brightness            2026-09-07T14:15:53.696Z 2026-09-07T14:15:53.696Z N2K.9   true     14.5 j    muette
  notifications.navigation.course.perpendicularPassed      2026-09-07T13:32:04.365Z 2026-09-07T13:32:04.365Z course-provider true     14.5 j    muette
  notifications.ais.AIS12Valarm                            2026-09-07T13:21:14.763Z 2026-09-07T13:21:14.763Z N2K.0   true     14.5 j    muette
  navigation.courseGreatCircle.bearingTrackTrue            2026-09-07T13:08:20.151Z 2026-09-07T13:08:20.151Z N2K.8   true     14.5 j    muette
  navigation.courseGreatCircle.crossTrackError             2026-09-07T13:08:20.148Z 2026-09-07T13:08:20.148Z N2K.8   true     14.5 j    muette
  navigation.courseGreatCircle.nextPoint.bearingTrue       2026-09-07T13:08:20.151Z 2026-09-07T13:08:20.151Z N2K.8   true     14.5 j    muette
  navigation.courseGreatCircle.nextPoint.distance          2026-09-07T13:08:20.151Z 2026-09-07T13:08:20.151Z N2K.8   true     14.5 j    muette
  navigation.courseGreatCircle.nextPoint.position          2026-09-07T13:08:20.151Z 2026-09-07T13:08:20.151Z N2K.8   true     14.5 j    muette
  navigation.courseGreatCircle.nextPoint.velocityMadeGood  2026-09-07T13:08:20.151Z 2026-09-07T13:08:20.151Z N2K.8   true     14.5 j    muette
  navigation.courseGreatCircle.nextPoint.timeToGo          2026-09-07T13:01:56.531Z 2026-09-07T13:01:56.531Z N2K.8   true     14.5 j    muette
  navigation.course.arrivalCircle                          2026-09-07T11:17:00.301Z 2026-09-07T11:17:00.301Z courseApi true     14.6 j    muette
  navigation.course.nextPoint                              2026-09-07T11:17:00.309Z 2026-09-07T11:17:00.309Z N2K.8   true     14.6 j    muette
  navigation.course.previousPoint                          2026-09-07T11:17:00.304Z 2026-09-07T11:17:00.304Z courseApi true     14.6 j    muette
  navigation.course.startTime                              2026-09-07T11:17:00.291Z 2026-09-07T11:17:00.291Z courseApi true     14.6 j    muette
  navigation.courseGreatCircle.activeRoute.startTime       2026-09-07T11:17:00.209Z 2026-09-07T11:17:00.209Z courseApi true     14.6 j    muette
  navigation.courseGreatCircle.nextPoint.arrivalCircle     2026-09-07T11:17:00.228Z 2026-09-07T11:17:00.228Z courseApi true     14.6 j    muette
  navigation.courseGreatCircle.nextPoint.value.type        2026-09-07T11:17:00.22Z 2026-09-07T11:17:00.22Z courseApi true     14.6 j    muette
  navigation.courseGreatCircle.previousPoint.position      2026-09-07T11:17:00.232Z 2026-09-07T11:17:00.232Z courseApi true     14.6 j    muette
  navigation.courseGreatCircle.previousPoint.value.type    2026-09-07T11:17:00.236Z 2026-09-07T11:17:00.236Z courseApi true     14.6 j    muette
  navigation.courseRhumbline.activeRoute.startTime         2026-09-07T11:17:00.209Z 2026-09-07T11:17:00.209Z courseApi true     14.6 j    muette
  navigation.courseRhumbline.nextPoint.arrivalCircle       2026-09-07T11:17:00.231Z 2026-09-07T11:17:00.231Z courseApi true     14.6 j    muette
  navigation.courseRhumbline.nextPoint.value.type          2026-09-07T11:17:00.224Z 2026-09-07T11:17:00.224Z courseApi true     14.6 j    muette
  navigation.courseRhumbline.previousPoint.position        2026-09-07T11:17:00.232Z 2026-09-07T11:17:00.232Z courseApi true     14.6 j    muette
  navigation.courseRhumbline.previousPoint.value.type      2026-09-07T11:17:00.239Z 2026-09-07T11:17:00.239Z courseApi true     14.6 j    muette
  navigation.courseRhumbline.crossTrackError               2026-09-07T11:16:59.686Z 2026-09-07T11:16:59.686Z N2K.8   true     14.6 j    muette
  electrical.displays.navico.default.nightMode.state       2026-09-04T16:06:01.133Z 2026-09-04T16:06:01.133Z N2K.9   true     17.4 j    muette
  notifications.ais.AISNosensorposition                    2026-08-30T19:11:15.535Z 2026-08-30T19:11:15.535Z N2K.0   true     22.3 j    muette
  navigation.attitude.yaw                                  2026-08-30T01:30:00.87Z 2026-08-30T01:30:00.87Z Calypso.XX true     23.0 j    muette
  <empty>                                                  (aucun)               2026-09-07T14:36:24.298Z N2K.0   (absent) -         AUCUN POINT A NOUS
  atonType                                                 (aucun)               2026-09-07T14:36:22.153Z N2K.0   (absent) -         AUCUN POINT A NOUS
  design.aisShipType                                       (aucun)               2026-09-07T14:36:16.699Z N2K.0   (absent) -         AUCUN POINT A NOUS
  design.beam                                              (aucun)               2026-09-07T14:36:19.339Z N2K.0   (absent) -         AUCUN POINT A NOUS
  design.draft                                             (aucun)               2026-09-07T14:36:05.18Z N2K.0   (absent) -         AUCUN POINT A NOUS
  design.length                                            (aucun)               2026-09-07T14:36:19.339Z N2K.0   (absent) -         AUCUN POINT A NOUS
  navigation.destination.commonName                        (aucun)               2026-09-07T14:36:19.339Z N2K.0   (absent) -         AUCUN POINT A NOUS
  navigation.specialManeuver                               (aucun)               2026-09-07T14:36:24.298Z N2K.0   (absent) -         AUCUN POINT A NOUS
  navigation.state                                         (aucun)               2026-09-07T14:36:24.298Z N2K.0   (absent) -         AUCUN POINT A NOUS
  offPosition                                              (aucun)               2026-09-07T14:36:22.153Z N2K.0   (absent) -         AUCUN POINT A NOUS
  selftest.token_rotation                                  (aucun)               2026-09-15T20:25:12Z  h2a     (absent) -         AUCUN POINT A NOUS
  sensors.ais.class                                        (aucun)               2026-09-07T14:36:24.298Z N2K.0   (absent) -         AUCUN POINT A NOUS
  sensors.ais.fromBow                                      (aucun)               2026-09-07T14:36:19.339Z N2K.0   (absent) -         AUCUN POINT A NOUS
  sensors.ais.fromCenter                                   (aucun)               2026-09-07T14:36:19.339Z N2K.0   (absent) -         AUCUN POINT A NOUS
  system                                                   (aucun)               2026-09-22T01:12:[COORD-MASQUEE]Z -       (absent) -         AUCUN POINT A NOUS
  virtual                                                  (aucun)               2026-09-07T14:36:22.153Z N2K.0   (absent) -         AUCUN POINT A NOUS

  MESURES_VIVANTES=0
  MESURES_MUETTES=110
  POSITION_DERNIER_A_NOUS=2026-09-07T14:36:24.199Z
  POSITION_DERNIER_TOUS=2026-09-07T14:36:24.298Z
  POSITION_ETAT=muette
  POSITION_SELF_DU_DERNIER_TOUS=absent
```

## navigation.position jour par jour, avec et sans l etiquette self

Comptes seuls. Aucune coordonnee n a ete demandee a InfluxDB.

```
  jour (UTC)         a nous       toutes   lecture
  2026-08-24              0            0   silence complet, nous et les autres
  2026-08-25              0            0   silence complet, nous et les autres
  2026-08-26              0            0   silence complet, nous et les autres
  2026-08-27              0            0   silence complet, nous et les autres
  2026-08-28              0            0   silence complet, nous et les autres
  2026-08-29              0            0   silence complet, nous et les autres
  2026-08-30              0        89326   aucune ligne a nous ; d autres contextes ecrivent
  2026-08-31              0      1290573   aucune ligne a nous ; d autres contextes ecrivent
  2026-09-01              0            0   silence complet, nous et les autres
  2026-09-02              0            0   silence complet, nous et les autres
  2026-09-03              0            0   silence complet, nous et les autres
  2026-09-04              0           70   aucune ligne a nous ; d autres contextes ecrivent
  2026-09-05              0      1052971   aucune ligne a nous ; d autres contextes ecrivent
  2026-09-06              0      2234042   aucune ligne a nous ; d autres contextes ecrivent
  2026-09-07              0      1525897   aucune ligne a nous ; d autres contextes ecrivent
  2026-09-08              0       405381   aucune ligne a nous ; d autres contextes ecrivent
  2026-09-09              0            0   silence complet, nous et les autres
  2026-09-10              0            0   silence complet, nous et les autres
  2026-09-11              0            0   silence complet, nous et les autres
  2026-09-12              0            0   silence complet, nous et les autres
  2026-09-13              0            0   silence complet, nous et les autres
  2026-09-14              0            0   silence complet, nous et les autres
  2026-09-15              0            0   silence complet, nous et les autres
  2026-09-16              0            0   silence complet, nous et les autres
  2026-09-17              0            0   silence complet, nous et les autres
  2026-09-18              0            0   silence complet, nous et les autres
  2026-09-19              0            0   silence complet, nous et les autres
  2026-09-20              0            0   silence complet, nous et les autres
  2026-09-21              0            0   silence complet, nous et les autres
  2026-09-22              0            0   silence complet, nous et les autres

  DERNIER_JOUR_AVEC_SELF=aucun
  DERNIER_JOUR_TOUTES_LIGNES=2026-09-08
  JOURS_SANS_AUCUNE_LIGNE_A_NOUS=30
```

## Retention du bucket

```
  bucket : midnight_rider
  cree le : 2026-05-03T22:54:[COORD-MASQUEE]Z
  retention : infinie - rien n expire
  RETENTION_SECONDES=0
```

## Lecture

aucune des 110 mesures du bucket n a recu de point A NOUS depuis plus d une heure. Ce n est pas un chemin qui manque : plus rien de ce qui nous concerne n entre. Le lien Signal K -> InfluxDB n ecrit plus.

## Ce que ce constat ne dit pas

- Il ne dit pas pourquoi le lien ou le chemin s est tu.
- Il porte sur ce qui est ARRIVE dans InfluxDB, jamais sur ce que Signal K
  a emis. Un capteur muet et un lien coupe laissent ici la meme trace.
- Il ne regarde que les 60 derniers jours.

## Ce que ce chantier n a pas fait

Aucune ecriture InfluxDB : le seul chemin HTTP appele est
`POST /api/v2/query`, plus un `GET /api/v2/buckets` pour la retention.
Aucun geste systemd, aucun geste docker, aucun redemarrage, aucun envoi
Telegram. Le jeton a ete lu depuis `/home/aneto/midnightrider-navigation/.env`, place dans un en-tete
HTTP, jamais affiche, jamais ecrit, jamais passe en argument.

Requetes reussies : 8. Requetes en echec : 1.
Reponses brutes conservees sur la machine dans `/tmp/ds-brut-20260922T011302Z`, hors depot.
