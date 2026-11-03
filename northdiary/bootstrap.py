"""Load this interpreter's DLLs before Qt or Python SSL can search system PATH."""
import os
import sys
from pathlib import Path


_handles = []
_configured = False


def configure_runtime():
    global _configured
    if _configured or sys.platform != 'win32':
        return
    # A conda-based venv does not activate conda's Library/bin automatically.
    # Keep DLL-directory handles alive for imports performed later in this process.
    base = Path(sys.base_prefix)
    directories = [base / 'Library' / 'bin', base / 'DLLs']
    # Qt's plugin loader can explicitly search PATH even with DLL handles loaded.
    # Change only this process; launch scripts also do this before Python starts.
    owned = [str(directory) for directory in directories if directory.is_dir()]
    if owned:
        os.environ['PATH'] = os.pathsep.join(owned + [os.environ.get('PATH', '')])
    for directory in directories:
        if directory.is_dir():
            _handles.append(os.add_dll_directory(str(directory)))
    # Explicit full paths also protect legacy loaders which search PATH themselves.
    # Load crypto first, so libssl cannot bind to another application's crypto DLL.
    import ctypes
    for name in ('libcrypto-3-x64.dll', 'libssl-3-x64.dll'):
        library = next((directory / name for directory in directories if (directory / name).is_file()), None)
        if library is not None:
            _handles.append(ctypes.WinDLL(str(library), winmode=0x1100))
    _configured = True
