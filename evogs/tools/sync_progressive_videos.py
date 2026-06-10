#!/usr/bin/env python3
"""Build an ffmpeg concat list that pins LOD boundaries to fixed wall-clock
times, so two progressive-streaming videos (e.g. LapisGS vs EvoGS) stay in
sync even when their per-LOD frame counts differ.

The script reads the per-method `budgets.csv` produced by
`scripts/progressive_sweep*.py`, finds the budget indices at which each LOD
is fully received (matching `block_in_progress == "L<k> (res<R>)"`), and
emits an ffmpeg concat-demuxer list with per-frame `duration` chosen so
that every LOD segment lasts a target number of seconds.

Run once per method with the SAME --segment-secs to guarantee that LOD
transitions land at identical timestamps in both output videos.

Example
-------
    python sync_progressive_videos.py \\
        --csv          /Volumes/.../lego/lapis/progressive_sweep/budgets.csv \\
        --frame-tmpl   "/Volumes/.../lego/lapis/progressive_sweep/budget_%03d/test/ours_30000/renders/00065.png" \\
        --segment-secs 4 4 4 \\
        --hold-secs    1.5 \\
        --out          lapis_list.txt

    python sync_progressive_videos.py \\
        --csv          /Volumes/.../lego/evogs/progressive_sweep/budgets.csv \\
        --frame-tmpl   "/Volumes/.../lego/evogs/progressive_sweep/budget_%03d/test/ours_30000/renders/00065.png" \\
        --segment-secs 4 4 4 \\
        --hold-secs    1.5 \\
        --out          evogs_list.txt

    ffmpeg -f concat -safe 0 -i lapis_list.txt -r 30 -c:v libx264 -pix_fmt yuv420p -crf 18 lapis_progressive.mp4
    ffmpeg -f concat -safe 0 -i evogs_list.txt -r 30 -c:v libx264 -pix_fmt yuv420p -crf 18 evogs_progressive.mp4

Both videos will be identical-length, and "L1 reached" / "L2 reached" /
"L3 reached" land at the same wall-clock times on both sides.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


LOD_DONE_RE = re.compile(r"^L(\d+)\s*\(res\d+\)$")
LOD_TRANSIT_RE = re.compile(r"^L(\d+)\s*->\s*L(\d+)\b")
DG_RE = re.compile(r"^dg(\d+)$", re.IGNORECASE)
ALL_RECEIVED_RE = re.compile(r"^\(?all received\)?$", re.IGNORECASE)


def _completed_lod(label: str, max_dg: int | None = None) -> int | None:
    """Return the highest fully-received LOD index implied by a label, or
    None if the label is unrecognized.

    LapisGS-style (discrete):
      "L2 (res2)"                  → 2 (L2 just reached, no progress into L3)
      "L1->L2 (37% of new_splats)" → 1 (L1 fully received; partway into L2)

    EvoGS / wavelet-HAC style:
      "dg0"                        → -1 (only P; pre-L0)
      "dg1"                        → 0  (DG0 done → L0 reached)
      "dg<k>"                      → k - 1
      "(all received)"             → max_dg (i.e. last LOD reached)
    """
    m = LOD_DONE_RE.match(label)
    if m:
        return int(m.group(1))
    m = LOD_TRANSIT_RE.match(label)
    if m:
        return int(m.group(1))
    m = DG_RE.match(label)
    if m:
        return int(m.group(1)) - 1
    if ALL_RECEIVED_RE.match(label):
        return max_dg
    return None


def find_lod_boundaries(csv_path: Path) -> dict[int, int]:
    """Return {lod_index -> first budget index where that LOD is fully reached}.

    Robust to the float32-budget bug (intermediate boundary frames land as
    "L<k>->L<k+1> (0% of ...)" instead of "L<k+1> (res<R>)") and to the
    wavelet/HAC sweep format ("dg0/dg1/.../all received").
    """
    # First pass: figure out the highest dg<k> seen so we can resolve
    # "(all received)" → max_dg.
    max_dg = -1
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            m = DG_RE.match(row["block_in_progress"].strip())
            if m:
                max_dg = max(max_dg, int(m.group(1)))
    max_dg_lod = max_dg if max_dg >= 0 else None

    boundaries: dict[int, int] = {}
    last_completed = -1
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            label = row["block_in_progress"].strip()
            completed = _completed_lod(label, max_dg=max_dg_lod)
            if completed is None or completed < 0:
                continue
            idx = int(row["idx"])
            for k in range(last_completed + 1, completed + 1):
                boundaries.setdefault(k, idx)
            last_completed = max(last_completed, completed)
    return boundaries


def _escape_drawtext(s: str) -> str:
    """Escape special chars for the drawtext `text=` value."""
    return (s.replace("\\", "\\\\")
             .replace(":", "\\:")
             .replace("'", "\\'"))


def build_annotation_filter(
    fontfile: str,
    method_label: str | None,
    later_lods: list[int],
    segment_secs: list[float],
    hold_secs: float,
) -> str:
    """Return an ffmpeg -vf chain that pins LOD labels to the same wall-clock
    intervals as the concat list (boundaries at cumulative `segment_secs`).
    """
    filters: list[str] = []
    if method_label:
        filters.append(
            f"drawtext=fontfile='{fontfile}':text='{_escape_drawtext(method_label)}':"
            f"fontsize=42:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=14:"
            f"x=w-tw-30:y=30"
        )

    seg_t = [0.0]
    for s in segment_secs:
        seg_t.append(seg_t[-1] + s)
    end_t = seg_t[-1] + max(hold_secs, 0.0)

    # One drawtext per transit segment: "LOD k  ->  LOD k+1".
    for i, (k_done, k_next) in enumerate(zip(later_lods[:-1], later_lods[1:])):
        t0, t1 = seg_t[i], seg_t[i + 1]
        text = f"LOD {k_done}  to  LOD {k_next}"
        filters.append(
            f"drawtext=fontfile='{fontfile}':text='{_escape_drawtext(text)}':"
            f"fontsize=56:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=18:"
            f"x=(w-tw)/2:y=h-th-40:"
            f"enable='between(t,{t0:.4f},{t1:.4f})'"
        )

    # Hold segment: "LOD N (full)".
    if hold_secs > 0 and later_lods:
        last_k = later_lods[-1]
        text = f"LOD {last_k}  (full)"
        filters.append(
            f"drawtext=fontfile='{fontfile}':text='{_escape_drawtext(text)}':"
            f"fontsize=56:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=18:"
            f"x=(w-tw)/2:y=h-th-40:"
            f"enable='between(t,{seg_t[-1]:.4f},{end_t:.4f})'"
        )
    return ",".join(filters)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", type=Path, required=True,
                   help="budgets.csv from progressive_sweep_*.py")
    p.add_argument("--frame-tmpl", required=True,
                   help="Printf-style absolute path to one rendered frame, with "
                        "%%03d in place of the budget index. Will be expanded for "
                        "each kept budget.")
    p.add_argument("--segment-secs", type=float, nargs="+", required=True,
                   help="Wall-clock seconds for each LOD segment after the start. "
                        "Length = (number of LOD boundaries after start). E.g. for "
                        "starts-at-L0 and ends-at-L3, pass three values for the "
                        "L0->L1, L1->L2, L2->L3 segments.")
    p.add_argument("--start-lod", type=int, default=0,
                   help="LOD at which the video begins. The pre-start budgets "
                        "(e.g. EvoGS's below-L0 frames) are dropped. Default: 0.")
    p.add_argument("--hold-secs", type=float, default=0.0,
                   help="Extra seconds to hold on the final frame. Default 0.")
    p.add_argument("--out", type=Path, default=None,
                   help="Output ffmpeg concat list (.txt). Required unless "
                        "--print-only is set.")
    p.add_argument("--print-only", action="store_true",
                   help="Just print detected LOD boundaries and exit.")
    p.add_argument("--annotate", action="store_true",
                   help="Also emit an ffmpeg -vf drawtext chain (<out>.vf.txt) "
                        "that annotates each frame with its current LOD. Use "
                        "with: ffmpeg ... -vf \"$(cat lapis_list.vf.txt)\" ...")
    p.add_argument("--method-label", type=str, default=None,
                   help="Optional method name shown top-right (e.g. 'LapisGS').")
    p.add_argument("--fontfile", type=str,
                   default="/System/Library/Fonts/Helvetica.ttc",
                   help="Font file for drawtext. Default works on macOS; on "
                        "Linux try /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf.")
    args = p.parse_args()

    if not args.print_only and args.out is None:
        p.error("--out is required unless --print-only is set.")

    boundaries = find_lod_boundaries(args.csv)
    if not boundaries:
        print(f"ERROR: no 'L<k> (res<R>)' rows found in {args.csv}. The CSV may "
              f"use a different block_in_progress format; check the column.",
              file=sys.stderr)
        return 1

    print(f"Detected LOD boundaries in {args.csv.name}:")
    for k in sorted(boundaries):
        print(f"  L{k}: budget idx {boundaries[k]}")
    if args.print_only:
        return 0

    sorted_lods = sorted(boundaries)
    if args.start_lod not in boundaries:
        print(f"ERROR: requested --start-lod {args.start_lod} not found.",
              file=sys.stderr)
        return 1
    start_idx_in_lods = sorted_lods.index(args.start_lod)
    later_lods = sorted_lods[start_idx_in_lods:]   # e.g. [0, 1, 2, 3]
    if len(args.segment_secs) != len(later_lods) - 1:
        print(f"ERROR: --segment-secs has {len(args.segment_secs)} values but "
              f"need {len(later_lods) - 1} (one per LOD transition after "
              f"--start-lod={args.start_lod}).",
              file=sys.stderr)
        return 1

    # Build per-frame duration map.
    durations: dict[int, float] = {}
    seg_start = boundaries[later_lods[0]]
    for end_lod, secs in zip(later_lods[1:], args.segment_secs):
        seg_end = boundaries[end_lod]
        n_frames = seg_end - seg_start
        if n_frames <= 0:
            print(f"WARN: empty segment L{end_lod - 1}->L{end_lod} "
                  f"(idx {seg_start}..{seg_end}); skipping.")
            continue
        per_frame = secs / n_frames
        for i in range(seg_start, seg_end):
            durations[i] = per_frame
        seg_start = seg_end
    last_idx = boundaries[later_lods[-1]]

    # Emit the concat list.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        f.write("ffconcat version 1.0\n")
        for i in sorted(durations):
            f.write(f"file '{args.frame_tmpl % i}'\n")
            f.write(f"duration {durations[i]:.6f}\n")
        # Final frame: hold for hold_secs, then re-declare it (ffmpeg quirk:
        # last `file` line must repeat for the previous `duration` to apply).
        hold = max(args.hold_secs, 1e-3)
        f.write(f"file '{args.frame_tmpl % last_idx}'\n")
        f.write(f"duration {hold:.6f}\n")
        f.write(f"file '{args.frame_tmpl % last_idx}'\n")

    total = sum(durations.values()) + args.hold_secs
    print(f"\nWrote {args.out}")
    print(f"  frames: {len(durations) + 1}   total duration: {total:.2f} s")

    if args.annotate:
        vf = build_annotation_filter(
            fontfile=args.fontfile,
            method_label=args.method_label,
            later_lods=later_lods,
            segment_secs=args.segment_secs,
            hold_secs=args.hold_secs,
        )
        vf_path = args.out.with_suffix(args.out.suffix + ".vf.txt")
        vf_path.write_text(vf + "\n")
        print(f"Wrote {vf_path}")
        print("\nSuggested ffmpeg command:")
        print(f"  ffmpeg -f concat -safe 0 -i {args.out} \\")
        print(f"         -vf \"$(cat {vf_path})\" \\")
        print(f"         -r 30 -c:v libx264 -pix_fmt yuv420p -crf 18 out.mp4")
    return 0


if __name__ == "__main__":
    sys.exit(main())
