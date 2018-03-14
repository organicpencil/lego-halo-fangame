from characters.character import Character


class Jackal(Character):
    config = Character.config.copy()
    config['hp'] = 1
    config['shield'] = None
    config['parts'] = 'jackal-parts'
    config['icon'] = 'icon-jackal'
    config['armature'] = 'jackal-armature'
    config['left_hand'] = 'jackal-lefthand'
    config['right_hand'] = 'jackal-righthand'
    config['shield_ob'] = 'jackal-shield'
    config['handshield'] = 'jackal-handshield'

def register(cont):
    owner = cont.owner
    if not 'component' in owner:
        owner['component'] = Jackal(owner)
