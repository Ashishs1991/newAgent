import sys

from job_research import JobResearchAgent, Settings


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            'Usage: python agent.py "Find Lead AI Engineer jobs in Bengaluru"'
        )

    settings = Settings.from_env()
    agent = JobResearchAgent(settings)
    user_message = " ".join(sys.argv[1:])
    response = agent.run(user_message)
    print(response.response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
