# Blue Connect Local - Journal des modifications

## 1.2.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

Cette version est entièrement consacrée à la robustesse : les problèmes de tentatives Bluetooth, de déchargement et de ré-authentification sont corrigés, un capteur de diagnostic **Redox Brut** rejoint le pH brut, et la suite de tests passe de 40 à ~400 tests.

### 🚨 Changements majeurs
- **Home Assistant 2026.3.0 ou plus récent** (`hacs.json`), première version livrée avec Python 3.14. Les tests passent sur 2026.3.0 et 2026.9.4.

### ✨ Nouveautés
- Capteur de diagnostic **Redox Brut** (mV), à côté du pH brut existant : la valeur de la sonde
  *avant* tout décalage, pour calibrer sur une solution étalon.

### 🧂 À propos du chlore
- Pas d'estimation du chlore, volontairement : l'ORP est un pouvoir oxydant, pas une concentration, donc une valeur de chlore qui en serait dérivée paraîtrait précise mais serait fausse. L'entité **CyA** et le **type de traitement** sont conservés, mais aucune valeur calculée n'en dépend pour l'instant.

### 🐛 Corrections
- **La ré-authentification et la reconfiguration ignoraient le nouveau code d'accès** : les options (prioritaires) et une copie dans le stockage local gardaient l'ancien, donc la notification de réparation revenait. Le nouveau code est désormais utilisé, n'est plus enregistré dans le stockage local, et la ré-authentification valide son format (9 caractères alphanumériques).
- Les entités **Intervalle d'Analyse** et **CyA (Stabilisant)** continuaient d'afficher leur ancienne valeur après une modification dans **Configurer**, alors que la nouvelle valeur était déjà utilisée ; elles suivent maintenant la valeur réellement utilisée.
- Des trames BLE invalides étaient relancées indéfiniment : le compteur de tentatives était remis à zéro avant le décodage, donc l'état « injoignable » n'était jamais atteint.
- Arrêt du coordinateur : `async_shutdown` appelle maintenant l'implémentation parente et est idempotent, et le minuteur de la première analyse (2 s après le démarrage) est annulé au déchargement.
- `validate_calibration` ne plante plus sur une valeur non numérique (ORP, décalage, CyA ou intervalle).
- Une calibration pH dégénérée (points trop proches) ne renvoie plus silencieusement une valeur fausse : le pH retombe sur le pH brut avec un avertissement journalisé.
- Un appareil vu uniquement par un scanner qui ne peut pas s'y connecter (`connectable=False`) n'est plus considéré comme absent.
- Le bouton **Nouvelle Analyse** gère proprement toute erreur inattendue au lieu de laisser une trace non gérée dans la tâche d'arrière-plan.
- Les notifications abandonnées (file pleine) et les événements de signal BLE perdu/retrouvé sont maintenant journalisés au niveau debug.

### 🛡️ Renforcement
- Un pH calculé hors de 0–14 devient *inconnu* au lieu d'être affiché.
- L'indice de Langelier et le pH d'équilibre refusent NaN et l'infini.

### 🧰 Maintenance
- Le coordinateur reçoit son `config_entry` explicitement ; les pauses BLE sont des constantes nommées ; une fonction de compatibilité remplace `device_registry.async_get_device` (obsolète), pour fonctionner sur 2026.3.0 comme sur 2026.9.4.
- Suite de tests passée de 40 à ~400 tests, avec 100 % de couverture : Bluetooth simulé, coordinateur, config/options flow, chaîne de migration 1.1 → 1.4, entités, cohérence des traductions, tests par propriétés.
- CI : workflow pytest + couverture (Python 3.14, 95 % minimum), `mypy --strict` dans son propre workflow *Typing*, configuration explicite de ruff / pytest dans `pyproject.toml`, `requirements_test.txt`.
- Style (ruff) et syntaxe Python 3.14 : `TimeoutError`, `except A, B:`.
- Le manifest déclare l'échelle de qualité `platinum`, avec des tests qui la gardent cohérente.

### 📚 Documentation
- `README.md` / `README.fr.md` : version minimale de Home Assistant, Redox brut, nouvelle section *Analyses planifiées*, entités manquantes dans le tableau, et badges de licence / CI / échelle de qualité.
- `calibration_help.md` / `calibration_help.fr.md` : vraie version anglaise du guide, liens entre les langues et lien depuis le README.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.1.1

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ Nouveautés
- **Détection instantanée d'un code d'accès invalide** : l'état d'authentification est lu directement sur la sonde, donc *Code d'accès invalide* est signalé en quelques secondes au lieu d'attendre le délai d'environ 2×60 s (avec une relecture de confirmation à 0,5 s pour éviter les faux positifs sur les proxys BLE à forte latence). Nouvel état `auth_failed` sur le capteur État Bluetooth.
- **Blue Connect Silver** : les entités Conductivité/Salinité sont désactivées automatiquement (une seule fois) dès que le modèle Silver est détecté, au lieu de rester actives avec la valeur *Inconnu*.
- Détection du modèle dès la découverte Bluetooth : la conductivité détectée pendant la découverte est conservée, donc les entités Conductivité/Salinité ont le bon état activé par défaut dès leur création.

### 🐛 Corrections
- Modifier un code d'accès existant dans le menu Options (par exemple pour corriger une faute de frappe) déclenche maintenant une analyse immédiate ; avant, seul le passage d'un champ vide à un code le faisait.
- L'ancien `hw_version` est explicitement supprimé du registre des appareils lors de la mise à jour depuis la 1.1.0, ce qui retire la ligne redondante « Hardware: WA000100 » de la page de l'appareil.

### 🧰 Maintenance
- Registre des appareils : le SKU est maintenant exposé comme `model_id` (*ID du modèle*) au lieu de `hw_version` ; le capteur de diagnostic `sw_version`, qui rapportait l'ID Cloud de l'appareil et non une version de firmware, est renommé `cloud_id` (une migration du registre conserve l'historique des entités).
- Les entités orphelines *Numéro de série* / *Modèle (SKU)* (déjà intégrées à l'en-tête de l'appareil en 1.1.0) sont nettoyées du registre des entités (migration de l'entrée 2 → 4).
- Chaînes anglaises harmonisées au singulier (*Automatic Analysis*, *Analysis paused*).
- Suppression de 3 constantes inutilisées et d'un import inutile.

### 🙏 Remerciements
- Merci à @alexdelprete pour son aide, ses suggestions et ses tests.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.1.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ Nouveautés
- Détection automatique du modèle (Blue Connect **Gold** ou **Silver**) : en mode actif via le SKU matériel et en mode entièrement passif en analysant la trame BLE. Le modèle détecté s'affiche dès l'écran de configuration, à la découverte Bluetooth.
- Les entités Conductivité et Salinité sont désactivées par défaut sur Blue Connect Silver.
- Informations enrichies dans l'en-tête de l'appareil : modèle détecté, numéro de modèle (SKU), numéro de série et adresse MAC Bluetooth.

### 🐛 Corrections
- Le numéro de série et le SKU restaurés depuis le stockage local sont injectés dès la création des entités, sans attendre la première lecture BLE.
- Le marqueur matériel `0xFFFF` est maintenant pris en compte au décodage des trames, ce qui supprime les valeurs de salinité erronées sur les appareils sans sonde de conductivité.

### 🧰 Maintenance
- Extraction centralisée de la trame BLE brute (`extract_raw_payload`), suppression des capteurs redondants *Modèle (SKU)* et *Numéro de série* et du code mort, et renforcement des tests unitaires.

### 📋 Notes de mise à jour
- Après la mise à jour depuis la 1.0.3, les anciens capteurs *Modèle (SKU)* et *Numéro de série* apparaissent comme indisponibles : ouvrez l'entité > icône engrenage > **Supprimer** (la 1.1.1 les nettoie automatiquement).
- Blue Connect Silver : une entité Conductivité déjà active reste visible avec la valeur *Inconnu* ; désactivez-la ou masquez-la dans **Paramètres** > **Appareils et services** > **Entités** (la 1.1.1 le fait automatiquement).

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.0.3

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ Nouveautés
- Détection automatique du **Blue Connect Silver**, à partir du préfixe de nom BLE `BC3-QX25001952`.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.0.2

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### 🐛 Corrections
- Correctif : le numéro de version de `manifest.json` avait été oublié en 1.0.1 ; HACS et Home Assistant affichent maintenant la bonne version. Aucun autre changement de code.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.0.1

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### 🧰 Maintenance
- Version « sous le capot », sans nouveauté visible.
- Refactorisation de l'architecture : la logique pure est extraite du coordinateur vers des modules dédiés (`protocol.py`, `model.py`, `validation.py`).
- Ajout d'une suite pytest sans dépendance à Home Assistant : chimie de l'eau (LSI, pH d'équilibre), décodage des trames BLE (18 et 19 octets) et validation du config flow.
- CI : un workflow GitHub Actions (`tests.yaml`) lance les tests à chaque modification.
- Suppression du code mort (conditions inatteignables) dans la validation de calibration.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

## 1.0.0

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬

### ✨ Nouveautés
- Première version stable.

🐬🐬🐬🐬🐬🐬🐬🐬🐬🐬
