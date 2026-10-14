"""Generated hero/fallback artwork (SVG). Used when no licensed stock photo is
available, so we never fall back to the business's own photos without permission."""

import hashlib

MOTIFS = {
    "tooth": "M50 18c-9 0-14 5-20 5s-12-5-18 2c-6 8 0 22 3 32 3 11 4 25 10 25 5 0 5-15 10-15h30c5 0 5 15 10 15 6 0 7-14 10-25 3-10 9-24 3-32-6-7-12-2-18-2s-11-5-20-5z",
    "plate": "M50 15a35 35 0 1 0 .1 0zM50 30a20 20 0 1 0 .1 0z",
    "droplet": "M50 10C38 32 26 46 26 62a24 24 0 0 0 48 0C74 46 62 32 50 10z",
    "dumbbell": "M14 40h10v20H14zM24 34h8v32h-8zM32 46h36v8H32zM68 34h8v32h-8zM76 40h10v20H76z",
    "pillar": "M20 20h60v8H20zM26 28h8v44h-8zM46 28h8v44h-8zM66 28h8v44h-8zM16 72h68v8H16z",
    "house": "M50 14L12 46h10v38h22V62h12v22h22V46h10z",
    "wrench": "M70 12a18 18 0 0 0-17 24L16 73l11 11 37-37a18 18 0 0 0 24-17l-11 11-11-3-3-11z",
    "orb": "M50 12a38 38 0 1 0 .1 0z",
}


def hero_svg(
    name: str, primary: str, accent: str, model: str, width: int = 1600, height: int = 900
) -> bytes:
    seed = int(hashlib.sha1(name.encode()).hexdigest()[:8], 16)  # noqa: S324
    cx, cy = 60 + seed % 25, 30 + (seed >> 5) % 40
    motif = MOTIFS.get(model, MOTIFS["orb"])
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Abstract illustration">
<defs>
<radialGradient id="g1" cx="{cx}%" cy="{cy}%" r="75%"><stop offset="0" stop-color="{accent}" stop-opacity=".85"/><stop offset="1" stop-color="{primary}"/></radialGradient>
<linearGradient id="g2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<rect width="100%" height="100%" fill="url(#g1)"/>
<circle cx="{width * 0.8:.0f}" cy="{height * 0.25:.0f}" r="{height * 0.35:.0f}" fill="url(#g2)"/>
<circle cx="{width * 0.15:.0f}" cy="{height * 0.85:.0f}" r="{height * 0.28:.0f}" fill="url(#g2)"/>
<g transform="translate({width * 0.62:.0f} {height * 0.18:.0f}) scale({height * 0.0065:.2f})" fill="#fff" fill-opacity=".22"><path d="{motif}"/></g>
</svg>"""
    return svg.encode()
