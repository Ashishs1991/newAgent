from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch

from job_research.prompts import load_system_prompt
from job_research.schemas import JobSearchResponse
from job_research.settings import Settings


class JobResearchAgent:
    """Builds and runs the read-only job research loop with structured output."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_model(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self._settings.openai_model,
            temperature=0,
            max_tokens=self._settings.max_output_tokens,
            api_key=self._settings.openai_api_key,
        )

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

    def run(self, user_message: str) -> JobSearchResponse:
        self._settings.apply_langsmith_env()
        agent = self.create_langchain_agent()
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]}
        )
        structured = result.get("structured_response")
        if structured is None:
            raise RuntimeError(
                "Agent finished without structured_response. "
                "Check LangSmith trace for limit errors or schema validation failures."
            )
        if isinstance(structured, JobSearchResponse):
            return structured
        return JobSearchResponse.model_validate(structured)
