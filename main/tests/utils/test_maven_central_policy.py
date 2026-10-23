import os

import pytest
from parameterized import parameterized

from release.utils.maven_central_policy import is_allowed, main, parse_policy

POLICY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "maven-central-policy.yml")


def test_shipped_policy_is_valid():
    with open(POLICY_FILE, encoding="utf-8") as policy:
        parse_policy(policy.read())


@parameterized.expand([
    ("allow_all_empty", "mode: allow-all\nrepositories: []\n", "SonarSource/sonar-java", True),
    ("allow_all_ignores_list", "mode: allow-all\nrepositories:\n  - SonarSource/sonar-java\n",
     "SonarSource/other", True),
    ("allowlist_listed", "mode: allowlist\nrepositories:\n  - SonarSource/sonar-java\n", "SonarSource/sonar-java", True),
    ("allowlist_case_insensitive", "mode: allowlist\nrepositories:\n  - SonarSource/Sonar-Java\n",
     "sonarsource/sonar-java", True),
    ("allowlist_unlisted", "mode: allowlist\nrepositories:\n  - SonarSource/sonar-java\n", "SonarSource/other", False),
    ("allowlist_empty", "mode: allowlist\nrepositories: []\n", "SonarSource/sonar-java", False),
    ("denylist_listed", "mode: denylist\nrepositories:\n  - SonarSource/sonar-java\n", "SonarSource/sonar-java", False),
    ("denylist_unlisted", "mode: denylist\nrepositories:\n  - SonarSource/sonar-java\n", "SonarSource/other", True),
    ("comments_and_blank_lines", "# header\nmode: allowlist # inline\n\nrepositories:\n  # why\n"
     "  - SonarSource/sonar-java  # P0\n", "SonarSource/sonar-java", True),
])
def test_is_allowed(_name, text, repository, expected):
    assert is_allowed(text, repository) is expected


@parameterized.expand([
    ("missing_mode", "repositories: []\n"),
    ("unknown_mode", "mode: whitelist\nrepositories: []\n"),
    ("missing_repositories", "mode: allow-all\n"),
    ("item_without_owner", "mode: allowlist\nrepositories:\n  - sonar-java\n"),
    ("item_outside_list", "mode: allowlist\n  - SonarSource/sonar-java\nrepositories: []\n"),
    ("unknown_key", "mode: allow-all\nrepositories: []\nextra: 1\n"),
])
def test_invalid_policy(_name, text):
    with pytest.raises(ValueError):
        parse_policy(text)


def test_main_prints_decision(tmp_path, capsys):
    policy = tmp_path / "policy.yml"
    policy.write_text("mode: allowlist\nrepositories:\n  - SonarSource/sonar-java\n")
    assert main(["x", str(policy), "SonarSource/sonar-java"]) == 0
    assert capsys.readouterr().out.strip() == "allowed"
    assert main(["x", str(policy), "SonarSource/other"]) == 0
    assert capsys.readouterr().out.strip() == "blocked"


def test_main_rejects_invalid_policy(tmp_path):
    policy = tmp_path / "policy.yml"
    policy.write_text("mode: nope\nrepositories: []\n")
    assert main(["x", str(policy), "SonarSource/sonar-java"]) == 2
