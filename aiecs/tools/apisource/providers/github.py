"""
GitHub API Provider

Provides access to GitHub's REST API for repository data, user information,
issues, pull requests, and more.

API Documentation: https://docs.github.com/en/rest
API Rate Limits: 
  - Authenticated: 5,000 requests/hour
  - Unauthenticated: 60 requests/hour

Authentication:
  - Personal Access Token (recommended)
  - OAuth token
  - GitHub App installation token

API Etiquette:
  - Use authentication for higher rate limits
  - Include User-Agent header
  - Respect rate limits
  - Cache responses when possible
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from aiecs.tools.apisource.providers.base import (
    BaseAPIProvider,
    expose_operation,
)

logger = logging.getLogger(__name__)

# Optional HTTP client
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class GitHubProvider(BaseAPIProvider):
    """
    GitHub API provider for repository and user data.

    Provides access to:
    - Repository information and statistics
    - User profiles and activity
    - Issues and pull requests
    - Search across repositories, users, code
    - Organization data
    """

    BASE_URL = "https://api.github.com"

    @property
    def name(self) -> str:
        return "github"

    @property
    def description(self) -> str:
        return "GitHub API for repositories, users, issues, and code search"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_repository",
            "search_repositories",
            "get_user",
            "search_users",
            "get_repository_issues",
            "get_repository_pulls",
            "search_code",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for GitHub operations"""

        if operation == "get_repository":
            if "owner" not in params or "repo" not in params:
                return False, "Missing required parameters: owner and repo"

        elif operation == "search_repositories":
            if "query" not in params:
                return False, "Missing required parameter: query"

        elif operation == "get_user":
            if "username" not in params:
                return False, "Missing required parameter: username"

        elif operation == "search_users":
            if "query" not in params:
                return False, "Missing required parameter: query"

        elif operation == "get_repository_issues":
            if "owner" not in params or "repo" not in params:
                return False, "Missing required parameters: owner and repo"

        elif operation == "get_repository_pulls":
            if "owner" not in params or "repo" not in params:
                return False, "Missing required parameters: owner and repo"

        elif operation == "search_code":
            if "query" not in params:
                return False, "Missing required parameter: query"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_repository",
        description="Get detailed information about a GitHub repository",
    )
    def get_repository(
        self,
        owner: str,
        repo: str,
    ) -> Dict[str, Any]:
        """
        Get repository information.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name

        Returns:
            Dictionary containing repository data and metadata
        """
        return self.execute("get_repository", {"owner": owner, "repo": repo})

    @expose_operation(
        operation_name="search_repositories",
        description="Search for GitHub repositories",
    )
    def search_repositories(
        self,
        query: str,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for repositories.

        Args:
            query: Search query string
            sort: Sort field (stars, forks, updated)
            order: Sort order (asc, desc)
            per_page: Results per page (max 100)

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order
        if per_page:
            params["per_page"] = per_page

        return self.execute("search_repositories", params)

    @expose_operation(
        operation_name="get_user",
        description="Get information about a GitHub user",
    )
    def get_user(self, username: str) -> Dict[str, Any]:
        """
        Get user information.

        Args:
            username: GitHub username

        Returns:
            Dictionary containing user data
        """
        return self.execute("get_user", {"username": username})

    @expose_operation(
        operation_name="search_users",
        description="Search for GitHub users",
    )
    def search_users(
        self,
        query: str,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for users.

        Args:
            query: Search query string
            sort: Sort field (followers, repositories, joined)
            order: Sort order (asc, desc)
            per_page: Results per page (max 100)

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order
        if per_page:
            params["per_page"] = per_page

        return self.execute("search_users", params)

    @expose_operation(
        operation_name="get_repository_issues",
        description="Get issues for a GitHub repository",
    )
    def get_repository_issues(
        self,
        owner: str,
        repo: str,
        state: Optional[str] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get repository issues.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all)
            per_page: Results per page (max 100)

        Returns:
            Dictionary containing issues data
        """
        params: Dict[str, Any] = {"owner": owner, "repo": repo}
        if state:
            params["state"] = state
        if per_page:
            params["per_page"] = per_page

        return self.execute("get_repository_issues", params)

    @expose_operation(
        operation_name="get_repository_pulls",
        description="Get pull requests for a GitHub repository",
    )
    def get_repository_pulls(
        self,
        owner: str,
        repo: str,
        state: Optional[str] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get repository pull requests.

        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state (open, closed, all)
            per_page: Results per page (max 100)

        Returns:
            Dictionary containing pull requests data
        """
        params: Dict[str, Any] = {"owner": owner, "repo": repo}
        if state:
            params["state"] = state
        if per_page:
            params["per_page"] = per_page

        return self.execute("get_repository_pulls", params)

    @expose_operation(
        operation_name="search_code",
        description="Search for code across GitHub repositories",
    )
    def search_code(
        self,
        query: str,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for code.

        Args:
            query: Search query string
            sort: Sort field (indexed)
            order: Sort order (asc, desc)
            per_page: Results per page (max 100)

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order
        if per_page:
            params["per_page"] = per_page

        return self.execute("search_code", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from GitHub API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for GitHub provider")

        # Get API token if available
        api_token = self.config.get("api_key") or self.config.get("token")
        timeout = self.config.get("timeout", 30)

        # Set headers
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": self.config.get(
                "user_agent",
                "AIECS-APISource/2.0 (https://github.com/your-org/aiecs)"
            ),
        }

        # Add authentication if token is available
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"

        # Build endpoint based on operation
        if operation == "get_repository":
            owner = params["owner"]
            repo = params["repo"]
            endpoint = f"{self.BASE_URL}/repos/{owner}/{repo}"
            query_params = {}

        elif operation == "search_repositories":
            endpoint = f"{self.BASE_URL}/search/repositories"
            query_params = {"q": params["query"]}
            if "sort" in params:
                query_params["sort"] = params["sort"]
            if "order" in params:
                query_params["order"] = params["order"]
            if "per_page" in params:
                query_params["per_page"] = params["per_page"]

        elif operation == "get_user":
            username = params["username"]
            endpoint = f"{self.BASE_URL}/users/{username}"
            query_params = {}

        elif operation == "search_users":
            endpoint = f"{self.BASE_URL}/search/users"
            query_params = {"q": params["query"]}
            if "sort" in params:
                query_params["sort"] = params["sort"]
            if "order" in params:
                query_params["order"] = params["order"]
            if "per_page" in params:
                query_params["per_page"] = params["per_page"]

        elif operation == "get_repository_issues":
            owner = params["owner"]
            repo = params["repo"]
            endpoint = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"
            query_params = {}
            if "state" in params:
                query_params["state"] = params["state"]
            if "per_page" in params:
                query_params["per_page"] = params["per_page"]

        elif operation == "get_repository_pulls":
            owner = params["owner"]
            repo = params["repo"]
            endpoint = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls"
            query_params = {}
            if "state" in params:
                query_params["state"] = params["state"]
            if "per_page" in params:
                query_params["per_page"] = params["per_page"]

        elif operation == "search_code":
            endpoint = f"{self.BASE_URL}/search/code"
            query_params = {"q": params["query"]}
            if "sort" in params:
                query_params["sort"] = params["sort"]
            if "order" in params:
                query_params["order"] = params["order"]
            if "per_page" in params:
                query_params["per_page"] = params["per_page"]

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.get(
                endpoint,
                params=query_params,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()

            data = response.json()

            # Extract relevant data based on operation
            if operation in ["search_repositories", "search_users", "search_code"]:
                # Search endpoints return items in 'items' field
                result_data = data.get("items", [])
            else:
                # Direct endpoints return data directly
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"GitHub API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"GitHub API request failed: {e}")
            raise Exception(f"GitHub API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for GitHub operations"""

        schemas = {
            "get_repository": {
                "description": "Get detailed information about a GitHub repository",
                "parameters": {
                    "owner": {
                        "type": "string",
                        "required": True,
                        "description": "Repository owner (username or organization)",
                        "examples": ["octocat", "microsoft", "python"],
                    },
                    "repo": {
                        "type": "string",
                        "required": True,
                        "description": "Repository name",
                        "examples": ["Hello-World", "vscode", "cpython"],
                    },
                },
            },
            "search_repositories": {
                "description": "Search for GitHub repositories",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query string",
                        "examples": ["machine learning", "language:python stars:>1000", "topic:api"],
                    },
                    "sort": {
                        "type": "string",
                        "required": False,
                        "description": "Sort field",
                        "examples": ["stars", "forks", "updated"],
                    },
                    "order": {
                        "type": "string",
                        "required": False,
                        "description": "Sort order",
                        "examples": ["asc", "desc"],
                        "default": "desc",
                    },
                    "per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                        "examples": [10, 30, 100],
                        "default": 30,
                    },
                },
            },
            "get_user": {
                "description": "Get information about a GitHub user",
                "parameters": {
                    "username": {
                        "type": "string",
                        "required": True,
                        "description": "GitHub username",
                        "examples": ["octocat", "torvalds", "gvanrossum"],
                    }
                },
            },
            "search_users": {
                "description": "Search for GitHub users",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query string",
                        "examples": ["tom", "location:san-francisco followers:>100", "language:python"],
                    },
                    "sort": {
                        "type": "string",
                        "required": False,
                        "description": "Sort field",
                        "examples": ["followers", "repositories", "joined"],
                    },
                    "order": {
                        "type": "string",
                        "required": False,
                        "description": "Sort order",
                        "examples": ["asc", "desc"],
                        "default": "desc",
                    },
                    "per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                        "examples": [10, 30, 100],
                        "default": 30,
                    },
                },
            },
            "get_repository_issues": {
                "description": "Get issues for a GitHub repository",
                "parameters": {
                    "owner": {
                        "type": "string",
                        "required": True,
                        "description": "Repository owner",
                        "examples": ["octocat", "microsoft"],
                    },
                    "repo": {
                        "type": "string",
                        "required": True,
                        "description": "Repository name",
                        "examples": ["Hello-World", "vscode"],
                    },
                    "state": {
                        "type": "string",
                        "required": False,
                        "description": "Issue state",
                        "examples": ["open", "closed", "all"],
                        "default": "open",
                    },
                    "per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                        "examples": [10, 30, 100],
                        "default": 30,
                    },
                },
            },
            "get_repository_pulls": {
                "description": "Get pull requests for a GitHub repository",
                "parameters": {
                    "owner": {
                        "type": "string",
                        "required": True,
                        "description": "Repository owner",
                        "examples": ["octocat", "microsoft"],
                    },
                    "repo": {
                        "type": "string",
                        "required": True,
                        "description": "Repository name",
                        "examples": ["Hello-World", "vscode"],
                    },
                    "state": {
                        "type": "string",
                        "required": False,
                        "description": "Pull request state",
                        "examples": ["open", "closed", "all"],
                        "default": "open",
                    },
                    "per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                        "examples": [10, 30, 100],
                        "default": 30,
                    },
                },
            },
            "search_code": {
                "description": "Search for code across GitHub repositories",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query string",
                        "examples": ["addClass in:file language:js", "repo:octocat/Hello-World"],
                    },
                    "sort": {
                        "type": "string",
                        "required": False,
                        "description": "Sort field",
                        "examples": ["indexed"],
                    },
                    "order": {
                        "type": "string",
                        "required": False,
                        "description": "Sort order",
                        "examples": ["asc", "desc"],
                        "default": "desc",
                    },
                    "per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                        "examples": [10, 30, 100],
                        "default": 30,
                    },
                },
            },
        }

        return schemas.get(operation)


