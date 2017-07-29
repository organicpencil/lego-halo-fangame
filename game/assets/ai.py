import logging
import random
import bge
import mathutils
import math
import collections


class AIManager:
    def __init__(self):
        self.next_unit = 0
        self.max_units = 100  # Soft limit
        self.units = [None] * self.max_units

        # Team index for faster searches
        self.teams = []

        self.navmesh = bge.logic.getCurrentScene().objects.get('Navmesh', None)

    def register(self, component, team, aitype=None):
        ai = None
        if type(aitype) is str:
            aitype = eval(aitype)
        elif aitype is None:
            aitype = AI_Stub
        else:
            aitype = AI_Standard

        for i in range(0, self.max_units):
            if self.units[i] is None:
                ai = aitype(self, component, team)
                self.units[i] = ai
                break

            if i == self.max_units - 1:
                logging.warning("Exeeding AI soft cap at %d" % self.max_units)
                ai = aitype(self, component, team)
                self.units.append(ai)
                self.max_units += 1
                break

        # Save to team index
        while team >= len(self.teams):
            self.teams.append([])
        self.teams[team].append(ai)

        return ai

    def unregister(self, component):
        i = 0
        for ai in self.units:
            if ai is not None and ai.component is component:
                ai.setLeader(None)
                self.units[i] = None
                self.teams[ai.team].remove(ai)
                return True
            i += 1

        return False

    def getAIController(self, component):
        for u in self.units:
            if u is not None:
                if u.component is component:
                    return u

        return None

    def update(self, dt):
        # Decide for 1 unit per frame
        n = self.next_unit
        max_units = self.max_units
        units = self.units
        while True:
            u = units[n]
            n += 1
            if u is not None:
                if u.component.hp < 1:
                    # Looks dead
                    self.teams[u.team].remove(u)
                    units[n - 1] = None
                    continue

                elif u.component.owner.invalid:
                    # Object was removed
                    print ("WARNING - object removed without unregistering AI")
                    self.teams[u.team].remove(u)
                    units[n - 1] = None
                    continue

                elif (type(u) is AI_Stub) or (u.component.disabled):
                    # Stub or in vehicle
                    continue

                # Check for pending leader assignment
                if u.leader_is_player and u.leader is None:
                    u._setLeaderPlayer()

                u.state()
                self.next_unit = n
                return

            if n == max_units:
                self.next_unit = 0
                return


def degreesFromVect(vect):
    if vect[1] == 0.0:
        vect[1] = 0.001

    deg = abs(math.atan(vect[0] / vect[1]) * 57.2958)
    if vect[1] < 0.0:
        deg = 180.0 - deg
    return deg


def deadCheck(ai):
    if ai is None:
        return True

    component = ai.component
    if component.hp < 1 or component.owner.invalid:  # or component.disabled:
        return True
    return False


class AI_Stub:
    def __init__(self, manager, component, team):
        self.component = component
        self.team = team
        self.squad = []
        self.leader = None
        self.leader_is_player = False

        self.vision_range = 100.0

    def setLeader(self, leader):
        pass

    def check_los(self, target):
        return AI_Standard.check_los(self, target)


class AI_Standard:
    def __init__(self, manager, component, team):
        self.manager = manager
        self.component = component
        self.team = team

        self.state = self.idle

        self.idle_enemy = self.shoot
        self.idle_nothing = self.idle

        self.shoot_enemy = self.shoot
        self.shoot_nothing = self.pathfind
        self.shoot_dead = self.idle

        self.pathfind_enemy = self.shoot
        self.pathfind_nothing = self.idle
        self.pathfind_dead = self.idle
        self.path = None

        self.leader = None
        self.leader_min_distance = 10.0
        self.leader_max_distance = 20.0
        self.leader_is_player = False

        self.squad = []

        self.target = None
        self.target_last_position = None

        self.vision_angle = 60.0
        self.vision_range = 100.0
        self.hearing_range = 100.0
        self.hearing_footstep_range = 20.0

        # Random delay between shots
        self.reaction_time_min = 0.5
        self.reaction_time_max = 1.5
        self.next_reaction = None

    def setLeader(self, leader):
        if self.leader is not None:
            self.leader.squad.remove(self)
            self.leader = None
            self.leader_is_player = False

        if type(leader) is str:
            # Leader is player. Figure out which.
            # Player death doesn't call setLeader, so leader_is_player should
            # remain true.
            self.leader_is_player = True
            self._setLeaderPlayer()
            return

        self.leader = leader
        if leader is not None:
            leader.squad.append(self)

    def _setLeaderPlayer(self):
        # Follow the player with the least amount of followers
        least_player_ai = None
        least_amount = 0
        for p in bge.logic.players:
            if p is not None:
                if self.team != p.team:
                    logging.warning('Enemies cannot join the player squad')
                    continue

                p_ai = bge.logic.game.ai.getAIController(p)
                if least_player_ai is None or len(p_ai.squad) < least_amount:
                    least_player_ai = p_ai

        if least_player_ai is None:
            # No players exist right now. Will try again later.
            pass
        else:
            self.setLeader(least_player_ai)

    def check_leader_dist(self):
        if deadCheck(self.leader):
            self.leader = None
            return False

        dist = self.component.owner.getDistanceTo(self.leader.component.owner)
        maxdist = self.leader_max_distance

        if self.target is not None:
            # Allow 2x max dist if busy with something
            maxdist *= 2

        if self.leader.component.disabled:
            # Allow even more if leader is in a vehicle
            maxdist *= 2

        if dist > maxdist:
            return True

        return False

    def check_for_enemy(self):
        vision_target = None
        vision_distance = 0.0

        hearing_target = None
        hearing_distance = 0.0

        final_target = None

        owner = self.component.owner
        teams = self.manager.teams
        for i in range(0, len(teams)):
            if i == self.team:
                continue

            team = teams[i]

            for target in team:
                if deadCheck(target):
                    continue

                dist, vec, lvec = owner.getVectTo(target.component.owner)
                if dist < self.vision_range:
                    if degreesFromVect(lvec) <= self.vision_angle:
                        # Check line-of-sight
                        if self.check_los(target):
                            if vision_target is None or dist < vision_distance:
                                vision_target = target
                                vision_distance = dist

                if self.check_hearing(target, dist):
                    if hearing_target is None or dist < hearing_distance:
                        hearing_target = target
                        hearing_distance = dist

        if vision_target is None:
            final_target = hearing_target
        else:
            final_target = vision_target

        if final_target is not None:
            self.target_last_position = final_target.component.owner.worldPosition.copy()
            ## TODO: Save time so things eventually stop chasing?

        return final_target

    def check_hearing(self, target, dist):
        c = target.component
        if dist < self.hearing_range:
            if c.loudtimer or (c.moving and dist < self.hearing_footstep_range):
                return True

        return False

    def check_los(self, target):
        source = self.component.owner
        pos = self.component.owner
        #source = self.component.weapon.barrel
        #pos = self.component.weapon.barrel

        count = 0
        to = target.component.owner
        while count < 5:
            count += 1
            result = source.rayCast(to, pos, self.vision_range)
            hit = result[0]
            if hit is None:
                break

            if 'ignore' in hit:
                source = hit
                pos = result[1]
                continue

            # Hit
            if hit is to:
                return True

            comp = hit.get('_component', None)
            if comp is not None:
                if hasattr(comp, 'takeDamage'):
                    if comp.team != self.team:
                        # Not the target, but still an enemy so fire anyway
                        return True

            break

        return False

    def lookAt(self, other):
        owner = self.component.owner
        dist, vec, lvec = owner.getVectTo(other)
        owner.alignAxisToVect(vec, 1)
        owner.alignAxisToVect((0.0, 0.0, 1.0), 2)
        return lvec[1]

    # ----- States ----- #

    def idle(self):
        if self.leader is not None:
            if self.check_leader_dist():
                self.state = self.pathfind_to_leader
                return

        target = self.check_for_enemy()
        if target is not None:
            self.target = target

            self.state = self.idle_enemy
        else:
            self.state = self.idle_nothing

    def shoot(self):
        self.component.target_position = None
        self.component.setPrimary(False)
        if self.leader is not None:
            if self.check_leader_dist():
                self.target = None
                self.next_reaction = None
                self.state = self.pathfind_to_leader
                return

        if deadCheck(self.target):
            self.target = None
            self.next_reaction = None
            self.state = self.shoot_dead
            return

        # Look for better targets first
        target = self.check_for_enemy()
        # Check LOS again in case we only heard the enemy
        if target is not None and self.check_los(target):
            self.target = target
            # Aim and shoot
            self.lookAt(self.target.component.owner.worldPosition)
            self.component.target_position = target.component.owner.worldPosition.copy()

            now = bge.logic.getFrameTime()
            if self.next_reaction is None:
                self.next_reaction = now + random.uniform(self.reaction_time_min, self.reaction_time_max)
            elif now > self.next_reaction:
                self.next_reaction = now + random.uniform(self.reaction_time_min, self.reaction_time_max)
                self.component.setPrimary(True)
            """
            # Don't fire until mostly facing the target
            v = self.component.owner.getVectTo(target.component.owner)[2]
            if v[1] > 0.5:
                self.component.setPrimary(True)
            """
        else:
            self.next_reaction = None
            self.state = self.shoot_nothing

    def pathfind(self):
        self.component.setForward(False)
        self.component.setRight(False)
        # Check for different target
        target = self.check_for_enemy()
        if target is not None:
            self.target = target
            self.state = self.pathfind_enemy
            return

        owner = self.component.owner

        if deadCheck(self.target):
            self.path = None
            self.target = None
            self.state = self.pathfind_dead
            return

        if self.path is None:
            start = owner.worldPosition
            end = self.target.component.owner.worldPosition
            self.path = self.get_path(start, end)

        if self.path is None:
            # Door in the way or no more points
            self.path = None
            self.component.setForward(False)
            self.target = None
            self.state = self.pathfind_nothing
            return

        # Follow path
        self.path[0][2] = owner.worldPosition[2]
        dist = owner.getDistanceTo(self.path[0])
        while dist < 3.0:
            # Move to the next
            self.path.popleft()
            if not len(self.path):
                if self.target_last_position is not None:
                    self.lookAt(self.target_last_position)
                self.path = None
                self.component.setForward(False)
                self.target = None
                self.state = self.pathfind_nothing
                return
            dist = owner.getDistanceTo(self.path[0])

        # Look at next point and proceed
        vec = self.lookAt(self.path[0])
        if vec < 0.5:
            # Wait until facing before moving
            self.component.setForward(False)
        else:
            self.component.setForward(True)

        # Check if running into someone
        vec = mathutils.Vector()
        vec[1] += 1.0
        vec = vec * owner.worldOrientation.inverted()
        vec += owner.worldPosition
        result = owner.rayCast(vec, owner, 2.5, 'obstacle', 0, 1)
        if result[0] is not None:
            # Push to the right
            self.component.setRight(True)
            self.component.setForward(False)
        else:
            self.component.setRight(False)

    def pathfind_to_leader(self):
        self.component.setForward(False)
        self.component.setRight(False)

        if deadCheck(self.leader):
            self.leader = None
            self.path = None
            self.state = self.idle
            return

        owner = self.component.owner
        dist = owner.getDistanceTo(self.leader.component.owner)

        min_dist = self.leader_min_distance
        if self.leader.component.disabled:
            # Allow more distance if leader is in vehicle
            min_dist *= 2.0

        if dist > min_dist:
            #if self.path is None:
            start = owner.worldPosition
            end = self.leader.component.owner.worldPosition
            self.path = self.get_path(start, end)
        else:
            self.path = None
            self.state = self.idle
            return

        if self.path is None:
            # No path or door in the way
            self.path = None
            self.component.setForward(False)
            self.target = None
            self.state = self.pathfind_nothing
            return

        # Follow path
        self.path[0][2] = owner.worldPosition[2]
        dist = owner.getDistanceTo(self.path[0])
        while dist < 3.0:
            # Move to the next
            self.path.popleft()
            if not len(self.path):
                if self.target_last_position is not None:
                    self.lookAt(self.target_last_position)
                self.path = None
                self.component.setForward(False)
                self.target = None
                self.state = self.pathfind_nothing
                return
            dist = owner.getDistanceTo(self.path[0])

        # Look at next point and proceed
        vec = self.lookAt(self.path[0])
        if vec < 0.5:
            # Wait until facing before moving
            self.component.setForward(False)
        else:
            self.component.setForward(True)

        # Check if running into someone
        vec = mathutils.Vector()
        vec[1] += 1.0
        vec = vec * owner.worldOrientation.inverted()
        vec += owner.worldPosition
        result = owner.rayCast(vec, owner, 2.5, 'obstacle', 0, 1)
        if result[0] is not None:
            # Push to the right
            self.component.setRight(True)
            self.component.setForward(False)
        else:
            self.component.setRight(False)

    def get_path(self, start, end, force=False):
        navmesh = self.manager.navmesh
        if navmesh is None:
            path = collections.deque([end])
        else:
            path = collections.deque(navmesh.findPath(start, end))
            if not len(path):
                if force:
                    path.append(end)
                else:
                    return None

        if force:
            # Don't check for doors when forcing
            return path

        # Check path for doors
        owner = self.component.owner
        p0 = mathutils.Vector(start)
        for i in range(0, len(path)):
            p1 = path[i]
            hitOb = owner.rayCast(p1, p0, 0, 'door', 0, 1)[0]
            if hitOb is not None:
                # Door in the way
                path = None
                break

            p0 = p1

        return path

    # ----- Buttons and stuff ----- #
    def go_to_location(self, location):
        path = self.get_path(self.component.owner.worldPosition, location, force=True)
        # Forced, always returns a path even if it's a bad one
        #if path is None:
        #    # There's a door in the way
        #    return

        self.path = path
        self.component.target_position = None
        self.component.setPrimary(False)
        self.location = location.copy()
        self.location_dist = 3.0
        self.location_finished = self.idle
        self.path_update = False
        self.timed_lerp = False
        self.state = self.pathfind_to_location

    def go_to_button(self, button):
        self.go_to_location(button.worldPosition)
        self.location_finished = self.stay_at_location
        self.timed_lerp = True

    def go_to_vehicle(self, vehicle):
        ob = vehicle.owner
        self.go_to_location(ob.worldPosition)
        self.location = vehicle

        self.path_update = True
        self.path_target = ob
        self.location_dist = 10.0
        self.location_finished = self.get_in_vehicle

    def forget_location(self):
        self.component.setForward(False)
        self.component.setRight(False)
        self.path = None
        self.path_update = False
        self.path_target = None
        self.location = None
        self.location_finished = None
        self.state = self.idle

    def pathfind_to_location(self):
        self.component.setForward(False)
        self.component.setRight(False)

        owner = self.component.owner

        if self.path_update:
            self.path = self.get_path(owner.worldPosition, self.path_target.worldPosition)

        if self.path is None:
            # There's a door in the way
            self.component.setForward(False)
            self.target = None
            self.state = self.idle_nothing
            return

        # Follow path
        self.path[0][2] = owner.worldPosition[2]
        dist = owner.getDistanceTo(self.path[0])
        while dist < self.location_dist:
            # Move to the next
            self.path.popleft()
            if not len(self.path):
                self.path = None
                self.component.setForward(False)
                self.target = None
                self.state = self.location_finished
                if self.timed_lerp:
                    bge.logic.game.add_lerper(owner, self.location, 0.2)
                return
            dist = owner.getDistanceTo(self.path[0])

        # Look at next point and proceed
        vec = self.lookAt(self.path[0])
        if vec < 0.5:
            # Wait until facing before moving
            self.component.setForward(False)
        else:
            self.component.setForward(True)

        # Check if running into someone
        vec = mathutils.Vector()
        vec[1] += 1.0
        vec = vec * owner.worldOrientation.inverted()
        vec += owner.worldPosition
        result = owner.rayCast(vec, owner, 2.5, 'obstacle', 0, 1)
        if result[0] is not None:
            # Push to the right
            self.component.setRight(True)
            self.component.setForward(False)
        else:
            self.component.setRight(False)

    def stay_at_location(self):
        return
        ## TODO: Shoot at stuff without moving
        #owner = self.component.owner
        #self.location[2] = owner.worldPosition[2]
        #owner.worldPosition = owner.worldPosition.lerp(self.location, 0.2)

    def get_in_vehicle(self):
        self.component.enter_timer = 0
        if self.component.enter_vehicle(self.location):
            self.location = None
        else:
            self.forget_location()


class AI_Turret(AI_Standard):
    def __init__(self, manager, component, team):
        AI_Standard.__init__(self, manager, component, team)
        self.shoot_nothing = self.idle

        self.reaction_time_min = 0.0
        self.reaction_time_max = 0.0

    def lookAt(self, other):
        base = self.component.base
        dist, vec, lvec = base.getVectTo(other)
        base.alignAxisToVect(vec, 1, 0.2)
        base.alignAxisToVect((0.0, 0.0, 1.0), 2)

        pitch = self.component.pitch
        dist, vec, lvec = pitch.getVectTo(other)
        pitch.alignAxisToVect(vec, 1, 0.2)
        #pitch.alignAxisToVect((1.0, 0.0, 0.0), 0)

        return lvec[1]