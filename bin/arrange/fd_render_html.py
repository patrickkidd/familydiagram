"""
Render a laid-out family diagram to an HTML/SVG file.

Input: list of person dicts (with x, y, id, name, gender, size, partners,
       parent_a, parent_b) — i.e. GT JSON with positions already filled in.

Output: HTML string with embedded SVG.

Geometry mirrors pkdiagram.scene conventions:
  - Person itemPos is the center of the symbol
  - SIZE_PX matches personRectForSize(size).width() (scaleForPersonSize * 100)
  - Marriage: U-shape from each spouse's bottom-center, bar at bottom + px/2.2 drop
  - ChildOf: line from child top-center to marriage bar level, x clamped to bar extents
"""

SIZE_PX = {1: 8, 2: 16, 3: 40, 4: 80, 5: 125}
PADDING = 80
LABEL_OFFSET = 8  # px below symbol bottom edge
STROKE = 2


def _px(p):
    return SIZE_PX.get(p.get("size", 5), 125)


def render_svg(people):
    """Return (svg_string, width, height) for the given people with x/y positions."""
    if not people:
        return "<svg></svg>", 0, 0

    by_id = {p["id"]: p for p in people}

    # Bounding box with enough margin for labels
    max_px = max(_px(p) for p in people)
    xs = [p["x"] for p in people]
    ys = [p["y"] for p in people]
    min_x = min(xs) - PADDING - max_px / 2
    min_y = min(ys) - PADDING - max_px / 2
    max_x = max(xs) + PADDING + max_px / 2
    max_y = max(ys) + PADDING + max_px / 2 + max_px  # extra for labels

    W = max_x - min_x
    H = max_y - min_y

    def tx(x):
        return x - min_x

    def ty(y):
        return y - min_y

    parts = []

    # --- Marriage connectors and child lines (drawn behind symbols) ---
    seen_pairs = set()
    for p in people:
        for partner_id in p.get("partners") or []:
            pair = tuple(sorted([p["id"], partner_id]))
            if pair in seen_pairs or partner_id not in by_id:
                continue
            seen_pairs.add(pair)
            q = by_id[partner_id]
            px_p, px_q = _px(p), _px(q)
            px_max = max(px_p, px_q)

            # Marriage bar drop mirrors Marriage.pathFor: height = personRect.height() / 2.2
            drop = px_max / 2.2

            xa = tx(p["x"])
            ya_bot = ty(p["y"]) + px_p / 2
            xb = tx(q["x"])
            yb_bot = ty(q["y"]) + px_q / 2
            y_bar = max(ya_bot, yb_bot) + drop

            x_left = min(xa, xb)
            x_right = max(xa, xb)

            # U-shape: drop from A, horizontal bar, rise to B
            parts.append(
                f'<line x1="{xa:.1f}" y1="{ya_bot:.1f}" x2="{xa:.1f}" y2="{y_bar:.1f}" '
                f'stroke="#333" stroke-width="{STROKE}"/>'
            )
            parts.append(
                f'<line x1="{xa:.1f}" y1="{y_bar:.1f}" x2="{xb:.1f}" y2="{y_bar:.1f}" '
                f'stroke="#333" stroke-width="{STROKE}"/>'
            )
            parts.append(
                f'<line x1="{xb:.1f}" y1="{y_bar:.1f}" x2="{xb:.1f}" y2="{yb_bot:.1f}" '
                f'stroke="#333" stroke-width="{STROKE}"/>'
            )

            # Child lines: each child connects from its top-center to the bar level,
            # x clamped to bar extents (mirrors ChildOf.pathFor)
            couple = frozenset([p["id"], partner_id])
            children = [
                c
                for c in by_id.values()
                if frozenset([c.get("parent_a"), c.get("parent_b")]) == couple
            ]
            for c in children:
                cx = tx(c["x"])
                cy_top = ty(c["y"]) - _px(c) / 2
                cx_clamped = max(x_left, min(x_right, cx))
                parts.append(
                    f'<line x1="{cx_clamped:.1f}" y1="{y_bar:.1f}" '
                    f'x2="{cx:.1f}" y2="{cy_top:.1f}" '
                    f'stroke="#333" stroke-width="{STROKE}"/>'
                )

    # --- Person symbols ---
    for p in people:
        sz = _px(p)
        cx, cy = tx(p["x"]), ty(p["y"])
        gender = p.get("gender", "")
        name = (p.get("name") or "").replace("&", "&amp;").replace("<", "&lt;")

        if gender == "male":
            parts.append(
                f'<rect x="{cx - sz/2:.1f}" y="{cy - sz/2:.1f}" '
                f'width="{sz}" height="{sz}" '
                f'fill="white" stroke="#333" stroke-width="{STROKE}"/>'
            )
        elif gender == "female":
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{sz/2:.1f}" '
                f'fill="white" stroke="#333" stroke-width="{STROKE}"/>'
            )
        else:
            # Diamond for unknown/miscarriage/abortion
            half = sz / 2
            pts = f"{cx:.1f},{cy-half:.1f} {cx+half:.1f},{cy:.1f} {cx:.1f},{cy+half:.1f} {cx-half:.1f},{cy:.1f}"
            parts.append(
                f'<polygon points="{pts}" fill="white" stroke="#333" stroke-width="{STROKE}"/>'
            )

        font_size = max(9, sz // 7)
        label_x = cx + sz / 2 + LABEL_OFFSET
        label_y = cy + font_size / 3  # vertically centered on symbol
        parts.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="start" '
            f'font-size="{font_size}" font-family="sans-serif" fill="#333">{name}</text>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">'
        + "".join(parts)
        + "</svg>"
    )
    return svg, W, H


def render_html(people, title="Family Diagram"):
    svg, W, H = render_svg(people)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ margin: 0; background: #f5f5f5; font-family: sans-serif; overflow: hidden; }}
  #header {{ padding: 8px 16px; display: flex; align-items: center; gap: 12px;
             background: #fff; border-bottom: 1px solid #ddd; }}
  h2 {{ margin: 0; font-size: 15px; color: #333; flex: 1; }}
  button {{ padding: 4px 10px; cursor: pointer; border: 1px solid #ccc;
            border-radius: 3px; background: #fff; font-size: 13px; }}
  button:hover {{ background: #eee; }}
  #canvas {{ position: absolute; top: 41px; left: 0; right: 0; bottom: 0; overflow: auto; }}
  #wrap {{ display: inline-block; padding: 20px; transform-origin: top left; }}
</style>
</head>
<body>
<div id="header">
  <h2>{title}</h2>
  <button onclick="fit()">Fit</button>
  <button onclick="zoom(1.25)">+</button>
  <button onclick="zoom(0.8)">−</button>
  <button onclick="setZ(1)">1:1</button>
</div>
<div id="canvas"><div id="wrap">{svg}</div></div>
<script>
var z = 1;
function applyZ() {{
  document.getElementById('wrap').style.transform = 'scale(' + z + ')';
}}
function zoom(f) {{ z = Math.max(0.05, Math.min(10, z * f)); applyZ(); }}
function setZ(v) {{ z = v; applyZ(); }}
function fit() {{
  var c = document.getElementById('canvas');
  var vw = c.clientWidth - 40, vh = c.clientHeight - 40;
  z = Math.min(vw / {W}, vh / {H}, 1);
  applyZ();
}}
window.addEventListener('load', fit);
</script>
</body>
</html>"""
