# Logos

Brand and app logos as SVG for MotionLab's motion graphics: one folder per logo (`youtube\`, `premiere-pro\`, ...),
one file per variant - `color` (the brand's colours), `mono` (one colour, takes any colour), `wordmark` (the name
written out), `color-dark` / `wordmark-dark` (for a dark background). `logos.json` = the index (names, groups, search
words, each variant's aspect, background and colours).

Made by `tools\logos.py import` from the folder `refs\logos\` (only read): cleaned copies - no scripts, no links
outside the file, ids and CSS classes renamed so two logos on one page never clash. Add a logo there
(`refs\logos\<name>\color.svg`, ...) and run the import again.

In a graphic: a logo setting (`logo`, `logos`, `*_logo`) takes `youtube`, `youtube/mono` or several `a|b|c`; a text
setting takes `:youtube:` where a letter or an emoji goes. `tools\logos.py find "<words>"` finds one.

The logos are trademarks of their respective owners. MotionLab includes them so a video can name the products it is
about ("edited in Premiere Pro", "follow me on TikTok"); using one does not mean the owner endorses the video.
Follow each brand's own guidelines when a logo is the centre of attention.
