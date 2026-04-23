# 🔴 SIGNAL K - LEÇONS CRITIQUES

**Ces leçons DOIVENT être mémorisées. Elles évitent des heures de debugging!**

---

## 🔴 LEÇON #1: Signal K v2.25 - npm link NE FONCTIONNE PAS

### Le Problème
- ❌ `npm link` crée des symlinks dans `~/.signalk/node_modules/`
- ❌ Signal K v2.25 **IGNORE les symlinks**
- ❌ Plugin jamais découvert, jamais chargé

### La Solution
**Copier directement au lieu de linker:**

```bash
# ❌ MAUVAIS (ne fonctionne pas):
npm link
cd ~/.signalk && npm link my-plugin

# ✅ CORRECT (fonctionne toujours):
cp -r ~/my-plugin ~/.signalk/node_modules/
```

### Checklist
1. Créer code plugin avec structure correcte
2. Créer `package.json` avec keywords `signalk-node-server-plugin`
3. **Copier directement** dans `~/.signalk/node_modules/`
4. Ajouter config dans `settings.json`
5. Redémarrer Signal K
6. **Activer manuellement via Admin UI**

---

## 🔴 LEÇON #2: Plugin Installed ≠ Plugin Running

### Le Problème
Même si un plugin est:
- ✅ Installé dans `~/.signalk/node_modules/`
- ✅ Dans `settings.json` avec `enabled: true`
- ✅ Découvert par Signal K (visible dans `/skServer/plugins`)
- **❌ IL NE FONCTIONNE PAS TANT QU'ON NE L'ACTIVE PAS MANUELLEMENT**

### La Solution
**Utiliser l'interface Admin Signal K:**

1. Ouvrir: `http://localhost:3000`
2. Admin → Installed Plugins
3. Trouver le plugin
4. Cliquer **Enable** ou toggle **ON**
5. Le plugin démarre

### Pourquoi?
- Signal K sépare "découvert" et "en cours d'exécution"
- Configuration ne lance pas automatiquement
- Sécurité: laisser l'utilisateur décider

### TOUJOURS VÉRIFIER
```bash
curl http://localhost:3000/skServer/plugins | grep "votre-plugin"
```

---

## 🔴 LEÇON #3: Structure Signal K v2.25 Correcte

### Format CORRECT
```javascript
module.exports = function(app) {
  const plugin = {}

  plugin.id = 'signalk-mon-plugin'
  plugin.name = 'Mon Plugin'
  plugin.description = 'Description'

  plugin.schema = {
    type: 'object',
    properties: {}
  }

  plugin.start = function(options) {
    app.debug('Plugin démarré')
  }

  plugin.stop = function() {
    app.debug('Plugin arrêté')
  }

  return plugin
}
```

### Format INCORRECT (ancien)
```javascript
// ❌ Cette structure ne fonctionne PAS avec v2.25:
module.exports = function(app) {
  return {
    id: 'signalk-mon-plugin',
    name: 'Mon Plugin',
    start: function() { ... }
  }
}
```

---

## 🔴 LEÇON #4: Keywords OBLIGATOIRES dans package.json

### MINIMUM REQUIS
```json
{
  "name": "signalk-mon-plugin",
  "version": "1.0.0",
  "main": "index.js",
  "keywords": [
    "signalk-node-server-plugin",
    "signalk-plugin"
  ]
}
```

Sans le keyword **"signalk-node-server-plugin"**, Signal K ne le reconnaît pas.

---

## 🔴 LEÇON #5: Redémarrage Signal K Nécessaire

Après CHAQUE changement:
- Ajout plugin
- Modification settings.json
- Changement code plugin

**Redémarrer Signal K:**
```bash
sudo systemctl restart signalk
sleep 120  # Attendre 2 min pour démarrage complet
```

---

## 📋 CHECKLIST PLUGIN INSTALLATION

- [ ] Code avec structure `plugin.id = ...`
- [ ] `package.json` avec keyword "signalk-node-server-plugin"
- [ ] Copier dans `~/.signalk/node_modules/` (PAS npm link!)
- [ ] Config dans `~/.signalk/settings.json`
- [ ] Redémarrer Signal K (2 min attente)
- [ ] Vérifier découverte: `curl http://localhost:3000/skServer/plugins`
- [ ] **ACTIVER MANUELLEMENT via Admin UI**
- [ ] Tester données API: `curl http://localhost:3000/signalk/v1/api/...`

---

## 🚀 SUMMARY

**Les 3 PIÈGES MAJEURS avec Signal K v2.25:**

1. **npm link ne marche pas** → Copier directement
2. **Plugin installé ≠ Plugin running** → Activer via Admin UI
3. **Structure de code spécifique** → Utiliser `plugin.x = ...`

**Si un plugin ne marche pas, vérifier dans cet ordre:**
1. ✅ Est-ce qu'il est dans `node_modules/`? (PAS un symlink!)
2. ✅ Est-ce qu'il a les bons keywords?
3. ✅ Est-ce qu'il est activé dans Admin UI?
4. ✅ Signal K a-t-il été redémarré?
5. ✅ Les données existent-elles? (GPS/vent/etc.)

