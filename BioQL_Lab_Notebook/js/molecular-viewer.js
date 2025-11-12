/**
 * 3D Molecular Viewer Module
 * Uses 3Dmol.js library for interactive molecular visualization
 * All text in English
 */

class MolecularViewer {
    constructor(containerId) {
        this.containerId = containerId;
        this.viewer = null;
        this.models = [];
        this.selectedAtoms = [];
        this.measurementLabels = [];
        this.init();
    }

    /**
     * Initialize the 3Dmol viewer
     */
    init() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error(`Container with ID '${this.containerId}' not found`);
            return;
        }

        // Create 3Dmol viewer
        this.viewer = $3Dmol.createViewer(container, {
            backgroundColor: 'white',
            antialias: true,
            cartoonQuality: 10
        });

        // Set default camera position
        this.viewer.zoomTo();
        this.viewer.render();

        // Setup click handler for atom information
        this.setupClickHandler();
    }

    /**
     * Setup click handler to display atom information
     */
    setupClickHandler() {
        const self = this;
        this.viewer.setClickable({}, true, function(atom, viewer, event, container) {
            if (atom) {
                self.showAtomInfo(atom);
                self.handleAtomSelection(atom);
            }
        });
    }

    /**
     * Display atom information
     */
    showAtomInfo(atom) {
        const info = `
            <strong>Atom Information:</strong><br>
            Element: ${atom.elem}<br>
            Atom: ${atom.atom || 'N/A'}<br>
            Residue: ${atom.resn || 'N/A'}<br>
            Chain: ${atom.chain || 'N/A'}<br>
            Residue #: ${atom.resi || 'N/A'}<br>
            Position: (${atom.x?.toFixed(2)}, ${atom.y?.toFixed(2)}, ${atom.z?.toFixed(2)})
        `;

        // Display in a tooltip or info panel
        this.displayInfoPanel(info);
    }

    /**
     * Display information panel
     */
    displayInfoPanel(content) {
        let infoPanel = document.getElementById('molecule-info-panel');
        if (!infoPanel) {
            infoPanel = document.createElement('div');
            infoPanel.id = 'molecule-info-panel';
            infoPanel.style.cssText = `
                position: absolute;
                top: 10px;
                right: 10px;
                background: rgba(255, 255, 255, 0.95);
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 13px;
                max-width: 250px;
                z-index: 1000;
                border: 1px solid #ddd;
            `;
            document.getElementById(this.containerId).parentElement.appendChild(infoPanel);
        }
        infoPanel.innerHTML = content;
    }

    /**
     * Handle atom selection for distance measurement
     */
    handleAtomSelection(atom) {
        this.selectedAtoms.push(atom);

        // If two atoms selected, measure distance
        if (this.selectedAtoms.length === 2) {
            const dist = this.measureDistance(this.selectedAtoms[0], this.selectedAtoms[1]);
            this.selectedAtoms = []; // Reset selection
        }
    }

    /**
     * Render protein structure from PDB data
     * @param {string} pdbData - PDB format data
     * @param {object} options - Rendering options
     */
    renderProtein(pdbData, options = {}) {
        const defaultOptions = {
            style: 'cartoon',
            color: 'spectrum',
            showSurface: false,
            surfaceOpacity: 0.7
        };
        const opts = { ...defaultOptions, ...options };

        // Clear previous models if specified
        if (options.clear !== false) {
            this.viewer.clear();
            this.models = [];
        }

        // Add model
        const model = this.viewer.addModel(pdbData, 'pdb');
        this.models.push(model);

        // Apply cartoon style for protein
        if (opts.style === 'cartoon') {
            model.setStyle({}, {
                cartoon: {
                    color: opts.color,
                    thickness: 0.5,
                    opacity: 0.9
                }
            });
        } else if (opts.style === 'ribbon') {
            model.setStyle({}, {
                ribbon: {
                    color: opts.color
                }
            });
        } else if (opts.style === 'stick') {
            model.setStyle({}, {
                stick: {
                    colorscheme: opts.color,
                    radius: 0.15
                }
            });
        }

        // Add surface if requested
        if (opts.showSurface) {
            this.viewer.addSurface($3Dmol.SurfaceType.VDW, {
                opacity: opts.surfaceOpacity,
                colorscheme: opts.color
            }, {model: model});
        }

        this.viewer.zoomTo();
        this.viewer.render();

        return model;
    }

    /**
     * Render small molecule
     * @param {string} molData - Molecule data (SDF, MOL2, etc.)
     * @param {string} format - Format type ('sdf', 'mol2', 'xyz', etc.)
     * @param {object} options - Rendering options
     */
    renderMolecule(molData, format = 'sdf', options = {}) {
        const defaultOptions = {
            style: 'stick',
            color: 'default',
            clear: false
        };
        const opts = { ...defaultOptions, ...options };

        // Clear previous models if specified
        if (opts.clear) {
            this.viewer.clear();
            this.models = [];
        }

        // Add model
        const model = this.viewer.addModel(molData, format);
        this.models.push(model);

        // Apply stick style for small molecules
        if (opts.style === 'stick') {
            model.setStyle({}, {
                stick: {
                    radius: 0.2,
                    colorscheme: opts.color === 'default' ? 'default' : opts.color
                },
                sphere: {
                    scale: 0.3,
                    colorscheme: opts.color === 'default' ? 'default' : opts.color
                }
            });
        } else if (opts.style === 'sphere') {
            model.setStyle({}, {
                sphere: {
                    colorscheme: opts.color === 'default' ? 'default' : opts.color
                }
            });
        } else if (opts.style === 'line') {
            model.setStyle({}, {
                line: {
                    colorscheme: opts.color === 'default' ? 'default' : opts.color
                }
            });
        }

        this.viewer.zoomTo();
        this.viewer.render();

        return model;
    }

    /**
     * Render docking result with protein and ligand
     * @param {string} proteinPDB - Protein PDB data
     * @param {string} ligandMOL2 - Ligand MOL2 data
     * @param {object} pose - Pose information
     */
    renderDockingResult(proteinPDB, ligandMOL2, pose = {}) {
        // Clear viewer
        this.viewer.clear();
        this.models = [];

        // Render protein with cartoon style
        const proteinModel = this.renderProtein(proteinPDB, {
            style: 'cartoon',
            color: 'spectrum',
            clear: false
        });

        // Render ligand with stick style
        const ligandModel = this.renderMolecule(ligandMOL2, 'mol2', {
            style: 'stick',
            color: 'greenCarbon',
            clear: false
        });

        // If binding site residues provided, highlight them
        if (pose.bindingSite && pose.bindingSite.length > 0) {
            this.highlightBindingSite(proteinModel, pose.bindingSite);
        }

        // Add pose information to info panel
        if (pose.score || pose.energy) {
            const poseInfo = `
                <strong>Docking Results:</strong><br>
                Score: ${pose.score || 'N/A'}<br>
                Energy: ${pose.energy ? pose.energy.toFixed(2) + ' kcal/mol' : 'N/A'}<br>
                RMSD: ${pose.rmsd ? pose.rmsd.toFixed(2) + ' Å' : 'N/A'}
            `;
            this.displayInfoPanel(poseInfo);
        }

        this.viewer.zoomTo();
        this.viewer.render();

        return { proteinModel, ligandModel };
    }

    /**
     * Highlight binding site residues
     */
    highlightBindingSite(model, residues) {
        residues.forEach(resi => {
            model.setStyle({ resi: resi }, {
                stick: {
                    radius: 0.15,
                    colorscheme: 'cyanCarbon'
                }
            });
        });
        this.viewer.render();
    }

    /**
     * Highlight molecular interactions
     * @param {array} interactions - Array of interaction objects
     */
    highlightInteractions(interactions) {
        interactions.forEach(interaction => {
            const { type, atom1, atom2, distance } = interaction;

            if (type === 'hbond') {
                // Hydrogen bond - show as dashed cyan line
                this.viewer.addCylinder({
                    start: { x: atom1.x, y: atom1.y, z: atom1.z },
                    end: { x: atom2.x, y: atom2.y, z: atom2.z },
                    radius: 0.1,
                    fromCap: 1,
                    toCap: 1,
                    color: 'cyan',
                    dashed: true
                });

                // Add label
                this.viewer.addLabel(`H-bond: ${distance.toFixed(2)} Å`, {
                    position: {
                        x: (atom1.x + atom2.x) / 2,
                        y: (atom1.y + atom2.y) / 2,
                        z: (atom1.z + atom2.z) / 2
                    },
                    backgroundColor: 'rgba(0, 255, 255, 0.7)',
                    fontColor: 'black',
                    fontSize: 10
                });

            } else if (type === 'hydrophobic') {
                // Hydrophobic interaction - show as dashed gray line
                this.viewer.addCylinder({
                    start: { x: atom1.x, y: atom1.y, z: atom1.z },
                    end: { x: atom2.x, y: atom2.y, z: atom2.z },
                    radius: 0.08,
                    fromCap: 1,
                    toCap: 1,
                    color: 'gray',
                    dashed: true
                });

                // Add label
                this.viewer.addLabel(`Hydrophobic: ${distance.toFixed(2)} Å`, {
                    position: {
                        x: (atom1.x + atom2.x) / 2,
                        y: (atom1.y + atom2.y) / 2,
                        z: (atom1.z + atom2.z) / 2
                    },
                    backgroundColor: 'rgba(128, 128, 128, 0.7)',
                    fontColor: 'white',
                    fontSize: 10
                });

            } else if (type === 'salt_bridge') {
                // Salt bridge - show as dashed yellow line
                this.viewer.addCylinder({
                    start: { x: atom1.x, y: atom1.y, z: atom1.z },
                    end: { x: atom2.x, y: atom2.y, z: atom2.z },
                    radius: 0.12,
                    fromCap: 1,
                    toCap: 1,
                    color: 'yellow',
                    dashed: true
                });

                // Add label
                this.viewer.addLabel(`Salt bridge: ${distance.toFixed(2)} Å`, {
                    position: {
                        x: (atom1.x + atom2.x) / 2,
                        y: (atom1.y + atom2.y) / 2,
                        z: (atom1.z + atom2.z) / 2
                    },
                    backgroundColor: 'rgba(255, 255, 0, 0.7)',
                    fontColor: 'black',
                    fontSize: 10
                });

            } else if (type === 'pi_stacking') {
                // Pi-stacking - show as dashed green line
                this.viewer.addCylinder({
                    start: { x: atom1.x, y: atom1.y, z: atom1.z },
                    end: { x: atom2.x, y: atom2.y, z: atom2.z },
                    radius: 0.1,
                    fromCap: 1,
                    toCap: 1,
                    color: 'green',
                    dashed: true
                });

                // Add label
                this.viewer.addLabel(`Pi-stacking: ${distance.toFixed(2)} Å`, {
                    position: {
                        x: (atom1.x + atom2.x) / 2,
                        y: (atom1.y + atom2.y) / 2,
                        z: (atom1.z + atom2.z) / 2
                    },
                    backgroundColor: 'rgba(0, 255, 0, 0.7)',
                    fontColor: 'black',
                    fontSize: 10
                });
            }
        });

        this.viewer.render();
    }

    /**
     * Measure distance between two atoms
     * @param {object} atom1 - First atom
     * @param {object} atom2 - Second atom
     * @returns {number} Distance in Angstroms
     */
    measureDistance(atom1, atom2) {
        const dx = atom1.x - atom2.x;
        const dy = atom1.y - atom2.y;
        const dz = atom1.z - atom2.z;
        const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);

        // Draw line between atoms
        this.viewer.addCylinder({
            start: { x: atom1.x, y: atom1.y, z: atom1.z },
            end: { x: atom2.x, y: atom2.y, z: atom2.z },
            radius: 0.1,
            fromCap: 1,
            toCap: 1,
            color: 'red'
        });

        // Add distance label
        const label = this.viewer.addLabel(`${distance.toFixed(2)} Å`, {
            position: {
                x: (atom1.x + atom2.x) / 2,
                y: (atom1.y + atom2.y) / 2,
                z: (atom1.z + atom2.z) / 2
            },
            backgroundColor: 'rgba(255, 0, 0, 0.8)',
            fontColor: 'white',
            fontSize: 12,
            fontWeight: 'bold'
        });

        this.measurementLabels.push(label);
        this.viewer.render();

        return distance;
    }

    /**
     * Clear all distance measurements
     */
    clearMeasurements() {
        this.viewer.removeAllLabels();
        this.measurementLabels = [];
        this.viewer.render();
    }

    /**
     * Rotate the view
     * @param {number} x - X-axis rotation
     * @param {number} y - Y-axis rotation
     * @param {number} z - Z-axis rotation
     * @param {number} duration - Animation duration in ms
     */
    rotate(x, y, z, duration = 1000) {
        const currentRotation = this.viewer.getView();
        this.viewer.rotate(x, y, z, duration);
        this.viewer.render();
    }

    /**
     * Zoom to fit all molecules
     */
    zoomTo(selection = {}) {
        this.viewer.zoomTo(selection);
        this.viewer.render();
    }

    /**
     * Zoom in/out
     * @param {number} factor - Zoom factor (> 1 zooms in, < 1 zooms out)
     */
    zoom(factor) {
        this.viewer.zoom(factor, 1000);
        this.viewer.render();
    }

    /**
     * Center view on selection
     * @param {object} selection - Selection criteria
     */
    center(selection = {}) {
        this.viewer.center(selection);
        this.viewer.render();
    }

    /**
     * Reset camera to default view
     */
    resetView() {
        this.viewer.zoomTo();
        this.viewer.render();
    }

    /**
     * Set camera position
     * @param {object} position - Camera position {x, y, z}
     */
    setCameraPosition(position) {
        this.viewer.setView(position);
        this.viewer.render();
    }

    /**
     * Spin the view
     * @param {boolean} enable - Enable/disable spinning
     * @param {object} axis - Rotation axis {x, y, z}
     * @param {number} speed - Rotation speed
     */
    spin(enable = true, axis = { y: 1 }, speed = 1) {
        if (enable) {
            this.viewer.spin(axis, speed);
        } else {
            this.viewer.spin(false);
        }
    }

    /**
     * Export current view to PNG
     * @param {string} filename - Output filename
     * @param {number} width - Image width
     * @param {number} height - Image height
     */
    exportToPNG(filename = 'molecule.png', width = 1200, height = 1200) {
        // Render at high quality
        this.viewer.render();

        // Get PNG data
        const canvas = this.viewer.pngURI();

        // Create download link
        const link = document.createElement('a');
        link.href = canvas;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    /**
     * Add custom label to molecule
     * @param {string} text - Label text
     * @param {object} position - 3D position {x, y, z}
     * @param {object} options - Label styling options
     */
    addLabel(text, position, options = {}) {
        const defaultOptions = {
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            fontColor: 'white',
            fontSize: 12,
            fontWeight: 'normal'
        };
        const opts = { ...defaultOptions, ...options };

        this.viewer.addLabel(text, {
            position: position,
            backgroundColor: opts.backgroundColor,
            fontColor: opts.fontColor,
            fontSize: opts.fontSize,
            fontWeight: opts.fontWeight
        });

        this.viewer.render();
    }

    /**
     * Remove all labels
     */
    removeAllLabels() {
        this.viewer.removeAllLabels();
        this.viewer.render();
    }

    /**
     * Clear the viewer
     */
    clear() {
        this.viewer.clear();
        this.models = [];
        this.selectedAtoms = [];
        this.measurementLabels = [];
        this.viewer.render();
    }

    /**
     * Set background color
     * @param {string} color - Background color (hex or named)
     */
    setBackgroundColor(color) {
        this.viewer.setBackgroundColor(color);
        this.viewer.render();
    }

    /**
     * Add surface representation
     * @param {object} selection - Atom selection
     * @param {object} options - Surface options
     */
    addSurface(selection = {}, options = {}) {
        const defaultOptions = {
            opacity: 0.7,
            colorscheme: 'whiteCarbon'
        };
        const opts = { ...defaultOptions, ...options };

        this.viewer.addSurface($3Dmol.SurfaceType.VDW, {
            opacity: opts.opacity,
            colorscheme: opts.colorscheme
        }, selection);

        this.viewer.render();
    }

    /**
     * Remove all surfaces
     */
    removeSurfaces() {
        this.viewer.removeAllSurfaces();
        this.viewer.render();
    }

    /**
     * Style atoms by selection
     * @param {object} selection - Selection criteria
     * @param {object} style - Style object
     */
    setStyle(selection, style) {
        this.viewer.setStyle(selection, style);
        this.viewer.render();
    }

    /**
     * Get current viewer instance
     * @returns {object} 3Dmol viewer instance
     */
    getViewer() {
        return this.viewer;
    }

    /**
     * Render multiple structures
     * @param {array} structures - Array of structure objects
     */
    renderMultiple(structures) {
        this.clear();

        structures.forEach((structure, index) => {
            const { data, format, type, options } = structure;

            if (type === 'protein') {
                this.renderProtein(data, { ...options, clear: false });
            } else if (type === 'molecule') {
                this.renderMolecule(data, format, { ...options, clear: false });
            }
        });

        this.viewer.zoomTo();
        this.viewer.render();
    }

    /**
     * Create animation
     * @param {array} frames - Array of frame configurations
     * @param {number} duration - Duration per frame in ms
     */
    animate(frames, duration = 1000) {
        let currentFrame = 0;

        const playFrame = () => {
            if (currentFrame >= frames.length) {
                currentFrame = 0; // Loop animation
            }

            const frame = frames[currentFrame];
            if (frame.rotation) {
                this.rotate(frame.rotation.x, frame.rotation.y, frame.rotation.z, duration);
            }
            if (frame.zoom) {
                this.zoom(frame.zoom);
            }

            currentFrame++;
            setTimeout(playFrame, duration);
        };

        playFrame();
    }
}

/**
 * Helper function to create a molecular viewer
 * @param {string} containerId - Container element ID
 * @returns {MolecularViewer} Viewer instance
 */
function createMolecularViewer(containerId) {
    return new MolecularViewer(containerId);
}

/**
 * Helper function to load PDB from URL
 * @param {string} url - PDB file URL or PDB ID
 * @returns {Promise<string>} PDB data
 */
async function loadPDB(url) {
    // If it's just a PDB ID (4 characters), fetch from RCSB
    if (url.length === 4) {
        url = `https://files.rcsb.org/download/${url}.pdb`;
    }

    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to load PDB: ${response.statusText}`);
    }
    return await response.text();
}

/**
 * Helper function to calculate interactions between protein and ligand
 * @param {object} proteinModel - Protein model
 * @param {object} ligandModel - Ligand model
 * @param {number} distanceCutoff - Distance cutoff in Angstroms
 * @returns {array} Array of interactions
 */
function detectInteractions(proteinModel, ligandModel, distanceCutoff = 4.5) {
    const interactions = [];
    const proteinAtoms = proteinModel.selectedAtoms({});
    const ligandAtoms = ligandModel.selectedAtoms({});

    // Simple distance-based interaction detection
    ligandAtoms.forEach(ligandAtom => {
        proteinAtoms.forEach(proteinAtom => {
            const dx = ligandAtom.x - proteinAtom.x;
            const dy = ligandAtom.y - proteinAtom.y;
            const dz = ligandAtom.z - proteinAtom.z;
            const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);

            if (distance <= distanceCutoff) {
                // Determine interaction type based on atom types
                let type = 'hydrophobic';

                // H-bond detection (simplified)
                if ((proteinAtom.elem === 'O' || proteinAtom.elem === 'N') &&
                    (ligandAtom.elem === 'O' || ligandAtom.elem === 'N') &&
                    distance <= 3.5) {
                    type = 'hbond';
                }

                interactions.push({
                    type: type,
                    atom1: proteinAtom,
                    atom2: ligandAtom,
                    distance: distance
                });
            }
        });
    });

    return interactions;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        MolecularViewer,
        createMolecularViewer,
        loadPDB,
        detectInteractions
    };
}
