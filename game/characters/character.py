import logging
import math

import bge
import mathutils

from core import Destructable
from collectables.weapons import create_weapon_component


# Base class for all playable characters
class Character(Destructable):
    config = Destructable.config.copy()
    config['hp'] = 1
    config['shield'] = None  # Shield suffix. None, 'energy_shield', 'energy_shield_elite'
    config['parts'] = None
    config['icon'] = None  # Icon is extrapolated from head
    config['team'] = 0
    config['speed'] = 12.0
    config['armature'] = 'minifig-armature'
    config['left_hand'] = 'minifig-lefthand'
    config['right_hand'] = 'minifig-righthand'
    config['shield_ob'] = 'minifig-shield'
    config['default_weapon'] = None

    def __init__(self, owner):
        Destructable.__init__(self, owner)
        if self.config['shield'] is None:
            self.shield = 0
        else:
            self.shield = self.hp

        # Movement / weapons / jump
        self.weapon = None
        self.moving = False
        self.time_since_shooting = 180
        self.loud_timer = 0
        self.auto_target = None  # Used by homing projectiles
        self.target_position = None  # Aim correction
        self.move_vector = mathutils.Vector()
        self.jump_timer = 0
        self.on_ground = 0

        # Set up object references
        config = self.config
        self.armature = owner.children[config['armature']]
        self.left_hand = self.armature.children[config['left_hand']]
        self.right_hand = self.armature.children[config['right_hand']]
        self.shield_ob = self.armature.children[config['shield_ob']]

        if self.config['shield'] is not None:
            self.shield_ob.setVisible(True)
            self.shield_ob.replaceMesh(self.config['shield'])

        # Handle collisions
        owner.collisionCallbacks.append(self.handle_collision)

        # Vehicle stuff
        self.vehicle = None
        self.disabled = False
        self.seat = None
        self.enter_timer = 30

        # Group configuration
        group = owner.groupObject
        assert(group is not None)

        self.team = group.get('team', config['team'])
        self.player_id = group.get('player', None)

        self.input = None  # Reference to a standard input dict

        if self.player_id is not None: # and player ingame:
            self.become_player()
        else:
            self.become_ai()

    def handle_collision(self, other, point, normal):
        if normal[2] < -0.75:
            self.on_ground = 2

    def find_studs(self):
        # TODO - use optimized search
        getDist = self.owner.getDistanceTo
        for stud in bge.logic.core.studs:
            dist = getDist(stud)
            if dist < 5.0:
                scene = bge.logic.getSceneList()[1]
                hud = bge.logic.getSceneList()[1]

                # Add score
                p = bge.logic.core.players[self.player_id]
                p.score += int(stud['value'])

                # Updates HUD
                self.send_event('score', [self.player_id, p.score, stud])

                # Play sound
                #scene.addObject('sound-coin')

                # Limit 1 stud pickup per frame per player
                # Consider adding more delay
                stud.endObject()
                bge.logic.core.studs.remove(stud)
                return

    def apply_damage(self, data):
        assert(not self.dead)
        if self.shield > 0:
            # TODO play shield effect
            pass

        damage = data['damage']
        self.shield -= damage
        if self.shield < 0:
            data['damage'] = abs(self.shield)
            self.shield = 0
            Character.apply_damage(self, data)

        if self.dead:
            # TODO explode
            pass

    def become_player(self):
        p = bge.logic.core.players[self.player_id]
        if p.component is not None:
            p.component.input = None
        p.component = self
        p.active = True
        self.input = p.input

    def become_ai(self):
        pass

    def play_idle(self):
        if self.time_since_shooting < 180:
            if self.time_since_shooting > 20:
                self.armature.playAction('minifig-shoot_standing', 0, 0, play_mode=bge.logic.KX_ACTION_MODE_LOOP, blendin=5)
        else:
            self.armature.playAction('minifig-idle', 0, 95, play_mode=bge.logic.KX_ACTION_MODE_LOOP, blendin=5)

    def play_run_forward(self):
        self.armature.playAction('minifig-battlerun1', 0, 19, play_mode=bge.logic.KX_ACTION_MODE_LOOP, blendin=5)

    def play_shoot_standing(self):
        #if weapon == "AssaultRifle":
        #    self.armature.playAction('minifig-shoot-assaultrifle', 0, 2, play_mode=bge.logic.KX_ACTION_MODE_LOOP, blendin=0, speed=1.0)
        #else:
        self.armature.playAction('minifig-shoot_standing', 0, 10, play_mode=bge.logic.KX_ACTION_MODE_PLAY, blendin=0)

    def play_melee(self):
        self.armature.playAction('minifig-melee', 0, 43)

    def enter_vehicle(self, vehicle):
        pass

    def exit_vehicle(self):
        pass

    def autoaim(self):
        moving = False
        if self.move_vector.length:
            # Do not rotate while moving
            moving = True

        owner = self.owner
        #head = self.head
        #head = self.owner.scene.active_camera.children[0]
        head = self.owner
        # TODO - re-add AI stuff
        #teams = bge.logic.game.ai.teams
        teams = []
        nearest = None
        nearvec = 0.0
        neardist = 0.0

        # TODO - re-add AI stuf
        #ai_stub = bge.logic.game.ai.getAIController(self)

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

    def update_player(self):
        self.find_studs()
        keystate = self.input
        if keystate['primary'] and self.autoaim():
            # Aligning to target
            pass
        else:
            if self.move_vector.length:
                # Using child because I suck at math and don't know how to get
                # global cam rotation that's Y = forward
                cc = self.owner.scene.active_camera.children[0]
                self.owner.alignAxisToVect(self.move_vector * cc.worldOrientation.inverted(), 1, 0.4)
                self.owner.alignAxisToVect((0, 0, 1), 2)

    def update(self):
        owner = self.owner
        assert(not owner.invalid)

        if self.player_id is not None:
            self.update_player()

        scene = owner.scene
        move = mathutils.Vector()

        if self.on_ground:
            self.on_ground -= 1

        if self.jump_timer:
            self.jump_timer -= 1
            if self.jump_timer > 25:
                owner.applyForce((0.0, 0.0, 300.0), False)

        keystate = self.input
        if keystate is not None:
            if keystate['forward']:
                move[1] += 1.0
            if keystate['back']:
                move[1] -= 1.0
            if keystate['left']:
                move[0] -= 1.0
            if keystate['right']:
                move[0] += 1.0

            if keystate['jump']:
                if not self.jump_timer:
                    if self.on_ground:
                        self.jump_timer = 30
                        self.armature.playAction('minifig-jump', 0, 35)
                        scene.addObject('sound-jump')

            if keystate['interact']:
                pass

        # Animate
        if move.length:
            self.moving = True
            if not self.jump_timer:
                self.play_run_forward()
        else:
            self.moving = False
            if not self.jump_timer:
                self.play_idle()

        # Move
        move.normalize()
        self.move_vector = move.copy()

        # Player is rotated to face movement direction. Always move forward.
        if move.length:
            move[1] = 1.0
            move[0] = 0.0

        move = move * self.config['speed']
        # FIXME manually hitting linear velocity is frowned upon
        move[2] = owner.localLinearVelocity[2]
        owner.localLinearVelocity = move

        # Extra gravity
        owner.applyForce((0.0, 0.0, -30.0), False)
