import sys
import bge


def exception_handler(type_, value, tb):
    # print the exception
    import traceback
    traceback.print_exception(type_, value, tb)

    # start the python debugger
    # (remove these two lines if you don't want to use pdb)
    #import pdb
    #pdb.pm()

    # stop the game engine after you finish with pdb
    bge.logic.endGame()

# tell Python to use your function
sys.excepthook = exception_handler


class Core:
    def __init__(self):
        # Remove linked folders from the python path
        # This eliminates potential name conflicts from nested python modules
        for folder in ['characters', 'collectables', 'levels', 'menu', 'vehicles']:
            path = bge.logic.expandPath('//../{}'.format(folder))
            if path in sys.path:
                sys.path.remove(path)

        self.players = [Player(), Player()]
        self.players[0].active = True
        self.components = []
        self.studs = []

        # Custom event system
        # Pretty much a better version of the message system
        self.observers = {}

        # Load the HUD
        bge.logic.addScene('HUD')

    def register(self, component):
        self.components.append(component)

    def create_input_dict(self):
        return {'forward': False,
                'back': False,
                'left': False,
                'right': False,
                'jump': False,
                'interact': False,
                'primary': False}

    def update(self):
        self.components = [c for c in self.components if update_component(c)]

        events = bge.logic.keyboard.events
        held = bge.logic.KX_INPUT_ACTIVE
        keystate = self.players[0].input
        keystate['forward'] = events[bge.events.WKEY] == held
        keystate['back'] = events[bge.events.SKEY] == held
        keystate['left'] = events[bge.events.AKEY] == held
        keystate['right'] = events[bge.events.DKEY] == held


def update_component(component):
    if component.owner.invalid:
        component.unsubscribe_from_events()
        return False

    component.update()
    return True

class Player:
    def __init__(self):
        self.active = False
        self.score = 0
        self.input = Core.create_input_dict(self)
        self.component = None
