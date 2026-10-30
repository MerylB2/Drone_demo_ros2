# À quoi sert ROS 2 dans notre projet

## Rappel de l'architecture

- **Drone** : quadplane (4 moteurs de sustentation + pusher).
- **Autopilote** : ArduPilot ou PX4, pour le vol.
- **Ordinateur compagnon** : Raspberry Pi 5.

## Ce que fait ROS 2, et ce qu'il ne fait pas

ROS 2 ne fait **pas voler le drone**. La stabilisation, la transition et la navigation restent le travail de l'autopilote.

ROS 2 est le **squelette du logiciel sur le Pi 5**. C'est là que se trouve la valeur ajoutée évaluée par le jury.

## Ce qu'il nous apporte

- **Découper le code par pôle.** La vision (ArUco pour la station, YOLO nano), la décision (machine à états de mission) et le dialogue avec l'autopilote deviennent des nœuds séparés. Chacun avance sur son nœud sans casser celui des autres.
- **Faire le lien avec ArduPilot.** MAVROS, ou l'interface DDS native d'ArduPilot, expose la position du drone et accepte des consignes sous forme de topics ROS 2.
- **Passer de la simulation au vrai drone sans réécrire.** Le même code tourne contre SITL/Gazebo puis sur le drone réel. Seule la source des données change.
- **Enregistrer chaque vol.** `ros2 bag` permet de rejouer un essai ou un crash, et de montrer des courbes au jury.
- **Préparer la collaboration entre drones.** Deux drones sur le même réseau voient leurs topics respectifs. C'est utile même si cette partie rapporte moins de points.
- **Préparer le jalon des deux mois.** L'équipe précédente avait montré de la reconnaissance d'image à ce stade. La démo, avec une webcam et un marqueur imprimé, nous en donne une base.

Meryl a déjà pratiqué ROS : elle serait une bonne référente pour l'équipe.

## La démo (`drone_demo_ws`)

C'est un package ROS 2 Jazzy qui reproduit notre cas réel : **l'atterrissage de précision sur la station**. Il compte trois nœuds :

| Nœud | Rôle |
|---|---|
| `sim_drone` | simule le drone et sa caméra |
| `aruco_detector` | repère la station (pôle vision) |
| `mission_manager` | enchaîne les états `SEARCH → ALIGN → DESCEND → LAND → LANDED` (pôle décision) |

Le README contient le guide pas à pas : installation, lancement, webcam réelle, puis branchement sur ArduPilot. Pour ce dernier, il suffit de renommer deux topics, car les messages utilisés sont déjà ceux de MAVROS.

**Résultat en simulation** : posé à **4 à 15 cm** du centre de la station.

## Leçons pour le vrai drone

- **Il faut une caméra grand angle.** Avec un champ étroit, la station sort de l'image près du sol, et le drone ne la voit parfois même pas au départ.
- **Le dernier mètre se fait presque à l'aveugle.** La station sort du champ juste avant le contact : il faut être bien centré avant de s'engager.

## Prochaine étape

Faire tourner le même `mission_manager` contre ArduPilot SITL, en mode QuadPlane, avec MAVROS.
