# taiko-github-profile 🥁

**English** | [Tiếng Việt](docs/README.vi.md)

A small, looping Taiko banner for your README, drawn entirely from geometric shapes. Offline rendering needs no browser, source image assets, or audio.

![Classic layout](assets/taiko.gif)

## Use from your profile workflow

To try the Action first, copy [the manual test workflow](examples/test-workflow.yml) to `.github/workflows/test-taiko.yml` in your caller repository and replace `OWNER` with the Action repository owner. Run **Actions → Try taiko-github-profile → Run workflow** and download `taiko-preview`. This test uploads SVG previews without publishing an output branch. If GitHub refuses the built-in token, configure the `CONTRIBUTIONS_TOKEN` repository secret with appropriate access.

This repository now exposes a composite Action via [action.yml](action.yml). Your profile repository calls it; the Python source stays here. SVG is the default. The example generates two backgrounds and publishes them in a separate workflow step to the profile repo's `output` branch.

Copy [examples/profile-workflow.yml](examples/profile-workflow.yml) into your profile repo and replace its `OWNER/taiko-github-profile@main` placeholder after pushing this project to GitHub. No Action version tag has been published from this local checkout.

```yaml
- name: Generate Taiko
  uses: OWNER/taiko-github-profile@main
  with:
    username: ${{ github.repository_owner }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
    bpm: '120'
    outputs: |
      dist/taiko.svg?background=original&variant=full
      dist/taiko-festival.svg?background=festival&variant=full
```

This step only renders. The linked full workflow includes checkout, scheduling, permissions and publication. `outputs` selects format by extension and accepts per-file visual options. GIF defaults to **30 FPS in the Action**; SVG uses continuous animation at the browser's rendering cadence. The manual GIF CLIs currently default to **25 FPS**; use `--fps 30` for the same setting. Custom TJA keeps its own BPM.

## Quick start

Requires Python 3.10 or newer. Run all commands from the repository root.

```sh
python -m pip install -r requirements.txt
python scripts/render.py
```

This renders the static [demo chart](charts/demo.tja) to `generated/renders/taiko.gif` and `generated/renders/taiko.png`: 800 × 220, 25 FPS, an 8-second seamless loop.

**Current status:** the manual CLI defaults to `charts/demo.tja`. Contribution generation accepts offline snapshots or GitHub GraphQL data. This repository runs tests only; the packaged Action and profile workflow example support scheduled publishing after setup.

## Layouts and backgrounds

- `--variant classic`: variant 1, 800 × 220, with decorative background space.
- `--variant full`: variant 2, a compact 766 × 108 strip with a smaller drum and a full-height note highway.
- `--background original`: orange stripes.
- `--background festival`: burgundy, rays, gold accents and waves.

![Compact layout](assets/taiko-full.gif)

![Festival background](assets/taiko-festival.gif)

```sh
python scripts/render.py --variant full
python scripts/render.py --background festival
python scripts/render.py --variant full --background festival
```

| Layout | Original background | Festival background |
| --- | --- | --- |
| Classic | `assets/taiko.gif` | `assets/taiko-festival.gif` |
| Full | `assets/taiko-full.gif` | `assets/taiko-full-festival.gif` |

The table lists curated files under `assets/`. Local rendering defaults to `generated/renders/`; each GIF has a matching PNG preview. Use the CLI to regenerate the four layout/background combinations.

## Build the default contribution beatmap

The generator reads contributions chronologically and writes TJA plus metadata. Start with [examples/contributions.json](examples/contributions.json), or supply your own snapshot:

```json
{"username":"your-username","days":[{"date":"2026-01-01","count":3},{"date":"2026-01-02","count":0}]}
```

```sh
python scripts/generate_contributions.py examples/contributions.json
python scripts/render.py --chart generated/contributions/contributions.tja --variant full --background festival --auto-spacing --output generated/contributions/taiko.gif
```

Generation defaults to **120 BPM** and seed `default`. Output: `generated/contributions/contributions.tja` and `generated/contributions/contributions.meta.json`. To change tempo or the pattern seed, add `--bpm 180 --seed your-seed` to the generation command. To change the destination, use `--output-directory generated/mine`.

### Input and classification

Dates must be unique, counts must be non-negative integers, and the window must span 1–366 calendar days. Missing dates between the supplied endpoints become zero-contribution days. The generator does not fetch GitHub data or choose the one-year window for you.

Percentiles use **active days only**, sorted by count. The nearest-rank boundary is the element at position `ceil(p × N)` for p = 0.8 or 0.9. Equal boundary counts stay equal, so ties can include more than exactly 10% or 20% of days.

Apply these rules in order; each day receives only one type of segment:

| Priority | Condition | Result |
| --- | --- | --- |
| Rest | Zero contributions | No notes; always breaks a streak |
| Drumroll | Top-10% band, strictly above the active-day median, at least 10 contributions and at least 3 times the median | Within each group of consecutive candidates, only the highest day becomes a roll; earliest date wins ties |
| Spike stream | Top-20% band, strictly above the median, not selected for a roll | Exactly **N continuous taps** for N contributions, including unselected roll candidates |
| Streak stream | Other active days in a streak longer than 7 days | One tap per day, continuously; no artificial breaks every five notes |
| Normal tap | Remaining active days | Don at or below the median; Ka above the median |

A uniform year never creates percentile outliers or rolls, even with 365 days of one contribution each. Streak rules still apply. The minimum of 10 and multiplier of 3 are provisional defaults in `Rules` in [contributions.py](scripts/taiko/contributions.py).

### Timing, rests and rolls

- Generated streams do not use sixth-beat spam. Tap spacing is `84/190 beat`: about 0.221 seconds at 120 BPM, matching 42px notes at 190px/s. Changing BPM changes tap intervals; `--auto-spacing` changes visual speed to prevent overlap.
- Rests shorter than 7 days use normal per-day tap spacing. Longer rests last **days / 7 seconds**, independent of BPM: 28 days = 4 seconds; 30 days ≈ 4.286 seconds. They always break streaks.
- A roll targets exactly N strikes. Its duration is `min(N / 20, 2)` seconds, followed by one tap interval for the TJA end marker `8`. The drum-face visual runs at 72% of the strike frequency; it does not alter chart events.
- SHA-256 seeds depend on generator version, username, date and user seed. New low-activity days do not reseed old days. Classification can change when percentile boundaries change. Repeated colour motifs do not create five-note groups or inserted rests.
- Duration follows the data rather than a forced 30-second cap. Limits of 100,000 notes/strikes, 4096 beats and 100,000 source frames raise errors instead of silently truncating streams.

### Metadata and reproducibility

Keep generated `.tja` and `.meta.json` files together. Metadata stores source dates/counts, configuration, seeds, daily decisions and exact roll strike counts. The reader loads it automatically and verifies a SHA-256 binding to the TJA.

If you edit generated TJA, regenerate the pair or remove the sidecar to use ordinary custom-chart behavior. Without metadata, rolls use the default 16 strikes/s; standard `5...8` notation does not encode a strike count.

## Write a custom TJA chart

Use [charts/demo.tja](charts/demo.tja) as a simple example. [charts/patterns.tja](charts/patterns.tja) demonstrates streams, mixed subdivisions, sixths and rests; custom charts can use sixths even though the contribution generator does not generate them.

- `0`: rest; `1`: Don; `2`: Ka; `5`: start a drumroll; `8`: end it.
- A comma ends a measure; line breaks do not. An empty comma is a full measure of rest.
- In 4/4, 4 slots give whole-beat spacing, 16 give quarter-beat spacing, and 24 give sixth-beat spacing.
- Spaces and `// comments` are ignored.

Supported subset: UTF-8/BOM, one course per file, constant BPM 30–300, `#START`, `#END`, and `#MEASURE` between measures. `WAVE`/`OFFSET` metadata is accepted, but audio is not played and audio offset is not applied. BPM changes, scrolling commands, branches, big notes and balloons are unsupported and produce file/line errors.

```sh
python scripts/render.py --chart path/to/custom.tja --speed 190
python scripts/render.py --chart path/to/custom.tja --auto-spacing --note-gap 4 --output generated/renders/custom.gif
```

`--speed` accepts 50–1000px/s. `--auto-spacing` overrides it with one constant speed computed from the tightest tap interval, including the loop seam, and the 42px diameter. `--note-gap 4` leaves a 4px gap between the closest pair. Rolls are excluded; slower sections remain farther apart. Automatic spacing never edits BPM or note timing, and dense charts may scroll very fast. Custom TJA does not require metadata.

TJA is the renderer chart format. JSON contribution snapshots and metadata serve different purposes.

## GIF quality, tests and benchmarks

The exporter prepares the scene once, filters visible notes, caches both backgrounds, quantizes each frame immediately, combines identical frames into timed holds, and enables GIF compression. Timing uses GIF's 10ms clock without accumulating per-frame duration drift. Holds longer than 655.35 seconds are split without changing pixels; this fallback writes full frames to avoid automatic re-merging. GIFs are replaced only after encoding succeeds.

```sh
python scripts/render.py --chart charts/demo.tja --fps 25 --colors 96
python scripts/render.py --chart charts/demo.tja --fps 15 --colors 64 --output generated/renders/smaller.gif
python -m unittest discover -s tests -v
python benchmarks/run.py
```

Lower FPS or colour counts are optional quality tradeoffs, not defaults. [benchmarks/report.json](benchmarks/report.json) compares exporters on the same prepared renderer, 16-second chart, 25 FPS and 96 colours: on the recorded Windows run, file size fell **21%**, peak RSS fell **68.7%**, and export time rose **15.5%**. Results are fixture-specific. The frozen old exporter is retained for reproducible comparisons.

## GitHub Actions and README embedding

The [test workflow](.github/workflows/test-action.yml) runs the offline test suite on relevant pushes and pull requests, or manually through **Actions → Test taiko-github-profile → Run workflow**. It needs only repository read permission.

To regenerate demo images, run the local rendering commands and commit the chosen assets. For daily contribution animations published to an output branch, use the separate [profile workflow example](examples/profile-workflow.yml); that workflow needs checkout and `contents: write`.

To embed an image elsewhere, replace `OWNER/REPO` and the branch:

```md
![Taiko](https://raw.githubusercontent.com/OWNER/REPO/main/assets/taiko.gif)
```

## Fetch real GitHub contributions

Set `GH_TOKEN` or `GITHUB_TOKEN` in your environment, then run:

```sh
python scripts/github_contributions.py your-username --bpm 200 --output generated/github-your-username/taiko.gif
```

The command fetches **365 UTC calendar days including today**, then generates the snapshot, TJA/metadata, and GIF. Today's count is taken at fetch time and may increase on later runs. UTC changes date at 07:00 in Vietnam; the runner's local timezone does not select the date window. `--end-date` accepts today or an earlier UTC date, never a future date. By default it uses the compact festival layout with automatic tap spacing. Tokens are read only from the environment, never saved in snapshots or command arguments. Counts include only activity visible to the supplied token and the profile's privacy settings; private activity may differ from the public calendar.

```sh
python scripts/github_contributions.py your-username --days 365 --end-date 2026-10-28 --fetch-only
python scripts/github_contributions.py your-username --bpm 180 --fps 15 --colors 64 --output generated/renders/github-smaller.gif
```

Default generated files are under `generated/github-USERNAME/`; override with `--output-directory`. The client uses small date-range GraphQL queries, checks every expected date, rejects partial/error responses, retries transient network/server failures, and never silently substitutes zero activity on failure. Fetching errors leave the previous GIF unchanged. TLS verification remains enabled.

For GitHub Actions, use the [profile workflow example](examples/profile-workflow.yml). If GitHub denies contribution access or you need additional authorized visibility, set the repository secret `CONTRIBUTIONS_TOKEN`. See [GitHub authentication](https://docs.github.com/en/graphql/guides/forming-calls-with-graphql). Never paste tokens into chat, source files, or workflow inputs.

For downloadable artifacts, add an upload-artifact step to your own workflow. Artifact downloads are not permanent README image URLs; use the profile workflow output branch for stable image URLs.

Replace `your-username` in commands with your GitHub username. The bundled preview uses a previously captured **public HTML calendar**, not live data for this placeholder account. GraphQL network integration still requires a configured token for live verification; mocked client tests are separate from this public-calendar preview.

## Experimental animated SVG

The compact vector exporter keeps the same TJA timing and scroll speed, including roll metadata and the 72% drum-face visual rate. It uses declarative SVG animation, reusable note shapes and no JavaScript, external assets or embedded raster frames.

```sh
python scripts/render_svg.py --chart generated/github-your-username/contributions.tja --auto-spacing --output generated/github-your-username/taiko.svg
```

[Download the bundled SVG preview](assets/github-your-username-public-200bpm.svg). This is a historical public-calendar example, not live data for `your-username`. Static renderers may show only the first frame. The Action supports `variant=full` and `variant=classic`; the standalone SVG CLI currently exports the compact layout. SVG artwork approximates the raster design rather than matching every pixel.

To test it in a README after uploading the asset:

```md
![Taiko](assets/github-your-username-public-200bpm.svg)
```

## Asset organization

- `assets/`: only curated README demos (four GIF/PNG pairs) and the current contribution SVG. See [assets/README.md](assets/README.md).
- `generated/`: snapshots, TJA/metadata and local render outputs. See [generated/README.md](generated/README.md).
- `generated/previews/`: historical experiments, moved intact from `assets/`; the manifest records their previous paths. These files are local-only and ignored by Git.

Ordinary CLI runs write into `generated/`. Use an explicit `--output assets/name.svg` or `--output assets/name.gif` to update a curated example, then commit it manually. Repository CI only runs tests; profile publishing is configured separately.

## Source structure

`scripts/render.py` is the rendering CLI; `scripts/generate_contributions.py` is the offline chart-generation CLI. Components under `scripts/taiko/`:

| File | Responsibility |
| --- | --- |
| `config.py` | Dimensions, FPS and shared colours |
| `chart.py` | TJA loading and validation |
| `drawing.py` | Supersampled shape helpers |
| `backgrounds.py` | Original and festival backgrounds |
| `drum.py` | Drum geometry and Don/Ka feedback |
| `highway.py` | Lane, target, notes and beat markers |
| `renderer.py` | Prepared scenes and layout composition |
| `export.py` | GIF encoding, palette and PNG previews |
| `spacing.py` | Automatic scroll speed |
| `contributions.py` | Offline contribution rules and TJA generation |
| `metadata.py` | Sidecar validation and roll strike restoration |
| `github.py` | Authenticated GraphQL calendar client |
| `action_options.py` | Per-file Action query options and validation |
| `publish.py` | Legacy single-file output-branch publisher |
| `svg.py` | Animated SVG composition and timing |
| `svg_backgrounds.py` | Separate original/festival SVG background functions |
| `svg_notes.py` | Don/Ka symbol definitions and note instances |
| `svg_elements.py` | Shared SVG element and number helpers |
