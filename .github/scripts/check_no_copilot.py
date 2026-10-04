import os
import sys
import json
import subprocess
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

COPILOT_PATTERN = re.compile(r"copilot", re.IGNORECASE)

def contains_copilot(text: str) -> bool:
    if not text:
        return False
    return bool(COPILOT_PATTERN.search(text))

def check_event_file(event_path: str):
    violations = []
    if not event_path or not os.path.exists(event_path):
        return violations

    try:
        with open(event_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Warning: Could not read event file: {e}")
        return violations

    # Check PR author and details if PR event
    pr = data.get("pull_request")
    if pr:
        pr_user = pr.get("user", {}).get("login", "")
        pr_title = pr.get("title", "")
        pr_body = pr.get("body", "") or ""
        pr_head_ref = pr.get("head", {}).get("ref", "")

        if contains_copilot(pr_user):
            violations.append(f"PR creator username contains 'copilot': {pr_user}")
        if contains_copilot(pr_title):
            violations.append(f"PR title contains 'copilot': {pr_title}")
        if contains_copilot(pr_body):
            violations.append("PR description / body contains 'copilot' reference (e.g. Copilot summary)")
        if contains_copilot(pr_head_ref):
            violations.append(f"PR branch name contains 'copilot': {pr_head_ref}")

    # Check commits in the push event payload
    commits = data.get("commits", [])
    for c in commits:
        c_id = c.get("id", "")[:8]
        c_msg = c.get("message", "")
        author_name = c.get("author", {}).get("name", "")
        author_email = c.get("author", {}).get("email", "")
        committer_name = c.get("committer", {}).get("name", "")
        committer_email = c.get("committer", {}).get("email", "")

        if contains_copilot(c_msg):
            violations.append(f"Commit [{c_id}] message contains 'copilot': {c_msg.splitlines()[0]}")
        if contains_copilot(author_name) or contains_copilot(author_email):
            violations.append(f"Commit [{c_id}] author contains 'copilot': {author_name} <{author_email}>")
        if contains_copilot(committer_name) or contains_copilot(committer_email):
            violations.append(f"Commit [{c_id}] committer contains 'copilot': {committer_name} <{committer_email}>")

    return violations

def check_git_log(event_name: str, base_ref: str, event_path: str):
    violations = []
    
    rev_range = None
    if event_name == "pull_request" and base_ref:
        rev_range = f"origin/{base_ref}..HEAD"
    elif event_name == "push" and event_path and os.path.exists(event_path):
        try:
            with open(event_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            before = data.get("before")
            after = data.get("after")
            if before and after and not before.startswith("0000000"):
                rev_range = f"{before}..{after}"
        except Exception:
            pass

    cmd = ["git", "log", "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e"]
    
    output = ""
    if rev_range:
        try:
            output = subprocess.check_output(cmd + [rev_range], text=True, stderr=subprocess.DEVNULL)
        except Exception:
            output = ""

    if not output:
        # Fallback to inspecting recent commits on current branch
        for n in [5, 3, 1]:
            try:
                output = subprocess.check_output(cmd + [f"-n", str(n)], text=True, stderr=subprocess.DEVNULL)
                break
            except Exception:
                continue

    if not output:
        return violations

    commits = output.strip().split("\x1e")
    for raw_commit in commits:
        parts = raw_commit.strip().split("\x1f")
        if len(parts) < 6:
            continue
        c_hash, author_name, author_email, committer_name, committer_email, body = parts[:6]
        short_hash = c_hash[:8]

        if contains_copilot(author_name) or contains_copilot(author_email):
            violations.append(f"Git commit [{short_hash}] author has 'copilot': {author_name} <{author_email}>")
        if contains_copilot(committer_name) or contains_copilot(committer_email):
            violations.append(f"Git commit [{short_hash}] committer has 'copilot': {committer_name} <{committer_email}>")
        if contains_copilot(body):
            first_line = body.strip().splitlines()[0] if body.strip() else ""
            violations.append(f"Git commit [{short_hash}] body / trailers has 'copilot': {first_line}")

    return violations

def main():
    print("=" * 60)
    print("🔍 Checking for GitHub Copilot references...")
    print("=" * 60)

    actor = os.environ.get("GITHUB_ACTOR", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    base_ref = os.environ.get("GITHUB_BASE_REF", "")

    all_violations = []

    if contains_copilot(actor):
        all_violations.append(f"GitHub Actor contains 'copilot': {actor}")

    all_violations.extend(check_event_file(event_path))
    all_violations.extend(check_git_log(event_name, base_ref, event_path))

    # Remove duplicates
    unique_violations = list(dict.fromkeys(all_violations))

    if unique_violations:
        print("\n" + "!" * 60)
        print("❌ POLICY VIOLATION DETECTED: COPILOT IS PROHIBITED!")
        print("The following Copilot references were found:")
        for v in unique_violations:
            print(f"   - {v}")
        print("!" * 60)
        print("\nPlease remove all Copilot generated commits, co-author tags,")
        print("or PR descriptions before pushing or merging to the 'main' branch.\n")
        sys.exit(1)

    print("\n✅ Verification passed! No Copilot references found.")
    print("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
