from core import Component

# Weapons, when spawned in a character's hand, will have their component created
# immediately. It is not the same component that would otherwise be created
# through normal registration.


class WeaponPickup(Component):
    def pickup(self, user):
        self.owner['weapon']

def register(cont):
    owner = cont.owner
    if not 'component' in owner:
        owner['component'] = WeaponPickup(owner)

class Weapon(Component):
    config = {}
    config['primary_delay'] = 30 # Frames
    config['projectile'] = 'projectile.laser'

weapons = {}
weapons['weapon.basic'] = Weapon

def create_weapon_component(ob):
    assert(not 'component' in ob)
    ob['component'] = weapons[ob.name]()
