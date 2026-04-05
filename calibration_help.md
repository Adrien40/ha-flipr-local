# 🎛️ Guide de Calibration - Flipr Local

Ce document explique comment configurer et affiner la calibration de votre sonde Flipr directement depuis l'interface de Home Assistant.

---

## 1. Comprendre les options de calibration

L'intégration **Flipr Local** est conçue pour être flexible et s'adapter à votre niveau d'aisance technique. Dans la fenêtre de Configuration (icône roue crantée), vous avez le choix entre deux méthodes pour les champs **Valeur pH 7** et **Valeur pH 4** :

### Méthode A : Les valeurs de l'application officielle (Recommandé)
Si vous n'avez pas vos données brutes, ouvrez simplement l'application officielle Flipr, allez dans **Menu > Mode Expert > Vue Expert** et relevez les valeurs de pH affichées (ex: `8.49` et `5.92`). Saisissez ces valeurs directement avec un point dans Home Assistant. L'intégration fera la conversion mathématique en arrière-plan.

### Méthode B : Les valeurs brutes en millivolts (Avancé)
Si vous avez "sniffé" vos trames Bluetooth ou que vous possédez vos valeurs d'usine exactes en mV (ex: `1600` et `1900`), vous pouvez les saisir directement. L'intégration comprendra automatiquement qu'il s'agit de millivolts (toute valeur supérieure à 20 est considérée comme des mV).

---

## 2. Ajuster la "Cible" de la solution (Température)

La chimie de l'eau est sensible à la chaleur. Dans un bassin protégé par un abri de piscine, l'eau chauffe vite, et cette règle s'applique aussi à vos solutions de calibration ! 

Le pH d'une solution tampon varie légèrement en fonction de sa température au moment où vous trempez la sonde.
* Regardez au dos de votre sachet/liquide de calibration (par exemple, pour le pH 7.00).
* Vous y verrez un tableau indiquant la valeur exacte selon la température de la pièce/du liquide.
* **Exemple :** À 20°C, une solution pH 7 vaut en réalité **7.02**. 

C'est cette valeur précise que vous devez saisir dans les champs **Cible de la solution**.

---

## 3. Configurer les seuils d'alerte

L'intégration crée automatiquement des capteurs de statut (Statut pH, Statut Chlore, Statut Température). Vous pouvez définir vos propres limites dans la configuration :
* **pH Min / Max :** (Défaut : 6.9 - 7.2)
* **Redox Min :** (Défaut : 650 mV)
* **Température Max :** Pratique pour éviter que l'eau ne tourne si elle chauffe trop (Défaut : 32°C).

Si l'une des sondes dépasse ces seuils, le capteur passera à l'état "Problème", ce qui est idéal pour déclencher vos automatisations.
