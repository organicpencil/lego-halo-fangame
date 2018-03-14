from characters.character import Character


class Arbiter(Character):
    config = Character.config.copy()
    config['hp'] = 4
    config['parts'] = 'arbiter-parts'
    config['icon'] = 'icon-arbiter'

def register(cont):
    owner = cont.owner.parent.parent
    if not 'component' in owner:
        owner['component'] = Arbiter(owner)
