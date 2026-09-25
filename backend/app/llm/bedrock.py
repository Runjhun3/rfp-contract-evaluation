"""The only Bedrock caller. Converse API, temperature 0, prompt caching on long
system prompts (system rules + criteria block are identical across item calls).

Auth: boto3 picks up AWS_BEARER_TOKEN_BEDROCK (Bedrock API key) or normal IAM
credentials from the environment.
"""
from app.aws.clients import client
from app.config import Settings

CACHE_MIN_CHARS = 6000   # below Bedrock's minimum cacheable size, skip the cache point


def make_completer(settings: Settings):
    runtime = client("bedrock-runtime", settings)

    def complete(system: str, user: str) -> str:
        system_blocks = [{"text": system}]
        if len(system) >= CACHE_MIN_CHARS:
            system_blocks.append({"cachePoint": {"type": "default"}})
        response = runtime.converse(
            modelId=settings.claude_model,
            system=system_blocks,
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"temperature": 0, "maxTokens": settings.llm_max_tokens},
        )
        content = response["output"]["message"]["content"]
        return "".join(block.get("text", "") for block in content)

    return complete
