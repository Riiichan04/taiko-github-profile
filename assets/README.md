# Curated README assets

This directory contains published examples, not general build output.

- `taiko.gif` / `.png`: classic layout, original background.
- `taiko-festival.gif` / `.png`: classic layout, festival background.
- `taiko-full.gif` / `.png`: compact layout, original background.
- `taiko-full-festival.gif` / `.png`: compact layout, festival background.
- `example`: current real public-calendar contribution example.

Local render commands default to `generated/`. Historical BPM comparisons, pattern experiments and drum-state screenshots are preserved in `generated/previews/` (ignored by Git). They are not required for rendering.

Run from the repository root to deliberately update a published example:

```sh
python scripts/render.py --output assets/taiko.gif
python scripts/render_svg.py --chart generated/github-your-username/contributions.tja --auto-spacing --output assets/example
```

Replace `your-username` with your GitHub username. Fetch/generate your snapshot and TJA first; their default directory is `generated/github-your-username/`. The bundled SVG is a historical public-calendar example.
