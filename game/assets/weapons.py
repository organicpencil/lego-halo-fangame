import bge
import mathutils


class RedLaserShot:
    particle = 'spark_emitter_red'

    def __init__(self, owner):
        self.owner = owner
        self.timer = bge.logic.getFrameTime() + 4.0
        self.speed = 30.0 + owner.get('deltaspeed', 0.0)

        vector = owner.get('vector', None)
        if vector is not None:
            owner.alignAxisToVect(vector, 1)

    def destroy(self):
        self.owner.endObject()

    def update(self):
        owner = self.owner

        # Move
        owner.applyMovement((0.0, self.speed * bge.logic.game.deltatime, 0.0),
            True)

        # Check for collisions
        vec = mathutils.Vector((0.0, 1.0, 0.0))
        vec = vec * owner.worldOrientation.inverted()
        vec = vec + owner.worldPosition

        hitOb, hitPos, hitNormal = owner.rayCast(vec,
            owner, 65 * bge.logic.game.deltatime)


        if hitOb is not None:
            self.on_hit(hitOb, hitPos, hitNormal)
        else:
            now = bge.logic.getFrameTime()
            if now > self.timer:
                self.destroy()

    def sparks(self, hitPos):
        # Spawn spark particle
        ob = self.owner.scene.addObject(self.particle)
        ob.worldPosition = hitPos
        #ob.scaling = (0.25, 0.25, 0.25)

    def on_hit(self, hitOb, hitPos, hitNormal):
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

        self.destroy()


class BlueLaserShot(RedLaserShot):
    particle = 'spark_emitter_plasma'


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


class NeedlerShot(RedLaserShot):
    particle = 'spark_emitter_red'

    def __init__(self, owner):
        RedLaserShot.__init__(self, owner)
        self.target = owner.get('target', None)

    def nothing(self):
        pass

    def on_hit(self, hitOb, hitPos, hitNormal):
        if hitOb is not None:
            self.hitOb = hitOb
            self.hitPos = hitPos
            self.hitNormal = hitNormal

            self.owner.setParent(hitOb)
            self.update = self.nothing
            bge.logic.game.add_timer(1.0, timer_explode, self)

        else:
            # Timed out

            # Make it explode for coolness
            self.owner.scene.addObject('needler_explosion', self.owner)

    def update(self):
        RedLaserShot.update(self)
        target = self.target
        if target is not None and not target.invalid:
            owner = self.owner
            v = owner.getVectTo(target)[1]
            owner.alignAxisToVect(v, 1, 0.1)


class FuelRodShot(RedLaserShot):
    particle = 'spark_emitter_alien'

    def __init__(self, owner):
        RedLaserShot.__init__(self, owner)
        owner.collisionCallbacks.append(self.collision)
        # Original model was too big, applying scale breaks animation
        owner.scaling = (0.5, 0.5, 0.5)

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

            self.destroy()

    def FuelRodShotSetup(self, table):
        self.LaserSetup(table)

    def update(self):
        owner = self.owner
        owner.applyRotation((0.0, 0.1745, 0.0), True)
        owner.applyMovement((0.0, 60.0 * bge.logic.game.deltatime, 0.0), True)

    def update_server(self):
        now = bge.logic.getFrameTime()

        if now > self.timer:
            self.destroy()


class AssaultRifle:
    obj = 'weapon-assaultrifle'
    name = 'AssaultRifle'  # There's a better way to pull class name
    primary_delay = 0.5  # Seconds
    bullet = 'laser_red'

    def __init__(self, user):
        self.user = user
        self.ob = None
        self.barrel = None
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
            b = self.ob.scene.addObject(self.bullet, self.barrel)
            b.worldPosition = self.ob.children[0].worldPosition
            b['deltaspeed'] = self.user.owner.getLinearVelocity(True)[1]
            if vector is not None:
                b['vector'] = vector
            return True

        return False

    def secondary(self, vector=None):
        now = bge.logic.getFrameTime()
        if now >= self.primary_next_time:
            self.primary_next_time = now + self.melee_delay

            target = None
            if self.user.player_id is not None:
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
            self.barrel = self.ob.children[self.ob.name + '-barrel']

    def hide(self):
        if self.ob is not None:
            self.ob.endObject()
            self.ob = None
            self.barrel = None


class PlasmaRifle(AssaultRifle):
    obj = 'weapon-plasmarifle'
    name = 'PlasmaRifle'
    primary_delay = 0.5
    bullet = 'laser_blue'


class Needler(AssaultRifle):
    obj = 'weapon-needler'
    name = 'Needler'
    primary_delay = 0.5
    bullet = 'needler_shot'

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
            b = self.ob.scene.addObject(self.bullet, self.barrel)
            b.worldPosition = self.ob.children[0].worldPosition
            b['deltaspeed'] = self.user.owner.getLinearVelocity(True)[1]
            b['vector'] = vector

            ## TODO - Fix homing needlers
            """
            if self.user.player_id is not None:
                b.set_target(self.user.auto_target)
            else:
                ai = bge.logic.game.ai.getAIController(self.user)
                if hasattr(ai, 'target'):
                    try:
                        b.set_target(ai.target.component.owner)
                    except:
                        b.set_target(None)

            """
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

            #barrel = self.user.barrel
            barrel = self.barrel
            ob = barrel.scene.addObject('sniper_shot', barrel)

            if vector is not None:
                ob.alignAxisToVect(vector, 1)

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
    # This one's kinda a hack because the weapon model is built into the hunter
    # TODO - Do something about this
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
            b = self.ob.scene.addObject('fuelrod_shot', self.user.barrel)
            b['deltaspeed'] = self.user.owner.getLinearVelocity(True)[1]
            if vector is not None:
                b['vector'] = vector
            return True
        return False

    def secondary(self, vector=None):
        return False


def main(cont):
    owner = cont.owner
    c = owner.get('_component', None)
    if c is None:
        owner['_component'] = COMPONENTS[owner['class']](owner)
    else:
        c.update()


# Could do eval(owner['class'])(owner) instead
# Is code injection a thing we need to worry about?
COMPONENTS = {}
# Projectiles
COMPONENTS['RedLaserShot'] = RedLaserShot
COMPONENTS['BlueLaserShot'] = BlueLaserShot
COMPONENTS['NeedlerShot'] = NeedlerShot
COMPONENTS['FuelRodShot'] = FuelRodShot

# Weapons
weapons = {}
weapons['AssaultRifle'] = AssaultRifle
weapons['PlasmaRifle'] = PlasmaRifle
weapons['Needler'] = Needler
weapons['Sniper'] = Sniper
weapons['FuelRod'] = FuelRod