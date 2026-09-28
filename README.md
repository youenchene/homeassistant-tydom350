# Delta Dore TYDOM 350 — Home Assistant

Intégration locale pour l'ancien **TYDOM 350 PC**, vérifiée avec son interface HTML française et Home Assistant 2026.9.3. Ce boîtier utilise des pages `.shtml` et des commandes CGI, contrairement aux passerelles Tydom modernes utilisant WebSocket.

## Fonctions

- **Lumières** : entités `light`, commandes allumer/éteindre. Aucun retour physique n'est exposé par la page observée. État inconnu au démarrage, puis **estimé d'après la dernière commande Home Assistant**. Les actions murales ne sont pas détectées.
- **Température intérieure** : mesure en °C affichée à l'accueil, sans l'attribuer artificiellement à chaque zone.
- **Chauffage** : sélecteur Éco/Confort pour chaque zone ; sélecteur Arrêt général/Automatique pour l'ensemble. États issus des icônes sélectionnées du boîtier. Pas de thermostat à consigne en °C, car le boîtier n'en expose pas. La zone nommée `N/A` est désactivée par défaut et peut être activée dans la liste des entités.
- **Consommation chauffage/clim**, totale, autres usages et production : unité exacte de la page (EUR, Wh ou kWh). Un montant en euros n'est jamais converti arbitrairement en kWh. Un zéro peut signifier une absence de comptage ; il ne prouve pas une consommation nulle.

Seuls les compteurs Wh/kWh sont utilisables comme énergie dans le tableau de bord Énergie. Le boîtier examiné expose des EUR. Si son unité est modifiée ultérieurement, recharger l'intégration pour créer les entités correspondant à la nouvelle unité ; les anciennes deviennent indisponibles.

## Installation manuelle

1. Copier `custom_components/tydom350` dans `/config/custom_components/tydom350` sur Home Assistant.
2. Redémarrer Home Assistant.
3. Paramètres → Appareils et services → Ajouter une intégration → **Delta Dore TYDOM 350 (local)**.
4. Saisir l'adresse du boîtier sur votre réseau local. Laisser les identifiants vides si l'interface n'en demande pas. Le formulaire accepte une authentification HTTP Basic existante.
5. Actualisation par défaut : 60 secondes, minimum 30 secondes. La découverte et la configuration lisent uniquement les pages et n'émettent pas de commande radio.

Pas de compte cloud, MQTT ou HACS nécessaire. Pour annuler : supprimer l'entrée depuis Appareils et services, retirer ce dossier, puis redémarrer Home Assistant.

## Limites et fonctionnement

- Interface française et structure des pages de ce firmware validées. D'autres versions/langues peuvent nécessiter des adaptations.
- Les requêtes sont séquentielles, avec délai maximal de 15 secondes par page et aucune répétition automatique de commande.
- `COUNT` est un jeton dynamique : la page est relue immédiatement avant chaque commande. Un verrou évite que l'actualisation de cette intégration interfère avec cet échange ; un autre client du boîtier peut encore intervenir.
- Seules les commandes lumière, Éco/Confort et Arrêt/Auto sont autorisées. Aucune remise à zéro de consommation, modification réseau, alarme, association ou changement de mot de passe.
- Les nouveaux équipements nécessitent un rechargement de l'intégration.
- La validation HTTP d'une commande n'est pas une preuve de réception radio par le récepteur.

## Recherche d'intégrations existantes

- [Delta Dore Tydom](https://github.com/CyrilP/hass-deltadore-tydom-component) : intégration pour l'API des passerelles Tydom modernes.
- [tydom2mqtt](https://github.com/mrwiwi/tydom2mqtt) : passerelle MQTT reposant également sur WebSocket.
- Aucune prise en charge documentée de l'interface CGI du TYDOM 350 trouvée dans ces projets lors de la recherche du 28 septembre 2026.

## Validation

19 tests automatisés : pages synthétiques reproduisant le format observé, HTML mal formé, jetons variables, unités, états inconnus, portée des commandes, erreurs, et transport HTTP simulé. Lecture réelle du boîtier ; les commandes physiques nécessitent une vérification sur place.


### Lancer les tests

Avec Python 3.14 et [uv](https://docs.astral.sh/uv/) :

```sh
uv venv --python 3.14
uv pip install --python .venv/bin/python -r requirements-test.txt
.venv/bin/python -m pytest -q
```

Les tests utilisent un serveur local simulé et des données fictives ; ils ne contactent aucun boîtier réel.

## Licence

MIT. Projet communautaire indépendant, non affilié à Delta Dore.
