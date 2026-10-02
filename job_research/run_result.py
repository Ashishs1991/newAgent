from dataclasses import dataclass

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage

from job_research.schema import JobSearchResponse


@dataclass(frozen=True)
class RunMetrics:
    """Observed usage from one agent run (best-effort from message metadata)."""

    agent_model_calls: int
    agent_tool_calls: int
    fallback_synthesis_calls: int
    total_input_tokens: int | None
    total_output_tokens: int | None
    total_tokens: int | None
    approximate_openai_usd: float | None


@dataclass(frozen=True)
class AgentRunResult:
    """Full outcome of JobResearchAgent.run for eval and baselines."""

    response: JobSearchResponse
    messages: tuple[AnyMessage, ...]
    latency_seconds: float
    used_fallback_synthesis: bool
    metrics: RunMetrics
