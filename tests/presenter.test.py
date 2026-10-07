"""Presenter window ownership against a loopback Chromium control service.

Install deckgen[presenter], then run: python tests/presenter.test.py
No ClassPoint account, capture or remote class is used.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from aiohttp import web

source = Path(__file__).resolve().parents[1] / 'src/deckgen/presenter_lifecycle.py'
if source.is_file():
    spec = importlib.util.spec_from_file_location('window_lifecycle', source)
    lifecycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lifecycle)
else:
    lifecycle = None


class DeckSelectionTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(lifecycle is not None and hasattr(lifecycle, 'select_deck'), 'Latest presentation selection is missing')
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        (self.project / 'deck').mkdir()

    def course(self, decks):
        (self.project / 'deckgen.toml').write_text('[course]\ncode="TEST"\ndecks=' + repr(decks) + '\n')

    def module(self, name):
        (self.project / 'deck' / f'{name}.py').write_text('raise RuntimeError("Selection must not execute modules")\n')

    def test_latest_follows_declared_order_without_executing_modules(self):
        self.course(['week05', 'workshop'])
        for name in ('week05', 'workshop', 'week99_future_draft'):
            self.module(name)
        self.assertEqual(lifecycle.select_deck(self.project), 'workshop')

    def test_new_declared_presentation_is_selected_without_launcher_changes(self):
        self.module('week05')
        self.course(['week05'])
        self.assertEqual(lifecycle.select_deck(self.project), 'week05')
        self.module('week06')
        self.course(['week05', 'week06'])
        self.assertEqual(lifecycle.select_deck(self.project), 'week06')

    def test_missing_latest_deck_fails_instead_of_opening_an_older_lesson(self):
        self.module('week05')
        self.course(['week05', 'week06'])
        with self.assertRaises(FileNotFoundError):
            lifecycle.select_deck(self.project)

    def test_explicit_selection_can_open_an_earlier_deck(self):
        self.course(['week05', 'week06'])
        self.module('week05')
        self.module('week06')
        self.assertEqual(lifecycle.select_deck(self.project, 'week05'), 'week05')

    def test_deck_selection_rejects_paths_outside_the_course(self):
        self.course(['../outside'])
        with self.assertRaises(ValueError):
            lifecycle.select_deck(self.project)


class WindowLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.assertIsNotNone(lifecycle, 'Deckgen does not provide the window lifecycle controller')
        self.url = 'http://127.0.0.1:8765'
        self.operator = {'id': 'operator', 'type': 'page', 'url': self.url + '/'}
        self.audience = {'id': 'audience', 'type': 'page', 'url': self.url + '/assets/audience.html'}
        self.targets = [self.operator, self.audience]
        self.polls = 0
        self.browser_failed = False
        self.activation_failed = False
        self.activations = []
        self.ends = 0
        self.notifications = 0
        self.tasks = []

        async def targets(request):
            self.polls += 1
            if self.browser_failed:
                raise web.HTTPServiceUnavailable()
            return web.json_response(self.targets)

        async def activate(request):
            if self.activation_failed:
                raise web.HTTPServiceUnavailable()
            self.activations.append(request.match_info['target'])
            return web.Response(text='Target activated')

        app = web.Application()
        app.router.add_get('/json/list', targets)
        app.router.add_get('/json/activate/{target}', activate)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '127.0.0.1', 0)
        await site.start()
        self.browser_url = f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'

    async def asyncTearDown(self):
        for task in getattr(self, 'tasks', []):
            task.cancel()
        await asyncio.gather(*getattr(self, 'tasks', []), return_exceptions=True)
        if hasattr(self, 'runner'):
            await self.runner.cleanup()

    async def eventually(self, check):
        async with asyncio.timeout(3):
            while not check():
                await asyncio.sleep(0.01)

    async def end(self):
        self.ends += 1

    async def notify(self):
        self.notifications += 1

    async def watch(self, end=None, notify=None, **options):
        settings = dict(poll_interval=0.01, close_grace=0.04, disconnect_grace=0.12, startup_grace=0.15)
        settings.update(options)
        monitor = lifecycle.WindowMonitor(
            self.browser_url, self.url, end or self.end, notify or self.notify, **settings,
        )
        task = asyncio.create_task(monitor.run())
        self.tasks.append(task)
        await self.eventually(lambda: self.polls >= 2)
        return task

    async def test_operator_close_waits_for_remote_shutdown_confirmation(self):
        confirmed = asyncio.Event()

        async def end():
            self.ends += 1
            await confirmed.wait()

        task = await self.watch(end=end)
        self.targets = [self.audience]
        await self.eventually(lambda: self.ends == 1)
        self.assertFalse(task.done())
        confirmed.set()
        await asyncio.wait_for(task, 3)
        self.assertEqual(self.ends, 1)

    async def test_audience_close_keeps_operator_alive(self):
        task = await self.watch()
        self.targets = [self.operator]
        before = self.polls
        await self.eventually(lambda: self.polls >= before + 8)
        self.assertFalse(task.done())
        self.assertEqual(self.ends, 0)

    async def test_reload_with_query_and_fragment_keeps_session(self):
        task = await self.watch()
        self.targets = [{**self.operator, 'url': self.url + '/?reload=1#slide-4'}]
        before = self.polls
        await self.eventually(lambda: self.polls >= before + 8)
        self.assertFalse(task.done())
        self.assertEqual(self.ends, 0)

    async def test_transient_browser_control_failure_keeps_session(self):
        task = await self.watch()
        self.browser_failed = True
        before = self.polls
        await self.eventually(lambda: self.polls >= before + 2)
        self.browser_failed = False
        before = self.polls
        await self.eventually(lambda: self.polls >= before + 8)
        self.assertFalse(task.done())
        self.assertEqual(self.ends, 0)

    async def test_browser_crash_triggers_shutdown(self):
        task = await self.watch()
        self.browser_failed = True
        await asyncio.wait_for(task, 3)
        self.assertEqual(self.ends, 1)

    async def test_failed_cleanup_keeps_service_available_until_reopened(self):
        async def end():
            self.ends += 1
            if self.ends == 1:
                raise RuntimeError('Mock shutdown rejected')

        task = await self.watch(end=end)
        self.targets = [self.audience]
        await self.eventually(lambda: self.notifications == 1)
        before = self.polls
        await self.eventually(lambda: self.polls >= before + 8)
        self.assertFalse(task.done())
        self.assertEqual(self.ends, 1)
        self.targets = [self.operator, self.audience]
        before = self.polls
        await self.eventually(lambda: self.polls >= before + 2)
        self.targets = [self.audience]
        await asyncio.wait_for(task, 3)
        self.assertEqual(self.ends, 2)

    async def test_notification_failure_does_not_discard_failed_cleanup(self):
        async def end():
            self.ends += 1
            raise RuntimeError('Mock shutdown rejected')

        async def notify():
            self.notifications += 1
            raise OSError('Desktop notification service unavailable')

        task = await self.watch(end=end, notify=notify)
        self.targets = []
        await self.eventually(lambda: self.notifications == 1)
        before = self.polls
        await self.eventually(lambda: task.done() or self.polls >= before + 8)
        self.assertFalse(task.done())
        self.assertEqual(self.ends, 1)

    async def test_shutdown_timeout_keeps_service_available(self):
        async def end():
            self.ends += 1
            await asyncio.Event().wait()

        task = await self.watch(end=end, shutdown_timeout=0.03)
        self.targets = []
        await self.eventually(lambda: self.notifications == 1)
        before = self.polls
        await self.eventually(lambda: self.polls >= before + 8)
        self.assertFalse(task.done())
        self.assertEqual(self.ends, 1)

    async def test_application_io_error_keeps_service_available(self):
        async def end():
            self.ends += 1
            raise OSError('Mock application cleanup failed')

        task = await self.watch(end=end)
        self.targets = []
        await self.eventually(lambda: self.notifications == 1 or task.done())
        self.assertFalse(task.done())
        self.assertEqual(self.notifications, 1)

    async def test_browser_never_opening_exits_after_startup_grace(self):
        self.targets = []
        task = await self.watch()
        await asyncio.wait_for(task, 3)
        self.assertEqual(self.ends, 1)

    async def test_relaunch_focuses_operator_and_does_not_reuse_audience(self):
        self.assertTrue(await lifecycle.reuse_presenter(self.browser_url, self.url))
        self.assertEqual(self.activations, ['operator'])
        self.targets = [self.audience]
        self.assertFalse(await lifecycle.reuse_presenter(self.browser_url, self.url))
        self.assertEqual(self.activations, ['operator'])

    async def test_activation_failure_does_not_authorize_a_duplicate_window(self):
        self.activation_failed = True
        with self.assertRaises(RuntimeError):
            await lifecycle.reuse_presenter(self.browser_url, self.url)

    async def test_unavailable_browser_control_does_not_authorize_a_duplicate_window(self):
        self.browser_failed = True
        with self.assertRaises(RuntimeError):
            await lifecycle.reuse_presenter(self.browser_url, self.url)


if __name__ == '__main__':
    unittest.main()
