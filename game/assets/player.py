import logging
import random
import bge
import mathutils
import utils
import weapons
from stud import STUDS, SCORES
from objects import Controllable


class Chief(Controllable):
    icon = 'icon-chief'
    obj = 'minifig'
    setuptable = 'ChiefSetup'
    body = 'chief-body'
    parts = 'chief-parts'
    hat = 'chief-helmet'
    team = 0
    hp = 4
    shield = 4

    def __init__(self, owner):
        Controllable.__init__(self, owner)
        self.player_id = None
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
        self.enter_timer = 30

        # Used to face movement direction
        self.move_vector = mathutils.Vector()

        # Jump
        self.jump_timer = 0
        self.on_ground = 0

        ## Temp - assign a random weapon
        if self.weapon is None:
            weps = ["AssaultRifle", "PlasmaRifle", "Needler", "Sniper"]
            self.set_weapon(random.choice(weps))

        #######################################################################
        ### Group configuration ###############################################
        #######################################################################
        group = owner.groupObject
        if group is None:
            raise ValueError('Minifigs can only be spawned via group instance')

        #self.set_weapon(group.get('weapon', None))
        self.team = group.get('team', self.team)
        self.control_id = group.get('control_id', 0)
        self.player_id = group.get('player', None)

        if self.control_id or self.player_id == 0:
            # Player ID must be uniquely defined in editor
            # 0 = player 1, 1 = player 2, etc
            self.become_player(self.player_id)
        else:
            self.become_ai()

        #######################################################################
        #######################################################################
        #######################################################################

    def setup_object(self):
        # Replace owner
        self.armature = self.owner.children['minifig-armature']

        #self.head = self.owner.children['minifig-cam-center']
        #self.cam_empty = self.head.children['minifig-camera-empty']
        #self.cam = self.cam_empty.children['minifig-camera']

        self.lefthand = self.armature.children['minifig-lefthand']
        self.righthand = self.armature.children['minifig-righthand']
        #self.hatempty = self.armature.children['minifig-hat']

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

        """
        # Destroy the extra group mesh if placed in editor
        group = self.owner.groupObject
        if group is not None:
            print ("Shouldn't be happening yet")
            group.groupMembers[self.body].endObject()
            if self.hat is not None:
                group.groupMembers[self.hat].endObject()
        """

    def studcollision(self, other, point, normal):
        # Only local players do stud detection
        if 'stud' in other:
            if len(bge.logic.getSceneList()) == 1:
                # Technically possible to collide with stud on first frame
                return

            # Play the sound
            bge.logic.getCurrentScene().addObject('sound-coin')

            # Remove the stud
            # Add score
            hud = bge.logic.getSceneList()[1]
            hud.objects['p1_studs']['Text'] += SCORES[other['stud']]

            # Play pickup effect
            pos = bge.logic.getCurrentScene().active_camera.getVectTo(other.worldPosition)[2]
            pos = pos * hud.active_camera.worldOrientation.inverted()
            #pos += hud.active_camera.worldPosition
            obj = other.name.split('-dynamic')[0]
            fake = hud.addObject(obj + '-fake')
            fake.worldPosition = pos
            fake['p'] = '1'
            fake.scaling = [0.2, 0.2, 0.2]
            hud.objects['p1_studcolor'].replaceMesh(obj)

            other.endObject()
            # Workaround for delayed endObject bug
            del other['stud']

        else:
            # Set ground timer
            if normal[2] < -0.75:
                self.on_ground = 2

    def takeDamage(self, data):
        if self.hp > 0:
            owner = self.owner
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

            if self.player_id is not None:
                bge.logic.game.refresh_hud()

            if self.hp == 0:
                # Exit vehicle if applicable
                self.enter_timer = 0
                self.exit_vehicle()

                # Spawn parts and end
                ob = data.get('ob', self.owner)
                if self.parts is not None:
                    parts = owner.scene.addObject(self.parts, owner)
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
                    # There should always be a group object now that networking
                    # has been nuked. Only delete if the group has no props.
                    ## TODO - Also check for logic bricks before deleting
                    group = owner.groupObject
                    if len(group.getPropertyNames()):
                        group['dead'] = True
                    else:
                        group.endObject()

                    if self.player_id is None:
                        # Only do AI squads here.
                        # Player squads will wait for respawn instead
                        old_ai = bge.logic.game.ai.getAIController(self)
                        squad = list(old_ai.squad)
                        if len(squad):
                            for s in squad:
                                s.setLeader(None)

                    ## TODO - Unregister should be doing setLeader(None)
                    bge.logic.game.ai.unregister(self)

                    if self.player_id is not None:
                        if self.player_id == 0 or self.control_id:
                            # Drop some of the player's studs
                            hud = bge.logic.getSceneList()[1]
                            stud_score = int(hud.objects['p' + str(self.player_id + 1) + '_studs']['Text'])
                            lost_stud_score = 0
                            # Drops between 2 - 5 studs with 25% chance of dropping gold
                            for i in range(0, random.randint(2, 5)):
                                gold = random.random()
                                if gold > 0.75:
                                    stud_id = 1
                                else:
                                    stud_id = 0

                                value = SCORES[stud_id]

                                if value + lost_stud_score <= stud_score:
                                    lost_stud_score += value

                                    stud = owner.scene.addObject(STUDS[stud_id] + '-dynamic')
                                    stud.worldPosition = owner.worldPosition
                                    stud.setLinearVelocity((random.uniform(-5.0, 5.0), random.uniform(-5.0, 5.0), random.uniform(5.0, 7.0)))

                                    hud.objects['p1_studs']['Text'] = stud_score - lost_stud_score

                            bge.logic.players[self.player_id] = None

                        # Respawn
                        ## TODO - Delay this a few seconds
                        new = owner.scene.addObject(type(self).__name__, owner)

                        # New object is a group instance. Copy the properties.
                        new['player'] = self.player_id
                        new['weapon'] = type(self.weapon).__name__
                        new['team'] = self.team
                        new['control_id'] = self.control_id

                        # Rather than automatically re-entering the vehicle,
                        # lets give vehicles their own hitpoints and make riders
                        # invulnerable while mounted.

                        ## TODO
                        # Former squad members need to become followers again
                        # Add this when I get the delay thing figured out
                        # No longer necessary. They figure this out on their
                        # own.
                        #for s in squad:
                        #    s.setLeader('player')

                    elif self.team != 0:
                        # Drop random loot (studs, heart, weapon, shield?)
                        pass

                self.owner['_invalid'] = 0
                self.owner.endObject()

    def become_player(self, player_id):
        if not None in bge.logic.players:
            logging.warning('Max players already reached')
            return

        if bge.logic.players[player_id] is not None:
            raise ValueError('Player slot in use')

        ## TODO - Set control ID
        self.player_id = player_id
        self.owner['is_player'] = True  # Prop used for player-only triggers
        bge.logic.players[player_id] = self

        # Allow picking up studs
        self.owner.collisionCallbacks.append(self.studcollision)

        # Unregister AI if applicable (returns False if not applicable)
        bge.logic.game.ai.unregister(self)

        # Register AI stub
        bge.logic.game.ai.register(self, self.team, 'AI_Stub')

        bge.logic.game.refresh_hud()

    def become_ai(self):
        owner = self.owner
        if 'is_player' in owner:
            # Previously a player. Keep the ID in case it rejoins.
            bge.logic.players[self.player_id] = None

            # Stop picking up studs
            self.owner.collisionCallbacks.remove(self.studcollision)
            del owner['is_player']

            # Unregister AI stub
            bge.logic.game.ai.unregister(self)
        else:
            # Throw warning if already an AI
            if bge.logic.game.ai.unregister(self):
                logging.warning("AI was already registered")

        # Now register the AI
        bge.logic.game.ai.register(self, self.team, 'AI_Standard')

        # Set as a squad follower if applicable
        if 'player' in owner.groupObject or 'squad' in owner.groupObject:
            self.become_follower()

        #ai.setLeader(bge.logic.game.ai.getAIController(bge.logic.players[0]))

    def become_follower(self):
        # Assuming it's already an AI-controlled unit
        ai = bge.logic.game.ai.getAIController(self)
        ai.setLeader('player')

    def set_weapon(self, weapon):
        if self.weapon is not None:
            self.weapon.hide()
            self.weapon = None

        if weapon is not None:
            self.weapon = weapons.weapons[weapon](self)

        #if bge.logic.netplay.server:
        #    print ("TODO: Forward to clients")

    # See takeDamage instead
    #def destroy(self):
    #    self.owner.endObject()

    ## TODO - Get rid of these. Keeping for now because AI uses it.
    def setForward(self, state):
        self.keystate['forward'] = bool(state)

    def setBackward(self, state):
        self.keystate['back'] = bool(state)

    def setLeft(self, state):
        self.keystate['left'] = bool(state)

    def setRight(self, state):
        self.keystate['right'] = bool(state)

    def setPrimary(self, state):
        self.keystate['shoot'] = bool(state)

    def setSecondary(self, state):
        None

    def update_player_input(self):
        if self.player_id == 0:
            self.set_keyboard_input()
        elif self.player_id > 0:
            self.set_controller_input()
            if not self.control_id:
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
        keystate = self.keystate
        if True in list(keystate.values()):
            if keystate['shoot'] and self.autoaim():
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

    def move(self):
        owner = self.owner

        # Apply input state
        keystate = self.keystate
        move = mathutils.Vector()

        if self.on_ground:
            self.on_ground -= 1

        if self.jump_timer:
            self.jump_timer -= 1
            if self.jump_timer > 25:
                self.owner.applyForce((0.0, 0.0, 300.0), False)

        if keystate['forward']:
            # Forward
            move[1] += 1.0
        if keystate['back']:
            # Back
            move[1] -= 1.0
        if keystate['left']:
            # Left
            move[0] -= 1.0
        if keystate['right']:
            # Right
            move[0] += 1.0

        if keystate['jump']:
            # Jump
            if not self.jump_timer:
                if self.on_ground:
                    self.jump_timer = 30
                    self.armature.playAction('minifig-jump', 0, 35)
                    bge.logic.getCurrentScene().addObject('sound-jump')

        if keystate['interact']:
            # Interact
            # Check for something
            # TODO: Refactor this bit of code. Doesn't always work.
            v = mathutils.Vector((0.0, 1.0, 0.0))
            v = v * owner.worldOrientation.inverted()
            v = v + owner.worldPosition
            hitOb = owner.rayCast(v, owner, 3.0, 'interact')[0]
            if hitOb is not None:
                if self.enter_vehicle(hitOb['vehicle']):
                    return

            # Check for nearby buildables (slooooow)
            for ob in bge.logic.getCurrentScene().objects:
                if 'buildable' in ob:
                    dist = owner.getDistanceTo(ob)
                    if dist < 10.0:
                        ob['buildable'].build = True
                        # TODO: Play build animation

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
        # Workaround to delayed endObject bug
        if '_invalid' in self.owner:
            self.owner['_invalid'] += 1
            logging.warning('Previously called endObject() on {} at {}. So far {} extra logic tic(s)'.format(self.owner.name, self.owner.worldPosition, self.owner['_invalid']))
            return

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

        if self.player_id is not None:
            self.update_player_input()

        if self.enter_timer:
            self.enter_timer -= 1

        if self.disabled:
            return

        self.move()

        if self.player_id is not None:
            # Check if stepping on something important
            v = mathutils.Vector((0.0, 0.0, -1.0))
            v = v + self.owner.worldPosition
            hitOb = self.owner.rayCast(v, self.owner, 2.1, 'step_trigger', 0, 1)[0]
            if hitOb is not None:
                trigger = hitOb['step_trigger']
                if trigger == 'complete':
                    bge.logic.endGame()


        keystate = self.keystate
        if keystate['shoot']:
            if self.weapon is not None:
                if self.target_position is not None:
                    dist, vec, lvec = self.weapon.barrel.getVectTo(self.target_position)
                else:
                    vec = None
                    dist = 100.0

                melee_dist = self.owner.getDistanceTo(self.weapon.barrel)

                if dist < melee_dist:
                    if self.weapon.secondary(vector=vec):
                        self.time_since_shooting = 0
                        self.loudtimer = 60
                        self.playMelee()

                elif self.weapon.primary(vector=vec):
                    self.time_since_shooting = 0
                    self.loudtimer = 60

                    if not self.moving:
                        self.playShootStanding(self.weapon.name)

        self.time_since_shooting += 1


class Marine(Chief):
    icon = 'icon-marine'
    obj = 'minifig'
    setuptable = 'MarineSetup'
    body = 'marine-body'
    parts = 'marine-parts'
    hat = None
    team = 0
    hp = 4
    shield = None


class Arbiter(Chief):
    icon = 'icon-arbiter'
    obj = 'minifig'
    setuptable = 'ArbiterSetup'
    body = 'arbiter-body'
    parts = 'arbiter-parts'
    hat = None
    team = 0
    hp = 4
    shield = 4


class Elite(Chief):
    icon = 'icon-elite'
    obj = 'minifig'
    setuptable = 'EliteSetup'
    body = 'elite-body'
    parts = 'elite-parts'
    hat = None
    team = 1
    hp = 1
    shield = 2


class Johnson(Chief):
    icon = 'icon-johnson'
    obj = 'minifig'
    setuptable = 'JohnsonSetup'
    body = 'johnson-body'
    parts = 'johnson-parts'
    hat = None
    team = 0
    hp = 1
    shield = None


class Keyes(Chief):
    icon = 'icon-keyes'
    obj = 'minifig'
    setuptable = 'KeyesSetup'
    body = 'keyes-body'
    parts = 'keyes-parts'
    hat = None
    team = 0
    hp = 1
    shield = None


class Bluecrew(Chief):
    icon = 'icon-crew'
    obj = 'minifig'
    setuptable = 'BluecrewSetup'
    body = 'bluecrew-body'
    parts = 'bluecrew-parts'
    hat = None
    team = 0
    hp = 1
    shield = None


class Orangecrew(Chief):
    icon = 'icon-crew'
    obj = 'minifig'
    setuptable = 'OrangecrewSetup'
    body = 'orangecrew-body'
    parts = 'orangecrew-parts'
    hat = None
    team = 0
    hp = 1
    shield = None


class Yellowcrew(Chief):
    icon = 'icon-crew'
    obj = 'minifig'
    setuptable = 'YellowcrewSetup'
    body = 'yellowcrew-body'
    parts = 'yellowcrew-parts'
    hat = None
    team = 0
    hp = 1
    shield = None


class Redcrew(Chief):
    icon = 'icon-crew'
    obj = 'minifig'
    setuptable = 'RedcrewSetup'
    body = 'redcrew-body'
    parts = 'redcrew-parts'
    hat = None
    team = 0
    hp = 1
    shield = None


class Graycrew(Chief):
    icon = 'icon-crew'
    obj = 'minifig'
    setuptable = 'GraycrewSetup'
    body = 'graycrew-body'
    parts = 'graycrew-parts'
    hat = None
    team = 0
    hp = 1
    shield = None


class Grunt(Chief):
    icon = 'icon-grunt'
    obj = 'grunt'
    setuptable = 'GruntSetup'
    parts = 'grunt-parts'
    team = 1
    hp = 1
    shield = None

    def setup_object(self):
        self.armature = self.owner.children['grunt-armature']

        #self.head = self.owner.children['grunt-cam-center']
        #self.cam_empty = self.head.children['grunt-camera-empty']
        #self.cam = self.cam_empty.children['grunt-camera']

        self.lefthand = self.armature.children['grunt-lefthand']
        self.righthand = self.armature.children['grunt-righthand']

    def playIdle(self):
        self.armature.stopAction()

    def playRunForward(self):
        self.armature.playAction('grunt-walk', 0, 24, play_mode=bge.logic.KX_ACTION_MODE_LOOP, blendin=5)

    def playShootStanding(self, weapon=None):
         return


class Jackal(Grunt):
    icon = 'icon-jackal'
    obj = 'jackal'
    setuptable = 'JackalSetup'
    parts = 'jackal-parts'
    team = 1
    hp = 1
    shield = 1

    def setup_object(self):
        self.armature = self.owner.children['jackal-armature']

        #self.head = self.owner.children['jackal-cam-center']
        #self.cam_empty = self.head.children['jackal-camera-empty']
        #self.cam = self.cam_empty.children['jackal-camera']

        self.lefthand = self.armature.children['jackal-lefthand']
        self.righthand = self.armature.children['jackal-righthand']
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
    icon = 'icon-hunter'
    obj = 'hunter'
    setuptable = 'HunterSetup'
    parts = 'hunter-parts'
    team = 1
    hp = 20
    shield = None

    def setup_object(self):
        self.armature = self.owner.children['hunter-armature']

        #self.head = self.owner.children['hunter-cam-center']
        #self.cam_empty = self.head.children['hunter-camera-empty']
        #self.cam = self.cam_empty.children['hunter-camera']

        self.lefthand = self.armature.children['hunter-lefthand']
        self.righthand = self.armature.children['hunter-righthand']

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


def main(cont):
    parent = cont.owner.parent.parent
    c = parent.get('_component', None)
    if c is None:
        parent['_component'] = COMPONENTS[cont.owner['class']](parent)
    else:
        c.update()


def grunt_main(cont):
    owner = cont.owner
    c = owner.get('_component', None)
    if c is None:
        owner['_component'] = COMPONENTS[owner['class']](owner)
    else:
        c.update()

# Could do eval(owner['class'])(owner) instead
# Is code injection a thing we need to worry about?
COMPONENTS = {}
COMPONENTS['Chief'] = Chief
COMPONENTS['Marine'] = Marine
COMPONENTS['Arbiter'] = Arbiter
COMPONENTS['Elite'] = Elite
COMPONENTS['Johnson'] = Johnson
COMPONENTS['Keyes'] = Keyes
COMPONENTS['Bluecrew'] = Bluecrew
COMPONENTS['Orangecrew'] = Orangecrew
COMPONENTS['Yellowcrew'] = Yellowcrew
COMPONENTS['Redcrew'] = Redcrew
COMPONENTS['Graycrew'] = Graycrew
COMPONENTS['Grunt'] = Grunt
COMPONENTS['Jackal'] = Jackal
COMPONENTS['Hunter'] = Hunter
