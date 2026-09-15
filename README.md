# English to ISL

Web app that translates English text into Indian Sign Language video, built
from a small library of pre-recorded clips in `VideoData/`.

## How it works

1. **Phrase match**: if the whole input matches a clip filename in
   `VideoData/` (e.g. "Thank you" -> `Thankyou.mp4`), that clip plays
   directly.
2. **Gloss fallback**: otherwise the sentence is parsed with spaCy and
   reordered into ISL gloss order (subject, object, remaining content
   words, with determiners/auxiliaries dropped), then each gloss word is
   looked up as its own clip and concatenated.
3. **Fingerspelling (optional)**: any gloss word without a clip is
   fingerspelled letter-by-letter if you add a `VideoData/alphabets/`
   folder with `a.mp4` .. `z.mp4`. Without that folder, unresolved words
   are just reported back as "missing" instead of breaking the video.

Add more `.mp4` files to `VideoData/` (filename = the word or phrase, e.g.
`Please.mp4`, `Good morning.mp4`) to grow the vocabulary -- no code or
restart required, the manifest is rebuilt on every request.

## 3D avatar mode

Instead of playing back recorded video, `/avatar` shows a 3D avatar (rigged
Mixamo character, `avatar/xbot.glb`) signing the gloss word-by-word. Its
animation data comes from `SignAnimations/*.json` clips, which you build
with the `/baker` tool:

1. Open `/baker`, pick a source clip from `VideoData/`, click **Start
   baking**. It runs MediaPipe pose + hand tracking on the clip in the
   browser, retargets the landmarks onto the avatar skeleton via Kalidokit,
   and shows a live 3D preview so you can sanity-check the result (there's
   a "swap left/right hands" checkbox if MediaPipe's handedness labeling
   comes out mirrored).
2. Name the sign (this is the lookup key, same convention as the video
   filenames -- e.g. `thank you`) and click **Save animation**.
3. Open `/avatar`, type a sentence, and it plays the avatar through the
   baked signs it has, reporting any gloss words with no animation yet.

This all runs client-side (MediaPipe Tasks Vision + Kalidokit + Three.js
via CDN) -- the Flask backend only stores/serves the baked JSON clips and
does the text -> ISL gloss step, same as the video pipeline.

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Run

```
python app.py
```

Then open http://127.0.0.1:5000 (video mode), `/avatar` (3D avatar), or
`/baker` (bake new signs from `VideoData/` clips into avatar animations).
