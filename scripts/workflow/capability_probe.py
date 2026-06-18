#!/usr/bin/env python3
"""
capability_probe.py — detect which optional capabilities are available, so a skill
can route through the plugin's capability-tier cascade (see
references/CAPABILITY-TIERS.md) instead of hard-depending on any one tool.

It reports two things it CAN honestly detect from a script:
  - CLI connectors on PATH (e.g. `gemini`, `node`, `npx`, `codex`)
  - relevant environment variables being SET (presence only — never their value)

It deliberately does NOT try to detect connected MCP servers: there is no
supported API for a script (or a skill) to enumerate the MCP tools exposed in a
Claude Code session. MCP availability is handled inside skill instructions as a
try-then-fallback chain (Tier 1 attempts the dedicated tool; on absence or error
the skill follows the written fallback). This probe informs Tiers 3-4 (CLI
connectors and the guided prompt) and surfaces which API keys are configured.

Security: this script reads environment variables but only ever records whether
each is SET (a boolean). It never prints, logs, or returns a secret value.

Output: machine-readable JSON by default; `--human` prints an ASCII-only summary
(safe on a Windows cp1252 console). Always exits 0 — availability is information,
not failure.

Usage:
  python3 capability_probe.py
  python3 capability_probe.py --human
  python3 capability_probe.py --env MY_PROVIDER_KEY,OTHER_KEY   # also check these
"""
import argparse
import json
import os
import shutil
import sys

# CLI connectors the plugin can route to when present.
DEFAULT_CLIS = ["gemini", "node", "npx", "codex", "python3", "py", "git"]

# Env vars that unlock paid/optional tiers. Presence is reported; values never are.
DEFAULT_ENV_VARS = [
    "DATAFORSEO_USERNAME",
    "DATAFORSEO_PASSWORD",
    "FIRECRAWL_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
]


def probe_clis(clis=None):
    """Return {name: bool} for each CLI, True when found on PATH.

    shutil.which resolves PATHEXT on Windows (.exe/.cmd/.bat), so an npm-installed
    `gemini.cmd` is detected the same as a POSIX `gemini`.
    """
    clis = DEFAULT_CLIS if clis is None else clis
    return {str(name): shutil.which(str(name)) is not None for name in clis}


def probe_env(env_vars=None):
    """Return {name: bool} for each env var, True when set to a non-empty value.

    Only the boolean is produced — the secret value is never read into the result,
    printed, or returned.
    """
    env_vars = DEFAULT_ENV_VARS if env_vars is None else env_vars
    return {str(name): bool(os.environ.get(str(name))) for name in env_vars}


def build_report(clis=None, env_vars=None):
    cli = probe_clis(clis)
    env = probe_env(env_vars)
    notes = []

    if cli.get("gemini"):
        notes.append("gemini CLI available -- usable as an image-generation connector (Tier 3).")
    if not any(env.values()):
        notes.append(
            "No optional API keys detected -- skills run their free/built-in path "
            "(Tier 2) and name what a paid tool would add (Tier 4 guidance)."
        )
    notes.append(
        "MCP server connections are not detectable from this script; skills test "
        "for a dedicated MCP at run time and fall back per references/CAPABILITY-TIERS.md."
    )
    return {"cli": cli, "env": env, "notes": notes}


def format_human(report):
    """ASCII-only rendering — safe on a cp1252 console.

    The whole output is forced to ASCII at the end (non-ASCII bytes become '?'),
    so even a caller-supplied non-ASCII env-var name (via --env) can never raise
    UnicodeEncodeError when printed to a Windows console.
    """
    lines = ["Capability probe", "================", "", "CLI connectors (on PATH):"]
    for name, present in report["cli"].items():
        lines.append("  [%s] %s" % ("x" if present else " ", name))
    lines.append("")
    lines.append("Environment keys (set?):")
    for name, present in report["env"].items():
        lines.append("  [%s] %s" % ("x" if present else " ", name))
    lines.append("")
    lines.append("Notes:")
    for note in report["notes"]:
        lines.append("  - " + note)
    text = "\n".join(lines)
    return text.encode("ascii", "replace").decode("ascii")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Detect optional CLI/env capabilities.")
    parser.add_argument("--human", action="store_true",
                        help="ASCII summary instead of JSON")
    parser.add_argument("--env", nargs="?", const="", default="",
                        help="comma-separated extra env-var names to also check")
    # parse_known_args + tolerant --env keep the contract: always exit 0, never
    # crash on unexpected args (availability is information, not failure).
    args, _unknown = parser.parse_known_args(argv)

    env_vars = list(DEFAULT_ENV_VARS)
    if args.env:
        for extra in args.env.split(","):
            extra = extra.strip()
            if extra and extra not in env_vars:
                env_vars.append(extra)

    report = build_report(env_vars=env_vars)

    if args.human:
        print(format_human(report))
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
