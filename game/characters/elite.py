from characters.character import Character


class Elite(Character):
    config = Character.config.copy()
    config['hp'] = 4
    config['parts'] = 'elite-parts'
    config['icon'] = 'icon-elite'

def register(cont):
    owner = cont.owner.parent.parent
    if not 'component' in owner:
        owner['component'] = Elite(owner)
