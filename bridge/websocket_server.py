import asyncio
import base64
import json
import secrets
from pathlib import Path

try:
    import websockets
except ImportError:
    msg = "websockets is required. Install with: pip install websockets"
    raise ImportError(msg)

from .capture import (
    batch_capture,
    capture_frame_jpeg,
    capture_screenshot,
)
from .adb_usb import list_usb_devices
from .adb_wifi import connect_wifi, list_wifi_devices
from .crawler import crawl_app
from .session import write_session, load_session

WS_PORT = 7700
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# Soft-launch defaults: ~6 fps preview, ~540px wide JPEG.
STREAM_INTERVAL_S = 0.16
STREAM_MAX_WIDTH = 540
STREAM_JPEG_QUALITY = 70

connected_clients = set()
_PAIRING_TOKEN: str | None = None


def _generate_token() -> str:
    return secrets.token_hex(8)


def _file_to_data_url(path: str | Path) -> str | None:
    """Encode a local PNG as a data URL so Glint-Web can display it in-browser."""
    try:
        raw = Path(path).read_bytes()
    except OSError:
        return None
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _paths_to_data_urls(paths: list) -> list[str]:
    out = []
    for p in paths:
        url = _file_to_data_url(p)
        if url:
            out.append(url)
    return out


async def _live_stream_loop(
    websocket,
    serial: str | None,
    interval: float,
    max_width: int,
    quality: int,
):
    """Push JPEG preview frames until cancelled."""
    loop = asyncio.get_running_loop()
    fails = 0
    while True:
        jpeg = await loop.run_in_executor(
            None,
            lambda: capture_frame_jpeg(
                serial=serial,
                max_width=max_width,
                quality=quality,
            ),
        )
        if jpeg:
            fails = 0
            b64 = base64.b64encode(jpeg).decode("ascii")
            await websocket.send(json.dumps({
                "type": "live_frame",
                "data_url": f"data:image/jpeg;base64,{b64}",
            }))
        else:
            fails += 1
            if fails == 1 or fails % 8 == 0:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Live mirror: no frame from device. Is ADB connected?",
                }))
            if fails >= 20:
                await websocket.send(json.dumps({
                    "type": "stream_stopped",
                    "reason": "no_frames",
                }))
                return
        await asyncio.sleep(interval)


async def handler(websocket):
    global _PAIRING_TOKEN

    # First message must be a valid pairing token
    try:
        raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        data = json.loads(raw)
        if data.get("action") != "pair" or data.get("token") != _PAIRING_TOKEN:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid pairing token. Request denied.",
            }))
            await websocket.close(1008, "Unauthorized")
            return
    except (asyncio.TimeoutError, json.JSONDecodeError):
        await websocket.close(1008, "Pairing required")
        return

    await websocket.send(json.dumps({"type": "paired", "success": True}))
    connected_clients.add(websocket)
    stream_task: asyncio.Task | None = None

    async def stop_stream(reason: str = "client", *, notify: bool = True):
        nonlocal stream_task
        had = stream_task is not None and not stream_task.done()
        if had:
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
        stream_task = None
        if had and notify:
            try:
                await websocket.send(json.dumps({
                    "type": "stream_stopped",
                    "reason": reason,
                }))
            except Exception:
                pass

    try:
        async for raw in websocket:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            action = data.get("action")

            if action == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

            elif action == "stream_start":
                await stop_stream("restart", notify=False)
                serial = data.get("serial") or None
                interval = float(data.get("interval", STREAM_INTERVAL_S))
                interval = max(0.08, min(1.0, interval))
                max_width = int(data.get("max_width", STREAM_MAX_WIDTH))
                quality = int(data.get("quality", STREAM_JPEG_QUALITY))
                stream_task = asyncio.create_task(
                    _live_stream_loop(websocket, serial, interval, max_width, quality),
                )
                await websocket.send(json.dumps({
                    "type": "stream_started",
                    "interval": interval,
                    "max_width": max_width,
                }))

            elif action == "stream_stop":
                await stop_stream("client")

            elif action == "capture_single":
                path = capture_screenshot()
                session = load_session()
                data_url = _file_to_data_url(path) if path else None
                await websocket.send(json.dumps({
                    "type": "screenshot",
                    "path": path,
                    "data_url": data_url,
                    "session": session,
                }))

            elif action == "capture_batch":
                count = data.get("count", 5)
                paths = batch_capture(count=count)
                if paths:
                    write_session(
                        screens=[Path(p).name for p in paths],
                        output_dir=OUTPUT_DIR,
                    )
                session = load_session()
                await websocket.send(json.dumps({
                    "type": "batch_result",
                    "paths": paths,
                    "data_urls": _paths_to_data_urls(paths),
                    "session": session,
                }))

            elif action == "crawl":
                package = data.get("package")
                max_screens = data.get("max_screens", 20)
                # AI key always from server env - never trust client-supplied secrets
                if "use_ai" not in data:
                    use_ai = None
                else:
                    use_ai = bool(data.get("use_ai"))
                if not package:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "package is required for crawl action",
                    }))
                else:
                    try:
                        paths = crawl_app(
                            package,
                            max_screens=max_screens,
                            use_ai=use_ai,
                        )
                        write_session(
                            screens=[Path(p).name for p in paths],
                            output_dir=OUTPUT_DIR,
                        )
                        session = load_session()
                        await websocket.send(json.dumps({
                            "type": "crawl_result",
                            "paths": paths,
                            "data_urls": _paths_to_data_urls(paths),
                            "session": session,
                        }))
                    except RuntimeError as e:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": str(e),
                        }))

            elif action == "crawl_web":
                url = data.get("url")
                max_screens = data.get("max_screens", 12)
                use_ai = True if data.get("use_ai") else (False if data.get("use_ai") is False else None)
                if not url:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "url is required for crawl_web action",
                    }))
                else:
                    try:
                        from .web_crawler import crawl_web

                        paths = crawl_web(
                            url,
                            max_screens=max_screens,
                            use_ai=use_ai,
                        )
                        write_session(
                            screens=[Path(p).name for p in paths],
                            output_dir=OUTPUT_DIR,
                        )
                        session = load_session()
                        await websocket.send(json.dumps({
                            "type": "crawl_result",
                            "paths": paths,
                            "data_urls": _paths_to_data_urls(paths),
                            "session": session,
                        }))
                    except RuntimeError as e:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": str(e),
                        }))

            elif action == "get_session":
                session = load_session()
                await websocket.send(json.dumps({
                    "type": "session",
                    "session": session,
                }))

            elif action == "list_devices":
                usb = list_usb_devices()
                wifi = list_wifi_devices()
                await websocket.send(json.dumps({
                    "type": "devices",
                    "usb": usb,
                    "wifi": wifi,
                }))

            elif action == "connect_wifi":
                ip = data.get("ip")
                if not ip:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "ip is required for connect_wifi action",
                    }))
                else:
                    port = data.get("port", 5555)
                    ok = connect_wifi(ip, port)
                    await websocket.send(json.dumps({
                        "type": "connect_result",
                        "success": ok,
                    }))

            else:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": f"Unknown action: {action}",
                }))
    finally:
        if stream_task and not stream_task.done():
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
        connected_clients.discard(websocket)


async def start_server(host: str = "127.0.0.1", port: int = WS_PORT):
    global _PAIRING_TOKEN
    _PAIRING_TOKEN = _generate_token()
    print(f"Glint Bridge WebSocket server on ws://{host}:{port}")
    print(f"Pairing token: {_PAIRING_TOKEN}")
    print("Clients must send {\"action\":\"pair\",\"token\":\"<token>\"} as first message.")
    async with websockets.serve(handler, host, port):
        await asyncio.Future()


def run():
    asyncio.run(start_server())


if __name__ == "__main__":
    run()
