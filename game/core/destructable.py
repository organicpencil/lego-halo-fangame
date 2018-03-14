import bge
from . import Component

# Base class for all objects that can be destroyed
class Destructable(Component):
    config = {}
    config['hp'] = 1

    def __init__(self, owner):
        Component.__init__(self, owner)
        self.hp = self.config['hp']
        self.dead = False

    def apply_damage(self, data):
        assert(not self.dead)
        self.hp = max(self.hp - data['damage'], 0)
        if self.hp == 0:
            self.dead = True
