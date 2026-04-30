import sys
import io
import traceback
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: Optional[str]
    exception_type: Optional[str]


class PythonExecutor:
    def __init__(self):
        pass

    @staticmethod
    def run(code: str, global_vars=None, local_vars=None) -> ExecutionResult:
        if global_vars is None:
            global_vars = {}
        if local_vars is None:
            local_vars = {}

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            exec(code, global_vars, local_vars)
            output = sys.stdout.getvalue()

            return ExecutionResult(
                success=True,
                output=output,
                error=None,
                exception_type=None
            )

        except Exception as e:
            output = sys.stdout.getvalue()
            error_msg = traceback.format_exc()

            return ExecutionResult(
                success=False,
                output=output,
                error=error_msg,
                exception_type=type(e).__name__
            )

        finally:
            sys.stdout = old_stdout


# TODO: 测试一下，用完删
if __name__ == "__main__":
    executor = PythonExecutor()

    code = """
    print("Hello World")
    x = 10
    print(x * 2)
    """

    result = executor.run(code)

    print(result)
