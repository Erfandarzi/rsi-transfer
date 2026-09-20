"""Figure style conforming to the NeurIPS camera-ready geometry.

Sizes and typography follow the NeurIPS 2024 template as encoded by `tueplots`
(https://github.com/pnkraemer/tueplots): a 5.5 inch text width, serif family, 9 pt body
and axis labels, 7 pt ticks and legends. Values are inlined rather than imported so that
regenerating figures needs no extra dependency.

LaTeX rendering is used when a TeX installation is present and silently skipped when it is
not, so `make figures` produces the same layout on a machine without TeX -- only the glyph
rendering of the maths differs.

Colours are the Okabe-Ito colourblind-safe palette.
"""

from __future__ import annotations

import shutil

TEXT_WIDTH_IN = 5.5

# Okabe & Ito (2008), "Color Universal Design".
BLACK = "#000000"
ORANGE = "#D55E00"
BLUE = "#0072B2"
GREY = "#8C8C8C"
LIGHT = "#DDDDDD"


def has_latex() -> bool:
    return shutil.which("latex") is not None and shutil.which("dvipng") is not None


def neurips_style(*, usetex: bool | None = None) -> dict:
    """rcParams for a NeurIPS-format figure.

    Args:
        usetex: force LaTeX on or off. Defaults to using it when available.
    """
    tex = has_latex() if usetex is None else usetex
    style = {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "STIXGeneral", "DejaVu Serif"],
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 9,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "text.usetex": tex,
        # Thin, deliberate linework: the frame should not compete with the data.
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "lines.linewidth": 1.1,
        "lines.markersize": 3.5,
        "legend.frameon": False,
        "legend.handlelength": 1.4,
        "figure.constrained_layout.use": True,
        "savefig.pad_inches": 0.015,
        "savefig.dpi": 400,
        "axes.axisbelow": True,
    }
    if tex:
        style["text.latex.preamble"] = r"\renewcommand{\rmdefault}{ptm}"
    else:
        style["mathtext.fontset"] = "stix"
    return style


def panel_label(ax, letter: str, *, dx: float = -0.08, dy: float = 1.06) -> None:
    """Bold (a)/(b) marker at a panel's top-left, in axes coordinates."""
    import matplotlib as mpl

    text = rf"\textbf{{({letter})}}" if mpl.rcParams["text.usetex"] else f"({letter})"
    ax.text(dx, dy, text, transform=ax.transAxes, fontsize=9,
            fontweight="bold", va="bottom", ha="left")


def beta(exponent: str = "") -> str:
    """The symbol beta, rendered through whichever maths engine is active."""
    return rf"$\beta{exponent}$"
