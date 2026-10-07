"""Own the presenter session independently of browser unload handlers."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import tomllib
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import quote, urlsplit

try:
    import aiohttp
except ImportError as error:
    raise ImportError('Install deckgen[presenter] to use the presenter window controller.') from error


def select_deck(project: Path | str, requested: str = 'latest') -> str:
    """Select the last declared deck, or an explicit module, without executing it."""
    root = Path(project).resolve()
    if requested == 'latest':
        settings = tomllib.loads((root / 'deckgen.toml').read_text(encoding='utf-8'))
        decks = settings.get('course', {}).get('decks', [])
        if not isinstance(decks, list) or not decks:
            raise ValueError('The course has no declared presentations.')
        requested = decks[-1]
    if not isinstance(requested, str) or not requested or Path(requested).name != requested or requested in {'.', '..'}:
        raise ValueError('Choose a deck module name inside the course.')
    if not (root / 'deck' / f'{requested}.py').is_file():
        raise FileNotFoundError(f'The selected deck module is missing: {requested}')
    return requested


def operator_target(target: dict, presenter_url: str) -> bool:
    actual = urlsplit(target.get("url", ""))
    expected = urlsplit(presenter_url)
    return (
        target.get("type") == "page"
        and (actual.scheme, actual.netloc, actual.path.rstrip("/"))
        == (expected.scheme, expected.netloc, expected.path.rstrip("/"))
    )


async def read_targets(session: aiohttp.ClientSession, browser_url: str) -> list[dict]:
    async with session.get(browser_url + "/json/list") as response:
        response.raise_for_status()
        targets = await response.json()
    if not isinstance(targets, list) or any(not isinstance(target, dict) for target in targets):
        raise ValueError("Invalid browser target list")
    return targets


async def reuse_presenter(browser_url: str, presenter_url: str) -> bool:
    """Focus the operator; return False only after confirming its absence.

    Browser control errors raise so callers cannot mistake failure for permission
    to open a duplicate operator.
    """
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            targets = await read_targets(session, browser_url)
            target = next((target for target in targets if operator_target(target, presenter_url)), None)
            if not target:
                return False
            async with session.get(browser_url + "/json/activate/" + quote(target["id"], safe="")) as response:
                response.raise_for_status()
            return True
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError):
        raise RuntimeError('Could not inspect or activate the existing presenter window. Retry when browser control is available.') from None


class WindowMonitor:
    """Return after the operator disappears and end_session confirms cleanup.

    end_session owns remote protocol cleanup; raising leaves the local session
    available until the operator reopens it and closes it again. Audience pages
    and operator reloads do not end the session. Browser control must be loopback.
    """

    def __init__(
        self, browser_url: str, presenter_url: str,
        end_session: Callable[[], Awaitable[object]],
        notify_failure: Callable[[], Awaitable[None]],
        *, poll_interval: float = 0.5, close_grace: float = 2,
        disconnect_grace: float = 5, startup_grace: float = 60,
        shutdown_timeout: float = 90,
    ):
        self.browser_url = browser_url
        self.presenter_url = presenter_url
        self.end_session = end_session
        self.notify_failure = notify_failure
        self.poll_interval = poll_interval
        self.close_grace = close_grace
        self.disconnect_grace = disconnect_grace
        self.startup_grace = startup_grace
        self.shutdown_timeout = shutdown_timeout

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        started = loop.time()
        seen = False
        missing_since = None
        wait_for_reopen = False
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            while True:
                unavailable = False
                try:
                    targets = await read_targets(session, self.browser_url)
                    present = any(operator_target(target, self.presenter_url) for target in targets)
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                    present = False
                    unavailable = True
                now = loop.time()
                if present:
                    seen = True
                    missing_since = None
                    wait_for_reopen = False
                elif not wait_for_reopen:
                    if missing_since is None:
                        missing_since = now
                    grace = self.disconnect_grace if unavailable else self.close_grace
                    expired = now - missing_since >= grace if seen else now - started >= self.startup_grace
                    if expired:
                        try:
                            await asyncio.wait_for(self.end_session(), self.shutdown_timeout)
                            return
                        except Exception:
                            # Retain the service and session so reopening can retry cleanup.
                            wait_for_reopen = True
                            try:
                                await self.notify_failure()
                            except Exception:
                                logging.getLogger(__name__).warning('Could not display the session cleanup notification.')
                await asyncio.sleep(self.poll_interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reuse an existing presenter window")
    parser.add_argument("presenter_url")
    parser.add_argument("--browser-url", default="http://127.0.0.1:9331")
    args = parser.parse_args()
    try:
        sys.exit(0 if asyncio.run(reuse_presenter(args.browser_url, args.presenter_url)) else 1)
    except RuntimeError as error:
        parser.exit(2, str(error) + '\n')
