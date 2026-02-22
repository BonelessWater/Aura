"""
Aura design system — matplotlib theme.

Usage in any notebook:
    import sys; sys.path.insert(0, '../src')
    from visualization.style import apply_aura_style, PALETTE, C
    apply_aura_style()
"""
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

# ── Color tokens ──────────────────────────────────────────────────────────────
PALETTE = {
    "bg":         "#0A0D14",   # page background
    "card":       "#1A1D2A",   # card surface / graph background
    "border":     "#2A2E3B",   # card borders, dividers
    "primary":    "#7B61FF",   # scores, gauges, gradients
    "secondary":  "#2563EB",   # links, gradient end
    "accent":     "#F4A261",   # CTA, amber highlights
    "text":       "#F0F2F8",   # headings, primary text
    "muted":      "#8A93B2",   # labels, secondary text
    "error":      "#E07070",   # warnings, disclaimers
    "success":    "#52D0A0",   # positive markers
    "teal":       "#3ECFCF",   # section icons
    "brand_red":  "#8C0716",   # AuRA glow, CTA
}

# Short alias
C = PALETTE

# ── Categorical sequence for multi-class plots ────────────────────────────────
#   healthy   systemic   GI           endocrine    extra1     extra2
CAT_COLORS = [
    "#52D0A0",  # success / green  → healthy
    "#7B61FF",  # primary / purple → systemic
    "#3ECFCF",  # teal             → gastrointestinal
    "#F4A261",  # accent / amber   → endocrine
    "#E07070",  # error / rose     → 5th class
    "#2563EB",  # secondary / blue → 6th class
]

# Map common category names to canonical colors
CATEGORY_COLOR = {
    "healthy":          CAT_COLORS[0],
    "systemic":         CAT_COLORS[1],
    "gastrointestinal": CAT_COLORS[2],
    "endocrine":        CAT_COLORS[3],
}

# ── Colormaps ─────────────────────────────────────────────────────────────────
# Diverging: brand purple → card bg → brand teal
AURA_DIVERGING = LinearSegmentedColormap.from_list(
    "aura_diverging",
    ["#7B61FF", "#1A1D2A", "#3ECFCF"],
)

# Sequential: dark → purple
AURA_SEQUENTIAL = LinearSegmentedColormap.from_list(
    "aura_sequential",
    ["#1A1D2A", "#7B61FF"],
)

# Sequential: dark → teal
AURA_TEAL = LinearSegmentedColormap.from_list(
    "aura_teal",
    ["#1A1D2A", "#3ECFCF"],
)

# RdYlGn replacement: rose → amber → teal
AURA_RDYLGN = LinearSegmentedColormap.from_list(
    "aura_rdylgn",
    ["#E07070", "#F4A261", "#52D0A0"],
)

# Register so seaborn/matplotlib can use by name
for _cm in [AURA_DIVERGING, AURA_SEQUENTIAL, AURA_TEAL, AURA_RDYLGN]:
    try:
        mpl.colormaps.register(_cm, force=True)
    except Exception:
        pass


def apply_aura_style():
    """
    Apply Aura dark theme to all subsequent matplotlib/seaborn figures.
    Call once near the top of each notebook after imports.
    """
    _C = PALETTE

    mpl.rcParams.update({
        # ── Canvas ────────────────────────────────────────────────────────
        "figure.facecolor":     _C["card"],
        "axes.facecolor":       _C["card"],
        "savefig.facecolor":    _C["card"],

        # ── Text ──────────────────────────────────────────────────────────
        "text.color":           _C["text"],
        "axes.labelcolor":      _C["text"],
        "xtick.color":          _C["muted"],
        "ytick.color":          _C["muted"],
        "font.family":          "sans-serif",
        "font.sans-serif":      ["Arial", "DejaVu Sans", "Liberation Sans"],
        "font.weight":          "bold",
        "axes.titleweight":     "bold",
        "axes.labelweight":     "bold",
        "font.size":            12,
        "axes.titlesize":       14,
        "axes.labelsize":       12,
        "xtick.labelsize":      11,
        "ytick.labelsize":      11,
        "legend.fontsize":      11,

        # ── Spines / grid ─────────────────────────────────────────────────
        "axes.edgecolor":       _C["border"],
        "axes.linewidth":       1.0,
        "grid.color":           _C["border"],
        "grid.linewidth":       0.6,
        "grid.alpha":           0.5,
        "axes.grid":            True,
        "axes.axisbelow":       True,

        # ── Default color cycle ───────────────────────────────────────────
        "axes.prop_cycle":      mpl.cycler(color=CAT_COLORS),

        # ── Legend ────────────────────────────────────────────────────────
        "legend.facecolor":     _C["card"],
        "legend.edgecolor":     _C["border"],
        "legend.labelcolor":    _C["text"],

        # ── Lines / markers ───────────────────────────────────────────────
        "lines.linewidth":      2.0,
        "patch.edgecolor":      _C["border"],
        "patch.linewidth":      0.5,

        # ── Figure ────────────────────────────────────────────────────────
        "figure.figsize":       (12, 6),
        "figure.dpi":           100,
        "savefig.dpi":          150,
        "savefig.bbox":         "tight",
    })

    # Apply to seaborn if imported
    try:
        import seaborn as sns
        sns.set_theme(
            style="dark",
            rc={
                "axes.facecolor":   _C["card"],
                "figure.facecolor": _C["card"],
                "grid.color":       _C["border"],
                "text.color":       _C["text"],
                "axes.labelcolor":  _C["text"],
                "xtick.color":      _C["muted"],
                "ytick.color":      _C["muted"],
            }
        )
    except ImportError:
        pass


def style_axis(ax, title=None, xlabel=None, ylabel=None):
    """Apply Aura polish to an existing axes object."""
    ax.set_facecolor(PALETTE["card"])
    for spine in ax.spines.values():
        spine.set_edgecolor(PALETTE["border"])

    if title:
        ax.set_title(title, color=PALETTE["text"], fontweight="bold",
                     fontsize=14, pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, color=PALETTE["text"], fontweight="bold")
    if ylabel:
        ax.set_ylabel(ylabel, color=PALETTE["text"], fontweight="bold")

    ax.tick_params(colors=PALETTE["muted"])
    ax.xaxis.label.set_color(PALETTE["text"])
    ax.yaxis.label.set_color(PALETTE["text"])
    return ax


def aura_figure(nrows=1, ncols=1, figsize=None, title=None, **kwargs):
    """Create a pre-styled Aura figure."""
    if figsize is None:
        figsize = (12 * ncols, 6 * nrows)
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, **kwargs)
    fig.patch.set_facecolor(PALETTE["card"])
    if title:
        fig.suptitle(title, color=PALETTE["text"], fontweight="bold",
                     fontsize=15, y=1.01)
    return fig, axes
