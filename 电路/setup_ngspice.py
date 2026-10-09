# -*- coding: utf-8 -*-
"""让 PySpice 找到 ngspice 共享库（dll），并顺手解决中文与警告噪音问题。

背景（这是本课件里最容易卡住的一环）：
    PySpice 通过 ffi.dlopen() **动态加载 ngspice 的共享库 dll**，
    它**不会**去启动 ngspice.exe。所以：
      · 有 ngspice.exe、`ngspice --version` 能打印版本  —— 不代表 PySpice 能用；
      · 真正需要的是 **ngspice.dll** 这个文件。
    有些 ngspice 的 Windows 发行包只带 exe、不带 dll，这时怎么改 PATH 都没用。

用法（放在脚本最前面，必须在 import PySpice 之前）：
    from setup_ngspice import setup
    setup()

它会做四件事：
    1. 若环境变量 NGSPICE_LIBRARY_PATH 未设置，则自动探测常见的 dll 位置；
    2. 设置 SPICE_LIB_DIR（**必须设**，否则会撞上 PySpice 的一个 bug，详见下）；
    3. 让终端支持中文（UTF-8）；
    4. 屏蔽 ngspice 的 "Unsupported Ngspice version" 提示。

关于第 2 点的 bug：
    PySpice 的 Shared.py 里，当你设置了 NGSPICE_LIBRARY_PATH 时，
    它会跳过内部变量 NGSPICE_PATH 的赋值，但后面又用 Path(NGSPICE_PATH) 去拼路径，
    于是抛出与 ngspice 毫不相干的
        TypeError: argument should be a str or an os.PathLike object ... not 'NoneType'
    预先设好 SPICE_LIB_DIR 就能跳过那段代码。所以两个变量要一起设。
"""

import io
import os
import sys

# 候选 dll 位置（按优先级）。第一项是本机实际安装位置。
_DLL_CANDIDATES = (
    r'D:\software\Spice64\bin\ngspice.dll',
    r'C:\Spice64\bin\ngspice.dll',
    r'C:\Spice64\dll-vs\ngspice.dll',
    r'C:\Program Files\Spice64\bin\ngspice.dll',
)

# 与 dll 配套的 spinit/脚本目录（注意：要指向含 scripts\spinit 的那个 share 目录，
# 不是 dll 所在的 bin 目录，否则 ngspice 会提示 can't find the initialization file spinit）
_LIB_DIR_CANDIDATES = (
    r'D:\software\Spice64\share\ngspice',
    r'C:\Spice64\share\ngspice',
    r'C:\Program Files\Spice64\share\ngspice',
)


def _enable_console_utf8() -> None:
    """Windows 终端默认 GBK，打印 τ/²/Ω 会报 UnicodeEncodeError。"""
    for name in ('stdout', 'stderr'):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            try:
                buf = getattr(stream, 'buffer', None)
                if buf is not None:
                    setattr(sys, name,
                            io.TextIOWrapper(buf, encoding='utf-8', errors='replace'))
            except Exception:
                pass


def _quiet_ngspice_noise() -> None:
    """过滤 PySpice / ngspice 打往 stderr 的"无害噪音"。

    实测会遇到这几条（都不影响仿真结果，但会混进终端干扰学生看数据）：
      · 'Unsupported Ngspice version 41'   —— ngspice 版本提示
      · "Node name 'in' is a Python keyword" —— 节点名与 Python 关键字同名
        的提醒（用 'in' 当节点名在 SPICE 里完全合法，实测结果正确）
      · "can't find the initialization file spinit" —— 初始化脚本路径提示
    """
    for name in ('stderr',):
        stream = getattr(sys, name, None)
        if stream is None:
            continue

        class _Filtered:
            _NOISE = (
                'Unsupported Ngspice version',
                'is a Python keyword',
                "can't find the initialization file",
            )

            def __init__(self, wrapped):
                self._w = wrapped

            def write(self, text):
                if any(n in text for n in self._NOISE):
                    return len(text)
                return self._w.write(text)

            def __getattr__(self, item):
                return getattr(self._w, item)

        try:
            setattr(sys, name, _Filtered(stream))
        except Exception:
            pass


def _find_first(paths) -> str | None:
    for p in paths:
        if os.path.isfile(p):
            return p
    return None


def _find_dir(paths) -> str | None:
    for p in paths:
        if os.path.isdir(p):
            return p
    return None


def setup(verbose: bool = True) -> bool:
    """配置 ngspice 共享库路径。返回 True 表示配置成功（不代表 dll 一定能加载）。"""
    _enable_console_utf8()
    _quiet_ngspice_noise()

    # ---- 1. dll 路径 ----
    dll = os.environ.get('NGSPICE_LIBRARY_PATH')
    if dll and os.path.isfile(dll):
        found = dll
    else:
        found = _find_first(_DLL_CANDIDATES)
        if found:
            os.environ['NGSPICE_LIBRARY_PATH'] = found
        elif dll:
            found = dll          # 已设但不存在，交给 PySpice 去报错

    # ---- 2. SPICE_LIB_DIR（必须！绕开 PySpice 的 NoneType bug）----
    if 'SPICE_LIB_DIR' not in os.environ:
        lib_dir = _find_dir(_LIB_DIR_CANDIDATES)
        if lib_dir is None:
            # 退化方案：找 dll 同级或上一级的 share\ngspice
            if found:
                base = os.path.dirname(os.path.dirname(found))   # ...\Spice64
                guess = os.path.join(base, 'share', 'ngspice')
                lib_dir = guess if os.path.isdir(guess) else os.path.dirname(found)
        if lib_dir:
            os.environ['SPICE_LIB_DIR'] = lib_dir

    if verbose:
        print('[环境] NGSPICE_LIBRARY_PATH = %s' % os.environ.get('NGSPICE_LIBRARY_PATH'))
        print('[环境] SPICE_LIB_DIR        = %s' % os.environ.get('SPICE_LIB_DIR'))
        if not os.environ.get('NGSPICE_LIBRARY_PATH'):
            print('[环境] ⚠ 没找到 ngspice.dll。')
            print('       PySpice 需要的是 **dll 共享库**，不是 ngspice.exe。')
            print('       请阅读 02-环境准备与PySpice入门.md 的 2.4.5~2.4.8 节。')
        elif not os.path.isfile(os.environ['NGSPICE_LIBRARY_PATH']):
            print('[环境] ⚠ 指定的 dll 不存在：%s' % os.environ['NGSPICE_LIBRARY_PATH'])

    return bool(found)


def check() -> bool:
    """跑一个最小电路，确认 PySpice 真的能用（返回 True/False）。"""
    try:
        import numpy as np
        from PySpice.Spice.Netlist import Circuit
        # 注意：`from PySpice.Unit import *` 只能写在模块顶层，
        # 不能写在函数里（Python 语法限制）。所以这里用模块方式引用单位。
        import PySpice.Unit as U
    except Exception as exc:
        print('[自检] 导入失败:', exc)
        return False

    try:
        c = Circuit('smoke test')
        c.V('in', 'n1', c.gnd, 5 @ U.u_V)
        c.R(1, 'n1', 'n2', 1 @ U.u_kΩ)
        c.R(2, 'n2', c.gnd, 2 @ U.u_kΩ)
        op = c.simulator(temperature=25, nominal_temperature=25).operating_point()
        # 关键：工作点结果是长度 1 的 WaveForm，必须取标量
        v = float(np.asarray(op['n2']).ravel()[0])
    except Exception as exc:
        print('[自检] 仿真失败：%s: %s' % (type(exc).__name__, exc))
        print('       90% 的情况是 ngspice 共享库没配好，见 02 章 2.4 节。')
        return False

    ok = abs(v - 3.3333333) < 1e-3
    print('[自检] V(n2) = %.6f V  (应为 3.333333)  ->  %s' % (v, '通过' if ok else '数值异常'))
    return ok


if __name__ == '__main__':
    setup()
    check()
