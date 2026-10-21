import json

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from website.models import (
    OsshArticle,
    OsshCommunity,
    OsshDiscussionChannel,
    Repo,
    Tag,
)


class OsshCatalogViewTests(TestCase):
    """Tests for the ossh_catalog view (GET /api/ossh/catalog/).

    Covers the JSON response shape, the empty-database case, method
    restriction (POST -> 405), and that prefetch_related("tags") keeps the
    query count flat as the number of rows grows (no N+1).
    """

    url_name = "ossh_catalog"

    def _seed_one_of_each(self, suffix=""):
        """Create exactly one Repo, OsshCommunity, OsshDiscussionChannel and
        OsshArticle, each carrying two tags. ``suffix`` keeps the unique
        fields distinct so this can be called more than once."""
        tag_python = Tag.objects.create(name=f"python{suffix}")
        tag_security = Tag.objects.create(name=f"security{suffix}")

        repo = Repo.objects.create(
            name=f"Repo {suffix}",
            repo_url=f"https://example.com/repo{suffix}",
            description="A test repo",
            primary_language="Python",
            stars=42,
            forks=7,
        )
        repo.tags.add(tag_python, tag_security)

        community = OsshCommunity.objects.create(
            name=f"Community {suffix}",
            description="A test community",
            website=f"https://example.com/community{suffix}",
            source="GitHub",
            category="community",
            external_id=f"com_{suffix}",
            contributors_count=12,
        )
        community.tags.add(tag_python)

        channel = OsshDiscussionChannel.objects.create(
            name=f"Channel {suffix}",
            description="A test channel",
            source="Discord",
            external_id=f"ch_{suffix}",
            member_count=100,
            invite_url=f"https://example.com/invite{suffix}",
            logo_url=f"https://example.com/logo{suffix}.png",
        )
        channel.tags.add(tag_python, tag_security)

        article = OsshArticle.objects.create(
            title=f"Article {suffix}",
            author="Test Author",
            author_profile_image=f"https://example.com/avatar{suffix}.png",
            description="A test article",
            publication_date=timezone.now(),
            source="Medium",
            external_id=f"art_{suffix}",
            url=f"https://example.com/article{suffix}",
            cover_image=f"https://example.com/cover{suffix}.png",
            reading_time_minutes=5,
        )
        article.tags.add(tag_security)

    # ------------------------------------------------------------------
    # Response shape
    # ------------------------------------------------------------------
    def test_catalog_returns_expected_top_level_keys(self):
        self._seed_one_of_each(suffix="1")
        response = self.client.get(reverse(self.url_name))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = json.loads(response.content)
        self.assertEqual(
            set(data.keys()),
            {"repos", "communities", "discussion_channels", "articles"},
        )
        for key in data:
            self.assertEqual(len(data[key]), 1)

    def test_repo_item_fields(self):
        self._seed_one_of_each(suffix="1")
        data = json.loads(self.client.get(reverse(self.url_name)).content)

        repo = data["repos"][0]
        self.assertEqual(
            set(repo.keys()),
            {
                "name",
                "url",
                "description",
                "primary_language",
                "stars",
                "forks",
                "tags",
            },
        )
        self.assertEqual(repo["name"], "Repo 1")
        self.assertEqual(repo["url"], "https://example.com/repo1")
        self.assertEqual(repo["primary_language"], "Python")
        self.assertEqual(repo["stars"], 42)
        self.assertEqual(repo["forks"], 7)
        self.assertCountEqual(repo["tags"], ["python1", "security1"])

    def test_community_item_fields(self):
        self._seed_one_of_each(suffix="1")
        data = json.loads(self.client.get(reverse(self.url_name)).content)

        community = data["communities"][0]
        self.assertEqual(
            set(community.keys()),
            {
                "name",
                "description",
                "website",
                "source",
                "category",
                "contributors_count",
                "tags",
            },
        )
        self.assertEqual(community["name"], "Community 1")
        self.assertEqual(community["website"], "https://example.com/community1")
        self.assertEqual(community["source"], "GitHub")
        self.assertEqual(community["category"], "community")
        self.assertEqual(community["contributors_count"], 12)
        self.assertCountEqual(community["tags"], ["python1"])

    def test_discussion_channel_item_fields(self):
        self._seed_one_of_each(suffix="1")
        data = json.loads(self.client.get(reverse(self.url_name)).content)

        channel = data["discussion_channels"][0]
        self.assertEqual(
            set(channel.keys()),
            {
                "name",
                "description",
                "source",
                "member_count",
                "invite_url",
                "logo_url",
                "tags",
            },
        )
        self.assertEqual(channel["name"], "Channel 1")
        self.assertEqual(channel["source"], "Discord")
        self.assertEqual(channel["member_count"], 100)
        self.assertEqual(channel["invite_url"], "https://example.com/invite1")
        self.assertCountEqual(channel["tags"], ["python1", "security1"])

    def test_article_item_fields(self):
        self._seed_one_of_each(suffix="1")
        data = json.loads(self.client.get(reverse(self.url_name)).content)

        article = data["articles"][0]
        self.assertEqual(
            set(article.keys()),
            {
                "title",
                "author",
                "author_profile_image",
                "description",
                "publication_date",
                "source",
                "url",
                "cover_image",
                "reading_time_minutes",
                "tags",
            },
        )
        self.assertEqual(article["title"], "Article 1")
        self.assertEqual(article["author"], "Test Author")
        self.assertEqual(article["source"], "Medium")
        self.assertEqual(article["url"], "https://example.com/article1")
        self.assertEqual(article["reading_time_minutes"], 5)
        self.assertNotEqual(article["publication_date"], "")
        self.assertCountEqual(article["tags"], ["security1"])

    # ------------------------------------------------------------------
    # Empty database
    # ------------------------------------------------------------------
    def test_empty_database_returns_empty_lists(self):
        response = self.client.get(reverse(self.url_name))

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(
            data,
            {
                "repos": [],
                "communities": [],
                "discussion_channels": [],
                "articles": [],
            },
        )

    # ------------------------------------------------------------------
    # Method restriction
    # ------------------------------------------------------------------
    def test_post_not_allowed(self):
        response = self.client.post(reverse(self.url_name))
        self.assertEqual(response.status_code, 405)

    # ------------------------------------------------------------------
    # N+1 guard: query count must not grow with the number of rows
    # ------------------------------------------------------------------
    def test_query_count_is_constant_regardless_of_row_count(self):
        # Four models are read, each with prefetch_related("tags"): one query
        # for the model rows plus one query for its prefetched tags = 2 queries
        # per model, 8 in total. The point of the test is that this number does
        # NOT grow with the number of rows (which an N+1 bug would cause).
        expected_queries = 8

        self._seed_one_of_each(suffix="1")
        with self.assertNumQueries(expected_queries):
            self.client.get(reverse(self.url_name))

        # Adding two more of every kind must not change the query count thanks
        # to prefetch_related("tags").
        self._seed_one_of_each(suffix="2")
        self._seed_one_of_each(suffix="3")
        with self.assertNumQueries(expected_queries):
            self.client.get(reverse(self.url_name))
