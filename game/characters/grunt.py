from characters.character import Character


class Grunt(Character):
    config = Character.config.copy()
    config['hp'] = 1
    config['shield'] = None
    config['parts'] = 'grunt-parts'
    config['icon'] = 'icon-grunt'
    config['armature'] = 'grunt-armature'
    config['left_hand'] = 'grunt-lefthand'
    config['right_hand'] = 'grunt-righthand'
    config['shield_ob'] = 'grunt-shield'

def register(cont):
    owner = cont.owner
    if not 'component' in owner:
        owner['component'] = Grunt(owner)
