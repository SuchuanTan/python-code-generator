import json
from dataclasses import dataclass
from typing import Optional

from code_executor.code_executor import PythonExecutor
from agent import Agent


@dataclass
class GenerationResult:
    success: bool
    code: Optional[str]
    test_cases: Optional[str]
    tla_spec: str
    error: Optional[str]


def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def build_input(requirement: str, tla_spec: str, error: Optional[str] = None) -> str:
    base = f"""
<REQUIREMENT>
{requirement}

<TLA+>
{tla_spec}
"""
    if error:
        base += f"""

<ERROR>
The previous attempt failed with the following error:
{error}

Please fix the code and test cases.
"""
    return base


def generate_with_retry(
    requirement: str,
    tla_spec: str,
    max_attempts: int = 3,
    prompt_path: str = "prompt.txt"
) -> GenerationResult:
    system_prompt = load_prompt(prompt_path)
    agent = Agent(system_prompt=system_prompt)

    last_error = None
    code = None
    test_cases = None

    for attempt in range(max_attempts):
        user_input = build_input(requirement, tla_spec, last_error)

        response = agent.run(user_input)

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            last_error = f"Invalid JSON:\n{response}"
            continue

        if "code" not in data or "test_cases" not in data:
            last_error = f"Missing fields in response:\n{response}"
            continue

        code = data["code"]
        test_cases = data["test_cases"]

        full_code = f"{code}\n\n{test_cases}"

        exec_result = PythonExecutor.run(full_code)

        if exec_result.success:
            return GenerationResult(
                success=True,
                code=code,
                test_cases=test_cases,
                tla_spec=tla_spec,
                error=None
            )

        last_error = exec_result.error or exec_result.output

    return GenerationResult(
        success=False,
        code=code,
        test_cases=test_cases,
        tla_spec=tla_spec,
        error=last_error
    )


# 示例
if __name__ == "__main__":
    requirement = "实现一个加法函数 add(a, b)"
    tla_spec = "Add(a, b) == a + b"

    result = generate_with_retry(requirement, tla_spec)

    print(result)