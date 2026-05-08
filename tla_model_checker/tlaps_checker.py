from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Sequence


MODULE_RE = re.compile(
    r"-{4,}\s*MODULE\s+([A-Za-z_][A-Za-z0-9_]*)\s*-{4,}"
)

THEOREM_RE = re.compile(
    r"\b(THEOREM|LEMMA|PROPOSITION|COROLLARY)\b"
)


@dataclass
class TLAPSResult:
    parse_succeeded: bool
    proof_succeeded: Optional[bool]
    next_step: str
    module_name: Optional[str]
    tla_file: Optional[str]
    returncode: int
    command: list[str]
    feedback: str
    stdout: str
    stderr: str


def strip_code_fence(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        return "\n".join(lines).strip()

    return text


def extract_module_name(tla_text: str) -> Optional[str]:
    match = MODULE_RE.search(tla_text)

    if match is None:
        return None

    return match.group(1)


def has_theorem_or_lemma(tla_text: str) -> bool:
    return THEOREM_RE.search(tla_text) is not None


def looks_like_parse_failure(output: str) -> bool:
    lower = output.lower()

    parse_failure_patterns = [
        "could not parse",
        "parse_file",
        "syntax error",
        "lexical error",
        "semantic error",
        "parsing error",
        "unknown operator",
        "expected",
        "required expression",
        "module.parser",
    ]

    return any(pattern in lower for pattern in parse_failure_patterns)


def looks_like_proof_failure(output: str) -> bool:
    lower = output.lower()

    proof_failure_patterns = [
        "not proved",
        "could not prove",
        "obligation failed",
        "backend failed",
        "prover failed",
        "proof failed",
        "failed obligation",
    ]

    return any(pattern in lower for pattern in proof_failure_patterns)


def extract_feedback(output: str, max_lines: int = 40) -> str:
    keywords = [
        "error",
        "failed",
        "failure",
        "syntax",
        "semantic",
        "lexical",
        "parse",
        "line",
        "column",
        "obligation",
        "not proved",
        "could not",
        "expected",
        "required",
        "unknown",
    ]

    useful_lines = []

    for line in output.splitlines():
        lower = line.lower()
        if any(keyword in lower for keyword in keywords):
            useful_lines.append(line)

    if useful_lines:
        return "\n".join(useful_lines[-max_lines:])

    output = output.strip()

    if output:
        return output[-3000:]

    return "No diagnostic output was produced by TLAPS."


def run_tlaps_checker(
    tla_text: str,
    work_dir: str | Path = "runs",
    tlapm_cmd: Sequence[str] = ("tlapm",),
    timeout_sec: int = 120,
    require_proof_success: bool = False,
) -> TLAPSResult:
    tla_text = strip_code_fence(tla_text)
    module_name = extract_module_name(tla_text)

    if module_name is None:
        return TLAPSResult(
            parse_succeeded=False,
            proof_succeeded=None,
            next_step="TLA+ Generator",
            module_name=None,
            tla_file=None,
            returncode=-1,
            command=[],
            feedback="Cannot find module header. Expected something like: ---- MODULE Spec ----",
            stdout="",
            stderr="",
        )

    work_path = Path(work_dir).resolve()
    work_path.mkdir(parents=True, exist_ok=True)

    tla_file = work_path / f"{module_name}.tla"
    tla_file.write_text(tla_text, encoding="utf-8")

    command = list(tlapm_cmd) + [tla_file.name]

    try:
        proc = subprocess.run(
            command,
            cwd=work_path,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )

    except FileNotFoundError:
        return TLAPSResult(
            parse_succeeded=False,
            proof_succeeded=None,
            next_step="TLA+ Generator",
            module_name=module_name,
            tla_file=str(tla_file),
            returncode=-3,
            command=command,
            feedback=(
                "Cannot find 'tlapm'. Please install TLAPS and make sure "
                "'tlapm' is available from the terminal."
            ),
            stdout="",
            stderr="",
        )

    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = e.stderr or ""

        return TLAPSResult(
            parse_succeeded=False,
            proof_succeeded=None,
            next_step="TLA+ Generator",
            module_name=module_name,
            tla_file=str(tla_file),
            returncode=-2,
            command=command,
            feedback=f"TLAPS timed out after {timeout_sec} seconds.",
            stdout=stdout,
            stderr=stderr,
        )

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    output = stdout + "\n" + stderr

    parse_failed = looks_like_parse_failure(output)
    parse_succeeded = not parse_failed

    contains_proof = has_theorem_or_lemma(tla_text)

    if contains_proof:
        proof_failed = looks_like_proof_failure(output)
        proof_succeeded = proc.returncode == 0 and not proof_failed
    else:
        proof_succeeded = None

    if not parse_succeeded:
        next_step = "TLA+ Generator"
    elif require_proof_success and proof_succeeded is not True:
        next_step = "TLA+ Generator"
    else:
        next_step = "TLA+ Reviewer"

    if next_step == "TLA+ Reviewer":
        if proof_succeeded is True:
            feedback = "TLAPS accepted the module and the proof appears to have succeeded."
        elif proof_succeeded is None:
            feedback = "TLAPS accepted the module. No theorem or lemma proof was detected."
        else:
            feedback = "TLAPS accepted the module, but proof success was not confirmed."
    else:
        feedback = extract_feedback(output)

    return TLAPSResult(
        parse_succeeded=parse_succeeded,
        proof_succeeded=proof_succeeded,
        next_step=next_step,
        module_name=module_name,
        tla_file=str(tla_file),
        returncode=proc.returncode,
        command=command,
        feedback=feedback,
        stdout=stdout,
        stderr=stderr,
    )


def check_generated_tla(tla_text: str) -> dict:
    result = run_tlaps_checker(
        tla_text=tla_text,
        work_dir="runs",
        timeout_sec=120,
        require_proof_success=False,
    )

    return {
        "parse_succeeded": result.parse_succeeded,
        "proof_succeeded": result.proof_succeeded,
        "next_step": result.next_step,
        "feedback": result.feedback,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--work-dir", default="runs")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--require-proof-success", action="store_true")

    args = parser.parse_args()

    tla_text = Path(args.input).read_text(encoding="utf-8")

    result = run_tlaps_checker(
        tla_text=tla_text,
        work_dir=args.work_dir,
        timeout_sec=args.timeout,
        require_proof_success=args.require_proof_success,
    )

    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
