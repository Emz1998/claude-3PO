#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from gh_utils import gh_json, load_config, run


def cmd_create(args, repo: str) -> None:
    """Create a pull request."""
    cmd = [
        "gh", "pr", "create",
        "--repo", repo,
        "--title", args.title,
        "--body", args.body,
        "--base", args.base,
    ]

    if args.head:
        cmd.extend(["--head", args.head])

    print(run(cmd))


def cmd_view(args, repo: str) -> None:
    """View pull request information."""
    cmd = [
        "gh", "pr", "view", args.pr_number,
        "--repo", repo,
        "--json", "number,title,state,body,url,author,headRefName,baseRefName,reviews,mergeable",
    ]

    pr = gh_json(cmd)
    if not pr:
        print(f"PR #{args.pr_number} not found")
        sys.exit(1)

    print(f"\n{'=' * 70}")
    print(f"PR #{pr['number']}: {pr['title']}")
    print(f"{'=' * 70}")
    print(f"State:     {pr['state']}")
    print(f"URL:       {pr['url']}")
    print(f"Author:    {pr['author']['login']}")
    print(f"Base:      {pr['baseRefName']}")
    print(f"Head:      {pr['headRefName']}")
    print(f"Mergeable: {pr['mergeable']}")
    print(f"\nBody:\n{pr['body']}")

    if pr.get("reviews"):
        print("\nReviews:")
        for review in pr["reviews"]:
            print(f"  - {review['author']['login']}: {review['state']}")


def cmd_review(args, repo: str) -> None:
    """Review a pull request."""
    cmd = ["gh", "pr", "review", args.pr_number, "--repo", repo]

    if args.approve:
        cmd.append("--approve")
    elif args.comment:
        cmd.extend(["--comment", "-b", args.comment])
    elif args.request_changes:
        cmd.extend(["--request-changes", "-b", args.request_changes])
    else:
        print("Error: Must specify --approve, --comment, or --request-changes")
        sys.exit(1)

    print(run(cmd))


def cmd_merge(args, repo: str) -> None:
    """Merge a pull request."""
    cmd = ["gh", "pr", "merge", args.pr_number, "--repo", repo]

    if args.squash:
        cmd.append("--squash")
    elif args.rebase:
        cmd.append("--rebase")
    elif args.merge:
        cmd.append("--merge")

    print(run(cmd))


def cmd_close(args, repo: str) -> None:
    """Close a pull request."""
    print(run(["gh", "pr", "close", args.pr_number, "--repo", repo]))


def cmd_list(args, repo: str) -> None:
    """List pull requests (all by default, or only active with --active)."""
    state = "open" if args.active else "all"
    cmd = [
        "gh", "pr", "list",
        "--repo", repo,
        "--json", "number,title,author,state",
        "--limit", "100",
        "--state", state,
    ]

    prs = gh_json(cmd)
    if not prs:
        label = "active PRs" if args.active else "PRs"
        print(f"No {label}")
        return

    print(f"\n{'=' * 80}")
    title = f"Active PRs ({len(prs)} total)" if args.active else f"All PRs ({len(prs)} total)"
    print(title)
    print(f"{'=' * 80}")
    for pr in prs:
        author = pr["author"]["login"] if pr.get("author") else "unknown"
        print(f"PR #{pr['number']}: {pr['title']} ({author}) - {pr['state']}")
    print(f"{'=' * 80}\n")


def cmd_is_open(args, repo: str) -> None:
    """Check if at least one PR is open. Returns true/false."""
    cmd = [
        "gh", "pr", "list",
        "--repo", repo,
        "--state", "open",
        "--json", "number",
        "--limit", "1",
    ]

    prs = gh_json(cmd)
    has_open = bool(prs)
    print("true" if has_open else "false")
    sys.exit(0 if has_open else 1)


COMMANDS = {
    "create": cmd_create,
    "view": cmd_view,
    "review": cmd_review,
    "merge": cmd_merge,
    "close": cmd_close,
    "list": cmd_list,
    "any-active": cmd_is_open,
}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage GitHub pull requests via gh CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list
  %(prog)s create --title "Fix bug" --body "Fixes #123" --base main --head feature
  %(prog)s view 42
  %(prog)s review 42 --approve
  %(prog)s review 42 --comment "Looks good!"
  %(prog)s merge 42 --squash
  %(prog)s close 42
  %(prog)s any-active
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # create
    create_parser = subparsers.add_parser("create", help="Create a pull request")
    create_parser.add_argument("--title", required=True, help="PR title")
    create_parser.add_argument("--body", required=True, help="PR body/description")
    create_parser.add_argument("--base", default="main", help="Base branch (default: main)")
    create_parser.add_argument("--head", help="Head branch")

    # view
    view_parser = subparsers.add_parser("view", help="View PR information")
    view_parser.add_argument("pr_number", help="PR number")

    # review
    review_parser = subparsers.add_parser("review", help="Review a pull request")
    review_parser.add_argument("pr_number", help="PR number")
    review_parser.add_argument("--approve", action="store_true", help="Approve the PR")
    review_parser.add_argument("--comment", help="Add a comment review")
    review_parser.add_argument("--request-changes", help="Request changes on the PR")

    # merge
    merge_parser = subparsers.add_parser("merge", help="Merge a pull request")
    merge_parser.add_argument("pr_number", help="PR number")
    merge_parser.add_argument("--squash", action="store_true", help="Use squash merge")
    merge_parser.add_argument("--rebase", action="store_true", help="Use rebase merge")
    merge_parser.add_argument("--merge", action="store_true", help="Use merge commit")

    # close
    close_parser = subparsers.add_parser("close", help="Close a pull request")
    close_parser.add_argument("pr_number", help="PR number")

    # list
    list_parser = subparsers.add_parser("list", help="List pull requests (all by default)")
    list_parser.add_argument("--active", action="store_true", help="List only active/open PRs")

    # any-active
    subparsers.add_parser("any-active", help="Check if any PR is active/open")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    config = load_config()
    repo = config.get("repo")
    if not repo:
        print("Error: 'repo' not found in config.yaml")
        sys.exit(1)

    try:
        COMMANDS[args.command](args, repo)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
