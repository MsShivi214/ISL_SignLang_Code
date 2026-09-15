from .gloss import to_isl_gloss
from .manifest import build_alphabet_manifest, build_animation_manifest, build_phrase_manifest
from .utils import normalize
from .video import concatenate_clips


def translate(text: str) -> dict:
    """Translate English `text` to an ISL video.

    Resolution order:
    1. Whole-sentence phrase match against VideoData (covers canned clips
       like "Hello", "Thank you", "How are you, I'm fine").
    2. Word-by-word match against the ISL gloss order (subject, object,
       remaining content words) for sentences without a canned clip.
    3. Per-letter fingerspelling for any gloss word that has no clip, if a
       VideoData/alphabets folder has been added.

    Words that still can't be resolved are reported in `missing` instead of
    silently breaking the video, so the caller can show the user what could
    not be signed yet.
    """
    phrase_manifest = build_phrase_manifest()

    direct_key = normalize(text)
    if direct_key in phrase_manifest:
        return {
            "gloss": [text.strip()],
            "clip_paths": [phrase_manifest[direct_key]],
            "missing": [],
        }

    gloss_sentences = to_isl_gloss(text)
    gloss_words = [w for sentence in gloss_sentences for w in sentence]

    alphabet_manifest = build_alphabet_manifest()
    clip_paths = []
    missing = []

    for word in gloss_words:
        key = normalize(word)
        if key in phrase_manifest:
            clip_paths.append(phrase_manifest[key])
            continue

        if alphabet_manifest and all(letter in alphabet_manifest for letter in key):
            clip_paths.extend(alphabet_manifest[letter] for letter in key)
            continue

        missing.append(word)

    return {"gloss": gloss_words, "clip_paths": clip_paths, "missing": missing}


def translate_to_animation_sequence(text: str) -> dict:
    """Same resolution order as translate(), but against baked avatar
    animation clips (SignAnimations/*.json) instead of video clips. Returns
    the ordered list of clip filenames to play plus any words that have no
    baked animation yet."""
    anim_manifest = build_animation_manifest()

    direct_key = normalize(text)
    if direct_key in anim_manifest:
        return {"gloss": [text.strip()], "clips": [anim_manifest[direct_key]], "missing": []}

    gloss_sentences = to_isl_gloss(text)
    gloss_words = [w for sentence in gloss_sentences for w in sentence]

    clips = []
    missing = []
    for word in gloss_words:
        key = normalize(word)
        if key in anim_manifest:
            clips.append(anim_manifest[key])
        else:
            missing.append(word)

    return {"gloss": gloss_words, "clips": clips, "missing": missing}


def translate_to_video(text: str) -> dict:
    result = translate(text)
    video_filename = concatenate_clips(result["clip_paths"]) if result["clip_paths"] else None
    return {
        "gloss": result["gloss"],
        "missing": result["missing"],
        "video_filename": video_filename,
    }
