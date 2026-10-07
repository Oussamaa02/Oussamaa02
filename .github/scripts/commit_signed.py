#!/usr/bin/env python3
"""Commit regenerated profile files through GitHub's GraphQL API.

createCommitOnBranch commits are signed by GitHub, so they show as
"Verified" without storing any signing key. Stdlib only.
"""
import base64, json, os, subprocess, sys, urllib.request

FILES = ["public-stats.json", "assets/heatmap.svg", "assets/analytics.svg"]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def main() -> None:
    changed = [f for f in FILES if git("status", "--porcelain", "--", f)]
    if not changed:
        print("no changes")
        return

    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    head = git("rev-parse", "HEAD")
    as_of = json.load(open("public-stats.json"))["as_of"]

    query = """mutation($input: CreateCommitOnBranchInput!) {
      createCommitOnBranch(input: $input) { commit { oid url } }
    }"""
    variables = {"input": {
        "branch": {"repositoryNameWithOwner": repo, "branchName": branch},
        "expectedHeadOid": head,
        "message": {"headline": f"chore(profile): refresh contribution stats ({as_of})"},
        "fileChanges": {"additions": [
            {"path": f, "contents": base64.b64encode(open(f, "rb").read()).decode()} for f in changed
        ]},
    }}
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors"):
        sys.exit(f"commit failed: {body['errors']}")
    c = body["data"]["createCommitOnBranch"]["commit"]
    print(f"committed {', '.join(changed)} -> {c['url']}")


if __name__ == "__main__":
    main()
