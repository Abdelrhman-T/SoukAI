from typing import Any

import requests

from helpers.config import Settings


class FacebookClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.page_access_token = settings.FACEBOOK_PAGE_ACCESS_TOKEN
        self.graph_version = settings.META_GRAPH_VERSION
        self.base_url = f"https://graph.facebook.com/{self.graph_version}"

        if not self.page_access_token:
            raise ValueError("FACEBOOK_PAGE_ACCESS_TOKEN is missing from .env")

    def get_page_posts(self, page_id: str, limit: int = 25) -> dict[str, Any]:
        url = f"{self.base_url}/{page_id}/posts"

        response = requests.get(
            url,
            params={
                "access_token": self.page_access_token,
                "fields": "id,message,created_time,permalink_url,full_picture",
                "limit": limit,
            },
            timeout=30,
        )

        data = response.json()

        if not response.ok:
            raise RuntimeError(f"Facebook API error: {data}")

        return data

    def get_all_page_posts(self, page_id: str, limit: int = 25, max_pages: int = 10) -> list[dict[str, Any]]:
        """
        Fetch posts with pagination.

        limit: number of posts per request
        max_pages: safety limit to avoid infinite pagination
        """
        url = f"{self.base_url}/{page_id}/posts"

        params = {
            "access_token": self.page_access_token,
            "fields": "id,message,created_time,permalink_url,full_picture",
            "limit": limit,
        }

        all_posts: list[dict[str, Any]] = []

        for _ in range(max_pages):
            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            if not response.ok:
                raise RuntimeError(f"Facebook API error: {data}")

            all_posts.extend(data.get("data", []))

            next_url = data.get("paging", {}).get("next")
            if not next_url:
                break

            # next URL already contains access token and pagination cursor
            url = next_url
            params = None

        return all_posts

    def get_post_comments(self, post_id: str, limit: int = 100) -> dict[str, Any]:
        url = f"{self.base_url}/{post_id}/comments"

        response = requests.get(
            url,
            params={
                "access_token": self.page_access_token,
                "fields": "id,message,from,created_time",
                "limit": limit,
            },
            timeout=30,
        )

        data = response.json()

        if not response.ok:
            raise RuntimeError(f"Facebook API error: {data}")

        return data

    def reply_to_comment(self, comment_id: str, message: str) -> dict[str, Any]:
        url = f"{self.base_url}/{comment_id}/comments"

        response = requests.post(
            url,
            data={
                "message": message,
                "access_token": self.page_access_token,
            },
            timeout=30,
        )

        data = response.json()

        if not response.ok:
            raise RuntimeError(f"Facebook API error: {data}")

        return data
