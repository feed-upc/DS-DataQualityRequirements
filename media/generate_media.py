#!/usr/bin/env python3
"""
Generate DQR pattern and instantiation PNG images from JSON source files.

Usage:
    python generate_media.py              # regenerate everything
    python generate_media.py DQRP1        # one pattern + its instantiations
    python generate_media.py DQR1EH       # one instantiation only
"""

import json
import re
import textwrap
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Paths ──────────────────────────────────────────────────────────────────────
HERE     = Path(__file__).resolve().parent
CATS     = HERE.parent
PATTERNS = CATS / 'prototype' / 'patterns'
REQS     = CATS / 'prototype' / 'requirements'

# ── Colour palette ─────────────────────────────────────────────────────────────
# Patterns → purple fallback (overridden per-dimension via DIM_PALETTE)
P_COMMON = '#5B2D8E'   # dark  — Common Part fallback
P_CUSTOM = '#9B6DC9'   # light — Customized Part fallback
SUB_P    = '#ffffff'   # white (subtitle text)

# Per-dimension dark/light pairs: dark = Common Part, light = Customized/Template Part
DIM_PALETTE: dict[str, dict[str, str]] = {
    "Completeness": {"dark": "#1E40AF", "light": "#3B82F6"},   # navy      → blue
    "Currentness":  {"dark": "#0C4A6E", "light": "#0EA5E9"},   # dark sky  → sky blue
    "Fairness":     {"dark": "#92400E", "light": "#D97706"},   # brown     → amber
    "Consistency":  {"dark": "#4C1D95", "light": "#7C3AED"},   # indigo    → violet
    "Compliance":   {"dark": "#064E3B", "light": "#059669"},   # forest    → emerald
    "Accuracy":     {"dark": "#7F1D1D", "light": "#DC2626"},   # deep      → red
    "Credibility":  {"dark": "#134E4A", "light": "#0D9488"},   # dark teal → teal
}
# Instantiations → blue family
I_LEFT   = '#2B5797'   # medium blue   (left column)
SUB_I    = '#ffffff'   # white (subtitle text — hierarchy via italic+small size)
# Shared
WHITE    = '#FEF8F4'   # very subtle warm white
OFF_WHT  = '#EDE8F5'   # light purple tint — alternating rows in pattern param table
BORDER   = '#C8C8C8'
TXT_R    = '#1A1A1A'

# ── Layout ─────────────────────────────────────────────────────────────────────
FIG_W  = 9.0
L_W    = 3.4
R_W    = FIG_W - L_W
PX     = 0.14
PY     = 0.10
LH     = 0.165
DPI    = 150
WL     = 40
WR     = 73
WL_SUB = 38
CHAR_W = 0.063   # fallback: approx data-units per char at fontsize 9


# ── Text helpers ───────────────────────────────────────────────────────────────

def wraplines(text: str, width: int) -> list[str]:
    if not text:
        return ['']
    out: list[str] = []
    for para in str(text).split('\n'):
        out.extend(textwrap.wrap(para.strip(), width) or [''])
    return out or ['']


def nlines(lt: str, ls: str | None, rt: str) -> int:
    nl = len(wraplines(lt, WL)) + (1 + len(wraplines(ls, WL_SUB)) if ls else 0)
    nr = len(wraplines(rt, WR))
    return max(nl, nr, 1)


def row_h(n: int) -> float:
    return n * LH + 2 * PY


def _primary_dim(p: dict) -> tuple[str, str]:
    """Return (dimension, source) for the primary quality dimension."""
    dims = p.get('qualityDimensions', p.get('qualityDimension'))
    if isinstance(dims, list):
        primary = next((d for d in dims if d.get('primary')), dims[0] if dims else {})
        return primary.get('dimension', ''), primary.get('source', '')
    if isinstance(dims, dict):
        return dims.get('dimension', ''), dims.get('source', '')
    return '', ''


def _dims_text(p: dict) -> str:
    """Format all quality dimensions for the pattern card."""
    dims = p.get('qualityDimensions', p.get('qualityDimension'))
    if isinstance(dims, list):
        lines = []
        for d in dims:
            label = '• ' + d.get('dimension', '')
            if d.get('primary'):
                label += ' [primary]'
            label += f" ({d.get('source', '')})"
            lines.append(label)
        return '\n'.join(lines)
    if isinstance(dims, dict):
        return f"{dims.get('dimension', '')} ({dims.get('source', '')})"
    return ''


# ── Styled-segment helpers ─────────────────────────────────────────────────────

def parse_stmt_segments(statement: str, params: dict) -> list[tuple[str, bool]]:
    """
    Split statement into (text, is_param) pairs.
    Parameter values found verbatim are flagged True → italic + underline.
    """
    stmt = statement.replace(' ', ' ')

    candidates: set[str] = set()
    for v in params.values():
        if not isinstance(v, str) or not v.strip():
            continue
        s = v.strip()
        candidates.add(s)
        if '.' in s:
            candidates.add(s.rsplit('.', 1)[-1])

    valid = [c for c in candidates if len(c) >= 2 and c in stmt]
    valid.sort(key=len, reverse=True)

    used = [False] * len(stmt)
    spans: list[tuple[int, int]] = []
    for v in valid:
        idx = 0
        while True:
            pos = stmt.find(v, idx)
            if pos == -1:
                break
            end = pos + len(v)
            if not any(used[pos:end]):
                spans.append((pos, end))
                for i in range(pos, end):
                    used[i] = True
            idx = pos + 1

    spans.sort()
    segs: list[tuple[str, bool]] = []
    pos = 0
    for start, end in spans:
        if pos < start:
            segs.append((stmt[pos:start], False))
        segs.append((stmt[start:end], True))
        pos = end
    if pos < len(stmt):
        segs.append((stmt[pos:], False))
    return segs or [(stmt, False)]


def parse_tmpl_segments(template: str) -> list[tuple[str, bool]]:
    """Split pattern template at %paramName%, flagging them True → bold."""
    parts = re.split(r'(%\w+%)', template)
    return [(p, bool(re.match(r'^%\w+%$', p))) for p in parts if p]


def _wrap_segments(segments: list[tuple[str, bool]], width_chars: int
                   ) -> list[list[tuple[str, bool]]]:
    """Word-wrap styled segments to width_chars. Returns lines of token pairs."""
    lines: list[list[tuple[str, bool]]] = []
    cur: list[tuple[str, bool]] = []
    cur_len = 0

    for text, styled in segments:
        for tok in re.split(r'(\s+)', text):
            if not tok:
                continue
            is_space = bool(re.match(r'^\s+$', tok))
            tl = len(tok)
            if is_space:
                if cur_len + tl <= width_chars:
                    cur.append((tok, styled))
                    cur_len += tl
            else:
                if cur_len > 0 and cur_len + tl > width_chars:
                    lines.append(cur)
                    cur = []
                    cur_len = 0
                cur.append((tok, styled))
                cur_len += tl

    if cur:
        lines.append(cur)
    return lines


def _get_renderer(ax):
    try:
        return ax.get_figure().canvas.get_renderer()
    except AttributeError:
        return None


def _text_width(t, ax, renderer, fontsize):
    """Return actual rendered width of a Text object in data units."""
    if renderer is not None:
        bb  = t.get_window_extent(renderer=renderer)
        pts = ax.transData.inverted().transform(
            [[bb.x0, bb.y0], [bb.x1, bb.y1]])
        return pts[1, 0] - pts[0, 0]
    # fallback: character-count estimate
    return len(t.get_text()) * CHAR_W * (fontsize / 9)


def render_styled_block(ax, x0: float, y0: float,
                         segments: list[tuple[str, bool]],
                         bold_styled: bool = False,
                         underline_styled: bool = True,
                         color: str = TXT_R,
                         fontsize: float = 9) -> int:
    """
    Render mixed-style text with word-wrapping at WR chars.
    Adjacent same-styled tokens are merged so spaces render correctly.
    Returns number of lines rendered.
    """
    lines    = _wrap_segments(segments, WR)
    renderer = _get_renderer(ax)
    y        = y0

    for line in lines:
        # Merge adjacent same-styled tokens so spaces are part of the string
        groups: list[list] = []   # [[text, styled], ...]
        for tok, styled in line:
            if groups and groups[-1][1] == styled:
                groups[-1][0] += tok
            else:
                groups.append([tok, styled])

        x = x0
        for text, styled in groups:
            kw: dict = dict(fontsize=fontsize, va='top', ha='left',
                            clip_on=True, zorder=3, color=color)
            if styled:
                kw['fontstyle'] = 'italic'
                if bold_styled:
                    kw['fontweight'] = 'bold'
            t = ax.text(x, y, text, **kw)
            w = _text_width(t, ax, renderer, fontsize)

            if styled and underline_styled and text.strip():
                ul_y = y - fontsize / 72 * 1.25
                ax.plot([x, x + w], [ul_y, ul_y],
                        color=color, lw=0.5, zorder=3, clip_on=True)
            x += w

        y -= LH

    return max(len(lines), 1)


# ── Drawing primitives ─────────────────────────────────────────────────────────

def rect(ax, x: float, y: float, w: float, h: float, fc: str, lw: float = 0.5):
    ax.add_patch(mpatches.Rectangle(
        (x, y), w, h,
        linewidth=lw, edgecolor=BORDER, facecolor=fc, zorder=2
    ))


def txt(ax, x: float, y: float, s: str, **kw):
    kw.setdefault('fontsize', 9)
    kw.setdefault('va', 'top')
    kw.setdefault('ha', 'left')
    kw.setdefault('clip_on', True)
    kw.setdefault('zorder', 3)
    ax.text(x, y, s, **kw)


# ── Row renderer ───────────────────────────────────────────────────────────────

def std_row(ax, y_top: float,
            lt: str, ls: str | None, rt: str,
            lbg: str = P_COMMON, rbg: str = WHITE,
            sub_color: str = SUB_P,
            right_segs: list | None = None,
            right_italic: bool = False) -> float:
    """
    Draw one two-column row.
    right_segs: mixed-style segments for the right cell (italic+underline on params).
    right_italic: render entire right cell italic+underlined (source/materials/history).
    Returns height consumed.
    """
    ll  = wraplines(lt, WL)
    lsl = wraplines(ls, WL_SUB) if ls else []
    rl  = wraplines(rt, WR)

    nl = len(ll) + (1 + len(lsl) if lsl else 0)
    h  = row_h(max(nl, len(rl), 1))
    yb = y_top - h

    # ── left cell ──
    rect(ax, 0, yb, L_W, h, lbg)
    ty = y_top - PY
    for line in ll:
        txt(ax, PX, ty, line, color='white', fontweight='bold')
        ty -= LH
    if lsl:
        ty -= 0.025
        for line in lsl:
            txt(ax, PX, ty, line, color=sub_color, fontsize=7.5, fontstyle='italic')
            ty -= LH

    # ── right cell ──
    rect(ax, L_W, yb, R_W, h, rbg)
    ty  = y_top - PY
    rx0 = L_W + PX

    if right_segs is not None:
        render_styled_block(ax, rx0, ty, right_segs)

    elif right_italic:
        renderer = _get_renderer(ax)
        for line in rl:
            t = ax.text(rx0, ty, line, fontsize=9, va='top', ha='left',
                        clip_on=True, zorder=3, color=TXT_R, fontstyle='italic')
            w    = _text_width(t, ax, renderer, 9)
            ul_y = ty - 9 / 72 * 1.25
            ax.plot([rx0, rx0 + w], [ul_y, ul_y],
                    color=TXT_R, lw=0.5, zorder=3, clip_on=True)
            ty -= LH

    else:
        for line in rl:
            txt(ax, rx0, ty, line, color=TXT_R)
            ty -= LH

    return h


def params_row(ax, y_top: float, params: list[dict], lbg: str = P_COMMON) -> float:
    """Draw the parameters sub-table row. Returns height consumed."""
    CW    = [1.55, 1.35, 2.35]
    HDR_H = LH + PY

    cells: list[tuple[list, list, list, int]] = []
    for p in params:
        nw = wraplines(p.get('name', ''), 22)
        dw = wraplines(p.get('domainType', ''), 20)
        raw_inv = p.get('invariants', '')
        if isinstance(raw_inv, list):
            inv_str = ' '.join(str(x) for x in raw_inv).replace('[', '').replace(']', '')
        else:
            inv_str = str(raw_inv) if raw_inv else '—'
        iw = wraplines(inv_str, 32)
        n  = max(len(nw), len(dw), len(iw), 1)
        cells.append((nw, dw, iw, n))

    sub_h = HDR_H + sum(row_h(c[3]) * 0.88 for c in cells) + PY

    lt_lines = ['Data Quality Requirement', 'Statement Template Parameters']
    ls_lines = ['Parameter name, Domain type and',
                'Invariants applied to the', 'statement parameters']
    nl = len(lt_lines) + 1 + len(ls_lines)
    h  = max(row_h(nl), sub_h + PY * 2)
    yb = y_top - h

    rect(ax, 0, yb, L_W, h, lbg)
    ty = y_top - PY
    for line in lt_lines:
        txt(ax, PX, ty, line, color='white', fontweight='bold')
        ty -= LH
    ty -= 0.025
    for line in ls_lines:
        txt(ax, PX, ty, line, color=SUB_P, fontsize=7.5, fontstyle='italic')
        ty -= LH

    rect(ax, L_W, yb, R_W, h, WHITE)

    ox = L_W + PX * 0.6
    sy = y_top - PY * 1.2

    hdrs = ['Parameter Name', 'Domain Type', 'Invariants']
    cx = ox
    for hdr, cw in zip(hdrs, CW):
        rect(ax, cx, sy - HDR_H, cw, HDR_H, lbg)
        txt(ax, cx + 0.06, sy - 0.04, hdr,
            color='white', fontweight='bold', fontsize=8)
        cx += cw
    sy -= HDR_H

    for i, (nw, dw, iw, n) in enumerate(cells):
        rh = row_h(n) * 0.88
        bg = OFF_WHT if i % 2 else WHITE
        cx = ox
        for content, cw in zip([nw, dw, iw], CW):
            rect(ax, cx, sy - rh, cw, rh, bg)
            tty = sy - PY * 0.55
            for line in content:
                txt(ax, cx + 0.06, tty, line, color=TXT_R, fontsize=8)
                tty -= LH * 0.9
            cx += cw
        sy -= rh

    return h


# ── Figure factory ─────────────────────────────────────────────────────────────

def make_fig(total_h: float):
    fig, ax = plt.subplots(figsize=(FIG_W, total_h), dpi=DPI)
    ax.set_xlim(0, FIG_W)
    ax.set_ylim(0, total_h)
    ax.axis('off')
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    return fig, ax


# ── Pattern renderer ───────────────────────────────────────────────────────────

def render_pattern(p: dict, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    dim, _src = _primary_dim(p)
    fname = out_dir / f"{p['id']}-{dim}.png"

    pal    = DIM_PALETTE.get(dim, {"dark": P_COMMON, "light": P_CUSTOM})
    C_DARK  = pal["dark"]   # Common Part rows
    C_LIGHT = pal["light"]  # Statement template, parameters, customized rows

    rels = p.get('relationships', [])
    rel_text = '\n'.join(
        f"• {r['type']} ({r.get('relatedPattern', '?')}): {r['description']}"
        for r in rels
    ) if rels else '—'

    tmpl      = p.get('statementTemplate', '')
    tmpl_segs = parse_tmpl_segments(tmpl)

    # tag: 'common' → C_DARK, 'custom' → C_LIGHT
    # (left_title, left_subtitle, right_content, tag, right_segs)
    row_defs = [
        ('Data Quality Requirement Pattern Id', None,
         p['id'], 'common', None),
        ('Goal', 'A value to identify the DQR',
         p.get('goal', ''), 'common', None),
        ('Data Quality Requirement Description',
         'A one sentence intention of the DQR',
         p.get('description', ''), 'common', None),
        ('Quality Dimensions',
         'Quality dimensions addressed by the DQR and their source',
         _dims_text(p), 'common', None),
        ('Date', 'When the DQR pattern was created or last modified',
         p.get('date', ''), 'common', None),
        ('Version', 'The current version of the DQR pattern',
         f"v {p.get('version', '1.0')}", 'common', None),
        ('Relationships',
         'Other DQR patterns that have some relationship with this one',
         rel_text, 'common', None),
        ('Data Quality Requirement Statement Template',
         'Parameterized statement representing the DQR',
         tmpl, 'custom', tmpl_segs),
        (None, None, None, 'params', None),
        ('Source Entity', 'Who raised the DQR?',
         p.get('sourceEntity', ''), 'custom', None),
        ('Supporting Materials',
         'Pointer to documents that illustrate or explain the DQR',
         p.get('supportingMaterials', ''), 'custom', None),
        ('History', 'A description of the different versions of the DQR',
         p.get('history', ''), 'custom', None),
    ]

    params = p.get('parameters', [])
    total_h = 0.0
    for lt, ls, rt, tag, _ in row_defs:
        if tag == 'params':
            HDR_H = LH + PY
            sub_h = HDR_H + sum(row_h(max(
                len(wraplines(pr.get('name', ''), 22)),
                len(wraplines(pr.get('domainType', ''), 20)),
                1
            )) * 0.88 for pr in params) + PY
            total_h += max(row_h(2 + 1 + 3), sub_h + PY * 2)
        else:
            total_h += row_h(nlines(lt, ls, rt))

    fig, ax = make_fig(total_h)
    y = total_h

    for lt, ls, rt, tag, rsegs in row_defs:
        if tag == 'params':
            h = params_row(ax, y, params, lbg=C_LIGHT)
        elif tag == 'custom':
            h = std_row(ax, y, lt, ls, rt, lbg=C_LIGHT, right_segs=rsegs)
        else:  # 'common'
            h = std_row(ax, y, lt, ls, rt, lbg=C_DARK, right_segs=rsegs)
        y -= h

    fig.savefig(fname, dpi=DPI, bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)
    print(f"  ✓ {fname.relative_to(HERE)}")


# ── Instantiation renderer ─────────────────────────────────────────────────────

def render_instantiation(r: dict, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    req_id = r['id']
    pid    = r.get('pattern', {}).get('id', '?')
    pver   = r.get('pattern', {}).get('version', '1.0')
    dim    = r.get('qualityDimension', {}).get('dimension', '')
    src    = r.get('qualityDimension', {}).get('source', '')
    fname  = out_dir / f"{req_id}Instantiation.png"

    params_dict = r.get('parameters', {})
    if not isinstance(params_dict, dict):
        params_dict = {}
    stmt      = r.get('statement', '')
    stmt_segs = parse_stmt_segments(stmt, params_dict)

    # (left_title, left_subtitle, right_content, right_segs, right_italic)
    row_defs = [
        ('Data Quality Requirement id',
         'A value to identify the DQR',
         req_id, None, False),
        ('Goal',
         'The problem-statement of the DQR',
         r.get('goal', ''), None, False),
        ('Data Quality Requirement description',
         'A one sentence intention of the DQR',
         r.get('description', ''), None, False),
        ('Quality dimension',
         'Name of quality dimension of the DQR and its source',
         f"{dim} ({src})", None, False),
        ('Data Quality Requirement Pattern id',
         'The identifier and version of the DQR pattern from which the requirement is instantiated',
         f"{pid}\nv {pver}", None, False),
        ('Data Quality Requirement Statement',
         'A statement representing the DQR',
         stmt, stmt_segs, False),
        ('Source Entity',
         'Who raised the DQR?',
         r.get('sourceEntity', ''), None, True),
        ('Supporting materials',
         'Pointer to documents that illustrate or explain the DQR',
         r.get('supportingMaterials', ''), None, True),
        ('History',
         'A description of the different versions of the DQR',
         r.get('history', ''), None, True),
    ]

    total_h = sum(row_h(nlines(lt, ls, rt)) for lt, ls, rt, _, _ in row_defs)
    fig, ax = make_fig(total_h)
    y = total_h

    for lt, ls, rt, rsegs, r_italic in row_defs:
        h = std_row(ax, y, lt, ls, rt,
                    lbg=I_LEFT, sub_color=SUB_I,
                    right_segs=rsegs, right_italic=r_italic)
        y -= h

    fig.savefig(fname, dpi=DPI, bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)
    print(f"  ✓ {fname.relative_to(HERE)}")


# ── Main ───────────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None

    all_patterns = sorted(PATTERNS.glob('DQRP*.json'))
    all_reqs     = sorted(REQS.glob('DQR[0-9]*.json'))

    by_pattern: dict[str, list[dict]] = {}
    for f in all_reqs:
        r = load_json(f)
        pid = r.get('pattern', {}).get('id')
        if pid:
            by_pattern.setdefault(pid, []).append(r)

    if target is None:
        for f in all_patterns:
            p = load_json(f)
            pid = p['id']
            print(f"\n[{pid}]")
            render_pattern(p, HERE / pid)
            for r in by_pattern.get(pid, []):
                render_instantiation(r, HERE / pid)

    elif target.startswith('DQRP'):
        f = PATTERNS / f'{target}.json'
        if not f.exists():
            sys.exit(f"Pattern not found: {f}")
        p = load_json(f)
        print(f"\n[{target}]")
        render_pattern(p, HERE / target)
        for r in by_pattern.get(target, []):
            render_instantiation(r, HERE / target)

    elif target.startswith('DQR'):
        f = REQS / f'{target}.json'
        if not f.exists():
            sys.exit(f"Requirement not found: {f}")
        r = load_json(f)
        pid = r.get('pattern', {}).get('id', 'unknown')
        print(f"\n[{target}]")
        render_instantiation(r, HERE / pid)

    else:
        sys.exit(f"Unknown target '{target}'. Use DQRPn or DQRxEH.")

    print("\nDone.")


if __name__ == '__main__':
    main()
