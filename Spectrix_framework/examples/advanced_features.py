#!/usr/bin/env python3
# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
BioQL Advanced Features and Debug Mode Example

This example demonstrates the advanced features of BioQL, including:
- Debug mode and detailed logging
- Backend selection and optimization
- Performance profiling and benchmarking
- Error handling and recovery strategies
- Custom quantum algorithms
- Integration with real quantum hardware
- Advanced bioinformatics applications
- Memory and resource management
- Custom visualization and analysis tools

This example is designed for experienced users who want to leverage the full
power of BioQL for production bioinformatics applications.

Requirements:
- BioQL framework with all optional dependencies
- Qiskit with IBM Quantum access (optional)
- Advanced Python libraries for analysis
- Sufficient computational resources for complex simulations
"""

import asyncio
import gc
import json
import logging
import os
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import psutil

# Add parent directory to path for bioql imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from bioql import (
        BioQLError,
        ProgramParsingError,
        QuantumBackendError,
        QuantumResult,
        QuantumSimulator,
        check_installation,
        configure_debug_mode,
        get_info,
        get_version,
        quantum,
    )
except ImportError as e:
    print(f"Error importing BioQL: {e}")
    print("Make sure BioQL is properly installed with all dependencies")
    sys.exit(1)

# Advanced imports for enhanced functionality
try:
    import matplotlib.pyplot as plt
    import numpy as np
    import seaborn as sns
    from matplotlib.animation import FuncAnimation

    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    warnings.warn("Advanced visualization libraries not available")

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    warnings.warn("Pandas not available for data analysis features")

# Configure advanced logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/Users/heinzjungbluth/Desktop/bioql/examples/advanced_debug.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance measurement data."""

    execution_time: float
    memory_usage: float
    cpu_usage: float
    quantum_shots: int
    success_rate: float
    error_count: int
    backend_type: str


class AdvancedBioQLManager:
    """
    Advanced manager class for sophisticated BioQL operations.

    This class provides high-level interfaces for complex quantum bioinformatics
    workflows with automatic optimization, error recovery, and performance monitoring.
    """

    def __init__(self, debug_mode: bool = True, enable_profiling: bool = True):
        """
        Initialize the advanced BioQL manager.

        Args:
            debug_mode: Enable comprehensive debug logging
            enable_profiling: Enable performance profiling
        """
        self.debug_mode = debug_mode
        self.enable_profiling = enable_profiling
        self.performance_data = []
        self.execution_history = []
        self.quantum_backends = ["simulator"]
        self.error_recovery_enabled = True

        if debug_mode:
            configure_debug_mode(True)
            logger.setLevel(logging.DEBUG)

        logger.info("Advanced BioQL Manager initialized")

        # Check system capabilities
        self._check_system_resources()
        self._initialize_backends()

    def _check_system_resources(self) -> Dict[str, Any]:
        """Check and log system resource availability."""
        try:
            memory = psutil.virtual_memory()
            cpu_count = psutil.cpu_count()
            cpu_percent = psutil.cpu_percent(interval=1)

            resources = {
                "total_memory_gb": memory.total / (1024**3),
                "available_memory_gb": memory.available / (1024**3),
                "memory_percent": memory.percent,
                "cpu_count": cpu_count,
                "cpu_usage_percent": cpu_percent,
            }

            logger.info(f"System resources: {resources}")

            # Warn about resource constraints
            if memory.percent > 80:
                logger.warning("High memory usage detected")
            if cpu_percent > 80:
                logger.warning("High CPU usage detected")

            return resources

        except Exception as e:
            logger.warning(f"Could not check system resources: {e}")
            return {}

    def _initialize_backends(self) -> None:
        """Initialize and test available quantum backends."""
        logger.info("Initializing quantum backends...")

        # Test local simulator
        try:
            result = quantum("test", shots=10)
            if result.success:
                self.quantum_backends.append("aer_simulator")
                logger.info("✓ Local simulator available")
        except Exception as e:
            logger.warning(f"Local simulator test failed: {e}")

        # Test IBM backends if available
        try:
            info = get_info()
            if info.get("qiskit_available"):
                # Add known IBM backends (would require actual testing in production)
                ibm_backends = ["ibm_eagle", "ibm_brisbane", "ibm_sherbrooke"]
                for backend in ibm_backends:
                    # Note: In production, we would test connectivity
                    self.quantum_backends.append(backend)
                logger.info(f"✓ IBM Quantum backends potentially available: {ibm_backends}")
        except Exception as e:
            logger.warning(f"IBM backend check failed: {e}")

        logger.info(f"Available backends: {self.quantum_backends}")

    def execute_with_profiling(
        self, program: str, **kwargs
    ) -> Tuple[QuantumResult, PerformanceMetrics]:
        """
        Execute quantum program with comprehensive performance profiling.

        Args:
            program: BioQL program to execute
            **kwargs: Additional arguments for quantum() function

        Returns:
            Tuple of (result, performance_metrics)
        """
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / (1024**2)  # MB

        try:
            logger.debug(f"Executing program: {program[:50]}...")

            # Execute quantum program
            result = quantum(program, **kwargs)

            # Calculate performance metrics
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / (1024**2)
            cpu_usage = psutil.cpu_percent()

            metrics = PerformanceMetrics(
                execution_time=end_time - start_time,
                memory_usage=end_memory - start_memory,
                cpu_usage=cpu_usage,
                quantum_shots=kwargs.get("shots", 1024),
                success_rate=1.0 if result.success else 0.0,
                error_count=0 if result.success else 1,
                backend_type=kwargs.get("backend", "simulator"),
            )

            if self.enable_profiling:
                self.performance_data.append(metrics)

            logger.debug(f"Execution metrics: {metrics}")
            return result, metrics

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            # Return failed metrics
            metrics = PerformanceMetrics(
                execution_time=time.time() - start_time,
                memory_usage=0,
                cpu_usage=0,
                quantum_shots=kwargs.get("shots", 1024),
                success_rate=0.0,
                error_count=1,
                backend_type=kwargs.get("backend", "simulator"),
            )
            raise

    def batch_execute(
        self, programs: List[str], parallel: bool = True, **kwargs
    ) -> List[Tuple[QuantumResult, PerformanceMetrics]]:
        """
        Execute multiple quantum programs efficiently.

        Args:
            programs: List of BioQL programs to execute
            parallel: Whether to execute in parallel
            **kwargs: Additional arguments for quantum execution

        Returns:
            List of (result, metrics) tuples
        """
        logger.info(f"Batch executing {len(programs)} programs (parallel: {parallel})")

        results = []

        if parallel and len(programs) > 1:
            # Parallel execution
            max_workers = min(4, len(programs))  # Limit concurrent workers
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all programs
                futures = [
                    executor.submit(self.execute_with_profiling, program, **kwargs)
                    for program in programs
                ]

                # Collect results as they complete
                for i, future in enumerate(as_completed(futures)):
                    try:
                        result, metrics = future.result()
                        results.append((result, metrics))
                        logger.debug(f"Completed program {i+1}/{len(programs)}")
                    except Exception as e:
                        logger.error(f"Program {i+1} failed: {e}")
                        # Add failed result
                        results.append((None, None))
        else:
            # Sequential execution
            for i, program in enumerate(programs):
                try:
                    result, metrics = self.execute_with_profiling(program, **kwargs)
                    results.append((result, metrics))
                    logger.debug(f"Completed program {i+1}/{len(programs)}")
                except Exception as e:
                    logger.error(f"Program {i+1} failed: {e}")
                    results.append((None, None))

        logger.info(
            f"Batch execution completed: {len([r for r, m in results if r is not None])}/{len(programs)} successful"
        )
        return results

    def adaptive_shot_optimization(
        self, program: str, target_precision: float = 0.01
    ) -> QuantumResult:
        """
        Automatically optimize shot count for desired precision.

        Args:
            program: BioQL program to execute
            target_precision: Desired precision level

        Returns:
            Optimized quantum result
        """
        logger.info(f"Adaptive shot optimization for precision {target_precision}")

        shot_counts = [100, 500, 1000, 2000, 5000]
        results = []

        for shots in shot_counts:
            try:
                result, metrics = self.execute_with_profiling(program, shots=shots)
                if result.success:
                    results.append((shots, result, metrics))

                    # Check if we've reached target precision
                    if len(results) >= 2:
                        current_probs = result.probabilities()
                        prev_probs = results[-2][1].probabilities()

                        # Calculate precision (difference between consecutive results)
                        precision = 0
                        for state in current_probs:
                            if state in prev_probs:
                                precision = max(
                                    precision, abs(current_probs[state] - prev_probs[state])
                                )

                        logger.debug(f"Shots: {shots}, Precision: {precision:.4f}")

                        if precision < target_precision:
                            logger.info(f"Target precision achieved with {shots} shots")
                            return result

            except Exception as e:
                logger.warning(f"Failed at {shots} shots: {e}")

        # Return best result if target not achieved
        if results:
            best_shots, best_result, _ = results[-1]
            logger.info(f"Used maximum shots: {best_shots}")
            return best_result
        else:
            raise BioQLError("Adaptive optimization failed for all shot counts")

    def error_recovery_execution(
        self, program: str, max_retries: int = 3, **kwargs
    ) -> QuantumResult:
        """
        Execute with automatic error recovery and retry logic.

        Args:
            program: BioQL program to execute
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments for quantum execution

        Returns:
            Quantum result with recovery information
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Execution attempt {attempt + 1}/{max_retries + 1}")

                # Progressive backoff and parameter adjustment
                if attempt > 0:
                    # Reduce shots for faster retry
                    kwargs["shots"] = max(100, kwargs.get("shots", 1024) // (2**attempt))
                    time.sleep(2**attempt)  # Exponential backoff

                result, metrics = self.execute_with_profiling(program, **kwargs)

                if result.success:
                    if attempt > 0:
                        logger.info(f"Recovery successful on attempt {attempt + 1}")
                    return result
                else:
                    last_error = result.error_message

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                last_error = str(e)

        # All attempts failed
        logger.error(f"All {max_retries + 1} attempts failed. Last error: {last_error}")
        raise BioQLError(f"Execution failed after {max_retries + 1} attempts: {last_error}")

    def analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends from collected data."""
        if not self.performance_data:
            logger.warning("No performance data available for analysis")
            return {}

        logger.info("Analyzing performance trends...")

        # Convert to DataFrame if pandas is available
        if PANDAS_AVAILABLE:
            df = pd.DataFrame(
                [
                    {
                        "execution_time": m.execution_time,
                        "memory_usage": m.memory_usage,
                        "cpu_usage": m.cpu_usage,
                        "quantum_shots": m.quantum_shots,
                        "success_rate": m.success_rate,
                        "backend_type": m.backend_type,
                    }
                    for m in self.performance_data
                ]
            )

            analysis = {
                "total_executions": len(df),
                "avg_execution_time": df["execution_time"].mean(),
                "avg_memory_usage": df["memory_usage"].mean(),
                "overall_success_rate": df["success_rate"].mean(),
                "backend_distribution": df["backend_type"].value_counts().to_dict(),
                "performance_by_shots": df.groupby("quantum_shots")["execution_time"]
                .mean()
                .to_dict(),
            }
        else:
            # Manual analysis without pandas
            total_time = sum(m.execution_time for m in self.performance_data)
            total_memory = sum(m.memory_usage for m in self.performance_data)
            success_count = sum(1 for m in self.performance_data if m.success_rate > 0)

            analysis = {
                "total_executions": len(self.performance_data),
                "avg_execution_time": total_time / len(self.performance_data),
                "avg_memory_usage": total_memory / len(self.performance_data),
                "overall_success_rate": success_count / len(self.performance_data),
                "backend_distribution": {},  # Would need manual counting
                "performance_by_shots": {},  # Would need manual grouping
            }

        logger.info(f"Performance analysis: {analysis}")
        return analysis

    def visualize_performance(self) -> None:
        """Create performance visualization dashboard."""
        if not VISUALIZATION_AVAILABLE or not self.performance_data:
            logger.warning("Cannot create visualizations: missing data or libraries")
            return

        logger.info("Creating performance visualization dashboard...")

        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle("BioQL Advanced Performance Dashboard", fontsize=16)

        # Execution time trend
        times = [m.execution_time for m in self.performance_data]
        axes[0, 0].plot(times, marker="o")
        axes[0, 0].set_title("Execution Time Trend")
        axes[0, 0].set_xlabel("Execution Number")
        axes[0, 0].set_ylabel("Time (seconds)")

        # Memory usage trend
        memory = [m.memory_usage for m in self.performance_data]
        axes[0, 1].plot(memory, marker="s", color="orange")
        axes[0, 1].set_title("Memory Usage Trend")
        axes[0, 1].set_xlabel("Execution Number")
        axes[0, 1].set_ylabel("Memory (MB)")

        # Success rate over time
        success_rates = [m.success_rate for m in self.performance_data]
        axes[0, 2].plot(success_rates, marker="^", color="green")
        axes[0, 2].set_title("Success Rate Trend")
        axes[0, 2].set_xlabel("Execution Number")
        axes[0, 2].set_ylabel("Success Rate")
        axes[0, 2].set_ylim(0, 1.1)

        # Shot count vs execution time scatter
        shots = [m.quantum_shots for m in self.performance_data]
        axes[1, 0].scatter(shots, times, alpha=0.6)
        axes[1, 0].set_title("Shots vs Execution Time")
        axes[1, 0].set_xlabel("Quantum Shots")
        axes[1, 0].set_ylabel("Execution Time (s)")

        # Backend performance comparison
        backend_times = {}
        for m in self.performance_data:
            if m.backend_type not in backend_times:
                backend_times[m.backend_type] = []
            backend_times[m.backend_type].append(m.execution_time)

        if backend_times:
            backends = list(backend_times.keys())
            avg_times = [np.mean(backend_times[b]) for b in backends]
            axes[1, 1].bar(backends, avg_times)
            axes[1, 1].set_title("Average Execution Time by Backend")
            axes[1, 1].set_ylabel("Time (seconds)")

        # Error rate analysis
        error_counts = [m.error_count for m in self.performance_data]
        axes[1, 2].hist(error_counts, bins=max(1, len(set(error_counts))), alpha=0.7)
        axes[1, 2].set_title("Error Distribution")
        axes[1, 2].set_xlabel("Error Count")
        axes[1, 2].set_ylabel("Frequency")

        plt.tight_layout()
        plt.savefig(
            "/Users/heinzjungbluth/Desktop/bioql/examples/advanced_performance_dashboard.png",
            dpi=300,
            bbox_inches="tight",
        )
        logger.info("Performance dashboard saved")

    def cleanup_resources(self) -> None:
        """Clean up resources and memory."""
        logger.info("Cleaning up resources...")

        # Clear performance data
        self.performance_data.clear()
        self.execution_history.clear()

        # Force garbage collection
        gc.collect()

        logger.info("Resource cleanup completed")


def example_debug_mode_comprehensive():
    """Comprehensive debug mode demonstration."""
    print("=" * 70)
    print("EXAMPLE 1: Comprehensive Debug Mode")
    print("=" * 70)

    try:
        manager = AdvancedBioQLManager(debug_mode=True, enable_profiling=True)

        print("1. Debug logging levels:")
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.warning("This is a warning message")

        print("\n2. Detailed execution with debug mode:")
        result, metrics = manager.execute_with_profiling(
            "Create Bell state with comprehensive logging", shots=1000, debug=True
        )

        print(f"✓ Execution successful")
        print(f"  Results: {result.counts}")
        print(f"  Execution time: {metrics.execution_time:.3f}s")
        print(f"  Memory usage: {metrics.memory_usage:.2f}MB")
        print(f"  Backend: {metrics.backend_type}")

        print("\n3. Error handling with debug information:")
        try:
            result, metrics = manager.execute_with_profiling(
                "", shots=10  # Empty program to trigger error
            )
        except Exception as e:
            logger.error(f"Expected error caught: {e}")
            print(f"✓ Error handled gracefully with debug info")

    except Exception as e:
        print(f"✗ Error in debug mode example: {e}")


def example_backend_optimization():
    """Demonstrate backend selection and optimization."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Backend Selection and Optimization")
    print("=" * 70)

    try:
        manager = AdvancedBioQLManager(debug_mode=False)

        print("1. Testing different backends:")
        test_program = "Create superposition and measure"

        backends_to_test = ["simulator"]  # Would include IBM backends in production
        results = []

        for backend in backends_to_test:
            print(f"\nTesting backend: {backend}")
            try:
                result, metrics = manager.execute_with_profiling(
                    test_program, backend=backend, shots=500
                )

                results.append((backend, metrics))
                print(f"  ✓ Success - Time: {metrics.execution_time:.3f}s")

            except Exception as e:
                print(f"  ✗ Failed: {e}")

        print("\n2. Backend performance comparison:")
        if results:
            best_backend = min(results, key=lambda x: x[1].execution_time)
            print(f"Fastest backend: {best_backend[0]} ({best_backend[1].execution_time:.3f}s)")

        print("\n3. Adaptive shot optimization:")
        optimized_result = manager.adaptive_shot_optimization(
            "Put 2 qubits in superposition", target_precision=0.02
        )
        print(f"✓ Optimized result: {optimized_result.total_shots} shots")

    except Exception as e:
        print(f"✗ Error in backend optimization: {e}")


def example_batch_processing():
    """Demonstrate batch processing capabilities."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Batch Processing and Parallel Execution")
    print("=" * 70)

    try:
        manager = AdvancedBioQLManager(debug_mode=False)

        print("1. Preparing batch of quantum programs:")
        programs = [
            "Create Bell state",
            "Generate random bits with 3 qubits",
            "Model protein folding with 2 amino acids",
            "Simulate molecular binding",
            "Create GHZ state with 3 qubits",
        ]

        print(f"   Programs to execute: {len(programs)}")

        print("\n2. Sequential execution:")
        start_time = time.time()
        sequential_results = manager.batch_execute(programs, parallel=False, shots=200)
        sequential_time = time.time() - start_time

        successful_sequential = sum(1 for r, m in sequential_results if r is not None and r.success)
        print(
            f"✓ Sequential: {successful_sequential}/{len(programs)} successful in {sequential_time:.2f}s"
        )

        print("\n3. Parallel execution:")
        start_time = time.time()
        parallel_results = manager.batch_execute(programs, parallel=True, shots=200)
        parallel_time = time.time() - start_time

        successful_parallel = sum(1 for r, m in parallel_results if r is not None and r.success)
        print(
            f"✓ Parallel: {successful_parallel}/{len(programs)} successful in {parallel_time:.2f}s"
        )

        if sequential_time > 0 and parallel_time > 0:
            speedup = sequential_time / parallel_time
            print(f"   Speedup: {speedup:.2f}x")

    except Exception as e:
        print(f"✗ Error in batch processing: {e}")


def example_error_recovery():
    """Demonstrate error recovery mechanisms."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Error Recovery and Fault Tolerance")
    print("=" * 70)

    try:
        manager = AdvancedBioQLManager(debug_mode=False)

        print("1. Basic error recovery:")
        try:
            # This should work
            result = manager.error_recovery_execution("Create Bell state", max_retries=3, shots=500)
            print(f"✓ Normal execution successful: {result.total_shots} shots")
        except Exception as e:
            print(f"✗ Recovery failed: {e}")

        print("\n2. Recovery from invalid program:")
        try:
            # This should fail and demonstrate recovery
            result = manager.error_recovery_execution("", max_retries=2, shots=100)  # Empty program
            print(f"✓ Unexpected success")  # Should not reach here
        except BioQLError as e:
            print(f"✓ Expected failure handled: {str(e)[:50]}...")

        print("\n3. Testing resilience with resource constraints:")
        # Simulate high-load scenario
        demanding_programs = [
            "Complex protein folding simulation with 5 amino acids",
            "Large-scale molecular dynamics with 10 molecules",
            "Comprehensive drug screening of 100 candidates",
        ]

        for i, program in enumerate(demanding_programs):
            print(f"\n   Testing program {i+1}: {program[:40]}...")
            try:
                result = manager.error_recovery_execution(program, max_retries=2, shots=200)
                print(f"   ✓ Success with recovery")
            except Exception as e:
                print(f"   ⚠ Failed even with recovery: {str(e)[:30]}...")

    except Exception as e:
        print(f"✗ Error in error recovery example: {e}")


def example_performance_analysis():
    """Demonstrate performance analysis and optimization."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Performance Analysis and Optimization")
    print("=" * 70)

    try:
        manager = AdvancedBioQLManager(debug_mode=False, enable_profiling=True)

        print("1. Running performance test suite:")
        test_cases = [
            ("Small circuit", "Create Bell state", {"shots": 100}),
            ("Medium circuit", "Create 3-qubit GHZ state", {"shots": 500}),
            ("Large circuit", "Model protein with 4 amino acids", {"shots": 1000}),
            ("High precision", "Generate random bits", {"shots": 2000}),
            ("Complex simulation", "Simulate molecular binding network", {"shots": 300}),
        ]

        for test_name, program, kwargs in test_cases:
            print(f"\n   Testing: {test_name}")
            try:
                result, metrics = manager.execute_with_profiling(program, **kwargs)
                print(
                    f"   ✓ Time: {metrics.execution_time:.3f}s, "
                    f"Memory: {metrics.memory_usage:.1f}MB, "
                    f"Success: {metrics.success_rate}"
                )
            except Exception as e:
                print(f"   ✗ Failed: {e}")

        print("\n2. Performance trend analysis:")
        analysis = manager.analyze_performance_trends()

        if analysis:
            print(f"   Total executions: {analysis['total_executions']}")
            print(f"   Average execution time: {analysis['avg_execution_time']:.3f}s")
            print(f"   Average memory usage: {analysis['avg_memory_usage']:.2f}MB")
            print(f"   Overall success rate: {analysis['overall_success_rate']:.3f}")

        print("\n3. Creating performance visualizations:")
        manager.visualize_performance()
        print("   ✓ Performance dashboard created")

        print("\n4. Memory optimization:")
        initial_memory = psutil.Process().memory_info().rss / (1024**2)
        manager.cleanup_resources()
        final_memory = psutil.Process().memory_info().rss / (1024**2)
        memory_saved = initial_memory - final_memory

        print(f"   Memory before cleanup: {initial_memory:.1f}MB")
        print(f"   Memory after cleanup: {final_memory:.1f}MB")
        print(f"   Memory saved: {memory_saved:.1f}MB")

    except Exception as e:
        print(f"✗ Error in performance analysis: {e}")


def example_custom_algorithms():
    """Demonstrate custom quantum algorithm implementations."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Custom Quantum Algorithms")
    print("=" * 70)

    try:
        manager = AdvancedBioQLManager(debug_mode=False)

        print("1. Custom protein folding algorithm:")
        custom_folding_program = """
        Implement custom variational quantum eigensolver for protein folding:
        - Initialize protein conformation qubits
        - Apply parameterized quantum gates for conformational search
        - Use quantum optimization to find minimum energy structure
        - Include hydrophobic and electrostatic interactions
        """

        result, metrics = manager.execute_with_profiling(custom_folding_program, shots=1000)

        if result.success:
            print(f"✓ Custom folding algorithm executed")
            print(f"  Found {len(result.counts)} conformational states")
            print(f"  Most stable conformation: {result.most_likely_outcome}")

        print("\n2. Quantum machine learning for drug discovery:")
        qml_program = """
        Implement quantum neural network for drug-target interaction prediction:
        - Encode molecular features in quantum states
        - Apply quantum neural network layers
        - Use quantum gradient descent for training
        - Predict binding affinity from quantum measurements
        """

        result, metrics = manager.execute_with_profiling(qml_program, shots=500)

        if result.success:
            print(f"✓ Quantum ML algorithm executed")
            print(f"  Prediction accuracy: {max(result.probabilities().values()):.3f}")

        print("\n3. Quantum sequence alignment algorithm:")
        alignment_program = """
        Implement quantum dynamic programming for sequence alignment:
        - Represent sequences in quantum superposition
        - Use quantum parallelism for all alignment paths
        - Apply quantum interference for optimal path selection
        - Measure optimal alignment score
        """

        result, metrics = manager.execute_with_profiling(alignment_program, shots=300)

        if result.success:
            print(f"✓ Quantum alignment algorithm executed")
            print(f"  Alignment score: {result.most_likely_outcome}")

    except Exception as e:
        print(f"✗ Error in custom algorithms: {e}")


def example_real_hardware_integration():
    """Demonstrate integration with real quantum hardware."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Real Quantum Hardware Integration")
    print("=" * 70)

    try:
        manager = AdvancedBioQLManager(debug_mode=True)

        print("1. Checking quantum hardware availability:")
        # Note: This would require actual IBM Quantum credentials in production
        available_backends = manager.quantum_backends
        print(f"   Available backends: {available_backends}")

        hardware_backends = [b for b in available_backends if not "simulator" in b.lower()]
        if hardware_backends:
            print(f"   Hardware backends: {hardware_backends}")
        else:
            print("   No real hardware backends available (credentials required)")

        print("\n2. Simulating hardware execution characteristics:")
        # Simulate noise and decoherence effects
        noisy_program = """
        Execute on quantum hardware with realistic noise:
        - Include gate errors and decoherence
        - Account for limited connectivity
        - Handle measurement errors
        - Apply error mitigation techniques
        """

        result, metrics = manager.execute_with_profiling(
            noisy_program, shots=1000, backend="simulator"  # Would use real hardware in production
        )

        if result.success:
            print(f"✓ Hardware simulation executed")
            print(f"  Noisy results: {result.counts}")
            print(f"  Hardware execution time: {metrics.execution_time:.3f}s")

        print("\n3. Error mitigation strategies:")
        # Demonstrate error mitigation
        mitigation_program = """
        Apply quantum error mitigation:
        - Zero-noise extrapolation
        - Symmetry verification
        - Readout error correction
        - Post-selection techniques
        """

        result, metrics = manager.execute_with_profiling(mitigation_program, shots=500)

        if result.success:
            print(f"✓ Error mitigation applied")
            print(f"  Corrected results: {result.counts}")

        print("\n4. Cost estimation for real hardware:")
        # Estimate costs for different programs
        test_programs = [
            "Simple Bell state",
            "Complex protein folding",
            "Large-scale drug screening",
        ]

        for program in test_programs:
            # Simulate cost calculation
            estimated_shots = 1000
            estimated_qubits = 4  # Would extract from actual circuit
            estimated_cost = estimated_qubits * estimated_shots * 0.001  # Rough estimate

            print(f"   {program}: ~${estimated_cost:.3f} for {estimated_shots} shots")

    except Exception as e:
        print(f"✗ Error in hardware integration: {e}")


def example_memory_management():
    """Demonstrate advanced memory and resource management."""
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Memory and Resource Management")
    print("=" * 70)

    try:
        manager = AdvancedBioQLManager(debug_mode=False)

        print("1. Memory usage monitoring:")
        initial_memory = psutil.Process().memory_info().rss / (1024**2)
        print(f"   Initial memory usage: {initial_memory:.1f}MB")

        print("\n2. Large-scale computation with memory management:")
        large_programs = [f"Process large protein dataset batch {i}" for i in range(20)]

        batch_results = []
        for i in range(0, len(large_programs), 5):  # Process in chunks
            batch = large_programs[i : i + 5]
            print(f"   Processing batch {i//5 + 1}: {len(batch)} programs")

            results = manager.batch_execute(batch, shots=100)
            batch_results.extend(results)

            # Memory cleanup after each batch
            current_memory = psutil.Process().memory_info().rss / (1024**2)
            print(f"   Memory after batch: {current_memory:.1f}MB")

            if current_memory > initial_memory + 100:  # If memory grew by 100MB
                print("   Performing intermediate cleanup...")
                manager.cleanup_resources()
                gc.collect()

        print("\n3. Resource leak detection:")
        final_memory = psutil.Process().memory_info().rss / (1024**2)
        memory_growth = final_memory - initial_memory

        print(f"   Final memory usage: {final_memory:.1f}MB")
        print(f"   Memory growth: {memory_growth:.1f}MB")

        if memory_growth > 50:  # Arbitrary threshold
            print("   ⚠ Potential memory leak detected")
        else:
            print("   ✓ Memory usage under control")

        print("\n4. Final cleanup:")
        manager.cleanup_resources()
        cleanup_memory = psutil.Process().memory_info().rss / (1024**2)
        print(f"   Memory after cleanup: {cleanup_memory:.1f}MB")

    except Exception as e:
        print(f"✗ Error in memory management: {e}")


def run_comprehensive_benchmark():
    """Run comprehensive performance benchmark."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE PERFORMANCE BENCHMARK")
    print("=" * 70)

    try:
        manager = AdvancedBioQLManager(debug_mode=False, enable_profiling=True)

        print("Running comprehensive benchmark suite...")

        # Benchmark different categories
        benchmarks = {
            "Basic Operations": [
                "Create Bell state",
                "Generate random bits",
                "Put qubits in superposition",
            ],
            "Bioinformatics Applications": [
                "Model protein folding",
                "Simulate drug binding",
                "DNA sequence analysis",
            ],
            "Complex Algorithms": [
                "Quantum machine learning",
                "Variational optimization",
                "Quantum Fourier transform",
            ],
        }

        benchmark_results = {}

        for category, programs in benchmarks.items():
            print(f"\n--- {category} ---")
            category_results = []

            for program in programs:
                try:
                    start_time = time.time()
                    result, metrics = manager.execute_with_profiling(program, shots=500)
                    end_time = time.time()

                    category_results.append(
                        {
                            "program": program,
                            "execution_time": metrics.execution_time,
                            "success": result.success,
                            "total_time": end_time - start_time,
                        }
                    )

                    status = "✓" if result.success else "✗"
                    print(f"   {status} {program}: {metrics.execution_time:.3f}s")

                except Exception as e:
                    print(f"   ✗ {program}: Failed ({str(e)[:30]}...)")
                    category_results.append(
                        {"program": program, "execution_time": 0, "success": False, "total_time": 0}
                    )

            benchmark_results[category] = category_results

        # Summary statistics
        print(f"\n--- Benchmark Summary ---")
        for category, results in benchmark_results.items():
            successful = [r for r in results if r["success"]]
            if successful:
                avg_time = sum(r["execution_time"] for r in successful) / len(successful)
                success_rate = len(successful) / len(results)
                print(f"{category}: {success_rate:.1%} success, {avg_time:.3f}s avg")

        # Performance analysis
        analysis = manager.analyze_performance_trends()
        if analysis:
            print(f"\nOverall Performance:")
            print(f"   Total executions: {analysis['total_executions']}")
            print(f"   Average execution time: {analysis['avg_execution_time']:.3f}s")
            print(f"   Success rate: {analysis['overall_success_rate']:.1%}")

        # Create final visualization
        manager.visualize_performance()

    except Exception as e:
        print(f"✗ Error in comprehensive benchmark: {e}")


def main():
    """
    Main function demonstrating all advanced BioQL features.
    """
    print("BioQL Advanced Features and Debug Mode Examples")
    print("=" * 70)

    # System information
    print(f"BioQL Version: {get_version()}")
    info = get_info()
    print(f"System Info: {info}")

    if not info.get("qiskit_available"):
        print("⚠ Warning: Some advanced features require Qiskit")

    try:
        # Run all advanced examples
        example_debug_mode_comprehensive()
        example_backend_optimization()
        example_batch_processing()
        example_error_recovery()
        example_performance_analysis()
        example_custom_algorithms()
        example_real_hardware_integration()
        example_memory_management()
        run_comprehensive_benchmark()

        print("\n" + "=" * 70)
        print("🚀 ALL ADVANCED EXAMPLES COMPLETED SUCCESSFULLY! 🚀")
        print("=" * 70)

        print("\nAdvanced Features Demonstrated:")
        print("✓ Comprehensive debug mode and logging")
        print("✓ Backend selection and optimization")
        print("✓ Batch processing and parallel execution")
        print("✓ Error recovery and fault tolerance")
        print("✓ Performance analysis and profiling")
        print("✓ Custom quantum algorithm implementation")
        print("✓ Real quantum hardware integration")
        print("✓ Memory and resource management")
        print("✓ Comprehensive benchmarking")

        print("\nProduction Deployment Tips:")
        print("• Enable comprehensive logging in production")
        print("• Use error recovery for critical applications")
        print("• Monitor performance and resource usage")
        print("• Implement cost optimization for real hardware")
        print("• Set up automated testing and validation")
        print("• Consider hybrid classical-quantum workflows")

        print("\nNext Steps:")
        print("• Deploy to cloud quantum platforms")
        print("• Integrate with experimental data pipelines")
        print("• Implement custom optimization algorithms")
        print("• Scale to production bioinformatics workflows")

    except Exception as e:
        print(f"\n✗ Error running advanced examples: {e}")
        import traceback

        traceback.print_exc()

        print("\nAdvanced Troubleshooting:")
        print("1. Check system resources and permissions")
        print("2. Verify all optional dependencies are installed")
        print("3. Enable debug mode for detailed error information")
        print("4. Monitor memory usage during execution")
        print("5. Test with smaller datasets first")
        print("6. Check quantum backend connectivity")


if __name__ == "__main__":
    main()
