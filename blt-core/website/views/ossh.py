import json
import re
import time
from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from website.models import OsshArticle, OsshCommunity, OsshDiscussionChannel
from website.utils import fetch_github_user_data, get_client_ip


def is_valid_github_username(username):
    if not isinstance(username, str):
        return False
    return re.match(r"^(?!-)[A-Za-z0-9-]{1,39}(?<!-)$", username) is not None


def rate_limit(max_requests=20, window_sec=60, methods=("POST",)):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                response = view_func(request, *args, **kwargs)
                response["X-RateLimit-Limit"] = str(max_requests)
                return response

            key = f"rl:{get_client_ip(request)}:{request.path}"
            now = int(time.time())
            cached = cache.get(key)

            if isinstance(cached, dict):
                count = int(cached.get("count", 0))
                reset_at = int(cached.get("reset_at", now + window_sec))
                if reset_at <= now:
                    count = 0
                    reset_at = now + window_sec
            else:
                count = int(cached) if isinstance(cached, int) else 0
                reset_at = now + window_sec

            if count >= max_requests:
                retry_after = max(1, reset_at - now)
                response = JsonResponse({"error": "Rate limit exceeded"}, status=429)
                response["X-RateLimit-Limit"] = str(max_requests)
                response["X-RateLimit-Remaining"] = "0"
                response["Retry-After"] = str(retry_after)
                return response

            count += 1
            cache.set(key, {"count": count, "reset_at": reset_at}, timeout=max(1, reset_at - now))

            response = view_func(request, *args, **kwargs)
            response["X-RateLimit-Limit"] = str(max_requests)
            response["X-RateLimit-Remaining"] = str(max(0, max_requests - count))
            return response

        return wrapper

    return decorator


def _weighted_tag_score(item_tags, user_tags):
    item_tag_set = {t.name.lower() for t in item_tags}
    matches = [(tag, weight) for tag, weight in user_tags if tag.lower() in item_tag_set]
    score = sum(weight for _, weight in matches)
    return score, matches


def discussion_channel_recommender(user_tags, language_weights, top_n=10):
    recommendations = []
    for channel in OsshDiscussionChannel.objects.prefetch_related("tags").all():
        score, matches = _weighted_tag_score(channel.tags.all(), user_tags)
        if score > 0:
            recommendations.append(
                {
                    "channel": channel,
                    "relevance_score": score,
                    "reasoning": "Matching tags: " + ", ".join(tag for tag, _ in matches),
                }
            )
    recommendations.sort(key=lambda x: x["relevance_score"], reverse=True)
    return recommendations[:top_n]


def community_recommender(user_tags, language_weights, top_n=10):
    recommendations = []
    normalized_languages = {k.lower(): v for k, v in (language_weights or {}).items()}

    for community in OsshCommunity.objects.prefetch_related("tags").all():
        score, matches = _weighted_tag_score(community.tags.all(), user_tags)
        language = (community.metadata or {}).get("primary_language")
        language_bonus = normalized_languages.get(language.lower(), 0) if isinstance(language, str) else 0
        total_score = score + language_bonus

        if total_score > 0:
            reasoning_parts = []
            if matches:
                reasoning_parts.append("Matching tags: " + ", ".join(tag for tag, _ in matches))
            if language_bonus:
                reasoning_parts.append(f"Language match: {language}")
            recommendations.append(
                {
                    "community": community,
                    "relevance_score": total_score,
                    "reasoning": "; ".join(reasoning_parts),
                }
            )

    recommendations.sort(key=lambda x: x["relevance_score"], reverse=True)
    return recommendations[:top_n]


def article_recommender(user_tags, language_weights, top_n=10):
    recommendations = []
    for article in OsshArticle.objects.prefetch_related("tags").all():
        score, matches = _weighted_tag_score(article.tags.all(), user_tags)
        if score > 0:
            recommendations.append(
                {
                    "article": article,
                    "relevance_score": score,
                    "reasoning": "Matching tags: " + ", ".join(tag for tag, _ in matches),
                }
            )
    recommendations.sort(key=lambda x: x["relevance_score"], reverse=True)
    return recommendations[:top_n]


def repo_recommender(user_tags, language_weights, top_n=10):
    return []


@require_GET
def ossh_home(request):
    return JsonResponse({"status": "ok"})


@require_GET
def ossh_results(request):
    return JsonResponse({"status": "ok"})


@require_POST
@rate_limit(max_requests=20, window_sec=60, methods=("POST",))
def get_github_data(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    username = payload.get("github_username")
    if not is_valid_github_username(username):
        return JsonResponse({"error": "Invalid GitHub username"}, status=400)

    data = fetch_github_user_data(username)
    return JsonResponse(data or {}, status=200)


def _parse_recommender_request(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return [], {}
    return payload.get("user_tags", []), payload.get("language_weights", {})


@require_POST
def get_recommended_repos(request):
    user_tags, language_weights = _parse_recommender_request(request)
    recommendations = repo_recommender(user_tags, language_weights)
    return JsonResponse({"recommendations": recommendations})


@require_POST
def get_recommended_communities(request):
    user_tags, language_weights = _parse_recommender_request(request)
    recommendations = community_recommender(user_tags, language_weights)
    data = [
        {
            "id": item["community"].id,
            "name": item["community"].name,
            "relevance_score": item["relevance_score"],
            "reasoning": item["reasoning"],
        }
        for item in recommendations
    ]
    return JsonResponse({"recommendations": data})


@require_POST
def get_recommended_discussion_channels(request):
    user_tags, language_weights = _parse_recommender_request(request)
    recommendations = discussion_channel_recommender(user_tags, language_weights)
    data = [
        {
            "id": item["channel"].id,
            "name": item["channel"].name,
            "relevance_score": item["relevance_score"],
            "reasoning": item["reasoning"],
        }
        for item in recommendations
    ]
    return JsonResponse({"recommendations": data})


@require_POST
def get_recommended_articles(request):
    user_tags, language_weights = _parse_recommender_request(request)
    recommendations = article_recommender(user_tags, language_weights)
    data = [
        {
            "id": item["article"].id,
            "title": item["article"].title,
            "relevance_score": item["relevance_score"],
            "reasoning": item["reasoning"],
        }
        for item in recommendations
    ]
    return JsonResponse({"recommendations": data})
