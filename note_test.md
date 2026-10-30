# 🚁 ROS 2 sur notre drone : à quoi ça sert, et une première démo qui marche

## ROS 2, c'est quoi pour nous ?

ROS 2 ne fait **pas voler le drone**. La stabilisation, la transition et la navigation restent le travail de l'autopilote (ArduPilot).

ROS 2, c'est le **squelette du logiciel sur le Raspberry Pi 5**, l'ordinateur embarqué. C'est là qu'on met notre valeur ajoutée : vision, décisions de mission, dialogue avec l'autopilote. C'est aussi ce que le jury va évaluer.

Concrètement, ça nous apporte :

- **Un code découpé par pôle.** La vision, la décision et la liaison avec l'autopilote sont des programmes séparés (des « nœuds ») qui s'échangent des messages. Chacun avance sur son nœud sans casser celui des autres.
- **La liaison avec ArduPilot.** Grâce à MAVROS, on lit la position du drone et on lui envoie des consignes, directement depuis notre code.
- **Le même code en simulation et sur le vrai drone.** On développe et on teste sur PC. Pour passer au drone, seule la source des données change.
- **L'enregistrement de chaque vol.** On peut rejouer un essai (ou un crash !) pour l'analyser, et montrer des courbes au jury.
- **Une base pour la collaboration entre drones.** Deux drones sur le même réseau voient les messages l'un de l'autre.

---

## La démo : atterrissage de précision sur la station

J'ai monté une démo qui reproduit le cœur de notre mission : **trouver la station, se centrer au-dessus et se poser**, entièrement en simulation.

Elle compte 3 nœuds :

| Nœud | Rôle |
|---|---|
| 🛸 `sim_drone` | simule le drone et sa caméra. Plus tard, il sera remplacé par le vrai drone |
| 👁️ `aruco_detector` | **pôle vision** : repère le marqueur de la station et calcule sa position en mètres |
| 🧠 `mission_manager` | **pôle décision** : enchaîne les étapes **SEARCH → ALIGN → DESCEND → LAND → LANDED** |

[📎 Vidéo : un atterrissage complet]

Comment lire la vue caméra :

- la **croix bleue** est la verticale du drone ;
- le **carré vert** est la station détectée ;
- la **ligne verte** est le décalage à corriger. Elle raccourcit au fur et à mesure que le drone se centre.

[📎 Image : vue caméra avec la station détectée]

[📎 Image : schéma des nœuds (rqt_graph)]

**Résultat :** le drone se pose à environ **10 à 20 cm** du centre de la station. 🎯

## Ce qu'on a appris

- 📷 Il faut une **caméra grand angle**. Avec un champ étroit, la station sort de l'image près du sol.
- 🙈 Le **dernier mètre se fait à l'aveugle**, car la station sort du champ juste avant le contact. Il faut donc être bien centré avant de descendre.

## Prochaine étape

Faire tourner la même mission sur **ArduPilot simulé (SITL), en mode QuadPlane**. Ce sera le dernier test avant le vrai drone. La marche à suivre est dans `SITL_QUADPLANE.md`.

---

Tout est dans le README (installation pas à pas, Ubuntu 24.04 + ROS 2 Jazzy) pour ceux qui veulent tester. Questions et retours bienvenus 🙌
