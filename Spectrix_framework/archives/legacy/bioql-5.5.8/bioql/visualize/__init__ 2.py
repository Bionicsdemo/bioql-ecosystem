"""
BioQL Visualization Module

Provides molecular visualization capabilities using PyMOL and py3Dmol.

Main Features:
- 3D molecular structure visualization
- Protein-ligand complex rendering
- PyMOL integration with fallback to py3Dmol
- Export to images and PyMOL sessions

Example:
    >>> from bioql.visualize import show, save_image
    >>> show("protein.pdb")
    >>> save_image("complex.pdb", "output.png")
"""

__all__ = [
    "show",
    "save_image",
    "save_session",
    "visualize_complex",
]

# Lazy imports to avoid hard dependencies
def show(*args, **kwargs):
    """Display molecular structure in viewer."""
    try:
        from .pymol_viz import show as _show
        return _show(*args, **kwargs)
    except ImportError:
        from .py3dmol_viz import show as _show
        return _show(*args, **kwargs)


def save_image(*args, **kwargs):
    """Save molecular visualization as image."""
    try:
        from .pymol_viz import save_image as _save
        return _save(*args, **kwargs)
    except ImportError:
        from .py3dmol_viz import save_image as _save
        return _save(*args, **kwargs)


def save_session(*args, **kwargs):
    """Save PyMOL session file."""
    from .pymol_viz import save_session as _save
    return _save(*args, **kwargs)


def visualize_complex(*args, **kwargs):
    """Visualize protein-ligand complex."""
    try:
        from .pymol_viz import visualize_complex as _viz
        return _viz(*args, **kwargs)
    except ImportError:
        from .py3dmol_viz import visualize_complex as _viz
        return _viz(*args, **kwargs)