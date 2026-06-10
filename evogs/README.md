# EvoGS Project Page

Project page for **EvoGS: Constructing Continuous-Layered Gaussian Splatting with Evolution Tree for Scalable 3D Streaming**.

## Structure

- `index.html` &mdash; main page (Bulma + Nerfies template, mirroring `../lapisgs/`).
- `static/css/`, `static/js/` &mdash; styles and scripts (copied verbatim from `../lapisgs/`).
- `static/images/` &mdash; figures converted from `~/Downloads/EvoGS/fig/`:
  - `teaser.png`
  - `continuous_vs_discrete.png`
  - `lod_illus/` &mdash; the three-paradigm illustration (spatial / lapis / continuous tree).
  - `options/` &mdash; design-space options A&ndash;D.
  - `visualization/` &mdash; quality&ndash;size scatters and qualitative comparisons (Playroom, Drjohnson).
  - `continuous_render/` &mdash; progressive-streaming PSNR curves and smooth-transition figure.
  - `compressibility/` &mdash; \(\psi\) energy-concentration plots.

## Updating images from the LaTeX source

Re-run the PDF&rarr;PNG conversion (ImageMagick required):

```sh
SRC=~/Downloads/EvoGS/fig
OUT=./static/images
magick -density 200 "$SRC/teaser.pdf"               -background white -alpha remove "$OUT/teaser.png"
magick -density 200 "$SRC/continuous_vs_discrete.pdf" -background white -alpha remove "$OUT/continuous_vs_discrete.png"
# ...and the other PDFs under fig/options, fig/lod_illus, fig/visualization, fig/compressibility, fig/continuous_render.
```

For the small `lod_illus/*.pdf` icons, use `-density 600` to keep them crisp on retina displays.

## Progressive-streaming videos

The "Smooth Quality Transitions" section references a single side-by-side video that is not yet checked in:

- `static/videos/progressive_comparison.mp4` &mdash; LapisGS (left) and EvoGS (right) `hstack`-ed into one file so the two methods stay perfectly synced across loop replays.

Both videos must hit each LOD boundary at the **same wall-clock time**, otherwise the side-by-side comparison is misleading. Because the two methods have different total frame counts and different bytes-per-LOD, a single `-framerate` won't sync them.

Use the helper in `tools/sync_progressive_videos.py` to build a per-method ffmpeg concat list that pins each LOD transition to a target time:

```sh
# 1. Inspect detected LOD boundaries (sanity check).
python tools/sync_progressive_videos.py \
    --csv        /Volumes/research-backup/3dgs-models/progressive_rendering/lego/lapis/progressive_sweep/budgets.csv \
    --frame-tmpl "/Volumes/research-backup/3dgs-models/progressive_rendering/lego/lapis/progressive_sweep/budget_%03d/test/ours_30000/renders/00065.png" \
    --segment-secs 4 4 4 \
    --print-only

# 2. Emit the two concat lists + drawtext annotations. SAME --segment-secs on
#    both so the L1/L2/L3 boundaries land at the same wall-clock time in both
#    outputs. The EvoGS pre-L0 (dg0) budgets are dropped automatically via
#    --start-lod 0. --annotate writes a sidecar <out>.vf.txt with a drawtext
#    chain that labels the current LOD on every frame.
python tools/sync_progressive_videos.py \
    --csv        .../lapis/progressive_sweep/budgets.csv \
    --frame-tmpl ".../lapis/progressive_sweep/budget_%03d/test/ours_30000/renders/00065.png" \
    --segment-secs 4 4 4 --hold-secs 1.5 \
    --annotate --method-label "LapisGS" \
    --out lapis_list.txt

python tools/sync_progressive_videos.py \
    --csv        .../evogs/progressive_sweep/budgets.csv \
    --frame-tmpl ".../evogs/progressive_sweep/budget_%03d/test/ours_30000/renders/00065.png" \
    --segment-secs 4 4 4 --hold-secs 1.5 \
    --annotate --method-label "EvoGS" \
    --out evogs_list.txt

# 3. Encode each method to web-friendly constant-framerate H.264 with the LOD
#    annotation. Pin the exact duration with -t so both files are bit-equal.
TOTAL=13.5   # sum of --segment-secs plus --hold-secs
ffmpeg -f concat -safe 0 -i lapis_list.txt -vf "$(cat lapis_list.txt.vf.txt)" \
       -t $TOTAL -r 30 -c:v libx264 -pix_fmt yuv420p -crf 18 lapis_progressive.mp4
ffmpeg -f concat -safe 0 -i evogs_list.txt -vf "$(cat evogs_list.txt.vf.txt)" \
       -t $TOTAL -r 30 -c:v libx264 -pix_fmt yuv420p -crf 18 evogs_progressive.mp4

# 4. Stack the two videos into a single side-by-side mp4 so they stay perfectly
#    synced across loop replays in the browser (two separate <video> elements
#    drift apart over time even when both files have identical durations).
ffmpeg -i lapis_progressive.mp4 -i evogs_progressive.mp4 \
       -filter_complex "[0:v]pad=iw+6:ih:0:0:color=white[L];[L][1:v]hstack=inputs=2[v]" \
       -map "[v]" -c:v libx264 -pix_fmt yuv420p -crf 18 \
       static/videos/progressive_comparison.mp4
```

The annotation shows:

- **Top-right:** method name (`LapisGS` / `EvoGS`).
- **Bottom-center:** `LOD k → LOD k+1` during each transit segment, then `LOD N (full)` during the hold.

Both labels appear in white text on a 55%-opaque black box, so they remain readable over any rendering. To change fonts use `--fontfile`; on Linux a good default is `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`. To skip annotation entirely just omit `--annotate` and drop the `-vf "$(cat ...)"` argument.

With `--segment-secs 4 4 4 --hold-secs 1.5`, both videos are exactly 13.5 s long and the L1/L2/L3 transitions land at 4 s / 8 s / 12 s on both sides regardless of how many EvoGS or LapisGS budgets fall inside each segment.

If the EvoGS `budgets.csv` uses block labels other than the `L<k> (res<R>)` pattern (e.g. wavelet block names like `P / DG0`), the helper will print "no boundaries found" — in that case, expose the LOD-aligned label in the sweep, or extend the regex at the top of the script.

Heads-up: also fix the float32 budget-boundary bug in `scripts/progressive_sweep_lapis.py` (use integer linspace) so the LapisGS video genuinely starts at "L0 received, nothing more."

## TODO before going public

- Confirm the BibTeX entry once the venue / year is known.
- Optional: add a teaser video (place under `static/videos/`) and swap the teaser image for an autoplaying clip, matching the GSVC layout.
