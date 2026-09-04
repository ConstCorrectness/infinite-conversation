"""
FastAPI Server for The Infinite Conversation.
Serves the web application and streams conversation audio (.wav/.mp3), subtitles (.vtt),
and playlist manifests infinitely from the live site with intelligent local caching.
"""

import os
import httpx
from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional

from backend.pipeline import ConversationPipeline, get_master_index

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
REMOTE_SITE_DATA = "https://www.infiniteconversation.com/data"

app = FastAPI(title="The Infinite Conversation", version="1.0.0")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

class GenerateBatchRequest(BaseModel):
    batch_id: Optional[str] = None
    num_turns: int = 6
    starting_speaker: str = "werner"
    initial_prompt: Optional[str] = None
    provider: str = "auto"

@app.get("/api/status")
async def get_status():
    master = get_master_index()
    return {
        "status": "online",
        "streaming_source": "live_infinite_conversation",
        "local_batches_count": len(master),
        "has_gemini_key": bool(os.environ.get("GEMINI_API_KEY")),
        "has_openai_key": bool(os.environ.get("OPENAI_API_KEY")),
    }

@app.get("/data/conversations.json")
async def get_conversations():
    """
    Fetches the 139 conversation batches from infiniteconversation.com,
    falling back to local batches if remote is unreachable.
    """
    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.get(f"{REMOTE_SITE_DATA}/conversations.json.php")
            if resp.status_code == 200:
                remote_data = resp.json()
                # Also save a cached copy
                with open(os.path.join(DATA_DIR, "conversations_remote_cache.json"), "w", encoding="utf-8") as f:
                    import json
                    json.dump(remote_data, f, indent=2)
                return remote_data
    except Exception as e:
        print(f"[Proxy] Error fetching remote conversations list: {e}")

    # Fallback to local master index
    return get_master_index()

@app.get("/data/{playlist_id}/{filename}")
async def get_data_file(playlist_id: str, filename: str, request: Request):
    """
    Streams audio (.wav / .mp3), subtitle (.vtt), and manifest (.json) files.
    First checks local cache; if missing, streams from infiniteconversation.com and caches locally.
    """
    local_dir = os.path.join(DATA_DIR, playlist_id)
    local_path = os.path.join(local_dir, filename)

    # 1. If already cached locally, serve immediately with range support
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        media_type = "audio/wav" if filename.endswith(".wav") else "audio/mpeg" if filename.endswith(".mp3") else "text/vtt" if filename.endswith(".vtt") else "application/json"
        return FileResponse(local_path, media_type=media_type)

    remote_url = f"{REMOTE_SITE_DATA}/{playlist_id}/{filename}"

    # 2. For JSON manifests and WebVTT subtitles: fetch, cache, and return
    if filename.endswith(".json") or filename.endswith(".vtt"):
        try:
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                resp = await client.get(remote_url)
                if resp.status_code == 200:
                    os.makedirs(local_dir, exist_ok=True)
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
                    media_type = "application/json" if filename.endswith(".json") else "text/vtt"
                    return Response(content=resp.content, media_type=media_type, headers={"access-control-allow-origin": "*"})
                raise HTTPException(status_code=resp.status_code, detail="Remote file not found")
        except Exception as e:
            print(f"[Proxy] Error fetching {remote_url}: {e}")
            raise HTTPException(status_code=502, detail=f"Failed to fetch {filename} from live site")

    # 3. For Audio files (.wav / .mp3): stream to client and cache on disk
    os.makedirs(local_dir, exist_ok=True)
    client = httpx.AsyncClient(verify=False, timeout=45.0)
    
    # Forward client range headers if present
    forward_headers = {}
    if "range" in request.headers:
        forward_headers["range"] = request.headers["range"]

    try:
        req = client.build_request("GET", remote_url, headers=forward_headers)
        remote_resp = await client.send(req, stream=True)

        if remote_resp.status_code not in (200, 206):
            await remote_resp.aclose()
            await client.aclose()
            raise HTTPException(status_code=remote_resp.status_code, detail="Remote audio not found")

        async def stream_and_cache():
            cache_file = None
            # Only cache on a clean 200 full response
            if remote_resp.status_code == 200:
                cache_temp = local_path + ".tmp"
                try:
                    cache_file = open(cache_temp, "wb")
                except Exception:
                    cache_file = None

            try:
                async for chunk in remote_resp.aiter_bytes():
                    if cache_file:
                        try:
                            cache_file.write(chunk)
                        except Exception:
                            pass
                    yield chunk
            finally:
                if cache_file:
                    cache_file.close()
                    try:
                        if os.path.exists(cache_temp) and os.path.getsize(cache_temp) > 0:
                            os.replace(cache_temp, local_path)
                    except Exception:
                        pass
                await remote_resp.aclose()
                await client.aclose()

        resp_headers = {
            "access-control-allow-origin": "*",
            "accept-ranges": "bytes"
        }
        if "content-length" in remote_resp.headers:
            resp_headers["content-length"] = remote_resp.headers["content-length"]
        if "content-range" in remote_resp.headers:
            resp_headers["content-range"] = remote_resp.headers["content-range"]

        media_type = remote_resp.headers.get("content-type", "audio/wav")

        return StreamingResponse(
            stream_and_cache(),
            status_code=remote_resp.status_code,
            headers=resp_headers,
            media_type=media_type
        )
    except Exception as e:
        print(f"[Proxy] Streaming error for {remote_url}: {e}")
        await client.aclose()
        raise HTTPException(status_code=502, detail="Streaming audio failed")

# Static assets mounts
app.mount("/css", StaticFiles(directory=os.path.join(STATIC_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(STATIC_DIR, "js")), name="js")
app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"error": "index.html not found"}, status_code=404)
