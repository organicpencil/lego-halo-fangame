import bge
from netplay import packer
from netplay.host import ServerHost
from assets import player, stud, weapons


def define():
    if 'tables' in bge.logic.globalDict:
        return
    bge.logic.globalDict['tables'] = 0

    # Standard humanoids
    tabledef = packer.TableDef('ChiefSetup')
    tabledef.define('uint16', 'id')
    tabledef.define('float', 'pos_x')
    tabledef.define('float', 'pos_y')
    tabledef.define('float', 'pos_z')
    tabledef.define('float', 'rot_x')
    tabledef.define('float', 'rot_y')
    tabledef.define('float', 'rot_z')
    tabledef.define('float', 'rot_w')
    tabledef.define('uint8', 'input', 0)
    tabledef.define('uint8', 'team')
    tabledef.define('json', 'weapon', '')
    tabledef.component = player.Chief

    tabledef = packer.TableDef('MarineSetup', template=tabledef)
    tabledef.component = player.Marine

    tabledef = packer.TableDef('ArbiterSetup', template=tabledef)
    tabledef.component = player.Arbiter

    tabledef = packer.TableDef('EliteSetup', template=tabledef)
    tabledef.component = player.Elite

    tabledef = packer.TableDef('JohnsonSetup', template=tabledef)
    tabledef.component = player.Johnson

    tabledef = packer.TableDef('KeyesSetup', template=tabledef)
    tabledef.component = player.Keyes

    tabledef = packer.TableDef('BluecrewSetup', template=tabledef)
    tabledef.component = player.Bluecrew

    tabledef = packer.TableDef('OrangecrewSetup', template=tabledef)
    tabledef.component = player.Orangecrew

    tabledef = packer.TableDef('YellowcrewSetup', template=tabledef)
    tabledef.component = player.Yellowcrew

    tabledef = packer.TableDef('RedcrewSetup', template=tabledef)
    tabledef.component = player.Redcrew

    tabledef = packer.TableDef('GraycrewSetup', template=tabledef)
    tabledef.component = player.Graycrew

    tabledef = packer.TableDef('GruntSetup', template=tabledef)
    tabledef.component = player.Grunt

    tabledef = packer.TableDef('JackalSetup', template=tabledef)
    tabledef.component = player.Jackal

    tabledef = packer.TableDef('HunterSetup', template=tabledef)
    tabledef.component = player.Hunter

    tabledef = packer.TableDef('ClientInput')
    tabledef.define('uint16', 'id')
    tabledef.define('uint8', 'input', 0)

    tabledef = packer.TableDef('ClientState')
    tabledef.define('uint16', 'id')
    tabledef.define('uint8', 'input', 0)
    tabledef.define('float', 'rot_z')
    tabledef.define('float', 'pos_x')
    tabledef.define('float', 'pos_y')
    tabledef.define('float', 'pos_z')

    tabledef = packer.TableDef('ChangeWeapon')
    tabledef.define('uint16', 'id')
    tabledef.define('json', 'weapon')

    tabledef = packer.TableDef('TargetShoot')
    tabledef.define('uint16', 'id')
    tabledef.define('uint16', 'target_id')

    # There should probably be a built-in means of destroying components
    tabledef = packer.TableDef('Destroy')
    tabledef.define('uint16', 'id')

    tabledef = packer.TableDef('LaserSetup')
    tabledef.define('uint16', 'id')
    tabledef.define('float', 'pos_x')
    tabledef.define('float', 'pos_y')
    tabledef.define('float', 'pos_z')
    tabledef.define('float', 'rot_x')
    tabledef.define('float', 'rot_z')
    tabledef.define('float', 'speed', 30.0)
    tabledef.component = weapons.Laser

    tabledef = packer.TableDef('RedLaserSetup', template=tabledef)
    tabledef.component = weapons.RedLaser

    tabledef = packer.TableDef('BlueLaserSetup', template=tabledef)
    tabledef.component = weapons.BlueLaser

    tabledef = packer.TableDef('NeedlerShotSetup', template=tabledef)
    tabledef.component = weapons.NeedlerShot

    # Studs
    tabledef = packer.TableDef('StudSetup')
    tabledef.define('uint16', 'id')
    tabledef.define('uint8', 'stud_id')
    tabledef.define('float', 'pos_x')
    tabledef.define('float', 'pos_y')
    tabledef.define('float', 'pos_z')
    tabledef.component = stud.Stud

    tabledef = packer.TableDef('DynamicStudSetup')
    tabledef.define('uint16', 'id')
    tabledef.define('uint8', 'stud_id')
    tabledef.define('float', 'pos_x')
    tabledef.define('float', 'pos_y')
    tabledef.define('float', 'pos_z')
    tabledef.define('float', 'vel_x')
    tabledef.define('float', 'vel_y')
    tabledef.define('float', 'vel_z')
    tabledef.component = stud.DynamicStud

    tabledef = packer.TableDef('StudCollision')
    tabledef.define('uint16', 'id')
    tabledef.define('uint16', 'stud_id')

    # onConnect and onDisconnect callbacks for spawning players on the server
    ServerHost.onConnect = onConnect
    ServerHost.onDisconnect = onDisconnect


def onConnect(self, peer_id):
    comp = player.Chief(None)
    comp.givePermission(peer_id)


def onDisconnect(self, peer_id):
    for comp in self.components:
        if comp is not None and peer_id in comp.permissions:
            comp.permissions.remove(peer_id)
            if len(comp.permissions) == 0:
                # Destroy the component
                bge.logic.game.ai.unregister_external(comp)
                self.components[comp.net_id] = None
                comp.owner.endObject()
                table = packer.Table('Destroy')
                table.set('id', comp.net_id)
                buff = packer.to_bytes(table)

                for client in self.clients:
                    if client is not None and client.peer.incomingPeerID != peer_id:
                        client.send_reliable(buff)