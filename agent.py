import os
import sys

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Set {name} before running the agent.")
    return value


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            'Usage: python agent.py "Find Lead AI Engineer jobs in Bengaluru"'
        )

    required("OPENAI_API_KEY")
    required("TAVILY_API_KEY")

    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        temperature=0,
        max_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "1200")),
    )
    search = TavilySearch(max_results=5, topic="general", include_raw_content=False)

    agent = create_agent(
        model=model,
        tools=[search],
        middleware=[
            ModelCallLimitMiddleware(run_limit=4, exit_behavior="end"),
            ToolCallLimitMiddleware(run_limit=3, exit_behavior="end"),
        ],
        system_prompt="""You are a read-only job research agent.
Search public web pages for the requested role, location, and constraints.
Compare evidence, remove obvious duplicates, and return at most five strong matches.
For every match include title, company, location, why it matches, and source URL.
Clearly label missing or uncertain facts. Never claim that you applied for a job.
Prefer company career pages. Do not search or scrape LinkedIn.""",
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": " ".join(sys.argv[1:])}]}
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
