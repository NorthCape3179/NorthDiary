"""Read exactly two playback doubles from a recognized CloudMusic build.

No injection, process writes, heap scanning, account/cache/database access,
network service or third-party runtime. Unknown DLL builds are rejected.
The published module offsets are referenced in docs/LYRICS_MEMORY.md.
"""
import ctypes
from ctypes import wintypes as w
import hashlib
import math
from pathlib import Path
import struct
import sys
import time


# cloudmusic.dll shipped with NetEase 3.1.41.205529 x64, verified locally.
BUILDS = {
    '7f667f876caf94bc3dac3b0070d3e495117005fafdcf18b6aaa51eb004edac8c':
        (41054208, 0x21A74D8, 0x2214778),
}


class ProcessEntry(ctypes.Structure):
    _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('pid', w.DWORD),
                ('heap', ctypes.c_size_t), ('module', w.DWORD), ('threads', w.DWORD),
                ('parent', w.DWORD), ('priority', w.LONG), ('flags', w.DWORD),
                ('name', w.WCHAR * 260)]


class ModuleEntry(ctypes.Structure):
    _fields_ = [('size', w.DWORD), ('module', w.DWORD), ('pid', w.DWORD),
                ('global_usage', w.DWORD), ('process_usage', w.DWORD),
                ('base', ctypes.c_void_p), ('image_size', w.DWORD), ('handle', w.HMODULE),
                ('name', w.WCHAR * 256), ('path', w.WCHAR * 260)]


class NetEaseProgressReader:
    def __init__(self):
        self.candidates = []
        self.active = None
        self.last_discovery = -10.0
        self.fingerprints = {}
        self.track = None
        self.detail = '正在定位网易云播放进度…'
        self.kernel = None
        if sys.platform != 'win32' or ctypes.sizeof(ctypes.c_void_p) != 8:
            self.detail = '此进度适配需要 64 位 Windows'
            return
        k = self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'CreateToolhelp32Snapshot': (w.HANDLE, [w.DWORD, w.DWORD]),
            'Process32FirstW': (w.BOOL, [w.HANDLE, ctypes.POINTER(ProcessEntry)]),
            'Process32NextW': (w.BOOL, [w.HANDLE, ctypes.POINTER(ProcessEntry)]),
            'Module32FirstW': (w.BOOL, [w.HANDLE, ctypes.POINTER(ModuleEntry)]),
            'Module32NextW': (w.BOOL, [w.HANDLE, ctypes.POINTER(ModuleEntry)]),
            'OpenProcess': (w.HANDLE, [w.DWORD, w.BOOL, w.DWORD]),
            'CloseHandle': (w.BOOL, [w.HANDLE]),
            'ReadProcessMemory': (w.BOOL, [w.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                         ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]),
        }
        for name, (result, args) in signatures.items():
            function = getattr(k, name)
            function.restype, function.argtypes = result, args

    def _entries(self, flags, pid, entry_type, first, following):
        handle = self.kernel.CreateToolhelp32Snapshot(flags, pid)
        if not handle or handle == ctypes.c_void_p(-1).value:
            return
        try:
            entry = entry_type()
            entry.size = ctypes.sizeof(entry)
            good = getattr(self.kernel, first)(handle, ctypes.byref(entry))
            while good:
                # Toolhelp overwrites its struct on Next, so copy before yielding.
                yield entry_type.from_buffer_copy(entry)
                good = getattr(self.kernel, following)(handle, ctypes.byref(entry))
        finally:
            self.kernel.CloseHandle(handle)

    def _build(self, module):
        path = Path(module.path)
        try:
            stat = path.stat()
            cache_key = (str(path), stat.st_size, stat.st_mtime_ns)
            if cache_key not in self.fingerprints:
                if not 30_000_000 <= stat.st_size <= 50_000_000:
                    return None
                self.fingerprints[cache_key] = hashlib.sha256(path.read_bytes()).hexdigest()
            build = BUILDS.get(self.fingerprints[cache_key])
            return build if build and module.image_size == build[0] else None
        except OSError:
            return None

    def _discover(self):
        self.close()
        self.last_discovery = time.monotonic()
        found_module = False
        supported = False
        for process in self._entries(0x2, 0, ProcessEntry, 'Process32FirstW', 'Process32NextW'):
            if process.name.casefold() != 'cloudmusic.exe':
                continue
            for module in self._entries(0x18, process.pid, ModuleEntry, 'Module32FirstW', 'Module32NextW'):
                if module.name.casefold() != 'cloudmusic.dll':
                    continue
                found_module = True
                build = self._build(module)
                if not build:
                    break
                supported = True
                # PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ only.
                handle = self.kernel.OpenProcess(0x1010, False, process.pid)
                if handle:
                    self.candidates.append(dict(handle=handle, base=module.base,
                        current_offset=build[1], total_offset=build[2], previous=None))
                break
        if self.candidates:
            self.detail = '正在校验网易云播放进度…'
        elif supported:
            self.detail = '无法读取网易云进度，请让两个软件以相同用户权限运行'
        elif found_module:
            self.detail = '当前网易云版本尚未适配免插件进度'
        else:
            self.detail = '等待网易云播放进程…'

    def _values(self, candidate):
        values = []
        for offset in (candidate['current_offset'], candidate['total_offset']):
            buffer = ctypes.create_string_buffer(8)
            size = ctypes.c_size_t()
            good = self.kernel.ReadProcessMemory(candidate['handle'], candidate['base'] + offset,
                                                  buffer, 8, ctypes.byref(size))
            if not good or size.value != 8:
                return None
            values.append(struct.unpack('<d', buffer.raw)[0])
        position, duration = values
        if not (math.isfinite(position) and math.isfinite(duration)
                and 1 <= duration <= 21600 and 0 <= position <= duration + 1):
            return None
        return min(position, duration), duration

    def read(self, track, playing):
        if not self.kernel:
            return None
        if track != self.track:
            self.track = track
            self.active = None
            for item in self.candidates:
                item['previous'] = None
        now = time.monotonic()
        if not self.candidates and now - self.last_discovery >= 3:
            self._discover()
        if self.active:
            value = self._values(self.active)
            if value:
                return dict(position=value[0], duration=value[1], sampled=now)
            self.close()
            self.last_discovery = -10.0
            self.detail = '正在重新定位网易云进度…'
            return None
        for item in self.candidates:
            value = self._values(item)
            if not value:
                continue
            previous = item['previous']
            item['previous'] = (*value, now)
            if not previous:
                continue
            delta = value[0] - previous[0]
            elapsed = now - previous[2]
            if (abs(value[1] - previous[1]) < .1 and 0 <= delta <= elapsed * 4 + 1
                    and (not playing or delta > .005)):
                self.active = item
                self.detail = ''
                return dict(position=value[0], duration=value[1], sampled=now)
        if self.candidates and now - self.last_discovery > 6:
            self._discover()
        return None

    def close(self):
        if self.kernel:
            for item in self.candidates:
                self.kernel.CloseHandle(item['handle'])
        self.candidates = []
        self.active = None
