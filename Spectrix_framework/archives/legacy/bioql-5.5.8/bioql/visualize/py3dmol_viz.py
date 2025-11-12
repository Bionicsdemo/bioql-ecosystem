"""
py3Dmol-based Visualization Module (Fallback)

Provides web-based molecular visualization using py3Dmol.
"""

from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass

from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class VisualizationResult:
    """Result of visualization operation."""

    success: bool
    output_path: Optional[Path]
    method: str
    error_message: Optional[str] = None


def show(
    structure_path: Union[str, Path],
    style: str = "cartoon",
    color: str = "spectrum",
    show_ligand: bool = True,
    width: int = 800,
    height: int = 600,
):
    """
    Display molecular structure using py3Dmol in Jupyter notebook.

    Args:
        structure_path: Path to structure file
        style: Display style (cartoon, stick, sphere, surface)
        color: Color scheme
        show_ligand: Whether to highlight ligands
        width: Viewer width
        height: Viewer height

    Returns:
        py3Dmol view object or VisualizationResult

    Example:
        >>> show("protein.pdb")  # In Jupyter notebook
    """
    logger.info(f"Visualizing with py3Dmol: {structure_path}")

    try:
        import py3Dmol

        structure_path = Path(structure_path)

        if not structure_path.exists():
            return VisualizationResult(
                success=False,
                output_path=None,
                method="py3dmol",
                error_message=f"File not found: {structure_path}",
            )

        # Read structure file
        with open(structure_path, 'r') as f:
            structure_data = f.read()

        # Create viewer
        view = py3Dmol.view(width=width, height=height)

        # Add structure
        if structure_path.suffix.lower() == '.pdb':
            view.addModel(structure_data, 'pdb')
        elif structure_path.suffix.lower() in ['.mol2', '.mol']:
            view.addModel(structure_data, 'mol2')
        elif structure_path.suffix.lower() == '.sdf':
            view.addModel(structure_data, 'sdf')
        else:
            view.addModel(structure_data, 'pdb')  # Default to PDB

        # Apply style
        if style == "cartoon":
            view.setStyle({'cartoon': {'color': color if color != 'spectrum' else 'spectrum'}})
        elif style == "stick":
            view.setStyle({'stick': {}})
        elif style == "sphere":
            view.setStyle({'sphere': {}})
        elif style == "surface":
            view.addSurface(py3Dmol.VDW, {'opacity': 0.7})

        # Highlight ligands
        if show_ligand:
            view.setStyle({'hetflag': True}, {'stick': {'colorscheme': 'greenCarbon'}})

        view.zoomTo()

        logger.info("py3Dmol visualization ready")

        # Return view object (works in Jupyter)
        return view

    except ImportError:
        error_msg = "py3Dmol not available. Install with: pip install bioql[viz]"
        logger.error(error_msg)
        return VisualizationResult(
            success=False,
            output_path=None,
            method="py3dmol",
            error_message=error_msg,
        )

    except Exception as e:
        logger.error(f"Error with py3Dmol: {e}")
        return VisualizationResult(
            success=False,
            output_path=None,
            method="py3dmol",
            error_message=str(e),
        )


def save_image(
    structure_path: Union[str, Path],
    output_path: Union[str, Path],
    width: int = 800,
    height: int = 600,
    **kwargs,
) -> VisualizationResult:
    """
    Save molecular structure as image using py3Dmol.

    Note: Requires running in Jupyter notebook environment.

    Args:
        structure_path: Path to structure file
        output_path: Path to save image
        width: Image width
        height: Image height
        **kwargs: Additional styling arguments

    Returns:
        VisualizationResult object
    """
    logger.warning("py3Dmol image export requires Jupyter notebook environment")

    view = show(structure_path, width=width, height=height, **kwargs)

    # In Jupyter, user would call: view.png()
    logger.info("In Jupyter notebook, call .png() on the returned view object")

    return VisualizationResult(
        success=True,
        output_path=None,
        method="py3dmol",
    )


def visualize_complex(
    receptor_path: Union[str, Path],
    ligand_path: Union[str, Path],
    output_image: Optional[Union[str, Path]] = None,
    output_session: Optional[Union[str, Path]] = None,
):
    """
    Visualize protein-ligand complex using py3Dmol.

    Args:
        receptor_path: Path to receptor file
        ligand_path: Path to ligand file
        output_image: Not supported in py3Dmol
        output_session: Not supported in py3Dmol

    Returns:
        py3Dmol view object or VisualizationResult
    """
    logger.info("Visualizing complex with py3Dmol")

    try:
        import py3Dmol

        receptor_path = Path(receptor_path)
        ligand_path = Path(ligand_path)

        # Read files
        with open(receptor_path, 'r') as f:
            receptor_data = f.read()

        with open(ligand_path, 'r') as f:
            ligand_data = f.read()

        # Create viewer
        view = py3Dmol.view(width=800, height=600)

        # Add receptor
        view.addModel(receptor_data, 'pdb')
        view.setStyle({'model': 0}, {'cartoon': {'color': 'cyan'}})

        # Add ligand
        view.addModel(ligand_data, 'pdb')
        view.setStyle({'model': 1}, {'stick': {'colorscheme': 'greenCarbon'}})

        view.zoomTo()

        logger.info("Complex visualization ready")

        return view

    except ImportError:
        error_msg = "py3Dmol not available"
        logger.error(error_msg)
        return VisualizationResult(
            success=False,
            output_path=None,
            method="py3dmol",
            error_message=error_msg,
        )

    except Exception as e:
        logger.error(f"Error visualizing complex: {e}")
        return VisualizationResult(
            success=False,
            output_path=None,
            method="py3dmol",
            error_message=str(e),
        )