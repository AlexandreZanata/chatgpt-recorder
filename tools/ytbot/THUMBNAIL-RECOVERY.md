# Thumbnail recovery

Recover a missing custom thumbnail from the local run without regenerating a whole video.
Find the channel's run folder under `.local/ytbot` and use its `thumbnail.png`.
If the asset is missing, recreate only that thumbnail from the existing article and the
selected channel's existing style; preserve the video's metadata, audience and schedule.

Open `https://studio.youtube.com/video/<video_id>/edit`, upload the image under the
thumbnail control and save. If the edit view does not commit it, use the existing Studio
upload dialog for that same video ID and save/schedule without changing the slot.
Verify the preview and record the recovery in the private run history. A missing thumbnail
never authorizes immediate publication or switching to another channel.

An expired Google session requires interactive sign-in in the dedicated bot profile.
Do not open the normal Chrome profile concurrently or expose private incident records,
video IDs or credentials in public documentation. Exact incident evidence remains in the
owner's private migration archive.
