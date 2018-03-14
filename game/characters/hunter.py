from characters.character import Character


class Hunter(Character):
    config = Character.config.copy()
    config['hp'] = 20
    config['shield'] = None
    config['parts'] = 'hunter-parts'
    config['icon'] = 'icon-hunter'
    config['armature'] = 'hunter-armature'
    config['left_hand'] = 'hunter-lefthand'
    config['right_hand'] = 'hunter-righthand'
    config['shield_ob'] = 'hunter-shield'

def register(cont):
    owner = cont.owner
    if not 'component' in owner:
        owner['component'] = Hunter(owner)
