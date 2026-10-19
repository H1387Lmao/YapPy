from .consts import BASE_URL
import aiohttp
import random
import asyncio

async def api_push(session: aiohttp.ClientSession, method: str, path: str, body=None, tries=3):
    headers = {
        "Authorization": f"Bot {session._bearer_token}",
        "Content-Type": "application/json"
    }

    try:
        async with session.request(method, BASE_URL + path, json=body, headers=headers, timeout=40) as r:
            r.raise_for_status()
            return await r.json()
    except aiohttp.ClientResponseError as e:
        try:
            err = await e.history[-1].json() if e.history else {}
        except Exception:
            err = {}

        msg = err.get("error") if isinstance(err, dict) else None
        busy = e.status == 503 and isinstance(err, dict) and "retry_after" in err
                
        wait = int(e.headers.get("Retry-After") or 0) if e.status == 429 or busy else 0
                
        if 0 < wait <= 60 and tries > 1:
            print(f"{'busy' if busy else 'rate limited'}, retrying in {wait}s")
            await asyncio.sleep(wait * (1 + random.random() * 0.5))
            return await api_push(session, method, path, body, tries - 1)
                    
        raise RuntimeError(f"{method} {path} failed ({e.status}): {msg or e.message}") from None

class API:
    @staticmethod
    async def _request(session, method, path="", body=None, tries=3):
        return await api_push(session, method, path, body, tries)

    @staticmethod
    async def get(session, path="", body=None, tries=3):
        return await API._request(session, "GET", path, body, tries)

    @staticmethod
    async def post(session, path="", body=None, tries=3):
        return await API._request(session, "POST", path, body, tries)

    @staticmethod
    async def put(session, path="", body=None, tries=3):
        return await API._request(session, "PUT", path, body, tries)

    @staticmethod
    async def patch(session, path="", body=None, tries=3):
        return await API._request(session, "PATCH", path, body, tries)

    @staticmethod
    async def delete(session, path="", body=None, tries=3):
        return await API._request(session, "DELETE", path, body, tries)

    @staticmethod
    async def send(session, channel_id=0, body=None, tries=3):
        return await API._request(session, "POST", f"/channels/{channel_id}/messages", body, tries)
        
