[![English](https://img.shields.io/badge/Language-English-red)](README.md) [![Français](https://img.shields.io/badge/Langue-Fran%C3%A7ais-blue)](#)

# Flipr Local pour Home Assistant 🐬
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Adrien40/ha-flipr-local)](https://github.com/Adrien40/ha-flipr-local/releases)
[![Licence : GPL v3](https://img.shields.io/badge/Licence-GPLv3-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-flipr-local/tests.yaml?branch=main&label=tests)](https://github.com/Adrien40/ha-flipr-local/actions/workflows/tests.yaml)
[![Validate](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-flipr-local/validate.yaml?branch=main&label=hassfest%2Fhacs)](https://github.com/Adrien40/ha-flipr-local/actions/workflows/validate.yaml)
[![Linting](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-flipr-local/lint.yaml?branch=main&label=lint)](https://github.com/Adrien40/ha-flipr-local/actions/workflows/lint.yaml)
[![Typing](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-flipr-local/mypy.yaml?branch=main&label=mypy%20--strict)](https://github.com/Adrien40/ha-flipr-local/actions/workflows/mypy.yaml)
[![CodeQL](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-flipr-local/codeql.yaml?branch=main&label=codeql)](https://github.com/Adrien40/ha-flipr-local/actions/workflows/codeql.yaml)
[![Quality Scale](https://img.shields.io/badge/HA%20Quality%20Scale-Platinum-e5e4e2)](custom_components/flipr_local/quality_scale.yaml)

Si ce projet vous est utile, vous pouvez soutenir son développement 🙏

<a href="https://www.buymeacoffee.com/adrien40"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="160"></a>

---

## ⚡ En résumé
- 🔌 Fonctionnement 100 % local via Bluetooth (BLE)
- 🏠 Compatible Home Assistant (sans cloud)
- 🌡️ Mesures : pH, Redox, Température
- 🔋 Optimisé pour préserver la batterie
- ⚙️ Installation via HACS en 2 minutes

---

## 📸 Exemples dans Home Assistant

### 📊 Visualisation

<p align="center">
  <img src="https://raw.githubusercontent.com/Adrien40/ha-flipr-local/main/docs/screenshots/dashboard_overview.png" width="500">
</p>

<p align="center">
  <em>📊 Vue d’ensemble des données de la piscine dans Home Assistant</em>
</p>

---

### 🔍 Détails techniques

<p align="center">
  <img src="https://raw.githubusercontent.com/Adrien40/ha-flipr-local/main/docs/screenshots/entities_overview.png" width="248">
  <img src="https://raw.githubusercontent.com/Adrien40/ha-flipr-local/main/docs/screenshots/entities_configuration.png" width="248">
</p>

<p align="center">
  <em>🔍 Entités exposées par l’intégration & ⚙️ Options de Configuration avancées</em>
</p>

---

Une **intégration 100% locale pour Home Assistant** qui transforme votre analyseur Flipr en capteur Bluetooth Low Energy (BLE), afin de piloter et surveiller votre piscine sans aucune dépendance au Cloud. 🛡️

> ⚠️ **Avertissement** : Cette intégration interroge le Flipr directement en Bluetooth. Si vous utilisez la passerelle Wi-Fi officielle en parallèle, une gestion rigoureuse des modes de synchronisation est intégrée pour préserver la batterie.

### 💡 Pourquoi cette intégration ?
La société CTAC-TECH / Flipr étant en liquidation judiciaire, l'accès aux serveurs cloud est devenu incertain. **Flipr Local** est le fruit d'un travail de **Reverse Engineering** approfondi pour transformer votre analyseur en un véritable capteur industriel local, capable de communiquer directement avec votre instance Home Assistant.
Flipr Local permet de remplacer le cloud par une solution de **local control**, tout en offrant un système fiable de **pool monitoring** basé sur un **BLE sensor**.

---

### ✅ Compatibilité
* 🏷️ **Modèles supportés** : Flipr AnalysR (Toutes versions Bluetooth - avec ou sans abonnement).
* 🌐 **Usage flexible** : Compatible avec ou sans la Passerelle Wi-Fi Flipr Connect.
* 🏅 **Testé sur** : Validé sur **Flipr AnalysR 3** et **Flipr Start Max**.
* 🛠️ **Matériel requis** : Bluetooth interne, clé USB Bluetooth ou **Bluetooth Proxy ESPHome** (Fortement recommandé, [installation facile ici](https://esphome.github.io/bluetooth-proxies/)).
* 📶 **Qualité du signal** : Un signal **RSSI stable (idéalement supérieur à -75 dBm)** est indispensable pour garantir la connexion au Flipr. Les tests montrent qu'un signal inférieur à **-80 dBm** peut entraîner des échecs fréquents. 
* ⏱️ **Temps réel** : Une entité `sensor.*_signal_bluetooth`, utilisant l'écoute passive de Home Assistant, vous permet de surveiller la force du signal en temps réel sans vider la batterie de la sonde !

> ❌ **Non compatible** : Les versions fonctionnant uniquement via le réseau Sigfox ne sont pas supportées.

---

### ✨ Points forts
* 🏠 **100% Local (BLE)** : Aucune dépendance au Cloud, pas d'abonnement, pas de latence.
* 🌡️ **Remontée des capteurs bruts** : Température, pH, ORP (Redox), Batterie (%).
* 🚀 **Analyse en temps réel** : Lancez une mesure manuelle quand vous le souhaitez.
* 🔬 **Précision Scientifique** : Calcul du pH par l'équation de Nernst avec compensation de température.
* 🛜 **Sans Passerelle** : La passerelle n'est pas nécessaire, mais elle permet de conserver le Cloud sur l'application mobile officielle !
* 🧪 **Intelligence Chimique Avancée** :
  * Calcul de l'**Indice de Langelier** (ISL) pour déterminer si l'eau est équilibrée, entartrante ou corrosive.
  * **pH d'Équilibre** (Balance de Taylor) calculé depuis la Température, le TAC, le TH et le TDS.
* 🟤 **Traitement de l'Eau et Stabilisant (CyA)** : vous pouvez renseigner votre traitement (Chlore / Brome) et votre taux de stabilisant. Ces réglages sont conservés pour un usage futur — **aucune valeur calculée n'en dépend pour le moment**.
* ⚙️ **Configuration 100% UI** : Découverte automatique Bluetooth, Calibration des Sondes et réglage des Seuils d'Alerte directement depuis l'interface Home Assistant (aucun YAML requis).
* 🔄 **Modes de Synchronisation** : Contrôle du mode de synchronisation (Sommeil, Éco, Normal, Boost) pour les utilisateurs possédant la Passerelle Wi-Fi, afin d'éviter de vider la batterie.
* ⏱️ **Analyses planifiées sur des créneaux fixes** : réglez un **Intervalle d'Analyse** et une **Heure de Référence** ; les analyses tombent aux mêmes heures chaque jour au lieu de suivre un intervalle glissant (voir *Analyses planifiées* plus bas).
* 🌍 **Multi-langue** : Développé en Français 🇫🇷 et disponible en EN, ES, DE, IT, NL, PL, PT, PT-BR, SV, RU, ZH-HANS, ZH-HANT, CS, HU, EL, HR, DA, NB (Traduction via IA).
* 📡 Transforme votre Flipr en véritable **BLE sensor** pour Home Assistant.

---

### 🚀 Installation

#### Via HACS (Recommandé)
Ce dépôt n'étant pas (encore) dans la liste officielle par défaut, vous devez l'ajouter en tant que dépôt personnalisé.

1. Ouvrez **HACS** dans votre Home Assistant.
2. Cliquez sur les 3 petits points en haut à droite et sélectionnez **Dépôts personnalisés**.
3. Dans **Dépôt**, collez l'URL : `https://github.com/Adrien40/ha-flipr-local`
4. Dans **Type**, choisissez **Intégration** puis cliquez sur **Ajouter**.
5. Une fois ajouté, une fenêtre apparaît : cliquez sur **Télécharger** (sélectionnez la dernière version).
6. **Redémarrez complètement Home Assistant**.
7. Allez dans **Paramètres** > **Appareils et Services** > **Ajouter une intégration** et cherchez "Flipr Local".

### Manuelle
Copiez le dossier `custom_components/flipr_local` dans le dossier `custom_components` de votre configuration Home Assistant, puis redémarrez.

### 🗑️ Suppression
1. Allez dans **Paramètres** > **Appareils et services**, sélectionnez votre appareil Flipr, cliquez sur les 3 points et choisissez **Supprimer**. Cela supprime toutes les entités et interrompt la scrutation Bluetooth.
2. Si installé via HACS : ouvrez **HACS**, trouvez **Flipr Local**, cliquez sur les 3 points et sélectionnez **Supprimer**.
3. Si installé manuellement : supprimez le dossier `custom_components/flipr_local`, puis redémarrez Home Assistant.

Supprimer l'intégration efface également son historique local (dernières valeurs connues, points de référence de calibration). Si vous souhaitez simplement suspendre les mesures sans perdre ces données, désactivez plutôt l'interrupteur **Analyses Automatiques**.

---

### 🌐 Gestion de la Passerelle Wi-Fi (Flipr Connect)
L'intégration cohabite parfaitement avec votre installation officielle :

* **Sans Passerelle** : Home Assistant réveille le Flipr sur les créneaux définis par l'**Intervalle d'Analyse** et l'**Heure de Référence** (par défaut : toutes les 60 min, pile à l'heure).
* **Avec Passerelle** : Configurez le Flipr en **Mode Éco** (2 mesures/jour) ou **Mode Sommeil** (0 mesure/jour) via les options. La passerelle officielle assure le cloud, tandis que Home Assistant lit les données localement sans épuiser la batterie.

---

### ⏱️ Analyses planifiées (Intervalle d'Analyse & Heure de Référence)
Les analyses automatiques ne se déclenchent pas « toutes les N minutes après la précédente » : elles sont calées sur des **créneaux fixes**, ce qui donne des relevés à des heures prévisibles, quoi qu'il se soit passé avant (redémarrage, analyse manuelle, erreur).

| Réglage | Défaut | Plage | Rôle |
| :--- | :--- | :--- | :--- |
| 🔄 **Intervalle d'Analyse** | 60 min | 5 – 1440 min | Durée entre deux analyses planifiées. |
| 🕒 **Heure de Référence** | 08:00 | HH:MM | Heure sur laquelle les créneaux sont calés. |

* **Exemple** : avec un intervalle de **120 min** et une heure de référence de **08:00**, les analyses ont lieu à 08:00, 10:00, 12:00, 14:00… (et 06:00, 04:00… avant).
* **Où les modifier** : **Configurer** ⚙️ > section **⏱️ Synchronisation**, ou directement depuis les entités **Intervalle d'Analyse** et **Heure de Référence** de l'appareil (catégorie configuration), par exemple sur un tableau de bord.
* **Prise en compte immédiate** : la prochaine analyse est replanifiée dès que vous changez l'un des deux réglages.
* **Conseil** : choisissez un intervalle qui divise 24 h en parts égales (5, 10, 15, 20, 30, 60, 120, 180, 240, 360, 480, 720 ou 1440 min). Sinon les créneaux se décalent d'un jour à l'autre, car ils sont recalés chaque jour sur l'Heure de Référence.
* Un créneau situé à moins de 10 secondes est ignoré au profit du suivant.
* **Nouvelle Analyse** s'exécute immédiatement et ne modifie pas la planification.
* **Analyses Automatiques** désactivées : les analyses planifiées sont ignorées. Les réactiver ne lance **pas** d'analyse par elles-mêmes ; la suivante a lieu au prochain créneau (ou appuyez sur **Nouvelle Analyse**).

---

### 📊 Capteurs et Contrôles disponibles
| Entité | Unité / Type | Description |
| :--- | :--- | :--- |
| 💧 **pH** | pH | pH calculé (Nernst + compensation thermique). |
| ⚡ **ORP (Redox)** | mV | Potentiel d'oxydoréduction. |
| 🌡️ **Température** | °C | Température précise de l'eau. |
| ⚖️ **Indice de Langelier** | ISL | Indicateur d'équilibre de l'eau (Corrosive, Équilibrée ou Entartrante). |
| 🎯 **pH d'Équilibre** | pH | Cible du pH idéal calculé selon la Balance de Taylor. |
| 🔋 **Batterie** | % et mV | Niveau de charge (%) et tension brute de la pile. |
| 📶 **Signal Bluetooth** | dBm | Force du signal Bluetooth reçu en temps réel (RSSI). |
| 🔵 **État Bluetooth** | Statut | État détaillé de la connexion (Connecté, En veille, Erreur...). |
| 🔄 **Mode Synchro. Passerelle** | Diagnostic | Mode actuel de la sonde lu dans la trame Bluetooth (Éco, Boost...). |
| ⏱️ **Prochaine Analyse** | Horodatage | Heure estimée de la prochaine relève de données. |
| 🚀 **Nouvelle Analyse** | Bouton | **Lancer une analyse instantanée (~60s).** |
| ⏸️ **Analyses Automatiques** | Interrupteur | Activer/Désactiver la relève automatique (Mode Pause). |
| 🔄 **Intervalle d'Analyse** | Réglage (min) | Durée entre deux analyses planifiées (5 – 1440). |
| 🕒 **Heure de Référence** | Réglage (heure) | Heure sur laquelle les créneaux d'analyse sont calés (08:00 par défaut). |
| 🧪 **Traitement de l'Eau** | Réglage | Chlore ou Brome (enregistré, aucune valeur calculée n'en dépend pour l'instant). |
| 💧 **TAC / TH / TDS / CyA** | Réglages (mg/L, ppm) | Paramètres de l'eau utilisés pour l'indice de Langelier et le pH d'équilibre (le CyA est conservé pour un usage futur). |

> 🛠️ **Diagnostic** : L'intégration expose également des capteurs avancés (pH Brut en mV, Redox Brut en mV, pH Brut Usine d'origine, Trame Brute hexadécimale complète, et statuts d'alerte binaires). La plupart sont **désactivés par défaut** (ils font doublon avec une valeur calibrée) — activez-les depuis les paramètres de l'entité si besoin.

---

### 🧪 Expertise Chimique : Une analyse de niveau Professionnel

👉 Pas besoin de comprendre ces calculs : tout est automatisé dans Home Assistant.

<details>
<summary>🔬 Voir les détails scientifiques</summary>

#### 1. Pourquoi il n'y a pas de capteur de Chlore 🧂
Avant la 1.2.0, l'intégration affichait un *Chlore Libre Estimé* (ppm) et un *Chlore Actif – HOCl* (mg/L). Ils ont été **supprimés volontairement**, pour ces raisons :

* **Le Redox n'est pas une concentration.** La sonde mesure le pouvoir oxydant de l'eau. À quantité de chlore égale, la lecture varie avec le pH, la température, le stabilisant (CyA), les autres oxydants, et avec le vieillissement ou l'encrassement de la sonde. Transformer une valeur en mV en « x ppm » masque toutes ces inconnues.
* **La conversion pouvait afficher du chlore là où il n'y en a pas.** La formule était plafonnée à 415 mV : tout Redox en dessous donnait le même résultat. À pH 7,2 sans stabilisant, un Redox de **100 mV** (aucun oxydant) affichait quand même **0,1 ppm** de chlore libre et **0,07 mg/L** de HOCl.
* **Les corrections du stabilisant étaient empilées et jamais validées.** Le chlore libre était multiplié par CyA/40, puis le HOCl divisé à nouveau par un facteur CyA. Avec le même Redox (700 mV), le même pH (7,2) et la même température (25 °C), le HOCl passait de **0,66 mg/L** sans stabilisant à **0,02 mg/L** avec 40 mg/L : un écart de ×33 dû à un chiffre saisi à la main et qui évolue au fil de la saison. Aucune donnée de mesure dans ce dépôt ne justifie ces facteurs.
* **La documentation promettait plus que le code** (un modèle de « Machine Learning », un « modèle thermodynamique »), ce qui donnait une fausse impression de précision.
* **Le chlore est une mesure de sécurité.** Une valeur fausse mais qui a l'air précise est pire que pas de valeur.

**À utiliser à la place :** la valeur **ORP (Redox)** avec vos propres Seuils d'Alerte, le nouveau capteur de diagnostic **Redox Brut (mV)** pour calibrer la sonde sur une solution étalon, et un kit de test ou des bandelettes pour le taux de chlore réel.

#### 2. Équilibre de l'eau : Indice de Saturation de Langelier & Balance de Taylor ⚖️
L'Indice de Saturation de Langelier (ISL) est le complément indispensable de la **Balance de Taylor**. Il permet de vérifier si votre eau est :
* **Corrosive (ISL < -0.3)** : L'eau attaque vos joints, liner et métaux.
* **Équilibrée (ISL entre -0.3 et +0.3)** : L'eau parfaite.
* **Entartrante (ISL > +0.3)** : Risque de dépôts calcaires.

Renseignez votre TAC, TH et TDS dans les options, et Home Assistant calculera votre équilibre en direct selon la température lue par le Flipr !

> **Diagnostic** : L'intégration expose également le pH Brut (mV), le Redox Brut (mV), le pH Brut (Usine), la Trame Brute complète et l'horodatage de la Dernière Analyse. Les valeurs brutes et usine sont **désactivées par défaut** — activez-les depuis les paramètres de l'entité si besoin.

</details>

### 🎯 Note sur la précision des mesures
Les valeurs affichées dans Home Assistant peuvent différer légèrement de celles de l'application officielle Flipr.

Flipr Local permet une calibration « Haute Précision ». Contrairement à l'application mobile qui utilise des valeurs fixes, notre intégration vous permet de saisir la valeur exacte de votre solution tampon (pH 7.02, 4.01, etc.) ajustée à la température lors de votre calibration. C'est cette rigueur scientifique qui peut créer un léger décalage, signe d'une mesure plus proche de la réalité de votre bassin. 🔬

---

## 🚀 Configuration
> ⚠️ Nécessite **Home Assistant 2026.3.0 ou plus récent** (première version livrée avec Python 3.14). Testé sur 2026.3.0 et 2026.9.3.

1. Allez dans **Paramètres** > **Appareils et Services**.
2. L'intégration devrait détecter automatiquement votre Flipr si votre clé/antenne Bluetooth est à portée.
3. Cliquez sur **Ajouter une intégration** et recherchez **Flipr Local**.
4. Suivez les instructions à l'écran pour définir le Traitement de l'Eau (Chlore, Brome), le taux de Stabilisant et le calibrage de vos sondes.

### ⚙️ Options, Calibrations et Alertes
Une fois l'appareil ajouté, vous pouvez cliquer sur **Configurer** ⚙️ pour :
* Ajuster les valeurs de vos solutions de calibration (pH 4, pH 7, Redox).
* Modifier les paramètres de votre eau (TAC, TH, TDS, Stabilisant) via le tableau de bord.
* Régler l'**Intervalle d'Analyse** et l'**Heure de Référence** (section ⏱️ *Synchronisation*), voir *Analyses planifiées* plus haut.
* Définir vos **Seuils d'Alerte personnalisés** (pH Min/Max, ORP Min/Max, etc.) pour piloter vos propres automatisations.

> 📖 **Besoin d'aide pour calibrer vos sondes ?**
> Retrouvez la procédure pas à pas (méthode via l'application officielle ou en mV bruts, ajustement selon la température et Seuils d'Alerte) dans le **[Guide de Calibration](calibration_help.fr.md)**. Les notes de version sont dans le **[Journal des modifications](CHANGELOG.fr.md)**.

---

### 🐛 Dépannage

<details>
<summary>⚠️ Voir les problèmes fréquents</summary>
  
* **Erreurs Bluetooth fréquentes** : L'intégration gère automatiquement les tentatives de connexion. Si le capteur indique `Signal Perdu`, le Flipr est hors de portée. Rapprochez votre antenne ou [installez un Proxy Bluetooth ESPHome](https://esphome.github.io/bluetooth-proxies/) au plus près du bassin (nécessite juste un ESP32 (~10€) et un chargeur USB).
* **Les capteurs Chlore Libre / Actif ont disparu après la mise à jour 1.2.0** : c'est voulu (voir *Pourquoi il n'y a pas de capteur de chlore*). Les entités orphelines sont supprimées automatiquement ; retirez-les de vos tableaux de bord si besoin.
* **Je n'ai pas de stabilisant** : Réglez simplement l'entité `CyA (Stabilisant)` sur `0`. Elle n'a actuellement aucun effet sur les valeurs calculées.

</details>

---

### 🎯 Cas d'usage
* **Automatisation de la sécurité du bassin** : déclenchez une notification ou coupez la filtration si le pH ou le Redox sort de votre plage de sécurité grâce aux capteurs binaires `Statut pH` et `Statut ORP (Redox)`.
* **Protection contre le gel** : associez le capteur `Statut Température` à la mise en route forcée de la pompe ou d'un volet dès que l'eau approche de 0°C l'hiver.
* **Rappels de traitement chimique** : surveillez le capteur `Statut Indice de Langelier` pour être alerté dès que l'eau devient corrosive ou entartrante, avant d'endommager vos équipements.
* **Maintenance préventive de la batterie** : recevez une alerte de batterie faible bien avant l'arrêt complet de la sonde.

### 🤖 Exemples d'automatisations

<details>
<summary>📋 Notification en cas de pH anormal</summary>

```yaml
automation:
  - alias: "Piscine : pH hors plage"
    trigger:
      - platform: state
        entity_id: binary_sensor.flipr_ph_status
        to: "on"
    action:
      - action: notify.mobile_app_votre_telephone
        data:
          title: "⚠️ Alerte pH Piscine"
          message: "Le pH est actuellement à {{ states('sensor.flipr_ph') }}, en dehors des limites configurées."
```
</details>

<details>
<summary>📋 Alerte si la sonde ne répond plus</summary>

```yaml
automation:
  - alias: "Flipr inaccessible"
    trigger:
      - platform: event
        event_type: repairs_issue_registry_updated
        event_data:
          action: create
          domain: flipr_local
    action:
      - action: notify.mobile_app_votre_telephone
        data:
          title: "🔌 Flipr injoignable"
          message: "La sonde Flipr ne répond plus depuis un moment. Vérifiez la batterie et la portée Bluetooth."
```
</details>

### ⚠️ Limitations connues
* **Portée Bluetooth** : comme tout équipement BLE, le Flipr doit rester à portée d'un adaptateur Bluetooth ou d'un proxy ESPHome. Les abris fermés, les volets roulants, la distance et les structures métalliques peuvent affaiblir le signal.
* **Pas de notifications instantanées de la sonde** : les données sont relevées selon les créneaux planifiés (ou à la demande via le bouton « Nouvelle Analyse ») ; il ne s'agit pas d'un flux continu.
* **Le Redox n'est pas une mesure de concentration de chlore** : utilisez la valeur Redox avec vos propres seuils et un test manuel (bandelettes/photomètre) pour vérifier votre concentration réelle.
* **Une seule sonde par entrée de configuration** : si vous possédez plusieurs sondes Flipr, ajoutez chacune via une entrée dédiée.

---

### 🛠️ Sauvetage Matériel

<details>
<summary>🔧 Voir la procédure complète</summary>

Si les sondes de votre Flipr sont HS, vous pouvez les remplacer vous-même !

**Matériel requis :**
1. Des sondes de remplacement (pH et ORP) avec connecteur BNC (Dimensions recommandées : **12 mm de diamètre, 15-16 cm de long**).
2. Deux câbles adaptateurs (**Pigtails**) : `MMCX Mâle coudé (90°) vers BNC Femelle`. *Le connecteur coudé est indispensable pour pouvoir refermer le capot du Flipr.*

**Procédure rapide :**
Retirez les anciennes sondes, nettoyez la base blanche. Branchez les adaptateurs MMCX sur la carte mère (Ports `PH` et `ORP`). Passez les nouvelles sondes dans les trous d'origine (12 mm), connectez-les aux câbles BNC. Calibrez via Home Assistant, et c'est reparti !

</details>

---

### 🤝 Contributions & Support
Si vous possédez une version plus ancienne du Flipr (1 ou 2) et que l'intégration fonctionne chez vous, n'hésitez pas à l'indiquer !
Pour tout bug ou demande d'amélioration, merci d'ouvrir une [Issue](https://github.com/Adrien40/ha-flipr-local/issues) sur ce dépôt.

### ⚠️ Avertissement (Disclaimer)
Cette intégration est un projet indépendant. Elle n'a aucun lien, de près ou de loin, avec l'entreprise CTAC-TECH / Flipr. L'utilisation de ce logiciel se fait sous votre propre responsabilité.

### ⚖️ Licence
Projet sous licence **GPLv3**. Indépendant de la société Flipr. Utilisation sous votre entière responsabilité.

---

**Développé avec ❤️ par @Adrien40**

<a href="https://www.buymeacoffee.com/adrien40"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="180"></a>