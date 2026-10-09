# -*- coding: utf-8 -*-
"""让 Windows 控制台能正常打印中文与 Ω、τ、² 等符号。

    ★ 这个文件现在是可选的 ★
    它的功能已经并入 setup_ngspice.py（那个文件还会顺便配置 ngspice 的 dll 路径）。
    本书所有脚本统一用：
        from setup_ngspice import setup
        setup()
    所以你不必单独 import 本文件 —— 保留它只是为了兼容你自己的旧脚本。
    直接运行本文件可以做一次中文显示自检。

背景（零基础必看）：
    Windows 的终端默认用 GBK 编码，而源码里的中文是 UTF-8。
    如果直接 print('τ = 1 ms')，程序可能报
        UnicodeEncodeError: 'gbk' codec can't encode character ...
    解决办法：把标准输出重新配置成 UTF-8。

用法（放在脚本最前面）：
    from console_utf8 import enable_utf8
    enable_utf8()
"""

import io
import sys


def enable_utf8() -> None:
    """把 stdout / stderr 切成 UTF-8。失败也不影响程序继续运行。"""
    for stream_name in ('stdout', 'stderr'):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            # Python 3.7+ 才支持 reconfigure，旧版本走下面的兼容分支
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            try:
                buffer = getattr(stream, 'buffer', None)
                if buffer is not None:
                    setattr(sys, stream_name,
                            io.TextIOWrapper(buffer, encoding='utf-8', errors='replace'))
            except Exception:
                pass


if __name__ == '__main__':
    enable_utf8()
    print('中文测试：τ = 1 ms，fc = 159.2 Hz，R = 10 kΩ，V² 、² 符号正常。')
