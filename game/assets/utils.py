import bge


def key_pressed(key):
    return bge.logic.keyboard.events[key] == bge.logic.KX_INPUT_JUST_ACTIVATED


def key_released(key):
    return bge.logic.keyboard.events[key] == bge.logic.KX_INPUT_JUST_RELEASED


def key_held(key):
    return bge.logic.keyboard.events[key] == bge.logic.KX_INPUT_ACTIVE


def mouse_pressed(key):
    return bge.logic.mouse.events[key] == bge.logic.KX_INPUT_JUST_ACTIVATED


def mouse_released(key):
    return bge.logic.mouse.events[key] == bge.logic.KX_INPUT_JUST_RELEASED


def mouse_held(key):
    return bge.logic.mouse.events[key] == bge.logic.KX_INPUT_JUST_ACTIVE