import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


def load_report(filename):
    return json.loads(Path(filename).read_text(encoding="utf-8"))


def dependency_issues(filename, checkout):
    report = load_report(filename)
    projects = report if isinstance(report, list) else [report]
    if not projects:
        raise ValueError("Snyk Open Source reported no projects")

    issues = set()
    for project in projects:
        if not isinstance(project.get("vulnerabilities"), list) or project.get("error"):
            raise ValueError("Snyk Open Source returned an incomplete project result")
        target = project.get("targetFile") or project.get("displayTargetFile") or ""
        if Path(target).is_absolute():
            target = str(Path(target).relative_to(checkout))
        identity = (project.get("projectName") or target, target)
        for issue in project["vulnerabilities"]:
            path = tuple(issue.get("from", [])[1:])
            issues.add((*identity, issue["id"], issue.get("version", ""), path))
    return issues


def changed_lines(base):
    entries = subprocess.check_output(
        ["git", "diff", "--name-status", "-z", "--find-renames", "--diff-filter=AMRT", base, "HEAD", "--"]
    )
    fields = iter(entries.decode().rstrip("\0").split("\0")) if entries else iter(())
    changed = {}
    for status in fields:
        path = next(fields)
        files = [path]
        if status.startswith("R"):
            path = next(fields)
            files.append(path)
        if status == "R100":
            continue
        patch = subprocess.check_output(
            ["git", "--literal-pathspecs", "diff", "--no-ext-diff", "--find-renames", "--unified=0",
             base, "HEAD", "--", *files],
            text=True,
            errors="replace",
        )
        ranges = []
        for match in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", patch, re.M):
            start, count = int(match[1]), int(match[2] or "1")
            # For deletions consider the surviving lines adjacent to the removed code.
            end = start + 1 if count == 0 else start + count - 1
            ranges.append((max(1, start), end))
        changed[path] = ranges
    return changed


def issue_locations(issue):
    yield from issue.get("locations", ())
    yield from issue.get("relatedLocations", ())
    for flow in issue.get("codeFlows", ()):
        for thread in flow.get("threadFlows", ()):
            for step in thread.get("locations", ()):
                yield step.get("location", {})


def location_path(location, run):
    artifact = location.get("artifactLocation", {})
    if "uri" not in artifact and "index" in artifact:
        artifact = run["artifacts"][artifact["index"]]["location"]
    uri = urlsplit(artifact.get("uri", ""))
    if uri.scheme not in ("", "file") or not uri.path:
        return None
    path = Path(unquote(uri.path))
    if path.is_absolute():
        return str(path.relative_to(Path.cwd())) if path.is_relative_to(Path.cwd()) else None
    return str(path)


def code_issues(filename, base):
    report = load_report(filename)
    runs = report.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("Snyk Code did not return a SARIF scan")
    changes = changed_lines(base)
    matches = set()
    for run in runs:
        for issue in run.get("results", ()):
            for item in issue_locations(issue):
                location = item.get("physicalLocation", {})
                path = location_path(location, run)
                if path not in changes:
                    continue
                region = location.get("region", {})
                start = region.get("startLine")
                end = region.get("endLine", start)
                if start is None or any(start <= high and end >= low for low, high in changes[path]):
                    matches.add((issue["ruleId"], path, start or 0))
                    break
    return matches


def main():
    mode, *args = sys.argv[1:]
    if mode == "dependencies":
        baseline, baseline_dir, current = args
        existing = dependency_issues(baseline, Path(baseline_dir).resolve())
        issues = dependency_issues(current, Path.cwd()) - existing
    elif mode == "code":
        report, base = args
        issues = code_issues(report, base)
    else:
        raise ValueError(f"Unknown scan type: {mode}")

    print(f"Snyk {mode}: {len(issues)} finding(s) in the changes.")
    for issue in sorted(issues):
        print(json.dumps(issue))
    return bool(issues)


if __name__ == "__main__":
    sys.exit(main())
