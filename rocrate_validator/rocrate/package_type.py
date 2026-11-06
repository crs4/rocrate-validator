"""Processing context for an RO-Crate metadata document."""

from enum import Enum


class PackageType(str, Enum):
    ATTACHED = "attached"
    DETACHED = "detached"
    UNSPECIFIED = "unspecified"


def parse_packaging_mode(value: str) -> str:
    """Validate the public setting; ``auto`` is resolved by the source adapter."""
    if value not in {"auto", "attached", "detached"}:
        raise ValueError("packaging_mode must be 'auto', 'attached', or 'detached'")
    return value
