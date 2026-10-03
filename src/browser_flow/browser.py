"""浏览器 Profile 工厂。

为什么需要这个:
    1. Windows 上 browser-use 默认 chromium_sandbox=True 容易超时,
      提供统一开关方便所有示例关掉
    2. 未来 headless、executable_path、UA 等可统一在这里配置
    3. 测试时可以用同一函数 mock 浏览器

设计:
    - get_browser_profile():返回 BrowserProfile,默认 sandbox=False
    - 用户可传参覆盖(headless / executable_path 等)
"""

from __future__ import annotations

from browser_use.browser.profile import BrowserProfile


def get_browser_profile(
    headless: bool | None = None,
    executable_path: str | None = None,
    chromium_sandbox: bool = False,
) -> BrowserProfile:
    """返回 BrowserFlow 默认的浏览器配置。

    Args:
        headless:True/False/None。None 时读 BROWSER_HEADLESS 环境变量,默认 False。
        executable_path:None 时让 browser-use 自己找 Chrome。
        chromium_sandbox:Windows 上默认 False(避免 sandbox 限制启动超时)。

    Returns:
        BrowserProfile 实例
    """
    import os

    if headless is None:
        headless = os.environ.get("BROWSER_HEADLESS", "").lower() in {"1", "true", "yes"}

    return BrowserProfile(
        headless=headless,
        executable_path=executable_path,
        chromium_sandbox=chromium_sandbox,
    )
