import os

from .utils import normalize

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_DATA_DIR = os.path.join(BASE_DIR, "VideoData")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SIGN_ANIM_DIR = os.path.join(BASE_DIR, "SignAnimations")

_ALPHABET_DIR_CANDIDATES = ["alphabets", "alphabet", "letters"]


def build_phrase_manifest():
    """Scan VideoData for .mp4 clips and index them by normalized phrase/word.

    Re-scans on every call so dropping new clips into VideoData picks them up
    without restarting the app.
    """
    manifest = {}
    if not os.path.isdir(VIDEO_DATA_DIR):
        return manifest
    for fname in os.listdir(VIDEO_DATA_DIR):
        full_path = os.path.join(VIDEO_DATA_DIR, fname)
        if not os.path.isfile(full_path) or not fname.lower().endswith(".mp4"):
            continue
        stem = os.path.splitext(fname)[0]
        if stem.lower().startswith("screen recording"):
            continue
        key = normalize(stem)
        if key:
            manifest[key] = full_path
    return manifest


def build_animation_manifest():
    """Scan SignAnimations for baked .json bone-rotation clips (produced by
    the baker tool) and index them by normalized phrase/word, same
    convention as build_phrase_manifest. Re-scans every call so newly baked
    signs show up without a restart."""
    manifest = {}
    if not os.path.isdir(SIGN_ANIM_DIR):
        return manifest
    for fname in os.listdir(SIGN_ANIM_DIR):
        full_path = os.path.join(SIGN_ANIM_DIR, fname)
        if not os.path.isfile(full_path) or not fname.lower().endswith(".json"):
            continue
        stem = os.path.splitext(fname)[0]
        key = normalize(stem)
        if key:
            manifest[key] = fname
    return manifest


def build_alphabet_manifest():
    """Optional fingerspelling fallback: looks for a VideoData/alphabets (or
    alphabet/letters) folder containing single-letter clips like A.mp4..Z.mp4.
    Returns {} if none exists yet -- fingerspelling is skipped in that case."""
    for candidate in _ALPHABET_DIR_CANDIDATES:
        d = os.path.join(VIDEO_DATA_DIR, candidate)
        if not os.path.isdir(d):
            continue
        letters = {}
        for fname in os.listdir(d):
            if not fname.lower().endswith(".mp4"):
                continue
            stem = os.path.splitext(fname)[0].strip().lower()
            if len(stem) == 1 and stem.isalpha():
                letters[stem] = os.path.join(d, fname)
        if letters:
            return letters
    return {}
