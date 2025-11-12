"""
PyMOL-based Visualization Module

Provides high-quality molecular visualization using PyMOL.
"""

from pathlib import Path
from typing import Optional, Union, List, Dict, Any
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


def check_pymol_available() -> bool:
    """Check if PyMOL is available."""
    try:
        import pymol
        return True
    except ImportError:
        return False


def show(
    structure_path: Union[str, Path],
    style: str = "cartoon",
    color: str = "spectrum",
    show_ligand: bool = True,
) -> VisualizationResult:
    """
    Display molecular structure using PyMOL.

    Args:
        structure_path: Path to structure file (PDB, MOL2, SDF)
        style: Display style (cartoon, sticks, spheres, surface)
        color: Color scheme (spectrum, bychain, byfactor, byatom)
        show_ligand: Whether to highlight ligands

    Returns:
        VisualizationResult object

    Example:
        >>> show("protein.pdb", style="cartoon", color="spectrum")
    """
    logger.info(f"Visualizing structure: {structure_path}")

    try:
        import pymol
        from pymol import cmd

        # Initialize PyMOL
        pymol.finish_launching(['pymol', '-q'])

        # Load structure
        structure_path = Path(structure_path)
        if not structure_path.exists():
            return VisualizationResult(
                success=False,
                output_path=None,
                method="pymol",
                error_message=f"File not found: {structure_path}",
            )

        cmd.load(str(structure_path), "structure")
        logger.debug(f"Loaded structure: {structure_path}")

        # Apply style
        cmd.hide("everything", "structure")
        if style == "cartoon":
            cmd.show("cartoon", "structure")
        elif style == "sticks":
            cmd.show("sticks", "structure")
        elif style == "spheres":
            cmd.show("spheres", "structure")
        elif style == "surface":
            cmd.show("surface", "structure")
        else:
            cmd.show("cartoon", "structure")

        # Apply coloring
        if color == "spectrum":
            cmd.spectrum("count", "rainbow", "structure")
        elif color == "bychain":
            cmd.util.cbc("structure")
        elif color == "byfactor":
            cmd.spectrum("b", "rainbow", "structure")
        elif color == "byatom":
            cmd.util.cnc("structure")
        else:
            cmd.color(color, "structure")

        # Highlight ligands
        if show_ligand:
            cmd.select("ligand", "structure and hetatm and not resn HOH")
            if cmd.count_atoms("ligand") > 0:
                cmd.show("sticks", "ligand")
                cmd.color("green", "ligand")
                logger.info("Ligands highlighted in green")

        # Zoom to structure
        cmd.zoom("structure")

        logger.info("Visualization complete")

        return VisualizationResult(
            success=True,
            output_path=None,
            method="pymol",
        )

    except ImportError:
        error_msg = "PyMOL not available. Install with: pip install bioql[viz]"
        logger.error(error_msg)
        return VisualizationResult(
            success=False,
            output_path=None,
            method="pymol",
            error_message=error_msg,
        )

    except Exception as e:
        logger.error(f"Error visualizing structure: {e}")
        return VisualizationResult(
            success=False,
            output_path=None,
            method="pymol",
            error_message=str(e),
        )


def save_image(
    structure_path: Union[str, Path],
    output_path: Union[str, Path],
    width: int = 1920,
    height: int = 1080,
    dpi: int = 300,
    ray_trace: bool = True,
    **kwargs,
) -> VisualizationResult:
    """
    Save molecular structure as high-quality image.

    Args:
        structure_path: Path to structure file
        output_path: Path to save image (PNG, TIFF)
        width: Image width in pixels
        height: Image height in pixels
        dpi: DPI for image quality
        ray_trace: Whether to use ray tracing for publication quality
        **kwargs: Additional styling arguments (style, color, etc.)

    Returns:
        VisualizationResult object

    Example:
        >>> save_image("protein.pdb", "figure.png", ray_trace=True)
    """
    logger.info(f"Rendering image: {structure_path} → {output_path}")

    try:
        import pymol
        from pymol import cmd

        # Initialize PyMOL in headless mode
        pymol.finish_launching(['pymol', '-cq'])

        # Load and style structure
        structure_path = Path(structure_path)
        output_path = Path(output_path)

        if not structure_path.exists():
            return VisualizationResult(
                success=False,
                output_path=None,
                method="pymol",
                error_message=f"File not found: {structure_path}",
            )

        cmd.load(str(structure_path), "structure")

        # Apply styling
        style = kwargs.get("style", "cartoon")
        color = kwargs.get("color", "spectrum")

        cmd.hide("everything", "structure")
        cmd.show(style, "structure")

        if color == "spectrum":
            cmd.spectrum("count", "rainbow", "structure")
        else:
            cmd.color(color, "structure")

        # Highlight ligands if present
        cmd.select("ligand", "structure and hetatm and not resn HOH")
        if cmd.count_atoms("ligand") > 0:
            cmd.show("sticks", "ligand")
            cmd.color("green", "ligand")

        # Set viewport and rendering
        cmd.viewport(width, height)
        cmd.zoom("structure")

        # Set ray tracing options
        if ray_trace:
            cmd.set("ray_opaque_background", 0)
            cmd.set("ray_shadows", 0)
            cmd.ray(width, height)

        # Save image
        cmd.png(str(output_path), width, height, dpi=dpi, ray=1 if ray_trace else 0)

        logger.info(f"Image saved: {output_path}")

        return VisualizationResult(
            success=True,
            output_path=output_path,
            method="pymol",
        )

    except ImportError:
        error_msg = "PyMOL not available. Install with: pip install bioql[viz]"
        logger.error(error_msg)
        return VisualizationResult(
            success=False,
            output_path=None,
            method="pymol",
            error_message=error_msg,
        )

    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return VisualizationResult(
            success=False,
            output_path=None,
            method="pymol",
            error_message=str(e),
        )


def save_session(
    structure_path: Union[str, Path],
    output_path: Union[str, Path],
    **kwargs,
) -> VisualizationResult:
    """
    Save PyMOL session file (.pse).

    Args:
        structure_path: Path to structure file
        output_path: Path to save session (.pse)
        **kwargs: Additional styling arguments

    Returns:
        VisualizationResult object

    Example:
        >>> save_session("complex.pdb", "complex.pse")
    """
    logger.info(f"Saving PyMOL session: {output_path}")

    try:
        import pymol
        from pymol import cmd

        pymol.finish_launching(['pymol', '-cq'])

        structure_path = Path(structure_path)
        output_path = Path(output_path)

        if not structure_path.exists():
            return VisualizationResult(
                success=False,
                output_path=None,
                method="pymol",
                error_message=f"File not found: {structure_path}",
            )

        # Load structure
        cmd.load(str(structure_path), "structure")

        # Apply default styling
        cmd.hide("everything", "structure")
        cmd.show("cartoon", "structure")
        cmd.spectrum("count", "rainbow", "structure")

        # Highlight ligands
        cmd.select("ligand", "structure and hetatm and not resn HOH")
        if cmd.count_atoms("ligand") > 0:
            cmd.show("sticks", "ligand")
            cmd.color("green", "ligand")

        cmd.zoom("structure")

        # Save session
        cmd.save(str(output_path))

        logger.info(f"Session saved: {output_path}")

        return VisualizationResult(
            success=True,
            output_path=output_path,
            method="pymol",
        )

    except ImportError:
        error_msg = "PyMOL not available"
        logger.error(error_msg)
        return VisualizationResult(
            success=False,
            output_path=None,
            method="pymol",
            error_message=error_msg,
        )

    except Exception as e:
        logger.error(f"Error saving session: {e}")
        return VisualizationResult(
            success=False,
            output_path=None,
            method="pymol",
            error_message=str(e),
        )


def visualize_complex(
    receptor_path: Union[str, Path],
    ligand_path: Union[str, Path],
    output_image: Optional[Union[str, Path]] = None,
    output_session: Optional[Union[str, Path]] = None,
) -> VisualizationResult:
    """
    Visualize protein-ligand complex.

    Args:
        receptor_path: Path to receptor PDB file
        ligand_path: Path to ligand file
        output_image: Optional path to save image
        output_session: Optional path to save PyMOL session

    Returns:
        VisualizationResult object

    Example:
        >>> visualize_complex("receptor.pdb", "ligand.mol2", output_image="complex.png")
    """
    logger.info("Visualizing protein-ligand complex")

    try:
        import pymol
        from pymol import cmd

        pymol.finish_launching(['pymol', '-cq'])

        receptor_path = Path(receptor_path)
        ligand_path = Path(ligand_path)

        # Load receptor and ligand
        cmd.load(str(receptor_path), "receptor")
        cmd.load(str(ligand_path), "ligand")

        # Style receptor
        cmd.hide("everything", "receptor")
        cmd.show("cartoon", "receptor")
        cmd.color("cyan", "receptor")

        # Style ligand
        cmd.show("sticks", "ligand")
        cmd.color("green", "ligand")

        # Show binding site
        cmd.select("binding_site", "receptor within 5 of ligand")
        cmd.show("lines", "binding_site")
        cmd.color("yellow", "binding_site")

        # Zoom to binding site
        cmd.zoom("ligand", 8)

        # Save outputs if requested
        if output_image:
            output_image = Path(output_image)
            cmd.ray(1920, 1080)
            cmd.png(str(output_image), dpi=300)
            logger.info(f"Image saved: {output_image}")

        if output_session:
            output_session = Path(output_session)
            cmd.save(str(output_session))
            logger.info(f"Session saved: {output_session}")

        return VisualizationResult(
            success=True,
            output_path=output_image or output_session,
            method="pymol",
        )

    except ImportError:
        error_msg = "PyMOL not available"
        logger.error(error_msg)
        return VisualizationResult(
            success=False,
            output_path=None,
            method="pymol",
            error_message=error_msg,
        )

    except Exception as e:
        logger.error(f"Error visualizing complex: {e}")
        return VisualizationResult(
            success=False,
            output_path=None,
            method="pymol",
            error_message=str(e),
        )