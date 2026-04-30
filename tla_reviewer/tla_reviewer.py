import json
from dataclasses import dataclass
from typing import Optional

from agent import Agent


@dataclass
class TLAValidationResult:
    success: bool
    reason: Optional[str]


def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def build_input(requirement: str, tla_spec: str) -> str:
    return f"""
<REQUIREMENT>
{requirement}

<TLA+>
{tla_spec}
""".strip()


def validate_tla(
    requirement: str,
    tla_spec: str,
    prompt_path: str = "prompt.txt"
) -> TLAValidationResult:

    system_prompt = load_prompt(prompt_path)
    agent = Agent(system_prompt=system_prompt)

    user_input = build_input(requirement, tla_spec)
    response = agent.run(user_input)

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        return TLAValidationResult(
            success=False,
            reason=f"Invalid JSON output: {response}"
        )

    if "success" not in data or "reason" not in data:
        return TLAValidationResult(
            success=False,
            reason=f"Missing required fields: {response}"
        )

    return TLAValidationResult(
        success=data["success"],
        reason=data["reason"]
    )


# TODO: 示例
if __name__ == "__main__":
    requirement = "实现一个加法函数 add(a, b)"
    tla_spec = "Add(a, b) == a + b"

    result = validate_tla(requirement, tla_spec)

    print(result)