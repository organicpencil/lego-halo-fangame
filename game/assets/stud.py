import bge
import mathutils
import utils
from netplay import packer, component

STUDS = ['stud-silver', 'stud-gold', 'stud-blue', 'stud-purple', 'stud-shinypurple']
SCORES = [10, 100, 1000, 10000, 100000]


class Stud(component.GameObject):
    obj = None
    setuptable = 'StudSetup'

    def start_client(self):
        return

    def start_server(self, args):
        self.stud_id = args['stud_id']

        scene = bge.logic.getCurrentScene()
        self.owner = scene.addObject(STUDS[self.stud_id])
        self.owner['_component'] = self
        self.owner.worldPosition = args['pos']

    def StudSetup(self, table):
        self.deserialize(table)

    def deserialize(self, table):
        get = table.get

        self.stud_id = table.get('stud_id')
        obj = STUDS[self.stud_id]
        self.owner = owner = bge.logic.getCurrentScene().addObject(obj)
        owner.worldPosition = (get('pos_x'), get('pos_y'), get('pos_z'))

    def serialize(self):
        table = packer.Table(self.setuptable)
        pos = self.owner.worldPosition

        table.set('id', self.net_id)
        table.set('stud_id', self.stud_id)
        table.set('pos_x', pos[0])
        table.set('pos_y', pos[1])
        table.set('pos_z', pos[2])

        return packer.to_bytes(table)

    def Destroy(self, table):
        if bge.logic.netplay.server:
            print("Running endobject on the server?")
            return

        if self.owner is not None:  # Will not exist when detected locally
            self.owner.endObject()

        bge.logic.netplay.components[self.net_id] = None


class DynamicStud(Stud):
    obj = None
    setuptable = 'DynamicStudSetup'

    def start_server(self, args):
        self.stud_id = args['stud_id']

        scene = bge.logic.getCurrentScene()
        self.owner = scene.addObject(STUDS[self.stud_id] + '-dynamic')
        self.owner['_component'] = self
        self.owner.worldPosition = args['pos']
        vel = args['vel']
        self.owner.setLinearVelocity(vel, False)

        vec = mathutils.Vector((vel[0], vel[1], vel[2]))
        self.owner.applyMovement(vec * 0.5, False)

    def DynamicStudSetup(self, table):
        self.StudSetup(table)
        get = table.get
        self.owner.setLinearVelocity(get('vel_x'), get('vel_y'), get('vel_z'), False)

    def serialize(self):
        table = packer.Table(self.setuptable)
        pos = self.owner.worldPosition
        vel = self.owner.getLinearVelocity(False)

        table.set('id', self.net_id)
        table.set('stud_id', self.stud_id)
        table.set('pos_x', pos[0])
        table.set('pos_y', pos[1])
        table.set('pos_z', pos[2])
        table.set('vel_x', vel[0])
        table.set('vel_y', vel[1])
        table.set('vel_z', vel[2])

        return packer.to_bytes(table)


def register(cont):
    owner = cont.owner
    group = owner.groupObject
    if group is None:
        # Spawned dynamically, no need to run this
        return

    # Placed in editor. Spawn the full thing and delete this object
    if bge.logic.netplay.server:
        args = {}
        args['stud_id'] = owner['stud']
        args['pos'] = owner.worldPosition
        Stud(None, ref=None, args=args)

    for m in list(group.groupMembers):
        m.endObject()
    group.endObject()


def fake(cont):
    owner = cont.owner
    p = bge.logic.getCurrentScene().objects['stud-counter' + owner['p']]
    owner.worldPosition = owner.worldPosition.lerp(p.worldPosition, 0.05)
    if owner.getDistanceTo(p) < 0.1:
        owner.endObject()