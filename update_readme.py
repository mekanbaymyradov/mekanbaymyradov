"""Rewrite the README's open source contributions from GitHub's search API.

Runs daily in .github/workflows/update-readme.yml. Locally:
GITHUB_TOKEN=$(gh auth token) python3 update_readme.py
"""

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

USER = "mekanbaymyradov"
README = Path(__file__).with_name("README.md")
SECTION = re.compile(r"(<!-- contributions:start -->\n).*?(<!-- contributions:end -->)", re.S)


def fetch_pull_requests() -> list[dict]:
    # -user: leaves out this account's own repos and forks; one page of 100 is plenty.
    query = urllib.parse.urlencode({"q": f"author:{USER} is:pr -user:{USER}", "per_page": 100})
    request = urllib.request.Request(
        f"https://api.github.com/search/issues?{query}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        },
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)["items"]


def repo(pr: dict) -> str:
    return pr["repository_url"].removeprefix("https://api.github.com/repos/")


def row(pr: dict, status: str) -> str:
    title = pr["title"].replace("|", "\\|")  # a bare | would end the table cell
    return f"| [{repo(pr)}](https://github.com/{repo(pr)}) | [{title}]({pr['html_url']}) | {status} |"


def render(pull_requests: list[dict]) -> str:
    """Return the section: merged PRs first, newest merge first, then open ones."""
    merged = sorted(
        (pr for pr in pull_requests if pr["pull_request"]["merged_at"]),
        key=lambda pr: pr["pull_request"]["merged_at"],
        reverse=True,
    )
    opened = sorted(
        (pr for pr in pull_requests if pr["state"] == "open"),
        key=lambda pr: pr["created_at"],
        reverse=True,
    )
    projects = len({repo(pr) for pr in merged + opened})
    return "\n".join(
        [
            f"**{len(merged)} merged · {len(opened)} open** across {projects} "
            f"project{'' if projects == 1 else 's'}",
            "",
            "| Project | Pull request | Status |",
            "|---|---|---|",
            *(row(pr, "✅ merged") for pr in merged),
            *(row(pr, "🟡 open") for pr in opened),
            "",
        ]
    )


def main() -> None:
    text = README.read_text()
    section = render(fetch_pull_requests())
    updated = SECTION.sub(lambda m: m[1] + section + m[2], text)
    if updated != text:
        README.write_text(updated)


if __name__ == "__main__":
    main()
