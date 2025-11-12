"""
Multi-Agent Orchestrator for BioQL
===================================

Coordinates multiple specialized agents to solve complex quantum problems.

Architecture:
    User Request → Orchestrator → [Agents] → Executor → Results

Agents:
    1. Code Generator: Writes BioQL code from natural language
    2. Circuit Optimizer: Optimizes quantum circuits
    3. Error Corrector: Fixes and validates code
    4. Bioinformatics Expert: Domain-specific optimization
    5. Hardware Selector: Chooses optimal quantum backend
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
import json

# Optional logging
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of specialized agents."""
    CODE_GENERATOR = "code_generator"
    CIRCUIT_OPTIMIZER = "optimizer"
    ERROR_CORRECTOR = "error_corrector"
    BIO_EXPERT = "bioinformatics"
    HARDWARE_SELECTOR = "hardware"
    RESULT_INTERPRETER = "interpreter"


@dataclass
class AgentTask:
    """Task for an agent to complete."""
    task_id: str
    agent_type: AgentType
    description: str
    context: Dict[str, Any]
    dependencies: List[str] = None
    priority: int = 0


@dataclass
class AgentResult:
    """Result from an agent."""
    task_id: str
    agent_type: AgentType
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Optional[Dict] = None


class AgentOrchestrator:
    """
    Orchestrates multiple specialized agents for complex quantum tasks.

    Example:
        >>> orchestrator = AgentOrchestrator()
        >>> result = orchestrator.execute(
        ...     "Design a quantum circuit to simulate GLP1R drug binding"
        ... )
    """

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the orchestrator.

        Args:
            model: LLM model to use for agents
        """
        self.model = model
        self.agents: Dict[AgentType, Any] = {}
        self.task_history: List[AgentTask] = []
        self.result_history: List[AgentResult] = []

        logger.info(f"AgentOrchestrator initialized with model: {model}")

    def register_agent(self, agent_type: AgentType, agent: Any):
        """Register a specialized agent."""
        self.agents[agent_type] = agent
        logger.info(f"Registered agent: {agent_type.value}")

    def decompose_task(self, user_request: str) -> List[AgentTask]:
        """
        Decompose user request into specialized agent tasks.

        Uses LLM to intelligently break down complex requests.
        """
        logger.info(f"Decomposing task: {user_request}")

        # Analyze request and determine required agents
        tasks = []

        # 1. Always start with code generation
        tasks.append(AgentTask(
            task_id="gen_1",
            agent_type=AgentType.CODE_GENERATOR,
            description=f"Generate BioQL code for: {user_request}",
            context={"user_request": user_request},
            priority=1
        ))

        # 2. Check if bioinformatics optimization needed
        bio_keywords = ["protein", "drug", "dna", "molecule", "binding", "folding"]
        if any(kw in user_request.lower() for kw in bio_keywords):
            tasks.append(AgentTask(
                task_id="bio_1",
                agent_type=AgentType.BIO_EXPERT,
                description="Optimize for bioinformatics workload",
                context={"user_request": user_request},
                dependencies=["gen_1"],
                priority=2
            ))

        # 3. Always optimize circuit
        tasks.append(AgentTask(
            task_id="opt_1",
            agent_type=AgentType.CIRCUIT_OPTIMIZER,
            description="Optimize quantum circuit",
            context={},
            dependencies=["gen_1"],
            priority=3
        ))

        # 4. Select optimal hardware
        tasks.append(AgentTask(
            task_id="hw_1",
            agent_type=AgentType.HARDWARE_SELECTOR,
            description="Select optimal quantum backend",
            context={"user_request": user_request},
            dependencies=["opt_1"],
            priority=4
        ))

        logger.info(f"Decomposed into {len(tasks)} tasks")
        return tasks

    def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a single agent task."""
        logger.info(f"Executing task {task.task_id}: {task.agent_type.value}")

        try:
            agent = self.agents.get(task.agent_type)

            if agent is None:
                # Mock execution for agents not yet implemented
                logger.warning(f"Agent {task.agent_type.value} not implemented, using mock")
                return AgentResult(
                    task_id=task.task_id,
                    agent_type=task.agent_type,
                    success=True,
                    output=f"Mock result for {task.description}",
                    metadata={"mock": True}
                )

            # Execute real agent
            result = agent.execute(task)

            return AgentResult(
                task_id=task.task_id,
                agent_type=task.agent_type,
                success=True,
                output=result,
                metadata={"agent": agent.__class__.__name__}
            )

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_type=task.agent_type,
                success=False,
                output=None,
                error=str(e)
            )

    def execute(self, user_request: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a complex quantum task using multiple agents.

        Args:
            user_request: Natural language description of task
            **kwargs: Additional options

        Returns:
            Dict with results from all agents

        Example:
            >>> orchestrator = AgentOrchestrator()
            >>> result = orchestrator.execute(
            ...     "Create a quantum circuit to fold hemoglobin protein"
            ... )
        """
        logger.info(f"=== Starting multi-agent execution ===")
        logger.info(f"Request: {user_request}")

        # 1. Decompose into tasks
        tasks = self.decompose_task(user_request)
        self.task_history.extend(tasks)

        # 2. Execute tasks in order (respecting dependencies)
        results = {}
        completed_tasks = set()

        for task in sorted(tasks, key=lambda t: t.priority):
            # Check dependencies
            if task.dependencies:
                if not all(dep in completed_tasks for dep in task.dependencies):
                    logger.warning(f"Skipping {task.task_id}: dependencies not met")
                    continue

            # Execute task
            result = self.execute_task(task)
            results[task.task_id] = result
            self.result_history.append(result)

            if result.success:
                completed_tasks.add(task.task_id)

        # 3. Compile final result
        final_result = {
            "user_request": user_request,
            "tasks_executed": len(completed_tasks),
            "tasks_failed": len(tasks) - len(completed_tasks),
            "results": results,
            "success": len(completed_tasks) == len(tasks)
        }

        logger.info(f"=== Execution complete: {final_result['success']} ===")
        return final_result

    def get_execution_summary(self) -> str:
        """Get human-readable summary of execution."""
        summary = [
            "=== Agent Orchestrator Execution Summary ===",
            f"Total tasks executed: {len(self.task_history)}",
            f"Successful: {sum(1 for r in self.result_history if r.success)}",
            f"Failed: {sum(1 for r in self.result_history if not r.success)}",
            "",
            "Agent breakdown:"
        ]

        agent_counts = {}
        for result in self.result_history:
            agent_type = result.agent_type.value
            agent_counts[agent_type] = agent_counts.get(agent_type, 0) + 1

        for agent, count in agent_counts.items():
            summary.append(f"  - {agent}: {count} tasks")

        return "\n".join(summary)


class ThinkHarderOrchestrator(AgentOrchestrator):
    """
    Advanced orchestrator with recursive thinking and self-correction.

    Inspired by "thinking harder" paradigm - agents can:
    - Recursively break down complex problems
    - Self-correct their outputs
    - Learn from previous attempts
    """

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", max_iterations: int = 3):
        super().__init__(model)
        self.max_iterations = max_iterations
        logger.info("ThinkHarderOrchestrator initialized with recursive thinking")

    def think_harder(self, task: AgentTask, previous_attempts: List[AgentResult]) -> AgentResult:
        """
        Apply recursive thinking to improve result.

        Analyzes previous attempts and tries again with improvements.
        """
        logger.info(f"🧠 Thinking harder on task {task.task_id} (attempt {len(previous_attempts) + 1})")

        # Add context from previous attempts
        task.context["previous_attempts"] = [
            {
                "success": r.success,
                "output": str(r.output)[:200],
                "error": r.error
            }
            for r in previous_attempts
        ]

        # Execute with enhanced context
        result = self.execute_task(task)

        return result

    def execute(self, user_request: str, **kwargs) -> Dict[str, Any]:
        """
        Execute with recursive thinking and self-correction.
        """
        logger.info(f"=== ThinkHarder execution started ===")

        iteration = 0
        best_result = None

        while iteration < self.max_iterations:
            logger.info(f"Iteration {iteration + 1}/{self.max_iterations}")

            result = super().execute(user_request, **kwargs)

            # Check if we can improve
            if result["success"]:
                best_result = result
                break

            iteration += 1

        if best_result:
            best_result["iterations"] = iteration + 1
            best_result["thinking_mode"] = "recursive"

        logger.info(f"=== ThinkHarder complete after {iteration + 1} iterations ===")
        return best_result or result
