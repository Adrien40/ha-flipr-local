[![English](https://img.shields.io/badge/Language-English-red)](#) [![Français](https://img.shields.io/badge/Langue-Fran%C3%A7ais-blue)](#)

# Flipr Local pour Home Assistant 🐬
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Adrien40/ha-flipr-local)](https://github.com/Adrien40/ha-flipr-local/releases)

Si ce projet vous est utile, vous pouvez soutenir son développement 🙏

<a href="https://www.buymeacoffee.com/adrien40"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="160"></a>

---

## ⚡ En résumé
- 🔌 Fonctionnement 100 % local via Bluetooth (BLE)
- 🏠 Compatible Home Assistant (sans cloud)
- 🌡️ Mesures : pH, Redox, Chlore Actif, Température
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
* 🌐 **Usage flexible** : Compatible avec ou sans la passerelle Wi-Fi Flipr Connect.
* 🏅 **Testé sur** : Validé sur **Flipr AnalysR 3**.
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
  * **Chlore Libre Estimé (FC)** calculé via le modèle de Nernst (ORP + pH).
  * **Chlore Actif (HOCl)** calculé via le modèle thermodynamique (O'Brien / USEPA) prenant en compte la température et le stabilisant (CYA).
* 🟤 **Support Multi-Traitements** : Prise en charge du **Brome** (désactive intelligemment les capteurs spécifiques au chlore) et des piscines sans stabilisant (CYA = 0).
* ⚙️ **Configuration 100% UI** : Découverte automatique Bluetooth, calibrage des sondes et réglage des seuils d'alerte directement depuis l'interface Home Assistant (aucun YAML requis).
* 🔄 **Modes de Synchronisation** : Contrôle du mode de synchronisation (Sommeil, Éco, Normal, Boost) pour les utilisateurs possédant la passerelle Wi-Fi, afin d'éviter de vider la batterie.
* 🌍 **Multi-langue** : Développé en Français 🇫🇷 et disponible en EN, ES, DE, IT, NL, PL, PT, PT-BR, SV, RU, ZH-HANS, ZH-HANT, CS, HU, EL, HR, DA, NB (Traduction via IA).
* 📡 Transforme votre Flipr en véritable **BLE sensor** pour Home Assistant

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

---

### 🌐 Gestion de la Passerelle Wi-Fi (Flipr Connect)
L'intégration cohabite parfaitement avec votre installation officielle :

* **SANS Passerelle** : Home Assistant réveille le Flipr selon l'intervalle que vous avez choisi (par défaut : toutes les 60 min).
* **AVEC Passerelle** : Configurez le Flipr en **Mode Éco** (2 mesures/jour) ou Sommeil (0 mesure/jour) via les options. La passerelle officielle assure le cloud, tandis que Home Assistant lit les données localement sans épuiser la batterie.

---

### 📊 Capteurs et Contrôles disponibles
| Entité | Unité / Type | Description |
| :--- | :--- | :--- |
| 💧 **pH** | pH | pH calculé (Nernst + Compensation thermique). |
| ⚡ **Redox / ORP** | mV | Potentiel d'oxydoréduction. |
| 🌡️ **Température** | °C | Température précise de l'eau. |
| 🌫️ **Chlore Libre Estimé** | ppm | Estimation du taux de Chlore Libre (FC). |
| 🧪 **Chlore Actif** | mg/L | Estimation de la puissance réelle de désinfection (HOCl). |
| ⚖️ **Indice de Langelier** | ISL | Indicateur d'équilibre de l'eau (Corrosive, Équilibrée ou Entartrante). |
| 🎯 **pH d'Équilibre** | pH | Cible du pH idéal calculé selon la Balance de Taylor. |
| 🔋 **Batterie** | % et mV | Niveau de charge (%) et tension brute de la pile. |
| 📶 **Signal RSSI** | dBm | Force du signal Bluetooth reçu en temps réel. |
| 🔵 **État Bluetooth** | Statut | État détaillé de la connexion (Connecté, En veille, Erreur...). |
| 🔄 **Mode Sync** | Diagnostic | Mode actuel de la sonde lu dans la trame Bluetooth (Éco, Boost...). |
| ⏱️ **Prochaine Analyse** | Horodatage | Heure estimée de la prochaine relève de données. |
| 🚀 **Nouvelle Analyse** | Bouton | **Lancer une analyse instantanée (~60s).** |
| ⏸️ **Analyses Auto.** | Interrupteur | Activer/Désactiver la relève automatique (Mode Pause). |

> 🛠️ **Diagnostic** : L'intégration expose également des capteurs avancés (pH brut en mV, pH formule usine d'origine, trame hexadécimale brute complète, et statuts d'alertes binaires).

---

### 🧪 Expertise Chimique : Une analyse de niveau Professionnel

👉 Pas besoin de comprendre ces calculs : tout est automatisé dans Home Assistant.

<details>
<summary>🔬 Voir les détails scientifiques</summary>

#### 1. Le Chlore Actif (Le vrai pouvoir désinfectant) 🧂
La sonde Redox (ORP) ne mesure pas la quantité de chlore (mg/L), mais la **force de désinfection** de l'eau. Cette puissance s'effondre quand le pH augmente. Flipr Local croise votre Redox et votre pH en temps réel pour vous donner une estimation du taux de **Chlore Actif**, le seul vrai indicateur pour savoir si votre eau est désinfectante.

#### 2. Équilibre de l'eau : Indice de Saturation de Langelier & Balance de Taylor ⚖️
L'Indice de Saturation de Langelier (ISL) est le complément indispensable de la **Balance de Taylor**. Il permet de vérifier si votre eau est :
* **Corrosive (ISL < -0.3)** : L'eau attaque vos joints, liner et métaux.
* **Équilibrée (ISL entre -0.3 et +0.3)** : L'eau parfaite.
* **Entartrante (ISL > +0.3)** : Risque de dépôts calcaires.

Renseignez votre TAC, TH et TDS dans les options, et Home Assistant calculera votre équilibre en direct selon la température lue par le Flipr !

> **Diagnostic** : L'intégration expose également le pH brut (mV), le pH calculé par la formule d'usine, la trame hexadécimale complète et l'horodatage de la dernière mesure.

</details>


### 🎯 Note sur la précision des mesures
Les valeurs affichées dans Home Assistant peuvent différer légèrement de celles de l'application officielle Flipr.

Flipr Local permet une calibration "haute précision". Contrairement à l'application mobile qui utilise des valeurs fixes, notre intégration vous permet de saisir la valeur exacte de votre solution tampon (pH 7.02, 4.01, etc.) ajustée à la température lors de votre calibration. C'est cette rigueur scientifique qui peut créer un léger décalage, signe d'une mesure plus proche de la réalité de votre bassin. 🔬

---

## 🚀 Configuration
1. Allez dans **Paramètres** > **Appareils et services**.
2. L'intégration devrait détecter automatiquement votre Flipr si votre clé/antenne Bluetooth est à portée.
2. Cliquez sur **Ajouter une intégration** et recherchez **Flipr Local**.
3. Suivez les instructions à l'écran pour définir le type de traitement (Chlore, Brome) et le calibrage/décalage de vos sondes.

### ⚙️ Options, Calibrations et Alertes
Une fois l'appareil ajouté, vous pouvez cliquer sur **Configurer** ⚙️ pour :
* Ajuster les valeurs de vos solutions de calibration (pH 4, pH 7, Redox).
* Modifier les paramètres de votre eau (TAC, TH, TDS, Stabilisant) via le tableau de bord.
* Définir vos **seuils d'alerte personnalisés** (pH Min/Max, ORP Min/Max, etc.) pour piloter vos propres automatisations.

---

### 🐛 Dépannage

<details>
<summary>⚠️ Voir les problèmes fréquents</summary>
  
* **Erreurs Bluetooth fréquentes** : L'intégration gère automatiquement les tentatives de connexion. Si le capteur indique `Signal Perdu`, le Flipr est hors de portée. Rapprochez votre antenne ou [installez un Proxy Bluetooth ESPHome](https://esphome.github.io/bluetooth-proxies/) au plus près du bassin (nécessite juste un ESP32 (~10€) et un chargeur USB).
* **Chlore Libre et Actif en "Inconnu"** : Si vous avez sélectionné "Brome" dans les options, c'est le comportement normal. Le brome ne se calcule pas comme le chlore. Fiez-vous à la valeur de la sonde Redox (ORP).
* **Je n'ai pas de stabilisant** : Réglez simplement l'entité `CyA (Stabilisant)` sur `0`. Le calcul chimique s'adaptera automatiquement.

</details>

---

### 🛠️ Sauvetage Matériel :

<details>
<summary>🔧 Voir la procédure complète</summary>

Si les sondes de votre Flipr sont HS, vous pouvez les remplacer vous-même !

**Matériel requis :**
1. Des sondes de remplacement (pH et ORP) avec connecteur BNC (Dimensions recommandées : **12 mm de diamètre, 15-16 cm de long**).
2. Deux câbles adaptateurs (**Pigtails**) : `MCX Mâle coudé (90°) vers BNC Femelle`. *Le connecteur coudé est indispensable pour pouvoir refermer le capot du Flipr.*

**Procédure rapide :**
Retirez les anciennes sondes, nettoyez la base blanche. Branchez les adaptateurs MCX sur la carte mère (Ports `PH` et `ORP`). Passez les nouvelles sondes dans les trous d'origine (12 mm), connectez-les aux câbles BNC. Calibrez via Home Assistant, et c'est reparti !

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

<!-- Keywords: Home Assistant custom integration, BLE sensor, pool monitoring, local control -->
