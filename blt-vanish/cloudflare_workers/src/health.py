from datetime import datetime, timezone

from js import AbortSignal
from workers import fetch

from responses import json_response


BROKER_URLS = {
    "whitepages": "https://www.whitepages.com/suppression-requests",
    "spokeo": "https://www.spokeo.com/optout",
    "beenverified": "https://www.beenverified.com/app/optout/search",
    "truthfinder": "https://www.truthfinder.com/opt-out/",
    "intelius": "https://www.intelius.com/opt-out/",
}


async def handle_health_check(path):
    broker_id = path.removeprefix("/api/health/")
    if not broker_id:
        return json_response({"error": "Broker ID required"}, status=400)

    return json_response(await check_broker_health(broker_id))


async def check_broker_health(broker_id):
    url = BROKER_URLS.get(broker_id)
    if url is None:
        return {
            "brokerId": broker_id,
            "status": "unknown",
            "message": "Broker not found",
            "checkedAt": current_timestamp(),
        }

    try:
        response = await fetch(
            url,
            method="HEAD",
            headers={"User-Agent": "BLT-Vanish-HealthCheck/1.0"},
            signal=AbortSignal.timeout(5000),
        )
        is_healthy = 200 <= response.status < 400
        return {
            "brokerId": broker_id,
            "status": "healthy" if is_healthy else "degraded",
            "httpStatus": response.status,
            "message": (
                "Broker site is accessible"
                if is_healthy
                else "Broker site may be experiencing issues"
            ),
            "checkedAt": current_timestamp(),
            "url": url,
        }
    except Exception as error:
        return {
            "brokerId": broker_id,
            "status": "error",
            "message": "Failed to check broker health",
            "error": str(error),
            "checkedAt": current_timestamp(),
            "url": url,
        }


def current_timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
