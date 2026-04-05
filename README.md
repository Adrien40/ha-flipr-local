# Flipr Local pour Home Assistant 🐬
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Adrien40/ha-flipr-local)](https://github.com/Adrien40/ha-flipr-local/releases)

<a href="https://www.buymeacoffee.com/adrien40"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="200"></a>

---

<p align="center">
  <img src="https://raw.githubusercontent.com/Adrien40/ha-flipr-local/main/icon.png" width="150" alt="Flipr Local Logo">
</p>

Prenez le contrôle total de votre analyseur de piscine **Flipr AnalysR** sans dépendre du cloud ! Cette intégration permet une lecture directe des données via **Bluetooth Low Energy (BLE)** pour une domotique 100% locale, rapide et privée.

### 💡 Pourquoi cette intégration ?
La société CTAC-TECH / Flipr est actuellement en liquidation judiciaire. Que l'activité soit reprise ou non, il est devenu essentiel de pouvoir continuer à utiliser nos sondes de manière totalement autonome en Bluetooth, sans dépendre de serveurs qui pourraient devenir inaccessibles.

---

### ✅ Compatibilité
* **Modèles supportés** : Flipr AnalysR (acheté avec ou sans abonnement).
* **Versions** : Compatible avec les versions Start et Max.
* **Testé sur** : À ce jour, l'intégration n'a été validée que sur le **Flipr AnalysR 3**.

> ❌ **Non compatible** : Les versions fonctionnant uniquement via le réseau Sigfox ne sont pas supportées.

### ✨ Points forts
* **100% Local** : Pas de compte cloud, pas d'abonnement, pas de latence.
* **Précision Scientifique** : Calcul du pH par l'équation de Nernst avec compensation de température en temps réel.
* **Calibration simple en local** : Ajustez les valeurs brutes (mV) de votre sonde directement via l'interface de configuration.
* **Compatible Bluetooth Proxy** : Fonctionne avec les proxys Bluetooth ESPHome pour couvrir toute la piscine.

---

### 🚀 Installation

#### Via HACS
Ce dépôt n'étant pas (encore) dans la liste officielle par défaut, vous devez l'ajouter en tant que dépôt personnalisé.

1. Ouvrez **HACS** dans votre Home Assistant.
2. Cliquez sur les 3 petits points en haut à droite et sélectionnez **Dépôts personnalisés**.
3. Dans **Dépôt**, collez l'URL : `https://github.com/Adrien40/ha-flipr-local`
4. Dans **Type**, choisissez **Intégration** puis cliquez sur **Ajouter**.
5. Une fois ajouté, une fenêtre apparaît : cliquez sur **Télécharger** (sélectionnez la dernière version).
6. **Redémarrez complètement Home Assistant**.
7. Allez dans **Paramètres** > **Appareils et Services** > **Ajouter une intégration** et cherchez "Flipr Local".

### 📊 Capteurs disponibles
| Capteur | Unité | Description |
| :--- | :--- | :--- |
| **Température** | °C | Température de l'eau. |
| **pH** | pH | pH calculé selon votre étalonnage. |
| **Redox** | mV | Potentiel d'oxydoréduction (ORP). |
| **Chlore Actif** | mg/L | Estimation de la fraction de chlore réellement désinfectante (compensée par le pH). |
| **Indice de Langelier** | ISL | Indicateur d'équilibre de l'eau (Corrosive, Équilibrée ou Entartrante). |
| **Batterie** | mV | Tension de la batterie interne. |

### 🧪 Expertise Chimique : Une analyse de niveau professionnel

Contrairement aux applications classiques qui se contentent de vous donner des valeurs brutes, **Flipr Local** intègre des algorithmes avancés de chimie de l'eau pour vous donner la véritable "santé" de votre bassin en temps réel.

#### 1. Le Chlore Actif (Le vrai pouvoir désinfectant)
La sonde Redox (ORP) ne mesure pas la quantité de chlore (mg/L), mais la **puissance de désinfection** de l'eau. Le problème ? Cette puissance s'effondre quand le pH augmente. 
* À pH 7.0, environ 75% de votre chlore est actif.
* À pH 7.5, il n'en reste plus que 50%.
Mon intégration utilise la constante de dissociation chimique (pKa) pour croiser en temps réel votre Redox et votre pH. Le capteur **Chlore Actif** vous indique la fraction de chlore qui désinfecte *réellement* votre bassin. Fini les calculs approximatifs !

#### 2. L'Indice de Saturation de Langelier (ISL)
C'est le Saint Graal de l'équilibre de l'eau. Une eau désinfectée c'est bien, mais une eau équilibrée, c'est mieux ! L'ISL permet de savoir si votre eau est :
* **Corrosive (ISL < -0.3)** : L'eau a "faim" et va attaquer vos joints, votre liner et les métaux.
* **Équilibrée (ISL entre -0.3 et +0.3)** : L'eau parfaite.
* **Entartrante (ISL > +0.3)** : L'eau est saturée, le calcaire va se déposer sur vos parois et dans vos tuyaux.

**La force de Flipr Local :** Le calcul de l'ISL dépend fortement de la **Température**. Dans un bassin (surtout sous abri), l'eau chauffe vite, ce qui modifie violemment l'équilibre. 
Saisissez simplement votre TAC (Alcalinité), TH (Dureté) et TDS (Solides dissous) mesurés aux bandelettes (par exemple) dans les options de l'intégration, et **Home Assistant calculera votre ISL en direct** en fonction de la température de l'eau lue par le Flipr !

> **Diagnostic** : L'intégration expose également le pH brut (mV), le pH calculé par la formule d'usine, la trame hexadécimale complète et l'horodatage de la dernière mesure.

### ⚙️ Calibration
Utilisez le bouton **Configurer** (roue crantée) sur la carte de l'intégration pour renseigner vos valeurs :
* **pH 7** : ~1600 mV
* **pH 4** : ~1900 mV

### 🤝 Contributions & Support
Si vous possédez une version plus ancienne du Flipr (1 ou 2) et que l'intégration fonctionne chez vous, n'hésitez pas à l'indiquer !
Pour tout bug ou demande d'amélioration, merci d'ouvrir une [Issue](https://github.com/Adrien40/ha-flipr-local/issues) sur ce dépôt.

### ⚠️ Avertissement (Disclaimer)
Cette intégration est un projet indépendant. Elle n'a aucun lien, de près ou de loin, avec l'entreprise CTAC-TECH / Flipr. L'utilisation de ce logiciel se fait sous votre propre responsabilité.

### ⚖️ Licence
Ce projet est sous licence **GPLv3**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

<a href="https://www.buymeacoffee.com/adrien40"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="200"></a>

---
**Développé avec passion par @Adrien40**
