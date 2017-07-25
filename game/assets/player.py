import random
import bge
import mathutils
import utils
import weapons
from netplay import packer, component, bitstring
from stud import DynamicStud, SCORES
from objects import Controllable


class Chief(Controllable):
    obj = 'minifig'
    setuptable = 'ChiefSetup'
    body = 'chief-body'
    parts = 'chief-parts'
    hat = 'chief-helmet'
    team = 0
    hp = 4
    shield = 4

    def start(self):
        Controllable.start(self)

        self.speed = 12.0

        # Combat
        self.weapon = None
        self.moving = False
        self.time_since_shooting = 180
        self.loudtimer = 0
        self.auto_target = None  # Used by homing projectiles
        self.target_position = None  # Aim correction workaround

        if not hasattr(self, 'hp'):
            self.hp = 1
        if self.shield is not None:
            self.shield_max = self.shield
            self.shield_initial_recharge = 3.0
            self.shield_post_recharge = 0.5
            self.next_recharge = None

        self.hp_max = self.hp

        self.setup_object()

        # Vehicle stuff
        self.vehicle = None
        self.disabled = False
        self.seat = None

        # Used to face movement direction
        self.move_vector = mathutils.Vector()

        # Jump
        self.jump_timer = 0
        self.on_ground = 0

    def setup_object(self):
        self.armature = self.owner.children['minifig-armature']

        #self.head = self.owner.children['minifig-cam-center']
        #self.cam_empty = self.head.children['minifig-camera-empty']
        #self.cam = self.cam_empty.children['minifig-camera']

        self.lefthand = self.armature.children['minifig-lefthand']
        self.righthand = self.armature.children['minifig-righthand']
        self.hatempty = self.armature.children['minifig-hat']
        self.barrel = self.owner.children['minifig-barrel']

        default = self.armature.children.get('minifig-default', None)
        # Replace default with correct mesh
        default.replaceMesh(self.body)
        if self.hat is not None:
            hat = self.owner.scene.addObject(self.hat, self.hatempty)
            hat.setParent(self.hatempty)

        if self.body in ['chief-body', 'arbiter-body', 'elite-body']:
            self.shield_ob = self.armature.children['minifig-shield']
            if self.body == 'chief-body':
                self.shield_ob.replaceMesh('energy_shield')
            else:
                self.shield_ob.replaceMesh('energy_shield_elite')
        else:
            try:
                self.armature.children['minifig-shield'].endObject()
            except:
                pass

        """
        # Destroy the extra group mesh if placed in editor
        group = self.owner.groupObject
        if group is not None:
            print ("Shouldn't be happening yet")
            group.groupMembers[self.body].endObject()
            if self.hat is not None:
                group.groupMembers[self.hat].endObject()
        """

    def start_client(self):
        return

    def start_server(self, args):
        self.controlled = 0
        # Start with gun
        if self.weapon is None:
            weps = ["AssaultRifle", "PlasmaRifle", "Needler", "Sniper"]
            self.setWeapon(random.choice(weps))

        self.enter_timer = 30

    def studcollision(self, other, point, normal):
        # Only local players do stud detection
        if 'stud' in other and '_component' in other:
            if len(bge.logic.getSceneList()) == 1:
                # Technically possible to collide with stud on first frame
                return

            # Play the sound
            bge.logic.getCurrentScene().addObject('sound-coin')

            # Remove the stud
            comp = other['_component']

            table = packer.Table('StudCollision')
            table.set('id', self.net_id)
            table.set('stud_id', comp.net_id)

            if bge.logic.netplay.server:
                # Non-dedicated server
                self.StudCollision(table)
            else:
                # Client
                comp.owner.endObject()
                comp.owner = None

                buff = packer.to_bytes(table)
                bge.logic.netplay.send_reliable(buff)

        else:
            # Set ground timer
            if normal[2] < -0.75:
                self.on_ground = 2

    def StudCollision(self, table):
        # Server-only
        stud_id = table.get('stud_id')
        comp = bge.logic.netplay.components[stud_id]
        if comp is not None:
            # Add score
            hud = bge.logic.getSceneList()[1]
            hud.objects['p1_studs']['Text'] += SCORES[comp.owner['stud']]

            # Play pickup effect
            pos = bge.logic.getCurrentScene().active_camera.getVectTo(comp.owner.worldPosition)[2]
            pos = pos * hud.active_camera.worldOrientation.inverted()
            #pos += hud.active_camera.worldPosition
            obj = comp.owner.name.split('-dynamic')[0]
            fake = hud.addObject(obj + '-fake')
            fake.worldPosition = pos
            fake['p'] = '1'
            fake.scaling = [0.2, 0.2, 0.2]

            host = bge.logic.netplay
            host.components[stud_id] = None
            comp.owner.endObject()
            table = packer.Table('Destroy')
            table.set('id', comp.net_id)
            buff = packer.to_bytes(table)

            for client in host.clients:
                if client is not None:
                    client.send_reliable(buff)

    def takeDamage(self, data):
        if self.hp > 0:
            damage = data.get('damage', 0)

            if self.shield is not None:
                # TODO: Reset recharge timer
                self.next_recharge = bge.logic.getFrameTime() + self.shield_initial_recharge

                if self.shield > 0:
                    # TODO: Shield visual effect
                    self.shield_ob['damaged'] = True

                    self.shield -= damage
                    damage = 0
                    if self.shield < 0:
                        damage -= self.shield
                        self.shield = 0

            self.hp -= damage
            if self.hp < 0:
                self.hp = 0

            #if self.controlled:
            if self in bge.logic.players:
                bge.logic.game.refresh_hud()

            if self.hp == 0:
                # Exit vehicle if applicable
                self.enter_timer = 0
                self.exit_vehicle()

                host = bge.logic.netplay
                if host.server:
                    host.components[self.net_id] = None

                    table = packer.Table('Destroy')
                    table.set('id', self.net_id)
                    buff = packer.to_bytes(table)

                    for client in host.clients:
                        if client is not None:
                            client.send_reliable(buff)
                        host = bge.logic.netplay

                    # Spawn parts and end
                    ob = data.get('ob', self.owner)
                    if self.parts is not None:
                        parts = self.owner.scene.addObject(self.parts, self.owner)
                        for c in list(parts.children):
                            c.removeParent()
                            v = ob.getVectTo(c)[1]
                            c.applyForce(v * (random.random() * 1000.0 * damage), False)

                            factor = 1.0
                            if random.random() > 0.5:
                                factor = -1.0
                            v = mathutils.Vector()
                            v[0] = random.random() * 100.0 * factor
                            v[1] = random.random() * 100.0 * factor
                            v[2] = random.random() * 100.0 * factor
                            c.applyTorque(v, False)

                    # Set group properties if applicable
                    if 'group' in self.owner:
                        self.owner['group']['dead'] = True

                    old_ai = bge.logic.game.ai.getAIController(self)
                    squad = list(old_ai.squad)
                    if len(squad):
                        for s in squad:
                            s.setLeader(None)

                    bge.logic.game.ai.unregister(self)

                    #if self.controlled:
                    if self in bge.logic.players:
                        # Drop some studs
                        hud = bge.logic.getSceneList()[1]
                        stud_score = int(hud.objects['p1_studs']['Text'])
                        lost_stud_score = 0
                        for i in range(0, random.randint(2, 5)):
                            args = {}
                            gold = random.random()
                            if gold > 0.75:
                                args['stud_id'] = 1
                            else:
                                args['stud_id'] = 0
                            value = SCORES[args['stud_id']]

                            if value + lost_stud_score <= stud_score:
                                lost_stud_score += value

                                args['pos'] = self.owner.worldPosition
                                args['vel'] = (random.uniform(-5.0, 5.0), random.uniform(-5.0, 5.0), random.uniform(5.0, 7.0))
                                DynamicStud(None, args=args)

                        hud.objects['p1_studs']['Text'] = stud_score - lost_stud_score

                        # Spawn new object first
                        comp = Chief(None, ref=self.owner)
                        comp.setWeapon(self.weapon.name)
                        bge.logic.players[self.controlled - 1] = comp
                        comp.setPlayer(self.controlled)
                        #comp.head.worldOrientation = self.head.worldOrientation
                        #bge.logic.getCurrentScene().active_camera = comp.cam
                        comp.owner.collisionCallbacks.append(comp.studcollision)

                        bge.logic.game.refresh_hud()

                        if self.controlled:
                            new_ai = bge.logic.game.ai.register(comp, self.team, 'AI_Stub')
                        else:
                            new_ai = bge.logic.game.ai.register(comp, self.team, 'AI_Standard')
                            player1_ai = bge.logic.game.ai.getAIController(bge.logic.players[0])
                            new_ai.setLeader(player1_ai)

                            # Get back in vehicle if applicable
                            vehicle = bge.logic.players[0].vehicle
                            if vehicle is not None:
                                self.enter_timer = 0
                                new_ai.go_to_vehicle(vehicle)

                        for s in squad:
                            s.setLeader(new_ai)

                        print ("Player respawned")

                    self.owner.endObject()

                else:
                    None
                    """ Client-side detection
                    table = packer.Table('HitTarget')
                    table.set('id', self.net_id)
                    table.set('target_id', comp.net_id)
                    buff = packer.to_bytes(table)
                    bge.logic.netplay.send_reliable(buff)
                    """

                self.owner.endObject()
                self.owner = None

    def deserialize(self, table):
        get = table.get
        pos = (get('pos_x'), get('pos_y'), get('pos_z'))
        rot = mathutils.Quaternion((get('rot_x'),
                                    get('rot_y'),
                                    get('rot_z'),
                                    get('rot_w')))

        self.owner.worldPosition = pos
        self.owner.worldOrientation = rot

        self.setWeapon(table.get('weapon'))

    def serialize(self):
        table = packer.Table(self.setuptable)
        pos = self.owner.worldPosition
        rot = self.owner.worldOrientation.to_quaternion()

        table.set('id', self.net_id)
        table.set('pos_x', pos[0])
        table.set('pos_y', pos[1])
        table.set('pos_z', pos[2])
        table.set('rot_x', rot[0])
        table.set('rot_y', rot[1])
        table.set('rot_z', rot[2])
        table.set('rot_w', rot[3])
        table.set('input', self.keystate.uint)
        table.set('team', self.team)

        if self.weapon is None:
            table.set('weapon', '')
        else:
            table.set('weapon', self.weapon.name)

        return packer.to_bytes(table)

    def ChiefSetup(self, table):
        self.deserialize(table)

    def setPlayer(self, controlled):
        self.controlled = controlled
        self.owner['player'] = True  # Player prop used for triggers

    def setWeapon(self, weapon):
        if self.weapon is not None:
            self.weapon.hide()
            self.weapon = None

        if weapon is not None:
            self.weapon = weapons.weapons[weapon](self)

        #if bge.logic.netplay.server:
        #    print ("TODO: Forward to clients")

    def ClientState(self, table):
        if not bge.logic.netplay.server and self.permission:
            # Player doesn't care about its own rotation
            return

        self.keystate.uint = table.get('input')
        rot = mathutils.Euler()
        rot[2] = table.get('rot_z')
        self.owner.worldOrientation = rot

        ## Uncomment on for dedicated servers, or something
        #if bge.logic.netplay.server:
        #    # Don't bother interpolating on the server
        #    self.owner.worldPosition = (table.get('pos_x'), table.get('pos_y'), table.get('pos_z'))
        #    return

        # Now interpolate the position...
        # No just set it
        #pos = self.expected_position
        pos = mathutils.Vector()
        pos[0] = table.get('pos_x')
        pos[1] = table.get('pos_y')
        pos[2] = table.get('pos_z')
        self.owner.worldPosition = pos

        ## Doesn't play nice with input-based prediction, remove this
        """
        # Set the velocity.  Client-side prediction is totally broken.
        vel = mathutils.Vector()
        vel[0] = table.get('vel_x')
        vel[1] = table.get('vel_y')
        vel[2] = table.get('vel_z')
        self.owner.setLinearVelocity(vel, False)
        """

    def Destroy(self, table):
        if bge.logic.netplay.server:
            print("Running endobject on the server?")
            return

        """
        # Spawn parts and end
        ob = data.get('ob', self.owner)
        if self.parts is not None:
            parts = self.owner.scene.addObject(self.parts, self.owner)
            for c in list(parts.children):
                c.removeParent()
                v = ob.getVectTo(c)[1]
                c.applyForce(v * (random.random() * 1000.0), False)

                factor = 1.0
                if random.random() > 0.5:
                    factor = -1.0
                v = mathutils.Vector()
                v[0] = random.random() * 100.0 * factor
                v[1] = random.random() * 100.0 * factor
                v[2] = random.random() * 100.0 * factor
                c.applyTorque(v, False)
        """

        self.owner.endObject()
        bge.logic.netplay.components[self.net_id] = None

    def setForward(self, state):
        self.keystate.set(state, (0,))

    def setBackward(self, state):
        self.keystate.set(state, (1,))

    def setLeft(self, state):
        self.keystate.set(state, (2,))

    def setRight(self, state):
        self.keystate.set(state, (3,))

    def setPrimary(self, state):
        self.keystate.set(state, (6,))

    def setSecondary(self, state):
        None

    def update_player_input(self):
        if self.controlled == 1:
            self.set_keyboard_input()
        else:
            self.set_controller_input()
            if not self.controlled:
                return

        # Mouse buttons
        """
        if not self.freeMouse:
            events = bge.logic.mouse.events
            if events[bge.events.LEFTMOUSE] == held:
                self.keystate.set(1, (6,))
            else:
                self.keystate.set(0, (6,))
        """

        # Always do mouselook?  Even in vehicle
        #self.mouseLook()

        if self.disabled:
            return

        #self.mouseLook()

        # Rotate main body if needed
        if self.keystate.int:
            if self.keystate.bin[6] == '1' and self.autoaim():
                # Align to target
                None
            else:
                #self.owner.worldOrientation = self.owner.worldOrientation.lerp(self.head.worldOrientation, 0.2)
                #self.owner.worldOrientation = self.head.worldOrientation
                #self.owner.alignAxisToVect((0, 0, 1), 2)
                if self.move_vector.length:
                    cc = self.owner.scene.active_camera.children[0]
                    #self.owner.worldOrientation = cc.worldOrientation
                    self.owner.alignAxisToVect(self.move_vector * cc.worldOrientation.inverted(), 1, 0.4)
                    self.owner.alignAxisToVect((0, 0, 1), 2)
                pass

        # Prevent camera from clipping through walls
        """
        point = self.head.rayCast(self.cam_empty, self.head, 28.0, 'wall', 0, 1)[1]
        if point is not None:
            vec = mathutils.Vector((0.0, 1.0, 0.0))
            vec = vec * self.head.worldOrientation.inverted()
            self.cam_empty.worldPosition = self.cam_empty.worldPosition.lerp(point + vec, 0.2)
        else:
            vec = mathutils.Vector((0.0, -27.0, 0.0))
            vec = vec * self.head.worldOrientation.inverted()
            self.cam_empty.worldPosition = self.cam_empty.worldPosition.lerp(self.head.worldPosition + vec, 0.2)
        """

        if bge.logic.netplay.server: # Don't send here on non-dedicated servers
            return
        else:
            # Send input state to server
            #bge.logic.netplay.send_to_server(
            pass

    def _permission(self, table):
        component.NetComponent._permission(self, table)
        if self.permission:
            #bge.logic.getCurrentScene().active_camera = self.cam
            bge.render.showMouse(False)
            self.owner.collisionCallbacks.append(self.studcollision)
            self.owner['local'] = True
        else:
            del self.owner['local']
            print("Uhh... which camera to use?")

    def update_client(self):
        if self.disabled:
            return

        #if self.permission:
        #    self.update_player_input()

        ## Predict movement and play animations
        self.move()

        """
        # Predict movement
        self.move()  # TODO - Broken / sending velocity instead.  Address this.

        if self.permission:
            return

        vel = self.owner.getLinearVelocity(False)
        vel = vel * (1.0 / 60.0)
        self.expected_position += vel

        self.owner.worldPosition = self.owner.worldPosition.lerp(self.expected_position, 0.1)
        """

    def move(self):
        owner = self.owner

        # Apply input state
        keys = self.keystate.bin
        move = mathutils.Vector()

        if self.on_ground:
            self.on_ground -= 1

        if self.jump_timer:
            self.jump_timer -= 1
            if self.jump_timer > 25:
                self.owner.applyForce((0.0, 0.0, 300.0), False)

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

        if keys[4] == '1':
            # Jump
            if not self.jump_timer:
                if self.on_ground:
                    self.jump_timer = 30
                    self.armature.playAction('minifig-jump', 0, 35)
                    bge.logic.getCurrentScene().addObject('sound-jump')

        if keys[5] == '1':
            # Interact
            # Check for something
            v = mathutils.Vector((0.0, 1.0, 0.0))
            v = v * owner.worldOrientation.inverted()
            v = v + owner.worldPosition
            hitOb = owner.rayCast(v, owner, 3.0, 'interact')[0]
            if hitOb is not None:
                if self.enter_vehicle(hitOb['vehicle']):
                    return

        # Animation
        if move.length:
            self.moving = True
            # Uncomment to make the body (but not camera) face the movement direction
            #self.armature.alignAxisToVect(move * owner.worldOrientation.inverted(), 1)
            #self.armature.alignAxisToVect((0, 0, 1), 2)
            if not self.jump_timer:
                self.playRunForward()
        else:
            self.moving = False
            if not self.jump_timer:
                self.playIdle()

        move.normalize()
        self.move_vector = move.copy()

        # Player gets rotated instead.  Always move forward.
        if move.length:
            move[1] = 1.0
            move[0] = 0.0

        move = move * self.speed
        move[2] = owner.localLinearVelocity[2]
        owner.localLinearVelocity = move

        # More gravity
        owner.applyForce((0.0, 0.0, -30.0), False)

    def playIdle(self):
        if self.time_since_shooting < 180:
            if self.time_since_shooting > 20:
                self.armature.playAction('minifig-shoot_standing', 0, 0, play_mode=bge.logic.KX_ACTION_MODE_LOOP, blendin=5)
        else:
            self.armature.playAction('minifig-idle', 0, 95, play_mode=bge.logic.KX_ACTION_MODE_LOOP, blendin=5)

    def playRunForward(self):
        self.armature.playAction('minifig-battlerun1', 0, 19, play_mode=bge.logic.KX_ACTION_MODE_LOOP, blendin=5)

    def playShootStanding(self, weapon=None):
        #if weapon == "AssaultRifle":
        #    self.armature.playAction('minifig-shoot-assaultrifle', 0, 2, play_mode=bge.logic.KX_ACTION_MODE_LOOP, blendin=0, speed=1.0)
        #else:
        self.armature.playAction('minifig-shoot_standing', 0, 10, play_mode=bge.logic.KX_ACTION_MODE_PLAY, blendin=0)

    def playMelee(self):
        self.armature.playAction('minifig-melee', 0, 43)

    def autoaim(self):
        moving = False
        if self.move_vector.length:
            # Do not rotate when moving
            moving = True

        owner = self.owner
        #head = self.head
        #head = self.owner.scene.active_camera.children[0]
        head = self.owner
        teams = bge.logic.game.ai.teams
        nearest = None
        nearvec = 0.0
        neardist = 0.0

        ai_stub = bge.logic.game.ai.getAIController(self)

        i = 0
        for team in teams:
            if i != self.team:
                for ai in team:
                    c = ai.component
                    if c.owner is None:
                        continue

                    dist, vec, lvec = head.getVectTo(c.owner)
                    y = lvec[1]
                    if y > 0.5:
                        if nearest is None or (y > nearvec and dist < neardist):
                            if ai_stub.check_los(ai):
                                nearest = c.owner
                                nearvec = y
                                neardist = dist

            i += 1

        self.auto_target = nearest
        if nearest is not None:
            self.target_position = nearest.worldPosition.copy()
            if not moving:
                # Do not rotate when moving
                vec = owner.getVectTo(nearest)[1]
                owner.alignAxisToVect(vec, 1)  #, 0.2)
                owner.alignAxisToVect((0, 0, 1), 2)
                return True
            return False
        else:
            self.target_position = None
            return False

    def enter_vehicle(self, vehicle):
        if self.enter_timer:
            return False

        ai = bge.logic.game.ai.getAIController(self)

        for i in range(0, len(vehicle.passengers)):
            if vehicle.passengers[i] is None:
                self.playIdle()
                vehicle.passengers[i] = self
                self.vehicle = vehicle
                self.passenger_id = i
                self.disabled = True
                self.owner.setParent(vehicle.seats[i])

                self.enter_timer = 30

                for s in ai.squad:
                    s.go_to_vehicle(vehicle)

                self.weapon.hide()

                return True

        return False

    def exit_vehicle(self):
        if self.enter_timer:
            return False

        other = self.owner.parent
        if other is None:
            # Not in vehicle
            return False

        self.enter_timer = 30

        self.vehicle.passengers[self.passenger_id] = None
        self.vehicle = None
        self.passenger_id = None
        self.disabled = False
        self.owner.removeParent()

        v = mathutils.Vector((0.0, 0.0, 1.0))
        self.owner.alignAxisToVect(v, 2)
        self.owner.setAngularVelocity((0.0, 0.0, 0.0))

        pos = mathutils.Vector((-5.0, 0.0, 0.0))
        pos = pos * other.worldOrientation.inverted()
        pos = pos + other.worldPosition
        self.owner.worldPosition = pos

        ai = bge.logic.game.ai.getAIController(self)
        for s in ai.squad:
            s.component.enter_timer = 0
            s.component.exit_vehicle()
            s.forget_location()

        self.weapon.show()

        return True

    def update(self):
        if self.disabled:
            seat = self.vehicle.seats[self.passenger_id]
            if seat is not None:
                owner = self.owner

                owner.worldPosition = owner.worldPosition.lerp(seat.worldPosition, 0.1)
                owner.worldOrientation = owner.worldOrientation.lerp(seat.worldOrientation, 0.1)

                dist = owner.getDistanceTo(seat)
                if dist < 0.1:
                    owner.worldPosition = seat.worldPosition
                    owner.worldOrientation = seat.worldOrientation
                    self.seat = None

    def update_server(self):
        # Shield recharge
        if self.shield is not None:
            if self.next_recharge is not None:
                now = bge.logic.getFrameTime()
                if now > self.next_recharge:
                    if self.shield < self.shield_max:
                        self.shield += 1
                        self.next_recharge = now + self.shield_post_recharge
                        self.shield_ob['damaged'] = False

                        if self in bge.logic.players:
                            bge.logic.game.refresh_hud()
                    else:
                        self.next_recharge = None

        if self.loudtimer:
            self.loudtimer -= 1

        if self.controlled or self in bge.logic.players:
            self.update_player_input()

        if self.enter_timer:
            self.enter_timer -= 1

        if self.disabled:
            return

        self.move()

        if self.controlled:
            # Check if stepping on something important
            v = mathutils.Vector((0.0, 0.0, -1.0))
            v = v + self.owner.worldPosition
            hitOb = self.owner.rayCast(v, self.owner, 2.1, 'step_trigger', 0, 1)[0]
            if hitOb is not None:
                trigger = hitOb['step_trigger']
                if trigger == 'complete':
                    bge.logic.endGame()


        # FIXME - Brute forcing every frame
        table = packer.Table('ClientState')
        table.set('id', self.net_id)
        table.set('input', self.keystate.uint)

        rot = self.owner.worldOrientation.to_euler()
        table.set('rot_z', rot[2])

        pos = self.owner.worldPosition
        table.set('pos_x', pos[0])
        table.set('pos_y', pos[1])
        table.set('pos_z', pos[2])

        # Send
        buff = packer.to_bytes(table)
        net = bge.logic.netplay
        for c in net.clients:
            if c is not None:
                # Non-authoritative, so no need to send to owner
                if c.peer.incomingPeerID not in self.permissions:
                    c.send_reliable(buff)

        keys = self.keystate.bin
        if keys[6] == '1':
            if self.weapon is not None:
                if self.target_position is not None:
                    dist, vec, lvec = self.barrel.getVectTo(self.target_position)
                else:
                    vec = None
                    dist = 100.0

                if dist < 4.5:
                    if self.weapon.secondary(vector=vec):
                        self.time_since_shooting = 0
                        self.loudtimer = 60
                        self.playMelee()

                elif self.weapon.primary(vector=vec):
                    self.time_since_shooting = 0
                    self.loudtimer = 60

                    if not self.moving:
                        self.playShootStanding(self.weapon.name)

        """
        if not self.shoot_timer:
            keys = self.keystate.bin
            if keys[6] == '1':
                weapons.Laser(None, ref=self.barrel)
                self.shoot_timer = self.shoot_timer_reset
                self.time_since_shooting = 0
                self.loudtimer = 60

                if not self.moving:
                    self.playShootStanding()

        else:
            self.shoot_timer -= 1
        """

        self.time_since_shooting += 1


class Marine(Chief):
    obj = 'minifig'
    setuptable = 'MarineSetup'
    body = 'marine-body'
    parts = 'marine-parts'
    hat = None
    team = 0
    hp = 4
    shield = None

    def MarineSetup(self, table):
        self.ChiefSetup(table)


class Arbiter(Chief):
    obj = 'minifig'
    setuptable = 'ArbiterSetup'
    body = 'arbiter-body'
    parts = 'arbiter-parts'
    hat = None
    team = 0
    hp = 4
    shield = 4

    def ArbiterSetup(self, table):
        self.ChiefSetup(table)


class Elite(Chief):
    obj = 'minifig'
    setuptable = 'EliteSetup'
    body = 'elite-body'
    parts = 'elite-parts'
    hat = None
    team = 1
    hp = 1
    shield = 2

    def EliteSetup(self, table):
        self.ChiefSetup(table)


class Johnson(Chief):
    obj = 'minifig'
    setuptable = 'JohnsonSetup'
    body = 'johnson-body'
    parts = 'johnson-parts'
    hat = None
    team = 0
    hp = 1
    shield = None

    def JohnsonSetup(self, table):
        self.ChiefSetup(table)


class Keyes(Chief):
    obj = 'minifig'
    setuptable = 'KeyesSetup'
    body = 'keyes-body'
    parts = 'keyes-parts'
    hat = None
    team = 0
    hp = 1
    shield = None

    def KeyesSetup(self, table):
        self.ChiefSetup(table)


class Bluecrew(Chief):
    obj = 'minifig'
    setuptable = 'BluecrewSetup'
    body = 'bluecrew-body'
    parts = 'bluecrew-parts'
    hat = None
    team = 0
    hp = 1
    shield = None

    def BluecrewSetup(self, table):
        self.ChiefSetup(table)


class Orangecrew(Chief):
    obj = 'minifig'
    setuptable = 'OrangecrewSetup'
    body = 'orangecrew-body'
    parts = 'orangecrew-parts'
    hat = None
    team = 0
    hp = 1
    shield = None

    def OrangecrewSetup(self, table):
        self.ChiefSetup(table)


class Yellowcrew(Chief):
    obj = 'minifig'
    setuptable = 'YellowcrewSetup'
    body = 'yellowcrew-body'
    parts = 'yellowcrew-parts'
    hat = None
    team = 0
    hp = 1
    shield = None

    def YellowcrewSetup(self, table):
        self.ChiefSetup(table)


class Redcrew(Chief):
    obj = 'minifig'
    setuptable = 'RedcrewSetup'
    body = 'redcrew-body'
    parts = 'redcrew-parts'
    hat = None
    team = 0
    hp = 1
    shield = None

    def RedcrewSetup(self, table):
        self.ChiefSetup(table)


class Graycrew(Chief):
    obj = 'minifig'
    setuptable = 'GraycrewSetup'
    body = 'graycrew-body'
    parts = 'graycrew-parts'
    hat = None
    team = 0
    hp = 1
    shield = None

    def GraycrewSetup(self, table):
        self.ChiefSetup(table)


class Grunt(Chief):
    obj = 'grunt'
    setuptable = 'GruntSetup'
    parts = 'grunt-parts'
    team = 1
    hp = 1
    shield = None

    def GruntSetup(self, table):
        self.ChiefSetup(table)

    def setup_object(self):
        self.armature = self.owner.children['grunt-armature']

        #self.head = self.owner.children['grunt-cam-center']
        #self.cam_empty = self.head.children['grunt-camera-empty']
        #self.cam = self.cam_empty.children['grunt-camera']

        self.lefthand = self.armature.children['grunt-lefthand']
        self.righthand = self.armature.children['grunt-righthand']
        self.barrel = self.owner.children['grunt-barrel']

    def playIdle(self):
        self.armature.stopAction()

    def playRunForward(self):
        self.armature.playAction('grunt-walk', 0, 24, play_mode=bge.logic.KX_ACTION_MODE_LOOP, blendin=5)

    def playShootStanding(self, weapon=None):
         return


class Jackal(Grunt):
    obj = 'jackal'
    setuptable = 'JackalSetup'
    parts = 'jackal-parts'
    team = 1
    hp = 1
    shield = 1

    def JackalSetup(self, table):
        self.ChiefSetup(table)

    def setup_object(self):
        self.armature = self.owner.children['jackal-armature']

        #self.head = self.owner.children['jackal-cam-center']
        #self.cam_empty = self.head.children['jackal-camera-empty']
        #self.cam = self.cam_empty.children['jackal-camera']

        self.lefthand = self.armature.children['jackal-lefthand']
        self.righthand = self.armature.children['jackal-righthand']
        self.barrel = self.owner.children['jackal-barrel']
        self.shield_ob = self.armature.children['jackal-shield']

    def takeDamage(self, data):
        ob = data.get('ob', None)
        if ob is not None:
            # Add 1 damage (ignore shield / insta-kill) when hit from behind
            v = self.owner.getVectTo(ob)[2]
            if v[1] < -0.5:
                data['damage'] += 1

        Grunt.takeDamage(self, data)

    def playRunForward(self):
        self.armature.stopAction()

    def playShootStanding(self, weapon=None):
        self.armature.playAction('jackal-shoot', 0, 6, play_mode=bge.logic.KX_ACTION_MODE_PLAY, blendin=0)


class Hunter(Grunt):
    obj = 'hunter'
    setuptable = 'HunterSetup'
    parts = 'hunter-parts'
    team = 1
    hp = 20
    shield = None

    def HunterSetup(self, table):
        self.ChiefSetup(table)

    def setup_object(self):
        self.armature = self.owner.children['hunter-armature']

        #self.head = self.owner.children['hunter-cam-center']
        #self.cam_empty = self.head.children['hunter-camera-empty']
        #self.cam = self.cam_empty.children['hunter-camera']

        self.lefthand = self.armature.children['hunter-lefthand']
        self.righthand = self.armature.children['hunter-righthand']
        self.barrel = self.owner.children['hunter-barrel']

    def takeDamage(self, data):
        ob = data.get('ob', None)
        if ob is not None:
            # Insta-kill when hit from behind
            v = self.owner.getVectTo(ob)[2]
            if v[1] < -0.75:
                data['damage'] = 20

        Grunt.takeDamage(self, data)

    def setWeapon(self, weapon):
        Grunt.setWeapon(self, 'FuelRod')

    def playRunForward(self):
        return

    def playShootStanding(self, weapon=None):
        return


def ensure_player_registered():
    if hasattr(bge.logic, 'player'):
        return True

    objects = bge.logic.getCurrentScene().objects
    for ob in objects:
        group = ob.groupObject
        if group is not None:
            if 'player' in group and 'class' in ob:
                register(ob.controllers[0])
                return True

    return False


def register(cont):
    owner = cont.owner

    if 'init' in owner:
        return
    owner['init'] = 0

    group = owner.groupObject
    if group is None:
        # Spawned dynamically, no need to run this
        del owner['class']
        return

    # Placed in editor. Spawn the full thing and delete this object
    if bge.logic.netplay.server:
        comp = eval(owner['class'])(None, ref=group)
        # But keep the group to preserve custom logic on the server
        comp.owner['group'] = group
        group['owner'] = comp.owner

        if 'weapon' in group:
            comp.setWeapon(group['weapon'])

        if 'team' in group:
            team = group['team']
        else:
            team = getattr(comp, 'team', 2)  # 0 = UNSC, 1 = covenant

        if 'player' in group:
            bge.logic.players.append(comp)
            number = len(bge.logic.players)

            if number == 1:
                # Set as player and register AI stub
                comp.setPlayer(number)
                #bge.logic.getCurrentScene().active_camera = comp.cam
                bge.render.showMouse(False)
                comp.owner.collisionCallbacks.append(comp.studcollision)
                bge.logic.game.ai.register(comp, team, 'AI_Stub')
            else:
                # Anything else becomes AI until pressing start
                ai = bge.logic.game.ai.register(comp, team, 'AI_Standard')
                ai.setLeader(bge.logic.game.ai.getAIController(bge.logic.players[0]))
        else:
            # Register AI-controlled unit
            ai = bge.logic.game.ai.register(comp, team, 'AI_Standard')
            if 'squad' in group:
                # Ensure player was registered
                if ensure_player_registered():
                    ai.setLeader(bge.logic.game.ai.getAIController(bge.logic.players[0]))
                else:
                    print ("No groups with player property")

    for m in list(group.groupMembers):
        m.endObject()

    if not bge.logic.netplay.server:
        group.endObject()