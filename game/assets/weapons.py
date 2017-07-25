import bge
import mathutils
import random

from netplay import packer, component


class Laser(component.GameObject):
    obj = 'marine_laser_0'
    setuptable = 'LaserSetup'
    particle = 'spark_emitter_red'

    def start_client(self):
        return

    def start_server(self, args):
        self.timer = bge.logic.getFrameTime() + 4.0
        if args is not None:
            self.speed = args.get('speed', 30.0)
            if args.get('vector', None) is not None:
                self.owner.alignAxisToVect(args['vector'], 1)
        else:
            self.speed = 30.0

    def deserialize(self, table):
        get = table.get
        self.owner.worldPosition = (get('pos_x'), get('pos_y'), get('pos_z'))
        rot = mathutils.Euler((get('rot_x'), 0.0, get('rot_z')))
        self.owner.worldOrientation = rot
        self.speed = table.get('speed')

    def serialize(self):
        table = packer.Table('LaserSetup')
        table.set('id', self.net_id)
        pos = self.owner.worldPosition
        table.set('pos_x', pos[0])
        table.set('pos_y', pos[1])
        table.set('pos_z', pos[2])
        rot = self.owner.worldOrientation.to_euler()
        table.set('rot_x', rot[0])
        table.set('rot_z', rot[2])

        # Don't need to send speed for stationary shooters
        if 29.9 < self.speed < 30.1:
            table.set('speed', self.speed)

        return packer.to_bytes(table)

    def LaserSetup(self, table):
        self.deserialize(table)

    def Destroy(self, table):
        if bge.logic.netplay.server:
            print("Running endobject on the server?")
            return

        self.owner.endObject()
        bge.logic.netplay.components[self.net_id] = None

    def update(self):
        self.owner.applyMovement((0.0, self.speed * bge.logic.game.deltatime, 0.0), True)

    def sparks(self, hitPos):
        # Spawn spark particle
        ob = self.owner.scene.addObject(self.particle)
        ob.worldPosition = hitPos
        #ob.scaling = (0.25, 0.25, 0.25)

    def on_hit(self, hitOb, hitPos, hitNormal):
        if hitOb is not None:
            self.sparks(hitPos)
            # Apply the damage
            if '_component' in hitOb:
                data = {}
                data['damage'] = 1
                data['ob'] = self.owner
                data['hitPos'] = hitPos
                data['hitVec'] = hitNormal

                comp = hitOb['_component']
                if hasattr(comp, 'takeDamage'):
                    comp.takeDamage(data)

        # Destroy the component
        host = bge.logic.netplay
        host.components[self.net_id] = None
        self.owner.endObject()
        table = packer.Table('Destroy')
        table.set('id', self.net_id)
        buff = packer.to_bytes(table)

        host.send_to_clients(buff)

    def update_server(self):
        owner = self.owner
        vec = mathutils.Vector((0.0, 1.0, 0.0))
        vec = vec * owner.worldOrientation.inverted()
        vec = vec + owner.worldPosition

        hitOb, hitPos, hitNormal = owner.rayCast(vec, owner, 65 * bge.logic.game.deltatime)
        now = bge.logic.getFrameTime()

        if hitOb is not None or now > self.timer:
            self.on_hit(hitOb, hitPos, hitNormal)


class RedLaser(Laser):
    obj = 'laser_red'
    setuptable = 'RedLaserSetup'
    particle = 'spark_emitter_red'

    def RedLaserSetup(self, table):
        self.LaserSetup(table)


class BlueLaser(Laser):
    obj = 'laser_blue'
    setuptable = 'BlueLaserSetup'
    particle = 'spark_emitter_plasma'

    def BlueLaserSetup(self, table):
        self.LaserSetup(table)


def timer_explode(self):
    # Apply the damage
    if (not self.hitOb.invalid) and ('_component' in self.hitOb):
        data = {}
        data['damage'] = 1
        if self.owner.invalid:
            data['ob'] = None
        else:
            data['ob'] = self.owner
        data['hitPos'] = self.hitPos
        data['hitVec'] = self.hitNormal

        comp = self.hitOb['_component']
        if hasattr(comp, 'takeDamage'):
            comp.takeDamage(data)

    # Destroy the component
    host = bge.logic.netplay
    host.components[self.net_id] = None
    if not self.owner.invalid:
        self.owner.scene.addObject('needler_explosion', self.owner)
        self.owner.endObject()
    table = packer.Table('Destroy')
    table.set('id', self.net_id)
    buff = packer.to_bytes(table)

    host.send_to_clients(buff)


class NeedlerShot(Laser):
    obj = 'needler_shot'
    setuptable = 'NeedlerShotSetup'
    particle = 'spark_emitter_red'

    def start(self):
        self.target = None

    def NeedlerShotSetup(self, table):
        self.LaserSetup(table)

    def set_target(self, target):
        self.target = target

    def nothing(self):
        pass

    def on_hit(self, hitOb, hitPos, hitNormal):
        if hitOb is not None:
            self.hitOb = hitOb
            self.hitPos = hitPos
            self.hitNormal = hitNormal

            self.owner.setParent(hitOb)
            self.update = self.nothing
            self.update_server = self.nothing
            bge.logic.game.add_timer(1.0, timer_explode, self)

        else:
            # Timed out

            # Make it explode for coolness
            self.owner.scene.addObject('needler_explosion', self.owner)

            # Destroy the component
            host = bge.logic.netplay
            host.components[self.net_id] = None
            self.owner.endObject()
            table = packer.Table('Destroy')
            table.set('id', self.net_id)
            buff = packer.to_bytes(table)

            host.send_to_clients(buff)

    def update(self):
        Laser.update(self)
        target = self.target
        if target is not None and not target.invalid:
            owner = self.owner
            v = owner.getVectTo(target)[1]
            owner.alignAxisToVect(v, 1, 0.1)


class FuelRodShot(Laser):
    obj = 'fuelrod_shot'
    setuptable = 'FuelRodShotSetup'
    particle = 'spark_emitter_alien'

    def start(self):
        self.owner.scaling = (0.5, 0.5, 0.5)

    def start_server(self, args):
        Laser.start_server(self, args)
        self.owner.collisionCallbacks.append(self.collision)

    def collision(self, hitOb, hitPos, hitNormal):
        # Spawn spark particle
        ob = self.owner.scene.addObject(self.particle)
        ob.worldPosition = hitPos

        # Apply the damage
        if '_component' in hitOb:
            data = {}
            data['damage'] = 3
            data['ob'] = self.owner
            data['hitPos'] = hitPos
            data['hitVec'] = hitNormal

            comp = hitOb['_component']
            if hasattr(comp, 'takeDamage'):
                comp.takeDamage(data)

            # Destroy the component
            host = bge.logic.netplay
            host.components[self.net_id] = None
            self.owner.endObject()
            table = packer.Table('Destroy')
            table.set('id', self.net_id)
            buff = packer.to_bytes(table)

            host.send_to_clients(buff)

    def FuelRodShotSetup(self, table):
        self.LaserSetup(table)

    def update(self):
        owner = self.owner
        owner.applyRotation((0.0, 0.1745, 0.0), True)
        owner.applyMovement((0.0, 60.0 * bge.logic.game.deltatime, 0.0), True)

    def update_server(self):
        now = bge.logic.getFrameTime()

        if now > self.timer:
            # Destroy the component
            host = bge.logic.netplay
            host.components[self.net_id] = None
            self.owner.endObject()
            table = packer.Table('Destroy')
            table.set('id', self.net_id)
            buff = packer.to_bytes(table)

            host.send_to_clients(buff)


class AssaultRifle:
    obj = 'weapon-assaultrifle'
    name = 'AssaultRifle'  # There's a better way to pull class name
    primary_delay = 0.5  # Seconds
    shoot = RedLaser

    def __init__(self, user):
        self.user = user
        self.ob = None
        self.primary_next_time = 0.0
        self.melee_delay = 0.5
        self.show()

    def primary(self, vector=None):
        if self.ob is None:
            print ("Can't fire hidden weapon")
            return

        now = bge.logic.getFrameTime()
        if now >= self.primary_next_time:
            self.primary_next_time = now + self.primary_delay

            # TODO - raycast or spawn projectile
            #Laser(None, ref=self.user.barrel)
            #BulletTracer(None, ref=self.ob.children[0])
            speed = self.user.owner.getLinearVelocity(True)[1] + 30.0
            b = self.shoot(None, ref=self.user.barrel, args={'speed': speed, 'vector': vector})
            b.owner.worldPosition = self.ob.children[0].worldPosition
            return True

        return False

    def secondary(self, vector=None):
        now = bge.logic.getFrameTime()
        if now >= self.primary_next_time:
            self.primary_next_time = now + self.melee_delay

            target = None
            if self.user.controlled:
                target = self.user.auto_target['_component']
            else:
                ai = bge.logic.game.ai.getAIController(self.user)
                if hasattr(ai, 'target'):
                    if ai.target is not None:
                        target = ai.target.component

            if target is not None:
                data = {}
                data['damage'] = 2
                if vector is not None:
                    data['hitVec'] = vector

                if hasattr(target, 'takeDamage'):
                    target.takeDamage(data)

            return True

        return False

    def show(self):
        if self.ob is None:
            hand = self.user.righthand
            self.ob = hand.scene.addObject(self.obj, hand)
            self.ob.setParent(hand)

    def hide(self):
        if self.ob is not None:
            self.ob.endObject()
            self.ob = None


class PlasmaRifle(AssaultRifle):
    obj = 'weapon-plasmarifle'
    name = 'PlasmaRifle'
    primary_delay = 0.5
    shoot = BlueLaser


class Needler(AssaultRifle):
    obj = 'weapon-needler'
    name = 'Needler'
    primary_delay = 0.5
    shoot = NeedlerShot

    def primary(self, vector=None):
        if self.ob is None:
            print ("Can't fire hidden weapon")
            return

        now = bge.logic.getFrameTime()
        if now >= self.primary_next_time:
            self.primary_next_time = now + self.primary_delay

            # TODO - raycast or spawn projectile
            #Laser(None, ref=self.user.barrel)
            #BulletTracer(None, ref=self.ob.children[0])
            speed = self.user.owner.getLinearVelocity(True)[1] + 30.0
            b = self.shoot(None, ref=self.user.barrel, args={'speed': speed, 'vector': vector})
            b.owner.worldPosition = self.ob.children[0].worldPosition

            if self.user.controlled:
                b.set_target(self.user.auto_target)
            else:
                ai = bge.logic.game.ai.getAIController(self.user)
                if hasattr(ai, 'target'):
                    try:
                        b.set_target(ai.target.component.owner)
                    except:
                        b.set_target(None)

            return True

        return False


class Sniper(AssaultRifle):
    obj = 'weapon-sniper'
    name = 'Sniper'
    primary_delay = 1.0

    def primary(self, vector=None):
        if self.ob is None:
            print ("Can't fire hidden weapon")
            return

        now = bge.logic.getFrameTime()
        if now >= self.primary_next_time:
            self.primary_next_time = now + self.primary_delay

            barrel = self.user.barrel
            ob = barrel.scene.addObject('sniper_shot', barrel)

            vec = mathutils.Vector((0.0, 1.0, 0.0))
            vec = vec * ob.worldOrientation.inverted()
            vec = vec + ob.worldPosition

            hitOb, hitPos, hitNormal = ob.rayCast(vec, ob, 200.0)
            if hitPos is not None:
                ob.scaling = (1.0, ob.getDistanceTo(hitPos), 1.0)
            else:
                ob.scaling = (1.0, 200.0, 1.0)

            if hitOb is not None:
                if '_component' in hitOb:
                    data = {}
                    data['damage'] = 2
                    data['hitPos'] = hitPos
                    data['hitVec'] = hitNormal

                    comp = hitOb['_component']
                    if hasattr(comp, 'takeDamage'):
                        comp.takeDamage(data)

            return True

        return False


class FuelRod:
    name = 'FuelRod'
    primary_delay = 2.0

    def __init__(self, user):
        self.user = user
        self.ob = None
        self.primary_next_time = 0.0

    def primary(self, vector=None):
        now = bge.logic.getFrameTime()
        if now >= self.primary_next_time:
            self.primary_next_time = now + self.primary_delay
            speed = self.user.owner.getLinearVelocity(True)[1] + 30.0
            FuelRodShot(None, ref=self.user.barrel, args={'speed': speed, 'vector': vector})
            return True
        return False

    def secondary(self, vector=None):
        return False


weapons = {}
weapons['AssaultRifle'] = AssaultRifle
weapons['PlasmaRifle'] = PlasmaRifle
weapons['Needler'] = Needler
weapons['Sniper'] = Sniper
weapons['FuelRod'] = FuelRod