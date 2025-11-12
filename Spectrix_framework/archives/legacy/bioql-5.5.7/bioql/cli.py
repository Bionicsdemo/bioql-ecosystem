#!/usr/bin/env python3
"""
BioQL Command Line Interface
Provides CLI commands for BioQL quantum computing framework
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path
import json
from typing import Optional

from . import __version__, get_info
from .logger import get_logger

# Get logger for CLI operations
logger = get_logger(__name__)

def install_cursor_extension():
    """Install BioQL extension for Cursor IDE"""
    print("🚀 Installing BioQL extension for Cursor IDE...")

    # Get the script path
    script_path = Path(__file__).parent.parent / "install_cursor_extension.py"

    if not script_path.exists():
        print(f"❌ Installation script not found: {script_path}")
        print("Please ensure you have the complete BioQL installation.")
        return False

    try:
        # Run the installation script
        result = subprocess.run([sys.executable, str(script_path)],
                              check=True, capture_output=True, text=True)

        print(result.stdout)
        print("✅ Cursor extension installation completed!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during installation: {e}")
        return False

def install_windsurf_extension():
    """Install BioQL plugin for Windsurf IDE"""
    print("🚀 Installing BioQL plugin for Windsurf IDE...")

    # Get the script path
    script_path = Path(__file__).parent.parent / "install_windsurf_extension.py"

    if not script_path.exists():
        print(f"❌ Installation script not found: {script_path}")
        print("Please ensure you have the complete BioQL installation.")
        return False

    try:
        # Run the installation script
        result = subprocess.run([sys.executable, str(script_path)],
                              check=True, capture_output=True, text=True)

        print(result.stdout)
        print("✅ Windsurf plugin installation completed!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during installation: {e}")
        return False

def show_version():
    """Show BioQL version and system information"""
    print(f"BioQL v{__version__}")

    # Get detailed system info
    info = get_info()

    print("\\nSystem Information:")
    print(f"  Python: {info['python_version']}")
    print(f"  Qiskit: {'✅' if info['qiskit_available'] else '❌'}")

    if info['qiskit_available']:
        print(f"    Version: {info.get('qiskit_version', 'Unknown')}")

    print("\\nOptional Modules:")
    for module, available in info['optional_modules'].items():
        status = '✅' if available else '❌'
        print(f"  {module}: {status}")

def run_quantum_code(code: str, shots: int = 1024, backend: str = "simulator",
                   api_key: str = None, enhanced: bool = True, return_ir: bool = False):
    """Run BioQL quantum code from command line with enhanced DevKit capabilities"""
    try:
        if enhanced:
            # Use enhanced quantum function with DevKit capabilities
            from .enhanced_quantum import enhanced_quantum

            if not api_key:
                print("❌ API key required for BioQL execution")
                print("💡 Get your API key at: https://bioql.com/signup")
                print("🔑 Use --api-key parameter or set BIOQL_API_KEY environment variable")
                return False

            print(f"🚀 Executing enhanced BioQL code with {shots} shots on {backend}...")
            print(f"🧠 Natural Language Processing: Enabled")
            print(f"⚡ IR Compilation: Enabled")
            print(f"Code: {code}")

            # Execute with enhanced capabilities
            result = enhanced_quantum(
                program=code,
                api_key=api_key,
                backend=backend,
                shots=shots,
                use_nlp=True,
                use_ir_compiler=True,
                return_ir=return_ir
            )

            # Handle enhanced result with IR
            if isinstance(result, dict) and 'result' in result:
                quantum_result = result['result']
                ir_program = result['ir']
                enhanced_flag = result['enhanced']

                print(f"\\n✅ Enhanced processing: {enhanced_flag}")
                if ir_program:
                    print(f"🔬 IR Program: {ir_program.name}")
                    if ir_program.operations:
                        print(f"🎯 Domain: {ir_program.operations[0].domain.value}")
                        print(f"⚙️  Operation: {ir_program.operations[0].operation_type}")

                result = quantum_result  # Use quantum result for display

        else:
            # Use original quantum function
            from . import quantum

            print(f"🔬 Executing quantum code with {shots} shots on {backend}...")
            print(f"Code: {code}")

            # Execute the quantum code (requires API key)
            if not api_key:
                print("❌ API key required for BioQL execution")
                print("💡 Get your API key at: https://bioql.com/signup")
                return False

            result = quantum(code, api_key=api_key, shots=shots, backend=backend)

        if result.success:
            print("\\n✅ Execution successful!")
            print(f"📊 Results: {result.counts}")
            print(f"🎲 Total shots: {result.total_shots}")
            print(f"🏆 Most likely outcome: {result.most_likely_outcome}")

            if hasattr(result, 'energy') and result.energy is not None:
                print(f"⚡ Energy: {result.energy}")

            if hasattr(result, 'bio_interpretation') and result.bio_interpretation:
                print(f"🧬 Biological interpretation: {result.bio_interpretation}")

            if hasattr(result, 'cost_estimate') and result.cost_estimate:
                print(f"💰 Cost estimate: ${result.cost_estimate:.4f}")

            # Show enhanced processing metadata
            if hasattr(result, 'metadata') and result.metadata:
                enhanced_processing = result.metadata.get('enhanced_processing', False)
                nlp_used = result.metadata.get('nlp_used', False)
                ir_compiler_used = result.metadata.get('ir_compiler_used', False)

                if enhanced_processing:
                    print(f"🔧 Enhanced processing used")
                    print(f"   🧠 NLP: {'✅' if nlp_used else '❌'}")
                    print(f"   ⚡ IR Compiler: {'✅' if ir_compiler_used else '❌'}")

        else:
            print(f"❌ Execution failed: {result.error_message}")
            return False

        return True

    except ImportError as e:
        print(f"❌ BioQL module not available: {e}")
        print("Please check your installation.")
        return False
    except Exception as e:
        print(f"❌ Error executing quantum code: {e}")
        return False

def compile_bioql_file(file_path: str, output_path: Optional[str] = None):
    """Compile a BioQL file"""
    try:
        from .compiler import compile_bioql

        input_file = Path(file_path)
        if not input_file.exists():
            print(f"❌ File not found: {file_path}")
            return False

        print(f"🔧 Compiling BioQL file: {file_path}")

        # Read the file
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Compile the content
        compiled_result = compile_bioql(content)

        if output_path:
            output_file = Path(output_path)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(compiled_result)
            print(f"✅ Compiled output saved to: {output_path}")
        else:
            print("✅ Compilation successful!")
            print("Compiled code:")
            print(compiled_result)

        return True

    except ImportError:
        print("❌ BioQL compiler not available. Please check your installation.")
        return False
    except Exception as e:
        print(f"❌ Compilation failed: {e}")
        return False

def check_installation():
    """Check if BioQL is properly installed"""
    print("🔍 Checking BioQL installation...")

    try:
        # Direct import test to handle Python path issues
        import importlib

        # Test core BioQL modules
        core_modules = [
            ('qiskit', 'qiskit'),
            ('qiskit_aer', 'qiskit_aer'),
            ('numpy', 'numpy'),
            ('matplotlib', 'matplotlib'),
            ('biopython', 'Bio')
        ]

        missing_modules = []
        for display_name, import_name in core_modules:
            try:
                importlib.import_module(import_name)
            except ImportError:
                missing_modules.append(display_name)

        # Show installation status
        info = get_info()
        print("\\n📋 Installation Summary:")
        print(f"  Version: {info['version']}")
        print(f"  Python: {info['python_version']}")

        if missing_modules:
            print(f"❌ Missing modules: {', '.join(missing_modules)}")
            print("\\n💡 Fix suggestions:")
            print("  1. Check if you're using the correct Python environment")
            print("  2. Try: pip install --upgrade bioql[dev]")
            print("  3. If using pyenv, ensure packages are installed in the active environment")
            return False
        else:
            print("✅ All core modules available")

            # Test BioQL functionality
            try:
                from . import quantum
                print("✅ BioQL quantum module imported successfully")
                return True
            except ImportError as e:
                print(f"❌ BioQL quantum module import failed: {e}")
                return False

    except Exception as e:
        print(f"❌ Installation check failed: {e}")
        return False

def setup_api_keys():
    """Interactive setup for IBM Quantum and IonQ API keys"""
    print("🔐 Setting up API keys for quantum cloud providers")
    print("=" * 50)

    # Determine config directory
    home_dir = Path.home()
    config_dir = home_dir / '.bioql'
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / 'config.json'

    # Load existing config if it exists
    config = {}
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            config = {}

    print("\\nCurrent API key status:")
    print(f"  IBM Quantum: {'✅ Configured' if config.get('ibm_token') else '❌ Not configured'}")
    print(f"  IonQ: {'✅ Configured' if config.get('ionq_token') else '❌ Not configured'}")

    # IBM Quantum setup
    print("\\n🌐 IBM Quantum Setup")
    print("-" * 20)
    print("To get your IBM Quantum token:")
    print("1. Visit: https://quantum-computing.ibm.com/")
    print("2. Sign in or create an account")
    print("3. Go to 'Account' > 'API Token'")
    print("4. Copy your token")

    current_ibm = config.get('ibm_token', '')
    if current_ibm:
        print(f"\\nCurrent IBM token: {current_ibm[:8]}...{current_ibm[-4:]}")
        update_ibm = input("Update IBM Quantum token? (y/N): ").lower().strip()
    else:
        update_ibm = 'y'

    if update_ibm == 'y':
        ibm_token = input("Enter your IBM Quantum token (or press Enter to skip): ").strip()
        if ibm_token:
            config['ibm_token'] = ibm_token
            print("✅ IBM Quantum token saved")
        else:
            print("⏭️  Skipping IBM Quantum setup")

    # IonQ setup
    print("\\n⚛️  IonQ Setup")
    print("-" * 12)
    print("To get your IonQ API key:")
    print("1. Visit: https://cloud.ionq.com/")
    print("2. Sign in or create an account")
    print("3. Go to 'API Keys' in the dashboard")
    print("4. Create a new API key and copy it")

    current_ionq = config.get('ionq_token', '')
    if current_ionq:
        print(f"\\nCurrent IonQ token: {current_ionq[:8]}...{current_ionq[-4:]}")
        update_ionq = input("Update IonQ API key? (y/N): ").lower().strip()
    else:
        update_ionq = 'y'

    if update_ionq == 'y':
        ionq_token = input("Enter your IonQ API key (or press Enter to skip): ").strip()
        if ionq_token:
            config['ionq_token'] = ionq_token
            print("✅ IonQ API key saved")
        else:
            print("⏭️  Skipping IonQ setup")

    # Save configuration
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"\\n✅ Configuration saved to: {config_file}")
        print("\\n💡 Usage examples:")
        if config.get('ibm_token'):
            print("  quantum('simulate protein folding', backend='ibm_brisbane')")
        if config.get('ionq_token'):
            print("  quantum('analyze DNA sequence', backend='ionq_simulator')")

        print("\\n🔒 Security note: API keys are stored locally in ~/.bioql/config.json")
        print("   Make sure to keep this file secure and never share it publicly.")

        return True

    except IOError as e:
        print(f"❌ Failed to save configuration: {e}")
        return False

def create_example_file(name: str = "example.bql"):
    """Create an example BioQL file"""
    example_content = '''# BioQL Example: Quantum Protein Analysis
# This file demonstrates basic BioQL syntax and capabilities

# Create a Bell state for quantum entanglement
create bell state with 2 qubits
apply hadamard gate to qubit 0
apply cnot gate from qubit 0 to qubit 1
measure all qubits

# Analyze protein folding using quantum simulation
analyze protein hemoglobin folding
simulate 100 amino acid interactions
optimize energy landscape using qaoa algorithm
measure folding stability

# DNA sequence alignment with quantum algorithms
align dna sequences ATCGATCGATCG and ATCGATCGATCG
use quantum fourier transform for pattern matching
find optimal alignment with 95% similarity
measure alignment score

# Drug-protein binding simulation
simulate drug aspirin binding to protein cyclooxygenase
model hydrogen bonds using quantum states
calculate binding affinity with 1000 shots
optimize molecular interaction

# Quantum circuit for biological process
create quantum circuit with 3 qubits
initialize qubits in ground state
apply hadamard gates
add measurement operations
execute with 1024 shots
'''

    try:
        file_path = Path(name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(example_content)

        print(f"✅ Example file created: {file_path}")
        print("\\nTo run this example:")
        print(f"  bioql run {name}")
        print("\\nOr execute specific operations:")
        print("  bioql quantum 'create bell state with 2 qubits'")

        return True

    except Exception as e:
        print(f"❌ Failed to create example file: {e}")
        return False

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="BioQL: Quantum Computing for Bioinformatics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enhanced natural language processing (DevKit)
  bioql quantum "Dock ligand SMILES CCO to protein PDB 1ABC" --api-key YOUR_KEY
  bioql quantum "Align DNA sequences ATCG and ATCGATCG" --api-key YOUR_KEY --return-ir

  # Molecular docking (NEW - Drug Discovery Pack)
  bioql dock --receptor protein.pdb --smiles "CC(=O)OC1=CC=CC=C1C(=O)O" --backend vina
  bioql dock --receptor cox2.pdb --smiles "CCO" --backend quantum --api-key YOUR_KEY

  # Visualization (NEW - Drug Discovery Pack)
  bioql visualize --structure complex.pdb --output complex.png
  bioql visualize --structure protein.pdb --ligand ligand.mol2 --output binding.png

  # Dynamic library calls (NEW - Meta-wrapper)
  bioql call "Use RDKit to calculate molecular weight of aspirin SMILES CC(=O)OC1=CC=CC=C1C(=O)O"
  bioql call "Use numpy to calculate mean of array [1, 2, 3, 4, 5]"
  bioql call "Use pandas to read CSV file data.csv and show first 5 rows"

  # Traditional quantum computing
  bioql quantum "Create Bell state" --api-key YOUR_KEY --no-enhanced

  # Development and setup
  bioql install cursor          Install Cursor IDE extension
  bioql install windsurf        Install Windsurf IDE plugin
  bioql compile example.bql     Compile BioQL file
  bioql check                   Check installation
  bioql setup-keys              Configure IBM Quantum and IonQ API keys
  bioql example                 Create example file

🔑 Get your API key at: https://bioql.com/signup
📚 For more information, visit: https://bioql.org
🧬 Drug Discovery Pack: https://docs.bioql.com/drug-discovery
        """
    )

    parser.add_argument('--version', action='version', version=f'BioQL {__version__}')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Install command
    install_parser = subparsers.add_parser('install', help='Install IDE extensions')
    install_parser.add_argument('ide', choices=['cursor', 'windsurf'],
                               help='IDE to install extension for')

    # Quantum command
    quantum_parser = subparsers.add_parser('quantum', help='Run quantum code with DevKit capabilities')
    quantum_parser.add_argument('code', help='BioQL code to execute')
    quantum_parser.add_argument('--shots', type=int, default=1024,
                               help='Number of shots (default: 1024)')
    quantum_parser.add_argument('--backend', default='simulator',
                               help='Quantum backend (default: simulator)')
    quantum_parser.add_argument('--api-key', dest='api_key',
                               help='BioQL API key (required)')
    quantum_parser.add_argument('--enhanced', action='store_true', default=True,
                               help='Use enhanced DevKit capabilities (default: True)')
    quantum_parser.add_argument('--no-enhanced', action='store_false', dest='enhanced',
                               help='Disable enhanced DevKit capabilities')
    quantum_parser.add_argument('--return-ir', action='store_true', dest='return_ir',
                               help='Return intermediate representation (IR) along with results')

    # Compile command
    compile_parser = subparsers.add_parser('compile', help='Compile BioQL file')
    compile_parser.add_argument('file', help='BioQL file to compile')
    compile_parser.add_argument('-o', '--output', help='Output file path')

    # Check command
    subparsers.add_parser('check', help='Check BioQL installation')

    # Version command
    subparsers.add_parser('version', help='Show version information')

    # Setup keys command
    subparsers.add_parser('setup-keys', help='Configure API keys for quantum cloud providers')

    # Example command
    example_parser = subparsers.add_parser('example', help='Create example BioQL file')
    example_parser.add_argument('--name', default='example.bql',
                               help='Example file name (default: example.bql)')

    # Dock command (NEW - Drug Discovery)
    dock_parser = subparsers.add_parser('dock', help='Perform molecular docking')
    dock_parser.add_argument('--receptor', required=True,
                            help='Path to receptor PDB file')
    dock_parser.add_argument('--smiles', dest='ligand_smiles',
                            help='Ligand SMILES string')
    dock_parser.add_argument('--ligand', dest='ligand_file',
                            help='Path to ligand file (alternative to --smiles)')
    dock_parser.add_argument('--backend', default='auto',
                            choices=['auto', 'vina', 'quantum'],
                            help='Docking backend (default: auto)')
    dock_parser.add_argument('--out', dest='output_dir',
                            help='Output directory for results')
    dock_parser.add_argument('--center', nargs=3, type=float, metavar=('X', 'Y', 'Z'),
                            help='Binding site center coordinates')
    dock_parser.add_argument('--box-size', nargs=3, type=float, default=[20, 20, 20],
                            metavar=('X', 'Y', 'Z'), help='Search box size (default: 20 20 20)')
    dock_parser.add_argument('--exhaustiveness', type=int, default=8,
                            help='Vina exhaustiveness (default: 8)')
    dock_parser.add_argument('--api-key', help='API key for quantum backend')

    # Visualize command (NEW - Drug Discovery)
    viz_parser = subparsers.add_parser('visualize', help='Visualize molecular structures')
    viz_parser.add_argument('--structure', required=True,
                           help='Path to structure file (PDB, MOL2, SDF)')
    viz_parser.add_argument('--style', default='cartoon',
                           choices=['cartoon', 'sticks', 'spheres', 'surface'],
                           help='Display style (default: cartoon)')
    viz_parser.add_argument('--output', help='Save image to file')
    viz_parser.add_argument('--session', help='Save PyMOL session file')
    viz_parser.add_argument('--ligand', help='Additional ligand file for complex visualization')

    # Dynamic call command (NEW - Meta-wrapper)
    dynamic_parser = subparsers.add_parser('call', help='Call any Python library via natural language')
    dynamic_parser.add_argument('command', nargs='+',
                               help='Natural language command (e.g., "Use RDKit to calculate molecular weight of aspirin SMILES ...")')

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Execute commands
    try:
        if args.command == 'install':
            if args.ide == 'cursor':
                success = install_cursor_extension()
            elif args.ide == 'windsurf':
                success = install_windsurf_extension()
            else:
                print(f"❌ Unknown IDE: {args.ide}")
                return 1

            return 0 if success else 1

        elif args.command == 'quantum':
            # Get API key from argument or environment
            api_key = args.api_key or os.getenv('BIOQL_API_KEY')

            success = run_quantum_code(
                code=args.code,
                shots=args.shots,
                backend=args.backend,
                api_key=api_key,
                enhanced=args.enhanced,
                return_ir=args.return_ir
            )
            return 0 if success else 1

        elif args.command == 'compile':
            success = compile_bioql_file(args.file, args.output)
            return 0 if success else 1

        elif args.command == 'check':
            success = check_installation()
            return 0 if success else 1

        elif args.command == 'version':
            show_version()
            return 0

        elif args.command == 'setup-keys':
            success = setup_api_keys()
            return 0 if success else 1

        elif args.command == 'example':
            success = create_example_file(args.name)
            return 0 if success else 1

        elif args.command == 'dock':
            # Molecular docking command
            from .docking import dock

            print("🧬 Starting molecular docking...")
            print(f"  Receptor: {args.receptor}")
            print(f"  Ligand: {args.ligand_smiles or args.ligand_file}")
            print(f"  Backend: {args.backend}")

            # Get API key from argument or environment
            api_key = args.api_key or os.getenv('BIOQL_API_KEY')

            result = dock(
                receptor=args.receptor,
                ligand_smiles=args.ligand_smiles,
                ligand_file=args.ligand_file,
                backend=args.backend,
                center=tuple(args.center) if args.center else None,
                box_size=tuple(args.box_size),
                output_dir=args.output_dir,
                exhaustiveness=args.exhaustiveness,
                api_key=api_key,
            )

            if result.success:
                print(f"\\n✅ Docking completed successfully!")
                print(f"  Job ID: {result.job_id}")
                print(f"  Backend: {result.backend}")
                if result.score:
                    print(f"  Score: {result.score:.2f} kcal/mol")
                if result.output_complex:
                    print(f"  Output: {result.output_complex}")
                if result.results_json:
                    print(f"  Results: {result.results_json}")
                return 0
            else:
                print(f"\\n❌ Docking failed: {result.error_message}")
                return 1

        elif args.command == 'visualize':
            # Molecular visualization command
            from .visualize import show, save_image, save_session, visualize_complex

            print(f"🔬 Visualizing: {args.structure}")

            if args.ligand:
                # Visualize complex
                result = visualize_complex(
                    receptor_path=args.structure,
                    ligand_path=args.ligand,
                    output_image=args.output,
                    output_session=args.session,
                )
            elif args.output:
                # Save image
                result = save_image(
                    structure_path=args.structure,
                    output_path=args.output,
                    style=args.style,
                )
            elif args.session:
                # Save session
                result = save_session(
                    structure_path=args.structure,
                    output_path=args.session,
                )
            else:
                # Interactive visualization
                result = show(
                    structure_path=args.structure,
                    style=args.style,
                )

            if hasattr(result, 'success') and result.success:
                print(f"✅ Visualization complete")
                if result.output_path:
                    print(f"  Output: {result.output_path}")
                return 0
            elif hasattr(result, 'success'):
                print(f"❌ Visualization failed: {result.error_message}")
                return 1
            else:
                print(f"✅ Visualization displayed (if in appropriate environment)")
                return 0

        elif args.command == 'call':
            # Dynamic library call command
            from .dynamic_bridge import dynamic_call

            command_str = ' '.join(args.command)
            print(f"🔮 Executing: {command_str}")

            result = dynamic_call(command_str)

            if result.success:
                print(f"\\n✅ Execution successful!")
                print(f"  Library: {result.library}")
                print(f"  Function: {result.function}")
                print(f"  Result: {result.result}")
                if result.code_executed:
                    print(f"\\n  Code executed:")
                    print(f"  {result.code_executed}")
                return 0
            else:
                print(f"\\n❌ Execution failed: {result.error_message}")
                return 1

        else:
            print(f"❌ Unknown command: {args.command}")
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error(f"CLI error: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())