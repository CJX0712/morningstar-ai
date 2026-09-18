"""将同步生成器放到后台线程执行，以异步生成器方式产出。

用于把阻塞式的 LLM 流式调用（openai SDK 同步接口）安全地接入 FastAPI 的事件循环，
在流式吐字的同时不阻塞其他请求。
"""
from __future__ import annotations

import asyncio
import threading
from collections.abc import Generator
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def run_generator_in_thread(gen_factory: Callable[..., Generator[T, None, None]], *args, **kwargs):
    """把同步生成器转入守护线程，返回一个异步生成器。"""
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def producer() -> None:
        try:
            for item in gen_factory(*args, **kwargs):
                asyncio.run_coroutine_threadsafe(queue.put(("item", item)), loop)
            asyncio.run_coroutine_threadsafe(queue.put(("stop", None)), loop)
        except Exception as exc:  # noqa: BLE001
            asyncio.run_coroutine_threadsafe(queue.put(("error", str(exc))), loop)

    threading.Thread(target=producer, daemon=True).start()

    async def async_gen():
        while True:
            kind, value = await queue.get()
            if kind == "stop":
                break
            if kind == "error":
                raise RuntimeError(value)
            yield value

    return async_gen()
