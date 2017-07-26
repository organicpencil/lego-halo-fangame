def key_pressed(key):
    import bge  # Why am I importing bge here? Might have been a pycomponent bug
    if bge.logic.KX_INPUT_JUST_ACTIVATED in bge.logic.keyboard.inputs[key].queue:
        return True
    return False


def key_released(key):
    import bge
    if bge.logic.KX_INPUT_JUST_RELEASED in bge.logic.keyboard.inputs[key].queue:
        return True
    return False


def key_held(key):
    import bge
    if bge.logic.KX_INPUT_ACTIVE in bge.logic.keyboard.inputs[key].status:
        return True
    return False


def mouse_pressed(key):
    import bge
    if bge.logic.KX_INPUT_ACTIVE in bge.logic.mouse.inputs[key].queue:
        return True
    return False


def mouse_released(key):
    import bge
    if bge.logic.KX_INPUT_JUST_RELEASED in bge.logic.mouse.inputs[key].queue:
        return True
    return False


def mouse_held(key):
    import bge
    if bge.logic.KX_INPUT_ACTIVE in bge.logic.mouse.inputs[key].status:
        return True
    return False