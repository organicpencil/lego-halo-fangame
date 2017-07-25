import bge
import mathutils
import weapons
import utils
from ai import AI_Turret


def clamp(number, minimum, maximum):
    return max(minimum, min(number, maximum))


class Warthog:
    def __init__(self, cont):
        self.owner = cont.owner
        self.passengers = [None, None, None]  # driver, turret, passenger
        self.seats = []  # Set with object setup

        self.config()
        self.setup(cont)

        cont.actuators['Camera'].owner.removeParent()
        self.act = cont.actuators['Sound']
        self.act.pitch = 1.0
        cont.activate(self.act)

        self.lastvel = 0.0
        self.started = False

        self.owner.collisionCallbacks.append(self.collision)

    def config(self):
        # Tire positions relative to carObj origin
        self.tirePos = [[-2.21696, 3.55996, -1.1],  # front left
                        [2.21587, 3.55996, -1.1],  # front right
                        [-2.21696, -3.55996, -1.1],  # rear left
                        [2.21587, -3.23513, -1.1]]  # rear right

        self.tireRadius = [1.153,  # front left
                           1.153,  # front right
                           1.153,  # rear left
                           1.153]  # rear right

        # Tire suspension height
        self.tireSuspension = [0.0,  # front left
                               0.0,  # front right
                               0.0,  # rear left
                               0.0]  # rear right

        # Tire suspension angle
        self.tireAngle = [[0.0, 0.0, -1.0],  # front left
                          [0.0, 0.0, -1.0],  # front right
                          [0.0, 0.0, -1.0],  # rear left
                          [0.0, 0.0, -1.0]]  # rear right

        # Tire axis attached to axle
        self.tireAxis = [[-1.0, 0.0, 0.0],  # front left
                         [-1.0, 0.0, 0.0],  # front right
                         [-1.0, 0.0, 0.0],  # rear left
                         [-1.0, 0.0, 0.0]]  # rear right

        # Which tires have steering
        self.tireSteering = [True,  # front left
                             True,  # front right
                             False,  # rear left
                             False]  # rear right

        # Grip factor (friction)
        self.tireGrip = [10.0,  # front left
                         10.0,  # front right
                         10.0,  # rear left
                         10.0]  # rear right

        # Tires that apply power (fwd/rwd/awd/etc)
        self.powerTires = [True,  # front left
                           True,  # front right
                           True,  # rear left
                           True]  # rear right

        # Suspension compression
        self.compression = [6.0,  # front left
                            6.0,  # front right
                            6.0,  # rear left
                            6.0]  # rear right

        # Suspension damping
        self.damping = [0.1,  # front left
                        0.1,  # front right
                        0.1,  # rear left
                        0.1]  # rear right

        # Suspension stiffness
        self.stiffness = [15.0,  # front left
                          15.0,  # front right
                          15.0,  # rear left
                          15.0]  # rear right

        # Roll influence
        self.roll = [0.00,  # front left
                     0.00,  # front right
                     0.00,  # rear left
                     0.00]  # rear right

        # Steering limit (more = potential for sharper turns)
        self.turnMax = 0.5

        # Steering change per second (more = faster turn rate)
        self.turnRate = 0.1
        self.steering = 0.0

        # Amount per second
        self.brakeAmount = 5.0
        self.gasPower = 400.0

    def setup(self, cont):
        ### Vehicle constraint setup
        ob = self.owner
        phys_ID = ob.getPhysicsId()

        constraint = bge.constraints.createConstraint(phys_ID, 0, 11)
        constraint_ID = constraint.getConstraintId()

        constraint = bge.constraints.getVehicleConstraint(constraint_ID)
        self.constraint = constraint

        ### Tire setup
        self.tires = []
        self.suspensions = []
        tirelist = ['FL', 'FR', 'RL', 'RR']
        for i in range(0, 4):
            tire_ob = ob.children['warthog-tire-' + tirelist[i]]
            tire_ob.removeParent()
            self.tires.append(tire_ob)
            self.suspensions.append(ob.children['warthog-suspension-' + tirelist[i]])

            pos = self.tirePos[i]
            suspA = self.tireAngle[i]
            axis = self.tireAxis[i]
            suspH = self.tireSuspension[i]
            radius = self.tireRadius[i]
            steering = self.tireSteering[i]

            constraint.addWheel(tire_ob, pos,
                    suspA, axis, suspH, radius, steering)

        ### Suspension setup
        for i in range(0, 4):
            constraint.setTyreFriction(self.tireGrip[i], i)
            constraint.setSuspensionCompression(self.compression[i], i)
            constraint.setSuspensionDamping(self.damping[i], i)
            constraint.setSuspensionStiffness(self.stiffness[i], i)
            constraint.setRollInfluence(self.roll[i], i)

        ## Seats
        sensors = cont.sensors
        self.seats.append(sensors['driver_seat'].owner)
        self.seats.append(sensors['turret_seat'].owner)
        self.seats.append(sensors['passenger_seat'].owner)

        ## Turret
        self.turret = Turret(self, sensors['turret_base'].owner)

    def collision(self, ob, point, normal):
        comp = ob.get('_component', None)
        if comp is not None:
            if hasattr(comp, 'takeDamage') and not comp in self.passengers:
                # Splatter
                v = self.owner.getLinearVelocity(True)[1]
                normal = normal * self.owner.worldOrientation
                if v > 10.0:
                    if normal[1] > 0.5:
                        data = {}
                        data['damage'] = int(v / 8)
                        data['ob'] = self.owner
                        comp.takeDamage(data)

                if v < -10.0:
                    if normal[1] < -0.5:
                        data = {}
                        data['damage'] = abs(int(v / 8))
                        data['ob'] = self.owner
                        comp.takeDamage(data)

    def addSteering(self, amount):
        start = self.steering
        self.steering = clamp(self.steering + amount, -1.0, 1.0)

        # Steering wheel
        diff = self.steering - start
        wheel = self.owner.children['warthog-steeringwheel']
        wheel.applyRotation((0.0, 0.0, diff * 2.0), True)

    def releaseSteering(self):
        start = self.steering
        amount = self.turnRate
        if self.steering < 0.0:
            self.steering += amount
            if self.steering > 0.0:
                self.steering = 0.0

        elif self.steering > 0.0:
            self.steering -= amount
            if self.steering < 0.0:
                self.steering = 0.0

        # Steering wheel
        diff = self.steering - start
        wheel = self.owner.children['warthog-steeringwheel']
        wheel.applyRotation((0.0, 0.0, diff * 2.0), True)

    def update(self, cont):
        dt = 0.016667
        self.update_driver(dt)
        self.turret.update(dt)

    def update_driver(self, dt):
        gas = 0.0
        steer = 0.0
        brake = 0.0

        driver = self.passengers[0]
        if driver is not None:
            if not self.started:
                self.started = True
                #cont.activate('enter')
                #cont.activate('Camera')
                #cont.activate('Scene')

            keys = driver.keystate.bin

            # Forward
            if keys[0] == '1':
                gas -= 1.0

            # Back
            if keys[1] == '1':
                gas += 1.0

            # Left
            if keys[2] == '1':
                steer += 1.0

            # Right
            if keys[3] == '1':
                steer -= 1.0

            # Brake (jump key)
            if keys[4] == '1':
                brake = 1.0
                gas = 0.0

            # Exit vehicle (interact key)
            if keys[5] == '1':
                driver.exit_vehicle()

            # Sounds
            vel = self.owner.localLinearVelocity.length
            diff = vel - self.lastvel
            self.lastvel = vel

            vol = self.act.volume
            if vol < 0.75:
                vol += 0.02

            pitch = self.act.pitch
            if abs(gas) > 0.5:
                if vol < 1.5:
                    vol += 0.01
                self.act.volume = vol
                if pitch < 1.0:
                    pitch += 0.001
            else:
                if vol > 0.75:
                    vol -= 0.002
                pitch -= 0.005

            if diff < 0.0:
                pitch -= clamp(abs(diff * 0.05), 0.0, 0.01)

            self.act.volume = vol
            self.act.pitch = clamp(pitch, 0.70, 1.0)
        else:
            brake = 1.0
            self.act.volume = 0.0



        # Steering etc
        constraint = self.constraint

        if steer == 0.0:
            self.releaseSteering()
        else:
            self.addSteering(steer * self.turnRate)

        brake = brake * self.brakeAmount
        for i in range(0, 4):
            constraint.applyBraking(brake, i)

        gas = gas * self.gasPower
        for i in range(0, 4):
            if self.powerTires[i]:
                constraint.applyEngineForce(gas, i)

        # Tire steering
        steer = self.steering * self.turnMax
        for i in range(0, 4):
            if self.tireSteering[i]:
                constraint.setSteeringValue(steer, i)
            else:
                constraint.setSteeringValue(-steer, i)

        # Brake lights
        lights = self.owner.children['warthog-taillights']
        v = self.owner.getLinearVelocity(True)[1]
        if brake > 0.0:
            lights.setVisible(True)
        elif v > 0.0:
            if gas > 0.0:
                lights.setVisible(True)
            else:
                lights.setVisible(False)
        elif v < 0.0:
            if gas < 0.0:
                lights.setVisible(True)
            else:
                lights.setVisible(False)
        else:
            lights.setVisible(False)

        # Extra gravity
        self.owner.applyForce((0.0, 0.0, -1000.0), False)

        # Suspension effect
        for i in range(0, 4):
            self.suspensions[i].worldPosition = self.tires[i].worldPosition


class Turret:
    def __init__(self, hog, base):
        self.hog = hog
        self.base = base
        self.pitch = base.children['warthog_turret_pitch']
        self.barrel = self.pitch.children['warthog_turret_barrel']
        self.owner = self.spawn = self.pitch.children['warthog_turret_spawn']

        self.firetime = 0.0
        self.speed = 0.0
        self.shoot_timer = 0.0

        self.state = self.state_idle
        self.ai = AI_Turret(bge.logic.game.ai, self, 0)
        self.primary = False

    def setPrimary(self, primary):
        self.primary = primary

    def update(self, dt):
        self.barrel.applyRotation((-self.speed, 0.0, 0.0), True)

        c = (13.5 - self.firetime) / 3.5
        if c > 1.0:
            c = 1.0
        self.barrel.color = (1.0, c, c, 1.0)

        self.state(dt)

        user = self.hog.passengers[1]
        if user is None:
            if self.state == self.state_firing:
                self.state = self.state_idle
            return

        if not user.controlled:
            # Run the AI
            self.ai.team = user.team
            self.ai.state()

        keys = user.keystate.bin

        if user.controlled:
            # Input and mouselook(?)
            if keys[6] == '1':
                self.primary = True
            else:
                self.primary = False

            move = mathutils.Vector()

            if keys[0] == '1':
                # Forward
                move[1] += 1.0
            if keys[1] == '1':
                # Back
                move[1] -= 1.0
            if keys[2] == '1':
                # Left
                move[0] -= 1.0
            if keys[3] == '1':
                # Right
                move[0] += 1.0

            base = self.base
            if move.length:
                base = self.base
                base.alignAxisToVect(move * bge.logic.getCurrentScene().active_camera.children[0].worldOrientation.inverted(), 1, 0.4)
                base.alignAxisToVect((0, 0, 1), 2)

            elif self.primary:
                # Run the AI and overwrite firing settings
                self.ai.team = user.team
                self.ai.state()
                self.setPrimary(True)

        # Fire turret (primary)
        #if keys[6] == '1':
        if self.primary:
            if self.state == self.state_idle:
                self.state = self.state_firing
        elif self.state == self.state_firing:
            self.state = self.state_idle

        # Exit vehicle (interact)
        if keys[5] == '1':
            user.exit_vehicle()

    def state_idle(self, dt):
        self.hog.owner['firing'] = False

        self.speed -= 0.005
        self.firetime -= dt

        if self.speed < 0.0:
            self.speed = 0.0

        if self.firetime < 0.0:
            self.firetime = 0.0

    def state_firing(self, dt):
        self.hog.owner['firing'] = True

        self.speed += 0.025
        if self.speed > 0.5:
            self.speed = 0.5

        self.firetime += dt
        self.shoot_timer -= dt

        if self.firetime > 13.5:
            # Cooldown
            self.state = self.state_cooldown
        else:
            if self.shoot_timer <= 0.0:
                # Shoot
                delta = max(0.0, self.hog.owner.getLinearVelocity(True)[1])
                speed = delta + 30.0
                weapons.Laser(None, ref=self.spawn, args={'speed': speed})
                self.shoot_timer = 0.2

    def state_cooldown(self, dt):
        self.hog.owner['firing'] = False

        self.speed -= 0.005
        self.firetime -= dt
        if self.speed < 0.0:
            self.speed = 0.0
            self.state = self.state_idle


def main(cont):
    owner = cont.owner
    v = owner.get('vehicle', None)
    if v is None:
        owner['vehicle'] = Warthog(cont)
    else:
        v.update(cont)