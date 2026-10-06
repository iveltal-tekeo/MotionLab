"""Canonical effect types: key -> (display name, family). Families follow the user's checklist."""

TYPES = {
    "hard_cut": ("Hard cut", "Hard cut"),
    "jump_cut": ("Jump cut", "Hard cut"),
    "flash_white": ("White flash", "Flash / white frame"),
    "flash": ("Flash (partial)", "Flash / white frame"),
    "flash_black": ("Black frame", "Flash / white frame"),
    "dip_black": ("Dip to black", "Dip to black / white"),
    "dip_white": ("Dip to white", "Dip to black / white"),
    "fade_in": ("Fade in", "Dip to black / white"),
    "fade_out": ("Fade out", "Dip to black / white"),
    "crossfade": ("Crossfade", "Crossfade"),
    "zoom_transition": ("Zoom transition", "Zoom punch in / out"),
    "zoom_in": ("Zoom in", "Zoom punch in / out"),
    "zoom_out": ("Zoom out", "Zoom punch in / out"),
    "whip_pan": ("Whip pan", "Whip pan"),
    "spin": ("Spin", "Spin"),
    "shake": ("Shake", "Shake"),
    "speed_ramp": ("Speed ramp", "Speed ramp"),
    "freeze": ("Freeze frame", "Freeze frame"),
    "stutter": ("Stutter", "Stutter / frame repeat / strobe"),
    "frame_repeat": ("Frame repeat (stepped)", "Stutter / frame repeat / strobe"),
    "strobe": ("Strobe", "Stutter / frame repeat / strobe"),
    "rgb_split": ("RGB split", "RGB split / glitch"),
    "glitch": ("Glitch", "RGB split / glitch"),
    "blur": ("Blur in / out", "Blur in / out"),
    "flash_color": ("Color flash", "Color flash / invert / saturation pop"),
    "invert": ("Invert", "Color flash / invert / saturation pop"),
    "sat_pop": ("Saturation pop", "Color flash / invert / saturation pop"),
    "light_leak": ("Light leak / film burn", "Light leak / film burn"),
    "split_screen": ("Split screen", "Split screen / mirror"),
    "mirror": ("Mirror", "Split screen / mirror"),
    "multi_screen": ("Multi-screen grid", "Split screen / mirror"),
    "text": ("Text / graphics", "Text / graphics"),
    "wipe": ("Wipe", "Wipe / mask / shape reveal"),
    "mask_reveal": ("Mask / shape reveal", "Wipe / mask / shape reveal"),
    "luma_fade": ("Luma fade / luma wipe", "Wipe / mask / shape reveal"),
    "push_slide": ("Push / slide", "Wipe / mask / shape reveal"),
    "unknown": ("Unknown / other", "Unknown / other"),
}

FAMILIES = [
    "Hard cut", "Flash / white frame", "Dip to black / white", "Crossfade", "Zoom punch in / out",
    "Whip pan", "Spin", "Shake", "Speed ramp", "Freeze frame", "Stutter / frame repeat / strobe",
    "RGB split / glitch", "Blur in / out", "Color flash / invert / saturation pop",
    "Light leak / film burn", "Split screen / mirror", "Text / graphics", "Wipe / mask / shape reveal",
    "Unknown / other",
]

# when several effects stack in one event, the earliest entry here names the event
PRIORITY = [
    "strobe", "flash_white", "dip_black", "dip_white", "fade_in", "fade_out", "flash_black", "zoom_transition",
    "whip_pan", "spin", "crossfade", "wipe", "mask_reveal", "luma_fade", "push_slide", "freeze",
    "stutter", "frame_repeat", "invert", "flash_color", "flash", "rgb_split", "glitch",
    "zoom_in", "zoom_out", "shake", "light_leak", "sat_pop", "blur", "speed_ramp", "split_screen",
    "mirror", "multi_screen", "text", "jump_cut", "unknown", "hard_cut",
]


def label(t: str) -> str:
    return TYPES.get(t, (t, "Unknown / other"))[0]


def family(t: str) -> str:
    return TYPES.get(t, (t, "Unknown / other"))[1]


def normalize(t: str) -> str:
    """Map free-text type names (from reviews / feedback) onto canonical keys."""
    s = t.strip().lower().replace("-", " ").replace("_", " ")
    for key, (name, _) in TYPES.items():
        if s in (key.replace("_", " "), name.lower()):
            return key
    aliases = {
        "white flash": "flash_white", "flash": "flash", "white frame": "flash_white",
        "cross dissolve": "crossfade", "dissolve": "crossfade", "cross fade": "crossfade",
        "dip": "dip_black", "fade to black": "dip_black", "fade through black": "dip_black",
        "zoom in transition": "zoom_transition", "zoom out transition": "zoom_transition",
        "zoom punch": "zoom_in", "punch in": "zoom_in", "punch out": "zoom_out",
        "zoom punch in": "zoom_in", "zoom punch out": "zoom_out",
        "whip": "whip_pan", "whip transition": "whip_pan", "freeze frame": "freeze",
        "frame hold": "freeze", "stutter loop": "stutter", "rgb": "rgb_split", "chromatic aberration": "rgb_split",
        "iris": "mask_reveal", "shape reveal": "mask_reveal", "mask reveal": "mask_reveal",
        "luma wipe": "luma_fade", "luma fade": "luma_fade", "slide": "push_slide", "push": "push_slide",
        "cut": "hard_cut", "other": "unknown",
    }
    return aliases.get(s, "unknown")
