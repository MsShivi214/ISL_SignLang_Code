import re

from .gloss import to_isl_gloss
from .manifest import build_alphabet_manifest, build_animation_manifest, build_phrase_manifest
from .utils import normalize
from .video import concatenate_clips

_WORD_RE = re.compile(r"[a-z0-9]+")

# Standalone filler words to drop before phrase-matching a sentence against
# the animation library -- not the same list ISL-gloss dependency parsing
# drops in to_isl_gloss (that's grammar-driven; this is just noise removal
# for literal phrase-spotting). Deliberately excludes "are": it's also part
# of the literal "how are you" phrase below, and phrase-matching runs before
# any word is treated as filler (see the loop), so it must stay in the
# token stream for that phrase to ever be recognized.
_FILLER_WORDS = {"to", "the", "a", "an", "and", "our", "is", "in", "at", "for", "of"}

# Spellings that don't literally normalize() to a baked clip's filename key
# but should still resolve to it -- e.g. "How_are_you_Im_Fine.json"
# normalizes to "howareyouimfine", but a sentence might say just "how are
# you" or "i am fine" (or both together) and expect that same clip.
_PHRASE_ALIASES = {
    "how are you": "howareyouimfine",
    "i am fine": "howareyouimfine",
    "how are you i am fine": "howareyouimfine",
}

# Longest phrase (in words) worth trying as a single unit before falling
# back to shorter/single-word matches. Covers today's library with room to
# spare; raise it if a longer multi-word phrase gets aliased above.
_MAX_PHRASE_WORDS = 6


def translate_sentence_to_signs(text: str) -> dict:
    """Phrase-first match a free-form sentence against baked avatar
    animation clips (SignAnimations/*.json), for continuous avatar-only
    playback of a whole sentence.

    Unlike translate_to_animation_sequence() (which runs the sentence
    through ISL-gloss dependency-parse reordering), this matches words in
    their original left-to-right reading order: at each position it tries
    the longest word-span first (so "how are you" matches as one phrase
    before "how", "are", "you" are tried individually), drops filler words,
    and silently skips any word/phrase with no matching clip -- it never
    raises for unresolved input.

    Returns an ordered list of {"label", "clip"} sign entries (label is the
    matched phrase, title-cased, for UI display) plus any skipped words.
    """
    anim_manifest = build_animation_manifest()

    # Filler words are NOT stripped up front -- "are" is itself both a
    # filler and part of the "how are you" phrase, so removing it before
    # phrase-matching would make that phrase unrecognizable. Instead every
    # token stays in place for phrase-matching, and filler-word status only
    # decides whether a token that fails to match *on its own* gets quietly
    # dropped versus reported as missing.
    tokens = _WORD_RE.findall(text.lower())

    signs = []
    missing = []
    i = 0
    while i < len(tokens):
        matched = False
        max_len = min(_MAX_PHRASE_WORDS, len(tokens) - i)
        for length in range(max_len, 0, -1):
            phrase = " ".join(tokens[i : i + length])
            key = _PHRASE_ALIASES.get(phrase, normalize(phrase))
            if key in anim_manifest:
                signs.append({"label": phrase.title(), "clip": anim_manifest[key]})
                i += length
                matched = True
                break
        if not matched:
            if tokens[i] not in _FILLER_WORDS:
                missing.append(tokens[i])
            i += 1

    return {"signs": signs, "missing": missing}


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
    baked animation yet.
    """
    anim_manifest = build_animation_manifest()

    direct_key = normalize(text)
    if direct_key in anim_manifest:
        return {
            "gloss": [text.strip()],
            "clips": [anim_manifest[direct_key]],
            "missing": [],
        }

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
