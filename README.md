# Démo ROS 2 : atterrissage de précision sur la station

Petit projet pour découvrir ROS 2 avec un cas réel de notre quadplane : **trouver la station de recharge, se centrer au-dessus et se poser**, en simulation, sans drone ni Gazebo.

```
 ┌────────────┐  /camera/image_raw   ┌────────────────┐  /landing_target  ┌──────────────────┐
 │ sim_drone  │ ───────────────────▶ │ aruco_detector │ ────────────────▶ │ mission_manager  │
 │ (drone +   │                      │   (vision)     │                   │   (décision)     │
 │  caméra)   │ ◀─────────────────────────────────────────────────────────│                  │
 └────────────┘        /cmd_vel                         /drone/pose ──────▶└──────────────────┘
```

- **sim_drone** joue le rôle du drone + caméra. Plus tard, il sera remplacé par la vraie caméra du Pi 5 et ArduPilot (via MAVROS), **sans toucher aux deux autres nœuds**.
- **aruco_detector** (pôle vision) repère le marqueur et calcule où est la station, en mètres.
- **mission_manager** (pôle décision) enchaîne les états `SEARCH → ALIGN → DESCEND → LAND → LANDED`.

Chaque nœud est un petit programme indépendant. Ils ne se connaissent pas : ils échangent seulement des **messages** sur des **topics**. C'est tout l'intérêt de ROS 2.

---

## Étape 0 : prérequis

- Un PC sous **Ubuntu 24.04** (ou le Pi 5 avec Ubuntu 24.04 pour Raspberry Pi).
- Sous Windows : WSL2 avec Ubuntu 24.04. Sous macOS : Docker (`docker run -it osrf/ros:jazzy-desktop`).

## Étape 1 : installer ROS 2 Jazzy

Jazzy est la version LTS qui correspond à Ubuntu 24.04. En cas de doute, la procédure officielle fait foi : https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

```bash
sudo apt update && sudo apt install -y software-properties-common curl
sudo add-apt-repository universe
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update

# PC de développement (avec les outils graphiques) :
sudo apt install -y ros-jazzy-desktop ros-dev-tools
# Raspberry Pi 5 (sans interface graphique) : ros-jazzy-ros-base à la place de ros-jazzy-desktop

sudo apt install -y ros-jazzy-cv-bridge python3-opencv ros-jazzy-rqt-image-view
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc && source ~/.bashrc
```

Vérification rapide, dans deux terminaux :

```bash
ros2 run demo_nodes_cpp talker      # terminal 1
ros2 run demo_nodes_py listener     # terminal 2 : doit afficher "I heard: Hello World"
```

## Étape 2 : compiler le projet

```bash
# Copier le dossier drone_demo_ws dans votre home, puis :
cd ~/drone_demo_ws
colcon build --symlink-install
source install/setup.bash          # à refaire dans chaque nouveau terminal
```

`--symlink-install` permet de modifier le code Python sans recompiler.

## Étape 3 : lancer les nœuds un par un (pour comprendre)

Ouvrez **4 terminaux** (pensez au `source install/setup.bash` dans chacun).

**Terminal 1 : le drone simulé**
```bash
ros2 run drone_demo sim_drone
```
Dans un autre terminal, observez ce qu'il publie :
```bash
ros2 topic list                     # /camera/image_raw, /drone/pose, /cmd_vel...
ros2 topic hz /camera/image_raw     # ~15 images/s
ros2 topic echo /drone/pose --once  # position du drone
```

**Terminal 2 : la vision**
```bash
ros2 run drone_demo aruco_detector
```
Le drone démarre à 4 m d'altitude, trop bas pour voir la station : `ros2 topic echo /landing_target` n'affiche rien. Normal.

**Terminal 3 : piloter à la main** (en attendant la mission)
```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {z: 1.0}}"
```
Le drone monte. Dès qu'il voit la station, `/landing_target` se met à publier. Faites `Ctrl+C` : sans consigne, le drone se met en stationnaire (sécurité intégrée, comme un vrai autopilote).

**Terminal 4 : regarder ce que voit la caméra**
```bash
ros2 run rqt_image_view rqt_image_view /camera/debug
```

**Terminal 3 : lancer la mission**
```bash
ros2 run drone_demo mission_manager
```
Vous voyez passer `SEARCH -> ALIGN -> DESCEND -> LAND -> LANDED`, puis le simulateur affiche la position d'atterrissage (en général moins de 15 cm du centre).

Pour recommencer : `Ctrl+C` partout et relancez.

## Étape 4 : tout lancer d'un coup

```bash
ros2 launch drone_demo demo.launch.py
```
Et en parallèle :
```bash
rqt_graph                                   # le schéma des nœuds et topics, généré automatiquement
ros2 topic echo /mission/state
ros2 run rqt_image_view rqt_image_view /camera/debug
```

## Étape 5 : enregistrer et rejouer un vol

```bash
ros2 bag record -o vol_test /landing_target /drone/pose /cmd_vel /mission/state
# ... lancer la démo, puis Ctrl+C
ros2 bag info vol_test
ros2 bag play vol_test
```
Les bags s'ouvrent dans PlotJuggler (`sudo apt install ros-jazzy-plotjuggler-ros`) pour tracer la trajectoire et les consignes. C'est exactement ce qu'on fera après chaque essai réel.

## Étape 6 : expérimenter

Les paramètres sont dans `src/drone_demo/config/params.yaml`. Modifiez, relancez `ros2 launch`, observez :

| Essai | Paramètre | Ce qu'on observe |
|---|---|---|
| Plus de dérive | `drift: 0.3` | la précision passe de ~10 à ~40 cm : à vous de régler `kp_xy` / `ki_xy` |
| Régulateur mou | `kp_xy: 0.3` | atterrissage plus lent, le drone se décentre de 15 à 30 cm pendant la descente |
| Régulateur vif | `kp_xy: 2.5` | suivi plus serré ici ; cherchez à partir de quelle valeur il se met à osciller |
| Pas d'intégrale | `ki_xy: 0.0` | précision finale plus irrégulière (de 2 à 30 cm selon les essais) |
| Caméra étroite | `fov_deg: 60.0` (et `start_y: 5.0`) | la station peut ne jamais entrer dans le champ : le drone reste en SEARCH |

Ce dernier cas montre une limite volontaire de la démo : l'état SEARCH se contente de monter. **Exercice** : ajoutez-y un motif de recherche (spirale ou carrés croissants) dans `mission_core.py`, puis vérifiez avec le test hors ROS.

Sans ROS (utile pour régler vite), le test en boucle fermée tourne en quelques secondes :
```bash
cd src/drone_demo && python3 test/test_closed_loop.py
```

## Étape 7 : la vision avec une vraie webcam

```bash
ros2 run drone_demo make_marker --id 0 --out station_marker.png   # à imprimer
sudo apt install -y ros-jazzy-v4l2-camera
ros2 run v4l2_camera v4l2_camera_node --ros-args -r image_raw:=/camera/image_raw
ros2 run drone_demo aruco_detector --ros-args -p marker_size:=0.15 -p fov_deg:=65.0
ros2 run rqt_image_view rqt_image_view /camera/debug
```
Mesurez le carré noir imprimé et mettez sa taille (en mètres) dans `marker_size`, et le champ horizontal de votre webcam dans `fov_deg`. Bougez la feuille : `dx`, `dy` et `z` doivent suivre. **Le nœud de vision n'a pas changé d'une ligne** entre la simulation et la vraie caméra. C'est une bonne démo pour le premier jalon.

## Étape 8 (suite) : brancher le vrai autopilote

Les messages ont été choisis pour correspondre à MAVROS. Le passage à ArduPilot (SITL d'abord, puis le vrai drone) consiste surtout à **remplacer `sim_drone`** et à **renommer deux topics** :

| Démo | ArduPilot via MAVROS |
|---|---|
| `/drone/pose` (PoseStamped) | `/mavros/local_position/pose` |
| `/cmd_vel` (Twist, ENU) | `/mavros/setpoint_velocity/cmd_vel_unstamped` |
| `/camera/image_raw` simulée | caméra du Pi 5 (`camera_ros` ou `v4l2_camera`) |

```bash
ros2 run drone_demo mission_manager --ros-args \
  -r /drone/pose:=/mavros/local_position/pose \
  -r /cmd_vel:=/mavros/setpoint_velocity/cmd_vel_unstamped
```

Ce qu'il restera à faire à ce moment-là :
1. Armer et passer en mode **GUIDED** (services `/mavros/cmd/arming` et `/mavros/set_mode`). En QuadPlane, vérifier le paramètre `Q_GUIDED_MODE` pour que GUIDED reste en vol quad.
2. Tenir compte du **cap** du drone : ici la caméra est supposée alignée nord. En vrai, il faut tourner `(dx, dy)` selon le lacet lu dans `/drone/pose`.
3. Calibrer la caméra (`camera_calibration`) plutôt que d'utiliser un simple champ de vision.
4. Alternative intéressante : envoyer la cible à l'**atterrissage de précision natif d'ArduPilot** (message MAVLink `LANDING_TARGET`) et le laisser gérer la descente.
5. Toujours valider en **SITL** avant le vrai vol.

---

## Organisation du code

```
drone_demo_ws/src/drone_demo/
├── drone_demo/
│   ├── aruco_utils.py          # vision pure (OpenCV), sans ROS
│   ├── sim_core.py             # simulateur pur, sans ROS
│   ├── mission_core.py         # machine à états pure, sans ROS
│   ├── sim_drone_node.py       # } enveloppes ROS 2 : abonnements,
│   ├── aruco_detector_node.py  # } publications, paramètres
│   ├── mission_manager_node.py # }
│   └── make_marker.py
├── launch/demo.launch.py
├── config/params.yaml
└── test/test_closed_loop.py
```

La logique est séparée de ROS : on peut la tester et la régler sans rien lancer, et les nœuds restent de minces enveloppes. Gardez cette habitude pour le vrai code embarqué.
