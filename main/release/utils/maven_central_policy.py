"""Decide whether a repository may publish to Maven Central, from maven-central-policy.yml.

The file uses a deliberately small YAML subset (a `mode` key and a `repositories` block list) so that it can be read
on a runner without a YAML library. Anything else is rejected.
"""
import re
import sys

MODES = ("allow-all", "allowlist", "denylist")
_MODE = re.compile(r"^mode:\s*(\S+)\s*$")
_EMPTY_LIST = re.compile(r"^repositories:\s*\[\s*\]\s*$")
_LIST_START = re.compile(r"^repositories:\s*$")
_ITEM = re.compile(r"^\s+-\s+([\w.-]+/[\w.-]+)\s*$")


def parse_policy(text):
    """Return (mode, set of lowercased repositories). Raises ValueError on an invalid file."""
    mode, repositories, in_list = None, None, False
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if match := _MODE.match(line):
            mode, in_list = match.group(1), False
        elif _EMPTY_LIST.match(line):
            repositories, in_list = set(), False
        elif _LIST_START.match(line):
            repositories, in_list = set(), True
        elif in_list and (match := _ITEM.match(line)):
            repositories.add(match.group(1).lower())
        else:
            raise ValueError(f"line {number}: unexpected content '{raw.strip()}'")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}, got '{mode}'")
    if repositories is None:
        raise ValueError("missing 'repositories' key")
    return mode, repositories


def is_allowed(text, repository):
    mode, repositories = parse_policy(text)
    listed = repository.lower() in repositories
    if mode == "allowlist":
        return listed
    if mode == "denylist":
        return not listed
    return True


def main(argv, stdin=sys.stdin):
    if len(argv) != 2:
        print("Usage: maven_central_policy.py <owner/name> < policy-file", file=sys.stderr)
        return 2
    try:
        allowed = is_allowed(stdin.read(), argv[1])
    except ValueError as e:
        print(f"invalid policy: {e}", file=sys.stderr)
        return 2
    print("allowed" if allowed else "blocked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
