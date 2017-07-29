import bge
import utils


def fade(cont):
    owner = cont.owner
    owner.color[3] -= 0.03
    if owner.color[3] <= 0.01:
        owner.endObject()


def sensors(cont):
    for sens in cont.sensors:
        if not sens.positive:
            return False

    return True


def get_hit_objects(cont):
    objects = []
    for sens in cont.sensors:
        if hasattr(sens, 'hitObjectList'):
            for ob in sens.hitObjectList:
                objects.append(ob)

    return objects


## Collision / ray sensor scripts
def killother(cont):
    if not sensors(cont):
        return

    objects = get_hit_objects(cont)
    for ob in objects:
        # Apply the damage
        if '_component' in ob:
            comp = ob['_component']
            if hasattr(comp, 'takeDamage'):
                data = {}
                data['damage'] = 99999
                comp.takeDamage(data)


def damageother(cont):
    if not sensors(cont):
        return

    objects = get_hit_objects(cont)
    for ob in objects:
        # Apply the damage
        if '_component' in ob:
            comp = ob['_component']
            if hasattr(comp, 'takeDamage'):
                data = {}
                data['damage'] = cont.owner.get('damage', 1)
                comp.takeDamage(data)


def teleportother(cont):
    if not sensors(cont):
        return

    owner = cont.owner
    target = owner.scene.objects[owner['teleport']]

    objects = get_hit_objects(cont)
    for ob in objects:
        if ob.parent is None:
            ob.worldPosition = target.worldPosition
            ob.worldOrientation = target.worldOrientation


## Minifig or similar entity scripts
def kill(cont):
    if not sensors(cont):
        return

    ob = cont.owner['owner']
    if ob is not None:
        comp = ob['_component']
        if hasattr(comp, 'takeDamage'):
            data = {}
            data['damage'] = 99999
            comp.takeDamage(data)


def damage(cont):
    if not sensors(cont):
        return

    ob = cont.owner['owner']
    if ob is not None:
        comp = ob['_component']
        if hasattr(comp, 'takeDamage'):
            data = {}
            data['damage'] = cont.owner.get('damage', 1)
            comp.takeDamage(data)


def teleport(cont):
    if not sensors(cont):
        return

    owner = cont.owner
    target = owner.scene.objects[owner['teleport']]

    for ob in owner.groupMembers:
        if ob.parent is None:
            ob.worldPosition = target.worldPosition
            ob.worldOrientation = target.worldOrientation


## AI scripts
def squadjoin(cont):
    if not sensors(cont):
        return

    ob = cont.owner['owner']
    if ob is not None:
        getAIController = bge.logic.game.ai.getAIController
        ai = getAIController(ob['_component'])
        ai.setLeader(getAIController(bge.logic.players[0]))


def squadleave(cont):
    if not sensors(cont):
        return

    ob = cont.owner['owner']
    if ob is not None:
        bge.logic.game.ai.getAIController(ob['_component']).setLeader(None)


def goto(cont):
    if not sensors(cont):
        return

    ob = cont.owner['owner']
    if ob is not None:
        target = ob.scene.objects[cont.owner['goto']]
        ai = bge.logic.game.ai.getAIController(ob['_component'])
        ai.go_to_location(target.worldPosition)


def vehicleenter(cont):
    if not sensors(cont):
        return

    ob = cont.owner['owner']
    if ob is not None:
        target = ob.scene.objects[cont.owner['vehicle']]
        print ("NOT IMPLEMENTED")
        return
        #vehicle = get_instance_owner(target)
        if vehicle is not None:
            ai = bge.logic.game.ai.getAIController(ob['_component'])
            ai.go_to_vehicle(vehicle)


def vehicleexit(cont):
    if not sensors(cont):
        return

    ob = cont.owner['owner']
    if ob is not None:
        ob['_component'].enter_timer = 0
        ob['_component'].exit_vehicle()


def dooropen(cont):
    if not sensors(cont):
        return

    cont.owner['open'] = True

    for ob in cont.owner.groupMembers:
        if 'open' in ob:
            ob['open'] = True


## Global scripts
def win(cont):
    pass


## Camera
def transition(cont):
    return
    # Transition camera to owner position
    if not sensors(cont):
        return

    # Assuming there's a collision sensor attached.  Can change later if needed.
    # Also needs to be a controlled player
    objects = get_hit_objects(cont)
    for ob in objects:
        comp = ob.get('_component', None)
        if comp is not None:
            if comp.controlled:
                followcam = bge.logic.followcam
                followcam.last_target[comp.controlled - 1] = cont.owner
                if (not bge.logic.players[1].controlled) or (followcam.last_target[0] == followcam.last_target[1]):
                    followcam.target.worldPosition = cont.owner.worldPosition
                    followcam.cam['move'] = True