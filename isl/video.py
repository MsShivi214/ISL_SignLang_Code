import os
import uuid

from moviepy import VideoFileClip, concatenate_videoclips

from .manifest import OUTPUT_DIR


def concatenate_clips(clip_paths):
    """Concatenate the given video files into one clip in OUTPUT_DIR and
    return its filename. Each request gets a unique filename so concurrent
    users never collide (the old code always wrote a fixed
    my_concatenation.mp4)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    clips = [VideoFileClip(p) for p in clip_paths]
    final = clips[0] if len(clips) == 1 else concatenate_videoclips(clips, method="compose")

    out_name = f"{uuid.uuid4().hex}.mp4"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    final.write_videofile(out_path, codec="libx264", audio_codec="aac", logger=None)

    if len(clips) > 1:
        final.close()
    for clip in clips:
        clip.close()

    return out_name
