import time

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch

from job_research.prompts import load_system_prompt
from job_research.run_metrics import collect_run_metrics
from job_research.run_result import AgentRunResult
from job_research.schema import JobSearchResponse
from job_research.settings import Settings


class JobResearchAgent:
    """Builds and runs the read-only job research loop with structured output."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_model(self) -> ChatOpenAI:
        kwargs: dict = {
            "model": self._settings.openai_model,
            "temperature": 0,
            "max_tokens": self._settings.max_output_tokens,
            "api_key": self._settings.openai_api_key,
        }
        if self._settings.openai_reasoning_effort:
            kwargs["reasoning_effort"] = self._settings.openai_reasoning_effort
        return ChatOpenAI(**kwargs)

    def create_tools(self) -> list:
        search = TavilySearch(
            max_results=self._settings.tavily_max_results,
            topic="general",
            include_raw_content=False,
        )
        return [search]

    def create_langchain_agent(self):
        return create_agent(
            model=self.create_model(),
            tools=self.create_tools(),
            middleware=[
                ModelCallLimitMiddleware(
                    run_limit=self._settings.max_model_calls,
                    exit_behavior="end",
                ),
                ToolCallLimitMiddleware(
                    run_limit=self._settings.max_tool_calls,
                    exit_behavior="end",
                ),
            ],
            system_prompt=load_system_prompt(),
            response_format=JobSearchResponse,
        )

    @staticmethod
    def _coerce_structured(structured: object) -> JobSearchResponse:
        if isinstance(structured, JobSearchResponse):
            return structured
        return JobSearchResponse.model_validate(structured)

    def _finalize_from_transcript(self, messages: list[AnyMessage]) -> JobSearchResponse:
        """Extra model call outside agent middleware if the loop ended without schema."""
        model = self.create_model().with_structured_output(JobSearchResponse)
        synthesis = [
            *messages,
            HumanMessage(
                content=(
                    "Using only the Tavily tool results and messages above, produce the "
                    "final JobSearchResponse JSON. Do not invent jobs; every match needs "
                    "a source_url that appeared in the search evidence."
                )
            ),
        ]
        return model.invoke(synthesis)

    def run(self, user_message: str) -> AgentRunResult:
        self._settings.apply_langsmith_env()
        agent = self.create_langchain_agent()
        started = time.perf_counter()
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]}
        )
        messages = list(result.get("messages", []))
        structured = result.get("structured_response")
        used_fallback = False

        if structured is not None:
            response = self._coerce_structured(structured)
        else:
            last_text = str(getattr(messages[-1], "content", "")) if messages else ""
            if "limit" in last_text.lower() and "exceeded" in last_text.lower():
                raise RuntimeError(
                    "Agent hit MAX_MODEL_CALLS or MAX_TOOL_CALLS before structured output. "
                    f"In .env try MAX_MODEL_CALLS=5 and MAX_TOOL_CALLS=2. Last message: {last_text}"
                )
            response = self._finalize_from_transcript(messages)
            used_fallback = True

        latency = time.perf_counter() - started
        metrics = collect_run_metrics(
            messages,
            used_fallback_synthesis=used_fallback,
            settings=self._settings,
        )
        return AgentRunResult(
            response=response,
            messages=tuple(messages),
            latency_seconds=round(latency, 2),
            used_fallback_synthesis=used_fallback,
            metrics=metrics,
        )
