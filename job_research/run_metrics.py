from langchain_core.messages import AIMessage, AnyMessage, ToolMessage

from job_research.run_result import RunMetrics
from job_research.settings import Settings

TAVILY_TOOL_NAMES = {"tavily_search", "tavily_search_results_json"}


def _usage_from_ai_message(message: AIMessage) -> tuple[int, int, int]:
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0

    meta = getattr(message, "response_metadata", None) or {}
    usage = meta.get("token_usage") or meta.get("usage") or {}
    if not usage and getattr(message, "usage_metadata", None):
        um = message.usage_metadata
        if isinstance(um, dict):
            usage = um
        else:
            usage = {
                "prompt_tokens": getattr(um, "input_tokens", 0) or getattr(um, "prompt_tokens", 0),
                "completion_tokens": getattr(um, "output_tokens", 0)
                or getattr(um, "completion_tokens", 0),
                "total_tokens": getattr(um, "total_tokens", 0),
            }

    input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    output_tokens = int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )
    total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
    return input_tokens, output_tokens, total_tokens


def collect_run_metrics(
    messages: list[AnyMessage],
    *,
    used_fallback_synthesis: bool,
    settings: Settings,
) -> RunMetrics:
    agent_model_calls = 0
    agent_tool_calls = 0
    total_in = 0
    total_out = 0
    total_all = 0
    saw_usage = False

    for message in messages:
        if isinstance(message, AIMessage):
            agent_model_calls += 1
            inp, out, tot = _usage_from_ai_message(message)
            if inp or out or tot:
                saw_usage = True
                total_in += inp
                total_out += out
                total_all += tot or (inp + out)
        elif isinstance(message, ToolMessage):
            name = (message.name or "").lower()
            if name in TAVILY_TOOL_NAMES or "tavily" in name:
                agent_tool_calls += 1

    fallback_calls = 1 if used_fallback_synthesis else 0
    approx_usd = None
    if saw_usage and settings.openai_input_usd_per_1m is not None:
        out_rate = settings.openai_output_usd_per_1m
        if out_rate is None:
            out_rate = settings.openai_input_usd_per_1m
        in_cost = (total_in / 1_000_000) * settings.openai_input_usd_per_1m
        out_cost = (total_out / 1_000_000) * out_rate
        approx_usd = round(in_cost + out_cost, 6)

    return RunMetrics(
        agent_model_calls=agent_model_calls,
        agent_tool_calls=agent_tool_calls,
        fallback_synthesis_calls=fallback_calls,
        total_input_tokens=total_in if saw_usage else None,
        total_output_tokens=total_out if saw_usage else None,
        total_tokens=total_all if saw_usage else None,
        approximate_openai_usd=approx_usd,
    )
