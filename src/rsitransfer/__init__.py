"""rsi-transfer: do self-generated improvements to AI agents survive a change of base model?

The crutch coefficient measures whether a harness modification's benefit decays as base
models improve. A negative slope means the modification compensates for a weakness the
model no longer has -- it is a crutch, and it depreciates. A flat slope means it supplies
something no model provides for itself, and it endures.
"""

from rsitransfer.crutch import CrutchFit, crutch_coefficient, headroom_normalised_gain

__all__ = ["CrutchFit", "crutch_coefficient", "headroom_normalised_gain"]
__version__ = "0.1.0"
