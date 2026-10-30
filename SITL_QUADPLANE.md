# Faire voler `mission_manager` sur ArduPilot SITL (QuadPlane) avec MAVROS

Suite de la démo `drone_demo_ws` : on remplace `sim_drone` par un **vrai autopilote ArduPilot simulé (SITL)** en mode **QuadPlane**, relié à ROS 2 par **MAVROS**. Le but est de garder `mission_manager` et `aruco_detector` **sans modifier une ligne**.

```
 ┌──────────────┐ MAVLink ┌────────┐            ┌───────────────┐  /drone/pose   ┌──────────────────┐
 │ SITL         │ ◀─────▶ │ MAVROS │ ◀────────▶ │ mavros_bridge │ ─────────────▶ │ mission_manager  │
 │ ArduPlane    │         └────────┘            │  (nouveau)    │ ◀───────────── │   (inchangé)     │
 │ (quadplane)  │             │                 └───────────────┘    /cmd_vel    └──────────────────┘
 └──────────────┘             │ /mavros/local_position/pose                            ▲
                              ▼                                                        │ /landing_target
                       ┌──────────────┐  /camera/image_raw   ┌────────────────┐        │
                       │ sim_camera   │ ───────────────────▶ │ aruco_detector │ ───────┘
                       │  (nouveau)   │                      │   (inchangé)   │
                       └──────────────┘                      └────────────────┘
```

---

## Ce qu'il faut savoir avant de commencer

L'étape 8 du README dit qu'il « suffit de renommer deux topics ». C'est vrai pour **ArduCopter**, mais pas pour un **QuadPlane**, pour deux raisons :

1. **Les consignes de vitesse sont probablement ignorées.** En GUIDED avec `Q_GUIDED_MODE=1`, les consignes de vitesse (`SET_POSITION_TARGET_LOCAL_NED`, c'est-à-dire `/mavros/setpoint_velocity/cmd_vel_unstamped`) ne semblent avoir aucun effet sur un QuadPlane. La commande qui fonctionne est `MAV_CMD_DO_REPOSITION` : un point GPS à rejoindre.
2. **Les QoS sont incompatibles.** MAVROS publie la pose en QoS *best effort* (données capteur), alors que `mission_manager` s'abonne en *reliable*. Les deux ne se connectent pas : le nœud ne reçoit rien, et aucun message d'erreur ne s'affiche.

D'où deux nouveaux nœuds, et toujours zéro changement dans la logique de mission :

| Nœud | Rôle |
|---|---|
| `mavros_bridge` | traduit `/cmd_vel` en `DO_REPOSITION`, republie la pose sur `/drone/pose` en *reliable*, passe en `QLAND` quand la mission entre en `LAND` |
| `sim_camera` | SITL n'a pas de caméra : ce nœud réutilise `SimDrone.render()` avec la position donnée par MAVROS |

> **Conseil :** faites d'abord tout le parcours avec **ArduCopter** (`-v ArduCopter`). Les consignes de vitesse y fonctionnent directement, et les remaps du README suffisent (en gardant `sim_camera` et en contournant le piège QoS). En 30 minutes, ça valide MAVROS, la caméra simulée et la mission. Passez ensuite au QuadPlane.

---

## Étape 0 : prérequis

- La démo de base fonctionne (README, étapes 1 à 4).
- Ubuntu 24.04 + ROS 2 Jazzy.
- Environ 5 Go d'espace disque pour ArduPilot.

> **Utilisateurs zsh** (prompt `➜`, Oh My Zsh…) : les scripts `.bash` ne fonctionnent pas sous zsh (erreurs `command not found: shopt`, `no such file or directory: .../setup.sh`). Utilisez partout la version `.zsh` :
>
> ```bash
> echo "source /opt/ros/jazzy/setup.zsh" >> ~/.zshrc     # au lieu de setup.bash dans ~/.bashrc
> source install/setup.zsh                               # au lieu de install/setup.bash, dans chaque terminal
> ```
>
> Ne faites jamais `source ~/.bashrc` depuis zsh. Si c'est déjà arrivé, `exec zsh` repart d'un shell propre.
>
> L'installation d'ArduPilot (étape 1) écrit ses chemins dans `~/.profile` et `~/.bashrc`. Si `sim_vehicle.py` est introuvable ensuite, ajoutez à `~/.zshrc` :
>
> ```bash
> export PATH="$HOME/ardupilot/Tools/autotest:$PATH"
> ```

## Étape 1 : installer ArduPilot SITL

```bash
cd ~
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile                      # ou rouvrir le terminal (zsh : voir la note de l'étape 0)
./waf configure --board sitl
./waf plane                       # (et ./waf copter pour le test préalable conseillé)
```

## Étape 2 : lancer le QuadPlane simulé

```bash
cd ~/ardupilot/ArduPlane
../Tools/autotest/sim_vehicle.py -v ArduPlane -f quadplane --console --map -w \
    --out=udp:127.0.0.1:14551
```

- `-w` remet les paramètres à zéro. Il ne sert qu'au **premier** lancement.
- `--out=udp:127.0.0.1:14551` crée une seconde sortie MAVLink, réservée à MAVROS. MAVProxy garde la sienne.

Une fois la console prête, tapez dans **MAVProxy** :

```
param set Q_GUIDED_MODE 1
```

Ce paramètre fait que GUIDED reste en **vol quad** : le drone stationnaire ne bascule pas en vol avion.

## Étape 3 : installer et brancher MAVROS

```bash
sudo apt install -y ros-jazzy-mavros ros-jazzy-mavros-extras
sudo /opt/ros/jazzy/lib/mavros/install_geographiclib_datasets.sh
ros2 launch mavros apm.launch fcu_url:=udp://:14551@
```

Vérifications, dans un autre terminal :

```bash
ros2 topic echo /mavros/state --once                 # connected: true, mode: ...
ros2 topic echo /mavros/local_position/pose --once   # la position du drone
ros2 topic info -v /mavros/local_position/pose       # "Reliability: BEST_EFFORT" : voilà le piège QoS
```

## Étape 4 : premier vol à la main (sans ROS)

On décolle en **QLOITER** avec la radiocommande simulée de MAVProxy :

```
mode qloiter
rc 3 1000          # gaz en bas pour pouvoir armer
arm throttle
rc 3 1700          # le drone monte : attendre ~4 m (affiché dans la console)
rc 3 1500          # gaz au neutre : maintien d'altitude
mode guided
```

Le même changement de mode depuis ROS :

```bash
ros2 service call /mavros/set_mode mavros_msgs/srv/SetMode "{custom_mode: 'GUIDED'}"
```

## Étape 5 : constater la limite des vitesses

Le drone est en GUIDED à ~4 m. Envoyez-lui une vitesse vers l'est :

```bash
ros2 topic pub -r 10 /mavros/setpoint_velocity/cmd_vel_unstamped geometry_msgs/msg/Twist "{linear: {x: 1.0}}"
```

- **Le drone ne bouge pas** : c'est le résultat attendu, et c'est pour ça qu'il faut `mavros_bridge`. Passez à l'étape 6.
- **Le drone part vers l'est** : votre version d'ArduPilot accepte les vitesses. Les remaps du README peuvent suffire, mais il faut quand même régler le problème de QoS.

## Étape 6 : créer `sim_camera`

Fichier `src/drone_demo/drone_demo/sim_camera_node.py` :

```python
"""Nœud « sim_camera » : caméra simulée pour SITL.

Écoute   /mavros/local_position/pose (geometry_msgs/PoseStamped, best effort)
Publie   /camera/image_raw           (sensor_msgs/Image) -> même topic que la vraie caméra
"""
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from .sim_core import SimDrone


class SimCameraNode(Node):
    def __init__(self):
        super().__init__("sim_camera")
        for name, default in {"station_x": 5.0, "station_y": 4.0, "marker_id": 0,
                              "marker_size": 0.5, "fov_deg": 80.0, "camera_hz": 15.0}.items():
            self.declare_parameter(name, default)
        g = lambda n: self.get_parameter(n).value  # noqa: E731
        self.station = np.array([g("station_x"), g("station_y")])
        self.sim = SimDrone(marker_id=int(g("marker_id")), marker_size=g("marker_size"), fov_deg=g("fov_deg"))
        self.have_pose = False
        self.bridge = CvBridge()

        self.create_subscription(PoseStamped, "/mavros/local_position/pose", self.on_pose, qos_profile_sensor_data)
        self.img_pub = self.create_publisher(Image, "/camera/image_raw", 5)
        self.create_timer(1.0 / g("camera_hz"), self.publish_image)
        self.get_logger().info(f"Station placée en x={self.station[0]} m, y={self.station[1]} m du décollage")

    def on_pose(self, msg: PoseStamped):
        p = msg.pose.position
        # SimDrone place la station en (0, 0) : on exprime le drone relativement à elle
        self.sim.pos[:] = (p.x - self.station[0], p.y - self.station[1], p.z)
        self.have_pose = True

    def publish_image(self):
        if not self.have_pose:
            return
        msg = self.bridge.cv2_to_imgmsg(self.sim.render(), encoding="mono8")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "camera"
        self.img_pub.publish(msg)


def main():
    rclpy.init()
    node = SimCameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
```

La station est placée à **5 m à l'est et 4 m au nord du point de décollage**, comme dans la démo. Comme le drone part à 4 m d'altitude, il ne la voit pas au départ et doit passer par l'état SEARCH.

## Étape 7 : créer `mavros_bridge`

Principe : une **« carotte »**. On intègre la vitesse demandée par `mission_manager` dans un point cible placé devant le drone. On envoie ce point à ArduPilot avec `DO_REPOSITION`, et on le borne à `max_lead` mètres du drone pour qu'il ne s'emballe pas.

Fichier `src/drone_demo/drone_demo/mavros_bridge_node.py` :

```python
"""Nœud « mavros_bridge » : relie mission_manager à un QuadPlane ArduPilot via MAVROS.

Écoute   /cmd_vel                       (geometry_msgs/Twist, ENU)  <- mission_manager
         /mission/state                 (std_msgs/String)           <- mission_manager
         /mavros/local_position/pose    (PoseStamped, best effort)
         /mavros/global_position/global (NavSatFix, best effort)
         /mavros/state                  (mavros_msgs/State)
Publie   /drone/pose                    (PoseStamped, reliable)     -> mission_manager
Appelle  /mavros/cmd/command_int        (MAV_CMD_DO_REPOSITION)
         /mavros/set_mode               (QLAND quand la mission passe en LAND)
"""
import math

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped, Twist
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandInt, SetMode
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import String

EARTH_R = 6378137.0
MAV_CMD_DO_REPOSITION = 192
MAV_FRAME_GLOBAL_RELATIVE_ALT_INT = 6


class MavrosBridgeNode(Node):
    def __init__(self):
        super().__init__("mavros_bridge")
        self.declare_parameter("send_hz", 4.0)        # fréquence d'envoi des DO_REPOSITION
        self.declare_parameter("max_lead", 2.0)       # avance max de la carotte (m)
        self.declare_parameter("cmd_timeout_s", 0.5)  # sans consigne récente : vitesse nulle
        g = lambda n: self.get_parameter(n).value  # noqa: E731
        self.max_lead, self.cmd_timeout = g("max_lead"), g("cmd_timeout_s")

        self.pos = None
        self.fix = None
        self.carrot = None
        self.vel = np.zeros(3)
        self.last_cmd = None
        self.mode = ""
        self.landing = False

        self.create_subscription(PoseStamped, "/mavros/local_position/pose", self.on_pose, qos_profile_sensor_data)
        self.create_subscription(NavSatFix, "/mavros/global_position/global", self.on_fix, qos_profile_sensor_data)
        self.create_subscription(State, "/mavros/state", self.on_state, 10)
        self.create_subscription(Twist, "/cmd_vel", self.on_cmd, 10)
        self.create_subscription(String, "/mission/state", self.on_mission, 10)
        self.pose_pub = self.create_publisher(PoseStamped, "/drone/pose", 10)
        self.reposition = self.create_client(CommandInt, "/mavros/cmd/command_int")
        self.set_mode = self.create_client(SetMode, "/mavros/set_mode")

        self.dt = 1.0 / g("send_hz")
        self.create_timer(self.dt, self.tick)

    def on_pose(self, msg: PoseStamped):
        p = msg.pose.position
        self.pos = np.array([p.x, p.y, p.z])
        self.pose_pub.publish(msg)  # relais best effort -> reliable

    def on_fix(self, msg: NavSatFix):
        self.fix = msg

    def on_state(self, msg: State):
        if msg.mode != self.mode:
            self.get_logger().info(f"Mode ArduPilot : {msg.mode}")
            self.carrot = None  # après chaque changement de mode, on repart de la position actuelle
        self.mode = msg.mode

    def on_cmd(self, msg: Twist):
        self.vel[:] = (msg.linear.x, msg.linear.y, msg.linear.z)
        self.last_cmd = self.get_clock().now()

    def on_mission(self, msg: String):
        if msg.data == "LAND" and not self.landing:
            self.landing = True
            self.get_logger().info("Mission en LAND : passage en QLAND")
            self.set_mode.call_async(SetMode.Request(custom_mode="QLAND"))

    def tick(self):
        # On ne commande qu'en GUIDED : en QLOITER, le pilote (MAVProxy) garde la main
        if self.pos is None or self.fix is None or self.mode != "GUIDED" or self.landing:
            return
        now = self.get_clock().now()
        stale = self.last_cmd is None or (now - self.last_cmd).nanoseconds * 1e-9 > self.cmd_timeout
        vel = np.zeros(3) if stale else self.vel

        if self.carrot is None:
            self.carrot = self.pos.copy()
        self.carrot += vel * self.dt
        lead = self.carrot - self.pos
        n = np.linalg.norm(lead)
        if n > self.max_lead:
            self.carrot = self.pos + lead * self.max_lead / n
            lead = self.carrot - self.pos

        # Décalage ENU (m) -> lat/lon autour de la position GPS actuelle
        lat = self.fix.latitude + math.degrees(lead[1] / EARTH_R)
        lon = self.fix.longitude + math.degrees(lead[0] / (EARTH_R * math.cos(math.radians(self.fix.latitude))))

        req = CommandInt.Request()
        req.frame = MAV_FRAME_GLOBAL_RELATIVE_ALT_INT
        req.command = MAV_CMD_DO_REPOSITION
        req.param1 = -1.0               # vitesse par défaut
        req.param4 = float("nan")       # cap inchangé
        req.x, req.y = int(lat * 1e7), int(lon * 1e7)
        req.z = float(self.carrot[2])   # altitude relative au point de décollage
        self.reposition.call_async(req)


def main():
    rclpy.init()
    node = MavrosBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
```

Pourquoi passer en **QLAND** au lieu de descendre « à la main » ? L'état `LAND` de `mission_manager` imite déjà le mode LAND : le dernier mètre se fait à l'aveugle. QLAND le fait mieux. Il détecte le contact avec le sol et désarme tout seul.

## Étape 8 : déclarer les nouveaux nœuds

Dans `setup.py`, ajoutez à `console_scripts` :

```python
"sim_camera = drone_demo.sim_camera_node:main",
"mavros_bridge = drone_demo.mavros_bridge_node:main",
```

Dans `package.xml` :

```xml
<exec_depend>mavros_msgs</exec_depend>
```

Puis recompilez :

```bash
cd ~/github_projets/ROS_2/drone_demo_ws    # toujours depuis la racine du workspace
colcon build --symlink-install
source install/setup.bash          # zsh : source install/setup.zsh
```

## Étape 9 : le vol complet

Ouvrez **6 terminaux**, avec `source install/setup.bash` (zsh : `setup.zsh`) dans chacun des terminaux ROS :

| Terminal | Commande |
|---|---|
| T1 | SITL (étape 2) |
| T2 | `ros2 launch mavros apm.launch fcu_url:=udp://:14551@` |
| T3 | `ros2 run drone_demo sim_camera` |
| T4 | `ros2 run drone_demo aruco_detector` |
| T5 | `ros2 run drone_demo mavros_bridge` |
| T6 | `ros2 run drone_demo mission_manager --ros-args --params-file src/drone_demo/config/params.yaml` |

Ensuite, dans MAVProxy (T1), faites le décollage de l'étape 4 jusqu'à ~4 m, puis `mode guided`.

Ce qu'on doit voir :

- T6 : `SEARCH -> ALIGN -> DESCEND -> LAND`.
- T5 : `Mission en LAND : passage en QLAND`, puis `Mode ArduPilot : QLAND`.
- MAVProxy : atterrissage, puis `DISARMED`.

Pour regarder ce que « voit » le drone :

```bash
ros2 run rqt_image_view rqt_image_view /camera/debug
rqt_graph
```

> `mission_manager` peut être lancé avant le passage en GUIDED : `mavros_bridge` n'envoie rien tant que le mode n'est pas GUIDED. En cas de souci, `mode qloiter` dans MAVProxy reprend la main immédiatement.

## Étape 10 : mesurer et enregistrer

```bash
ros2 bag record -o sitl_vol1 /mavros/local_position/pose /landing_target /cmd_vel /mission/state
```

Une fois posé, la précision se lit dans la pose : comparez `x` et `y` à la station `(5.0, 4.0)`.

```bash
ros2 topic echo /mavros/local_position/pose --once
```

Le bag s'ouvre dans PlotJuggler, comme pour la démo.

---

## Dépannage

| Symptôme | Cause probable | Piste |
|---|---|---|
| `mission_manager` n'affiche rien | il ne reçoit pas `/drone/pose` | `mavros_bridge` tourne-t-il ? `ros2 topic hz /drone/pose` |
| `/mavros/state` : `connected: false` | mauvais port | vérifier `--out=udp:127.0.0.1:14551` et `fcu_url:=udp://:14551@` |
| Le drone ne bouge pas en GUIDED | `Q_GUIDED_MODE` à 0 ou bridge inactif | `param show Q_GUIDED_MODE` dans MAVProxy ; logs de T5 |
| Mouvements saccadés | trop de `DO_REPOSITION` | baisser `send_hz` à 2, augmenter `max_lead` |
| Le drone bascule en vol avion | `Q_GUIDED_MODE` à 0 | `param set Q_GUIDED_MODE 1` |
| Reste en SEARCH | station hors du champ | `ros2 run rqt_image_view rqt_image_view /camera/debug` ; ajuster `station_x/y` ou `search_altitude` |
| `command not found: shopt` ou `.../setup.sh` introuvable | script bash chargé sous zsh | utiliser `setup.zsh` (note de l'étape 0) ; `exec zsh` |
| `sim_vehicle.py: command not found` (zsh) | PATH d'ArduPilot écrit dans `~/.bashrc` | ajouter `export PATH="$HOME/ardupilot/Tools/autotest:$PATH"` à `~/.zshrc` |
| `/mavros/global_position/global` vide | datasets GeographicLib absents | relancer `install_geographiclib_datasets.sh` |

## Limites et suites

- **Code non testé.** Les deux nœuds sont écrits d'après la doc ArduPilot et le code de la démo, mais n'ont pas encore tourné. À vérifier en premier :
  - que `DO_REPOSITION` envoyé à 4 Hz donne un mouvement fluide en GUIDED quad ;
  - que les petites corrections près du sol sont assez précises.
- **Le cap est ignoré.** `sim_camera` ne tient pas compte du lacet, donc la simulation reste cohérente. Sur le vrai drone, il faudra faire tourner `(dx, dy)` selon le lacet lu dans la pose.
- **Atterrissage de précision natif.** Une autre piste : envoyer le message MAVLink `LANDING_TARGET` à ArduPilot (`PLND_ENABLED=1`) et le laisser gérer toute la descente en QLAND. Pour un QuadPlane, c'est sans doute plus robuste que de piloter la descente depuis ROS.
- **Toujours SITL d'abord.** Chaque modification se valide ici avant le vrai vol.

## Références

- [Plane Commands in Guided Mode (doc ArduPilot)](https://ardupilot.org/dev/docs/plane-commands-in-guided-mode.html)
- [QuadPlane VTOL : SET_POSITION_TARGET_LOCAL_NED / vitesses en GUIDED (forum ArduPilot)](https://discuss.ardupilot.org/t/quadplane-vtol-set-position-target-local-ned-set-velocity-control-in-guided-mode/145444)
- [ArduPlane `mode_guided.cpp`](https://github.com/ardupilot/ardupilot/blob/master/ArduPlane/mode_guided.cpp)
- [Installation ArduPilot SITL](https://ardupilot.org/dev/docs/building-setup-linux.html)
