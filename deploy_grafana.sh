#!/bin/bash
cd /home/aneto/.openclaw/workspace
source .env

for json in \
    grafana-dashboards/07-race.json \
    grafana-dashboards/03-performance.json \
    grafana-dashboards/09-crew.json \
    grafana-dashboards/01-navigation-dashboard.json \
    grafana-dashboards/04-wind-current.json \
    grafana-dashboards/08-alerts.json; do
    
    [[ ! -f "$json" ]] && echo "⚠️ $json absent" && continue
    
    DASH=$(python3 -c "import json; d=json.load(open('$json')); r=d.get('dashboard',d); r['id']=None; print(json.dumps({'dashboard':r,'overwrite':True,'folderId':0}))")
    
    R=$(curl -s -X POST -H "Content-Type: application/json" \
        -u "admin:${GRAFANA_PASSWORD:-admin}" -d "$DASH" \
        http://localhost:3001/api/dashboards/db)
    
    S=$(echo "$R" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null)
    U=$(echo "$R" | python3 -c "import json,sys; print(json.load(sys.stdin).get('uid','?'))" 2>/dev/null)
    
    if [[ "$S" == "success" ]]; then
        echo "✅ $U"
    else
        echo "❌ $(basename $json)"
    fi
done
