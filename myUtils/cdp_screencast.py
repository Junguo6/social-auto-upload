import asyncio
import json
import os
import sys
from typing import Optional


class CDPScreencastBridge:
    """
    CDPScreencastBridge 建立与 Chromium 的 CDP 会话，
    负责抽取出实时渲染画面帧 (JPEG Base64)，并接收前端发来的鼠标与键盘输入反向控制。
    """
    def __init__(self, page, task_id: str = ""):
        self.page = page
        self.task_id = task_id or os.environ.get("CURRENT_TASK_ID", "live")
        self.cdp = None
        self._running = False
        self._input_task: Optional[asyncio.Task] = None

    async def start(self, quality: int = 85, max_width: int = 1440, max_height: int = 900, target_fps: int = 20):
        try:
            # 兼容 patchright 与 playwright 的 new_cdp_session
            self.cdp = await self.page.context.new_cdp_session(self.page)
            self._running = True

            min_interval = 1.0 / float(target_fps)
            last_frame_ts = 0.0

            async def _on_frame(params):
                nonlocal last_frame_ts
                if not self._running or not self.cdp:
                    return
                session_id = params.get("sessionId")
                data = params.get("data")
                metadata = params.get("metadata", {})

                dev_w = metadata.get("deviceWidth", max_width)
                dev_h = metadata.get("deviceHeight", max_height)
                self._frame_width = dev_w
                self._frame_height = dev_h

                # 必须立即回复 FrameAck，Chromium 才会继续下发后续帧
                try:
                    await self.cdp.send("Page.screencastFrameAck", {"sessionId": session_id})
                except Exception:
                    pass

                now = asyncio.get_event_loop().time()
                # 动态背压节流：若推送频次高于 target_fps，直接丢弃冗余帧，杜绝 CPU 与 IPC 拥塞
                if now - last_frame_ts < min_interval:
                    return

                last_frame_ts = now

                frame_event = {
                    "taskId": self.task_id,
                    "data": data,
                    "width": dev_w,
                    "height": dev_h,
                    "offsetTop": metadata.get("offsetTop", 0),
                    "pageScaleFactor": metadata.get("pageScaleFactor", 1),
                }
                # 输出单行紧凑帧格式
                sys.stdout.write(f"[CDP_FRAME] {json.dumps(frame_event)}\n")
                sys.stdout.flush()

            self.cdp.on("Page.screencastFrame", _on_frame)

            # 激活 Page 域
            try:
                await self.cdp.send("Page.enable")
            except Exception:
                pass

            await self.cdp.send("Page.startScreencast", {
                "format": "jpeg",
                "quality": quality,
                "maxWidth": max_width,
                "maxHeight": max_height,
                "everyNthFrame": 1
            })

            # 监听页面跨域跳转与刷新，自动重绑 Screencast 激活，防止扫码跳转后 Chromium 静默挂起卡死
            async def _on_navigated(frame):
                if not self._running or not self.cdp:
                    return
                try:
                    if frame == self.page.main_frame:
                        await self.cdp.send("Page.startScreencast", {
                            "format": "jpeg",
                            "quality": quality,
                            "maxWidth": max_width,
                            "maxHeight": max_height,
                            "everyNthFrame": 1
                        })
                except Exception:
                    pass

            self.page.on("framenavigated", _on_navigated)

            # 启动 stdin 输入监听协程
            self._input_task = asyncio.create_task(self._listen_stdin())
            sys.stdout.write(f"[CDP_INFO] Screencast started successfully for task {self.task_id} (FPS: {target_fps})\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"CDP startScreencast warning: {e}\n")
            sys.stderr.flush()

    async def _listen_stdin(self):
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        try:
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        except Exception:
            return

        while self._running:
            try:
                line_bytes = await reader.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8").strip()
                if not line or not line.startswith("{"):
                    continue
                cmd = json.loads(line)
                await self._handle_input_command(cmd)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _handle_input_command(self, cmd: dict):
        if not self.cdp:
            return
        action = cmd.get("action")

        # 视口尺寸等比映射：将前端投屏画面坐标精确映射到 Chromium 内部网页视口坐标
        vp = getattr(self.page, "viewport_size", None) or {"width": 1440, "height": 900}
        vp_w = float(vp.get("width", 1440))
        vp_h = float(vp.get("height", 900))
        fw = float(getattr(self, "_frame_width", 1440) or 1440)
        fh = float(getattr(self, "_frame_height", 900) or 900)
        scale_x = vp_w / fw if fw > 0 else 1.0
        scale_y = vp_h / fh if fh > 0 else 1.0

        if action == "click":
            raw_x = float(cmd.get("x", 0))
            raw_y = float(cmd.get("y", 0))
            x = raw_x * scale_x
            y = raw_y * scale_y
            button = cmd.get("button", "left")
            buttons = 1 if button == "left" else (2 if button == "right" else 4)
            try:
                # 1. 移动到目标坐标
                await self.cdp.send("Input.dispatchMouseEvent", {
                    "type": "mouseMoved", "x": x, "y": y, "button": "none", "buttons": 0, "pointerType": "mouse"
                })
                # 2. 按下按键 (携带正确 buttons 掩码)
                await self.cdp.send("Input.dispatchMouseEvent", {
                    "type": "mousePressed", "x": x, "y": y, "button": button, "buttons": buttons, "clickCount": 1, "pointerType": "mouse"
                })
                await asyncio.sleep(0.02)
                # 3. 抬起按键 (触发标准 DOM click 事件)
                await self.cdp.send("Input.dispatchMouseEvent", {
                    "type": "mouseReleased", "x": x, "y": y, "button": button, "buttons": 0, "clickCount": 1, "pointerType": "mouse"
                })
            except Exception:
                pass
        elif action == "mouse":
            event_type = cmd.get("type", "mouseMoved")
            raw_x = float(cmd.get("x", 0))
            raw_y = float(cmd.get("y", 0))
            x = raw_x * scale_x
            y = raw_y * scale_y
            button = cmd.get("button", "none")
            click_count = cmd.get("clickCount", 1)

            buttons = 0
            if button == "left":
                buttons = 1
            elif button == "right":
                buttons = 2
            elif button == "middle":
                buttons = 4
            if event_type == "mouseReleased":
                buttons = 0
            elif event_type == "mouseMoved":
                button = "none"

            params = {
                "type": event_type,
                "x": x,
                "y": y,
                "button": button,
                "buttons": buttons,
                "clickCount": click_count if event_type in ("mousePressed", "mouseReleased") else 0,
                "pointerType": "mouse"
            }
            if event_type == "mouseWheel":
                params["button"] = "none"
                params["deltaX"] = cmd.get("deltaX", 0)
                params["deltaY"] = cmd.get("deltaY", 0)
            try:
                await self.cdp.send("Input.dispatchMouseEvent", params)
            except Exception:
                pass
        elif action == "key":
            event_type = cmd.get("type", "keyDown")
            params = {
                "type": event_type,
                "key": cmd.get("key", ""),
                "text": cmd.get("text", ""),
                "unmodifiedText": cmd.get("text", ""),
            }
            try:
                await self.cdp.send("Input.dispatchKeyEvent", params)
            except Exception:
                pass

    async def stop(self):
        self._running = False
        if self._input_task and not self._input_task.done():
            self._input_task.cancel()
        if self.cdp:
            try:
                await self.cdp.send("Page.stopScreencast")
                await self.cdp.detach()
            except Exception:
                pass
            self.cdp = None


async def maybe_attach_screencast(page, task_id: str = "") -> Optional[CDPScreencastBridge]:
    """
    如果环境变量 ENABLE_SCREENCAST == "1"，则自动为该 page 开启 CDP 实时投屏与交互桥接。
    """
    if os.environ.get("ENABLE_SCREENCAST") == "1":
        tid = task_id or os.environ.get("CURRENT_TASK_ID", "live")
        bridge = CDPScreencastBridge(page, task_id=tid)
        page._cdp_bridge = bridge
        await bridge.start()
        return bridge
    return None


def _hook_api_module(api_module, module_name: str = "patchright"):
    """
    钩入指定库 (patchright 或 playwright) 的核心生命周期对象，
    确保所有通过 new_page()、new_context()、launch_persistent_context() 创建的页面均被捕获并自动挂载投屏。
    """
    if not api_module:
        return

    # 1. 钩入 BrowserContext.new_page
    if hasattr(api_module, "BrowserContext"):
        ctx_cls = api_module.BrowserContext
        if not getattr(ctx_cls, "_screencast_hooked", False):
            orig_new_page = ctx_cls.new_page

            async def hooked_new_page(self, *args, **kwargs):
                page = await orig_new_page(self, *args, **kwargs)
                try:
                    tid = os.environ.get("CURRENT_TASK_ID", "live")
                    bridge = CDPScreencastBridge(page, task_id=tid)
                    page._cdp_bridge = bridge
                    asyncio.create_task(bridge.start())
                except Exception as e:
                    sys.stderr.write(f"[{module_name}] cdp start error on new_page: {e}\n")
                    sys.stderr.flush()
                return page

            ctx_cls.new_page = hooked_new_page
            ctx_cls._screencast_hooked = True

    # 2. 钩入 Browser.new_page
    if hasattr(api_module, "Browser"):
        browser_cls = api_module.Browser
        if not getattr(browser_cls, "_screencast_hooked", False):
            orig_browser_new_page = browser_cls.new_page

            async def hooked_browser_new_page(self, *args, **kwargs):
                page = await orig_browser_new_page(self, *args, **kwargs)
                try:
                    tid = os.environ.get("CURRENT_TASK_ID", "live")
                    bridge = CDPScreencastBridge(page, task_id=tid)
                    page._cdp_bridge = bridge
                    asyncio.create_task(bridge.start())
                except Exception as e:
                    sys.stderr.write(f"[{module_name}] cdp start error on browser.new_page: {e}\n")
                    sys.stderr.flush()
                return page

            browser_cls.new_page = hooked_browser_new_page
            browser_cls._screencast_hooked = True

        # 钩入 Browser.new_context 监听 context.on("page")
        if not getattr(browser_cls, "_ctx_screencast_hooked", False):
            orig_new_ctx = browser_cls.new_context

            async def hooked_new_context(self, *args, **kwargs):
                ctx = await orig_new_ctx(self, *args, **kwargs)
                try:
                    def _on_page(p):
                        if not getattr(p, "_cdp_bridge", None):
                            tid = os.environ.get("CURRENT_TASK_ID", "live")
                            bridge = CDPScreencastBridge(p, task_id=tid)
                            p._cdp_bridge = bridge
                            asyncio.create_task(bridge.start())
                    ctx.on("page", _on_page)
                except Exception:
                    pass
                return ctx

            browser_cls.new_context = hooked_new_context
            browser_cls._ctx_screencast_hooked = True

    # 3. 钩入 BrowserType.launch_persistent_context
    if hasattr(api_module, "BrowserType"):
        bt_cls = api_module.BrowserType
        if not getattr(bt_cls, "_screencast_hooked", False):
            orig_launch_persistent = bt_cls.launch_persistent_context

            async def hooked_launch_persistent(self, *args, **kwargs):
                ctx = await orig_launch_persistent(self, *args, **kwargs)
                try:
                    tid = os.environ.get("CURRENT_TASK_ID", "live")
                    for p in ctx.pages:
                        if not getattr(p, "_cdp_bridge", None):
                            bridge = CDPScreencastBridge(p, task_id=tid)
                            p._cdp_bridge = bridge
                            asyncio.create_task(bridge.start())
                    def _on_persistent_page(p):
                        if not getattr(p, "_cdp_bridge", None):
                            bridge = CDPScreencastBridge(p, task_id=tid)
                            p._cdp_bridge = bridge
                            asyncio.create_task(bridge.start())
                    ctx.on("page", _on_persistent_page)
                except Exception:
                    pass
                return ctx

            bt_cls.launch_persistent_context = hooked_launch_persistent
            bt_cls._screencast_hooked = True


def install_global_screencast_hook():
    """
    当环境变量 ENABLE_SCREENCAST == '1' 时，
    全局钩入 patchright 和 playwright 的核心生命周期，
    使所有平台、所有页面（包括登录扫码、滑块验证、上传流程）全自动开启 CDP 实时画布投屏与反向输入通道。
    """
    if os.environ.get("ENABLE_SCREENCAST") != "1":
        return

    # 1. 拦截 patchright (主要用于抖音、快手、视频号等平台防风控内核)
    try:
        import patchright.async_api as patchright_api
        _hook_api_module(patchright_api, "patchright")
    except Exception as exc:
        sys.stderr.write(f"patchright screencast hook warning: {exc}\n")
        sys.stderr.flush()

    # 2. 拦截 playwright (备用或部分标准流程)
    try:
        import playwright.async_api as playwright_api
        _hook_api_module(playwright_api, "playwright")
    except Exception as exc:
        pass
