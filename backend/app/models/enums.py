from enum import Enum


class EventType(str, Enum):
    action = "action"
    dialogue = "dialogue"
    environment = "environment"
    conflict = "conflict"
    relationship_change = "relationship_change"
    director = "director"
    inciting = "inciting"


class MemoryType(str, Enum):
    observation = "observation"
    reflection = "reflection"
    plan = "plan"


class ImageAssetType(str, Enum):
    style_ref = "style_ref"
    character_ref = "character_ref"
    scene = "scene"


class DirectiveType(str, Enum):
    inject_event = "inject_event"
    set_goal = "set_goal"
    modify_world = "modify_world"
    force_action = "force_action"
