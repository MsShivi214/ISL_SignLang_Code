"""English -> ISL gloss reordering.

Replaces the old Stanford-Parser-based NP/VP tree walk with a spaCy
dependency parse. The intent is the same as the original code: pull the
subject noun phrase to the front, pull the object/complement out next, drop
function words (determiners, auxiliaries, prepositions) that ISL typically
omits, and lemmatize what's left -- approximating ISL's subject-object-verb,
topic-comment word order instead of English SVO.
"""

import spacy

_nlp = None

_SUBJECT_DEPS = {"nsubj", "nsubjpass", "expl"}
_OBJECT_DEPS = {"dobj", "dative", "attr", "acomp", "pobj", "oprd"}
_DROP_POS = {"DET", "AUX", "ADP", "PART", "PUNCT", "SPACE"}
_DROP_DEPS = {"det", "aux", "auxpass", "prep", "punct", "case", "cc"}
_KEEP_STOP_POS = {"PRON", "INTJ"}


def _load():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _keep_token(tok) -> bool:
    if tok.pos_ in _DROP_POS or tok.dep_ in _DROP_DEPS:
        return False
    if tok.is_stop and tok.pos_ not in _KEEP_STOP_POS:
        return False
    return True


def to_isl_gloss(text: str):
    """Returns a list of gloss word lists, one per sentence in `text`."""
    nlp = _load()
    doc = nlp(text)
    sentence_glosses = []

    for sent in doc.sents:
        subject_tokens, object_tokens = [], []
        for tok in sent:
            if tok.dep_ in _SUBJECT_DEPS:
                subject_tokens.extend(tok.subtree)
            elif tok.dep_ in _OBJECT_DEPS:
                object_tokens.extend(tok.subtree)

        subject_ids = {t.i for t in subject_tokens}
        object_ids = {t.i for t in object_tokens}

        # dedupe each group and restore original token order within it
        subject_ordered = sorted({t.i: t for t in subject_tokens}.values(), key=lambda t: t.i)
        object_ordered = sorted(
            ({t.i: t for t in object_tokens if t.i not in subject_ids}).values(),
            key=lambda t: t.i,
        )
        remaining = [t for t in sent if t.i not in subject_ids and t.i not in object_ids]

        ordered = subject_ordered + object_ordered + remaining
        gloss_words = [t.lemma_.lower() for t in ordered if _keep_token(t)]
        if gloss_words:
            sentence_glosses.append(gloss_words)

    return sentence_glosses
