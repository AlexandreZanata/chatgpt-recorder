# Zaflas Agro profile

CLI profile: `zaflas`. Narration, topics, titles, descriptions, thumbnail text and
tags are in Brazilian Portuguese. Prompt instructions remain in English.
The public channel display name is **Zaflas**, handle `@zaflas`, channel ID
`UCi2aftoK7vlS3A6OozMHXKg`. Use that display name for the bot's account switcher;
**Zaflas Agro** is the spoken brand from the user's reference article.

## Evidence inspected on 2026-11-13

The [public Videos tab](https://www.youtube.com/@zaflas/videos) yielded 39
long-form videos. Shorts are excluded from the duration calculation:

- Mean: **30:16**; median: **29:54**.
- Range: **23:08 to 42:51**.
- The latest 30 long-form videos average **29:41**.
- The channel header's 86-video count also includes content outside the Videos
  tab and must not be used as the sample size for this average.

The user's energy article has 6,777 whitespace-delimited words and matches the
[31:50 energy episode](https://www.youtube.com/watch?v=gGxbGDm4cQs).
The generation target is 6,000 to 7,200 words, approximately 30 minutes at this
channel's narration pace, normally 25 to 35 minutes. Duration is a target, not a
hard audio limit. The article retry threshold is 40,000 characters.

## Narration identity

`article_header.txt` includes a short excerpt from the supplied article as a
style reference. Every episode starts with its own topic question, then this
fixed identification:

> Você está ouvindo Zaflas Agro, conhecimento para quem faz o campo acontecer.

Every episode finishes with this exact final paragraph:

> Zaflas Agro. Tecnologia, gestão e conhecimento para o campo.

The source opening uses an em dash. Its comma above follows the repository's
existing prohibition of em/en dashes in article and metadata output. Hooks,
examples, technical explanations and conclusions must change with the topic.
These identity lines are generation instructions, not an audio postprocessing
step; generated articles still require review before relying on exact wording.

## Description format

Inspected full descriptions for the
[connectivity](https://www.youtube.com/watch?v=sCyGgu_IZWk),
[soil](https://www.youtube.com/watch?v=1H4Ukk-HCu0), and
[quarantine-pests](https://www.youtube.com/watch?v=KvBMX_QJKF8) episodes.
They consistently use this order: website, subscription link, `nossas redes:`,
LinkedIn/Instagram/Facebook/YouTube/GitHub links, one detailed subject paragraph,
seven lowercase hashtags, then `TAGS:`. The metadata prompt preserves that
branding and those URLs, replacing social-link em dashes with colons.
Tags remain within the bot's 425-character budget. `DESCRIPTION:` is required
as an internal parser label and is not included in the final video description.

## Thumbnail and video

`thumbnail.txt` preserves the user's master design: dark left gradient covering
45 to 50 percent, a topic-specific photographic agricultural subject on the
right, huge condensed uppercase Portuguese text, white supporting words and one
thematic keyword accent. No logo, frames, cards or decorative clutter.
The bot attaches the article without separate thumbnail text; the prompt thus
selects an accurate 2 to 6 word Portuguese phrase when none is supplied. Any
explicitly supplied phrase takes precedence. The source master prompt's lists
are reflowed without changing its visual requirements.

The existing `agro` background theme resolves to `zaflas_agro.mp4`. Data remains
isolated under `.local/ytbot/channels/zaflas/`. Shared scheduling, subtitles,
audience and end-screen rules apply unchanged.
The bot explicitly recognizes Portuguese (`pt`) for Zaflas subtitles; English
profiles still use `en`. The desktop transcriber's English-only entry point
retains its existing contract. Recognition caches are already language-specific.

## Studio confirmation

The exact [requested Studio channel](https://studio.youtube.com/channel/UCi2aftoK7vlS3A6OozMHXKg)
was opened in the bot's hidden Chrome, with no upload or scheduling. It returned
an access-denied page requesting an authorized account. The bot account switcher
did not list Zaflas. The signed-in bot account needs access to this channel
before a batch can run. Public identity was confirmed; Studio permission was not.

To refresh the public catalog without uploading:

```bash
python3 -m tools.ytbot catalog --channel zaflas
```
