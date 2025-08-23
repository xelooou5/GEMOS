#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
üêô GEM OS - GitHub Plugin (plugins/github_plugin.py)

Provides GitHub API integration.
Registers commands:
- "github:repos" (list user repos)
- "github:issues" (list repo issues)
- "github:create_issue" (create a new issue)
"""

from __future__ import annotations
import requests
import json
import os
from typing import Dict, Any


CONFIG_FILE = "data/github_config.json"
API_URL = "https://api.github.com"


def _load_config() -> Dict[str, Any]:
    """Load GitHub token and user."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def list_repos() -> str:
    """List user repositories."""
    cfg = _load_config()
    if not cfg.get("token") or not cfg.get("user"):
        return "‚ö†Ô∏è GitHub config missing (data/github_config.json)."

    headers = {"Authorization": f"token {cfg['token']}"}
    url = f"{API_URL}/users/{cfg['user']}/repos"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        repos = [repo["name"] for repo in r.json()]
        return "üìÇ Repos:\n" + "\n".join(repos)
    except Exception as e:
        return f"‚ùå Error listing repos: {e}"


def list_issues(repo: str) -> str:
    """List issues for a given repository."""
    cfg = _load_config()
    if not cfg.get("token") or not cfg.get("user"):
        return "‚ö†Ô∏è GitHub config missing."

    headers = {"Authorization": f"token {cfg['token']}"}
    url = f"{API_URL}/repos/{cfg['user']}/{repo}/issues"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        issues = [f"#{i['number']} - {i['title']}" for i in r.json()]
        if not issues:
            return f"üì≠ Nenhuma issue em {repo}."
        return f"üêû Issues em {repo}:\n" + "\n".join(issues)
    except Exception as e:
        return f"‚ùå Error listing issues: {e}"


def create_issue(repo: str, title: str, body: str = "") -> str:
    """Create a new issue in a repository."""
    cfg = _load_config()
    if not cfg.get("token") or not cfg.get("user"):
        return "‚ö†Ô∏è GitHub config missing."

    headers = {
        "Authorization": f"token {cfg['token']}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"{API_URL}/repos/{cfg['user']}/{repo}/issues"
    data = {"title": title, "body": body}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=10)
        r.raise_for_status()
        issue = r.json()
        return f"‚úÖ Issue criada em {repo}: #{issue['number']} - {issue['title']}"
    except Exception as e:
        return f"‚ùå Error creating issue: {e}"


def register(plugin_manager):
    """Register plugin commands."""
    plugin_manager.register_command("github:repos", list_repos)
    plugin_manager.register_command("github:issues", list_issues)
    plugin_manager.register_command("github:create_issue", create_issue)
