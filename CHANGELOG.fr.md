# Flipr Local - Journal des modifications

## 1.2.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

Cette version apporte des analyses planifiées sur des créneaux fixes, un capteur de diagnostic **Redox Brut** et des fondations bien plus solides : typage strict, code modulaire et une suite de plus de 450 tests.

Elle retire aussi les capteurs de chlore estimé, qui ne pouvaient pas être rendus fiables. Voir les changements majeurs ci-dessous.

### 🚨 Changements majeurs
- **Home Assistant 2026.3.0 ou plus récent** (`hacs.json`), première version livrée avec Python 3.14.
- Capteurs **Chlore Libre Estimé** et **Chlore Actif (HOCl)** :
  - Le Redox (mV) mesure un pouvoir oxydant global et non une concentration (ppm) ; la formule tronquait à 415 mV et affichait du chlore inexistant sous ce seuil.
  - Les facteurs de correction du stabilisant (CyA) étaient arbitraires et non documentés.
  - Utilisez la valeur Redox avec vos **Seuils d'Alerte** et un kit d'analyse physique pour le chlore réel.

### ✨ Nouveautés
- Capteur de diagnostic **Redox Brut (mV)** pour calibrer la sonde sur solution étalon avant application du décalage.
- Analyses planifiées calées sur des créneaux fixes (**Intervalle d'Analyse** + **Heure de Référence**) au lieu d'un intervalle glissant.
- Entité **Heure de Référence** (08:00 par défaut) et révision de l'**Intervalle d'Analyse**, également configurables dans la nouvelle section **Synchronisation** des options.
- Fiche appareil (`DeviceInfo`) enrichie : connexion Bluetooth MAC et numéro de série extrait du nom d'annonce (ex. `F3A12BC` ou MAC en repli).
- Nettoyage automatique des deux entités de chlore retirées lors de la migration (1.1 → 1.2), pour qu'elles ne restent pas *indisponibles* indéfiniment.

### 🚀 Améliorations
- Capteurs de diagnostic désactivés par défaut : **pH Brut (mV)**, **Redox Brut (mV)**, **pH Brut (Usine)**, **Batterie (Tension)** (mV) et **Trame Brute** (réactivables manuellement).
- Capteur de signal (**Signal Bluetooth** / RSSI) : bascule à l'état *Indisponible* dès la perte de portée au lieu de conserver sa dernière valeur.
- Bouton **Nouvelle Analyse** : tente la connexion même sans annonce récente et consomme immédiatement l'ordre.
- Qualité du code : passage en typage strict (`mypy --strict`) et couverture de tests > 95 %.
- La réactivation des **Analyses Automatiques** ne force plus d'analyse immédiate : la suivante a lieu au prochain créneau planifié (utilisez **Nouvelle Analyse** pour mesurer tout de suite).

### 🐛 Corrections
- Ajout d'un délai d'attente de 10 s (`TIMEOUT_GATT_OP`) sur `start_notify`, `stop_notify`, `disconnect` et la lecture Start Max.
- Gestion du débordement de la file de notifications BLE déplacée pour intercepter correctement `QueueFull`.
- Correction de la boucle infinie sur trame invalide (le compteur d'essais n'est plus réinitialisé prématurément).
- Maintien du taux de CyA lors de la modification d'autres options.
- Déchargement complet du coordinateur (`async_shutdown`) pour libérer les tâches d'arrière-plan.
- Traduction des erreurs de calibration et suppression de clés dupliquées (`nl.json`, `pt-br.json`).
- Gestion des valeurs non numériques dans `validate_calibration`.
- Les données restaurées au démarrage ne réinjectent plus d'anciennes valeurs de chlore.
- Réinitialisation de l'état `is_connected` entre les cycles dans les tests unitaires BLE.

### 🛡️ Renforcement
- Repli sur la calibration d'usine si la calibration pH est dégénérée (pente nulle).
- pH hors de la plage 0–14 marqué comme *Inconnu*.
- Rejet des valeurs NaN et infinies sur l'**Indice de Langelier** et le **pH d'Équilibre**.

### 🧰 Maintenance
- Découpage modulaire : `coordinator.py`, `frame.py`, `model.py`, `validation.py`, `chemistry.py`.
- Suite de tests réécrite (> 450 tests unitaires et basés sur les propriétés).
- Intégration continue : validation pytest, couverture et linter Ruff sous Python 3.14.

### 📚 Documentation
- `README.md` / `README.fr.md` : retrait du chlore, **Redox Brut**, cas d'usage et limitations synchronisés.
- `calibration_help.md` / `calibration_help.fr.md` : guide bilingue, calibration Redox et activation des capteurs de diagnostic.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.1.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ Nouveautés
- Prise en charge du modèle Flipr Start Max.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.0.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ Nouveautés
- Première version stable officielle de l'intégration.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬
