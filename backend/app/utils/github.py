"""GitHub API yardımcıları — repo doğrulama ve metadata."""
import re
import httpx


GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/?.#]+)"
)


async def validate_repo_url(url: str) -> dict:
    """Repo'nun mevcut ve public olup olmadığını kontrol eder."""
    m = GITHUB_URL_RE.match(url)
    if not m:
        return {"invalid": True}

    owner, repo = m.group("owner"), m.group("repo")
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(api_url, headers={"Accept": "application/vnd.github+json"})
        except httpx.RequestError:
            return {"not_found": True}

    if resp.status_code == 404:
        return {"not_found": True}
    if resp.status_code == 403:
        return {"private": True}
    if resp.status_code != 200:
        return {"not_found": True}

    data = resp.json()
    return {
        "private": data.get("private", False),
        "size_kb": data.get("size", 0),
        "language": data.get("language"),
        "description": data.get("description"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "default_branch": data.get("default_branch", "main"),
    }


async def get_repo_size_mb(url: str) -> float:
    info = await validate_repo_url(url)
    return info.get("size_kb", 0) / 1024
