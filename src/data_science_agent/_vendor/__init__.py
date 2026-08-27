"""Vendored ``dsa_*`` workspace packages (self-contained single wheel).

The umbrella distribution ``jack-data-science-agent`` bundles the ``dsa_*``
sub-packages that used to be separate workspace distributions. They are shipped
inside this package under ``_vendor`` so that ``pip install
jack-data-science-agent`` works without publishing 15 separate packages.

To keep the vendored code importable under its original top-level names
(``dsa_agent``, ``dsa_tools``, …), this package inserts its own directory at
the front of ``sys.path`` when imported. Importing ``data_science_agent`` (or
any of its submodules) therefore makes ``dsa_*`` importable as top-level names
resolving to these vendored copies.
"""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR_DIR = str(Path(__file__).resolve().parent)

if _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)
