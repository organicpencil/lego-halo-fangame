from characters.character import Character


class Chief(Character):
    config = Character.config.copy()
    config['hp'] = 4
    config['shield'] = None
    config['parts'] = 'chief-parts'
    config['icon'] = 'icon-chief'

def register(cont):
    owner = cont.owner.parent.parent
    if not 'component' in owner:
        owner['component'] = Chief(owner)
