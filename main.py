#!/usr/bin/env python3
import sys
import os
import subprocess
import importlib
import importlib.util
import warnings
import math

if sys.platform != 'win32':
    os.environ['PYOPENGL_PLATFORM'] = 'osmesa'
    os.environ['PYRENDER_OFFSCREEN'] = '1'

try:
    from check_deps import (
        REQUIRED_MODULES as _REQUIRED_MODULES,
        find_owning_packages as _find_owning_packages,
        deep_check_module as _deep_check_module,
        auto_install_missing_modules as _shared_auto_install_missing_modules,
        check_required_modules as _shared_check_required_modules,
    )
    _HAS_CHECK_DEPS_MODULE = True
except ImportError:
    _HAS_CHECK_DEPS_MODULE = False
    _REQUIRED_MODULES = [
        ("flask",                                  "Flask",                  "Flask",              None),
        ("werkzeug",                                "Werkzeug",               None,                 None),
        ("cryptography.hazmat.primitives.ciphers",  "cryptography",           "Cipher",             None),
        ("numpy",                                   "numpy",                  "array",              None),
        ("PIL.Image",                               "Pillow",                 "open",               None),
        ("trimesh",                                 "trimesh",                "load",               None),
        ("requests",                                "requests",               "get",                None),
        ("packaging.version",                       "packaging",              "parse",              None),
        ("nest_asyncio",                            "nest_asyncio",           "apply",              None),
        ("webview",                                 "pywebview",              "create_window",      None),
        ("smbclient",                               "smbprotocol",            "open_file",          None),
        ("rarfile",                                 "rarfile",                "RarFile",            None),
        ("waitress",                                "waitress",               "serve",              None),
        ("pymeshfix",                               "pymeshfix",              "MeshFix",            None),
        ("defusedxml.ElementTree",                  "defusedxml",             "parse",              None),
        ("paho.mqtt.client",                        "paho-mqtt",              "Client",             None),
        ("rectpack",                                "rectpack",               "newPacker",          None),
        ("shapely.affinity",                        "shapely",                None,                 None),
        ("py7zr",                                   "py7zr",                  "SevenZipFile",       None),
        ("fast_simplification",                     "fast-simplification",    None,                 None),
        ("pyrender",                                "pyrender",               "OffscreenRenderer",  None),
        ("matplotlib",                              "matplotlib",             "use",                None),
        ("psutil",                                  "psutil",                 "virtual_memory",     None),
        ("qrcode",                                  "qrcode",                 "QRCode",             None),
        ("websocket",                               "websocket-client",       "WebSocketApp",       ["websocket", "websocket-client"]),
        ("flashforge",                              "flashforge-python-api",  "FlashForgeClient",   None),
    ]


def _find_owning_packages(top_level_import_name):
    try:
        import importlib.metadata as importlib_metadata
        mapping = importlib_metadata.packages_distributions()
        return list(mapping.get(top_level_import_name, []))
    except Exception:
        return []


def _deep_check_module(import_name, expected_attr):
    try:
        mod = importlib.import_module(import_name)
    except Exception as e:
        return False, f"échec d'import ({e})"
    if expected_attr and not hasattr(mod, expected_attr):
        return False, f"importé mais '{expected_attr}' absent (mauvais paquet installé sous ce nom ?)"
    return True, None


def _auto_install_missing_modules():
    if getattr(sys, 'frozen', False):
        return
    if os.environ.get('STELLIO_NO_AUTO_INSTALL', '').strip().lower() in ('1', 'true', 'yes'):
        print("[MODULES] Vérification/installation automatique désactivée (STELLIO_NO_AUTO_INSTALL=1)")
        return

    print("[MODULES] === Vérification complète (import réel + signature) de tous les modules requis ===")
    problems = []
    for import_name, pip_name, expected_attr, conflicting in _REQUIRED_MODULES:
        ok, reason = _deep_check_module(import_name, expected_attr)
        print(f"[MODULES]   {import_name:<42} -> {'OK' if ok else 'PROBLÈME : ' + reason}")
        if not ok:
            problems.append((import_name, pip_name, expected_attr, conflicting, reason))

    if not problems:
        print("[MODULES] ✅ Tous les modules requis sont présents et fonctionnels")
        return

    print(f"[MODULES] {len(problems)} module(s) manquant(s) ou cassé(s) — correction automatique en cours...")
    still_broken = []
    for import_name, pip_name, expected_attr, conflicting, reason in problems:
        top_level = import_name.split('.')[0]

        wrong_module_installed = "attribut" in reason
        bad_packages = set(conflicting or [])
        if wrong_module_installed:
            bad_packages.update(_find_owning_packages(top_level))
        bad_packages.discard(pip_name)

        for bad_pkg in bad_packages:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'uninstall', '-y', bad_pkg],
                capture_output=True, timeout=120
            )

        force_reinstall = bool(bad_packages) or wrong_module_installed
        base_cmd = [sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-input']
        base_cmd += ['--force-reinstall'] if force_reinstall else ['--upgrade']
        base_cmd += [pip_name]

        installed_ok = False
        for extra_args in ([], ['--break-system-packages']):
            try:
                subprocess.run(base_cmd + extra_args, check=True, timeout=900)
                installed_ok = True
                break
            except Exception:
                continue

        if not installed_ok:
            still_broken.append((import_name, pip_name, "échec de la commande pip install"))
            continue

        importlib.invalidate_caches()
        top_level = import_name.split('.')[0]
        for mod_name in list(sys.modules):
            if mod_name == top_level or mod_name.startswith(top_level + '.'):
                del sys.modules[mod_name]

        ok, reason = _deep_check_module(import_name, expected_attr)
        if ok:
            print(f"[MODULES] ✅ {pip_name} corrigé")
        else:
            still_broken.append((import_name, pip_name, reason))

    if still_broken:
        print("[MODULES] ❌ Modules toujours en échec après tentative de correction automatique :")
        for import_name, pip_name, reason in still_broken:
            print(f"[MODULES]     - {import_name} ({pip_name}) : {reason}")
        print("[MODULES] Stellio ne peut pas démarrer de façon fiable sans ces modules. Arrêt.")
        sys.exit(1)

    print("[MODULES] ✅ Tous les modules corrigés avec succès")


def _run_startup_module_check():
    if getattr(sys, 'frozen', False):
        return
    if os.environ.get('STELLIO_NO_AUTO_INSTALL', '').strip().lower() in ('1', 'true', 'yes'):
        print("[MODULES] Vérification/installation automatique désactivée (STELLIO_NO_AUTO_INSTALL=1)")
        return

    if _HAS_CHECK_DEPS_MODULE:
        all_ok, still_broken = _shared_auto_install_missing_modules(modules=_REQUIRED_MODULES)
        if not all_ok:
            print("[MODULES] Stellio ne peut pas démarrer de façon fiable sans ces modules. Arrêt.")
            sys.exit(1)
        return

    _auto_install_missing_modules()


_run_startup_module_check()

import nest_asyncio
nest_asyncio.apply()
import uuid
import socket
import asyncio
import sqlite3
import hashlib
import json
import ssl
import struct
import subprocess
import shlex
import secrets
import datetime
import logging
from logging.handlers import RotatingFileHandler
import trimesh
try:
    import pymeshfix
    HAS_PYMESHFIX = True
except ImportError:
    HAS_PYMESHFIX = False
import numpy as np
import smbclient
from PIL import Image, ImageDraw
import base64
from pathlib import Path
from functools import wraps
from flask import Flask, request, jsonify, session, send_file, Response
from werkzeug.utils import secure_filename
import trimesh.transformations as tra
import io
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import zipfile
import rarfile
import tarfile
import shutil
try:
    from defusedxml.ElementTree import parse as _safe_xml_parse
except ImportError:
    from xml.etree.ElementTree import parse as _safe_xml_parse
    print("[SECURITE] ⚠️  defusedxml non installé — parsing XML des .3mf non protégé contre XXE. Ajouter 'defusedxml' à requirements.txt")
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, wait as futures_wait, FIRST_COMPLETED
import queue
import collections
import requests
import re
import difflib
from urllib.parse import urlparse, unquote
import threading
import glob
import atexit
import platform
import multiprocessing as mp


thumb_generation_queue = queue.Queue()
metadata_generation_queue = queue.Queue()
currently_downloading_paths = set()
is_generation_running = False
ignored_files_cache = {}
IGNORED_FILE_COOLDOWN_S = 600

_thumb_inflight_lock = threading.Lock()
_thumb_inflight_paths = set()


def _queue_thumb_task(path, thumb_path, priority='low'):
    normalized = path.replace('\\', '/')
    with _thumb_inflight_lock:
        if normalized in _thumb_inflight_paths:
            return False
        _thumb_inflight_paths.add(normalized)
    thumb_generation_queue.put({'path': path, 'thumb_path': thumb_path, 'priority': priority})
    return True


def _release_thumb_inflight(path):
    normalized = path.replace('\\', '/')
    with _thumb_inflight_lock:
        _thumb_inflight_paths.discard(normalized)

def _is_ignored_recently(path):
    ts = ignored_files_cache.get(path)
    if ts is None:
        return False
    return (time.time() - ts) < IGNORED_FILE_COOLDOWN_S

def _mark_ignored(path):
    ignored_files_cache[path] = time.time()

scan_lock = threading.Lock()
matplotlib_render_lock = threading.Lock()

def _load_repair_ignored():
    try:
        if os.path.exists(REPAIR_IGNORE_FILE):
            with open(REPAIR_IGNORE_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()

def _save_repair_ignored():
    try:
        tmp_path = REPAIR_IGNORE_FILE + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(sorted(repair_ignored_cache), f, ensure_ascii=False)
        _atomic_replace(tmp_path, REPAIR_IGNORE_FILE)
    except Exception:
        pass

def mark_repair_attempted(file_path):
    normalized = file_path.replace('\\', '/')
    repair_ignored_cache.add(normalized)
    _save_repair_ignored()

pyrender_lock = threading.Lock()
_persistent_renderer = None
_persistent_renderer_size = None

def _release_persistent_renderer():
    global _persistent_renderer, _persistent_renderer_size
    with pyrender_lock:
        if _persistent_renderer is not None:
            try:
                _persistent_renderer.delete()
            except Exception:
                pass
            _persistent_renderer = None
            _persistent_renderer_size = None
NUM_THUMB_WORKERS = max(2, min(6, (os.cpu_count() or 4) - 1))
THUMB_GENERATION_TIMEOUT = 90
THUMB_GENERATION_TIMEOUT_PER_MB = 5
THUMB_GENERATION_TIMEOUT_MAX = 600
thumb_failure_notifications = queue.Queue()

_thumb_session_lock = threading.Lock()
_thumb_session_active = False
_thumb_session_generated = 0
_thumb_session_failed = []
_thumb_session_total_at_start = 0
_thumb_pending_summary = None
_thumb_reconciled_this_run = False


def _thumb_session_note_start(extra_count):
    global _thumb_session_active, _thumb_session_generated, _thumb_session_failed, _thumb_session_total_at_start
    with _thumb_session_lock:
        if not _thumb_session_active:
            _thumb_session_active = True
            _thumb_session_generated = 0
            _thumb_session_failed = []
            _thumb_session_total_at_start = extra_count
        else:
            _thumb_session_total_at_start = max(_thumb_session_total_at_start, extra_count)
    _prevent_system_sleep(True)


def _thumb_session_note_result(name, path, ok, reason=None):
    global _thumb_session_generated
    with _thumb_session_lock:
        _thumb_session_generated += 1
        if not ok:
            _thumb_session_failed.append({'name': name, 'path': path, 'reason': reason or 'error'})


def _thumb_session_maybe_finish():
    global _thumb_session_active, _thumb_pending_summary
    finished = False
    with _thumb_session_lock:
        if _thumb_session_active and thumb_generation_queue.empty():
            _thumb_pending_summary = {
                'total': _thumb_session_total_at_start,
                'generated': _thumb_session_generated,
                'failed': list(_thumb_session_failed),
            }
            _thumb_session_active = False
            finished = True
    if finished:
        _prevent_system_sleep(False)


def get_thumb_timeout(file_path):
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        return THUMB_GENERATION_TIMEOUT
    timeout = THUMB_GENERATION_TIMEOUT + size_mb * THUMB_GENERATION_TIMEOUT_PER_MB


    if file_path.lower().endswith('.3mf'):
        timeout *= 1.6
    return min(timeout, THUMB_GENERATION_TIMEOUT_MAX)


def _lower_thread_priority():
    try:
        if sys.platform == 'win32':
            import ctypes
            THREAD_PRIORITY_BELOW_NORMAL = -1
            handle = ctypes.windll.kernel32.GetCurrentThread()
            ctypes.windll.kernel32.SetThreadPriority(handle, THREAD_PRIORITY_BELOW_NORMAL)
        else:
            tid = threading.get_native_id()
            os.setpriority(os.PRIO_PROCESS, tid, 5)
    except Exception:
        pass


_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
_sleep_prevention_lock = threading.Lock()
_sleep_prevention_active = False


def _prevent_system_sleep(enable):
    global _sleep_prevention_active
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        with _sleep_prevention_lock:
            if enable and not _sleep_prevention_active:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED
                )
                _sleep_prevention_active = True
                app_logger.info("[POWER] Veille système inhibée (génération de miniatures en cours)")
            elif not enable and _sleep_prevention_active:
                ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
                _sleep_prevention_active = False
                app_logger.info("[POWER] Veille système ré-autorisée (génération terminée)")
    except Exception as e:
        app_logger.warning(f"[POWER] Impossible de gérer l'état de veille: {e}")


def get_base_path():
    return os.path.dirname(os.path.abspath(__file__))

def get_data_path():
    env_override = os.environ.get('STELLIO_DATA_DIR')
    if env_override:
        data_dir = Path(env_override)
    elif os.name == 'nt':
        appdata = os.environ.get('APPDATA', str(Path.home() / 'AppData' / 'Roaming'))
        data_dir = Path(appdata) / 'Stellio'
    else:
        data_dir = Path.home() / '.stellio'
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir)

BASE_DIR = get_base_path()
DATA_DIR = get_data_path()

_ALL_SOURCE_TYPES = {'folder', 'file', 'smb', 'nfs'}
_env_allowed = os.environ.get('STELLIO_ALLOWED_SOURCE_TYPES', '').strip()
if _env_allowed:
    ALLOWED_SOURCE_TYPES = {t.strip().lower() for t in _env_allowed.split(',') if t.strip().lower() in _ALL_SOURCE_TYPES}
    if not ALLOWED_SOURCE_TYPES:
        ALLOWED_SOURCE_TYPES = set(_ALL_SOURCE_TYPES)
else:
    ALLOWED_SOURCE_TYPES = set(_ALL_SOURCE_TYPES)
DB_PATH = os.path.join(DATA_DIR, "stellio.db")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
THUMBNAILS_DIR = os.path.join(DATA_DIR, "thumbnails")
PRINT_PHOTOS_DIR = os.path.join(DATA_DIR, "print_photos")
os.makedirs(PRINT_PHOTOS_DIR, exist_ok=True)
SOSPRINT_CONV_PHOTOS_DIR = os.path.join(DATA_DIR, "sosprint_conversation_photos")
os.makedirs(SOSPRINT_CONV_PHOTOS_DIR, exist_ok=True)


IMPORTED_PROFILES_DIR = os.path.join(DATA_DIR, "imported_slicer_profiles")
os.makedirs(IMPORTED_PROFILES_DIR, exist_ok=True)
CACHE_FILE = os.path.join(DATA_DIR, "file_cache.json")
CACHE_DURATION = 18000
CACHE_SCHEMA_VERSION = 2
REPAIR_IGNORE_FILE = os.path.join(DATA_DIR, "repair_ignored.json")
repair_ignored_cache = _load_repair_ignored()

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)


KEY_FILE = os.path.join(DATA_DIR, 'encryption.key')
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'rb') as f:
        ENCRYPTION_KEY = f.read()
    with open(KEY_FILE.replace('.key', '.iv'), 'rb') as f:
        IV = f.read()
else:
    ENCRYPTION_KEY = os.urandom(32)
    IV = os.urandom(16)
    with open(KEY_FILE, 'wb') as f:
        f.write(ENCRYPTION_KEY)
    with open(KEY_FILE.replace('.key', '.iv'), 'wb') as f:
        f.write(IV)
    os.chmod(KEY_FILE, 0o600)
    os.chmod(KEY_FILE.replace('.key', '.iv'), 0o600)


LOG_FILE = os.path.join(DATA_DIR, "stellio.log")
LOG_MAX_SIZE = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


DEBUG_FLAG_FILE = os.path.join(DATA_DIR, ".debug_session_pending")

DEBUG_SESSION_ACTIVE = False

def setup_logging():
    global DEBUG_SESSION_ACTIVE
    try:
        if os.path.exists(LOG_FILE):
            open(LOG_FILE, 'w').close()
    except Exception:
        pass

    debug_requested = os.path.exists(DEBUG_FLAG_FILE)
    if debug_requested:
        try:
            os.remove(DEBUG_FLAG_FILE)
        except Exception:
            pass
    DEBUG_SESSION_ACTIVE = debug_requested


    level = logging.DEBUG if debug_requested else logging.WARNING

    logger = logging.getLogger('stellio')
    logger.setLevel(level)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_stream = sys.stderr if sys.stderr is not None else sys.stdout
    if console_stream is not None:
        try:
            if hasattr(console_stream, 'reconfigure'):
                console_stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
        console_handler = logging.StreamHandler(console_stream)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    werkzeug_log = logging.getLogger('werkzeug')
    werkzeug_log.setLevel(logging.DEBUG if debug_requested else logging.ERROR)

    if debug_requested:
        logger.warning("🐞 [DEBUG] Session de debug active pour ce démarrage — logs au maximum. "
                        "Redémarrez à nouveau l'app pour revenir au mode normal.")

    return logger

app_logger = setup_logging()


def _check_required_modules(log=True):
    try:
        import importlib.metadata as importlib_metadata
    except ImportError:
        importlib_metadata = None

    results = []
    for import_name, pip_name, expected_attr, _conflicting in _REQUIRED_MODULES:
        ok, reason = _deep_check_module(import_name, expected_attr)

        version_str = None
        if ok and importlib_metadata is not None:
            try:
                version_str = importlib_metadata.version(pip_name)
            except Exception:
                version_str = "?"

        results.append({
            "import": import_name,
            "pip": pip_name,
            "installed": ok,
            "reason": reason,
            "version": version_str,
        })

    if log:
        try:
            broken = [r for r in results if not r["installed"]]

            app_logger.info("[MODULES] === Vérification complète des modules Python ===")
            for r in results:
                if r["installed"]:
                    status = f"OK (v{r['version']})" if r["version"] not in (None, "?") else "OK"
                else:
                    status = f"PROBLÈME ({r['reason']})"
                app_logger.info(f"[MODULES]   {r['import']:<42} -> {status}")

            if broken:
                names = ", ".join(r["pip"] for r in broken)
                app_logger.error(f"[MODULES] ❌ Modules en échec: {names}")
            else:
                app_logger.info("[MODULES] ✅ Tous les modules requis sont présents et fonctionnels")
            app_logger.info("[MODULES] === Fin de la vérification ===")
        except Exception as e:
            app_logger.error(f"[MODULES] Erreur lors du rapport de vérification: {e}")

    return results

_check_required_modules()


def formatSize(bytes):
    if not bytes:
        return '0 B'
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024 * 1024:
        return f"{bytes / 1024:.1f} KB"
    else:
        return f"{bytes / (1024 * 1024):.1f} MB"


def _setup_rar_tool():
    base_dir = get_base_path()
    exe_name = 'UnRAR.exe' if sys.platform == 'win32' else 'unrar'

    unrar_paths = [
        os.path.join(base_dir, 'bin', exe_name),
        os.path.join(base_dir, 'tools', exe_name),
        os.path.join(base_dir, exe_name)
    ]
    for path in unrar_paths:
        if os.path.exists(path):
            rarfile.UNRAR_TOOL = path
            app_logger.info(f"[RAR] UnRAR configuré: {path}")
            return True

    if sys.platform != 'win32':
        system_unrar = shutil.which('unrar')
        if system_unrar:
            rarfile.UNRAR_TOOL = system_unrar
            app_logger.info(f"[RAR] UnRAR configuré (PATH système): {system_unrar}")
            return True

    app_logger.info("[RAR] UnRAR non trouvé. L'extraction .rar sera désactivée.")
    return False

_setup_rar_tool()


FFMPEG_TOOL = None

def _setup_ffmpeg_tool():
    global FFMPEG_TOOL
    base_dir = get_base_path()
    exe_name = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
    ffmpeg_paths = [
        os.path.join(base_dir, 'bin', exe_name),
        os.path.join(base_dir, 'tools', exe_name),
        os.path.join(base_dir, exe_name),
    ]
    for path in ffmpeg_paths:
        if os.path.exists(path):
            FFMPEG_TOOL = path
            app_logger.info(f"[FFmpeg] Configuré (bin local): {path}")
            return True

    system_ffmpeg = shutil.which('ffmpeg')
    if system_ffmpeg:
        FFMPEG_TOOL = system_ffmpeg
        app_logger.info(f"[FFmpeg] Configuré (PATH système): {system_ffmpeg}")
        return True


    try:
        bin_dir = os.path.join(base_dir, 'bin')
        archive_hint = next(
            (f for f in os.listdir(bin_dir)
             if f.lower().startswith('ffmpeg') and f.lower().endswith(('.zip', '.7z', '.tar.gz', '.tar.xz'))),
            None
        ) if os.path.isdir(bin_dir) else None
    except Exception:
        archive_hint = None

    if archive_hint:
        app_logger.warning(
            f"[FFmpeg] Archive '{archive_hint}' détectée dans bin/ mais non extraite — "
            f"extrayez {exe_name} (build 'full'/'essentials' statique recommandé, "
            f"sinon les .dll du build 'shared' doivent aussi être copiées à côté) "
            f"directement dans bin/, à côté de UnRAR.exe. Flux caméra RTSPS (X1/X2/H2) indisponible en attendant."
        )
    else:
        app_logger.info("[FFmpeg] ffmpeg introuvable (ni bin/, ni PATH). Flux caméra RTSPS (X1/X2/H2) indisponible.")
    return False

_setup_ffmpeg_tool()


SETTINGS_FILE = os.path.join(DATA_DIR, "app_settings.json")
_settings_cache = {}

def load_settings():
    global _settings_cache
    if not _settings_cache:
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                _settings_cache = json.load(f)
        except:
            _settings_cache = {"theme": "dark", "fabricant": "stellio"}
    return _settings_cache

def save_settings(settings):
    global _settings_cache
    _settings_cache = settings
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


_STARTUP_REGISTRY_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_STARTUP_REGISTRY_VALUE_NAME = "Stellio"
_STARTUP_MINIMIZED_FLAG = "--minimized"

def _get_startup_launch_command(minimized=False):
    launcher_exe = os.environ.get('STELLIO_LAUNCHER_EXE')
    base = None
    if launcher_exe and os.path.exists(launcher_exe):
        base = f'"{launcher_exe}"'
    elif getattr(sys, 'frozen', False) and os.path.exists(sys.executable):
        base = f'"{sys.executable}"'
    if not base:
        return None
    return f'{base} {_STARTUP_MINIMIZED_FLAG}' if minimized else base

def _read_startup_registry_command():
    if sys.platform != 'win32':
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_REGISTRY_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, _STARTUP_REGISTRY_VALUE_NAME)
            return value or None
    except (OSError, ImportError):
        return None
    except Exception as e:
        app_logger.warning(f"[Startup] Lecture du registre échouée: {e}")
        return None

def is_startup_enabled():
    return bool(_read_startup_registry_command())

def is_startup_minimized():
    command = _read_startup_registry_command()
    return bool(command) and _STARTUP_MINIMIZED_FLAG in command

def set_startup_enabled(enabled, minimized=False):
    if sys.platform != 'win32':
        raise RuntimeError("Le démarrage automatique n'est disponible que sur Windows")
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_REGISTRY_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                command = _get_startup_launch_command(minimized=minimized)
                if not command:
                    raise RuntimeError("Impossible de déterminer le chemin de l'exécutable Stellio (build non figé ?)")
                winreg.SetValueEx(key, _STARTUP_REGISTRY_VALUE_NAME, 0, winreg.REG_SZ, command)
                mode = "réduit" if minimized else "fenêtre normale"
                app_logger.info(f"[Startup] Démarrage automatique activé ({mode}): {command}")
            else:
                try:
                    winreg.DeleteValue(key, _STARTUP_REGISTRY_VALUE_NAME)
                    app_logger.info("[Startup] Démarrage automatique désactivé")
                except FileNotFoundError:
                    pass
    except Exception as e:
        app_logger.error(f"[Startup] Erreur lors de la mise à jour du registre: {e}")
        raise


_cache_saved = False

def save_cache_on_exit():
    global _cache_saved
    if _cache_saved:
        return
    _cache_saved = True
    app_logger.info("[CACHE] 💾 Sauvegarde de fermeture...")
    try:
        flush_pending_thumb_updates()
    except Exception as e:
        app_logger.info(f"[CACHE] Erreur flush miniatures à la fermeture: {e}")
    try:
        with cache_file_lock:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                cache['timestamp'] = time.time()
                tmp_path = CACHE_FILE + '.tmp'
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, ensure_ascii=False, separators=(',', ':'))
                _atomic_replace(tmp_path, CACHE_FILE)
                app_logger.info("[CACHE] ✅ Cache sauvegardé avec succès")
    except Exception as e:
        app_logger.info(f"[CACHE] ❌ Erreur sauvegarde: {e}")

atexit.register(save_cache_on_exit)


_share_lock = threading.Lock()
_share_links = {}
SHARE_LINK_MAX_AGE = 24 * 3600


def _cleanup_expired_shares():
    now = time.time()
    with _share_lock:
        expired = [t for t, info in _share_links.items() if now - info['created'] > SHARE_LINK_MAX_AGE]
        for t in expired:
            _share_links.pop(t, None)


def encrypt_password(password):
    try:
        if not password:
            return None
        iv = os.urandom(16)
        padding_length = 16 - (len(password) % 16)
        padded_password = password.encode('utf-8') + bytes([padding_length] * padding_length)
        cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_password) + encryptor.finalize()
        return f"{iv.hex()}:{encrypted.hex()}"
    except Exception as e:
        app_logger.error(f"Erreur encrypt_password: {e}")
        return None

def decrypt_password(encrypted_data):
    try:
        if not encrypted_data:
            return None
        iv = IV
        if isinstance(encrypted_data, str):
            if ':' in encrypted_data:
                iv_hex, _, data_hex = encrypted_data.partition(':')
                try:
                    iv = bytes.fromhex(iv_hex)
                    encrypted_bytes = bytes.fromhex(data_hex)
                except ValueError:
                    iv = IV
                    encrypted_bytes = encrypted_data.encode('latin-1')
            else:
                try:
                    encrypted_bytes = bytes.fromhex(encrypted_data)
                except ValueError:
                    encrypted_bytes = encrypted_data.encode('latin-1')
        else:
            encrypted_bytes = encrypted_data

        cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted_bytes) + decryptor.finalize()

        if len(decrypted) > 0:
            padding_length = decrypted[-1]
            if 0 < padding_length <= 16:
                if all(b == padding_length for b in decrypted[-padding_length:]):
                    decrypted = decrypted[:-padding_length]
            try:
                return decrypted.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return decrypted.decode('latin-1')
                except:
                    return decrypted.hex()
        else:
            return None
    except Exception as e:
        app_logger.error(f"❌ Erreur decrypt_password: {e}")
        return None

_ENC_FORMAT_RE = re.compile(r'^[0-9a-f]{32}:[0-9a-f]+$')

def _is_encrypted_format(value):
    return bool(value) and bool(_ENC_FORMAT_RE.match(value))

def decrypt_account_secret(value):
    if not value:
        return value
    if _is_encrypted_format(value):
        decrypted = decrypt_password(value)
        return decrypted if decrypted is not None else value
    return value

def _safe_int(raw, default=None):
    if raw is None or raw == '' or raw == 'null':
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default

def migrate_account_passwords_to_random_iv():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, password_encrypted, api_key, session_cookies FROM account_credentials"
        ).fetchall()
        migrated = 0
        for row in rows:
            row_id = row['id']
            updates = {}

            enc = row['password_encrypted']
            if enc and ':' not in enc:
                plain = decrypt_password(enc)
                if plain is not None:
                    new_enc = encrypt_password(plain)
                    if new_enc:
                        updates['password_encrypted'] = new_enc
                else:
                    app_logger.warning(f"[MIGRATION] Mot de passe illisible pour account_credentials.id={row_id}, laissé tel quel")

            for col in ('api_key', 'session_cookies'):
                val = row[col]
                if val and not _is_encrypted_format(val):
                    new_val = encrypt_password(val)
                    if new_val:
                        updates[col] = new_val

            if updates:
                set_clause = ", ".join(f"{c} = ?" for c in updates)
                conn.execute(f"UPDATE account_credentials SET {set_clause} WHERE id = ?", (*updates.values(), row_id))
                migrated += 1
        if migrated:
            conn.commit()
            app_logger.info(f"[MIGRATION] {migrated} enregistrement(s) de compte(s) tiers migré(s) (IV aléatoire / chiffrement api_key & cookies)")
    except Exception as e:
        app_logger.error(f"[MIGRATION] Erreur migrate_account_passwords_to_random_iv: {e}")
        conn.rollback()
    finally:
        conn.close()

def migrate_printer_api_keys():
    conn = get_db()
    try:
        rows = conn.execute("SELECT id, api_key FROM printers WHERE api_key IS NOT NULL AND api_key != ''").fetchall()
        migrated = 0
        for row in rows:
            if _is_encrypted_format(row['api_key']):
                continue
            new_val = encrypt_password(row['api_key'])
            if new_val:
                conn.execute("UPDATE printers SET api_key = ? WHERE id = ?", (new_val, row['id']))
                migrated += 1
        if migrated:
            conn.commit()
            app_logger.info(f"[MIGRATION] {migrated} clé(s) API d'imprimante chiffrée(s)")
    except Exception as e:
        app_logger.error(f"[MIGRATION] Erreur migrate_printer_api_keys: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("PRAGMA busy_timeout = 20000")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA synchronous=NORMAL;")
    c.execute("PRAGMA cache_size=-2000;")
    c.execute("PRAGMA temp_store=MEMORY;")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT DEFAULT '',
        reset_code TEXT,
        reset_expiry TIMESTAMP,
        role TEXT DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        path TEXT NOT NULL,
        config TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, name)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS slicer_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        color TEXT DEFAULT '#4ea1d3'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS file_tags (
        file_path TEXT NOT NULL,
        tag_id INTEGER NOT NULL,
        FOREIGN KEY (tag_id) REFERENCES tags(id),
        PRIMARY KEY (file_path, tag_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS account_credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        platform TEXT NOT NULL,
        email TEXT,
        password_encrypted TEXT,
        api_key TEXT,
        session_cookies TEXT,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, platform)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS favorites (
        file_path TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS remote_instances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        peer_key TEXT NOT NULL,
        inbox_folder TEXT,
        last_status TEXT,
        last_seen_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS printers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        ip TEXT NOT NULL,
        api_key TEXT,
        config TEXT,
        is_connected BOOLEAN DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS download_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        file_ext TEXT DEFAULT '',
        source_url TEXT DEFAULT '',
        platform TEXT DEFAULT '',
        downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS print_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        file_ext TEXT DEFAULT '',
        slicer TEXT DEFAULT '',
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS file_descriptions (
        file_path TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        description TEXT DEFAULT '',
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        PRIMARY KEY (file_path, user_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS print_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        image_filename TEXT NOT NULL,
        note TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        color TEXT DEFAULT '#4ea1d3',
        status TEXT DEFAULT 'in_progress',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS project_files (
        project_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        quantity_needed INTEGER DEFAULT 1,
        quantity_printed INTEGER DEFAULT 0,
        notes TEXT DEFAULT '',
        position INTEGER DEFAULT 0,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id),
        PRIMARY KEY (project_id, file_path)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS spool_assignments (
        file_path TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        spoolman_url TEXT NOT NULL,
        spool_id INTEGER NOT NULL,
        spool_name TEXT DEFAULT '',
        spool_material TEXT DEFAULT '',
        spool_color_hex TEXT DEFAULT '',
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        PRIMARY KEY (file_path, user_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS filament_assignments (
        file_path TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        source_type TEXT NOT NULL DEFAULT 'spoolman',
        source_id TEXT NOT NULL,
        source_label TEXT DEFAULT '',
        material TEXT DEFAULT '',
        color_hex TEXT DEFAULT '',
        spoolman_url TEXT DEFAULT '',
        printer_id INTEGER,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        PRIMARY KEY (file_path, user_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS manual_filament_spools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        material TEXT DEFAULT '',
        color_hex TEXT DEFAULT '#888888',
        remaining_g REAL,
        capacity_g REAL DEFAULT 1000,
        source_label TEXT DEFAULT 'Manuel',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sos_print_diagnostics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        printer_id INTEGER,
        material TEXT DEFAULT '',
        description TEXT NOT NULL,
        causes TEXT,
        had_photo BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (printer_id) REFERENCES printers(id)
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sos_diag_user_printer ON sos_print_diagnostics(user_id, printer_id, created_at)")

    c.execute("""CREATE TABLE IF NOT EXISTS sos_print_conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        printer_id INTEGER,
        material TEXT DEFAULT '',
        description TEXT NOT NULL,
        title TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'open',
        candidate_causes TEXT DEFAULT '[]',
        eliminated_causes TEXT DEFAULT '[]',
        last_causes TEXT DEFAULT '[]',
        resolution_note TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (printer_id) REFERENCES printers(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sos_print_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT DEFAULT '',
        image_filename TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES sos_print_conversations(id)
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sos_conv_user_status ON sos_print_conversations(user_id, status, updated_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sos_msg_conv ON sos_print_messages(conversation_id, created_at)")
    conn.commit()

    try:
        c.execute("""
            INSERT INTO filament_assignments (file_path, user_id, source_type, source_id, source_label, material, color_hex, spoolman_url)
            SELECT sa.file_path, sa.user_id, 'spoolman', CAST(sa.spool_id AS TEXT), sa.spool_name, sa.spool_material, sa.spool_color_hex, sa.spoolman_url
            FROM spool_assignments sa
            WHERE NOT EXISTS (
                SELECT 1 FROM filament_assignments fa
                WHERE fa.file_path = sa.file_path AND fa.user_id = sa.user_id
            )
        """)
        conn.commit()
    except Exception as e:
        app_logger.info(f"[FilamentBridge] Migration spool_assignments ignorée: {e}")
    conn.close()
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("PRAGMA table_info(account_credentials)")
        columns = [col[1] for col in c.fetchall()]
        new_cols = {
            'api_key': 'ALTER TABLE account_credentials ADD COLUMN api_key TEXT',
        }
        for col_name, sql in new_cols.items():
            if col_name not in columns:
                try:
                    c.execute(sql)
                except sqlite3.OperationalError:
                    pass

        if 'email' not in columns and 'username' in columns:
            try:
                c.execute("ALTER TABLE account_credentials ADD COLUMN email TEXT")
            except sqlite3.OperationalError:
                pass
            c.execute("UPDATE account_credentials SET email = username WHERE email IS NULL")
        conn.commit()
    except Exception as e:
        app_logger.info(f"[ERROR] Migration: {e}")
        conn.rollback()
    finally:
        conn.close()

def migrate_print_history():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("PRAGMA table_info(print_history)")
        columns = [col[1] for col in c.fetchall()]
        if 'source_platform' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN source_platform TEXT DEFAULT ''")
        if 'spool_id' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN spool_id INTEGER")
        if 'spool_weight_used_g' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN spool_weight_used_g REAL")
        if 'result' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN result TEXT DEFAULT ''")
        if 'failure_reason' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN failure_reason TEXT DEFAULT ''")
        if 'rating_notes' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN rating_notes TEXT DEFAULT ''")
        if 'slicer_profile_id' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN slicer_profile_id TEXT DEFAULT ''")
        if 'slicer_profile_name' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN slicer_profile_name TEXT DEFAULT ''")
        if 'rated_at' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN rated_at TIMESTAMP")
        if 'material_cost' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN material_cost REAL")
        if 'elec_cost' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN elec_cost REAL")
        if 'total_cost' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN total_cost REAL")
        if 'printer_id' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN printer_id INTEGER")
        if 'estimated_seconds' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN estimated_seconds REAL")
        if 'actual_seconds' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN actual_seconds REAL")
        if 'time_recorded_at' not in columns:
            c.execute("ALTER TABLE print_history ADD COLUMN time_recorded_at TIMESTAMP")
        conn.commit()
    except Exception as e:
        app_logger.info(f"[ERROR] migrate_print_history: {e}")
    finally:
        conn.close()

def migrate_printer_maintenance():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("PRAGMA table_info(printers)")
        columns = [col[1] for col in c.fetchall()]
        if 'total_print_hours' not in columns:
            c.execute("ALTER TABLE printers ADD COLUMN total_print_hours REAL DEFAULT 0")
        if 'last_status_poll_at' not in columns:
            c.execute("ALTER TABLE printers ADD COLUMN last_status_poll_at TIMESTAMP")
        if 'brand' not in columns:
            c.execute("ALTER TABLE printers ADD COLUMN brand TEXT DEFAULT ''")
        if 'power_w' not in columns:
            c.execute("ALTER TABLE printers ADD COLUMN power_w INTEGER DEFAULT 120")

        c.execute("""CREATE TABLE IF NOT EXISTS printer_maintenance_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            printer_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            interval_hours REAL,
            interval_days REAL,
            hours_at_last_reset REAL DEFAULT 0,
            last_reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (printer_id) REFERENCES printers(id)
        )""")
        conn.commit()
    except Exception as e:
        app_logger.info(f"[ERROR] migrate_printer_maintenance: {e}")
    finally:
        conn.close()

init_db()
migrate_account_passwords_to_random_iv()
migrate_printer_api_keys()
def migrate_print_photos():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("PRAGMA table_info(print_photos)")
        columns = [col[1] for col in c.fetchall()]
        if 'result' not in columns:
            c.execute("ALTER TABLE print_photos ADD COLUMN result TEXT DEFAULT 'success'")
        conn.commit()
    except Exception as e:
        app_logger.info(f"[ERROR] migrate_print_photos: {e}")
    finally:
        conn.close()

def migrate_manual_filament_spools():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("PRAGMA table_info(manual_filament_spools)")
        columns = [col[1] for col in c.fetchall()]
        if 'vendor' not in columns:
            c.execute("ALTER TABLE manual_filament_spools ADD COLUMN vendor TEXT DEFAULT ''")
        if 'price' not in columns:
            c.execute("ALTER TABLE manual_filament_spools ADD COLUMN price REAL")
        if 'diameter_mm' not in columns:
            c.execute("ALTER TABLE manual_filament_spools ADD COLUMN diameter_mm REAL DEFAULT 1.75")
        if 'notes' not in columns:
            c.execute("ALTER TABLE manual_filament_spools ADD COLUMN notes TEXT DEFAULT ''")
        if 'storage_location' not in columns:
            c.execute("ALTER TABLE manual_filament_spools ADD COLUMN storage_location TEXT DEFAULT ''")
        if 'archived' not in columns:
            c.execute("ALTER TABLE manual_filament_spools ADD COLUMN archived BOOLEAN DEFAULT 0")
        if 'updated_at' not in columns:
            c.execute("ALTER TABLE manual_filament_spools ADD COLUMN updated_at TIMESTAMP")
        conn.commit()
    except Exception as e:
        app_logger.info(f"[ERROR] migrate_manual_filament_spools: {e}")
    finally:
        conn.close()

migrate_print_history()
migrate_printer_maintenance()
migrate_manual_filament_spools()
migrate_print_photos()

def migrate_users_recovery_code():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in c.fetchall()]
        if 'recovery_code_hash' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN recovery_code_hash TEXT")
        if 'security_question_key' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN security_question_key TEXT")
        if 'security_question_custom' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN security_question_custom TEXT")
        if 'security_answer_hash' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN security_answer_hash TEXT")
        conn.commit()
    except Exception as e:
        app_logger.info(f"[ERROR] migrate_users_recovery_code: {e}")
    finally:
        conn.close()

migrate_users_recovery_code()


try:
    import paho.mqtt.client as mqtt
    import ssl
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False
    app_logger.info("[WARN] paho-mqtt non installé. BambuLab ne fonctionnera pas.")

try:
    import websocket as ws_client
    app_logger.info(
        f"[WEBSOCKET] Module chargé depuis : {getattr(ws_client, '__file__', '???')} "
        f"— WebSocketApp présent : {hasattr(ws_client, 'WebSocketApp')}"
    )
    if not hasattr(ws_client, 'WebSocketApp'):
        raise ImportError("mauvais paquet 'websocket' installé")
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False
    app_logger.info(
        "[WARN] Le module websocket-client est absent ou remplacé par le "
        "paquet 'websocket' (différent, obsolète, sans rapport). "
        "Elegoo (résine/Centauri Carbon 1) et Creality ne fonctionneront pas. "
        "Corrige avec : pip uninstall -y websocket websocket-client && "
        "pip install websocket-client"
    )

try:
    from flashforge import FlashForgeClient as _FFClient
    from flashforge.models.machine_info import MachineState as _FFMachineState
    HAS_FLASHFORGE = True
except ImportError:
    HAS_FLASHFORGE = False
    app_logger.info("[WARN] flashforge-python-api non installé (pip install flashforge-python-api). FlashForge ne fonctionnera pas.")

try:
    from rectpack import newPacker, MaxRectsBssf, SORT_AREA
    HAS_RECTPACK = True
except ImportError:
    HAS_RECTPACK = False
    app_logger.info("[WARN] rectpack non installé (pip install rectpack). Nesting en mode dégradé (étagères).")

try:
    from shapely.geometry import MultiPoint
    from shapely import affinity as shapely_affinity
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False
    app_logger.info("[WARN] shapely non installé (pip install shapely). Nesting en mode rectangle englobant.")

def _build_bambu_result_from_state(raw_state, default_result):
    status_map = {
        'printing': 'printing', 'running': 'printing',
        'pause': 'paused', 'paused': 'paused',
        'finish': 'idle', 'idle': 'idle', 'prepare': 'idle',
        'failed': 'error', 'slicing': 'idle'
    }
    gcode_state = raw_state.get('gcode_state', '').lower()
    status = status_map.get(gcode_state, 'idle')
    nozzle_temp = raw_state.get('nozzle_temper', 0)
    nozzle_target = raw_state.get('nozzle_target_temper', 0)
    bed_temp = raw_state.get('bed_temper', 0)
    bed_target = raw_state.get('bed_target_temper', 0)
    chamber_temp = raw_state.get('chamber_temper', 0)
    mc_percent = raw_state.get('mc_percent', 0)
    mc_remaining = raw_state.get('mc_remaining_time', 0)
    layer_num = raw_state.get('layer_num', 0)
    total_layer = raw_state.get('total_layer_num', 0)
    subtask_name = raw_state.get('subtask_name', '')
    ams_info = []
    ams = raw_state.get('ams', {})
    if ams and isinstance(ams, dict):
        for tray in ams.get('tray', []):
            remain_pct = tray.get('remain', -1)
            try:
                remain_pct = float(remain_pct)
            except (TypeError, ValueError):
                remain_pct = -1
            tray_weight_raw = tray.get('tray_weight', '')
            try:
                tray_weight = float(tray_weight_raw) if tray_weight_raw not in ('', None) else 1000.0
            except (TypeError, ValueError):
                tray_weight = 1000.0
            remaining_g = round(tray_weight * remain_pct / 100, 1) if remain_pct >= 0 else None
            ams_info.append({
                'id': tray.get('id', ''),
                'color': tray.get('tray_color', ''),
                'material': tray.get('tray_type', ''),
                'temp': tray.get('nozzle_temp_max', 0),
                'remain_pct': remain_pct if remain_pct >= 0 else None,
                'tray_weight': tray_weight,
                'remaining_g': remaining_g
            })
    elapsed_min = 0
    total_min = 0
    if mc_percent > 0 and mc_remaining > 0:
        total_min = int(mc_remaining / (1 - mc_percent / 100)) if mc_percent < 100 else mc_remaining
        elapsed_min = total_min - mc_remaining
    return {
        'status': status,
        'progress': mc_percent,
        'file': subtask_name,
        'temps': {
            'extruder': {'current': round(nozzle_temp, 1), 'target': round(nozzle_target, 1)},
            'bed': {'current': round(bed_temp, 1), 'target': round(bed_target, 1)},
            'chamber': {'current': round(chamber_temp, 1), 'target': 0}
        },
        'time': {
            'elapsed': elapsed_min * 60,
            'remaining': mc_remaining * 60,
            'total': total_min * 60
        },
        'layers': {'current': layer_num, 'total': total_layer},
        'ams': ams_info,
        'last_print': {'filename': '', 'duration': 0, 'finished_at': ''}
    }


class BambuPersistentConnection:

    def __init__(self, pid, ip, access_code, serial):
        self.pid = pid
        self.ip = ip
        self.access_code = access_code
        self.serial = serial
        self.raw_state = {}
        self.lock = threading.Lock()
        self.is_connected = False
        self.client = None
        self._thread = None
        self._stopping = False

    def matches(self, ip, access_code, serial):
        return self.ip == ip and self.access_code == access_code and self.serial == serial

    def _on_connect(self, client, userdata, flags, rc):
        self.is_connected = (rc == 0)
        if rc == 0:
            topic = f"device/{self.serial}/report" if self.serial else '#'
            client.subscribe(topic)
            if self.serial:
                client.publish(
                    f"device/{self.serial}/request",
                    json.dumps({"pushing": {"sequence_id": "0", "command": "pushall"}}),
                    qos=1
                )

    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            print_info = payload.get('print', {})
            if not print_info:
                return
            with self.lock:
                self.raw_state.update(print_info)
        except Exception as e:
            app_logger.info(f"[Bambu MQTT] Erreur parsing (printer #{self.pid}): {e}")

    def start(self):
        try:
            try:
                self.client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
                    client_id=f"stellio_persist_{self.pid}_{uuid.uuid4().hex[:8]}",
                    protocol=mqtt.MQTTv311,
                    clean_session=True
                )
            except TypeError:
                self.client = mqtt.Client(
                    client_id=f"stellio_persist_{self.pid}_{uuid.uuid4().hex[:8]}",
                    protocol=mqtt.MQTTv311,
                    clean_session=True
                )
            self.client.username_pw_set('bblp', self.access_code)
            self.client.tls_set(cert_reqs=ssl.CERT_NONE)
            self.client.tls_insecure_set(True)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.reconnect_delay_set(min_delay=1, max_delay=30)
            self.client.connect(self.ip, 8883, keepalive=5)
            self._thread = threading.Thread(target=self.client.loop_forever, kwargs={'retry_first_connection': False}, daemon=True)
            self._thread.start()
        except Exception as e:
            app_logger.info(f"[Bambu MQTT] Échec démarrage connexion persistante (printer #{self.pid}): {e}")

    def stop(self):
        self._stopping = True
        try:
            if self.client:
                self.client.disconnect()
        except Exception:
            pass

    def get_state_snapshot(self):
        with self.lock:
            return dict(self.raw_state)


_bambu_connections = {}
_bambu_connections_lock = threading.Lock()


def _ensure_bambu_connection(db_row):
    pid = db_row['id']
    ip = db_row['ip']
    config = db_row.get('config') or {}
    access_code = config.get('code', '') or db_row.get('api_key', '')
    serial = config.get('serial', '')
    if not access_code:
        return None
    with _bambu_connections_lock:
        existing = _bambu_connections.get(pid)
        if existing and existing.matches(ip, access_code, serial):
            return existing
        if existing:
            existing.stop()
        conn = BambuPersistentConnection(pid, ip, access_code, serial)
        _bambu_connections[pid] = conn
    conn.start()
    return conn


def _stop_bambu_connection(pid):
    with _bambu_connections_lock:
        conn = _bambu_connections.pop(pid, None)
    if conn:
        conn.stop()


def _generate_bambu_mjpeg_stream(ip, access_code):
    username = 'bblp'
    auth_data = bytearray()
    auth_data += struct.pack("<I", 0x40)
    auth_data += struct.pack("<I", 0x3000)
    auth_data += struct.pack("<I", 0)
    auth_data += struct.pack("<I", 0)
    auth_data += username.encode('ascii').ljust(32, b'\x00')
    auth_data += access_code.encode('ascii').ljust(32, b'\x00')

    jpeg_start = b'\xff\xd8\xff\xe0'
    jpeg_end = b'\xff\xd9'

    ssl_sock = None
    try:
        raw_sock = socket.create_connection((ip, 6000), timeout=10)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ssl_sock = ctx.wrap_socket(raw_sock, server_hostname=ip)
        ssl_sock.write(auth_data)
        ssl_sock.settimeout(10)

        img = None
        payload_size = 0
        while True:
            dr = ssl_sock.recv(4096)
            if len(dr) == 0:
                app_logger.info(f"[Bambu Camera] Connexion refusée par {ip} (code d'accès incorrect ?)")
                break
            if img is not None and len(dr) > 0:
                img += dr
                if len(img) > payload_size:
                    img = None
                elif len(img) == payload_size:
                    if img[:4] == jpeg_start and img[-2:] == jpeg_end:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n'
                               b'Content-Length: ' + str(len(img)).encode() + b'\r\n\r\n' +
                               bytes(img) + b'\r\n')
                    img = None
            elif len(dr) == 16:
                img = bytearray()
                payload_size = int.from_bytes(dr[0:4], byteorder='little')
    except (ssl.SSLError, OSError, socket.timeout) as e:
        app_logger.info(f"[Bambu Camera] Flux interrompu ({ip}): {e}")
    except GeneratorExit:
        pass
    finally:
        if ssl_sock:
            try:
                ssl_sock.close()
            except Exception:
                pass


BAMBU_JPEG_PORT6000_MODELS = {'A1', 'A1_MINI', 'P1P', 'P1S'}


BAMBU_RTSP_PORT322_MODELS = {'X1', 'X1C', 'X1E', 'X2D', 'H2D', 'H2S', 'H2C', 'P2S'}


def _generate_bambu_rtsp_mjpeg_stream(ip, access_code):
    ffmpeg_path = FFMPEG_TOOL
    if not ffmpeg_path:
        app_logger.warning("[Bambu Camera RTSP] ffmpeg introuvable (bin/ ou PATH) — flux caméra indisponible pour ce modèle")
        return

    rtsp_url = f"rtsps://bblp:{access_code}@{ip}:322/streaming/live/1"
    cmd = [
        ffmpeg_path,
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-an',
        '-f', 'mjpeg',
        '-q:v', '5',
        '-r', '10',
        '-loglevel', 'error',
        'pipe:1',
    ]

    proc = None
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **_popen_kwargs_silent())
        jpeg_start = b'\xff\xd8'
        jpeg_end = b'\xff\xd9'
        buf = bytearray()
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            buf += chunk
            start = buf.find(jpeg_start)
            end = buf.find(jpeg_end, start + 2) if start != -1 else -1
            while start != -1 and end != -1:
                frame = bytes(buf[start:end + 2])
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame)).encode() + b'\r\n\r\n' +
                       frame + b'\r\n')
                buf = buf[end + 2:]
                start = buf.find(jpeg_start)
                end = buf.find(jpeg_end, start + 2) if start != -1 else -1
    except GeneratorExit:
        pass
    except Exception as e:
        app_logger.info(f"[Bambu Camera RTSP] Flux interrompu ({ip}): {e}")
    finally:
        if proc:
            try:
                proc.kill()
                proc.wait(timeout=2)
            except Exception:
                pass


def _elegoo_sdcp_discover(ip, timeout=3):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(timeout)
        sock.sendto(b"M99999", (ip, 3000))
        data, _addr = sock.recvfrom(8192)
        sock.close()
        payload = json.loads(data.decode('utf-8'))
        data_dict = payload.get('Data', payload)
        attrs = data_dict.get('Attributes', data_dict)
        return {
            'connection': payload.get('Id'),
            'mainboard_id': attrs.get('MainboardID'),
            'name': attrs.get('Name', ''),
            'model': attrs.get('MachineName', ''),
        }
    except Exception as e:
        app_logger.info(f"[Elegoo SDCP] Découverte échouée pour {ip}: {e}")
        return None


def _elegoo_cc2_discover(ip, timeout=3):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(timeout)
        sock.sendto(json.dumps({"id": 0, "method": 7000}).encode('utf-8'), (ip, 52700))
        data, _addr = sock.recvfrom(8192)
        sock.close()
        payload = json.loads(data.decode('utf-8'))
        result = payload.get('result', payload)
        return {
            'serial': result.get('sn'),
            'name': result.get('host_name', ''),
            'model': result.get('machine_model', ''),
        }
    except Exception as e:
        app_logger.info(f"[Elegoo CC2] Découverte échouée pour {ip}: {e}")
        return None


ELEGOO_SDCP_STATUS_MAP = {
    0: 'idle', 1: 'idle', 2: 'idle', 3: 'printing', 4: 'idle',
    5: 'paused', 6: 'paused', 7: 'idle', 8: 'idle', 9: 'idle',
    10: 'idle', 12: 'error', 13: 'printing', 114: 'error',
}


def _build_elegoo_sdcp_result(raw_state, default_result):
    print_info = raw_state.get('PrintInfo', {})
    sub_status = print_info.get('Status', 0)
    status = ELEGOO_SDCP_STATUS_MAP.get(sub_status, 'idle')
    current_ticks = print_info.get('CurrentTicks', 0) or 0
    total_ticks = print_info.get('TotalTicks', 0) or 0
    remaining_ticks = max(0, total_ticks - current_ticks)
    progress = print_info.get('Progress', 0) or 0
    return {
        'status': status,
        'progress': progress,
        'file': print_info.get('Filename', ''),
        'temps': {
            'extruder': {'current': round(raw_state.get('TempOfNozzle', 0) or 0, 1), 'target': round(raw_state.get('TempTargetNozzle', 0) or 0, 1)},
            'bed': {'current': round(raw_state.get('TempOfHotbed', 0) or 0, 1), 'target': round(raw_state.get('TempTargetHotbed', 0) or 0, 1)},
            'chamber': {'current': round(raw_state.get('TempOfBox', 0) or 0, 1), 'target': 0}
        },
        'time': {'elapsed': current_ticks / 1000, 'remaining': remaining_ticks / 1000, 'total': total_ticks / 1000},
        'layers': {'current': print_info.get('CurrentLayer', 0) or 0, 'total': print_info.get('TotalLayer', 0) or 0},
        'ams': [],
        'last_print': {'filename': '', 'duration': 0, 'finished_at': ''}
    }


class ElegooSDCPConnection:

    def __init__(self, pid, ip, connection_id, mainboard_id):
        self.pid = pid
        self.ip = ip
        self.connection_id = connection_id
        self.mainboard_id = mainboard_id
        self.raw_state = {}
        self.lock = threading.Lock()
        self.is_connected = False
        self.ws = None
        self._stopping = False
        self._thread = None
        self._refresh_thread = None
        self.video_url = None
        self.video_ack = None
        self._video_event = threading.Event()

    def matches(self, ip, connection_id, mainboard_id):
        return self.ip == ip and self.connection_id == connection_id and self.mainboard_id == mainboard_id

    def _send_cmd(self, cmd, data=None):
        if not self.ws or not self.is_connected:
            return
        payload = {
            "Id": self.connection_id,
            "Data": {
                "Cmd": cmd,
                "Data": data or {},
                "RequestID": uuid.uuid4().hex[:16],
                "MainboardID": self.mainboard_id,
                "TimeStamp": int(time.time()),
                "From": 0,
            },
            "Topic": f"sdcp/request/{self.mainboard_id}",
        }
        try:
            self.ws.send(json.dumps(payload))
        except Exception:
            pass

    def _on_open(self, ws):
        self.is_connected = True
        self._send_cmd(0)

    def _on_close(self, ws, *args):
        self.is_connected = False

    def _on_error(self, ws, error):
        self.is_connected = False

    def _on_message(self, ws, message):
        try:
            payload = json.loads(message)
            topic = payload.get('Topic', '')
            if '/status/' in topic:
                status_data = payload.get('Status', payload.get('Data', {}))
                with self.lock:
                    self.raw_state.update(status_data)
                return
            if '/response/' in topic:
                resp = payload.get('Data', {})
                if resp.get('Cmd') == 386:
                    inner = resp.get('Data', {}) or {}
                    ack = inner.get('Ack')
                    with self.lock:
                        self.video_ack = ack
                        self.video_url = inner.get('VideoUrl') if ack == 0 else None
                    self._video_event.set()
        except Exception as e:
            app_logger.info(f"[Elegoo SDCP] Erreur parsing (printer #{self.pid}): {e}")

    def request_video(self, timeout=4):
        if not self.is_connected:
            return None, None
        with self.lock:
            self.video_url = None
            self.video_ack = None
        self._video_event.clear()
        self._send_cmd(386, {"Enable": 1})
        self._video_event.wait(timeout)
        with self.lock:
            return self.video_url, self.video_ack

    def _refresh_loop(self):
        while not self._stopping:
            time.sleep(6)
            if self.is_connected:
                self._send_cmd(0)

    def _run_forever_loop(self):
        if not HAS_WEBSOCKET:
            app_logger.info(
                f"[Elegoo SDCP] Désactivé (printer #{self.pid}) : "
                f"websocket-client indisponible ou cassé."
            )
            return
        while not self._stopping:
            try:
                self.ws = ws_client.WebSocketApp(
                    f"ws://{self.ip}:3030/websocket",
                    on_open=self._on_open,
                    on_close=self._on_close,
                    on_error=self._on_error,
                    on_message=self._on_message,
                )
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                app_logger.info(f"[Elegoo SDCP] Connexion perdue (printer #{self.pid}): {e}")
            self.is_connected = False
            if self._stopping:
                break
            time.sleep(5)

    def start(self):
        self._thread = threading.Thread(target=self._run_forever_loop, daemon=True)
        self._thread.start()
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()

    def stop(self):
        self._stopping = True
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

    def get_state_snapshot(self):
        with self.lock:
            return dict(self.raw_state)


_elegoo_sdcp_connections = {}
_elegoo_sdcp_connections_lock = threading.Lock()


def _ensure_elegoo_sdcp_connection(db_row):
    pid = db_row['id']
    ip = db_row['ip']
    with _elegoo_sdcp_connections_lock:
        existing = _elegoo_sdcp_connections.get(pid)
        if existing and existing.ip == ip:
            return existing
    discovered = _elegoo_sdcp_discover(ip)
    if not discovered or not discovered.get('mainboard_id'):
        return None
    with _elegoo_sdcp_connections_lock:
        existing = _elegoo_sdcp_connections.get(pid)
        if existing:
            existing.stop()
        conn = ElegooSDCPConnection(pid, ip, discovered['connection'], discovered['mainboard_id'])
        _elegoo_sdcp_connections[pid] = conn
    conn.start()
    return conn


def _stop_elegoo_sdcp_connection(pid):
    with _elegoo_sdcp_connections_lock:
        conn = _elegoo_sdcp_connections.pop(pid, None)
    if conn:
        conn.stop()


def _build_creality_result(raw_state, default_result):
    err_code = (raw_state.get('err') or {}).get('errcode', 0)
    if err_code:
        status = 'error'
    else:
        st = raw_state.get('state')
        if st == 1:
            status = 'printing'
        elif st == 5:
            status = 'paused'
        else:
            status = 'idle'
    progress = raw_state.get('printProgress')
    if progress is None:
        progress = raw_state.get('dProgress', 0) or 0
    return {
        'status': status,
        'progress': progress,
        'file': raw_state.get('printFileName', '') or '',
        'temps': {
            'extruder': {'current': round(raw_state.get('nozzleTemp', 0) or 0, 1), 'target': round(raw_state.get('targetNozzleTemp', 0) or 0, 1)},
            'bed': {'current': round(raw_state.get('bedTemp0', 0) or 0, 1), 'target': round(raw_state.get('targetBedTemp0', 0) or 0, 1)},
            'chamber': {'current': round(raw_state.get('boxTemp', 0) or 0, 1), 'target': round(raw_state.get('targetBoxTemp', 0) or 0, 1)}
        },
        'time': {
            'elapsed': raw_state.get('printJobTime', 0) or 0,
            'remaining': raw_state.get('printLeftTime', 0) or 0,
            'total': (raw_state.get('printJobTime', 0) or 0) + (raw_state.get('printLeftTime', 0) or 0)
        },
        'layers': {'current': 0, 'total': 0},
        'ams': [],
        'last_print': {'filename': '', 'duration': 0, 'finished_at': ''}
    }


class CrealityConnection:

    def __init__(self, pid, ip):
        self.pid = pid
        self.ip = ip
        self.raw_state = {}
        self.lock = threading.Lock()
        self.is_connected = False
        self.ws = None
        self._stopping = False
        self._thread = None

    def _on_open(self, ws):
        self.is_connected = True

    def _on_close(self, ws, *args):
        self.is_connected = False

    def _on_error(self, ws, error):
        self.is_connected = False

    def _on_message(self, ws, message):
        try:
            if message == 'ok':
                return
            payload = json.loads(message)
            if not isinstance(payload, dict):
                return
            if payload.get('ModeCode') == 'heart_beat':
                try:
                    ws.send('ok')
                except Exception:
                    pass
                return
            with self.lock:
                self.raw_state.update(payload)
        except Exception as e:
            app_logger.info(f"[Creality] Erreur parsing (printer #{self.pid}): {e}")

    def _run_forever_loop(self):
        if not HAS_WEBSOCKET:
            app_logger.info(
                f"[Creality] Désactivé (printer #{self.pid}) : "
                f"websocket-client indisponible ou cassé."
            )
            return
        while not self._stopping:
            try:
                self.ws = ws_client.WebSocketApp(
                    f"ws://{self.ip}:9999",
                    subprotocols=['wsslicer'],
                    on_open=self._on_open,
                    on_close=self._on_close,
                    on_error=self._on_error,
                    on_message=self._on_message,
                )
                self.ws.run_forever(ping_interval=None)
            except Exception as e:
                app_logger.info(f"[Creality] Connexion perdue (printer #{self.pid}): {e}")
            self.is_connected = False
            if self._stopping:
                break
            time.sleep(5)

    def start(self):
        self._thread = threading.Thread(target=self._run_forever_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stopping = True
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

    def get_state_snapshot(self):
        with self.lock:
            return dict(self.raw_state)


_creality_connections = {}
_creality_connections_lock = threading.Lock()


def _ensure_creality_connection(db_row):
    pid = db_row['id']
    ip = db_row['ip']
    with _creality_connections_lock:
        existing = _creality_connections.get(pid)
        if existing and existing.ip == ip:
            return existing
        if existing:
            existing.stop()
        conn = CrealityConnection(pid, ip)
        _creality_connections[pid] = conn
    conn.start()
    return conn


def _stop_creality_connection(pid):
    with _creality_connections_lock:
        conn = _creality_connections.pop(pid, None)
    if conn:
        conn.stop()


def _build_flashforge_result(info, default_result):
    state_value = info.machine_state.value if info.machine_state else 'unknown'
    status_map = {'printing': 'printing', 'paused': 'paused', 'pausing': 'paused', 'error': 'error'}
    status = status_map.get(state_value, 'idle')
    extruder = info.extruder
    bed = info.print_bed
    chamber = info.chamber
    return {
        'status': status,
        'progress': info.print_progress_int or 0,
        'file': info.print_file_name or '',
        'temps': {
            'extruder': {'current': round(extruder.current, 1) if extruder else 0, 'target': round(extruder.set, 1) if extruder else 0},
            'bed': {'current': round(bed.current, 1) if bed else 0, 'target': round(bed.set, 1) if bed else 0},
            'chamber': {'current': round(chamber.current, 1) if chamber else 0, 'target': round(chamber.set, 1) if chamber else 0}
        },
        'time': {'elapsed': info.print_duration or 0, 'remaining': 0, 'total': 0},
        'layers': {'current': info.current_print_layer or 0, 'total': info.total_print_layers or 0},
        'ams': [],
        'last_print': {'filename': '', 'duration': 0, 'finished_at': ''}
    }


class FlashForgePersistentConnection:

    def __init__(self, pid, ip, serial, check_code):
        self.pid = pid
        self.ip = ip
        self.serial = serial
        self.check_code = check_code
        self.snapshot = None
        self.lock = threading.Lock()
        self.is_connected = False
        self._stopping = False
        self._thread = None
        self._client = None

    def matches(self, ip, serial, check_code):
        return self.ip == ip and self.serial == serial and self.check_code == check_code

    async def _main(self):
        while not self._stopping:
            try:
                self._client = _FFClient(self.ip, self.serial, self.check_code)
                ok = await self._client.initialize()
                if not ok:
                    self.is_connected = False
                    await asyncio.sleep(10)
                    continue
                await self._client.init_control()
                self.is_connected = True
                while not self._stopping:
                    try:
                        info = await self._client.info.get()
                        if info:
                            with self.lock:
                                self.snapshot = info
                    except Exception as e:
                        app_logger.info(f"[FlashForge] Erreur lecture statut (printer #{self.pid}): {e}")
                        self.is_connected = False
                        break
                    await asyncio.sleep(5)
            except Exception as e:
                app_logger.info(f"[FlashForge] Connexion perdue (printer #{self.pid}): {e}")
            self.is_connected = False
            try:
                if self._client:
                    await self._client.dispose()
            except Exception:
                pass
            if self._stopping:
                break
            await asyncio.sleep(10)

    def _thread_main(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._main())
        except Exception:
            pass

    def start(self):
        self._thread = threading.Thread(target=self._thread_main, daemon=True)
        self._thread.start()

    def stop(self):
        self._stopping = True

    def get_state_snapshot(self):
        with self.lock:
            return self.snapshot


_flashforge_connections = {}
_flashforge_connections_lock = threading.Lock()


def _ensure_flashforge_connection(db_row):
    pid = db_row['id']
    ip = db_row['ip']
    config = db_row.get('config') or {}
    serial = config.get('serial', '')
    check_code = config.get('code', '') or db_row.get('api_key', '')
    if not serial or not check_code:
        return None
    with _flashforge_connections_lock:
        existing = _flashforge_connections.get(pid)
        if existing and existing.matches(ip, serial, check_code):
            return existing
        if existing:
            existing.stop()
        conn = FlashForgePersistentConnection(pid, ip, serial, check_code)
        _flashforge_connections[pid] = conn
    conn.start()
    return conn


def _stop_flashforge_connection(pid):
    with _flashforge_connections_lock:
        conn = _flashforge_connections.pop(pid, None)
    if conn:
        conn.stop()


ELEGOO_CC2_STATUS_MAP = {
    0: 'idle', 1: 'idle', 2: 'printing', 3: 'idle', 4: 'idle',
    5: 'idle', 6: 'idle', 7: 'idle', 8: 'idle', 9: 'idle',
    10: 'idle', 11: 'idle', 12: 'idle', 13: 'idle', 14: 'error', 15: 'idle',
}


def _build_elegoo_cc2_result(raw_state, default_result):
    machine_status = raw_state.get('machine_status', {})
    sub_status = machine_status.get('sub_status', 0)
    status = 'paused' if sub_status in (2502, 2505) else ELEGOO_CC2_STATUS_MAP.get(machine_status.get('status', 0), 'idle')
    print_status = raw_state.get('print_status', {})
    extruder = raw_state.get('extruder', {})
    heater_bed = raw_state.get('heater_bed', {})
    ztemp = raw_state.get('ztemperature_sensor', {})
    progress = print_status.get('progress', machine_status.get('progress', 0)) or 0
    current_time = print_status.get('print_duration', 0) or 0
    total_time = print_status.get('total_duration', 0) or 0
    remaining_time = print_status.get('remaining_time_sec', max(0, total_time - current_time))
    return {
        'status': status,
        'progress': progress,
        'file': print_status.get('filename', ''),
        'temps': {
            'extruder': {'current': round(extruder.get('temperature', 0) or 0, 1), 'target': round(extruder.get('target', 0) or 0, 1)},
            'bed': {'current': round(heater_bed.get('temperature', 0) or 0, 1), 'target': round(heater_bed.get('target', 0) or 0, 1)},
            'chamber': {'current': round(ztemp.get('temperature', 0) or 0, 1), 'target': 0}
        },
        'time': {'elapsed': current_time, 'remaining': remaining_time, 'total': total_time},
        'layers': {'current': print_status.get('current_layer', 0) or 0, 'total': print_status.get('total_layer', 0) or 0},
        'ams': [],
        'last_print': {'filename': '', 'duration': 0, 'finished_at': ''}
    }


class ElegooCC2Connection:

    def __init__(self, pid, ip, serial, access_code):
        self.pid = pid
        self.ip = ip
        self.serial = serial
        self.access_code = access_code or '123456'
        self.client_id = f"stellio{uuid.uuid4().hex[:8]}"
        self.raw_state = {}
        self.lock = threading.Lock()
        self.is_connected = False
        self.is_registered = False
        self.client = None
        self._stopping = False
        self._thread = None
        self._loop_thread = None

    def matches(self, ip, serial, access_code):
        return self.ip == ip and self.serial == serial and (self.access_code or '123456') == (access_code or '123456')

    def _on_connect(self, client, userdata, flags, rc):
        self.is_connected = (rc == 0)
        if rc != 0:
            return
        client.subscribe(f"elegoo/{self.serial}/{self.client_id}/api_response")
        client.subscribe(f"elegoo/{self.serial}/api_status")
        client.subscribe(f"elegoo/{self.serial}/{self.client_id}/register_response")
        client.publish(f"elegoo/{self.serial}/api_register", json.dumps({
            "client_id": self.client_id, "request_id": self.client_id
        }))

    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        self.is_registered = False

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            topic = msg.topic
            if 'register_response' in topic:
                self.is_registered = (payload.get('error', payload.get('error_code', 0)) in (0, None, ''))
                return
            result = payload.get('result', payload.get('params', {}))
            if not isinstance(result, dict):
                return
            with self.lock:
                self.raw_state.update(result)
        except Exception as e:
            app_logger.info(f"[Elegoo CC2] Erreur parsing (printer #{self.pid}): {e}")

    def _request_status(self):
        if not self.client or not self.is_connected:
            return
        topic = f"elegoo/{self.serial}/{self.client_id}/api_request"
        try:
            self.client.publish(topic, json.dumps({"id": 1, "method": 1002, "params": {}}))
        except Exception:
            pass

    def _heartbeat_loop(self):
        while not self._stopping:
            time.sleep(8)
            if self.is_connected:
                self._request_status()
                try:
                    self.client.publish(f"elegoo/{self.serial}/{self.client_id}/api_request", json.dumps({"type": "PING"}))
                except Exception:
                    pass

    def start(self):
        try:
            try:
                self.client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
                    client_id=self.client_id, protocol=mqtt.MQTTv311, clean_session=True
                )
            except TypeError:
                self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311, clean_session=True)
            self.client.username_pw_set('elegoo', self.access_code)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.reconnect_delay_set(min_delay=1, max_delay=30)
            self.client.connect(self.ip, 1883, keepalive=60)
            self._loop_thread = threading.Thread(target=self.client.loop_forever, kwargs={'retry_first_connection': False}, daemon=True)
            self._loop_thread.start()
            self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._thread.start()
        except Exception as e:
            app_logger.info(f"[Elegoo CC2] Échec démarrage connexion persistante (printer #{self.pid}): {e}")

    def stop(self):
        self._stopping = True
        try:
            if self.client:
                self.client.disconnect()
        except Exception:
            pass

    def get_state_snapshot(self):
        with self.lock:
            return dict(self.raw_state)


_elegoo_cc2_connections = {}
_elegoo_cc2_connections_lock = threading.Lock()


def _ensure_elegoo_cc2_connection(db_row):
    pid = db_row['id']
    ip = db_row['ip']
    config = db_row.get('config') or {}
    access_code = config.get('code', '') or db_row.get('api_key', '') or '123456'
    with _elegoo_cc2_connections_lock:
        existing = _elegoo_cc2_connections.get(pid)
        if existing and existing.matches(ip, existing.serial, access_code):
            return existing
    serial = config.get('serial', '')
    if not serial:
        discovered = _elegoo_cc2_discover(ip)
        if not discovered or not discovered.get('serial'):
            return None
        serial = discovered['serial']
    with _elegoo_cc2_connections_lock:
        existing = _elegoo_cc2_connections.get(pid)
        if existing:
            existing.stop()
        conn = ElegooCC2Connection(pid, ip, serial, access_code)
        _elegoo_cc2_connections[pid] = conn
    conn.start()
    return conn


def _fetch_klipper_spoolman_active_spool(base):
    try:
        r = requests.get(f"{base}/printer/objects/query?spoolman", timeout=3)
        if not r.ok:
            return None
        status = (r.json().get('result', {}) or {}).get('status', {}) or {}
        sm = status.get('spoolman') or {}
        spool_id = sm.get('spool_id')
        if not spool_id:
            return None
        settings = load_settings()
        spoolman_url = (settings.get('spoolman_url') or '').rstrip('/')
        if not spoolman_url:
            return None
        sr = requests.get(f"{spoolman_url}/api/v1/spool/{spool_id}", timeout=5, headers={"Accept": "application/json"})
        if not sr.ok:
            return None
        spool = sr.json()
        filament = spool.get('filament') or {}
        vendor = filament.get('vendor') or {}
        color_hex = str(filament.get('color_hex') or '').lstrip('#')
        return {
            'id': spool_id,
            'name': filament.get('name') or vendor.get('name') or f"Bobine #{spool_id}",
            'material': filament.get('material') or '',
            'color': color_hex,
            'temp': 0,
            'remain_pct': None,
            'tray_weight': filament.get('weight'),
            'remaining_g': spool.get('remaining_weight'),
        }
    except Exception as e:
        app_logger.info(f"[Klipper] Bobine active Spoolman (best-effort, non bloquant) indisponible: {e}")
        return None


def _stop_elegoo_cc2_connection(pid):
    with _elegoo_cc2_connections_lock:
        conn = _elegoo_cc2_connections.pop(pid, None)
    if conn:
        conn.stop()


class PrinterManager:
    def __init__(self):
        self.clients = {}

    def connect_printer(self, db_row):
        pid = db_row['id']
        ptype = db_row['type']
        ip = db_row['ip']
        api_key = db_row['api_key']
        try:
            if ptype == 'octoprint':
                url = f"http://{ip}/api/connection"
                headers = {'X-Api-Key': api_key}
                r = requests.get(url, headers=headers, timeout=5)
                return r.status_code == 200
            elif ptype == 'prusalink':
                url = f"http://{ip}/api/version"
                headers = {'X-Api-Key': api_key}
                r = requests.get(url, headers=headers, timeout=5)
                return r.status_code == 200
            elif ptype == 'klipper':
                port = db_row['config'].get('port', '7125') if db_row['config'] else '7125'
                url = f"http://{ip}:{port}/server/info"
                r = requests.get(url, timeout=5)
                return r.status_code == 200
            elif ptype == 'bambu':
                if not HAS_MQTT: return False
                conn = _ensure_bambu_connection(db_row)
                if not conn:
                    return False
                for _ in range(20):
                    if conn.is_connected:
                        return True
                    time.sleep(0.2)
                return conn.is_connected
            elif ptype == 'elegoo_sdcp':
                if not HAS_WEBSOCKET: return False
                conn = _ensure_elegoo_sdcp_connection(db_row)
                if not conn:
                    return False
                for _ in range(20):
                    if conn.is_connected:
                        return True
                    time.sleep(0.2)
                return conn.is_connected
            elif ptype == 'elegoo_cc2':
                if not HAS_MQTT: return False
                conn = _ensure_elegoo_cc2_connection(db_row)
                if not conn:
                    return False
                for _ in range(30):
                    if conn.is_connected and conn.is_registered:
                        return True
                    time.sleep(0.2)
                return conn.is_connected and conn.is_registered
            elif ptype == 'creality':
                if not HAS_WEBSOCKET: return False
                conn = _ensure_creality_connection(db_row)
                if not conn:
                    return False
                for _ in range(20):
                    if conn.is_connected:
                        return True
                    time.sleep(0.2)
                return conn.is_connected
            elif ptype == 'flashforge':
                if not HAS_FLASHFORGE: return False
                conn = _ensure_flashforge_connection(db_row)
                if not conn:
                    return False
                for _ in range(40):
                    if conn.is_connected:
                        return True
                    time.sleep(0.5)
                return conn.is_connected
        except Exception as e:
            app_logger.info(f"[Printer] Erreur connexion {ptype} ({ip}): {e}")
            return False
        return False

    def get_status(self, db_row):
        ptype = db_row['type']
        ip = db_row['ip']
        api_key = db_row['api_key']
        default_result = {
            'status': 'unknown', 'progress': 0, 'file': '',
            'temps': {'extruder': {'current': 0, 'target': 0},
                      'bed': {'current': 0, 'target': 0},
                      'chamber': {'current': 0, 'target': 0}},
            'time': {'elapsed': 0, 'remaining': 0, 'total': 0},
            'last_print': {'filename': '', 'duration': 0, 'finished_at': ''}
        }
        try:
            if ptype in ('octoprint', 'prusalink'):
                headers = {'X-Api-Key': api_key}
                r_temp = requests.get(f"http://{ip}/api/printer", headers=headers, timeout=3).json()
                temps = r_temp.get('temperature', {})
                extruder = temps.get('tool0', {})
                bed = temps.get('bed', {})
                chamber = temps.get('chamber', {})
                r_job = requests.get(f"http://{ip}/api/job", headers=headers, timeout=3).json()
                state = r_job.get('state', 'Offline').lower()
                progress = r_job.get('progress', {}) or {}
                job = r_job.get('job', {}) or {}
                completion = progress.get('completion', 0) or 0
                print_time = progress.get('printTime', 0) or 0
                print_time_left = progress.get('printTimeLeft', 0) or 0
                if 'printing' in state:
                    status = 'printing'
                elif 'operational' in state or 'ready' in state:
                    status = 'idle'
                elif 'error' in state or 'closed' in state:
                    status = 'error'
                else:
                    status = state
                return {
                    'status': status,
                    'progress': round(completion, 1),
                    'file': job.get('file', {}).get('name', ''),
                    'temps': {
                        'extruder': {'current': round(extruder.get('actual', 0), 1),
                                     'target': round(extruder.get('target', 0), 1)},
                        'bed': {'current': round(bed.get('actual', 0), 1),
                                'target': round(bed.get('target', 0), 1)},
                        'chamber': {'current': round(chamber.get('actual', 0), 1),
                                    'target': round(chamber.get('target', 0), 1)}
                    },
                    'time': {
                        'elapsed': int(print_time),
                        'remaining': int(print_time_left),
                        'total': int(print_time + print_time_left) if print_time > 0 else 0
                    },
                    'last_print': self._get_octoprint_last_print(ip, api_key)
                }
            elif ptype == 'klipper':
                port = db_row['config'].get('port', '7125') if isinstance(db_row['config'], dict) else '7125'
                base = f"http://{ip}:{port}"
                try:
                    query_params = 'extruder&heater_bed&print_stats&display_status&virtual_sdcard'
                    url = f"{base}/printer/objects/query?{query_params}"
                    r = requests.get(url, timeout=5)
                    r.raise_for_status()
                    data = r.json()
                    result = data.get('result', {})
                    status_data = result.get('status', {})
                    extruder = status_data.get('extruder', {})
                    bed = status_data.get('heater_bed', {})
                    stats = status_data.get('print_stats', {})
                    display = status_data.get('display_status', {})
                    v_sdcard = status_data.get('virtual_sdcard', {})
                    ext_temp = extruder.get('temperature', 0)
                    ext_target = extruder.get('target', 0)
                    bed_temp = bed.get('temperature', 0)
                    bed_target = bed.get('target', 0)
                    if ext_temp == 0 and 'actual' in extruder:
                        ext_temp = extruder.get('actual', 0)
                    if bed_temp == 0 and 'actual' in bed:
                        bed_temp = bed.get('actual', 0)
                    state = stats.get('state', 'standby').lower()
                    status_map = {
                        'printing': 'printing', 'standby': 'idle', 'paused': 'paused',
                        'complete': 'complete', 'cancelled': 'idle', 'error': 'error',
                        'busy': 'busy', 'ready': 'idle'
                    }
                    status = status_map.get(state, state)
                    duration = stats.get('print_duration', 0) or 0
                    filename = stats.get('filename', '')
                    if not filename and v_sdcard:
                        filename = v_sdcard.get('file', '').split('/')[-1]
                    progress = (display.get('progress', 0) or 0) * 100
                    remaining = 0
                    if progress > 0 and progress < 100 and duration > 0:
                        remaining = int((duration / progress) * (100 - progress))
                    last_print = self._get_klipper_last_print(ip, port)
                    mm_info = []
                    try:
                        mm_url = f"{base}/printer/objects/query?box&filament_hub"
                        mm_r = requests.get(mm_url, timeout=3)
                        mm_status = (mm_r.json().get('result', {}) or {}).get('status', {}) if mm_r.ok else {}
                        box = mm_status.get('box')
                        if box and isinstance(box, dict):
                            slots = box.get('slots') or box.get('tray') or []
                            for i, slot in enumerate(slots):
                                if not isinstance(slot, dict):
                                    continue
                                color = slot.get('color') or slot.get('colour') or ''
                                if isinstance(color, list) and len(color) >= 3:
                                    color = ''.join(f'{int(c):02X}' for c in color[:3])
                                elif isinstance(color, str):
                                    color = color.lstrip('#')
                                mm_info.append({
                                    'id': slot.get('id', slot.get('index', i)),
                                    'color': color,
                                    'material': slot.get('material', slot.get('material_name', '')),
                                    'temp': slot.get('temp', slot.get('nozzle_temp', 0)) or 0,
                                    'remain_pct': slot.get('remain'),
                                    'tray_weight': None,
                                    'remaining_g': None
                                })
                        hub = mm_status.get('filament_hub')
                        if hub and isinstance(hub, dict):
                            slots = hub.get('slots') or hub.get('lanes') or []
                            for i, slot in enumerate(slots):
                                if not isinstance(slot, dict):
                                    continue
                                if slot.get('empty') or slot.get('status') == 'empty':
                                    continue
                                color = slot.get('color') or ''
                                if isinstance(color, list) and len(color) >= 3:
                                    color = ''.join(f'{int(c):02X}' for c in color[:3])
                                elif isinstance(color, str):
                                    color = color.lstrip('#')
                                mm_info.append({
                                    'id': slot.get('index', i),
                                    'color': color,
                                    'material': slot.get('material', ''),
                                    'temp': slot.get('temp', 0) or 0,
                                    'remain_pct': None,
                                    'tray_weight': None,
                                    'remaining_g': None
                                })
                    except Exception as e:
                        app_logger.info(f"[Klipper] CFS/ACE (best-effort, non bloquant) indisponible: {e}")


                    if not mm_info:
                        active_spool = _fetch_klipper_spoolman_active_spool(base)
                        if active_spool:
                            mm_info.append(active_spool)
                    return {
                        'status': status,
                        'progress': round(progress, 1),
                        'file': filename,
                        'temps': {
                            'extruder': {'current': round(float(ext_temp), 1), 'target': round(float(ext_target), 1)},
                            'bed': {'current': round(float(bed_temp), 1), 'target': round(float(bed_target), 1)},
                            'chamber': {'current': 0, 'target': 0}
                        },
                        'time': {
                            'elapsed': int(duration),
                            'remaining': remaining,
                            'total': int(duration + remaining)
                        },
                        'ams': mm_info,
                        'last_print': last_print
                    }
                except requests.exceptions.RequestException as e:
                    return {**default_result, 'status': 'offline'}
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    return {**default_result, 'status': 'error'}
            elif ptype == 'bambu':
                return self._get_bambu_status(db_row, default_result)
            elif ptype == 'elegoo_sdcp':
                return self._get_elegoo_sdcp_status(db_row, default_result)
            elif ptype == 'elegoo_cc2':
                return self._get_elegoo_cc2_status(db_row, default_result)
            elif ptype == 'creality':
                return self._get_creality_status(db_row, default_result)
            elif ptype == 'flashforge':
                return self._get_flashforge_status(db_row, default_result)
        except requests.exceptions.Timeout:
            return {**default_result, 'status': 'timeout'}
        except requests.exceptions.ConnectionError:
            return {**default_result, 'status': 'offline'}
        except Exception as e:
            app_logger.info(f"[Printer] Erreur get_status: {e}")
            return {**default_result, 'status': 'error'}
        return default_result

    def _get_bambu_status(self, db_row, default_result):
        if not HAS_MQTT:
            return {**default_result, 'status': 'error'}
        config = db_row.get('config') or {}
        access_code = config.get('code', '') or db_row.get('api_key', '')
        if not access_code:
            return {**default_result, 'status': 'error'}
        conn = _ensure_bambu_connection(db_row)
        if not conn:
            return {**default_result, 'status': 'error'}
        if not conn.is_connected:
            return {**default_result, 'status': 'offline'}
        raw_state = conn.get_state_snapshot()
        if 'gcode_state' not in raw_state:
            return {**default_result, 'status': 'idle'}
        return _build_bambu_result_from_state(raw_state, default_result)

    def _get_elegoo_sdcp_status(self, db_row, default_result):
        if not HAS_WEBSOCKET:
            return {**default_result, 'status': 'error'}
        conn = _ensure_elegoo_sdcp_connection(db_row)
        if not conn:
            return {**default_result, 'status': 'error'}
        if not conn.is_connected:
            return {**default_result, 'status': 'offline'}
        raw_state = conn.get_state_snapshot()
        if 'PrintInfo' not in raw_state:
            return {**default_result, 'status': 'idle'}
        return _build_elegoo_sdcp_result(raw_state, default_result)

    def _get_elegoo_cc2_status(self, db_row, default_result):
        if not HAS_MQTT:
            return {**default_result, 'status': 'error'}
        conn = _ensure_elegoo_cc2_connection(db_row)
        if not conn:
            return {**default_result, 'status': 'error'}
        if not conn.is_connected or not conn.is_registered:
            return {**default_result, 'status': 'offline'}
        raw_state = conn.get_state_snapshot()
        if 'machine_status' not in raw_state:
            return {**default_result, 'status': 'idle'}
        return _build_elegoo_cc2_result(raw_state, default_result)

    def _get_creality_status(self, db_row, default_result):
        if not HAS_WEBSOCKET:
            return {**default_result, 'status': 'error'}
        conn = _ensure_creality_connection(db_row)
        if not conn:
            return {**default_result, 'status': 'error'}
        if not conn.is_connected:
            return {**default_result, 'status': 'offline'}
        raw_state = conn.get_state_snapshot()
        if 'state' not in raw_state:
            return {**default_result, 'status': 'idle'}
        return _build_creality_result(raw_state, default_result)

    def _get_flashforge_status(self, db_row, default_result):
        if not HAS_FLASHFORGE:
            return {**default_result, 'status': 'error'}
        conn = _ensure_flashforge_connection(db_row)
        if not conn:
            return {**default_result, 'status': 'error'}
        if not conn.is_connected:
            return {**default_result, 'status': 'offline'}
        info = conn.get_state_snapshot()
        if not info:
            return {**default_result, 'status': 'idle'}
        return _build_flashforge_result(info, default_result)

    def _get_octoprint_last_print(self, ip, api_key):
        try:
            headers = {'X-Api-Key': api_key}
            r = requests.get(f"http://{ip}/api/job", headers=headers, timeout=3).json()
            if r.get('state', '').lower() in ['printing', 'paused']:
                return {'filename': '', 'duration': 0, 'finished_at': ''}
            history = requests.get(f"http://{ip}/api/history?limit=1", headers=headers, timeout=3).json()
            records = history.get('logs', [])
            if records:
                last = records[0]
                return {
                    'filename': last.get('printFile', {}).get('name', last.get('printFile', {}).get('path', '')),
                    'duration': int(last.get('printTime', 0) or 0),
                    'finished_at': last.get('timestamp', '')
                }
        except Exception:
            pass
        return {'filename': '', 'duration': 0, 'finished_at': ''}

    def _get_klipper_last_print(self, ip, port):
        try:
            base = f"http://{ip}:{port}"
            r = requests.get(f"{base}/server/history/list?limit=1", timeout=3)
            if r.status_code == 200:
                data = r.json()
                jobs = data.get('result', {}).get('jobs', [])
                if jobs:
                    last_job = jobs[0]
                    end_time = last_job.get('end_time', 0)
                    duration = last_job.get('print_duration', 0) or 0
                    metadata = last_job.get('metadata', {})
                    filename = metadata.get('filename', last_job.get('filename', ''))
                    finished_at = ""
                    if end_time:
                        finished_at = datetime.datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
                    return {
                        'filename': filename,
                        'duration': int(duration),
                        'finished_at': finished_at
                    }
        except Exception as e:
            app_logger.info(f"[Klipper History] Erreur: {e}")
        return {'filename': '', 'duration': 0, 'finished_at': ''}

    def upload_file(self, db_row, file_path):
        ptype = db_row['type']
        ip = db_row['ip']
        api_key = db_row['api_key']
        try:
            if ptype in ('octoprint', 'prusalink'):
                url = f"http://{ip}/api/files/local"
                headers = {'X-Api-Key': api_key}
                with open(file_path, 'rb') as f:
                    files = {'file': f}
                    r = requests.post(url, headers=headers, files=files, timeout=30)
                return r.status_code == 201
            elif ptype == 'klipper':
                port = db_row['config'].get('port', '7125') if isinstance(db_row['config'], dict) else '7125'
                base = f"http://{ip}:{port}"
                try:
                    with open(file_path, 'rb') as f:
                        files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
                        data = {'root': 'gcodes'}
                        r = requests.post(f"{base}/server/files/upload", files=files, data=data, timeout=60)
                    if r.status_code == 200:
                        response_data = r.json()
                        if response_data.get('result') == "ok" or 'accepted' in str(response_data).lower():
                            return True
                    return False
                except Exception as e:
                    app_logger.info(f"[Klipper Upload] Erreur: {e}")
                    return False
            elif ptype == 'bambu':
                return True
        except Exception as e:
            app_logger.info(f"[Printer Upload] Erreur: {e}")
            return False
        return False

def parse_printer_config(db_row):
    row = dict(db_row)
    config = row.get('config')
    if isinstance(config, str):
        try:
            row['config'] = json.loads(config) if config else {}
        except json.JSONDecodeError:
            row['config'] = {}
    elif not isinstance(config, dict):
        row['config'] = {}
    if row.get('api_key'):
        row['api_key'] = decrypt_account_secret(row['api_key'])
    if row.get('power_w') is None:
        row['power_w'] = 120
    return row

printer_hub = PrinterManager()


def is_first_launch():
    conn = get_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()
    return count == 0

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def hash_pw_strong(password):
    salt = secrets.token_hex(16)
    iterations = 200_000
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"

def verify_pw_strong(password, stored_hash):
    if not stored_hash:
        return False
    if stored_hash.startswith('pbkdf2_sha256$'):
        try:
            _, iterations, salt, expected_hex = stored_hash.split('$')
            dk = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations))
            return secrets.compare_digest(dk.hex(), expected_hex)
        except Exception:
            return False
    return secrets.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored_hash)

def _is_legacy_hash(stored_hash):
    return bool(stored_hash) and not stored_hash.startswith('pbkdf2_sha256$')

def generate_recovery_code():
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    raw = ''.join(secrets.choice(alphabet) for _ in range(16))
    return '-'.join(raw[i:i + 4] for i in range(0, 16, 4))

SECURITY_QUESTION_KEYS = {'pet', 'city', 'school', 'nickname', 'custom'}

def normalize_answer(answer):
    return (answer or '').strip().lower()

def hash_answer(answer):
    return hash_pw_strong(normalize_answer(answer))

def verify_answer(answer, stored_hash):
    return verify_pw_strong(normalize_answer(answer), stored_hash)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "non authentifié"}), 401
        return f(*args, **kwargs)
    return decorated


app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
_SECRET_KEY_FILE = os.path.join(DATA_DIR, 'flask_secret.key')
if os.path.exists(_SECRET_KEY_FILE):
    with open(_SECRET_KEY_FILE, 'r') as _f:
        app.secret_key = _f.read().strip()
else:
    app.secret_key = secrets.token_hex(32)
    with open(_SECRET_KEY_FILE, 'w') as _f:
        _f.write(app.secret_key)
    try:
        os.chmod(_SECRET_KEY_FILE, 0o600)
    except Exception:
        pass

app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.before_request
def _csrf_protect():
    if 'user_id' not in session:
        return
    if not session.get('csrf_token'):
        session['csrf_token'] = secrets.token_hex(32)
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        header_token = request.headers.get('X-CSRF-Token', '')
        if not header_token or not secrets.compare_digest(session['csrf_token'], header_token):
            return jsonify({"error": "Jeton de sécurité manquant ou expiré. Rechargez la page et réessayez."}), 403

@app.after_request
def _set_security_headers(response):
    csrf_token = session.get('csrf_token')
    if csrf_token and request.cookies.get('stellio_csrf') != csrf_token:
        response.set_cookie('stellio_csrf', csrf_token, httponly=False,
                             samesite='Lax', max_age=60 * 60 * 24 * 30)
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'same-origin')
    response.headers.setdefault(
        'Content-Security-Policy',
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob: http: https:; "
        "connect-src 'self' http: https: ws: wss: blob: data:; "
        "media-src 'self' http: https:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'self'"
    )
    return response

@app.errorhandler(413)
def _handle_payload_too_large(e):
    return jsonify({"error": "Requête trop volumineuse"}), 413

@app.errorhandler(500)
def _handle_internal_error(e):
    app_logger.error(f"[500] Erreur interne non gérée: {e}")
    return jsonify({"error": "Erreur interne du serveur"}), 500

SUPPORTED_EXTENSIONS = {'.stl', '.3mf', '.obj'}
SUPPORTED_3D_EXTS = {'.stl', '.obj', '.3mf', '.step', '.stp', '.iges', '.igs', '.amf'}


class UnsafeArchiveError(Exception):
    pass

def _assert_safe_member_path(member_name, target_dir):
    if not member_name:
        return
    normalized = member_name.replace('\\', '/')
    if normalized.startswith('/') or (len(normalized) > 1 and normalized[1] == ':'):
        raise UnsafeArchiveError(f"Entrée d'archive avec chemin absolu refusée: {member_name}")
    real_target = os.path.realpath(target_dir)
    dest = os.path.realpath(os.path.join(target_dir, normalized))
    if dest != real_target and not dest.startswith(real_target + os.sep):
        raise UnsafeArchiveError(f"Entrée d'archive suspecte (path traversal) refusée: {member_name}")

def safe_extract_zip(zf, target_dir):
    for name in zf.namelist():
        _assert_safe_member_path(name, target_dir)
    zf.extractall(target_dir)

def safe_extract_tar(tar_ref, target_dir):
    real_target = os.path.realpath(target_dir)
    for member in tar_ref.getmembers():
        _assert_safe_member_path(member.name, target_dir)
        if member.issym() or member.islnk():
            link_dest = os.path.realpath(os.path.join(target_dir, os.path.dirname(member.name), member.linkname))
            if link_dest != real_target and not link_dest.startswith(real_target + os.sep):
                raise UnsafeArchiveError(f"Lien symbolique suspect refusé: {member.name} -> {member.linkname}")
    try:
        tar_ref.extractall(target_dir, filter='data')
    except TypeError:
        tar_ref.extractall(target_dir)

def safe_extract_rar(rf, target_dir):
    for name in rf.namelist():
        _assert_safe_member_path(name, target_dir)
    rf.extractall(target_dir)

def safe_extract_7z(z, target_dir):
    names = list(z.getnames()) if hasattr(z, 'getnames') else []
    for name in names:
        _assert_safe_member_path(name, target_dir)
    z.extractall(path=target_dir)


ARCHIVE_VIRTUAL_SEP = '::'
IN_MEMORY_ARCHIVE_EXTS = {'.zip', '.7z'}

def is_virtual_archive_path(path):
    return bool(path) and ARCHIVE_VIRTUAL_SEP in path

def split_virtual_archive_path(virtual_path):
    archive_path, _, internal_path = virtual_path.partition(ARCHIVE_VIRTUAL_SEP)
    return archive_path, internal_path

def make_virtual_archive_path(archive_path, internal_path):
    return f"{archive_path}{ARCHIVE_VIRTUAL_SEP}{internal_path}"

def list_archive_3d_entries(archive_path):
    ext = os.path.splitext(archive_path)[1].lower()
    entries = []
    try:
        if ext == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    inner_name = info.filename
                    inner_ext = os.path.splitext(inner_name)[1].lower()
                    if inner_ext in SUPPORTED_EXTENSIONS:
                        entries.append({
                            'internal_path': inner_name,
                            'name': os.path.basename(inner_name) or inner_name,
                            'extension': inner_ext,
                            'size': info.file_size
                        })
        elif ext == '.7z':
            import py7zr
            with py7zr.SevenZipFile(archive_path, mode='r') as zf:
                for info in zf.list():
                    if getattr(info, 'is_directory', False):
                        continue
                    inner_name = info.filename
                    inner_ext = os.path.splitext(inner_name)[1].lower()
                    if inner_ext in SUPPORTED_EXTENSIONS:
                        entries.append({
                            'internal_path': inner_name,
                            'name': os.path.basename(inner_name) or inner_name,
                            'extension': inner_ext,
                            'size': getattr(info, 'uncompressed', 0) or 0
                        })
    except ImportError:
        app_logger.info(f"[ARCHIVE] Module 'py7zr' manquant, {os.path.basename(archive_path)} ignoré")
    except Exception as e:
        app_logger.info(f"[ARCHIVE] Erreur lecture {os.path.basename(archive_path)}: {e}")
    return entries

def read_archive_entry_bytes(archive_path, internal_path):
    ext = os.path.splitext(archive_path)[1].lower()
    if ext == '.zip':
        with zipfile.ZipFile(archive_path, 'r') as zf:
            return zf.read(internal_path)
    elif ext == '.7z':
        import py7zr
        with py7zr.SevenZipFile(archive_path, mode='r') as zf:
            extracted = zf.read(targets=[internal_path])
            entry = extracted.get(internal_path)
            if entry is None:
                for k, v in extracted.items():
                    if k.replace('\\', '/') == internal_path.replace('\\', '/'):
                        entry = v
                        break
            if entry is None:
                raise FileNotFoundError(internal_path)
            return entry.read()
    raise ValueError(f"Format d'archive non supporté pour lecture directe: {ext}")


def get_cache_key(sources):
    src_str = json.dumps(sorted([f"{s['id']}:{s['path']}:{s.get('config', '')}" for s in sources]), sort_keys=True)
    return hashlib.md5(src_str.encode()).hexdigest()

def load_file_cache():
    try:
        if not os.path.exists(CACHE_FILE):
            return None
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        if not isinstance(cache, dict) or 'timestamp' not in cache or 'files' not in cache:
            app_logger.info("[WARN] Cache invalide, suppression...")
            invalidate_cache()
            return None
        if time.time() - cache.get('timestamp', 0) > CACHE_DURATION:
            return None
        return cache.get('files')
    except json.JSONDecodeError as e:
        app_logger.info(f"[ERROR] Cache JSON corrompu: {e}")
        invalidate_cache()
        return None
    except Exception as e:
        app_logger.info(f"[WARN] Erreur lecture cache: {e}")
        return None

cache_file_lock = threading.Lock()


def _atomic_replace(tmp_path, dest_path, retries=5, delay=0.08):
    last_err = None
    for attempt in range(retries):
        try:
            os.replace(tmp_path, dest_path)
            return True
        except (PermissionError, OSError) as e:
            last_err = e
            time.sleep(delay)
    app_logger.info(f"[CACHE] Échec remplacement atomique après {retries} tentatives: {last_err}")
    try:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    except Exception:
        pass
    return False


def save_file_cache(files, sources):
    try:
        if not isinstance(files, list):
            app_logger.info(f"[ERROR] files n'est pas une liste: {type(files)}")
            return
        cache = {
            'timestamp': time.time(),
            'cache_key': get_cache_key(sources),
            'schema_version': CACHE_SCHEMA_VERSION,
            'files': files
        }
        with cache_file_lock:
            tmp_path = CACHE_FILE + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, separators=(',', ':'))
            _atomic_replace(tmp_path, CACHE_FILE)
    except Exception as e:
        app_logger.info(f"[WARN] Échec sauvegarde cache: {e}")

def invalidate_cache():
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
    except:
        pass


def _migrate_file_cache_schema():
    try:
        if not os.path.exists(CACHE_FILE):
            return
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        if not isinstance(cache, dict) or 'files' not in cache:
            return
        if cache.get('schema_version') == CACHE_SCHEMA_VERSION:
            return

        files = cache.get('files') or []
        to_patch = [f for f in files if (f.get('extension') or '').lower() == '.3mf'
                    and ('plate_count' not in f or 'multi_plate' not in f)]

        if to_patch:
            smb_sources_by_name = {}
            try:
                conn = get_db()
                rows = conn.execute("SELECT * FROM sources WHERE type = 'smb'").fetchall()
                conn.close()
                for row in rows:
                    s = dict(row)
                    config = json.loads(s.get('config') or '{}')
                    kwargs = {}
                    if config.get('username'):
                        kwargs['username'] = config['username']
                    if config.get('password'):
                        kwargs['password'] = config['password']
                    smb_sources_by_name[s['name']] = kwargs
            except Exception as e:
                app_logger.info(f"[CACHE] Migration: lecture sources SMB impossible ({e}), fichiers réseau ignorés")

            patched = 0
            for f in to_patch:
                path = f.get('path', '')
                try:
                    is_smb = path.startswith('//') or path.startswith('\\\\')
                    if is_smb:
                        kwargs = smb_sources_by_name.get(f.get('source'))
                        if kwargs is None:
                            continue
                        smb_path = path.replace('\\\\', '//').replace('\\', '/')
                        with smbclient.open_file(smb_path, mode='rb', **kwargs) as smb_f:
                            plate_count = get_3mf_plate_count(smb_f)
                    else:
                        if not os.path.exists(path):
                            continue
                        plate_count = get_3mf_plate_count(path)
                    f['plate_count'] = plate_count
                    f['multi_plate'] = plate_count > 1
                    patched += 1
                except Exception:
                    continue

            if patched:
                app_logger.info(
                    f"[CACHE] Migration schéma v{CACHE_SCHEMA_VERSION} : {patched}/{len(to_patch)} "
                    f"fichier(s) .3mf mis à jour (détection plateaux multiples)."
                )

        cache['schema_version'] = CACHE_SCHEMA_VERSION
        with cache_file_lock:
            tmp_path = CACHE_FILE + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, separators=(',', ':'))
            _atomic_replace(tmp_path, CACHE_FILE)
    except Exception as e:
        app_logger.info(f"[CACHE] Migration schéma échouée, cache invalidé par précaution: {e}")
        invalidate_cache()


def _backfill_multiplate_tags():
    try:
        if not os.path.exists(CACHE_FILE):
            return
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        if not isinstance(cache, dict):
            return
        if cache.get('multiplate_tags_backfilled'):
            return

        files = cache.get('files') or []
        multi_plate_paths = [
            (f.get('path') or '').replace('\\', '/')
            for f in files
            if f.get('multi_plate') and f.get('path')
        ]

        if multi_plate_paths:
            conn = get_db()
            try:
                tag_id = _get_or_create_tag(conn, MULTI_PLATE_TAG_NAME)
                if tag_id:
                    tagged = 0
                    for path in multi_plate_paths:
                        try:
                            conn.execute(
                                "INSERT OR IGNORE INTO file_tags (file_path, tag_id) VALUES (?, ?)",
                                (path, tag_id)
                            )
                            tagged += 1
                        except Exception:
                            continue
                    conn.commit()
                    app_logger.info(
                        f"[TAGS] Rattrapage 'Multi plateaux' : {tagged}/{len(multi_plate_paths)} fichier(s) tagué(s)."
                    )
            finally:
                conn.close()

        cache['multiplate_tags_backfilled'] = True
        with cache_file_lock:
            tmp_path = CACHE_FILE + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, separators=(',', ':'))
            _atomic_replace(tmp_path, CACHE_FILE)
    except Exception as e:
        app_logger.info(f"[TAGS] Rattrapage 'Multi plateaux' échoué (sera retenté au prochain démarrage): {e}")


active_downloads = {}
cancelled_downloads = set()
scan_state = {
    'new_batch': [],
    'status': 'idle',
    'found': 0,
    'total_scanned': 0
}

def mark_download_complete_and_refresh_thumbnail(dest_path):
    normalized = dest_path.replace('\\', '/')
    currently_downloading_paths.discard(normalized)
    try:
        thumb_filename = hashlib.md5(normalized.encode()).hexdigest()
        thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        ignored_files_cache.pop(normalized, None)
        _release_thumb_inflight(dest_path)
        _queue_thumb_task(dest_path, thumb_path, priority='high')
    except Exception as e:
        app_logger.warning(f"[Download] Impossible de replanifier la miniature pour {dest_path}: {e}")

def process_generation_queue():
    global is_generation_running
    if is_generation_running:
        return
    is_generation_running = True

    def thumb_worker(worker_id):
        _lower_thread_priority()
        app_logger.info(f"[BACKGROUND] Générateur lazy #{worker_id} démarré")
        processed_count = 0
        consecutive_errors = 0
        while True:
            try:
                task = thumb_generation_queue.get(timeout=1)
            except queue.Empty:
                time.sleep(0.5)
                continue
            try:
                file_path = task.get('path')
                thumb_path = task.get('thumb_path')
                if _is_ignored_recently(file_path):
                    app_logger.info(f"[SKIP] Fichier déjà ignoré (retenté dans <10 min): {os.path.basename(file_path)}")
                    time.sleep(0.05)
                    continue
                if file_path.replace('\\', '/') in currently_downloading_paths:
                    app_logger.info(f"[SKIP] Téléchargement en cours, miniature différée: {os.path.basename(file_path)}")
                    continue
                is_smb = file_path.startswith('//') or file_path.startswith('\\\\')
                is_virtual = is_virtual_archive_path(file_path)
                file_accessible = False
                smb_error = None
                if is_virtual:
                    archive_path, _internal = split_virtual_archive_path(file_path)
                    file_accessible = os.path.exists(archive_path)
                elif not is_smb:
                    file_accessible = os.path.exists(file_path)
                else:
                    try:
                        smb_path = file_path.replace('\\\\', '//').replace('\\', '/')
                        smbclient.stat(smb_path, connection_timeout=8)
                        file_accessible = True
                    except Exception as e:
                        file_accessible = False
                        smb_error = e
                if not file_accessible:
                    app_logger.info(f"[SKIP] Fichier inaccessible: {file_path}" + (f" ({smb_error})" if smb_error else ""))
                    ignored_files_cache[file_path] = time.time()
                    consecutive_errors += 1
                    if consecutive_errors > 10:
                        app_logger.info(f"[ABORT #{worker_id}] Trop d'erreurs, pause 60s...")
                        time.sleep(60)
                        consecutive_errors = 0
                    continue
                if not os.path.exists(thumb_path):
                    app_logger.info(f"[GENERATING #{worker_id}] {os.path.basename(file_path)}")
                    success = False
                    timed_out = False
                    timeout_s = get_thumb_timeout(file_path)
                    try:
                        success = generate_thumbnail_pyrender(file_path, thumb_path, timeout_s=timeout_s)
                    except Exception as render_err:
                        app_logger.warning(f"[ERROR #{worker_id}] Génération {os.path.basename(file_path)}: {render_err}")

                    if success:
                        processed_count += 1
                        consecutive_errors = 0
                        update_cache_thumb_status(file_path, True)
                        _thumb_session_note_result(os.path.basename(file_path), file_path, True)
                    else:
                        app_logger.info(f"[FALLBACK] Création miniature fallback pour {os.path.basename(file_path)}")
                        create_fallback_thumbnail(thumb_path)
                        update_cache_thumb_status(file_path, True, is_fallback=True)
                        consecutive_errors = 0
                        reason = 'timeout' if timed_out else 'error'
                        thumb_failure_notifications.put({
                            'name': os.path.basename(file_path),
                            'path': file_path,
                            'reason': reason
                        })
                        _thumb_session_note_result(os.path.basename(file_path), file_path, False, reason)
                    if processed_count and processed_count % 10 == 0:
                        app_logger.info(f"[STATS #{worker_id}] {processed_count} miniatures générées")
                    time.sleep(0.8)
                if consecutive_errors > 5:
                    app_logger.info(f"[PAUSE #{worker_id}] Trop d'erreurs consécutives, pause 30s...")
                    time.sleep(30)
                    consecutive_errors = 0
            except Exception as e:
                app_logger.info(f"[BACKGROUND ERROR #{worker_id}] {e}")
                time.sleep(2)
            finally:
                if 'file_path' in locals() and file_path:
                    _release_thumb_inflight(file_path)
                thumb_generation_queue.task_done()
                if thumb_generation_queue.empty():
                    _thumb_session_maybe_finish()

    def scan_and_metadata_worker():
        _lower_thread_priority()
        while True:
            try:
                if not metadata_generation_queue.empty():
                    task = metadata_generation_queue.get(timeout=1)
                    file_path = task.get('path')
                    app_logger.info(f"[ANALYZING] {os.path.basename(file_path)}")
                    analyze_3d_file(file_path)
                    metadata_generation_queue.task_done()
                    time.sleep(0.2)
                    continue

                conn = get_db()
                try:
                    sources = conn.execute("SELECT * FROM sources").fetchall()
                finally:
                    conn.close()
                for source in sources:
                    if source['type'] == 'folder' and os.path.exists(source['path']):
                        for root, dirs, files in os.walk(source['path']):
                            for f in sorted(files, key=str.lower):
                                if f.lower().endswith(('.stl', '.obj', '.3mf')):
                                    file_path = os.path.join(root, f).replace('\\', '/')
                                    if _is_ignored_recently(file_path):
                                        continue
                                    normalized_path = file_path
                                    thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()
                                    thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')
                                    if not os.path.exists(thumb_path):
                                        _queue_thumb_task(file_path, thumb_path, priority='low')
                time.sleep(90)
            except queue.Empty:
                time.sleep(2)
            except Exception as e:
                app_logger.info(f"[BACKGROUND ERROR SCAN] {e}")
                time.sleep(5)

    def thumbnail_coverage_supervisor():
        _lower_thread_priority()
        time.sleep(15)  
        app_logger.info("[THUMBS] Superviseur de couverture démarré")
        while True:
            try:
                result = reconcile_thumbnails_with_disk()
                total = result.get('total', 0)
                with_thumb = result.get('with_thumb', 0)
                requeued = result.get('requeued', 0)
                if total > 0:
                    app_logger.info(
                        f"[THUMBS] Couverture: {with_thumb}/{total} miniature(s)"
                        + (f" — {requeued} remise(s) en file" if requeued else "")
                    )
                if requeued > 0 or not thumb_generation_queue.empty():
                    time.sleep(20)
                else:
                    time.sleep(60)
            except Exception as e:
                app_logger.info(f"[THUMBS] Erreur superviseur de couverture: {e}")
                time.sleep(30)

    for i in range(NUM_THUMB_WORKERS):
        threading.Thread(target=thumb_worker, args=(i,), daemon=True).start()
    threading.Thread(target=scan_and_metadata_worker, daemon=True).start()
    threading.Thread(target=thumbnail_coverage_supervisor, daemon=True).start()

    app_logger.info(f"[BACKGROUND] File d'attente lazy active ({NUM_THUMB_WORKERS} workers en parallèle)")


def _get_transformed_scene_geometries(scene, node_filter=None):
    out = []
    try:
        for node_name in scene.graph.nodes_geometry:
            if node_filter is not None:
                candidate_ids = {str(node_name), str(node_name).split('/')[-1]}
                if not (candidate_ids & node_filter):
                    continue
            transform, geom_name = scene.graph[node_name]
            geom = scene.geometry.get(geom_name)
            if geom is None or not hasattr(geom, 'vertices') or len(geom.vertices) == 0:
                continue
            if transform is not None and not np.allclose(transform, np.eye(4)):
                geom = geom.copy()
                geom.apply_transform(transform)
            out.append(geom)
    except Exception as e:
        app_logger.debug(f"[3MF] Extraction géométries transformées échouée: {e}")
    return out

def _concatenate_filtering_outliers(geoms):
    if not geoms:
        return None
    if len(geoms) == 1:
        return geoms[0]

    info = []
    for g in geoms:
        try:
            centroid = g.centroid
            n_verts = len(g.vertices)
            if n_verts < 4:
                continue
            info.append((g, centroid, n_verts))
        except Exception:
            continue

    if not info:
        return trimesh.util.concatenate(geoms)

    info.sort(key=lambda x: x[2], reverse=True)
    main_centroid = info[0][1]
    ref_scale = np.linalg.norm(info[0][0].extents) or 1.0

    kept = []
    for g, centroid, n_verts in info:
        dist_to_main = np.linalg.norm(centroid - main_centroid)
        if dist_to_main <= ref_scale * 5:
            kept.append(g)

    if not kept:
        kept = [info[0][0]]

    try:
        return trimesh.util.concatenate(kept)
    except Exception:
        return kept[0]

def _parse_3mf_plate_object_ids(source):
    try:
        is_bytes = isinstance(source, (bytes, bytearray))
        zip_source = io.BytesIO(source) if is_bytes else source
        with zipfile.ZipFile(zip_source, 'r') as zf:
            settings_path = next((n for n in zf.namelist() if n.lower().endswith('model_settings.config')), None)
            if not settings_path:
                return None
            with zf.open(settings_path) as f:
                tree = _safe_xml_parse(f)
                root = tree.getroot()
                plates = {}
                for i, plate_el in enumerate(root.findall('.//plate')):
                    plater_id = None
                    for meta in plate_el.findall('metadata'):
                        if meta.get('key') == 'plater_id':
                            plater_id = meta.get('value')
                            break
                    if not plater_id:
                        plater_id = str(i + 1)
                    obj_ids = set()
                    for inst in plate_el.findall('.//model_instance'):
                        for meta in inst.findall('metadata'):
                            if meta.get('key') == 'object_id':
                                obj_ids.add(meta.get('value'))
                    if obj_ids:
                        plates[plater_id] = obj_ids
                return plates if len(plates) > 1 else None
    except Exception:
        return None


def get_3mf_plate_count(source):
    plates = _parse_3mf_plate_object_ids(source)
    return len(plates) if plates else 1


def _resolve_3mf_plate_mesh(source, wanted_ids):
    try:
        is_bytes = isinstance(source, (bytes, bytearray))
        zip_source = io.BytesIO(source) if is_bytes else source
        with zipfile.ZipFile(zip_source, 'r') as zf:
            all_names = zf.namelist()
            model_files = [n for n in all_names if n.lower().endswith('.model')]
            if not model_files:
                return None

            ns = {'ns': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
            NS_PROD = 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'

            def _find(el, tag):
                found = el.find(f'ns:{tag}', ns)
                return found if found is not None else el.find(tag)

            def _findall(el, tag):
                found = el.findall(f'ns:{tag}', ns)
                return found if found else el.findall(tag)

            def _get_path_attr(el):
                return el.get(f'{{{NS_PROD}}}path') or el.get('path')

            def _resolve_part_name(raw_path, referer):
                if not raw_path:
                    return None
                candidate = raw_path.lstrip('/')
                for n in all_names:
                    if n.lower() == candidate.lower():
                        return n
                base_dir = referer.rsplit('/', 1)[0] if '/' in referer else ''
                joined = (base_dir + '/' + candidate).lstrip('/') if base_dir else candidate
                for n in all_names:
                    if n.lower() == joined.lower():
                        return n
                return None

            def _parse_transform(s):
                if not s:
                    return np.eye(4)
                try:
                    vals = [float(x) for x in s.split()]
                    if len(vals) != 12:
                        return np.eye(4)
                    m = np.eye(4)
                    m[0, 0], m[1, 0], m[2, 0] = vals[0], vals[1], vals[2]
                    m[0, 1], m[1, 1], m[2, 1] = vals[3], vals[4], vals[5]
                    m[0, 2], m[1, 2], m[2, 2] = vals[6], vals[7], vals[8]
                    m[0, 3], m[1, 3], m[2, 3] = vals[9], vals[10], vals[11]
                    return m
                except Exception:
                    return np.eye(4)

            _tree_cache = {}
            _objs_cache = {}

            def _get_tree(model_path):
                if model_path not in _tree_cache:
                    try:
                        with zf.open(model_path) as xml_file:
                            _tree_cache[model_path] = _safe_xml_parse(xml_file).getroot()
                    except Exception:
                        _tree_cache[model_path] = None
                return _tree_cache[model_path]

            def _get_objects(model_path):
                if model_path not in _objs_cache:
                    root_el = _get_tree(model_path)
                    objs = {}
                    if root_el is not None:
                        for obj in (root_el.findall('.//ns:object', ns) or root_el.findall('.//object')):
                            oid = obj.get('id')
                            if oid and oid not in objs:
                                objs[oid] = obj
                    _objs_cache[model_path] = objs
                return _objs_cache[model_path]

            def _resolve(model_path, oid, transform, depth=0):
                out = []
                if depth > 8:
                    return out
                objs = _get_objects(model_path)
                if not objs or oid not in objs:
                    return out
                obj = objs[oid]

                obj_type = obj.get('type', 'model')
                mesh_el = _find(obj, 'mesh') if obj_type in ('model', 'solid', '') else None
                if mesh_el is not None:
                    verts_el = _find(mesh_el, 'vertices')
                    tris_el = _find(mesh_el, 'triangles')
                    if verts_el is not None and tris_el is not None:
                        vertices, faces = [], []
                        for v in list(verts_el):
                            try:
                                vertices.append([float(v.get('x', 0)),
                                                 float(v.get('y', 0)),
                                                 float(v.get('z', 0))])
                            except Exception:
                                pass
                        for t in list(tris_el):
                            try:
                                faces.append([int(t.get('v1', 0)),
                                              int(t.get('v2', 0)),
                                              int(t.get('v3', 0))])
                            except Exception:
                                pass
                        if vertices and faces:
                            varr = np.array(vertices, dtype=np.float64)
                            farr = np.array(faces, dtype=np.int32)
                            if not np.allclose(transform, np.eye(4)):
                                varr = (np.hstack([varr, np.ones((len(varr), 1))]) @ transform.T)[:, :3]
                            out.append((varr, farr))

                components_el = _find(obj, 'components')
                if components_el is not None:
                    for comp in _findall(components_el, 'component'):
                        comp_id = comp.get('objectid')
                        if not comp_id:
                            continue
                        comp_tf = _parse_transform(comp.get('transform'))
                        target_file = model_path
                        comp_path_raw = _get_path_attr(comp)
                        if comp_path_raw:
                            resolved_name = _resolve_part_name(comp_path_raw, model_path)
                            if resolved_name:
                                target_file = resolved_name
                        out.extend(_resolve(target_file, comp_id, transform @ comp_tf, depth + 1))
                return out

            preferred_root = next((n for n in model_files if n.lower() == '3d/3dmodel.model'), None)
            root_candidates = [preferred_root] if preferred_root else model_files

            all_parts = []
            found_build = False
            searched = set()
            for model_path in root_candidates + model_files:
                if model_path in searched:
                    continue
                searched.add(model_path)
                root_el = _get_tree(model_path)
                if root_el is None:
                    continue
                build_el = _find(root_el, 'build')
                if build_el is None:
                    continue
                items = _findall(build_el, 'item')
                if not items:
                    continue
                found_build = True
                for item in items:
                    item_id = item.get('objectid')
                    if not item_id or item_id not in wanted_ids:
                        continue
                    item_tf = _parse_transform(item.get('transform'))
                    target_file = model_path
                    item_path_raw = _get_path_attr(item)
                    if item_path_raw:
                        resolved_name = _resolve_part_name(item_path_raw, model_path)
                        if resolved_name:
                            target_file = resolved_name
                    all_parts.extend(_resolve(target_file, item_id, item_tf))
                if found_build:
                    break

            if all_parts:
                sub_meshes = [trimesh.Trimesh(vertices=v, faces=f, process=False) for v, f in all_parts]
                mesh = _concatenate_filtering_outliers(sub_meshes) if len(sub_meshes) > 1 else sub_meshes[0]
                if mesh is not None and not mesh.is_empty and len(mesh.vertices) > 0:
                    return mesh
        return None
    except Exception as e:
        app_logger.debug(f"[3MF] _resolve_3mf_plate_mesh échoué: {e}")
        return None


def load_3mf_mesh(source, plate_index=None):
    is_bytes = isinstance(source, (bytes, bytearray))
    display_name = "archive (mémoire)" if is_bytes else os.path.basename(source)

    plates = _parse_3mf_plate_object_ids(source)
    plate_object_ids = None
    if plates:
        plate_keys_sorted = sorted(plates.keys(), key=lambda k: (len(k), k))
        wanted_idx = (plate_index - 1) if plate_index else 0
        wanted_idx = max(0, min(wanted_idx, len(plate_keys_sorted) - 1))
        selected_key = plate_keys_sorted[wanted_idx]
        plate_object_ids = plates[selected_key]
        app_logger.info(
            f"[3MF] {len(plates)} plateaux détectés dans {display_name}, "
            f"rendu du plateau '{selected_key}' uniquement ({len(plate_object_ids)} objet(s))"
        )

        resolved_mesh = _resolve_3mf_plate_mesh(source, plate_object_ids)
        if resolved_mesh is not None:
            app_logger.info(f"[3MF] Plateau isolé via résolution XML directe ({len(resolved_mesh.vertices)} sommets)")
            return resolved_mesh
        app_logger.debug(f"[3MF] Résolution XML directe infructueuse pour {display_name}, repli sur trimesh")

    try:
        if is_bytes:
            loaded = trimesh.load(io.BytesIO(source), file_type='3mf')
        else:
            loaded = trimesh.load(source)

        if isinstance(loaded, trimesh.Scene):
            all_geoms = _get_transformed_scene_geometries(loaded)

            if plate_object_ids is not None:
                filtered_geoms = _get_transformed_scene_geometries(loaded, node_filter=plate_object_ids)

                if filtered_geoms:
                    mesh = _concatenate_filtering_outliers(filtered_geoms)
                    if mesh is not None and not mesh.is_empty and len(mesh.vertices) > 0:
                        app_logger.info(f"[3MF] Plateau isolé avec succès ({len(filtered_geoms)} géométrie(s))")
                        return mesh
                app_logger.debug(f"[3MF] Mapping plateau→géométrie impossible pour {display_name}, fusion complète en repli")

            if all_geoms:
                mesh = _concatenate_filtering_outliers(all_geoms)
                if mesh is not None and not mesh.is_empty and len(mesh.vertices) > 0:
                    return mesh
        elif loaded is not None and not loaded.is_empty and len(loaded.vertices) > 0:
            return loaded
    except Exception as e:
        app_logger.debug(f"[3MF] trimesh.load direct échoué pour {display_name}: {e}")

    def _parse_manual(filter_ids):
        try:
            zip_source = io.BytesIO(source) if is_bytes else source
            with zipfile.ZipFile(zip_source, 'r') as zf:
                model_files = [n for n in zf.namelist() if n.lower().endswith('.model')]
                model_files.sort(key=lambda n: (0 if '3D/' in n or '3d/' in n else 1, n))
                for model_path in model_files:
                    try:
                        with zf.open(model_path) as xml_file:
                            tree = _safe_xml_parse(xml_file)
                            xml_root = tree.getroot()
                            ns_uri = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
                            ns = {'ns': ns_uri}
                            meshes_data = []
                            for tag in ['.//ns:object', './/object']:
                                try:
                                    objects = xml_root.findall(tag, ns) if tag.startswith('.//ns:') else xml_root.findall(tag)
                                except Exception:
                                    objects = []
                                for obj in objects:
                                    obj_type = obj.get('type', 'model')
                                    if obj_type not in ('model', 'solid', ''):
                                        continue
                                    if filter_ids is not None and obj.get('id') not in filter_ids:
                                        continue
                                    mesh_el = (obj.find('ns:mesh', ns) or obj.find('mesh'))
                                    if mesh_el is None:
                                        continue
                                    verts_el = (mesh_el.find('ns:vertices', ns) or mesh_el.find('vertices'))
                                    tris_el  = (mesh_el.find('ns:triangles', ns) or mesh_el.find('triangles'))
                                    if verts_el is None or tris_el is None:
                                        continue
                                    vertices = []
                                    for v in list(verts_el):
                                        try:
                                            vertices.append([float(v.get('x', 0)),
                                                             float(v.get('y', 0)),
                                                             float(v.get('z', 0))])
                                        except Exception:
                                            pass
                                    faces = []
                                    for t in list(tris_el):
                                        try:
                                            faces.append([int(t.get('v1', 0)),
                                                          int(t.get('v2', 0)),
                                                          int(t.get('v3', 0))])
                                        except Exception:
                                            pass
                                    if vertices and faces:
                                        meshes_data.append((np.array(vertices, dtype=np.float64),
                                                            np.array(faces,    dtype=np.int32)))
                            if meshes_data:
                                sub_meshes = [trimesh.Trimesh(vertices=v, faces=f, process=False)
                                              for v, f in meshes_data]
                                mesh = _concatenate_filtering_outliers(sub_meshes) if len(sub_meshes) > 1 else sub_meshes[0]
                                if mesh is not None and not mesh.is_empty and len(mesh.vertices) > 0:
                                    return mesh
                    except Exception as e:
                        app_logger.debug(f"[3MF] Erreur parsing {model_path}: {e}")
                        continue
        except Exception as e:
            app_logger.warning(f"[3MF] Erreur extraction XML {display_name}: {e}")
        return None

    mesh = _parse_manual(plate_object_ids)
    if mesh is None and plate_object_ids is not None:
        app_logger.debug(f"[3MF] Filtrage du plateau vide pour {display_name}, repli sur tous les objets")
        mesh = _parse_manual(None)

    if mesh is not None:
        app_logger.info(f"[3MF] Mesh extrait via XML ({len(mesh.vertices)} sommets)")
        return mesh

    app_logger.warning(f"[3MF] ⚠️  Impossible de charger le mesh: {display_name}")
    return trimesh.Trimesh()


def _build_multiplate_overview_mesh(source, max_plates=12):
    try:
        display_name = "archive (mémoire)" if isinstance(source, (bytes, bytearray)) else os.path.basename(source)

        plates = _parse_3mf_plate_object_ids(source)
        if not plates:
            return None

        plate_keys_sorted = sorted(plates.keys(), key=lambda k: (len(k), k))[:max_plates]

        resolved = []
        for key in plate_keys_sorted:
            obj_ids = plates[key]
            mesh = _resolve_3mf_plate_mesh(source, obj_ids)
            if mesh is not None and not mesh.is_empty and len(mesh.vertices) > 0:
                resolved.append((key, mesh))
            else:
                app_logger.debug(f"[3MF] Vue d'ensemble : plateau '{key}' omis (résolution rapide infructueuse) pour {display_name}")

        if len(resolved) < 2:
            return None

        max_extent = 0.0
        for _, mesh in resolved:
            ext = mesh.bounds[1][:2] - mesh.bounds[0][:2]
            max_extent = max(max_extent, float(np.max(ext)))
        if max_extent <= 0:
            max_extent = 1.0
        cell_size = max_extent * 1.35

        grid_cols = max(1, int(math.ceil(math.sqrt(len(resolved)))))

        placed_meshes = []
        for i, (key, mesh) in enumerate(resolved):
            row, col = divmod(i, grid_cols)
            bbox_center = mesh.bounds.mean(axis=0)
            m = mesh.copy()
            m.apply_translation(-bbox_center)
            m.apply_translation([col * cell_size, -row * cell_size, 0])
            placed_meshes.append(m)

        overview = trimesh.util.concatenate(placed_meshes)
        app_logger.info(
            f"[3MF] Vue d'ensemble multi-plateaux : {len(resolved)}/{len(plates)} "
            f"plateau(x) assemblés côte à côte pour {display_name}"
        )
        return overview
    except Exception as e:
        app_logger.debug(f"[3MF] _build_multiplate_overview_mesh échoué: {e}")
        return None

def create_fallback_thumbnail(thumb_path, resolution=(768, 768)):
    try:
        logo_path = os.path.join(BASE_DIR, 'assets', 'logo-nom-stellio.png')
        img = Image.new('RGBA', resolution, (26, 29, 35, 255))
        draw = ImageDraw.Draw(img)
        center = (resolution[0] // 2, resolution[1] // 2)
        radius = min(resolution) // 3
        for r in range(radius, 0, -2):
            alpha = int(50 * (r / radius))
            draw.ellipse([
                center[0] - r, center[1] - r,
                center[0] + r, center[1] + r
            ], outline=(78, 161, 211, alpha), width=2)

        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert('RGBA')
                logo_size = int(min(resolution) * 0.6)
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                logo_pos = (center[0] - logo_size // 2, center[1] - logo_size // 2)
                img.paste(logo, logo_pos, logo)
            except Exception as e:
                app_logger.info(f"    Erreur chargement logo: {e}")
            _draw_fallback_cube(draw, center)
        else:
            _draw_fallback_cube(draw, center)

        draw.rectangle([0, 0, resolution[0]-1, resolution[1]-1],
                       outline=(60, 65, 75, 255), width=2)
        img_rgb = Image.new('RGB', resolution, (26, 29, 35))
        if img.mode == 'RGBA':
            img_rgb.paste(img, mask=img.split()[3])
        img_rgb.save(thumb_path, quality=90, optimize=True)
        return True
    except Exception as e:
        app_logger.info(f"    Erreur création fallback: {e}")
        try:
            img = Image.new('RGB', resolution, (40, 40, 40))
            draw = ImageDraw.Draw(img)
            draw.text((resolution[0]//2, resolution[1]//2), "✗",
                      fill=(150, 150, 150), anchor='mm', font_size=48)
            img.save(thumb_path)
            return True
        except:
            return False

def _draw_fallback_cube(draw, center):
    cube_size = 80
    cube_center = center
    draw.polygon([
        (cube_center[0], cube_center[1] - cube_size//2),
        (cube_center[0] + cube_size//2, cube_center[1]),
        (cube_center[0], cube_center[1] + cube_size//2),
        (cube_center[0] - cube_size//2, cube_center[1])
    ], fill=(78, 161, 211, 180), outline=(100, 180, 230, 255))

def generate_thumbnail_pyrender(stl_path, thumb_path, resolution=(768, 768), timeout_s=None):
    if timeout_s is None:
        timeout_s = get_thumb_timeout(stl_path)

    result = {}

    def _run():
        try:
            result['value'] = _generate_thumbnail_pyrender_impl(stl_path, thumb_path, resolution)
        except Exception as e:
            result['error'] = e

    worker = threading.Thread(target=_run, daemon=True, name="thumb-render-1shot")
    worker.start()
    worker.join(timeout=timeout_s)

    if worker.is_alive():
        app_logger.warning(
            f"[TIMEOUT] Rendu miniature trop long (> {timeout_s:.0f}s), "
            f"abandon et passage au fichier suivant: {os.path.basename(stl_path)}"
        )
        return False

    if 'error' in result:
        app_logger.warning(f"[ERROR] Rendu miniature {os.path.basename(stl_path)}: {result['error']}")
        return False

    return bool(result.get('value', False))


def _generate_thumbnail_pyrender_impl(stl_path, thumb_path, resolution=(768, 768)):
    try:
        is_smb = stl_path.startswith('//') or stl_path.startswith('\\\\')
        is_virtual = is_virtual_archive_path(stl_path)
        mesh = None
        tmp_path = None
        try:
            if is_virtual:
                archive_path, internal_path = split_virtual_archive_path(stl_path)
                try:
                    raw_bytes = read_archive_entry_bytes(archive_path, internal_path)
                    tmp_fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(internal_path)[1])
                    with os.fdopen(tmp_fd, 'wb') as tmp_file:
                        tmp_file.write(raw_bytes)
                except Exception as arch_err:
                    app_logger.warning(f"[ARCHIVE] Lecture impossible pour miniature ({internal_path}): {arch_err}")
                    return False
                file_to_load = tmp_path
            elif is_smb:
                smb_path = stl_path.replace('\\\\', '//').replace('\\', '/')
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        tmp_fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(stl_path)[1])
                        os.close(tmp_fd)
                        with smbclient.open_file(smb_path, 'rb', share_access='r') as smb_file:
                            with open(tmp_path, 'wb') as local_file:
                                while True:
                                    chunk = smb_file.read(8192)
                                    if not chunk:
                                        break
                                    local_file.write(chunk)
                        break
                    except Exception as smb_err:
                        if '0xc0000043' in str(smb_err) and attempt < max_retries - 1:
                            time.sleep(1)
                        if tmp_path and os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                        tmp_path = None
                        continue
                    raise
                file_to_load = tmp_path
            else:
                if not os.path.exists(stl_path):
                    return False
                file_to_load = stl_path

            ext = os.path.splitext(file_to_load)[1].lower()

            if ext == '.3mf':
                mesh = None
                if get_3mf_plate_count(file_to_load) > 1:
                    mesh = _build_multiplate_overview_mesh(file_to_load)
                if mesh is None:
                    mesh = load_3mf_mesh(file_to_load)
            elif ext == '.obj':
                mesh = trimesh.load(file_to_load, force='mesh', process=False)
            else:
                mesh = trimesh.load(file_to_load, force='mesh')

            if isinstance(mesh, trimesh.Scene):
                geoms = [m for m in mesh.geometry.values()
                         if hasattr(m, 'vertices') and len(m.vertices) > 0]
                if not geoms:
                    return False
                mesh = _concatenate_filtering_outliers(geoms)

            if mesh is None or mesh.is_empty or len(mesh.vertices) == 0:
                return False


            MAX_RENDER_FACES = 60000
            faces_before = len(mesh.faces)
            if faces_before > MAX_RENDER_FACES:
                try:
                    import fast_simplification
                    mesh = mesh.simplify_quadric_decimation(face_count=MAX_RENDER_FACES)
                    app_logger.info(
                        f"[RENDER] Mesh décimé {faces_before} → {len(mesh.faces)} faces "
                        f"({os.path.basename(stl_path)})"
                    )
                except Exception as simplify_err:
                    app_logger.info(
                        f"[RENDER] Décimation rapide indisponible ({simplify_err}), "
                        f"rendu du mesh complet ({faces_before} faces)"
                    )

            bbox_center = mesh.bounds.mean(axis=0)
            mesh.apply_translation(-bbox_center)
            rot_fix = tra.rotation_matrix(np.radians(-90), [1, 0, 0])
            mesh.apply_transform(rot_fix)

            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        'ignore', category=RuntimeWarning,
                        message='.*divide by zero encountered in divide.*'
                    )
                    warnings.filterwarnings(
                        'ignore', category=RuntimeWarning,
                        message='.*invalid value encountered in divide.*'
                    )
                    mesh.fix_normals()
            except Exception:
                pass

            try:
                import pyrender
                with pyrender_lock:
                    scene = pyrender.Scene(
                        bg_color=[0x1a / 255.0, 0x1d / 255.0, 0x23 / 255.0, 1.0],
                        ambient_light=[0x40 / 255.0 * 1.3, 0x40 / 255.0 * 1.3, 0x40 / 255.0 * 1.3]
                    )
                    material = pyrender.MetallicRoughnessMaterial(
                        baseColorFactor=[0x4e / 255.0, 0xa1 / 255.0, 0xd3 / 255.0, 1.0],
                        metallicFactor=0.0,
                        roughnessFactor=0.35
                    )
                    render_mesh = pyrender.Mesh.from_trimesh(mesh, material=material, smooth=True)
                    scene.add(render_mesh)

                    max_dim = np.linalg.norm(mesh.extents)
                    dist = max(max_dim * 1.8, 0.5)
                    elev_rad = np.radians(25)
                    azim_rad = np.radians(45)

                    cam_x =  dist * np.cos(elev_rad) * np.sin(azim_rad)
                    cam_y =  dist * np.sin(elev_rad)
                    cam_z =  dist * np.cos(elev_rad) * np.cos(azim_rad)

                    forward = -np.array([cam_x, cam_y, cam_z])
                    forward /= np.linalg.norm(forward)
                    up = np.array([0.0, 1.0, 0.0])
                    right = np.cross(forward, up)
                    if np.linalg.norm(right) < 1e-6:
                        up = np.array([0.0, 0.0, 1.0])
                        right = np.cross(forward, up)
                    right  /= np.linalg.norm(right)
                    up_true = np.cross(right, forward)

                    camera_pose = np.eye(4)
                    camera_pose[:3, 0] = right
                    camera_pose[:3, 1] = up_true
                    camera_pose[:3, 2] = -forward
                    camera_pose[:3, 3] = [cam_x, cam_y, cam_z]

                    camera = pyrender.PerspectiveCamera(yfov=np.pi / 4.0, aspectRatio=1.0)
                    scene.add(camera, pose=camera_pose)

                    headlight = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=2.2)
                    scene.add(headlight, pose=camera_pose)

                    ss = 1
                    render_w, render_h = resolution[0] * ss, resolution[1] * ss
                    global _persistent_renderer, _persistent_renderer_size
                    if _persistent_renderer is None or _persistent_renderer_size != (render_w, render_h):
                        if _persistent_renderer is not None:
                            try:
                                _persistent_renderer.delete()
                            except Exception:
                                pass
                        _persistent_renderer = pyrender.OffscreenRenderer(render_w, render_h)
                        _persistent_renderer_size = (render_w, render_h)
                    color, _ = _persistent_renderer.render(scene)

                img = Image.fromarray(color)
                if ss != 1:
                    img = img.resize(resolution, Image.Resampling.LANCZOS)
                img.save(thumb_path, quality=95, method=6)

                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                return True

            except (AttributeError, Exception) as render_err:
                err_str = str(render_err)
                if 'OSMesa' in err_str or 'Win32Platform' in err_str or 'osmesa' in err_str.lower():
                    app_logger.info(f"[FALLBACK] PyRender GPU non dispo → rendu CPU rapide pour {os.path.basename(stl_path)}")
                    return _generate_thumbnail_raster(mesh, thumb_path, resolution)
                app_logger.warning(f"[ERROR] Rendu pyrender {os.path.basename(stl_path)}: {render_err}")
                return _generate_thumbnail_raster(mesh, thumb_path, resolution)

        except Exception as load_err:
            app_logger.warning(f"[ERROR] Chargement mesh {os.path.basename(stl_path)}: {load_err}")
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return False

    except Exception as e:
        app_logger.error(f"[ERROR] generate_thumbnail_pyrender {os.path.basename(stl_path)}: {e}")
        return False

def _generate_thumbnail_raster(mesh, thumb_path, resolution=(768, 768)):
    try:
        vertices = mesh.vertices
        faces = mesh.faces
        if len(vertices) == 0 or len(faces) == 0:
            return False

        MAX_RASTER_FACES = 40000
        if len(faces) > MAX_RASTER_FACES:
            try:
                import fast_simplification
                mesh = mesh.simplify_quadric_decimation(face_count=MAX_RASTER_FACES)
                vertices = mesh.vertices
                faces = mesh.faces
            except Exception as simplify_err:
                app_logger.info(
                    f"[RASTER] Décimation rapide indisponible ({simplify_err}), "
                    f"repli sur le sous-échantillonnage par pas fixe"
                )
                stride = (len(faces) // MAX_RASTER_FACES) + 1
                faces = faces[::stride]

        ss = 3
        w, h = resolution[0] * ss, resolution[1] * ss

        camera_dir = np.array([1.0, 1.0, 1.0])
        camera_dir /= np.linalg.norm(camera_dir)
        forward = -camera_dir
        world_up = np.array([0.0, 1.0, 0.0])
        right = np.cross(forward, world_up)
        right /= np.linalg.norm(right)
        up = np.cross(right, forward)

        bbox_center = (vertices.min(axis=0) + vertices.max(axis=0)) / 2.0
        v = vertices - bbox_center
        cam_x = v @ right
        cam_y = v @ up
        cam_z = v @ forward

        extent = max(np.ptp(cam_x), np.ptp(cam_y), 1e-6)
        scale = (min(w, h) * 0.80) / extent
        px_all = (cam_x * scale) + w / 2.0
        py_all = (h / 2.0) - (cam_y * scale)

        v0 = vertices[faces[:, 0]]
        v1 = vertices[faces[:, 1]]
        v2 = vertices[faces[:, 2]]
        face_normals = np.cross(v1 - v0, v2 - v0)
        n_len = np.linalg.norm(face_normals, axis=1, keepdims=True)
        n_len[n_len == 0] = 1.0
        face_normals = face_normals / n_len

        face_height = (v0[:, 1] + v1[:, 1] + v2[:, 1]) / 3.0

        view_dot = face_normals @ forward
        visible_mask = view_dot < 0
        if visible_mask.any() and visible_mask.sum() < len(faces):
            faces = faces[visible_mask]
            face_normals = face_normals[visible_mask]
            face_height = face_height[visible_mask]

        if len(faces) == 0:
            return False

        AMBIENT = 0x40 / 255.0 * 1.3
        KEY_INTENSITY = 0.7
        SPECULAR_COLOR, SHININESS = (0x11 / 255.0), 120.0
        base_color = np.array([0x4e, 0xa1, 0xd3], dtype=np.float64)

        vertex_normals = mesh.vertex_normals
        smooth_normals = (
            vertex_normals[faces[:, 0]] + vertex_normals[faces[:, 1]] + vertex_normals[faces[:, 2]]
        )
        sn_len = np.linalg.norm(smooth_normals, axis=1, keepdims=True)
        sn_len[sn_len == 0] = 1.0
        smooth_normals = smooth_normals / sn_len

        n_dot_light = np.clip(-smooth_normals @ forward, 0.0, 1.0)
        shade = AMBIENT + KEY_INTENSITY * n_dot_light

        specular_term = SPECULAR_COLOR * np.power(n_dot_light, SHININESS)
        face_colors = np.clip(
            base_color[None, :] * shade[:, None] + specular_term[:, None] * 255.0,
            0, 255
        ).astype(np.uint8)

        avg_z = cam_z[faces].mean(axis=1)
        order = np.argsort(-avg_z)

        tri_px = px_all[faces]
        tri_py = py_all[faces]

        img = Image.new('RGB', (w, h), (26, 29, 35))
        draw = ImageDraw.Draw(img)
        for idx in order:
            poly = [
                (float(tri_px[idx, 0]), float(tri_py[idx, 0])),
                (float(tri_px[idx, 1]), float(tri_py[idx, 1])),
                (float(tri_px[idx, 2]), float(tri_py[idx, 2])),
            ]
            color = tuple(int(c) for c in face_colors[idx])
            draw.polygon(poly, fill=color, outline=color)

        if ss != 1:
            img = img.resize(resolution, Image.Resampling.LANCZOS)

        img.save(thumb_path, quality=92, method=6)
        return True
    except Exception as e:
        app_logger.warning(f"[ERROR] Rendu rapide (raster) {os.path.basename(thumb_path)}: {e}")
        return False

def _generate_thumbnail_matplotlib(mesh, thumb_path, resolution=(768, 768)):
    with matplotlib_render_lock:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection
            import numpy as np

            fig = plt.figure(figsize=(resolution[0]/100, resolution[1]/100), dpi=100, facecolor='#1a1d23')
            ax = fig.add_subplot(111, projection='3d', facecolor='#1a1d23')

            vertices = mesh.vertices
            faces = mesh.faces
            if len(vertices) == 0 or len(faces) == 0:
                plt.close(fig)
                return False

            vertices_normalized = vertices.copy()
            vertices_normalized -= vertices_normalized.mean(axis=0)
            max_range = np.max(np.ptp(vertices_normalized, axis=0))
            if max_range > 0:
                vertices_normalized /= max_range

            try:
                face_normals = mesh.face_normals
            except Exception:
                face_normals = None

            base_color = np.array([0.30, 0.63, 0.83])
            if face_normals is not None and len(face_normals) == len(faces):
                light_dir = np.array([0.4, 0.6, 0.7])
                light_dir = light_dir / np.linalg.norm(light_dir)
                intensity = np.clip(face_normals @ light_dir, 0.0, 1.0)
                shade = 0.45 + 0.55 * intensity
                face_colors = np.clip(base_color[None, :] * shade[:, None], 0.0, 1.0)
            else:
                face_colors = np.tile(base_color, (len(faces), 1))

            tri = Poly3DCollection(
                vertices_normalized[faces],
                facecolors=face_colors,
                edgecolors=face_colors,
                linewidths=0.15,
                antialiased=True,
                alpha=1.0
            )
            ax.add_collection3d(tri)

            ax.set_xlim([-0.6, 0.6])
            ax.set_ylim([-0.6, 0.6])
            ax.set_zlim([-0.6, 0.6])
            ax.set_box_aspect([1, 1, 1])
            ax.view_init(elev=25, azim=45)
            ax.set_axis_off()
            ax.grid(False)

            plt.savefig(thumb_path, bbox_inches='tight', pad_inches=0, facecolor='#1a1d23', dpi=100)
            plt.close(fig)
            return True
        except Exception as e:
            app_logger.info(f"[ERROR] Fallback matplotlib: {e}")
            return False


def analyze_3d_file(file_path):
    try:
        mesh = trimesh.load(file_path, force='mesh')
        if isinstance(mesh, trimesh.Scene):
            geoms = [m for m in mesh.geometry.values() if hasattr(m, 'vertices') and len(m.vertices) > 0]
            if not geoms:
                return None
            mesh = trimesh.util.concatenate(geoms)

        if mesh.is_empty or len(mesh.vertices) == 0:
            return None

        bounds = mesh.bounds
        dimensions = bounds[1] - bounds[0]
        volume_cm3 = abs(mesh.volume) / 1000 if mesh.volume else 0
        surface_cm2 = mesh.area / 100 if mesh.area else 0
        triangle_count = len(mesh.faces)

        densities = {'pla': 1.24, 'petg': 1.27, 'abs': 1.04, 'tpu': 1.21, 'nylon': 1.14}
        weights = {mat: round(volume_cm3 * dens, 1) for mat, dens in densities.items()}

        volume_mm3 = abs(mesh.volume) if mesh.volume else 0
        flow_rate = 10
        if volume_mm3 > 0 and flow_rate > 0:
            estimated_time_seconds = volume_mm3 / flow_rate
            complexity_factor = 1 + (triangle_count / 100000)
            estimated_time_seconds *= complexity_factor
        else:
            estimated_time_seconds = 0

        hours = int(estimated_time_seconds // 3600)
        minutes = int((estimated_time_seconds % 3600) // 60)

        already_handled = file_path.replace('\\', '/') in repair_ignored_cache

        try:
            winding_ok = bool(mesh.is_winding_consistent)
        except Exception:
            winding_ok = True

        mesh_is_sane = mesh.is_watertight and winding_ok

        return {
            'dimensions': {'x': round(dimensions[0], 1), 'y': round(dimensions[1], 1), 'z': round(dimensions[2], 1)},
            'volume_cm3': round(volume_cm3, 2),
            'surface_cm2': round(surface_cm2, 2),
            'triangle_count': triangle_count,
            'weights': weights,
            'estimated_time': {'seconds': int(estimated_time_seconds), 'formatted': f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"},
            'is_manifold': mesh_is_sane or already_handled,
            'needs_repair': (not mesh_is_sane) and not already_handled,
            'is_empty': mesh.is_empty,
            'estimate_source': 'geometric'
        }
    except Exception as e:
        app_logger.info(f"[WARN] Erreur analyse 3D {file_path}: {e}")
        return None

def get_cached_3d_analysis(file_path):
    normalized_path = file_path.replace('\\', '/')
    cache_key = f"analysis_{hashlib.md5(normalized_path.encode()).hexdigest()}"
    ts_key = f"{cache_key}_ts"

    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            if cache_key in cache and ts_key in cache:
                age = time.time() - cache[ts_key]
                if cache[cache_key] == "FAILED":
                    if age < 600:
                        return None
                elif age < 3600:
                    return cache[cache_key]
        except Exception:
            pass

    metadata = analyze_3d_file(file_path)

    try:
        with cache_file_lock:
            cache_data = {}
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            cache_data[cache_key] = metadata if metadata else "FAILED"
            cache_data[ts_key] = time.time()
            tmp_path = CACHE_FILE + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            _atomic_replace(tmp_path, CACHE_FILE)
    except Exception:
        pass

    return metadata


@app.route('/api/files/analyze', methods=['POST'])
@login_required
def api_analyze_file():
    data = request.json
    file_path = data.get('path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Fichier non trouvé"}), 404
    if not _is_path_within_sources(file_path, session['user_id']):
        app_logger.warning(f"[SECURITY] Tentative d'analyse hors sources: {file_path}")
        return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

    normalized_path = file_path.replace('\\', '/')
    cache_key = f"analysis_{hashlib.md5(normalized_path.encode()).hexdigest()}"

    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            ts_key = f"{cache_key}_ts"
            if cache_key in cache and ts_key in cache:
                age = time.time() - cache[ts_key]
                if cache[cache_key] == "FAILED":
                    if age < 600:
                        return jsonify({"error": "Impossible d'analyser le fichier"}), 500
                elif age < 3600:
                    return jsonify({"success": True, "metadata": cache[cache_key], "cached": True})
        except:
            pass

    metadata = analyze_3d_file(file_path)
    if not metadata:
        try:
            with cache_file_lock:
                cache_data = {}
                if os.path.exists(CACHE_FILE):
                    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    cache_data[cache_key] = "FAILED"
                    cache_data[f"{cache_key}_ts"] = time.time()
                    tmp_path = CACHE_FILE + '.tmp'
                    with open(tmp_path, 'w', encoding='utf-8') as f:
                        json.dump(cache_data, f, indent=2, ensure_ascii=False)
                    _atomic_replace(tmp_path, CACHE_FILE)
        except:
            pass
        return jsonify({"error": "Impossible d'analyser le fichier"}), 500

    try:
        with cache_file_lock:
            cache_data = {}
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                cache_data[cache_key] = metadata
                cache_data[f"{cache_key}_ts"] = time.time()
                tmp_path = CACHE_FILE + '.tmp'
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2, ensure_ascii=False)
                _atomic_replace(tmp_path, CACHE_FILE)
    except:
        pass

    return jsonify({"success": True, "metadata": metadata, "cached": False})

@app.route('/')
def index():
    return send_file(os.path.join(BASE_DIR, 'index.html'))

@app.route('/api/auth/first-launch', methods=['GET'])
def api_first_launch():
    return jsonify({"first_launch": is_first_launch()})

_login_attempts = {}
_login_attempts_lock = threading.Lock()
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300

def _check_rate_limit(bucket, key):
    full_key = f"{bucket}:{(key or '').strip().lower()}"
    now = time.time()
    with _login_attempts_lock:
        attempts = [t for t in _login_attempts.get(full_key, []) if now - t < LOGIN_LOCKOUT_SECONDS]
        if attempts:
            _login_attempts[full_key] = attempts
        else:
            _login_attempts.pop(full_key, None)
        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            wait = int(LOGIN_LOCKOUT_SECONDS - (now - min(attempts)))
            return False, max(wait, 1)
    return True, 0

def _record_failed_attempt(bucket, key):
    full_key = f"{bucket}:{(key or '').strip().lower()}"
    with _login_attempts_lock:
        _login_attempts.setdefault(full_key, []).append(time.time())

def _clear_attempts(bucket, key):
    full_key = f"{bucket}:{(key or '').strip().lower()}"
    with _login_attempts_lock:
        _login_attempts.pop(full_key, None)

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    question_key = data.get('security_question_key', '').strip()
    question_custom = data.get('security_question_custom', '').strip()
    answer = data.get('security_answer', '')

    if not username or not password:
        return jsonify({"error": "Nom et mot de passe requis"}), 400
    if len(password) < 3:
        return jsonify({"error": "Mot de passe trop court"}), 400
    if question_key not in SECURITY_QUESTION_KEYS:
        return jsonify({"error": "Question secrète requise"}), 400
    if question_key == 'custom' and not question_custom:
        return jsonify({"error": "Veuillez préciser votre question personnalisée"}), 400
    if not normalize_answer(answer):
        return jsonify({"error": "Réponse à la question secrète requise"}), 400

    recovery_code = generate_recovery_code()
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO users
               (username, password_hash, recovery_code_hash,
                security_question_key, security_question_custom, security_answer_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, hash_pw_strong(password), hash_pw(recovery_code),
             question_key, question_custom if question_key == 'custom' else '', hash_answer(answer))
        )
        conn.commit()
        user = conn.execute("SELECT id, username FROM users WHERE username = ?", (username,)).fetchone()
        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({
            "message": "Compte créé",
            "user": {"id": user['id'], "username": user['username']},
            "recovery_code": recovery_code
        })
    except sqlite3.IntegrityError:
        return jsonify({"error": "Nom d'utilisateur déjà utilisé"}), 409
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    remember = bool(data.get('remember', False))

    allowed, wait_seconds = _check_rate_limit('login', username)
    if not allowed:
        return jsonify({"error": f"Trop de tentatives échouées. Réessayez dans {wait_seconds} secondes."}), 429

    conn = get_db()
    user = conn.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,)).fetchone()

    if user and verify_pw_strong(password, user['password_hash']):
        if _is_legacy_hash(user['password_hash']):
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_pw_strong(password), user['id']))
            conn.commit()
        conn.close()
        _clear_attempts('login', username)
        session.permanent = remember
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({"message": "Connecté", "user": {"id": user['id'], "username": user['username']}})
    conn.close()
    _record_failed_attempt('login', username)
    return jsonify({"error": "Identifiants invalides"}), 401

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"message": "Déconnecté"})

@app.route('/api/auth/me', methods=['GET'])
def api_me():
    if 'user_id' in session:
        return jsonify({"user": {"id": session['user_id'], "username": session['username']}})
    return jsonify({"error": "non authentifié"}), 401

@app.route('/api/auth/security-question', methods=['GET'])
def api_get_security_question():
    username = request.args.get('username', '').strip()
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT security_question_key, security_question_custom FROM users WHERE username = ?", (username,)
        ).fetchone()
    finally:
        conn.close()
    if not user or not user['security_question_key']:
        return jsonify({"error": "Utilisateur introuvable"}), 404
    return jsonify({
        "security_question_key": user['security_question_key'],
        "security_question_custom": user['security_question_custom'] or ''
    })

@app.route('/api/auth/recovery-code/regenerate', methods=['POST'])
@login_required
def api_regenerate_recovery_code():
    data = request.json or {}
    answer = data.get('security_answer', '')

    conn = get_db()
    user = conn.execute(
        "SELECT security_answer_hash FROM users WHERE id = ?", (session['user_id'],)
    ).fetchone()

    if not user or not user['security_answer_hash'] or not verify_answer(answer, user['security_answer_hash']):
        conn.close()
        return jsonify({"error": "Réponse à la question secrète incorrecte"}), 400

    new_code = generate_recovery_code()
    conn.execute("UPDATE users SET recovery_code_hash = ? WHERE id = ?", (hash_pw(new_code), session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({"recovery_code": new_code})

@app.route('/api/auth/reset-with-recovery', methods=['POST'])
def api_reset_with_recovery():
    data = request.json
    username = data.get('username', '').strip()
    recovery_code = data.get('recovery_code', '').strip().upper()
    answer = data.get('security_answer', '')
    new_password = data.get('password', '')

    if not username or not recovery_code or not normalize_answer(answer) or not new_password:
        return jsonify({"error": "Champs requis"}), 400
    if len(new_password) < 3:
        return jsonify({"error": "Mot de passe trop court"}), 400

    allowed, wait_seconds = _check_rate_limit('reset', username)
    if not allowed:
        return jsonify({"error": f"Trop de tentatives échouées. Réessayez dans {wait_seconds} secondes."}), 429

    conn = get_db()
    user = conn.execute(
        "SELECT id, recovery_code_hash, security_answer_hash FROM users WHERE username = ?", (username,)
    ).fetchone()

    valid = (
        user
        and user['recovery_code_hash'] and user['recovery_code_hash'] == hash_pw(recovery_code)
        and user['security_answer_hash'] and verify_answer(answer, user['security_answer_hash'])
    )
    if not valid:
        conn.close()
        _record_failed_attempt('reset', username)
        return jsonify({"error": "Nom d'utilisateur, code de récupération ou réponse invalide"}), 400

    _clear_attempts('reset', username)
    new_recovery_code = generate_recovery_code()
    conn.execute(
        "UPDATE users SET password_hash = ?, recovery_code_hash = ? WHERE id = ?",
        (hash_pw_strong(new_password), hash_pw(new_recovery_code), user['id'])
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Mot de passe réinitialisé", "recovery_code": new_recovery_code})


@app.route('/api/app-config', methods=['GET'])
@login_required
def api_app_config():
    return jsonify({
        "allowed_source_types": sorted(ALLOWED_SOURCE_TYPES),
        "headless": os.environ.get('STELLIO_HEADLESS', '').strip().lower() in ('1', 'true', 'yes')
    })


@app.route('/api/sources', methods=['GET'])
@login_required
def api_get_sources():
    conn = get_db()
    try:
        sources = conn.execute("SELECT * FROM sources WHERE user_id = ?", (session['user_id'],)).fetchall()
    finally:
        conn.close()
    return jsonify([dict(s) for s in sources])

@app.route('/api/sources', methods=['POST'])
@login_required
def api_add_source():
    data = request.json
    name = data.get('name', '').strip()
    src_type = data.get('type')
    path = data.get('path')
    config = json.dumps(data.get('config', {}))
    user_id = session['user_id']

    if not all([src_type, path]):
        return jsonify({"error": "Champs requis"}), 400

    if src_type not in ALLOWED_SOURCE_TYPES:
        return jsonify({"error": f"Type de source '{src_type}' désactivé sur ce serveur. Types autorisés : {', '.join(sorted(ALLOWED_SOURCE_TYPES))}"}), 403

    conn = get_db()
    if not name:
        name = f"Source {len(conn.execute('SELECT id FROM sources WHERE user_id=?', (user_id,)).fetchall()) + 1}"
    try:
        conn.execute("INSERT INTO sources (user_id, name, type, path, config) VALUES (?, ?, ?, ?, ?)",
                     (user_id, name, src_type, path, config))
        conn.commit()
        invalidate_cache()

        new_sources_list = [dict(s) for s in conn.execute(
            "SELECT * FROM sources WHERE user_id = ?", (user_id,)
        ).fetchall()]
        threading.Thread(
            target=_do_background_scan,
            args=(new_sources_list, user_id),
            kwargs={'blocking': True},
            daemon=True
        ).start()

        return jsonify({"message": "Source ajoutée"}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500
    finally:
        conn.close()

@app.route('/api/sources/drop', methods=['POST'])
@login_required
def api_add_sources_from_drop():
    data = request.json or {}
    paths = data.get('paths') or []
    user_id = session['user_id']

    DROPPABLE_FILE_EXTS = SUPPORTED_EXTENSIONS | IN_MEMORY_ARCHIVE_EXTS | {'.rar', '.step', '.stp', '.amf', '.ply'}

    added, skipped = [], []
    conn = get_db()
    try:
        existing_names = {r[0] for r in conn.execute("SELECT name FROM sources WHERE user_id=?", (user_id,)).fetchall()}
        for raw_path in paths:
            path = (raw_path or '').strip()
            if not path:
                continue
            if not os.path.exists(path):
                skipped.append({"path": path, "reason": "introuvable"})
                continue

            is_dir = os.path.isdir(path)
            if is_dir:
                src_type = 'folder'
            else:
                ext = os.path.splitext(path)[1].lower()
                if ext not in DROPPABLE_FILE_EXTS:
                    skipped.append({"path": path, "reason": f"extension {ext or '?'} non supportée"})
                    continue
                src_type = 'file'

            if src_type not in ALLOWED_SOURCE_TYPES:
                skipped.append({"path": path, "reason": f"type '{src_type}' désactivé sur ce serveur"})
                continue

            base_name = os.path.basename(path.rstrip('/\\')) or path
            name = base_name
            suffix = 2
            while name in existing_names:
                name = f"{base_name} ({suffix})"
                suffix += 1
            existing_names.add(name)

            try:
                conn.execute("INSERT INTO sources (user_id, name, type, path, config) VALUES (?, ?, ?, ?, ?)",
                             (user_id, name, src_type, path, '{}'))
                added.append({"path": path, "name": name, "type": src_type})
            except Exception as e:
                skipped.append({"path": path, "reason": str(e)})

        conn.commit()
    finally:
        conn.close()

    if added:
        invalidate_cache()
        conn2 = get_db()
        new_sources_list = [dict(s) for s in conn2.execute(
            "SELECT * FROM sources WHERE user_id = ?", (user_id,)
        ).fetchall()]
        conn2.close()
        threading.Thread(
            target=_do_background_scan,
            args=(new_sources_list, user_id),
            kwargs={'blocking': True},
            daemon=True
        ).start()

    return jsonify({"added": added, "skipped": skipped}), 200


@app.route('/api/sources/<int:source_id>', methods=['PUT'])
@login_required
def api_update_source(source_id):
    data = request.json
    new_name = data.get('name', '').strip()
    if not new_name:
        return jsonify({"error": "Nom requis"}), 400

    conn = get_db()
    try:
        conn.execute("UPDATE sources SET name = ? WHERE id = ? AND user_id = ?",
                     (new_name, source_id, session['user_id']))
        conn.commit()
        invalidate_cache()
    finally:
        conn.close()
    return jsonify({"message": "Source mise à jour"}), 200

@app.route('/api/sources/<int:source_id>', methods=['DELETE'])
@login_required
def api_delete_source(source_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM sources WHERE id = ? AND user_id = ?",
                     (source_id, session['user_id']))
        conn.commit()
        remaining_sources = [dict(s) for s in conn.execute(
            "SELECT * FROM sources WHERE user_id = ?", (session['user_id'],)
        ).fetchall()]
    finally:
        conn.close()
    invalidate_cache()

    def _rescan_after_delete(sources):
        acquired = _background_scan_running.acquire(blocking=True, timeout=10)
        if acquired:
            try:
                app_logger.info("[DELETE] Rescan post-suppression source...")
                all_files = []
                for source in sources:
                    try:
                        if source['type'] == 'folder':
                            all_files.extend(scan_local_folder(source['path']))
                        elif source['type'] == 'smb':
                            try:
                                smbclient.reset_connection_cache()
                            except Exception:
                                pass
                            unc_path = source['path'].replace('\\\\', '//').replace('\\', '/')
                            kwargs = {'connection_timeout': 8}
                            config = json.loads(source['config']) if source['config'] else {}
                            if config.get('username'):
                                kwargs['username'] = config['username']
                            if config.get('password'):
                                kwargs['password'] = config['password']
                            all_files.extend(scan_smb_folder_recursive(unc_path, '', kwargs, source['name']))
                    except Exception as e:
                        app_logger.warning(f"[DELETE] Erreur source {source.get('name')}: {e}")
                save_file_cache(all_files, sources)
                app_logger.info(f"[DELETE] Cache mis à jour : {len(all_files)} fichiers")
            finally:
                _background_scan_running.release()
        else:
            app_logger.warning("[DELETE] Lock background non acquis, cache invalidé sans rescan")

    threading.Thread(target=_rescan_after_delete, args=(remaining_sources,), daemon=True).start()
    return jsonify({"message": "Source supprimée"}), 200


@app.route('/api/accounts', methods=['GET'])
@login_required
def api_get_accounts():
    conn = get_db()
    try:
        accounts = conn.execute(
            "SELECT id, platform, email, api_key, created_at, last_login FROM account_credentials WHERE user_id = ?",
            (session['user_id'],)
        ).fetchall()
    finally:
        conn.close()

    accounts_list = [dict(a) for a in accounts]
    for acc in accounts_list:
        if acc.get('api_key'):
            acc['api_key'] = '••••••••'
    return jsonify(accounts_list)

@app.route('/api/accounts/<platform>', methods=['GET'])
@login_required
def api_get_account(platform):
    platform = platform.lower()
    conn = get_db()
    try:
        account = conn.execute(
            "SELECT id, platform, email, api_key, session_cookies, created_at, last_login FROM account_credentials WHERE user_id = ? AND platform = ?",
            (session['user_id'], platform)
        ).fetchone()
    finally:
        conn.close()

    if not account:
        return jsonify({"error": "Compte non trouvé"}), 404

    result = dict(account)
    if result.get('api_key'):
        result['api_key'] = '••••••••'
    if result.get('session_cookies'):
        result['session_cookies'] = '••••••••'
    return jsonify(result)

@app.route('/api/accounts/<platform>/key', methods=['GET'])
@login_required
def api_get_account_key(platform):
    platform = platform.lower()
    conn = get_db()
    try:
        account = conn.execute(
            "SELECT api_key FROM account_credentials WHERE user_id = ? AND platform = ?",
            (session['user_id'], platform)
        ).fetchone()
    finally:
        conn.close()

    if not account or not account['api_key']:
        return jsonify({"api_key": None}), 404

    try:
        clear_key = decrypt_account_secret(account['api_key'])
    except Exception as e:
        app_logger.warning(f"[Accounts] Échec déchiffrement clé API ({platform}): {e}")
        return jsonify({"api_key": None}), 500

    return jsonify({"api_key": clear_key})

@app.route('/api/accounts/thingiverse/validate', methods=['POST'])
@login_required
def validate_thingiverse_account():
    try:
        conn = get_db()
        account = conn.execute(
            "SELECT * FROM account_credentials WHERE user_id = ? AND platform = 'thingiverse'",
            (session['user_id'],)
        ).fetchone()
        conn.close()

        if not account:
            return jsonify({"connected": False, "error": "Aucun compte Thingiverse configuré"}), 404

        api_token = decrypt_account_secret(account['api_key'])
        if not api_token:
            return jsonify({"connected": False, "error": "Token API manquant"}), 400

        api_token = api_token.strip()
        app_logger.info(f"[THINGIVERSE] Test du token: {api_token[:10]}...")

        try:
            response = requests.get(
                'https://api.thingiverse.com/me',
                headers={
                    'Authorization': f'Bearer {api_token}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'Stellio-App/1.0'
                },
                timeout=10
            )
            app_logger.info(f"[THINGIVERSE] Endpoint api.thingiverse.com/me: Status {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if 'id' in data or 'username' in data:
                    conn = get_db()
                    conn.execute(
                        "UPDATE account_credentials SET last_login = CURRENT_TIMESTAMP WHERE user_id = ? AND platform = 'thingiverse'",
                        (session['user_id'],)
                    )
                    conn.commit()
                    conn.close()
                    return jsonify({
                        "connected": True,
                        "message": "Connecté à Thingiverse",
                        "username": data.get('public_name') or data.get('username') or 'Utilisateur'
                    })
            elif response.status_code == 401:
                return jsonify({"connected": False, "error": "Token invalide (401)"}), 401
            elif response.status_code == 404:
                app_logger.info("[THINGIVERSE] L'API officielle n'est plus disponible")
                conn = get_db()
                conn.execute(
                    "UPDATE account_credentials SET last_login = CURRENT_TIMESTAMP WHERE user_id = ? AND platform = 'thingiverse'",
                    (session['user_id'],)
                )
                conn.commit()
                conn.close()
                return jsonify({
                    "connected": True,
                    "message": "Token enregistré (API limitée)",
                    "warning": "L'API Thingiverse est limitée, certaines fonctionnalités peuvent ne pas être disponibles"
                })
        except requests.exceptions.RequestException as e:
            app_logger.info(f"[THINGIVERSE] Erreur connexion API: {e}")
        except json.JSONDecodeError as e:
            app_logger.info(f"[THINGIVERSE] Erreur parsing JSON: {e}")

        conn = get_db()
        conn.execute(
            "UPDATE account_credentials SET last_login = CURRENT_TIMESTAMP WHERE user_id = ? AND platform = 'thingiverse'",
            (session['user_id'],)
        )
        conn.commit()
        conn.close()

        return jsonify({
            "connected": True,
            "message": "Token enregistré (validation API indisponible)",
            "warning": "Impossible de valider le token via l'API, mais il sera utilisé pour les téléchargements"
        })

    except Exception as e:
        app_logger.info(f"[THINGIVERSE VALIDATE] Erreur: {e}")
        return jsonify({"connected": False, "error": str(e)}), 500

@app.route('/api/accounts', methods=['POST'])
@login_required
def api_save_account():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Données invalides"}), 400

        platform = data.get('platform', '').lower()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        api_key = (data.get('api_key') or '').strip()
        cookie_data = (data.get('cookie_data') or '').strip()

        if platform == 'thingiverse':
            if not api_key:
                return jsonify({"error": "Token API requis pour Thingiverse"}), 400
        elif platform and platform != 'thingiverse':
            if not email and not password:
                return jsonify({"error": "Email et/ou mot de passe requis"}), 400

        conn = get_db()
        try:
            password_enc = encrypt_password(password) if password else None
            api_key_enc = encrypt_password(api_key) if api_key else None
            cookie_data_enc = encrypt_password(cookie_data) if cookie_data else None

            conn.execute("""
                INSERT INTO account_credentials
                (user_id, platform, email, password_encrypted, api_key, session_cookies, last_login)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, platform) DO UPDATE SET
                    email = excluded.email,
                    password_encrypted = excluded.password_encrypted,
                    api_key = excluded.api_key,
                    session_cookies = excluded.session_cookies,
                    last_login = CURRENT_TIMESTAMP
            """, (
                session['user_id'],
                platform,
                email or None,
                password_enc,
                api_key_enc,
                cookie_data_enc,
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            conn.commit()
            app_logger.info(f"[ACCOUNT] Compte {platform} enregistré")
            return jsonify({"message": "Compte enregistré avec succès"}), 200
        except Exception as db_err:
            conn.rollback()
            app_logger.info(f"[DB] Erreur: {db_err}")
            return jsonify({"error": f"Erreur BD: {str(db_err)}"}), 500
        finally:
            conn.close()

    except Exception as e:
        app_logger.info(f"[ERROR] Erreur serveur: {e}")
        return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500

@app.route('/api/accounts/<platform>', methods=['DELETE'])
@login_required
def api_delete_account(platform):
    conn = get_db()
    try:
        conn.execute("DELETE FROM account_credentials WHERE user_id = ? AND platform = ?",
                     (session['user_id'], platform.lower()))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"message": "Compte supprimé"}), 200


@app.route('/api/file/mesh', methods=['GET'])
@login_required
def api_file_mesh():
    file_path = request.args.get('path', '').split('&t=')[0].strip()
    plate_index = request.args.get('plate', type=int)
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400

    file_path = file_path.replace('\\', '/')
    if '..' in file_path:
        return jsonify({"error": "Chemin invalide"}), 400

    if is_virtual_archive_path(file_path):
        archive_path, internal_path = split_virtual_archive_path(file_path)
        if not _is_path_within_sources(archive_path, session['user_id']):
            app_logger.warning(f"[SECURITY] Tentative de lecture mesh hors sources: {archive_path}")
            return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403
        if not os.path.exists(archive_path):
            app_logger.warning(f"[Viewer] Archive non trouvée: {archive_path}")
            return jsonify({"error": "Archive non trouvée"}), 404

        ext = os.path.splitext(internal_path)[1].lower()
        try:
            raw_bytes = read_archive_entry_bytes(archive_path, internal_path)
        except Exception as e:
            app_logger.warning(f"[Viewer] Lecture archive impossible {archive_path}::{internal_path}: {e}")
            return jsonify({"error": "Lecture de l'archive impossible"}), 500

        try:
            if ext == '.stl':
                buf = io.BytesIO(raw_bytes)
                buf.seek(0)
                return send_file(buf, mimetype='application/octet-stream',
                                 download_name=os.path.basename(internal_path))

            elif ext in ('.3mf', '.obj'):
                if ext == '.3mf':
                    mesh = load_3mf_mesh(raw_bytes, plate_index=plate_index)
                else:
                    mesh = trimesh.load(io.BytesIO(raw_bytes), file_type='obj', force='mesh')

                if isinstance(mesh, trimesh.Scene):
                    geoms = [m for m in mesh.geometry.values()
                             if hasattr(m, 'vertices') and len(m.vertices) > 0]
                    if not geoms:
                        return jsonify({"error": "Mesh vide"}), 422
                    mesh = _concatenate_filtering_outliers(geoms)

                if mesh is None or mesh.is_empty or len(mesh.vertices) == 0:
                    return jsonify({"error": "Mesh vide ou invalide"}), 422

                stl_buffer = io.BytesIO()
                mesh.export(stl_buffer, file_type='stl')
                stl_buffer.seek(0)
                return send_file(stl_buffer, mimetype='application/octet-stream',
                                 download_name=os.path.splitext(os.path.basename(internal_path))[0] + '.stl')
            else:
                return jsonify({"error": f"Format non supporté: {ext}"}), 415
        except Exception as e:
            app_logger.error(f"[Viewer] Erreur mesh depuis archive {file_path}: {e}")
            return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

    if not _is_path_within_sources(file_path, session['user_id']):
        app_logger.warning(f"[SECURITY] Tentative de lecture mesh hors sources: {file_path}")
        return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

    if not os.path.exists(file_path):
        app_logger.warning(f"[Viewer] Fichier non trouvé: {file_path}")
        return jsonify({"error": "Fichier non trouvé"}), 404

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == '.stl':
            return send_file(file_path, mimetype='application/octet-stream')

        elif ext in ('.3mf', '.obj'):
            if ext == '.3mf':
                mesh = load_3mf_mesh(file_path, plate_index=plate_index)
            else:
                mesh = trimesh.load(file_path, force='mesh')

            if isinstance(mesh, trimesh.Scene):
                geoms = [m for m in mesh.geometry.values()
                         if hasattr(m, 'vertices') and len(m.vertices) > 0]
                if not geoms:
                    return jsonify({"error": "Mesh vide"}), 422
                mesh = _concatenate_filtering_outliers(geoms)

            if mesh is None or mesh.is_empty or len(mesh.vertices) == 0:
                return jsonify({"error": "Mesh vide ou invalide"}), 422

            stl_buffer = io.BytesIO()
            mesh.export(stl_buffer, file_type='stl')
            stl_buffer.seek(0)
            return send_file(stl_buffer, mimetype='application/octet-stream',
                             download_name=os.path.splitext(os.path.basename(file_path))[0] + '.stl')

        else:
            return jsonify({"error": f"Format non supporté: {ext}"}), 415

    except Exception as e:
        app_logger.error(f"[Viewer] Erreur serving mesh {file_path}: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/file/plate-count', methods=['GET'])
@login_required
def api_file_plate_count():
    file_path = request.args.get('path', '').split('&t=')[0].strip()
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400

    file_path = file_path.replace('\\', '/')
    if '..' in file_path:
        return jsonify({"error": "Chemin invalide"}), 400

    try:
        if is_virtual_archive_path(file_path):
            archive_path, internal_path = split_virtual_archive_path(file_path)
            if not _is_path_within_sources(archive_path, session['user_id']):
                return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403
            if os.path.splitext(internal_path)[1].lower() != '.3mf':
                return jsonify({"plate_count": 1})
            raw_bytes = read_archive_entry_bytes(archive_path, internal_path)
            count = get_3mf_plate_count(raw_bytes)
        else:
            if not _is_path_within_sources(file_path, session['user_id']):
                return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403
            if os.path.splitext(file_path)[1].lower() != '.3mf':
                return jsonify({"plate_count": 1})
            if not os.path.exists(file_path):
                return jsonify({"error": "Fichier non trouvé"}), 404
            count = get_3mf_plate_count(file_path)
        return jsonify({"plate_count": count})
    except Exception as e:
        app_logger.warning(f"[3MF] Erreur comptage plateaux {file_path}: {e}")
        return jsonify({"plate_count": 1})


@app.route('/api/thumb', methods=['GET'])
@login_required
def api_get_thumb():
    file_path = request.args.get('path')
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400

    if '&t=' in file_path:
        file_path = file_path.split('&t=')[0]

    normalized_path = file_path.replace('\\', '/')
    thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()
    thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename)

    for ext in ['.webp', '.png', '.jpg']:
        img_path = thumb_path + ext
        if os.path.exists(img_path):
            mimetype = {'.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg'}[ext]
            return send_file(img_path, mimetype=mimetype)

    return jsonify({"error": "Miniature non trouvée"}), 404

MAX_THUMB_FALLBACK_RETRIES = 3

_pending_thumb_lock = threading.Lock()
_pending_thumb_updates = {}
_last_thumb_flush = 0.0
THUMB_CACHE_BATCH_SIZE = 25
THUMB_CACHE_FLUSH_INTERVAL = 2.0  

def update_cache_thumb_status(file_path, has_thumb, is_fallback=False):
    global _last_thumb_flush
    with _pending_thumb_lock:
        _pending_thumb_updates[file_path] = (has_thumb, is_fallback)
        should_flush = (
            len(_pending_thumb_updates) >= THUMB_CACHE_BATCH_SIZE
            or (time.time() - _last_thumb_flush) >= THUMB_CACHE_FLUSH_INTERVAL
        )
    if should_flush:
        flush_pending_thumb_updates()

def flush_pending_thumb_updates():
    global _last_thumb_flush
    with _pending_thumb_lock:
        if not _pending_thumb_updates:
            return
        updates = dict(_pending_thumb_updates)
        _pending_thumb_updates.clear()
        _last_thumb_flush = time.time()
    try:
        if not os.path.exists(CACHE_FILE):
            return
        with cache_file_lock:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            if 'files' in cache and isinstance(cache['files'], list):
                for f in cache['files']:
                    upd = updates.get(f.get('path'))
                    if upd is None:
                        continue
                    has_thumb, is_fallback = upd
                    f['has_thumb'] = has_thumb
                    if is_fallback:
                        f['thumb_fallback'] = True
                        f['thumb_fallback_retries'] = f.get('thumb_fallback_retries', 0) + 1
                    else:
                        f.pop('thumb_fallback', None)
                        f.pop('thumb_fallback_retries', None)
            tmp_path = CACHE_FILE + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, separators=(',', ':'))
            _atomic_replace(tmp_path, CACHE_FILE)
    except Exception as e:
        app_logger.info(f"[CACHE] Erreur flush thumb status: {e}")

def pregenerate_thumbnails_on_startup(limit=90):
    app_logger.info("[THUMBS] 🔄 Pré-génération des miniatures au démarrage...")
    conn = get_db()
    try:
        sources = conn.execute("SELECT * FROM sources").fetchall()
    finally:
        conn.close()

    to_process = []
    for source in sources:
        if len(to_process) >= limit:
            break
        try:
            if source['type'] == 'folder' and os.path.exists(source['path']):
                for root, dirs, files in os.walk(source['path']):
                    for f in sorted(files, key=str.lower):
                        if len(to_process) >= limit:
                            break
                        if f.lower().endswith(('.stl', '.obj', '.3mf')):
                            file_path = os.path.join(root, f).replace('\\', '/')
                            normalized_path = file_path
                            thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()
                            thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')
                            if not os.path.exists(thumb_path) and not _is_ignored_recently(file_path):
                                to_process.append((file_path, thumb_path))
                    break
        except Exception as e:
            app_logger.info(f"[THUMBS] Erreur source {source['name']}: {e}")

    def _generate_one(item):
        file_path, thumb_path = item
        try:
            app_logger.info(f"[THUMBS] Génération: {os.path.basename(file_path)}")
            success = generate_thumbnail_pyrender(file_path, thumb_path)
            if success:
                update_cache_thumb_status(file_path, True)
                return True
            create_fallback_thumbnail(thumb_path)
            update_cache_thumb_status(file_path, True, is_fallback=True)
            return False
        except Exception as e:
            app_logger.info(f"[THUMBS] Erreur génération {os.path.basename(file_path)}: {e}")
            return False

    generated = 0
    if to_process:
        with ThreadPoolExecutor(max_workers=NUM_THUMB_WORKERS) as pool:
            results = list(pool.map(_generate_one, to_process))
        generated = sum(1 for r in results if r)

    app_logger.info(f"[THUMBS] ✅ {generated}/{len(to_process)} miniatures pré-générées")

@app.route('/api/thumb/failures', methods=['GET'])
@login_required
def api_thumb_failures():
    failures = []
    while not thumb_failure_notifications.empty():
        try:
            failures.append(thumb_failure_notifications.get_nowait())
        except queue.Empty:
            break
    return jsonify({"failures": failures})


@app.route('/api/thumb/check', methods=['POST'])
@login_required
def api_check_thumb():
    data = request.json or {}

    paths = data.get('paths') or ([data.get('path')] if data.get('path') else [])
    if not paths:
        return jsonify({"exists": False}), 400

    if data.get('path') and not data.get('paths'):
        file_path = data['path']
        normalized = file_path.replace('\\', '/')
        thumb_filename = hashlib.md5(normalized.encode()).hexdigest()
        thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename)
        for ext in ['.webp', '.png', '.jpg']:
            if os.path.exists(thumb_path + ext):
                return jsonify({
                    "exists": True, "type": "cached",
                    "url": f"/api/thumb?path={file_path}",
                    "timestamp": int(os.path.getmtime(thumb_path + ext))
                })
        return jsonify({"exists": False})

    results = []
    for file_path in paths:
        normalized = file_path.replace('\\', '/')
        thumb_filename = hashlib.md5(normalized.encode()).hexdigest()
        thumb_path_base = os.path.join(THUMBNAILS_DIR, thumb_filename)
        found = False
        for ext in ['.webp', '.png', '.jpg']:
            full = thumb_path_base + ext
            if os.path.exists(full):
                results.append({
                    "path": file_path,
                    "ready": True,
                    "url": f"/api/thumb?path={file_path}",
                    "thumb_mtime": int(os.path.getmtime(full))
                })
                found = True
                break
        if not found:
            results.append({"path": file_path, "ready": False})

    return jsonify({"results": results})

def reconcile_thumbnails_with_disk():
    global _thumb_reconciled_this_run
    _thumb_reconciled_this_run = True

    result = {'total': 0, 'with_thumb': 0, 'without_thumb': 0, 'requeued': 0}
    if not os.path.exists(CACHE_FILE):
        return result

    try:
        with cache_file_lock:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            files = cache.get('files', [])

            try:
                existing_thumbs = set(os.listdir(THUMBNAILS_DIR))
            except Exception:
                existing_thumbs = None

            if existing_thumbs is not None:
                requeued = 0
                changed = False
                seen_paths = set()
                files_ordered = sorted(files, key=lambda f: os.path.basename(f.get('path', '')).lower())
                for f in files_ordered:
                    normalized = f['path'].replace('\\', '/')
                    thumb_filename = hashlib.md5(normalized.encode()).hexdigest()
                    real_has_thumb = (
                        (thumb_filename + '.webp') in existing_thumbs or
                        (thumb_filename + '.jpg') in existing_thumbs
                    )
                    if f.get('has_thumb') and not real_has_thumb:
                        f['has_thumb'] = False
                        f.pop('thumb_mtime', None)
                        changed = True
                        if not _is_ignored_recently(normalized) and normalized not in seen_paths:
                            seen_paths.add(normalized)
                            thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')
                            if _queue_thumb_task(normalized, thumb_path, priority='low'):
                                requeued += 1
                    elif f.get('thumb_fallback') and f.get('thumb_fallback_retries', 0) < MAX_THUMB_FALLBACK_RETRIES:
                        if not _is_ignored_recently(normalized) and normalized not in seen_paths:
                            seen_paths.add(normalized)
                            thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')
                            try:
                                if os.path.exists(thumb_path):
                                    os.remove(thumb_path)
                            except Exception:
                                pass
                            if _queue_thumb_task(normalized, thumb_path, priority='low'):
                                requeued += 1
                    elif not f.get('has_thumb') and not real_has_thumb:
                        if not _is_ignored_recently(normalized) and normalized not in seen_paths:
                            seen_paths.add(normalized)
                            thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')
                            if _queue_thumb_task(normalized, thumb_path, priority='low'):
                                requeued += 1
                if changed:
                    try:
                        tmp_path = CACHE_FILE + '.tmp'
                        with open(tmp_path, 'w', encoding='utf-8') as f_out:
                            json.dump(cache, f_out, indent=2, ensure_ascii=False)
                        _atomic_replace(tmp_path, CACHE_FILE)
                    except Exception as e:
                        app_logger.info(f"[THUMBS] Échec sauvegarde après réconciliation: {e}")
                if requeued:
                    app_logger.info(f"[THUMBS] 🔄 Comparaison fichiers/miniatures : {requeued} manquante(s) — génération lancée")
                    _thumb_session_note_start(requeued)
                result['requeued'] = requeued

            for file_entry in files:
                if file_entry.get('has_thumb'):
                    result['with_thumb'] += 1
                else:
                    result['without_thumb'] += 1
            result['total'] = result['with_thumb'] + result['without_thumb']
    except Exception as e:
        app_logger.info(f"[THUMBS] Erreur réconciliation: {e}")

    return result


@app.route('/api/thumb/progress', methods=['GET'])
@login_required
def api_thumb_progress():
    pending = thumb_generation_queue.qsize()
    files_without_thumb = 0
    files_with_thumb = 0

    if not _thumb_reconciled_this_run:
        reconcile_thumbnails_with_disk()
        pending = thumb_generation_queue.qsize()

    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            for file_entry in cache.get('files', []):
                if file_entry.get('has_thumb'):
                    files_with_thumb += 1
                else:
                    files_without_thumb += 1
        except:
            pass

    total = files_with_thumb + files_without_thumb
    progress = (files_with_thumb / total * 100) if total > 0 else 100

    return jsonify({
        'pending': pending,
        'files_with_thumb': files_with_thumb,
        'files_without_thumb': files_without_thumb,
        'total': total,
        'progress': round(progress, 1),
        'is_generating': pending > 0 or is_generation_running
    })


@app.route('/api/thumb/summary', methods=['GET'])
@login_required
def api_thumb_summary():
    global _thumb_pending_summary
    with _thumb_session_lock:
        summary = _thumb_pending_summary
        _thumb_pending_summary = None
    return jsonify({'summary': summary})


@app.route('/api/thumb/generate-now', methods=['POST'])
@login_required
def api_generate_thumb_now():
    data = request.json
    file_path = data.get('path')
    force = data.get('force', False)

    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400

    normalized_path = file_path.replace('\\', '/')
    thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()
    thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')

    if not force and _is_ignored_recently(normalized_path):
        return jsonify({"success": False, "ignored": True, "message": "Fichier précédemment marqué inaccessible"}), 200

    if force and os.path.exists(thumb_path):
        try:
            os.remove(thumb_path)
            app_logger.info(f"[REGEN] Miniature supprimée: {os.path.basename(file_path)}")
        except Exception as e:
            app_logger.warning(f"[REGEN] Suppression impossible: {e}")

    if force:
        ignored_files_cache.pop(normalized_path, None)

    if os.path.exists(thumb_path) and not force:
        return jsonify({"success": True, "cached": True})

    if force:
        _release_thumb_inflight(file_path)
    _queue_thumb_task(file_path, thumb_path, priority='high')

    return jsonify({"success": True, "message": "Génération démarrée"})

@app.route('/api/thumb/regen-batch', methods=['POST'])
@login_required
def api_regen_thumb_batch():
    data = request.json or {}
    paths = data.get('paths')

    if not paths or not isinstance(paths, list):
        return jsonify({"error": "Liste de chemins requise"}), 400

    queued = 0
    for file_path in paths:
        if not file_path or not isinstance(file_path, str):
            continue

        normalized_path = file_path.replace('\\', '/')
        thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()
        thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')

        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except Exception as e:
                app_logger.warning(f"[REGEN-BATCH] Suppression impossible pour {os.path.basename(file_path)}: {e}")

        ignored_files_cache.pop(normalized_path, None)
        _release_thumb_inflight(file_path)
        if _queue_thumb_task(file_path, thumb_path, priority='high'):
            queued += 1

    app_logger.info(f"[REGEN-BATCH] {queued} miniature(s) replanifiée(s) pour régénération groupée")
    return jsonify({"success": True, "queued": queued})

@app.route('/api/files/analyze-now', methods=['POST'])
@login_required
def api_analyze_now():
    data = request.json
    file_path = data.get('path')
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400

    metadata_generation_queue.put({'path': file_path, 'priority': 'high'})
    return jsonify({"success": True, "message": "Analyse démarrée"})


@app.route('/api/tags', methods=['GET'])
@login_required
def api_get_tags():
    conn = get_db()
    try:
        tags = conn.execute(
            "SELECT t.id, t.name, t.color, COUNT(ft.file_path) as count FROM tags t LEFT JOIN file_tags ft ON t.id = ft.tag_id GROUP BY t.id ORDER BY t.name"
        ).fetchall()
    finally:
        conn.close()
    return jsonify([dict(t) for t in tags])

@app.route('/api/tags', methods=['POST'])
@login_required
def api_create_tag():
    data = request.json
    name = data.get('name', '').strip()
    color = data.get('color', '#4ea1d3')

    if not name:
        return jsonify({"error": "Nom requis"}), 400

    conn = get_db()
    try:
        conn.execute("INSERT INTO tags (name, color) VALUES (?, ?)", (name, color))
        conn.commit()
        return jsonify({
            "id": conn.execute("SELECT last_insert_rowid()").fetchone()[0],
            "name": name,
            "color": color
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Existant"}), 409
    finally:
        conn.close()

@app.route('/api/tags/<int:tag_id>', methods=['PUT'])
@login_required
def api_update_tag(tag_id):
    data = request.json
    name = data.get('name', '').strip()
    color = data.get('color')

    if not name:
        return jsonify({"error": "Nom requis"}), 400

    conn = get_db()
    try:
        if color:
            conn.execute("UPDATE tags SET name = ?, color = ? WHERE id = ?", (name, color, tag_id))
        else:
            conn.execute("UPDATE tags SET name = ? WHERE id = ?", (name, tag_id))
        conn.commit()
        return jsonify({"message": "Mis à jour"}), 200
    except:
        return jsonify({"error": "Erreur"}), 500
    finally:
        conn.close()

@app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
@login_required
def api_delete_tag(tag_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM file_tags WHERE tag_id = ?", (tag_id,))
        conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"message": "Supprimé"}), 200

@app.route('/api/files/tags', methods=['POST'])
@login_required
def api_assign_tags():
    data = request.json
    file_path = data.get('path')
    tags = data.get('tags', [])

    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400

    conn = get_db()
    try:
        conn.execute("DELETE FROM file_tags WHERE file_path = ?", (file_path,))
        for tag_name in tags:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
            tid = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()[0]
            conn.execute("INSERT OR IGNORE INTO file_tags (file_path, tag_id) VALUES (?, ?)", (file_path, tid))
        conn.commit()
        return jsonify({"message": "Assignés"}), 200
    except:
        return jsonify({"error": "Erreur"}), 500
    finally:
        conn.close()


def extract_archive_to_disk(file_path, source_name, extensions_3d=None):
    if extensions_3d is None:
        extensions_3d = {'.stl', '.obj', '.3mf'}
    ext = os.path.splitext(file_path)[1].lower()
    filename = os.path.basename(file_path)
    root = os.path.dirname(file_path)
    found = []
    try:
        if filename.lower().endswith('.tar.gz'):
            extract_folder = os.path.join(root, filename[:-7])
        else:
            extract_folder = os.path.splitext(file_path)[0]
        os.makedirs(extract_folder, exist_ok=True)

        extracted_count = 0
        if ext == '.rar':
            if rarfile.UNRAR_TOOL and os.path.exists(rarfile.UNRAR_TOOL):
                with rarfile.RarFile(file_path, 'r') as rf:
                    safe_extract_rar(rf, extract_folder)
                    extracted_count = len(rf.namelist())
        elif ext in ('.tar.gz', '.tgz') or filename.lower().endswith('.tar.gz'):
            with tarfile.open(file_path, 'r:*') as tar_ref:
                safe_extract_tar(tar_ref, extract_folder)
                extracted_count = len(tar_ref.getnames())
        elif ext == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zf:
                safe_extract_zip(zf, extract_folder)
                extracted_count = len(zf.namelist())
        elif ext == '.7z':
            try:
                import py7zr
                with py7zr.SevenZipFile(file_path, mode='r') as zf:
                    safe_extract_7z(zf, extract_folder)
                    extracted_count = len(zf.getnames())
            except ImportError:
                app_logger.info(f"    Module 'py7zr' manquant, {filename} ignoré")
                return []

        for extracted_file in os.listdir(extract_folder):
            extracted_ext = os.path.splitext(extracted_file)[1].lower()
            if extracted_ext in extensions_3d:
                extracted_path = os.path.join(extract_folder, extracted_file)
                normalized_path = extracted_path.replace('\\', '/')
                thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()
                thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')
                plate_count = 1
                if extracted_ext == '.3mf':
                    try:
                        plate_count = get_3mf_plate_count(extracted_path)
                    except Exception:
                        plate_count = 1
                found.append({
                    'name': extracted_file,
                    'path': normalized_path,
                    'extension': extracted_ext,
                    'size': os.path.getsize(extracted_path),
                    'source': source_name,
                    'date_added': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'has_thumb': os.path.exists(thumb_path),
                    'has_metadata': False,
                    'multi_plate': plate_count > 1,
                    'plate_count': plate_count
                })

        if extracted_count > 0:
            os.remove(file_path)
            app_logger.info(f"[EXTRACT] ✅ {filename} extrait ({extracted_count} élément(s)) puis supprimé")
    except Exception as e:
        app_logger.info(f"    Erreur extraction {filename}: {e}")
    return found

def scan_local_folder(folder_path):
    files = []
    if not os.path.exists(folder_path):
        return files

    extensions_3d = {'.stl', '.obj', '.3mf'}
    extensions_archive = {'.rar', '.tar.gz', '.tgz', '.zip', '.7z'}

    for root, dirs, filenames in os.walk(folder_path):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            file_path = os.path.join(root, filename)

            try:
                file_size = os.path.getsize(file_path)
            except Exception:
                continue

            if ext in extensions_archive or filename.lower().endswith('.tar.gz'):
                files.extend(extract_archive_to_disk(file_path, os.path.basename(folder_path), extensions_3d))
                continue

            if ext in extensions_3d:
                try:
                    normalized_path = file_path.replace('\\', '/')
                    thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()
                    thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')

                    thumb_exists = os.path.exists(thumb_path)
                    plate_count = 1
                    if ext == '.3mf':
                        try:
                            plate_count = get_3mf_plate_count(file_path)
                        except Exception:
                            plate_count = 1
                    files.append({
                        'name': filename,
                        'path': normalized_path,
                        'extension': ext,
                        'size': file_size,
                        'source': os.path.basename(folder_path),
                        'date_added': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'mtime': int(os.path.getmtime(file_path)),
                        'has_thumb': thumb_exists,
                        'thumb_mtime': int(os.path.getmtime(thumb_path)) if thumb_exists else 0,
                        'has_metadata': False,
                        'multi_plate': plate_count > 1,
                        'plate_count': plate_count
                    })
                except Exception as e:
                    app_logger.info(f"    Erreur lecture {filename}: {e}")

    return files

def scan_smb_folder_recursive(base_path, current_subdir, kwargs, source_name):
    files = []
    current_path = f"{base_path}/{current_subdir}" if current_subdir else base_path
    folders_to_skip = ['.recycle', '$recycle.bin', 'system volume information', '@eaDir', '.@__thumb']

    try:
        if any(skip_folder in current_path.lower() for skip_folder in folders_to_skip):
            app_logger.info(f"[SMB] Dossier système ignoré: {current_path}")
            return files

        if not smbclient.path.exists(current_path, **kwargs):
            app_logger.info(f"[SMB] Chemin inaccessible: {current_path}")
            return files

        entries = smbclient.listdir(current_path, **kwargs)
        for entry in entries:
            if entry.startswith('.') or entry.startswith('$'):
                continue

            entry_path = f"{current_subdir}/{entry}" if current_subdir else entry
            full_path = f"{base_path}/{entry_path}"

            try:
                info = smbclient.stat(full_path, **kwargs)
                if (info.st_mode & 0o170000) == 0o040000:
                    if entry.lower() not in folders_to_skip:
                        files.extend(scan_smb_folder_recursive(base_path, entry_path, kwargs, source_name))
                elif entry.lower().endswith(('.stl', '.obj', '.3mf')):
                    normalized_path = full_path.replace('\\', '/')
                    thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()
                    thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')

                    plate_count = 1
                    if entry.lower().endswith('.3mf'):
                        try:
                            with smbclient.open_file(full_path, mode='rb', **kwargs) as smb_f:
                                plate_count = get_3mf_plate_count(smb_f)
                        except Exception:
                            plate_count = 1

                    files.append({
                        'name': entry,
                        'path': normalized_path,
                        'extension': f".{entry.split('.')[-1]}",
                        'size': info.st_size,
                        'source': source_name,
                        'date_added': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'subdir': current_subdir,
                        'has_thumb': os.path.exists(thumb_path),
                        'has_metadata': False,
                        'multi_plate': plate_count > 1,
                        'plate_count': plate_count
                    })
            except Exception as e:
                if "ACCESS_DENIED" not in str(e):
                    app_logger.info(f"[SMB] Erreur lecture {entry}: {e}")
                continue

    except Exception as e:
        error_msg = str(e)
        if "ACCESS_DENIED" not in error_msg:
            app_logger.info(f"[SMB] Erreur connexion: {e}")

    return files

def deduplicate_files_hybrid(files):
    seen_names = set()
    candidates = []
    for f in files:
        key = (f['name'].lower(), f['extension'].lower())
        if key not in seen_names:
            seen_names.add(key)
            candidates.append(f)

    size_groups = {}
    for f in candidates:
        size_groups.setdefault(f.get('size', 0), []).append(f)

    final_unique = []
    md5_candidates = []
    for size, group in size_groups.items():
        if len(group) == 1:
            final_unique.append(group[0])
        else:
            md5_candidates.extend(group)

    if md5_candidates:
        seen_hashes = {}
        for f in md5_candidates:
            md5 = hashlib.md5(f.get('path', '').encode()).hexdigest()
            if md5 not in seen_hashes:
                seen_hashes[md5] = f
        final_unique.extend(seen_hashes.values())

    return sorted(final_unique, key=lambda x: x.get('path', ''))

_background_scan_running = threading.Lock()

AUTO_TAG_COLORS = {
    'makerworld': '#00a884',
    'printables': '#f5a623',
    'thingiverse': '#1a8fe3',
    'local': '#8899aa',
    'réseau (smb)': '#8899aa',
    'fichier unique': '#8899aa',
    'multi plateaux': '#e0679e',
}
_SOURCE_TYPE_TAG_LABELS = {
    'folder': 'Local',
    'smb': 'Réseau (SMB)',
    'file': 'Fichier unique',
}
MULTI_PLATE_TAG_NAME = 'Multi plateaux'


def _get_or_create_tag(conn, name):
    row = conn.execute("SELECT id FROM tags WHERE LOWER(name) = LOWER(?)", (name,)).fetchone()
    if row:
        return row[0]
    color = AUTO_TAG_COLORS.get(name.lower(), '#4ea1d3')
    try:
        conn.execute("INSERT INTO tags (name, color) VALUES (?, ?)", (name, color))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    row = conn.execute("SELECT id FROM tags WHERE LOWER(name) = LOWER(?)", (name,)).fetchone()
    return row[0] if row else None


def _auto_tag_new_files(new_files, sources_list, user_id):
    if not new_files:
        return
    conn = get_db()
    try:
        sources_by_name = {s['name']: s for s in sources_list}

        platform_by_path = {}
        try:
            rows = conn.execute(
                "SELECT file_path, platform FROM download_history WHERE user_id = ? AND platform != ''",
                (user_id,)
            ).fetchall()
            for r in rows:
                platform_by_path[r['file_path'].replace('\\', '/')] = r['platform']
        except Exception:
            pass

        for f in new_files:
            normalized = f['path'].replace('\\', '/')
            platform = platform_by_path.get(normalized)
            if platform:
                tag_name = platform.strip()
            else:
                source = sources_by_name.get(f.get('source'))
                source_type = source.get('type') if source else None
                tag_name = _SOURCE_TYPE_TAG_LABELS.get(source_type)
            if tag_name:
                tag_id = _get_or_create_tag(conn, tag_name)
                if tag_id:
                    try:
                        conn.execute("INSERT OR IGNORE INTO file_tags (file_path, tag_id) VALUES (?, ?)", (normalized, tag_id))
                    except Exception:
                        pass

            if f.get('multi_plate'):
                mp_tag_id = _get_or_create_tag(conn, MULTI_PLATE_TAG_NAME)
                if mp_tag_id:
                    try:
                        conn.execute("INSERT OR IGNORE INTO file_tags (file_path, tag_id) VALUES (?, ?)", (normalized, mp_tag_id))
                    except Exception:
                        pass
        conn.commit()
    finally:
        conn.close()


def _do_background_scan(sources_list, user_id, blocking=False):
    if blocking:
        acquired = _background_scan_running.acquire(blocking=True, timeout=180)
    else:
        acquired = _background_scan_running.acquire(blocking=False)
    if not acquired:
        app_logger.info("[SCAN] Scan déjà en cours, ignoré")
        return

    try:
        app_logger.info(f"[SCAN] Démarrage scan arrière-plan... ({len(sources_list)} source(s))")
        all_files = []
        unreachable_sources = []

        for source in sources_list:
            try:
                if source['type'] in ('folder', 'nfs'):
                    if not os.path.exists(source['path']):
                        app_logger.warning(f"[SCAN] Source \"{source['name']}\" introuvable ({source['path']}) — ignorée pour ce scan")
                        unreachable_sources.append(source['name'])
                        continue
                    all_files.extend(scan_local_folder(source['path']))
                elif source['type'] == 'smb':
                    try:
                        smbclient.reset_connection_cache()
                    except Exception:
                        pass
                    unc_path = source['path'].replace('\\\\', '//').replace('\\', '/')
                    kwargs = {'connection_timeout': 8}
                    config = json.loads(source['config']) if source['config'] else {}
                    if config.get('username'):
                        kwargs['username'] = config['username']
                    if config.get('password'):
                        kwargs['password'] = config['password']
                    try:
                        smbclient.stat(unc_path, **kwargs)
                    except Exception:
                        app_logger.warning(f"[SCAN] Source réseau \"{source['name']}\" injoignable ({unc_path}) — ignorée pour ce scan")
                        unreachable_sources.append(source['name'])
                        continue
                    all_files.extend(scan_smb_folder_recursive(unc_path, '', kwargs, source['name']))
                elif source['type'] == 'file':
                    if not os.path.exists(source['path']):
                        app_logger.warning(f"[SCAN] Fichier source \"{source['name']}\" introuvable — ignoré pour ce scan")
                        unreachable_sources.append(source['name'])
                        continue

                    src_ext = os.path.splitext(source['path'])[1].lower()
                    is_archive_src = (
                        src_ext in {'.zip', '.7z', '.rar', '.tgz'}
                        or source['path'].lower().endswith('.tar.gz')
                    )
                    if is_archive_src:
                        extracted_files = extract_archive_to_disk(source['path'], source['name'])
                        if extracted_files:
                            all_files.extend(extracted_files)
                            new_folder = (source['path'][:-7] if source['path'].lower().endswith('.tar.gz')
                                          else os.path.splitext(source['path'])[0])
                            try:
                                conn_upd = get_db()
                                conn_upd.execute(
                                    "UPDATE sources SET type = 'folder', path = ? WHERE id = ?",
                                    (new_folder, source['id'])
                                )
                                conn_upd.commit()
                                conn_upd.close()
                                app_logger.info(f"[SCAN] Source \"{source['name']}\" convertie en dossier après extraction: {new_folder}")
                            except Exception as e:
                                app_logger.warning(f"[SCAN] Conversion de source après extraction échouée: {e}")
                        continue

                    normalized_path = source['path'].replace('\\', '/')
                    thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()
                    thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')
                    plate_count = 1
                    if src_ext == '.3mf':
                        try:
                            plate_count = get_3mf_plate_count(source['path'])
                        except Exception:
                            plate_count = 1
                    all_files.append({
                        'name': os.path.basename(source['path']),
                        'path': normalized_path,
                        'extension': f".{source['path'].split('.')[-1]}",
                        'size': os.path.getsize(source['path']),
                        'source': source['name'],
                        'date_added': source.get('created_at') or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'has_thumb': os.path.exists(thumb_path),
                        'has_metadata': False,
                        'multi_plate': plate_count > 1,
                        'plate_count': plate_count
                    })
            except Exception as e:
                app_logger.info(f"    [SCAN] Erreur source {source['name']}: {e}")
                unreachable_sources.append(source['name'])

        try:
            conn2 = get_db()
            file_paths = [f['path'] for f in all_files]
            if file_paths:
                placeholders = ','.join('?' * len(file_paths))
                tag_results = conn2.execute(
                    f"SELECT ft.file_path, t.name, t.color FROM file_tags ft JOIN tags t ON ft.tag_id = t.id WHERE ft.file_path IN ({placeholders})",
                    file_paths
                ).fetchall()
                tags_by_file = {}
                for row in tag_results:
                    tags_by_file.setdefault(row['file_path'], []).append({'name': row['name'], 'color': row['color']})
                for f in all_files:
                    f['tags'] = tags_by_file.get(f['path'], [])
            conn2.close()
        except Exception as e:
            app_logger.info(f"[SCAN] Erreur tags: {e}")

        previous_count = 0
        previous_paths = set()
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    prev_files = json.load(f).get('files', [])
                previous_count = len(prev_files)
                previous_paths = {pf['path'] for pf in prev_files if 'path' in pf}
        except Exception:
            previous_count = 0
            previous_paths = set()

        newly_seen_files = [f for f in all_files if f['path'] not in previous_paths]
        if newly_seen_files:
            try:
                _auto_tag_new_files(newly_seen_files, sources_list, user_id)
                conn3 = get_db()
                new_paths = [f['path'] for f in newly_seen_files]
                placeholders = ','.join('?' * len(new_paths))
                tag_results = conn3.execute(
                    f"SELECT ft.file_path, t.name, t.color FROM file_tags ft JOIN tags t ON ft.tag_id = t.id WHERE ft.file_path IN ({placeholders})",
                    new_paths
                ).fetchall()
                conn3.close()
                tags_by_new_path = {}
                for row in tag_results:
                    tags_by_new_path.setdefault(row['file_path'], []).append({'name': row['name'], 'color': row['color']})
                for f in newly_seen_files:
                    f['tags'] = tags_by_new_path.get(f['path'], f.get('tags', []))
            except Exception as e:
                app_logger.info(f"[SCAN] Erreur auto-tagging: {e}")

        if unreachable_sources and len(all_files) < previous_count * 0.5 and previous_count > 0:
            app_logger.warning(
                f"[SCAN] ⚠️ Résultat suspect ({len(all_files)} fichiers contre {previous_count} avant, "
                f"sources injoignables: {', '.join(unreachable_sources)}) — cache existant conservé, pas d'écrasement."
            )
        else:
            try:
                save_file_cache(all_files, sources_list)
            except Exception as e:
                app_logger.info(f"[SCAN] Échec sauvegarde cache: {e}")
            missing_count = 0
            seen_paths = set()
            for f in all_files:
                if not f.get('has_thumb') and not _is_ignored_recently(f['path']) and f['path'] not in seen_paths:
                    seen_paths.add(f['path'])
                    thumb_filename = hashlib.md5(f['path'].encode()).hexdigest()
                    thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')
                    if _queue_thumb_task(f['path'], thumb_path, priority='low'):
                        missing_count += 1
            if missing_count:
                _thumb_session_note_start(missing_count)

        app_logger.info(f"[SCAN] ✅ Terminé : {len(all_files)} fichiers"
                         + (f" — sources ignorées: {', '.join(unreachable_sources)}" if unreachable_sources else ""))

    except Exception as e:
        app_logger.info(f"[SCAN] Erreur critique: {e}")
    finally:
        _background_scan_running.release()


def _auto_scan_scheduler():
    _lower_thread_priority()
    app_logger.info("[AUTO-SCAN] Planificateur démarré")
    while True:
        interval_min = 5
        try:
            settings = load_settings() or {}
            enabled = settings.get('auto_scan_enabled', True)
            try:
                interval_min = max(1, int(settings.get('auto_scan_interval_minutes', 5)))
            except (TypeError, ValueError):
                interval_min = 5

            if enabled:
                conn = get_db()
                try:
                    sources = [dict(s) for s in conn.execute("SELECT * FROM sources").fetchall()]
                finally:
                    conn.close()
                if sources:
                    app_logger.info(f"[AUTO-SCAN] Scan périodique de {len(sources)} source(s)...")
                    _do_background_scan(sources, None, blocking=False)
        except Exception as e:
            app_logger.info(f"[AUTO-SCAN] Erreur: {e}")
        time.sleep(interval_min * 60)

@app.route('/api/files', methods=['GET'])
@login_required
def api_get_files():
    try:
        conn = get_db()
        sources = conn.execute("SELECT * FROM sources WHERE user_id = ?", (session['user_id'],)).fetchall()
        sources_list = [dict(s) for s in sources]
        tag_filter = request.args.get('tags', '')

        cached_files = None
        cache_data = None

        if os.path.exists(CACHE_FILE):
            for attempt in range(2):
                try:
                    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    if isinstance(cache_data, dict) and 'files' in cache_data:
                        cached_files = cache_data['files']
                    else:
                        invalidate_cache()
                        cache_data = None
                    break
                except json.JSONDecodeError:
                    if attempt == 0:
                        time.sleep(0.1)
                        continue
                    app_logger.info("[WARN] Lecture cache impossible dans api_get_files (fichier momentanément verrouillé ?)")
                    cache_data = None

        cache_timestamp = cache_data.get('timestamp', 0) if cache_data else 0

        if cached_files is not None:
            app_logger.info(f"[FILES] Cache hit — {len(cached_files)} fichiers servis instantanément")
            try:
                existing_thumbs = set(os.listdir(THUMBNAILS_DIR))
            except Exception:
                existing_thumbs = None

            if existing_thumbs is not None:
                changed = False
                seen_paths = set()
                for f in cached_files:
                    normalized = f['path'].replace('\\', '/')
                    thumb_filename = hashlib.md5(normalized.encode()).hexdigest()
                    real_has_thumb = (
                        (thumb_filename + '.webp') in existing_thumbs or
                        (thumb_filename + '.jpg') in existing_thumbs
                    )
                    if f.get('has_thumb') and not real_has_thumb:
                        f['has_thumb'] = False
                        f.pop('thumb_mtime', None)
                        changed = True
                        if not _is_ignored_recently(normalized) and normalized not in seen_paths:
                            seen_paths.add(normalized)
                            thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')
                            _queue_thumb_task(normalized, thumb_path, priority='low')
                    elif real_has_thumb and not f.get('has_thumb'):
                        f['has_thumb'] = True
                        changed = True

                if seen_paths:
                    _thumb_session_note_start(len(seen_paths))

                if changed:
                    try:
                        with cache_file_lock:
                            cache_data['files'] = cached_files
                            tmp_path = CACHE_FILE + '.tmp'
                            with open(tmp_path, 'w', encoding='utf-8') as f_out:
                                json.dump(cache_data, f_out, indent=2, ensure_ascii=False)
                            _atomic_replace(tmp_path, CACHE_FILE)
                    except Exception as e:
                        app_logger.info(f"[FILES] Échec sauvegarde après revalidation has_thumb: {e}")

            for f in cached_files:
                if 'thumb_mtime' not in f and f.get('has_thumb'):
                    try:
                        normalized = f['path'].replace('\\', '/')
                        thumb_filename = hashlib.md5(normalized.encode()).hexdigest()
                        thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + '.webp')
                        if os.path.exists(thumb_path):
                            f['thumb_mtime'] = int(os.path.getmtime(thumb_path))
                    except Exception:
                        pass

            file_paths = [f['path'] for f in cached_files]
            if file_paths:
                try:
                    placeholders = ','.join('?' * len(file_paths))
                    tag_results = conn.execute(
                        f"SELECT ft.file_path, t.name, t.color FROM file_tags ft JOIN tags t ON ft.tag_id = t.id WHERE ft.file_path IN ({placeholders})",
                        file_paths
                    ).fetchall()
                    tags_by_file = {}
                    for row in tag_results:
                        tags_by_file.setdefault(row['file_path'], []).append({'name': row['name'], 'color': row['color']})
                    for f in cached_files:
                        f['tags'] = tags_by_file.get(f['path'], [])
                except Exception as e:
                    app_logger.info(f"[WARN] Erreur rechargement tags: {e}")
        else:
            app_logger.info("[FILES] Pas de cache — scan initial (attente de la fin du scan)...")
            _do_background_scan(sources_list, session['user_id'], blocking=True)

            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    cached_files = cache_data.get('files', [])
                except Exception:
                    cached_files = []
            else:
                cached_files = []

        conn.close()

        if not isinstance(cached_files, list):
            cached_files = []

        try:
            for f in cached_files:
                analysis_key = f"analysis_{hashlib.md5(f['path'].replace(chr(92), '/').encode()).hexdigest()}"
                cached_analysis = (cache_data or {}).get(analysis_key)
                if cached_analysis and cached_analysis.get('weights'):
                    f['weight_g'] = cached_analysis['weights'].get('pla') or next(iter(cached_analysis['weights'].values()), None)
                else:
                    f['weight_g'] = None

            conn4 = get_db()
            status_rows = conn4.execute(
                "SELECT file_path, result FROM print_history WHERE user_id = ?", (session['user_id'],)
            ).fetchall()
            conn4.close()
            results_by_path = {}
            for r in status_rows:
                results_by_path.setdefault(r['file_path'], []).append(r['result'])
            for f in cached_files:
                results = results_by_path.get(f['path'])
                if not results:
                    f['print_status'] = 'never'
                elif 'success' in results:
                    f['print_status'] = 'success'
                elif 'failed' in results:
                    f['print_status'] = 'failed'
                else:
                    f['print_status'] = 'printed'
        except Exception as e:
            app_logger.info(f"[WARN] Erreur enrichissement poids/statut: {e}")

        if tag_filter.strip():
            required_tags = set(t.strip().lower() for t in tag_filter.split(',') if t.strip())
            if required_tags:
                cached_files = [f for f in cached_files if required_tags.issubset(set(t['name'].lower() for t in f.get('tags', [])))]

        return jsonify(cached_files)

    except Exception as e:
        app_logger.info(f"[api_get_files] Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500

@app.route('/api/files/changes', methods=['GET'])
@login_required
def api_check_changes():
    try:
        last_check = float(request.args.get('since', 0))

        if os.path.exists(CACHE_FILE):
            for attempt in range(2):
                try:
                    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    cache_time = cache_data.get('timestamp', 0)
                    files = cache_data.get('files', [])
                    if not isinstance(files, list):
                        files = []

                    return jsonify({
                        'has_changes': cache_time > last_check,
                        'timestamp': cache_time,
                        'count': len(files)
                    })
                except json.JSONDecodeError:
                    if attempt == 0:
                        time.sleep(0.1)
                        continue
                    app_logger.info("[WARN] Lecture cache impossible dans api_check_changes (fichier momentanément verrouillé ?)")
                    return jsonify({'has_changes': False, 'timestamp': last_check, 'count': 0})

        return jsonify({'has_changes': True, 'timestamp': 0, 'count': 0})

    except Exception as e:
        app_logger.info(f"[ERROR] api_check_changes: {e}")
        return jsonify({'has_changes': False, 'timestamp': 0, 'count': 0}), 500

@app.route('/api/files/invalidate-cache', methods=['POST'])
@login_required
def api_invalidate_cache_route():
    invalidate_cache()
    return jsonify({"message": "Cache vidé"}), 200

@app.route('/api/scan/delta', methods=['GET'])
@login_required
def scan_delta():
    with scan_lock:
        batch = scan_state.get('new_batch', [])
        status = scan_state.get('status', 'done')
        found = scan_state.get('found', 0)
        total_scanned = scan_state.get('total_scanned', 0)
        scan_state['new_batch'] = []

        if status == 'idle' and found == 0:
            status = 'done'

        return jsonify({
            "status": status,
            "found": found,
            "total_scanned": total_scanned,
            "new_files": batch
        })


@app.route('/api/files/share', methods=['POST'])
@login_required
def api_create_share_link():
    data = request.json or {}
    file_path = (data.get('file_path') or '').strip()

    if os.name == 'nt':
        file_path = file_path.replace('/', '\\')

    if not file_path or not os.path.isfile(file_path):
        return jsonify({"error": "Fichier introuvable"}), 404

    if not _is_path_within_sources(file_path, session['user_id']):
        app_logger.warning(f"[SECURITY] Tentative de partage hors sources: {file_path}")
        return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

    _cleanup_expired_shares()

    token = secrets.token_urlsafe(24)
    with _share_lock:
        _share_links[token] = {
            'path': file_path,
            'name': os.path.basename(file_path),
            'created': time.time(),
        }

    remote_state = get_remote_state()
    if remote_state.get('status') == 'ready' and remote_state.get('url'):
        base_url = remote_state['url'].rstrip('/')
    else:
        base_url = f"http://{get_local_ip()}:5000"

    share_url = f"{base_url}/share/{token}"
    app_logger.info(f"[SHARE] Lien créé pour {os.path.basename(file_path)} (token={token[:8]}...)")
    return jsonify({"url": share_url, "expires_in": SHARE_LINK_MAX_AGE}), 200


@app.route('/share/<token>', methods=['GET'])
def download_shared_file(token):
    _cleanup_expired_shares()
    with _share_lock:
        info = _share_links.get(token)

    if not info or not os.path.isfile(info['path']):
        return "Ce lien est invalide, a expiré, ou le fichier a déjà été téléchargé.", 404

    def _invalidate_token():
        with _share_lock:
            _share_links.pop(token, None)
        app_logger.info(f"[SHARE] Lien désactivé après téléchargement (token={token[:8]}...)")

    response = send_file(info['path'], as_attachment=True, download_name=info['name'])
    response.call_on_close(_invalidate_token)
    return response

def _get_or_create_local_peer_key():
    settings = load_settings()
    if not settings.get('local_peer_key'):
        settings['local_peer_key'] = secrets.token_urlsafe(24)
        save_settings(settings)
    return settings['local_peer_key']

def _get_primary_user_id():
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
        return row['id'] if row else None
    finally:
        conn.close()

def require_peer_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        provided = request.headers.get('X-Stellio-Peer-Key', '')
        expected = _get_or_create_local_peer_key()
        if not provided or not secrets.compare_digest(provided, expected):
            return jsonify({"error": "Clé d'appairage invalide ou manquante"}), 403
        return f(*args, **kwargs)
    return wrapper


@app.route('/api/remote-instances', methods=['GET'])
@login_required
def api_remote_instances_list():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, name, url, inbox_folder, last_status, last_seen_at, created_at FROM remote_instances WHERE user_id=? ORDER BY created_at ASC",
            (session['user_id'],)
        ).fetchall()
        return jsonify({"instances": [dict(r) for r in rows], "local_peer_key": _get_or_create_local_peer_key()}), 200
    finally:
        conn.close()


@app.route('/api/remote-instances', methods=['POST'])
@login_required
def api_remote_instances_add():
    data = request.json or {}
    name = (data.get('name') or '').strip()
    url = (data.get('url') or '').strip().rstrip('/')
    peer_key = (data.get('peer_key') or '').strip()
    inbox_folder = (data.get('inbox_folder') or '').strip() or None

    if not name or not url or not peer_key:
        return jsonify({"error": "Nom, adresse et clé d'appairage requis"}), 400
    if not url.startswith('http://') and not url.startswith('https://'):
        url = f"http://{url}"

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO remote_instances (user_id, name, url, peer_key, inbox_folder) VALUES (?,?,?,?,?)",
            (session['user_id'], name, url, peer_key, inbox_folder)
        )
        conn.commit()
        return jsonify({"success": True, "id": cur.lastrowid}), 200
    finally:
        conn.close()


@app.route('/api/remote-instances/<int:instance_id>', methods=['DELETE'])
@login_required
def api_remote_instances_delete(instance_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM remote_instances WHERE id=? AND user_id=?", (instance_id, session['user_id']))
        conn.commit()
        return jsonify({"success": True}), 200
    finally:
        conn.close()


@app.route('/api/remote-instances/<int:instance_id>/ping', methods=['POST'])
@login_required
def api_remote_instances_ping(instance_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM remote_instances WHERE id=? AND user_id=?", (instance_id, session['user_id'])
        ).fetchone()
        if not row:
            return jsonify({"error": "Instance introuvable"}), 404

        try:
            r = requests.get(
                f"{row['url']}/api/peer/handshake", timeout=5,
                headers={"X-Stellio-Peer-Key": row['peer_key']}
            )
            if r.ok:
                remote_info = r.json()
                conn.execute(
                    "UPDATE remote_instances SET last_status='online', last_seen_at=CURRENT_TIMESTAMP WHERE id=?",
                    (instance_id,)
                )
                conn.commit()
                return jsonify({"status": "online", "remote": remote_info}), 200
            conn.execute("UPDATE remote_instances SET last_status='error' WHERE id=?", (instance_id,))
            conn.commit()
            if r.status_code == 403:
                return jsonify({"status": "error", "error": "Clé d'appairage refusée par l'autre instance"}), 200
            return jsonify({"status": "error", "error": f"Réponse HTTP {r.status_code}"}), 200
        except Exception as e:
            conn.execute("UPDATE remote_instances SET last_status='offline' WHERE id=?", (instance_id,))
            conn.commit()
            return jsonify({"status": "offline", "error": "Instance injoignable"}), 200
    finally:
        conn.close()


@app.route('/api/remote-instances/<int:instance_id>/send', methods=['POST'])
@login_required
def api_remote_instances_send(instance_id):
    data = request.json or {}
    file_path = (data.get('file_path') or '').strip()
    if not file_path or not os.path.isfile(file_path):
        return jsonify({"error": "Fichier introuvable"}), 404
    if not _is_path_within_sources(file_path, session['user_id']):
        return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM remote_instances WHERE id=? AND user_id=?", (instance_id, session['user_id'])
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return jsonify({"error": "Instance introuvable"}), 404

    _cleanup_expired_shares()
    token = secrets.token_urlsafe(24)
    with _share_lock:
        _share_links[token] = {
            'path': file_path, 'name': os.path.basename(file_path), 'created': time.time(),
        }
    local_ip = get_local_ip()
    share_url = f"http://{local_ip}:5000/share/{token}"

    try:
        r = requests.post(
            f"{row['url']}/api/peer/receive-file", timeout=20,
            headers={"X-Stellio-Peer-Key": row['peer_key']},
            json={"url": share_url, "filename": os.path.basename(file_path)}
        )
        if r.ok:
            app_logger.info(f"[RemoteInstance] Fichier {os.path.basename(file_path)} envoyé vers '{row['name']}'")
            return jsonify({"success": True}), 200
        with _share_lock:
            _share_links.pop(token, None)
        if r.status_code == 403:
            return jsonify({"error": "Clé d'appairage refusée par l'autre instance"}), 502
        return jsonify({"error": f"L'autre instance a refusé le fichier (HTTP {r.status_code})"}), 502
    except Exception as e:
        with _share_lock:
            _share_links.pop(token, None)
        app_logger.warning(f"[RemoteInstance] Envoi échoué vers '{row['name']}': {e}")
        return jsonify({"error": "Instance injoignable"}), 503


@app.route('/api/peer/handshake', methods=['GET'])
@require_peer_key
def api_peer_handshake():
    settings = load_settings()
    return jsonify({
        "name": settings.get('instance_name') or platform.node(),
        "version": get_current_version(),
    }), 200


@app.route('/api/peer/receive-file', methods=['POST'])
@require_peer_key
def api_peer_receive_file():
    data = request.json or {}
    share_url = (data.get('url') or '').strip()
    filename = secure_filename((data.get('filename') or '').strip()) or 'fichier_recu'
    if not share_url:
        return jsonify({"error": "URL manquante"}), 400

    user_id = _get_primary_user_id()
    if not user_id:
        return jsonify({"error": "Aucun utilisateur configuré sur cette instance"}), 500

    conn = get_db()
    try:
        inbox_row = conn.execute(
            """SELECT inbox_folder FROM remote_instances
               WHERE user_id=? AND inbox_folder IS NOT NULL AND inbox_folder != '' LIMIT 1""",
            (user_id,)
        ).fetchone()
        inbox_folder = inbox_row['inbox_folder'] if inbox_row else None
        if not inbox_folder:
            folder_row = conn.execute(
                "SELECT path FROM sources WHERE user_id=? AND type='folder' LIMIT 1", (user_id,)
            ).fetchone()
            inbox_folder = folder_row['path'] if folder_row else None
    finally:
        conn.close()

    if not inbox_folder or not os.path.isdir(inbox_folder):
        return jsonify({"error": "Aucun dossier de réception disponible sur cette instance"}), 500

    try:
        r = requests.get(share_url, timeout=30, stream=True)
        if not r.ok:
            return jsonify({"error": f"Téléchargement échoué depuis l'instance émettrice (HTTP {r.status_code})"}), 502
        dest_path = os.path.join(inbox_folder, filename)
        base, ext = os.path.splitext(dest_path)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = f"{base} ({counter}){ext}"
            counter += 1
        with open(dest_path, 'wb') as out:
            for chunk in r.iter_content(chunk_size=65536):
                out.write(chunk)
        app_logger.info(f"[RemoteInstance] Fichier reçu et enregistré: {dest_path}")
        return jsonify({"success": True, "saved_as": os.path.basename(dest_path)}), 200
    except Exception as e:
        app_logger.warning(f"[RemoteInstance] Réception échouée: {e}")
        return jsonify({"error": "Échec de la récupération du fichier"}), 502


def _get_all_source_paths(user_id):
    try:
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT path, type FROM sources WHERE user_id = ?", (user_id,)
            ).fetchall()
        finally:
            conn.close()

        folders = [r['path'] for r in rows if r['type'] in ('folder', 'smb', 'nfs')]
        files = [r['path'] for r in rows if r['type'] == 'file']
        return folders, files
    except Exception:
        return [], []

def _is_path_within_sources(file_path, user_id):
    if not file_path:
        return False

    def _normalize_path(p):
        if not p:
            return ''
        norm = p.replace('\\', '/')
        if norm.startswith('//'):
            parts = norm.split('/')
            cleaned = [x for x in parts if x]
            if len(cleaned) >= 2:
                return '//' + '/'.join(cleaned)
            return norm
        else:
            try:
                return os.path.realpath(norm).replace('\\', '/')
            except Exception:
                return norm

    norm_file = _normalize_path(file_path)
    is_smb_file = norm_file.startswith('//')

    try:
        folders, files = _get_all_source_paths(user_id)
    except Exception:
        return False

    for f in files:
        norm_f = _normalize_path(f)
        if norm_f == norm_file:
            return True

    norm_file_cmp = norm_file.rstrip('/').lower()

    for folder in folders:
        norm_folder = _normalize_path(folder)
        is_smb_folder = norm_folder.startswith('//')
        norm_folder_cmp = norm_folder.rstrip('/').lower()

        if is_smb_file != is_smb_folder:
            continue

        folder_prefix = norm_folder_cmp + '/'
        if norm_file_cmp == norm_folder_cmp or norm_file_cmp.startswith(folder_prefix):
            return True

    app_logger.warning(f"[SECURITY] Rejet '{file_path}' — hors des sources configurées")
    return False

def _get_source_root_paths(user_id):
    try:
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT path FROM sources WHERE user_id = ? AND type IN ('folder', 'smb', 'nfs')", (user_id,)
            ).fetchall()
        finally:
            conn.close()
        return [r['path'] for r in rows]
    except Exception:
        return []

def _cleanup_empty_parent_dirs(file_path, stop_at_paths=None):
    stop_at = {os.path.normpath(p) for p in (stop_at_paths or [])}
    current = os.path.dirname(file_path)
    removed = []
    while current and os.path.isdir(current):
        if os.path.normpath(current) in stop_at:
            break
        try:
            if os.listdir(current):
                break
            os.rmdir(current)
            removed.append(current)
            app_logger.info(f"[DELETE] 📁 Dossier vide supprimé: {current}")
        except Exception as e:
            app_logger.warning(f"[DELETE] Impossible de supprimer le dossier vide {current}: {e}")
            break
        parent = os.path.dirname(current)
        if not parent or parent == current:
            break
        current = parent
    return removed

def _show_open_with_dialog_windows(file_path):
    import ctypes
    from ctypes import wintypes

    class OPENASINFO(ctypes.Structure):
        _fields_ = [
            ("pcszFile", wintypes.LPCWSTR),
            ("pcszClass", wintypes.LPCWSTR),
            ("oaifInFlags", wintypes.DWORD),
        ]

    OAIF_EXEC = 0x00000004
    OAIF_HIDE_REGISTRATION = 0x00000020
    COINIT_APARTMENTTHREADED = 0x2

    def _worker():
        ole32 = ctypes.windll.ole32
        hr_init = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        try:
            shell32 = ctypes.windll.shell32
            info = OPENASINFO(
                pcszFile=file_path,
                pcszClass=None,
                oaifInFlags=OAIF_EXEC | OAIF_HIDE_REGISTRATION,
            )
            hr = shell32.SHOpenWithDialog(None, ctypes.byref(info))
            if hr != 0:
                app_logger.info(f"[OpenWith] SHOpenWithDialog code retour: {hr:#x}")
        except Exception as e:
            app_logger.error(f"[OpenWith] SHOpenWithDialog a échoué: {e}")
        finally:
            if hr_init in (0, 1):  
                ole32.CoUninitialize()

    threading.Thread(target=_worker, daemon=True).start()


@app.route('/api/files/open-with', methods=['POST'])
@login_required
def api_open_file_with():
    try:
        data = request.json
        file_path = data.get('file_path', '').strip()
        if not file_path:
            return jsonify({"error": "Chemin du fichier requis"}), 400

        file_path = file_path.replace('/', '\\') if os.name == 'nt' else file_path.replace('\\', '/')

        if not os.path.exists(file_path):
            return jsonify({"error": "Fichier introuvable"}), 404
        if not os.path.isfile(file_path):
            return jsonify({"error": "Le chemin n'est pas un fichier"}), 400

        if not _is_path_within_sources(file_path, session['user_id']):
            app_logger.warning(f"[SECURITY] Tentative d'ouverture hors sources: {file_path}")
            return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

        try:
            if sys.platform == 'win32':
                _show_open_with_dialog_windows(file_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', '-R', file_path], check=False)
            else:
                if shutil.which('mimeopen'):
                    subprocess.run(['mimeopen', '-a', file_path], check=False)
                else:
                    subprocess.run(['xdg-open', file_path], check=False)
        except Exception as e:
            app_logger.error(f"[OpenWith] Échec ouverture {file_path}: {e}")
            return jsonify({"error": f"Impossible d'ouvrir le fichier : {str(e)}"}), 500

        return jsonify({"success": True, "message": "Sélectionnez une application"})
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/files/delete', methods=['POST'])
@login_required
def api_delete_file():
    try:
        data = request.json
        file_path = data.get('file_path', '').strip()
        if not file_path:
            return jsonify({"error": "Chemin du fichier requis"}), 400

        if is_virtual_archive_path(file_path):
            archive_path, internal_path = split_virtual_archive_path(file_path)
            return jsonify({
                "error": f"Ce fichier est à l'intérieur de l'archive '{os.path.basename(archive_path)}' — la suppression de fichiers individuels dans une archive n'est pas prise en charge.",
                "in_archive": True
            }), 400

        file_path = file_path.replace('/', '\\') if os.name == 'nt' else file_path.replace('\\', '/')

        if not os.path.exists(file_path):
            return jsonify({"error": "Fichier introuvable"}), 404
        if not os.path.isfile(file_path):
            return jsonify({"error": "Le chemin n'est pas un fichier"}), 400

        if not _is_path_within_sources(file_path, session['user_id']):
            app_logger.warning(f"[SECURITY] Tentative de suppression hors sources: {file_path}")
            return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

        filename = os.path.basename(file_path)
        normalized_path = file_path.replace('\\', '/')
        thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()

        for ext in ['.webp', '.png', '.jpg']:
            thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + ext)
            if os.path.exists(thumb_path):
                try:
                    os.remove(thumb_path)
                    app_logger.info(f"[DELETE] Miniature supprimée: {thumb_filename}{ext}")
                except Exception as e:
                    app_logger.warning(f"[DELETE] Erreur suppression miniature: {e}")

        os.remove(file_path)
        app_logger.info(f"[DELETE] ✅ Fichier supprimé: {filename}")

        try:
            _cleanup_empty_parent_dirs(file_path, stop_at_paths=_get_source_root_paths(session['user_id']))
        except Exception as e:
            app_logger.warning(f"[DELETE] Nettoyage dossier vide ignoré: {e}")

        invalidate_cache()

        return jsonify({
            "success": True,
            "message": f"Fichier '{filename}' supprimé avec succès"
        }), 200

    except PermissionError:
        app_logger.error(f"[DELETE] Permission refusée: {file_path}")
        return jsonify({"error": "Permission refusée. Le fichier est peut-être utilisé."}), 403
    except Exception as e:
        app_logger.error(f"[DELETE] Erreur: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/files/delete-batch', methods=['POST'])
@login_required
def api_delete_files_batch():
    try:
        data = request.json or {}
        file_paths = data.get('file_paths') or []
        if not file_paths:
            return jsonify({"error": "Aucun fichier à supprimer"}), 400

        deleted, errors = [], []
        source_roots = _get_source_root_paths(session['user_id'])
        for raw_path in file_paths:
            file_path = (raw_path or '').strip()
            if not file_path:
                continue
            try:
                if is_virtual_archive_path(file_path):
                    archive_path, _ = split_virtual_archive_path(file_path)
                    errors.append({
                        "path": file_path,
                        "error": f"Dans l'archive '{os.path.basename(archive_path)}' — non supprimable individuellement"
                    })
                    continue

                norm_path = file_path.replace('/', '\\') if os.name == 'nt' else file_path.replace('\\', '/')
                if not os.path.exists(norm_path) or not os.path.isfile(norm_path):
                    errors.append({"path": file_path, "error": "Fichier introuvable"})
                    continue

                if not _is_path_within_sources(norm_path, session['user_id']):
                    app_logger.warning(f"[SECURITY] Tentative de suppression hors sources: {norm_path}")
                    errors.append({"path": file_path, "error": "N'appartient à aucune source configurée"})
                    continue

                filename = os.path.basename(norm_path)
                normalized_path = norm_path.replace('\\', '/')
                thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()
                for ext in ['.webp', '.png', '.jpg']:
                    thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + ext)
                    if os.path.exists(thumb_path):
                        try:
                            os.remove(thumb_path)
                        except Exception as e:
                            app_logger.warning(f"[DELETE] Erreur suppression miniature: {e}")

                os.remove(norm_path)
                deleted.append(filename)
                try:
                    _cleanup_empty_parent_dirs(norm_path, stop_at_paths=source_roots)
                except Exception as e:
                    app_logger.warning(f"[DELETE] Nettoyage dossier vide ignoré: {e}")
            except PermissionError:
                errors.append({"path": file_path, "error": "Permission refusée (fichier peut-être utilisé)"})
            except Exception as e:
                errors.append({"path": file_path, "error": str(e)})

        if deleted:
            invalidate_cache()
            app_logger.info(f"[DELETE] ✅ {len(deleted)} fichier(s) supprimé(s) en lot")

        return jsonify({
            "success": len(errors) == 0,
            "deleted_count": len(deleted),
            "deleted": deleted,
            "errors": errors
        }), 200
    except Exception as e:
        app_logger.error(f"[DELETE] Erreur suppression en lot: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/files/rename', methods=['POST'])
@login_required
def api_rename_file():
    try:
        data = request.json
        file_path = (data.get('file_path') or '').strip()
        new_name  = (data.get('new_name') or '').strip()

        app_logger.info(f"[RENAME] Reçu: file_path={repr(file_path)}, new_name={repr(new_name)}")

        if not file_path or not new_name:
            return jsonify({"error": "Chemin et nouveau nom requis"}), 400

        if '..' in new_name or new_name.startswith('/') or new_name.startswith('\\'):
            return jsonify({"error": "Nom de fichier invalide"}), 400

        if os.name == 'nt':
            file_path = file_path.replace('/', '\\')
            app_logger.info(f"[RENAME] Chemin normalisé: {repr(file_path)}")

        app_logger.info(f"[RENAME] Fichier existe: {os.path.isfile(file_path)}")
        if not os.path.isfile(file_path):
            raw_path = (data.get('file_path') or '').strip()
            app_logger.info(f"[RENAME] Tentative chemin brut: {repr(raw_path)}, existe: {os.path.isfile(raw_path)}")
            return jsonify({"error": f"Fichier introuvable. Chemin reçu: {file_path}"}), 404

        if not _is_path_within_sources(file_path, session['user_id']):
            app_logger.warning(f"[SECURITY] Tentative de renommage hors sources: {file_path}")
            return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

        old_ext = os.path.splitext(file_path)[1]
        if not os.path.splitext(new_name)[1]:
            new_name = new_name + old_ext

        dir_path = os.path.dirname(file_path)
        new_path = os.path.join(dir_path, new_name)

        app_logger.info(f"[RENAME] Destination: {repr(new_path)}")
        if os.path.exists(new_path):
            return jsonify({"error": "Un fichier portant ce nom existe déjà"}), 409

        norm_old = file_path.replace('\\', '/')
        old_thumb_base = os.path.join(THUMBNAILS_DIR, hashlib.md5(norm_old.encode()).hexdigest())
        for ext in ['.webp', '.png', '.jpg']:
            p = old_thumb_base + ext
            if os.path.exists(p):
                try: os.remove(p)
                except: pass

        shutil.move(file_path, new_path)
        invalidate_cache()

        new_path_norm = new_path.replace('\\', '/')
        app_logger.info(f"[RENAME] ✅ {os.path.basename(file_path)} → {new_name}")

        return jsonify({"success": True, "message": f"Renommé en « {new_name} »", "new_path": new_path_norm}), 200

    except PermissionError:
        return jsonify({"error": "Permission refusée — fichier ouvert dans une autre application ?"}), 403
    except Exception as e:
        app_logger.error(f"[RENAME] Erreur: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/files/duplicates', methods=['GET'])
@login_required
def api_find_duplicates():
    try:
        conn = get_db()
        try:
            sources = conn.execute("SELECT * FROM sources WHERE user_id = ?", (session['user_id'],)).fetchall()
        finally:
            conn.close()

        all_files = []
        for source in sources:
            try:
                if source['type'] == 'folder' and os.path.exists(source['path']):
                    all_files.extend(scan_local_folder(source['path']))
            except Exception:
                pass

        groups = {}
        for f in all_files:
            key = (f['name'].lower(), f.get('size', 0))
            groups.setdefault(key, []).append(f)

        duplicates = []
        for (name, size), group in groups.items():
            if len(group) > 1:
                duplicates.append({
                    'name': group[0]['name'],
                    'size': size,
                    'count': len(group),
                    'files': [{'path': g['path'], 'source': g.get('source', ''),
                               'has_thumb': g.get('has_thumb', False),
                               'in_archive': g.get('in_archive', False),
                               'archive_name': g.get('archive_name', '')} for g in group]
                })

        duplicates.sort(key=lambda x: x['size'], reverse=True)
        return jsonify({"groups": duplicates, "total_groups": len(duplicates)}), 200

    except Exception as e:
        app_logger.error(f"[DUPLICATES] Erreur: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

SIMILAR_DUPLICATES_MAX_FILES = 250
SIMILAR_DUPLICATES_VOLUME_TOLERANCE = 0.03
SIMILAR_DUPLICATES_DIM_TOLERANCE = 0.03

def _geometric_signatures_match(sig_a, sig_b):
    vol_a, dims_a = sig_a
    vol_b, dims_b = sig_b
    if vol_a <= 0 or vol_b <= 0:
        return False
    if abs(vol_a - vol_b) / max(vol_a, vol_b) > SIMILAR_DUPLICATES_VOLUME_TOLERANCE:
        return False
    for da, db in zip(dims_a, dims_b):
        if max(da, db) <= 0:
            continue
        if abs(da - db) / max(da, db) > SIMILAR_DUPLICATES_DIM_TOLERANCE:
            return False
    return True

@app.route('/api/files/duplicates/similar', methods=['GET'])
@login_required
def api_find_similar_duplicates():
    try:
        conn = get_db()
        try:
            sources = conn.execute("SELECT * FROM sources WHERE user_id = ?", (session['user_id'],)).fetchall()
        finally:
            conn.close()

        all_files = []
        for source in sources:
            try:
                if source['type'] == 'folder' and os.path.exists(source['path']):
                    all_files.extend(scan_local_folder(source['path']))
            except Exception:
                pass

        GEO_EXTENSIONS = ('.stl', '.3mf', '.obj')
        candidates = [f for f in all_files if os.path.splitext(f['name'])[1].lower() in GEO_EXTENSIONS]

        exact_groups = {}
        for f in candidates:
            exact_groups.setdefault((f['name'].lower(), f.get('size', 0)), []).append(f)
        exact_dup_paths = {f['path'] for group in exact_groups.values() if len(group) > 1 for f in group}
        candidates = [f for f in candidates if f['path'] not in exact_dup_paths]

        truncated = False
        if len(candidates) > SIMILAR_DUPLICATES_MAX_FILES:
            candidates.sort(key=lambda f: f.get('size', 0), reverse=True)
            candidates = candidates[:SIMILAR_DUPLICATES_MAX_FILES]
            truncated = True

        analyzed = []
        for f in candidates:
            metadata = get_cached_3d_analysis(f['path'])
            if not metadata:
                continue
            dims = sorted(metadata['dimensions'].values())
            analyzed.append({
                'file': f,
                'signature': (metadata['volume_cm3'], dims),
                'volume_cm3': metadata['volume_cm3'],
                'dimensions': metadata['dimensions'],
                'triangle_count': metadata['triangle_count'],
            })

        groups = []
        for item in analyzed:
            placed = False
            for group in groups:
                if _geometric_signatures_match(group['ref_signature'], item['signature']):
                    group['items'].append(item)
                    placed = True
                    break
            if not placed:
                groups.append({'ref_signature': item['signature'], 'items': [item]})

        result_groups = []
        for group in groups:
            if len(group['items']) < 2:
                continue
            items = group['items']
            result_groups.append({
                'name': items[0]['file']['name'],
                'count': len(items),
                'volume_cm3': items[0]['volume_cm3'],
                'dimensions': items[0]['dimensions'],
                'files': [{
                    'path': it['file']['path'],
                    'name': it['file']['name'],
                    'source': it['file'].get('source', ''),
                    'has_thumb': it['file'].get('has_thumb', False),
                    'volume_cm3': it['volume_cm3'],
                    'dimensions': it['dimensions'],
                    'in_archive': it['file'].get('in_archive', False),
                    'archive_name': it['file'].get('archive_name', ''),
                } for it in items],
            })

        result_groups.sort(key=lambda g: g['volume_cm3'], reverse=True)
        return jsonify({
            "groups": result_groups,
            "total_groups": len(result_groups),
            "analyzed_count": len(analyzed),
            "candidate_count": len(candidates),
            "truncated": truncated,
        }), 200

    except Exception as e:
        app_logger.error(f"[SIMILAR-DUPLICATES] Erreur: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/stats', methods=['GET'])
@login_required
def api_get_stats():
    try:
        conn = get_db()
        try:
            user_id = session['user_id']

            cached = load_file_cache() or []
            total_files = len(cached)
            total_size  = sum(f.get('size', 0) for f in cached)

            by_format = {}
            for f in cached:
                ext = (f.get('extension') or '').lower()
                by_format[ext] = by_format.get(ext, 0) + 1

            fav_count = conn.execute(
                "SELECT COUNT(*) FROM favorites WHERE user_id=?", (user_id,)
            ).fetchone()[0]

            import calendar
            now = datetime.datetime.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_ts = month_start.timestamp()

            new_this_month = sum(
                1 for f in cached
                if (f.get('mtime') or 0) >= month_ts
            )

            top_printed = conn.execute(
                """SELECT file_name, COUNT(*) as cnt
                   FROM print_history WHERE user_id=?
                   GROUP BY file_name ORDER BY cnt DESC LIMIT 5""",
                (user_id,)
            ).fetchall()

            total_prints = conn.execute(
                "SELECT COUNT(*) FROM print_history WHERE user_id=?", (user_id,)
            ).fetchone()[0]

            cost_row = conn.execute(
                """SELECT COALESCE(SUM(total_cost), 0), COUNT(total_cost),
                          COALESCE(SUM(CASE WHEN sent_at >= ? THEN total_cost ELSE 0 END), 0)
                   FROM print_history WHERE user_id=? AND total_cost IS NOT NULL""",
                (month_start.strftime('%Y-%m-%d %H:%M:%S'), user_id)
            ).fetchone()
            total_spent = round(cost_row[0] or 0, 2)
            costed_prints = cost_row[1] or 0
            spent_this_month = round(cost_row[2] or 0, 2)
            avg_cost_per_print = round(total_spent / costed_prints, 2) if costed_prints else None

            failed_cost_row = conn.execute(
                """SELECT COALESCE(SUM(total_cost), 0), COUNT(*)
                   FROM print_history WHERE user_id=? AND result='failed' AND total_cost IS NOT NULL""",
                (user_id,)
            ).fetchone()
            failed_prints_cost = round(failed_cost_row[0] or 0, 2)
            failed_prints_count = failed_cost_row[1] or 0

            platform_rows = conn.execute(
                """SELECT platform, COUNT(*) as cnt
                   FROM download_history
                   WHERE user_id=? AND platform != ''
                   GROUP BY platform ORDER BY cnt DESC""",
                (user_id,)
            ).fetchall()
        finally:
            conn.close()

        by_platform = {r["platform"]: r["cnt"] for r in platform_rows}

        conn2 = get_db()
        reliability_rows = conn2.execute(
            """SELECT slicer_profile_name, result, COUNT(*) as cnt
               FROM print_history
               WHERE user_id=? AND slicer_profile_name != '' AND slicer_profile_name IS NOT NULL
               GROUP BY slicer_profile_name, result""",
            (user_id,)
        ).fetchall()
        reliability_by_profile = {}
        for r in reliability_rows:
            entry = reliability_by_profile.setdefault(r["slicer_profile_name"], {"success": 0, "failed": 0, "unrated": 0})
            if r["result"] == "success":
                entry["success"] += r["cnt"]
            elif r["result"] == "failed":
                entry["failed"] += r["cnt"]
            else:
                entry["unrated"] += r["cnt"]
        profile_reliability = []
        for name, counts in reliability_by_profile.items():
            rated = counts["success"] + counts["failed"]
            total = rated + counts["unrated"]
            profile_reliability.append({
                "name": name,
                "success": counts["success"],
                "failed": counts["failed"],
                "unrated": counts["unrated"],
                "total": total,
                "success_rate": round(counts["success"] / rated * 100, 1) if rated > 0 else None,
            })
        profile_reliability.sort(key=lambda p: (p["success_rate"] is None, -(p["success_rate"] or 0)))
        conn2.close()

        platform_keywords = {
            'thingiverse': 'Thingiverse',
            'printables': 'Printables',
            'makerworld': 'MakerWorld',
        }
        for f in cached:
            path_lower = (f.get('path') or '').lower().replace('\\', '/')
            name_lower = (f.get('name') or '').lower()
            for kw, label in platform_keywords.items():
                if kw in path_lower or kw in name_lower:
                    if label not in by_platform:
                        by_platform[label] = by_platform.get(label, 0) + 1
                    break

        return jsonify({
            "total_files": total_files,
            "total_size": total_size,
            "by_format": by_format,
            "favorites": fav_count,
            "new_this_month": new_this_month,
            "total_prints": total_prints,
            "total_spent": total_spent,
            "spent_this_month": spent_this_month,
            "avg_cost_per_print": avg_cost_per_print,
            "failed_prints_cost": failed_prints_cost,
            "failed_prints_count": failed_prints_count,
            "top_printed": [{"name": r["file_name"], "count": r["cnt"]} for r in top_printed],
            "by_platform": by_platform,
            "profile_reliability": profile_reliability,
        }), 200

    except Exception as e:
        app_logger.error(f"[Stats] Erreur: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/print-history', methods=['GET'])
@login_required
def api_get_print_history():
    try:
        limit_raw = request.args.get('limit', 50)
        offset_raw = request.args.get('offset', 0)
        try:
            limit = int(limit_raw)
            offset = int(offset_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "Paramètres 'limit'/'offset' invalides"}), 400
        limit = max(1, min(limit, 500))
        offset = max(0, offset)

        conn = get_db()
        try:
            rows = conn.execute(
                """SELECT id, file_path, file_name, file_size, file_ext, slicer, sent_at, source_platform,
                          result, failure_reason, rating_notes, slicer_profile_id, slicer_profile_name, rated_at,
                          material_cost, elec_cost, total_cost
                   FROM print_history WHERE user_id=?
                   ORDER BY sent_at DESC LIMIT ? OFFSET ?""",
                (session['user_id'], limit, offset)
            ).fetchall()

            total = conn.execute(
                "SELECT COUNT(*) FROM print_history WHERE user_id=?", (session['user_id'],)
            ).fetchone()[0]
        finally:
            conn.close()

        return jsonify({
            "history": [dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset
        }), 200

    except Exception as e:
        app_logger.error(f"[PrintHistory] Erreur: {e}")
        return jsonify({"error": "Erreur lors de la récupération de l'historique"}), 500

@app.route('/api/print-history/<int:entry_id>', methods=['DELETE'])
@login_required
def api_delete_print_history(entry_id):
    try:
        conn = get_db()
        try:
            conn.execute(
                "DELETE FROM print_history WHERE id=? AND user_id=?",
                (entry_id, session['user_id'])
            )
            conn.commit()
        finally:
            conn.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/print-history/clear', methods=['DELETE'])
@login_required
def api_clear_print_history():
    try:
        conn = get_db()
        try:
            conn.execute("DELETE FROM print_history WHERE user_id=?", (session['user_id'],))
            conn.commit()
        finally:
            conn.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

VALID_PRINT_RESULTS = ('success', 'failed', 'partial')

@app.route('/api/print-history/<int:entry_id>/rate', methods=['POST'])
@login_required
def api_rate_print_history(entry_id):
    data = request.json or {}
    result = data.get('result')
    if result not in VALID_PRINT_RESULTS:
        return jsonify({"error": f"result doit être l'un de : {', '.join(VALID_PRINT_RESULTS)}"}), 400

    failure_reason = (data.get('failure_reason') or '').strip()[:100]
    notes = (data.get('notes') or '').strip()[:500]

    try:
        conn = get_db()
        try:
            cur = conn.execute(
                """UPDATE print_history SET result=?, failure_reason=?, rating_notes=?, rated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND user_id=?""",
                (result, failure_reason, notes, entry_id, session['user_id'])
            )
            conn.commit()
            found = cur.rowcount > 0
        finally:
            conn.close()
        if not found:
            return jsonify({"error": "Entrée introuvable"}), 404
        return jsonify({"success": True}), 200
    except Exception as e:
        app_logger.error(f"[PrintHistory] Notation échouée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/print-history/<int:entry_id>/cost', methods=['POST'])
@login_required
def api_set_print_history_cost(entry_id):
    data = request.json or {}

    def _parse_cost(value):
        if value in (None, ''):
            return None
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        return round(max(0, v), 4)

    material_cost = _parse_cost(data.get('material_cost'))
    elec_cost = _parse_cost(data.get('elec_cost'))
    total_cost = None
    if material_cost is not None or elec_cost is not None:
        total_cost = round((material_cost or 0) + (elec_cost or 0), 4)

    try:
        conn = get_db()
        try:
            cur = conn.execute(
                """UPDATE print_history SET material_cost=?, elec_cost=?, total_cost=?
                   WHERE id=? AND user_id=?""",
                (material_cost, elec_cost, total_cost, entry_id, session['user_id'])
            )
            conn.commit()
            found = cur.rowcount > 0
        finally:
            conn.close()
        if not found:
            return jsonify({"error": "Entrée introuvable"}), 404
        return jsonify({"success": True, "material_cost": material_cost, "elec_cost": elec_cost, "total_cost": total_cost}), 200
    except Exception as e:
        app_logger.error(f"[PrintHistory] Mise à jour coût échouée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


PRINT_PHOTO_ALLOWED_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
PRINT_PHOTO_MAX_SIZE = 15 * 1024 * 1024


@app.route('/api/print-photos', methods=['GET'])
@login_required
def api_get_print_photos():
    file_path = request.args.get('path', '').replace('\\', '/')
    result_filter = request.args.get('result', '').strip().lower()
    conn = get_db()
    try:
        query = "SELECT id, file_path, image_filename, note, result, created_at FROM print_photos WHERE user_id=?"
        params = [session['user_id']]
        if file_path:
            query += " AND file_path=?"
            params.append(file_path)
        if result_filter in ('success', 'failed'):
            query += " AND result=?"
            params.append(result_filter)
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    return jsonify([{
        "id": r["id"],
        "file_path": r["file_path"],
        "file_name": os.path.basename(r["file_path"]),
        "url": f"/api/print-photos/{r['id']}/image",
        "note": r["note"],
        "result": r["result"] or "success",
        "created_at": r["created_at"],
    } for r in rows])


@app.route('/api/print-photos', methods=['POST'])
@login_required
def api_add_print_photo():
    file_path = (request.form.get('path') or '').replace('\\', '/')
    note = (request.form.get('note') or '').strip()[:300]
    result = (request.form.get('result') or 'success').strip().lower()
    if result not in ('success', 'failed'):
        result = 'success'
    photo = request.files.get('photo')

    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400
    if not photo or not photo.filename:
        return jsonify({"error": "Image requise"}), 400

    ext = os.path.splitext(photo.filename)[1].lower()
    if ext not in PRINT_PHOTO_ALLOWED_EXTS:
        return jsonify({"error": f"Format non supporté (attendu : {', '.join(sorted(PRINT_PHOTO_ALLOWED_EXTS))})"}), 400

    photo.seek(0, os.SEEK_END)
    size = photo.tell()
    photo.seek(0)
    if size > PRINT_PHOTO_MAX_SIZE:
        return jsonify({"error": "Image trop volumineuse (15 Mo max)"}), 400

    image_filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(PRINT_PHOTOS_DIR, image_filename)
    try:
        photo.save(dest_path)
        try:
            img = Image.open(dest_path)
            img.thumbnail((1600, 1600))
            img.convert('RGB').save(dest_path, quality=85, optimize=True) if ext in ('.jpg', '.jpeg') else img.save(dest_path)
        except Exception:
            pass

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO print_photos (user_id, file_path, image_filename, note, result) VALUES (?, ?, ?, ?, ?)",
                (session['user_id'], file_path, image_filename, note, result)
            )
            conn.commit()
            new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        finally:
            conn.close()
        return jsonify({"id": new_id, "url": f"/api/print-photos/{new_id}/image", "note": note, "result": result}), 201
    except Exception as e:
        app_logger.error(f"[PrintPhotos] Upload échoué: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/print-photos/<int:photo_id>/image', methods=['GET'])
@login_required
def api_get_print_photo_image(photo_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT image_filename FROM print_photos WHERE id=? AND user_id=?",
            (photo_id, session['user_id'])
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return jsonify({"error": "Introuvable"}), 404
    img_path = os.path.join(PRINT_PHOTOS_DIR, row["image_filename"])
    if not os.path.exists(img_path):
        return jsonify({"error": "Fichier image manquant"}), 404
    return send_file(img_path)


@app.route('/api/print-photos/<int:photo_id>', methods=['DELETE'])
@login_required
def api_delete_print_photo(photo_id):
    conn = get_db()
    row = conn.execute(
        "SELECT image_filename FROM print_photos WHERE id=? AND user_id=?",
        (photo_id, session['user_id'])
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Introuvable"}), 404
    conn.execute("DELETE FROM print_photos WHERE id=? AND user_id=?", (photo_id, session['user_id']))
    conn.commit()
    conn.close()
    try:
        os.remove(os.path.join(PRINT_PHOTOS_DIR, row["image_filename"]))
    except Exception:
        pass
    return jsonify({"success": True}), 200


@app.route('/api/browse-folder', methods=['POST'])
@login_required
def api_browse_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(title="Choisir le dossier de destination")
        root.destroy()

        if folder:
            folder = folder.replace('/', '\\') if os.name == 'nt' else folder
            return jsonify({"success": True, "path": folder}), 200
        else:
            return jsonify({"success": False, "path": None}), 200

    except Exception as e:
        app_logger.error(f"[BROWSE] Erreur: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/files/move', methods=['POST'])
@login_required
def api_move_file():
    try:
        data = request.json
        source_path = data.get('source_path', '').strip()
        destination_folder = data.get('destination_folder', '').strip()

        if not source_path or not destination_folder:
            return jsonify({"error": "Chemin source et destination requis"}), 400

        source_path = source_path.replace('/', '\\') if os.name == 'nt' else source_path.replace('\\', '/')
        destination_folder = destination_folder.replace('/', '\\') if os.name == 'nt' else destination_folder.replace('\\', '/')

        if not os.path.exists(source_path):
            app_logger.warning(f"[MOVE] Fichier source introuvable: {source_path}")
            return jsonify({"error": "Fichier source introuvable"}), 404
        if not os.path.isfile(source_path):
            return jsonify({"error": "La source n'est pas un fichier"}), 400

        if not _is_path_within_sources(source_path, session['user_id']):
            app_logger.warning(f"[SECURITY] Tentative de déplacement hors sources (source): {source_path}")
            return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403
        if not _is_path_within_sources(destination_folder, session['user_id']):
            app_logger.warning(f"[SECURITY] Tentative de déplacement hors sources (destination): {destination_folder}")
            return jsonify({"error": "Le dossier de destination n'appartient à aucune source configurée"}), 403

        if not os.path.exists(destination_folder):
            try:
                os.makedirs(destination_folder, exist_ok=True)
                app_logger.info(f"[MOVE] Dossier destination créé: {destination_folder}")
            except Exception as e:
                return jsonify({"error": f"Impossible de créer le dossier: {str(e)}"}), 500

        if not os.path.isdir(destination_folder):
            return jsonify({"error": "La destination n'est pas un dossier"}), 400

        filename = os.path.basename(source_path)
        dest_path = os.path.join(destination_folder, filename)

        if os.path.exists(dest_path):
            name, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(destination_folder, f"{name}_{counter}{ext}")
                counter += 1
            app_logger.info(f"[MOVE] Conflit de nom résolu: {os.path.basename(dest_path)}")

        if os.path.normpath(os.path.dirname(source_path)) == os.path.normpath(destination_folder):
            return jsonify({"error": "Le fichier est déjà dans ce dossier"}), 400

        try:
            shutil.move(source_path, dest_path)
            app_logger.info(f"[MOVE] ✅ Fichier déplacé: {filename} → {destination_folder}")

            normalized_path = source_path.replace('\\', '/')
            thumb_filename = hashlib.md5(normalized_path.encode()).hexdigest()

            for ext in ['.webp', '.png', '.jpg']:
                thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename + ext)
                if os.path.exists(thumb_path):
                    try:
                        os.remove(thumb_path)
                        app_logger.info(f"[MOVE] Miniature supprimée: {thumb_filename}{ext}")
                    except Exception as e:
                        app_logger.warning(f"[MOVE] Erreur suppression miniature: {e}")

            invalidate_cache()

            return jsonify({
                "success": True,
                "message": f"Fichier déplacé vers {os.path.basename(destination_folder)}",
                "new_path": dest_path.replace('\\', '/'),
                "filename": os.path.basename(dest_path)
            }), 200

        except PermissionError:
            app_logger.error(f"[MOVE] Permission refusée: {source_path}")
            return jsonify({"error": "Permission refusée. Le fichier est peut-être utilisé par une autre application."}), 403
        except Exception as e:
            app_logger.error(f"[MOVE] Erreur déplacement: {e}")
            return jsonify({"error": f"Erreur lors du déplacement: {str(e)}"}), 500

    except Exception as e:
        app_logger.error(f"[MOVE] Erreur générale: {e}")
        import traceback
        traceback.print_exc()
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/files/decompress', methods=['POST'])
@login_required
def api_decompress_archive():
    data = request.json
    archive_path = data.get('file_path')
    if not archive_path or not os.path.exists(archive_path):
        return jsonify({"error": "Archive non trouvée"}), 404
    if not _is_path_within_sources(archive_path, session['user_id']):
        app_logger.warning(f"[SECURITY] Tentative de décompression hors sources: {archive_path}")
        return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

    ext = os.path.splitext(archive_path)[1].lower()
    extract_dir = os.path.dirname(archive_path)
    archive_name = os.path.splitext(os.path.basename(archive_path))[0]
    target_dir = os.path.join(extract_dir, archive_name)
    os.makedirs(target_dir, exist_ok=True)

    try:
        if ext == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                safe_extract_zip(zip_ref, target_dir)
                extracted_files = zip_ref.namelist()
        elif ext in ['.tar.gz', '.tgz', '.tar.bz2', '.tar.xz', '.tar']:
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                safe_extract_tar(tar_ref, target_dir)
                extracted_files = tar_ref.getnames()
        elif ext == '.7z':
            try:
                import py7zr
                with py7zr.SevenZipFile(archive_path, mode='r') as z:
                    safe_extract_7z(z, target_dir)
                    extracted_files = z.getnames()
            except ImportError:
                shutil.rmtree(target_dir, ignore_errors=True)
                return jsonify({"error": "Module 'py7zr' manquant"}), 500
        elif ext == '.rar':
            try:
                with rarfile.RarFile(archive_path, 'r') as rf:
                    safe_extract_rar(rf, target_dir)
                    extracted_files = rf.namelist()
            except ImportError:
                shutil.rmtree(target_dir, ignore_errors=True)
                return jsonify({"error": "Module 'rarfile' manquant"}), 500
        else:
            return jsonify({"error": "Format non supporté"}), 400

        found_3d_files = []
        for f in extracted_files:
            full_path = os.path.join(target_dir, f)
            if os.path.isfile(full_path) and os.path.splitext(f)[1].lower() in SUPPORTED_3D_EXTS:
                found_3d_files.append(full_path)

        return jsonify({
            "success": True,
            "archive_path": archive_path,
            "extracted_folder": target_dir,
            "found_3d_files": found_3d_files,
            "message": f"Extraction terminée. {len(found_3d_files)} fichier(s) 3D trouvé(s)."
        }), 200

    except Exception as e:
        if os.path.exists(target_dir) and not os.listdir(target_dir):
            os.rmdir(target_dir)
        return jsonify({"error": f"Erreur extraction: {str(e)}"}), 500

@app.route('/api/archive/extract-entry', methods=['POST'])
@login_required
def api_archive_extract_entry():
    data = request.json or {}
    archive_path = data.get('archive_path')
    internal_path = data.get('internal_path')

    if not archive_path or not internal_path:
        return jsonify({"error": "Paramètres manquants"}), 400
    if not os.path.exists(archive_path):
        return jsonify({"error": "Archive non trouvée"}), 404

    try:
        raw_bytes = read_archive_entry_bytes(archive_path, internal_path)
    except Exception as e:
        return jsonify({"error": f"Lecture de l'archive impossible: {e}"}), 500

    try:
        target_dir = os.path.dirname(archive_path)
        target_name = os.path.basename(internal_path)
        target_path = os.path.join(target_dir, target_name)
        base, ext_ = os.path.splitext(target_path)
        counter = 1
        while os.path.exists(target_path):
            target_path = f"{base} ({counter}){ext_}"
            counter += 1

        with open(target_path, 'wb') as f:
            f.write(raw_bytes)

        invalidate_cache()
        return jsonify({
            "success": True,
            "extracted_path": target_path.replace('\\', '/'),
            "message": f"{target_name} extrait avec succès."
        }), 200
    except Exception as e:
        return jsonify({"error": f"Erreur écriture disque: {str(e)}"}), 500

@app.route('/api/files/cleanup-archive', methods=['POST'])
@login_required
def api_cleanup_archive():
    data = request.json
    archive_path = data.get('archive_path')
    if not archive_path or not os.path.exists(archive_path):
        return jsonify({"error": "Archive déjà supprimée"}), 404

    try:
        os.remove(archive_path)
        invalidate_cache()
        return jsonify({"success": True, "message": "Archive supprimée"}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


def get_slice_temp_dir():
    base = os.path.join(os.environ.get('LOCALAPPDATA', tempfile.gettempdir()), 'Stellio', 'SliceTemp')
    os.makedirs(base, exist_ok=True)
    return base


VIEWER_ORIENTATION_ROTATIONS = {
    'flipZ': ('x', 180),
    'posX':  ('y', 90),
    'negX':  ('y', -90),
    'posY':  ('x', -90),
    'negY':  ('x', 90),
}

def _export_reoriented_mesh(file_path, orientation_key):
    if not orientation_key or orientation_key == 'default':
        return None
    axis_deg = VIEWER_ORIENTATION_ROTATIONS.get(orientation_key)
    if not axis_deg:
        return None
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ('.stl', '.obj', '.3mf', '.ply'):
        return None

    try:
        mesh = trimesh.load(file_path, force='mesh')
        axis, degrees = axis_deg
        direction = [1, 0, 0] if axis == 'x' else [0, 1, 0]
        rot = tra.rotation_matrix(np.radians(degrees), direction)
        mesh.apply_transform(rot)

        out_dir = get_slice_temp_dir()
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        out_path = os.path.join(out_dir, f"{base_name}_{orientation_key}_{secrets.token_hex(4)}.stl")
        mesh.export(out_path, file_type='stl')
        return out_path
    except Exception as e:
        app_logger.warning(f"[Slicer] Échec ré-orientation du mesh avant envoi: {e}")
        return None

def _popen_kwargs_silent():
    kwargs = {}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs

def _slicer_search_roots():
    roots = []
    for env_var in ('ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)'):
        p = os.environ.get(env_var)
        if p and p not in roots:
            roots.append(p)
    local_appdata = os.environ.get('LOCALAPPDATA')
    if local_appdata:
        programs = os.path.join(local_appdata, 'Programs')
        if programs not in roots:
            roots.append(programs)
    return roots

def _find_exe_by_glob(relative_patterns):
    for root in _slicer_search_roots():
        for pattern in relative_patterns:
            try:
                matches = glob.glob(os.path.join(root, pattern))
            except Exception:
                matches = []
            if matches:
                return sorted(matches)[-1]
    return None

def _find_exe_in_registry(exe_names):
    if sys.platform != 'win32':
        return None
    try:
        import winreg
    except ImportError:
        return None
    for exe_name in exe_names:
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
                with winreg.OpenKey(hive, key_path) as key:
                    value, _ = winreg.QueryValueEx(key, None)
                    if value and os.path.exists(value):
                        return value
            except OSError:
                continue
    return None

def _locate_slicer(relative_patterns, registry_exe_names):
    found = _find_exe_by_glob(relative_patterns)
    if found:
        return found
    return _find_exe_in_registry(registry_exe_names)

def detect_installed_slicers():
    candidates = [
        ('orcaslicer', 'OrcaSlicer', [
            "OrcaSlicer/orca-slicer.exe",
            "OrcaSlicer*/orca-slicer.exe",
        ], ['orca-slicer.exe', 'OrcaSlicer.exe']),
        ('bambustudio', 'Bambu Studio', [
            "Bambu Studio/bambu-studio.exe",
            "Bambu Studio*/bambu-studio.exe",
        ], ['bambu-studio.exe']),
        ('prusaslicer', 'PrusaSlicer', [
            "Prusa3D/PrusaSlicer/prusa-slicer-console.exe",
            "Prusa3D/PrusaSlicer/prusa-slicer.exe",
            "PrusaSlicer/prusa-slicer-console.exe",
            "PrusaSlicer/prusa-slicer.exe",
        ], ['prusa-slicer-console.exe', 'prusa-slicer.exe']),
        ('superslicer', 'SuperSlicer', [
            "SuperSlicer/superslicer_console.exe",
            "SuperSlicer/superslicer.exe",
        ], ['superslicer_console.exe', 'superslicer.exe']),
        ('crealityprint', 'Creality Print', [
            "Creality Print/*/Creality Print.exe",
            "Creality Print/Creality Print.exe",
            "CrealityPrint/*/CrealityPrint.exe",
        ], ['Creality Print.exe', 'CrealityPrint.exe']),
        ('elegooslicer', 'Elegoo Slicer', [
            "ElegooSlicer/ElegooSlicer.exe",
            "ElegooSlicer*/ElegooSlicer.exe",
        ], ['ElegooSlicer.exe']),
        ('anycubicslicernext', 'Anycubic Slicer Next', [
            "Anycubic Slicer Next/AnycubicSlicerNext.exe",
            "Anycubic Slicer Next*/AnycubicSlicerNext.exe",
            "AnycubicSlicerNext/AnycubicSlicerNext.exe",
        ], ['AnycubicSlicerNext.exe']),
        ('anycubicslicer', 'Anycubic Slicer', [
            "AnycubicSlicer/Anycubic-Slicer.exe",
        ], ['Anycubic-Slicer.exe']),
        ('simplify3d', 'Simplify3D', [
            "Simplify3D*/Simplify3D.exe",
        ], ['Simplify3D.exe']),
        ('ideamaker', 'ideaMaker', [
            "Raise3D/ideaMaker/ideaMaker.exe",
            "ideaMaker/ideaMaker.exe",
            "ideaMaker*/ideaMaker.exe",
        ], ['ideaMaker.exe']),
        ('flashprint', 'FlashPrint', [
            "FlashPrint/FlashPrint.exe",
            "FlashPrint*/FlashPrint.exe",
        ], ['FlashPrint.exe']),
        ('lycheeslicer', 'Lychee Slicer', [
            "LycheeSlicer/LycheeSlicer.exe",
            "LycheeSlicer*/LycheeSlicer.exe",
        ], ['LycheeSlicer.exe']),
        ('craftware', 'CraftWare', [
            "CraftWare/CraftWare.exe",
            "CraftWare*/CraftWare.exe",
            "CraftWarePro/CraftWarePro.exe",
        ], ['CraftWare.exe', 'CraftWarePro.exe']),
        ('mattercontrol', 'MatterControl', [
            "MatterControl/MatterControl.exe",
            "MatterHackers/MatterControl/MatterControl.exe",
        ], ['MatterControl.exe']),
        ('makerbotprint', 'MakerBot Print', [
            "MakerBot Print/MakerBotPrint.exe",
            "MakerBot Print*/MakerBotPrint.exe",
        ], ['MakerBotPrint.exe']),
        ('voxelizer', 'Voxelizer', [
            "Voxelizer/Voxelizer.exe",
            "ZMorph*/Voxelizer.exe",
        ], ['Voxelizer.exe']),
        ('slic3r', 'Slic3r', [
            "Slic3r/slic3r.exe",
        ], ['slic3r.exe', 'slic3r-console.exe']),
        ('kisslicer', 'KISSlicer', [
            "KISSlicer*/KISSlicer.exe",
            "KISSlicer*/KISSlicer-x64.exe",
        ], ['KISSlicer.exe', 'KISSlicer-x64.exe']),
    ]
    found = []
    for slicer_id, label, patterns, registry_names in candidates:
        path = _locate_slicer(patterns, registry_names)
        if path:
            found.append({'id': slicer_id, 'name': label, 'path': path})

    try:
        cura_patterns = [
            "Ultimaker Cura*", "UltiMaker Cura*", "Cura*",
            "Elegoo Cura*", "Creality Slicer*", "CrealitySlicer*",
            "Cura LulzBot*", "LulzBot Cura*", "Longer3D Cura*", "Sovol Cura*",
        ]
        for root in _slicer_search_roots():
            found_cura = False
            for pattern in cura_patterns:
                for install_dir in glob.glob(os.path.join(root, pattern)):
                    engine_path = os.path.join(install_dir, 'CuraEngine.exe')
                    definitions_dir = os.path.join(install_dir, 'share', 'cura', 'resources', 'definitions')
                    if not os.path.exists(definitions_dir):
                        definitions_dir = os.path.join(install_dir, 'resources', 'definitions')
                    if os.path.exists(engine_path) and os.path.exists(definitions_dir):
                        found.append({
                            'id': 'cura', 'name': 'Cura', 'path': engine_path,
                            'definitions_dir': definitions_dir
                        })
                        found_cura = True
                        break
                if found_cura:
                    break
            if found_cura:
                break
    except Exception:
        pass

    try:
        settings = load_settings()
        custom_path = (settings.get('custom_slicer_path') or '').strip()
        custom_args = (settings.get('custom_slicer_args') or '').strip()
        if custom_path and os.path.exists(custom_path) and custom_args:
            found.append({
                'id': 'custom',
                'name': (settings.get('custom_slicer_name') or 'Slicer personnalisé').strip(),
                'path': custom_path,
                'args_template': custom_args,
                'output_type': (settings.get('custom_slicer_output_type') or 'gcode').strip()
            })
    except Exception as e:
        app_logger.info(f"[PreSlice] Erreur lecture config slicer personnalisé: {e}")

    try:
        preferred = (load_settings().get('preferred_slicer_id') or '').strip()
        if preferred:
            found.sort(key=lambda f: 0 if f['id'] == preferred else 1)
    except Exception:
        pass

    return found

_installed_slicers_cache = {'result': None, 'ts': 0}
def get_cached_installed_slicers(force=False):
    now = time.time()
    if force or _installed_slicers_cache['result'] is None or (now - _installed_slicers_cache['ts']) > 300:
        _installed_slicers_cache['result'] = detect_installed_slicers()
        _installed_slicers_cache['ts'] = now
    return _installed_slicers_cache['result']

def _parse_duration_to_seconds(raw):
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    raw = str(raw).strip()
    if raw.isdigit():
        return int(raw)
    total = 0
    matches = re.findall(r'(\d+)\s*([dhms])', raw.lower())
    for value, unit in matches:
        value = int(value)
        total += {'d': 86400, 'h': 3600, 'm': 60, 's': 1}[unit] * value
    return total if total > 0 else None

def _seconds_to_result(weight_g, seconds):
    result = {}
    if weight_g is not None:
        try:
            result['weight_g'] = round(float(weight_g), 1)
        except (TypeError, ValueError):
            pass
    if seconds is not None:
        try:
            seconds = int(seconds)
            hours, minutes = seconds // 3600, (seconds % 3600) // 60
            result['time_seconds'] = seconds
            result['time_formatted'] = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"
        except (TypeError, ValueError):
            pass
    return result or None

def _extract_gcode_from_gcode3mf(gcode3mf_path):
    try:
        with zipfile.ZipFile(gcode3mf_path, 'r') as zf:
            gcode_entries = sorted([n for n in zf.namelist() if n.lower().endswith('.gcode')])
            if not gcode_entries:
                return None
            plate1 = [n for n in gcode_entries if 'plate_1' in n.lower()]
            target = plate1[0] if plate1 else gcode_entries[0]
            return zf.read(target).decode('utf-8', errors='ignore')
    except Exception as e:
        app_logger.info(f"[PreSlice] Erreur lecture .gcode.3mf: {e}")
        return None

_WEIGHT_PATTERNS = [
    r'(?:total\s+)?filament used\s*\[g\]\s*[:=]\s*([\d.]+)',
    r'total filament weight\s*\[g\]\s*[:=]\s*([\d.]+)',
    r'total[_ ]filament[_ ]used\s*[:=]\s*([\d.]+)\s*g',
    r'filament_used_g\s*[:=]\s*([\d.]+)',
]
_TIME_PATTERNS = [
    r'total estimated time\s*[:=]\s*([^\n\r;]+)',
    r'estimated printing time[^=:]*[:=]\s*([^\n\r;]+)',
    r'model printing time\s*[:=]\s*([^\n\r;]+)',
    r'estimated_time\s*[:=]\s*([^\n\r;]+)',
]
_CURA_TIME_PATTERN = r';TIME:\s*(\d+)'
_CURA_FILAMENT_LENGTH_PATTERN = r';Filament used:\s*([\d.]+)m'
DEFAULT_FILAMENT_DIAMETER_MM = 1.75
DEFAULT_FILAMENT_DENSITY_G_CM3 = 1.24

def _filament_length_m_to_weight_g(length_m, diameter_mm=DEFAULT_FILAMENT_DIAMETER_MM, density=DEFAULT_FILAMENT_DENSITY_G_CM3):
    radius_cm = (diameter_mm / 10) / 2
    volume_cm3 = 3.14159265 * (radius_cm ** 2) * (length_m * 100)
    return volume_cm3 * density

def _extract_weight_time_from_gcode_text(blob, is_cura=False):
    weight_g = None
    seconds = None

    if is_cura:
        m = re.search(_CURA_TIME_PATTERN, blob)
        if m:
            seconds = int(m.group(1))
        m = re.search(_CURA_FILAMENT_LENGTH_PATTERN, blob)
        if m:
            try:
                weight_g = _filament_length_m_to_weight_g(float(m.group(1)))
            except ValueError:
                pass
        result = _seconds_to_result(weight_g, seconds)
        if result:
            result['weight_approximate'] = True
        return result

    for pattern in _WEIGHT_PATTERNS:
        m = re.search(pattern, blob, re.IGNORECASE)
        if m:
            try:
                weight_g = float(m.group(1))
                break
            except ValueError:
                continue

    for pattern in _TIME_PATTERNS:
        m = re.search(pattern, blob, re.IGNORECASE)
        if m:
            seconds = _parse_duration_to_seconds(m.group(1))
            if seconds:
                break

    return _seconds_to_result(weight_g, seconds)

def parse_bambu_orca_gcode3mf(gcode3mf_path):
    gcode_text = _extract_gcode_from_gcode3mf(gcode3mf_path)
    if not gcode_text:
        return None
    blob = gcode_text[:6000] + '\n' + gcode_text[-6000:]
    return _extract_weight_time_from_gcode_text(blob)

def parse_slic3r_derived_gcode(gcode_path):
    if not os.path.exists(gcode_path):
        return None
    try:
        file_size = os.path.getsize(gcode_path)
        with open(gcode_path, 'rb') as f:
            f.seek(max(0, file_size - 8192))
            tail = f.read().decode('utf-8', errors='ignore')
        with open(gcode_path, 'r', encoding='utf-8', errors='ignore') as f:
            head = f.read(4096)
        blob = head + '\n' + tail
        return _extract_weight_time_from_gcode_text(blob)
    except Exception as e:
        app_logger.info(f"[PreSlice] Erreur parsing gcode: {e}")
        return None

def parse_cura_gcode(gcode_path):
    if not os.path.exists(gcode_path):
        return None
    try:
        with open(gcode_path, 'r', encoding='utf-8', errors='ignore') as f:
            head = f.read(4096)
        return _extract_weight_time_from_gcode_text(head, is_cura=True)
    except Exception as e:
        app_logger.info(f"[PreSlice] Erreur parsing gcode Cura: {e}")
        return None

def parse_generic_output(output_path):
    if not os.path.exists(output_path):
        return None
    if output_path.lower().endswith('.3mf'):
        return parse_bambu_orca_gcode3mf(output_path)
    result = parse_cura_gcode(output_path)
    if result:
        return result
    return parse_slic3r_derived_gcode(output_path)

def run_silent_slice(stl_path, slicer, timeout=150):
    slug = hashlib.md5(f"{stl_path}|{time.time()}".encode()).hexdigest()[:12]
    out_dir = os.path.join(get_slice_temp_dir(), slug)
    os.makedirs(out_dir, exist_ok=True)

    try:
        settings = load_settings()
        if slicer['id'] in ('orcaslicer', 'bambustudio', 'elegooslicer', 'anycubicslicernext'):
            out_3mf = os.path.join(out_dir, 'preslice.gcode.3mf')
            cmd = [slicer['path'], '--slice', '1', '--allow-newer-file', '--mstpp', str(max(30, timeout - 20))]

            load_settings_str = (settings.get('slicer_profile_settings') or '').strip()
            load_filament_str = (settings.get('slicer_profile_filament') or '').strip()
            if load_settings_str:
                cmd += ['--load-settings', load_settings_str]
            if load_filament_str:
                cmd += ['--load-filaments', load_filament_str]

            cmd += ['--export-3mf', out_3mf, stl_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **_popen_kwargs_silent())
            if not os.path.exists(out_3mf):
                app_logger.info(f"[PreSlice] Pas de sortie générée par {slicer['name']} - stderr: {(result.stderr or '')[:300]}")
                parsed = None
            else:
                parsed = parse_bambu_orca_gcode3mf(out_3mf)
        elif slicer['id'] in ('prusaslicer', 'superslicer'):
            gcode_path = os.path.join(out_dir, 'preslice.gcode')
            cmd = [slicer['path'], '--export-gcode', '--output', gcode_path]

            profile_key = 'slicer_profile_prusa_ini' if slicer['id'] == 'prusaslicer' else 'slicer_profile_super_ini'
            ini_str = (settings.get(profile_key) or '').strip()
            if ini_str:
                for ini_path in ini_str.split(';'):
                    ini_path = ini_path.strip()
                    if ini_path:
                        cmd += ['--load', ini_path]

            cmd += [stl_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **_popen_kwargs_silent())
            if not os.path.exists(gcode_path):
                if not ini_str:
                    app_logger.info(f"[PreSlice] {slicer['name']} n'a rien généré (aucun profil .ini configuré) - "
                                     f"renseigne '{profile_key}' dans app_settings.json. stderr: {(result.stderr or '')[:300]}")
                else:
                    app_logger.info(f"[PreSlice] Pas de sortie générée par {slicer['name']} - stderr: {(result.stderr or '')[:300]}")
                parsed = None
            else:
                parsed = parse_slic3r_derived_gcode(gcode_path)

        elif slicer['id'] == 'cura':
            gcode_path = os.path.join(out_dir, 'preslice.gcode')
            definitions_dir = slicer.get('definitions_dir')
            definition_file = (settings.get('cura_definition_file') or 'fdmprinter.def.json').strip()
            cmd = [slicer['path'], 'slice']
            if definitions_dir:
                cmd += ['-j', os.path.join(definitions_dir, definition_file)]
            cmd += ['-l', stl_path, '-o', gcode_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **_popen_kwargs_silent())
            if not os.path.exists(gcode_path):
                app_logger.info(f"[PreSlice] Pas de sortie générée par CuraEngine - stderr: {(result.stderr or '')[:300]}")
                parsed = None
            else:
                parsed = parse_cura_gcode(gcode_path)

        elif slicer['id'] == 'custom':
            output_type = slicer.get('output_type', 'gcode')
            out_name = 'preslice.gcode.3mf' if output_type == 'gcode3mf' else 'preslice.gcode'
            out_path = os.path.join(out_dir, out_name)
            try:
                args_str = slicer['args_template'].replace('{input}', stl_path).replace('{output}', out_path)
                cmd = [slicer['path']] + shlex.split(args_str, posix=(sys.platform != 'win32'))
            except Exception as e:
                app_logger.warning(f"[PreSlice] Template de commande invalide pour le slicer personnalisé: {e}")
                parsed = None
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **_popen_kwargs_silent())
                if not os.path.exists(out_path):
                    app_logger.info(f"[PreSlice] Pas de sortie générée par {slicer['name']} - stderr: {(result.stderr or '')[:300]}")
                    parsed = None
                else:
                    parsed = parse_generic_output(out_path)
        else:
            parsed = None

        if parsed:
            parsed['slicer_name'] = slicer['name']
        return parsed
    except subprocess.TimeoutExpired:
        app_logger.warning(f"[PreSlice] Timeout ({timeout}s) pour {os.path.basename(stl_path)}")
        return None
    except Exception as e:
        app_logger.warning(f"[PreSlice] Erreur slicing silencieux {os.path.basename(stl_path)}: {e}")
        return None
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


slice_estimate_queue = queue.Queue()
slice_estimate_results = collections.OrderedDict()
slice_estimate_lock = threading.Lock()
NUM_SLICE_WORKERS = 1

SLICE_ESTIMATE_CACHE_MAX = 500

def _slice_cache_set(file_path, value):
    slice_estimate_results[file_path] = value
    slice_estimate_results.move_to_end(file_path)
    while len(slice_estimate_results) > SLICE_ESTIMATE_CACHE_MAX:
        slice_estimate_results.popitem(last=False)

def process_slice_estimate_queue():
    def slice_worker(worker_id):
        _lower_thread_priority()
        app_logger.info(f"[PreSlice] Worker #{worker_id} démarré")
        while True:
            try:
                task = slice_estimate_queue.get(timeout=1)
            except queue.Empty:
                time.sleep(0.5)
                continue
            file_path = task.get('path')
            tmp_stl = None
            try:
                if is_virtual_archive_path(file_path):
                    archive_path, internal_path = split_virtual_archive_path(file_path)
                    raw_bytes = read_archive_entry_bytes(archive_path, internal_path)
                    tmp_fd, tmp_stl = tempfile.mkstemp(suffix=os.path.splitext(internal_path)[1])
                    with os.fdopen(tmp_fd, 'wb') as f:
                        f.write(raw_bytes)
                    stl_for_slicer = tmp_stl
                else:
                    stl_for_slicer = file_path

                slicers = get_cached_installed_slicers()
                if not slicers or not any(s.get('preslice_supported', True) for s in slicers):
                    with slice_estimate_lock:
                        _slice_cache_set(file_path, {'status': 'unavailable', 'reason': 'no_slicer'})
                    continue

                slicer = next(s for s in slicers if s.get('preslice_supported', True))
                data = run_silent_slice(stl_for_slicer, slicer)

                with slice_estimate_lock:
                    if data:
                        _slice_cache_set(file_path, {'status': 'done', 'data': data})
                    else:
                        _slice_cache_set(file_path, {'status': 'error', 'reason': 'slice_failed'})
            except Exception as e:
                app_logger.warning(f"[PreSlice] Erreur worker: {e}")
                with slice_estimate_lock:
                    _slice_cache_set(file_path, {'status': 'error', 'reason': str(e)})
            finally:
                if tmp_stl and os.path.exists(tmp_stl):
                    try:
                        os.remove(tmp_stl)
                    except Exception:
                        pass
                slice_estimate_queue.task_done()

    for i in range(NUM_SLICE_WORKERS):
        threading.Thread(target=slice_worker, args=(i,), daemon=True).start()
    app_logger.info(f"[PreSlice] File d'attente de pre-slicing active ({NUM_SLICE_WORKERS} worker)")

def detect_platform_from_path(file_path):
    path_lower = (file_path or '').lower().replace('\\', '/')
    if 'thingiverse' in path_lower:
        return 'Thingiverse'
    if 'printables' in path_lower:
        return 'Printables'
    if 'makerworld' in path_lower:
        return 'MakerWorld'
    return ''

def find_slicer_by_name(slicer_name):
    if not slicer_name or slicer_name == 'system_default':
        return None

    known_slicers = {
        'orca-slicer.exe': (["OrcaSlicer/orca-slicer.exe", "OrcaSlicer*/orca-slicer.exe"], ['orca-slicer.exe', 'OrcaSlicer.exe']),
        'bambu-studio.exe': (["Bambu Studio/bambu-studio.exe", "Bambu Studio*/bambu-studio.exe"], ['bambu-studio.exe']),
        'prusa-slicer.exe': (["Prusa3D/PrusaSlicer/prusa-slicer.exe", "PrusaSlicer/prusa-slicer.exe"], ['prusa-slicer.exe', 'prusa-slicer-console.exe']),
        'superslicer.exe': (["SuperSlicer/superslicer.exe"], ['superslicer.exe', 'superslicer_console.exe']),
        'Creality Print.exe': (["Creality Print/*/Creality Print.exe", "Creality Print/Creality Print.exe", "CrealityPrint/*/CrealityPrint.exe"], ['Creality Print.exe', 'CrealityPrint.exe']),
        'Cura.exe': (["Ultimaker Cura*/Cura.exe", "UltiMaker Cura*/Cura.exe"], ['Cura.exe']),
        'ElegooSlicer.exe': (["ElegooSlicer/ElegooSlicer.exe", "ElegooSlicer*/ElegooSlicer.exe"], ['ElegooSlicer.exe']),
        'AnycubicSlicerNext.exe': (["Anycubic Slicer Next/AnycubicSlicerNext.exe", "Anycubic Slicer Next*/AnycubicSlicerNext.exe", "AnycubicSlicerNext/AnycubicSlicerNext.exe"], ['AnycubicSlicerNext.exe']),
        'Anycubic-Slicer.exe': (["AnycubicSlicer/Anycubic-Slicer.exe"], ['Anycubic-Slicer.exe']),
        'Simplify3D.exe': (["Simplify3D*/Simplify3D.exe"], ['Simplify3D.exe']),
        'ideaMaker.exe': (["Raise3D/ideaMaker/ideaMaker.exe", "ideaMaker/ideaMaker.exe", "ideaMaker*/ideaMaker.exe"], ['ideaMaker.exe']),
        'FlashPrint.exe': (["FlashPrint/FlashPrint.exe", "FlashPrint*/FlashPrint.exe"], ['FlashPrint.exe']),
        'LycheeSlicer.exe': (["LycheeSlicer/LycheeSlicer.exe", "LycheeSlicer*/LycheeSlicer.exe"], ['LycheeSlicer.exe']),
        'CraftWare.exe': (["CraftWare/CraftWare.exe", "CraftWare*/CraftWare.exe", "CraftWarePro/CraftWarePro.exe"], ['CraftWare.exe', 'CraftWarePro.exe']),
        'MatterControl.exe': (["MatterControl/MatterControl.exe", "MatterHackers/MatterControl/MatterControl.exe"], ['MatterControl.exe']),
        'MakerBotPrint.exe': (["MakerBot Print/MakerBotPrint.exe", "MakerBot Print*/MakerBotPrint.exe"], ['MakerBotPrint.exe']),
        'Voxelizer.exe': (["Voxelizer/Voxelizer.exe", "ZMorph*/Voxelizer.exe"], ['Voxelizer.exe']),
        'slic3r.exe': (["Slic3r/slic3r.exe"], ['slic3r.exe', 'slic3r-console.exe']),
        'KISSlicer.exe': (["KISSlicer*/KISSlicer.exe", "KISSlicer*/KISSlicer-x64.exe"], ['KISSlicer.exe', 'KISSlicer-x64.exe']),
    }

    entry = known_slicers.get(slicer_name)
    if not entry:
        return None
    patterns, registry_names = entry
    return _locate_slicer(patterns, registry_names)

@app.route('/api/slicer/pre-slice-estimate', methods=['POST'])
@login_required
def api_request_slice_estimate():
    data = request.json or {}
    file_path = (data.get('path') or '').strip()
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400

    with slice_estimate_lock:
        existing = slice_estimate_results.get(file_path)
    if existing and existing.get('status') in ('done', 'error', 'unavailable'):
        return jsonify(existing), 200

    if not is_virtual_archive_path(file_path) and not os.path.exists(file_path):
        return jsonify({"error": "Fichier non trouvé"}), 404
    if is_virtual_archive_path(file_path):
        archive_path, _ = split_virtual_archive_path(file_path)
        if not os.path.exists(archive_path):
            return jsonify({"error": "Archive non trouvée"}), 404

    with slice_estimate_lock:
        if file_path not in slice_estimate_results or slice_estimate_results[file_path].get('status') == 'error':
            _slice_cache_set(file_path, {'status': 'pending'})
            slice_estimate_queue.put({'path': file_path})
        result = slice_estimate_results[file_path]

    return jsonify(result), 202

def _get_cached_slice_estimate_seconds(file_path):
    with slice_estimate_lock:
        entry = slice_estimate_results.get(file_path)
    if entry and entry.get('status') == 'done':
        return entry.get('data', {}).get('time_seconds')
    return None

@app.route('/api/slicer/pre-slice-estimate', methods=['GET'])
@login_required
def api_get_slice_estimate():
    file_path = (request.args.get('path') or '').strip()
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400
    with slice_estimate_lock:
        result = slice_estimate_results.get(file_path, {'status': 'unknown'})
    return jsonify(result), 200

_SLICER_FAMILY_BY_FILENAME = {
    'orca-slicer.exe': 'orcaslicer',
    'orcaslicer.exe': 'orcaslicer',
    'bambu-studio.exe': 'bambustudio',
    'bambustudio.exe': 'bambustudio',
    'prusa-slicer.exe': 'prusaslicer',
    'prusa-slicer-console.exe': 'prusaslicer',
    'superslicer.exe': 'superslicer',
    'superslicer_console.exe': 'superslicer',
    'elegooslicer.exe': 'elegooslicer',
    'anycubicslicernext.exe': 'anycubicslicernext',


    'creality print.exe': 'creality_print',
    'crealityprint.exe': 'creality_print',
}


def _resolve_slicer_family(slicer_path, slicer_name):
    basename = os.path.basename(slicer_path).lower() if slicer_path else ''
    return (_SLICER_FAMILY_BY_FILENAME.get(basename)
            or _SLICER_FAMILY_BY_FILENAME.get((slicer_name or '').lower()))


_SLICER_LOAD_SETTINGS_FAMILIES = ('orcaslicer', 'bambustudio', 'elegooslicer', 'anycubicslicernext', 'creality_print')
_SLICER_LOAD_INI_FAMILIES = ('prusaslicer', 'superslicer')


def _resolve_slicer_profile_paths(slicer_family, printer_id, material_type=None):
    if not printer_id or not slicer_family:
        return [], [], []

    try:
        printer_id_int = int(printer_id)
    except (TypeError, ValueError):
        return [], [], []

    profiles = load_slicer_profiles()
    settings_paths, filament_paths, matched_ids = [], [], []

    for p in profiles:
        if p.get('printer_id') != printer_id_int:
            continue
        if not p.get('source_path') or not os.path.exists(p['source_path']):
            continue
        p_slicer = (p.get('slicer') or '').strip().lower()
        if p_slicer and p_slicer != slicer_family:
            continue

        ptype = p.get('profile_type')
        if ptype == 'filament':
            if material_type and (p.get('material_type') or '').strip().lower() != material_type.strip().lower():
                continue
            filament_paths.append(p['source_path'])
            matched_ids.append(p['id'])
        elif ptype in ('process', 'printer'):
            settings_paths.append(p['source_path'])
            matched_ids.append(p['id'])


    confirmed_settings = [p['source_path'] for p in profiles
                           if p.get('printer_id') == printer_id_int and p.get('printer_match_confirmed')
                           and p.get('profile_type') in ('process', 'printer')
                           and p.get('source_path') and os.path.exists(p['source_path'])
                           and (not (p.get('slicer') or '').strip() or (p.get('slicer') or '').strip().lower() == slicer_family)]
    if confirmed_settings:
        settings_paths = confirmed_settings

    return settings_paths, filament_paths, matched_ids


@app.route('/api/slicer/send', methods=['POST'])
@login_required
def api_send_to_slicer():
    data = request.json
    file_path = data.get('file_path', '')
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Fichier non trouvé"}), 404
    if not _is_path_within_sources(file_path, session['user_id']):
        app_logger.warning(f"[SECURITY] Tentative d'ouverture slicer hors sources: {file_path}")
        return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

    try:
        settings = load_settings()
        slicer_name = settings.get('default_slicer', 'system_default')
        slicer_path = find_slicer_by_name(slicer_name)
        detected_slicer = os.path.basename(slicer_path).replace('.exe','') if slicer_path else 'Défaut système'

        orientation_key = data.get('orientation') or 'default'
        reoriented_path = _export_reoriented_mesh(file_path, orientation_key)
        path_to_open = reoriented_path or file_path


        applied_profile_ids = []
        if slicer_path:
            slicer_family = _resolve_slicer_family(slicer_path, slicer_name)
            printer_id = data.get('printer_id')
            material_type = data.get('material_type')
            cmd = [slicer_path]

            if slicer_family and printer_id:
                settings_paths, filament_paths, matched_ids = _resolve_slicer_profile_paths(
                    slicer_family, printer_id, material_type
                )
                applied_profile_ids = matched_ids
                if slicer_family in _SLICER_LOAD_SETTINGS_FAMILIES:
                    if settings_paths:
                        cmd += ['--load-settings', ';'.join(settings_paths)]
                    if filament_paths:
                        cmd += ['--load-filaments', ';'.join(filament_paths)]
                elif slicer_family in _SLICER_LOAD_INI_FAMILIES:
                    for ini_path in (settings_paths + filament_paths):
                        cmd += ['--load', ini_path]
                if not settings_paths and not filament_paths:
                    app_logger.info(f"[Slicer] Aucun profil importé rattaché à l'imprimante {printer_id} pour {slicer_family}, ouverture sans --load-settings")

            cmd.append(path_to_open)
            subprocess.Popen(cmd)
        else:
            if sys.platform == 'win32':
                os.startfile(path_to_open)
            else:
                subprocess.run(['xdg-open', path_to_open], check=False)

        try:
            conn = get_db()
            norm = file_path.replace('\\', '/')

            assignment_row = conn.execute(
                "SELECT source_type, source_id FROM filament_assignments WHERE file_path=? AND user_id=?",
                (norm, session['user_id'])
            ).fetchone()

            spool_id_logged, weight_used_logged = None, None
            if assignment_row and data.get('consume_spool'):
                source_type, source_id = assignment_row
                required_g, _ = _get_required_weight_for_file(norm)
                if required_g:
                    if _consume_filament_slot(source_type, source_id, required_g, session['user_id']):
                        weight_used_logged = required_g
                        if source_type == 'spoolman':
                            try:
                                spool_id_logged = int(source_id)
                            except (TypeError, ValueError):
                                spool_id_logged = None

            material_cost, elec_cost, total_cost, _weight_for_cost = _compute_estimated_cost(norm, weight_g_hint=weight_used_logged)
            estimated_seconds_logged = _get_cached_slice_estimate_seconds(norm)

            cur = conn.execute(
                "INSERT INTO print_history (user_id, file_path, file_name, file_size, file_ext, slicer, source_platform, spool_id, spool_weight_used_g, slicer_profile_id, slicer_profile_name, material_cost, elec_cost, total_cost, printer_id, estimated_seconds) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (session['user_id'], norm, os.path.basename(file_path),
                 os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                 os.path.splitext(file_path)[1].lower(), detected_slicer,
                 detect_platform_from_path(norm), spool_id_logged, weight_used_logged,
                 data.get('slicer_profile_id') or (applied_profile_ids[0] if applied_profile_ids else ''), data.get('slicer_profile_name') or '',
                 material_cost, elec_cost, total_cost, printer_id, estimated_seconds_logged)
            )
            history_id = cur.lastrowid
            conn.commit()
            conn.close()
        except Exception as log_err:
            app_logger.warning(f"[PrintHistory] Log échoué: {log_err}")
            history_id = None

        return jsonify({"message": f"Envoyé via {detected_slicer}", "history_id": history_id,
                         "stock_warning": (_check_restock_for_files([file_path], session['user_id']) or [None])[0]}), 200

    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/slicer/send-batch', methods=['POST'])
@login_required
def api_slicer_send_batch():
    try:
        data = request.json
        file_paths = data.get('files', [])
        if not file_paths:
            return jsonify({"error": "Aucun fichier sélectionné"}), 400
        for fp in file_paths:
            if not _is_path_within_sources(fp, session['user_id']):
                app_logger.warning(f"[SECURITY] Tentative d'ouverture slicer (batch) hors sources: {fp}")
                return jsonify({"error": "Un ou plusieurs fichiers n'appartiennent à aucune source configurée"}), 403

        if sys.platform == 'win32':
            file_paths = [p.replace('/', '\\') for p in file_paths]


        settings = load_settings()
        slicer_name = settings.get('default_slicer', 'system_default')
        slicer_path = find_slicer_by_name(slicer_name)

        if not slicer_path:
            installed = get_cached_installed_slicers()
            if installed:
                slicer_path = installed[0]['path']

        if not slicer_path:
            return jsonify({
                "error": "Aucun slicer trouvé. Installez OrcaSlicer, BambuStudio, PrusaSlicer ou Cura."
            }), 404


        applied_profile_ids = []
        cmd = [slicer_path]
        slicer_family = _resolve_slicer_family(slicer_path, slicer_name)
        printer_id = data.get('printer_id')
        material_type = data.get('material_type')
        if slicer_family and printer_id:
            settings_paths, filament_paths, matched_ids = _resolve_slicer_profile_paths(
                slicer_family, printer_id, material_type
            )
            applied_profile_ids = matched_ids
            if slicer_family in _SLICER_LOAD_SETTINGS_FAMILIES:
                if settings_paths:
                    cmd += ['--load-settings', ';'.join(settings_paths)]
                if filament_paths:
                    cmd += ['--load-filaments', ';'.join(filament_paths)]
            elif slicer_family in _SLICER_LOAD_INI_FAMILIES:
                for ini_path in (settings_paths + filament_paths):
                    cmd += ['--load', ini_path]

        app_logger.info(f"[Slicer] Lancement avec {len(file_paths)} fichiers...")
        try:
            subprocess.Popen(cmd + file_paths)
        except Exception as e:
            app_logger.info(f"[Slicer] Erreur ouverture multiple: {e}")
            subprocess.Popen(cmd + [file_paths[0]])

        try:
            conn = get_db()
            try:
                slicer_label = os.path.basename(slicer_path).replace('.exe', '')
                profile_id_to_log = applied_profile_ids[0] if applied_profile_ids else ''
                for fp in file_paths:
                    norm = fp.replace('\\', '/')
                    material_cost, elec_cost, total_cost, _w = _compute_estimated_cost(norm)
                    estimated_seconds_logged = _get_cached_slice_estimate_seconds(norm)
                    conn.execute(
                        "INSERT INTO print_history (user_id, file_path, file_name, file_size, file_ext, slicer, source_platform, slicer_profile_id, material_cost, elec_cost, total_cost, printer_id, estimated_seconds) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (session['user_id'], norm, os.path.basename(fp),
                         os.path.getsize(fp) if os.path.exists(fp) else 0,
                         os.path.splitext(fp)[1].lower(), slicer_label,
                         detect_platform_from_path(norm), profile_id_to_log, material_cost, elec_cost, total_cost,
                         printer_id, estimated_seconds_logged)
                    )
                conn.commit()
            finally:
                conn.close()
        except Exception as log_err:
            app_logger.warning(f"[PrintHistory] Log batch échoué: {log_err}")

        return jsonify({
            "message": f"{len(file_paths)} fichiers ouverts dans le slicer",
            "count": len(file_paths),
            "stock_warnings": _check_restock_for_files(file_paths, session['user_id'])
        }), 200

    except Exception as e:
        app_logger.info(f"[ERROR] api_slicer_send_batch: {e}")
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/picker/folder', methods=['POST'])
@login_required
def api_pick_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.update()
        folder = filedialog.askdirectory(title="Sélectionner un dossier", initialdir=os.path.expanduser("~"))
        root.destroy()

        if folder:
            return jsonify({"path": folder.replace("\\", "/")})
        else:
            return jsonify({"error": "Annulé"}), 400

    except ImportError as e:
        return jsonify({"error": "tkinter manquant"}), 500
    except Exception as e:
        return jsonify({"error": f"Erreur: {str(e)}"}), 500

@app.route('/api/picker/file', methods=['POST'])
@login_required
def api_pick_file():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.update()
        files = filedialog.askopenfilenames(
            title="Sélectionner des fichiers 3D",
            initialdir=os.path.expanduser("~"),
            filetypes=[("Fichiers 3D", "*.stl *.3mf *.obj"), ("STL", "*.stl"), ("3MF", "*.3mf"), ("OBJ", "*.obj"), ("Tous", "*.*")]
        )
        root.destroy()

        if files:
            return jsonify({"paths": [f.replace("\\", "/") for f in files]})
        else:
            return jsonify({"error": "Annulé"}), 400

    except ImportError as e:
        return jsonify({"error": "tkinter manquant"}), 500
    except Exception as e:
        return jsonify({"error": f"Erreur: {str(e)}"}), 500


@app.route('/api/test-connection', methods=['POST'])
@login_required
def api_test_connection():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalide"}), 400

        conn_type = data.get('type', '')
        host = data.get('host', '').strip()

        if not host:
            return jsonify({"error": "Hôte requis"}), 400

        if conn_type == 'smb':
            share    = data.get('share', '').strip()
            username = data.get('username', '').strip()
            password = data.get('password', '')
            path     = data.get('path', '').strip()

            if not share:
                return jsonify({"error": "Nom du partage requis"}), 400

            unc = f"//{host}/{share}"
            if path:
                unc = f"{unc}/{path.lstrip('/')}"

            try:
                smbclient.reset_connection_cache()
            except Exception:
                pass

            kwargs = {'connection_timeout': 8}
            if username:
                kwargs['username'] = username
            if password:
                kwargs['password'] = password

            try:
                smbclient.listdir(unc, **kwargs)
                app_logger.info(f"[TestConn] ✅ SMB OK: {unc}")
                return jsonify({"success": True, "message": "Connexion réussie"}), 200
            except Exception as e:
                err = str(e)
                app_logger.warning(f"[TestConn] ❌ SMB échec ({unc}): {err}")
                if 'STATUS_LOGON_FAILURE' in err or '0xc000006d' in err:
                    return jsonify({"error": "Identifiants incorrects (STATUS_LOGON_FAILURE)"}), 401
                elif 'STATUS_ACCESS_DENIED' in err or '0xc0000022' in err:
                    return jsonify({"error": "Accès refusé (STATUS_ACCESS_DENIED)"}), 403
                elif 'STATUS_BAD_NETWORK_NAME' in err or '0xc00000cc' in err:
                    return jsonify({"error": "Partage introuvable (STATUS_BAD_NETWORK_NAME)"}), 404
                elif 'STATUS_OBJECT_PATH_NOT_FOUND' in err or '0xc000003a' in err:
                    return jsonify({"error": "Chemin introuvable dans le partage"}), 404
                elif 'timed out' in err.lower() or 'unreachable' in err.lower() or 'refused' in err.lower():
                    return jsonify({"error": f"Hôte inaccessible : {host}"}), 503
                else:
                    return jsonify({"error": f"Erreur SMB : {err}"}), 500

        elif conn_type == 'nfs':
            return jsonify({"success": True, "message": "NFS non testé activement"}), 200

        return jsonify({"error": "Type non supporté"}), 400

    except Exception as e:
        app_logger.error(f"[TestConn] Erreur générale: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/download/create-folder', methods=['POST'])
@login_required
def api_create_download_folder():
    try:
        data = request.json
        folder_path = data.get('folder_path')
        folder_name = data.get('folder_name', '').strip()
        add_as_source = data.get('add_as_source', False)

        if not folder_path or not folder_name:
            return jsonify({"error": "Chemin et nom requis"}), 400

        folder_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)
        if not folder_name:
            return jsonify({"error": "Nom de dossier invalide"}), 400

        is_smb = folder_path.startswith('//') or folder_path.startswith('\\\\')
        is_local = not is_smb

        if is_smb:
            import smbclient
            base_path = folder_path.replace('\\\\', '//').replace('\\', '/')
            config = json.loads(data.get('config', '{}') if isinstance(data.get('config'), str) else '{}')
            parent_config = dict(config)
            kwargs = {'connection_timeout': 8}
            if config.get('username'):
                kwargs['username'] = config.get('username')
            if config.get('password'):
                kwargs['password'] = config.get('password')

            if not kwargs.get('username'):
                try:
                    conn = get_db()
                    try:
                        rows = conn.execute(
                            "SELECT path, config FROM sources WHERE user_id = ? AND type = 'smb'",
                            (session['user_id'],)
                        ).fetchall()
                    finally:
                        conn.close()
                    norm_target = base_path.rstrip('/').lower()
                    best_cfg, best_len = None, -1
                    for row in rows:
                        src_norm = (row['path'] or '').replace('\\\\', '//').replace('\\', '/').rstrip('/').lower()
                        if src_norm and (norm_target == src_norm or norm_target.startswith(src_norm + '/')):
                            if len(src_norm) > best_len:
                                best_cfg, best_len = row['config'], len(src_norm)
                    if best_cfg:
                        parent_config.update(json.loads(best_cfg or '{}'))
                        if parent_config.get('username'):
                            kwargs['username'] = parent_config['username']
                        if parent_config.get('password'):
                            kwargs['password'] = parent_config['password']
                except Exception as e:
                    app_logger.warning(f"[create-folder] Identifiants SMB de la source ignorés: {e}")

            try:
                if not smbclient.path.exists(base_path, **kwargs):
                    smbclient.makedirs(base_path, exist_ok=True, **kwargs)

                added_as_source = False
                if add_as_source:
                    try:
                        unc_path = base_path.replace('/', '\\')
                        conn = get_db()
                        try:
                            if not conn.execute("SELECT id FROM sources WHERE user_id = ? AND path = ?",
                                                (session['user_id'], unc_path)).fetchone():
                                source_name = folder_name
                                counter = 1
                                while conn.execute("SELECT id FROM sources WHERE user_id = ? AND name = ?",
                                                   (session['user_id'], source_name)).fetchone():
                                    source_name = f"{folder_name} ({counter})"
                                    counter += 1
                                smb_cfg = {'type': 'smb'}
                                if parent_config.get('username'):
                                    smb_cfg['username'] = parent_config['username']
                                if parent_config.get('password'):
                                    smb_cfg['password'] = parent_config['password']
                                conn.execute(
                                    "INSERT INTO sources (user_id, name, type, path, config) VALUES (?, ?, 'smb', ?, ?)",
                                    (session['user_id'], source_name, unc_path, json.dumps(smb_cfg))
                                )
                                conn.commit()
                                added_as_source = True
                                invalidate_cache()
                        finally:
                            conn.close()
                    except Exception as db_err:
                        app_logger.error(f"[create-folder] Erreur ajout source SMB: {db_err}")

                return jsonify({
                    "success": True,
                    "message": "Dossier SMB créé",
                    "path": base_path,
                    "is_local": False,
                    "added_as_source": added_as_source
                }), 200
            except Exception as smb_err:
                err_msg = str(smb_err)
                if 'ACCESS_DENIED' in err_msg or '0xc0000022' in err_msg:
                    err_msg += (" — le compte SMB utilisé n'a pas les droits en écriture sur ce partage "
                                "(vérifie les permissions du dossier partagé côté OMV).")
                return jsonify({"error": f"Erreur SMB: {err_msg}"}), 500

        else:
            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)

            added_as_source = False
            if add_as_source and is_local:
                try:
                    conn = get_db()
                    try:
                        existing = conn.execute(
                            "SELECT id FROM sources WHERE user_id = ? AND path = ?",
                            (session['user_id'], folder_path)
                        ).fetchone()

                        if not existing:
                            source_name = folder_name
                            counter = 1
                            while conn.execute(
                                "SELECT id FROM sources WHERE user_id = ? AND name = ?",
                                (session['user_id'], source_name)
                            ).fetchone():
                                source_name = f"{folder_name} ({counter})"
                                counter += 1

                            conn.execute(
                                "INSERT INTO sources (user_id, name, type, path, config) VALUES (?, ?, ?, ?, ?)",
                                (session['user_id'], source_name, 'folder', folder_path, '{}')
                            )
                            conn.commit()
                            added_as_source = True
                            invalidate_cache()
                    finally:
                        conn.close()
                except Exception as db_err:
                    app_logger.error(f"Erreur ajout source: {db_err}")

            return jsonify({
                "success": True,
                "message": "Dossier créé",
                "path": folder_path.replace('\\', '/'),
                "is_local": True,
                "added_as_source": added_as_source
            }), 200

    except Exception as e:
        app_logger.error(f"[create-folder] Erreur: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/download/progress/<int:download_id>', methods=['GET'])
@login_required
def api_download_progress(download_id):
    info = active_downloads.get(download_id)
    if info:
        return jsonify({
            "active": True,
            "download_id": download_id,
            "filename": info.get("filename", ""),
            "percentage": info.get("percentage", 0),
            "current": info.get("current", 0),
            "total": info.get("total", 0),
        })
    return jsonify({"active": False, "download_id": download_id})

@app.route('/api/download/cancel/<int:download_id>', methods=['POST'])
@login_required
def api_download_cancel(download_id):
    was_active = download_id in active_downloads
    cancelled_downloads.add(download_id)
    active_downloads.pop(download_id, None)
    app_logger.info(f"[Download] Annulation demandée pour download_id={download_id} (actif={was_active})")
    return jsonify({"success": True, "download_id": download_id, "was_active": was_active})


PRINTABLES_API_URL = "https://api.printables.com/graphql/"
PRINTABLES_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def printables_get_model_files(model_id):
    query = """
    query ModelFiles($id: ID!) {
        model: print(id: $id) {
            id
            stls { id name fileSize __typename }
            otherFiles { id name fileSize __typename }
            __typename
        }
    }
    """
    payload = {"operationName": "ModelFiles", "query": query, "variables": {"id": str(model_id)}}

    try:
        res = requests.post(PRINTABLES_API_URL, headers=PRINTABLES_HEADERS, json=payload, timeout=15)
        res.raise_for_status()
        data = res.json()
        model = (data.get('data') or {}).get('model')
        if not model:
            return []

        files = []
        for f in (model.get('stls') or []):
            if f.get('id') and f.get('name'):
                files.append({"id": f['id'], "name": f['name'], "file_type": "stl"})

        valid_other_ext = ('.3mf', '.step', '.stp', '.obj', '.amf', '.ply', '.zip')
        for f in (model.get('otherFiles') or []):
            name = f.get('name') or ''
            if f.get('id') and name.lower().endswith(valid_other_ext):
                files.append({"id": f['id'], "name": name, "file_type": "other"})

        return files

    except Exception as e:
        app_logger.warning(f"[Printables] Erreur récupération liste de fichiers (model {model_id}): {e}")
        return []

def printables_get_download_link(file_id, model_id, file_type):
    query = """
    mutation GetDownloadLink($id: ID!, $modelId: ID!, $fileType: DownloadFileTypeEnum!, $source: DownloadSourceEnum!) {
        getDownloadLink(id: $id, printId: $modelId, fileType: $fileType, source: $source) {
            ok
            errors { field messages __typename }
            output { link count ttl __typename }
            __typename
        }
    }
    """
    variables = {"id": str(file_id), "modelId": str(model_id), "fileType": file_type, "source": "model_detail"}
    payload = {"operationName": "GetDownloadLink", "query": query, "variables": variables}

    try:
        res = requests.post(PRINTABLES_API_URL, headers=PRINTABLES_HEADERS, json=payload, timeout=15)
        res.raise_for_status()
        data = res.json()
        result = (data.get('data') or {}).get('getDownloadLink')

        if result and result.get('ok') and result.get('output', {}).get('link'):
            return result['output']['link']

        if result and result.get('errors'):
            app_logger.warning(f"[Printables] GetDownloadLink erreur (file {file_id}): {result['errors']}")

    except Exception as e:
        app_logger.warning(f"[Printables] Erreur récupération lien (file {file_id}): {e}")

    return None


MAKERWORLD_API = "https://api.bambulab.com"
MAKERWORLD_DL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

def makerworld_get_model_files(model_id, bearer_token=None, profile_id=None, preferred_format=None):
    headers = {
        "User-Agent": "BambuStudio/01.09.00.00",
        "Accept": "application/json",
        "Referer": f"https://makerworld.com/en/models/{model_id}",
    }
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    files = []
    try:
        r = requests.get(
            f"{MAKERWORLD_API}/v1/design-service/design/{model_id}",
            headers=headers,
            timeout=20
        )
        app_logger.info(f"[MakerWorld] design/{model_id} status={r.status_code}")
        if not r.ok:
            app_logger.warning(f"[MakerWorld] design/{model_id} non-OK: {r.status_code} {r.text[:200]}")
            return files

        data = r.json()
        alpha_model_id = data.get("modelId") or data.get("model_id") or ""
        app_logger.info(f"[MakerWorld] alphaModelId={alpha_model_id}")

        design_title = (
            data.get("title") or
            data.get("titleTranslated") or
            data.get("slug") or
            f"makerworld_{model_id}"
        ).strip()
        design_title = re.sub(r'[<>:"/\\|?*]', '_', design_title)
        app_logger.info(f"[MakerWorld] Titre du design: '{design_title}'")

        instances = (
            data.get("instances") or
            data.get("designProfileList") or
            data.get("profileList") or
            data.get("profiles") or
            []
        )
        app_logger.info(f"[MakerWorld] {len(instances)} instance(s) disponible(s)")
        if instances:
            app_logger.info(f"[MakerWorld] instance[0] keys: {list(instances[0].keys())}")
            app_logger.info(f"[MakerWorld] instance[0] sample: { {k: instances[0][k] for k in list(instances[0].keys())[:8]} }")

        target_instances = instances
        if profile_id and instances:
            matched = [inst for inst in instances if str(inst.get('id', '')) == str(profile_id)]
            if matched:
                target_instances = matched
                app_logger.info(f"[MakerWorld] Instance ciblée: id={profile_id} → profileId={matched[0].get('profileId')}")
            else:
                app_logger.warning(f"[MakerWorld] id={profile_id} non trouvé dans les instances, téléchargement de toutes les instances")

        for inst in target_instances:
            pid_primary = inst.get("profileId")
            pid_fallback = inst.get("id")
            if not pid_primary and not pid_fallback:
                continue

            pname = design_title
            if len(target_instances) > 1:
                inst_idx = target_instances.index(inst) + 1
                pname = f"{design_title}_{inst_idx}"

            app_logger.info(f"[MakerWorld] Instance id={pid_fallback} profileId={pid_primary} → '{pname}'")

            try:
                params = {}
                if alpha_model_id:
                    params["model_id"] = alpha_model_id

                r_dl = requests.get(
                    f"{MAKERWORLD_API}/v1/iot-service/api/user/profile/{pid_primary}",
                    params=params,
                    headers=headers,
                    timeout=15
                )
                app_logger.info(f"[MakerWorld] iot-service/profile/{pid_primary} status={r_dl.status_code}")

                if not r_dl.ok and pid_fallback and pid_fallback != pid_primary:
                    app_logger.info(f"[MakerWorld] Retry avec id={pid_fallback}")
                    r_dl = requests.get(
                        f"{MAKERWORLD_API}/v1/iot-service/api/user/profile/{pid_fallback}",
                        params=params,
                        headers=headers,
                        timeout=15
                    )
                    app_logger.info(f"[MakerWorld] iot-service/profile/{pid_fallback} status={r_dl.status_code}")

                if r_dl.ok:
                    dl_data = r_dl.json()
                    app_logger.info(f"[MakerWorld] profile keys={list(dl_data.keys())}")

                    dl_url = (
                        dl_data.get("url") or
                        dl_data.get("downloadUrl") or
                        dl_data.get("download_url") or
                        dl_data.get("fileUrl")
                    )
                    if dl_url:
                        ext = os.path.splitext(dl_url.split("?")[0])[1].lower()
                        if not ext:
                            ext = ".3mf"
                        safe_name = re.sub(r'[<>:"/\\|?*]', '_', pname) + ext
                        files.append({"name": safe_name, "url": dl_url, "format": ext.lstrip('.')})
                        app_logger.info(f"[MakerWorld] ✅ {safe_name}")

                        if profile_id and target_instances != instances:
                            break
                else:
                    app_logger.warning(f"[MakerWorld] Deux essais échoués pour instance id={pid_fallback} profileId={pid_primary}: {r_dl.status_code} {r_dl.text[:200]}")

            except Exception as ep:
                app_logger.warning(f"[MakerWorld] Erreur iot-service/profile/{pid}: {ep}")

        if not files or (preferred_format == 'stl' and not any(f['format'] == 'stl' for f in files)):
            app_logger.info(f"[MakerWorld] Tentative endpoint STL direct...")
            try:
                r_stl = requests.get(
                    f"{MAKERWORLD_API}/v1/design-service/design/{model_id}/stl",
                    params={"profile_id": profile_id} if profile_id else {},
                    headers=headers,
                    timeout=20
                )
                app_logger.info(f"[MakerWorld] design/{model_id}/stl status={r_stl.status_code}")

                if r_stl.ok:
                    stl_data = r_stl.json()
                    app_logger.info(f"[MakerWorld] /stl keys={list(stl_data.keys())}")

                    stl_url = stl_data.get("url") or stl_data.get("downloadUrl") or stl_data.get("download_url")
                    if stl_url:
                        files.append({"name": f"makerworld_{model_id}.zip", "url": stl_url, "format": "zip"})
                        app_logger.info(f"[MakerWorld] ✅ STL ZIP via design/{model_id}/stl")

            except Exception as e_stl:
                app_logger.warning(f"[MakerWorld] Endpoint STL échoué: {e_stl}")

    except Exception as e:
        app_logger.warning(f"[MakerWorld] Erreur design/{model_id}: {e}")

    app_logger.info(f"[MakerWorld] Modèle {model_id}: {len(files)} fichier(s) trouvé(s)")

    if preferred_format and files:
        target_ext = preferred_format
        filtered = [f for f in files if f.get('format', '') == target_ext]
        if filtered:
            app_logger.info(f"[MakerWorld] Filtre format '{preferred_format}': {len(filtered)} fichier(s) gardé(s)")
            files = filtered
        else:
            app_logger.warning(f"[MakerWorld] Format '{preferred_format}' non disponible, retour de tous les fichiers ({len(files)})")

    return files

def _makerworld_save_token(user_id, email, token):
    conn = get_db()
    try:
        token_enc = encrypt_password(token) if token else None
        conn.execute("""
            INSERT INTO account_credentials (user_id, platform, email, api_key, last_login)
            VALUES (?, 'makerworld', ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, platform) DO UPDATE SET
                email = excluded.email,
                api_key = excluded.api_key,
                last_login = CURRENT_TIMESTAMP
        """, (user_id, email, token_enc))
        conn.commit()
    finally:
        conn.close()
    app_logger.info(f"[MakerWorld] Token sauvegardé pour user {user_id} ({email})")

@app.route('/api/accounts/makerworld/login', methods=['POST'])
@login_required
def makerworld_login_step1():
    data = request.json or {}
    email    = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    try:
        r = requests.post(
            f"{MAKERWORLD_API}/v1/user-service/user/login",
            json={"account": email, "password": password},
            headers={"Content-Type": "application/json", "User-Agent": "BambuStudio/01.09.00.00"},
            timeout=15
        )
        body = r.json()
    except Exception as e:
        return jsonify({"error": f"Erreur réseau : {e}"}), 502

    login_type = body.get("loginType", "")
    if login_type == "verifyCode":
        return jsonify({"needCode": True}), 200

    access_token = body.get("accessToken") or body.get("token")
    if access_token:
        _makerworld_save_token(session['user_id'], email, access_token)
        return jsonify({"success": True}), 200

    msg = body.get("message") or body.get("error") or "Identifiants incorrects"
    return jsonify({"error": msg}), 401

@app.route('/api/accounts/makerworld/verify', methods=['POST'])
@login_required
def makerworld_login_step2():
    data = request.json or {}
    email = (data.get('email') or '').strip()
    code  = (data.get('code') or '').strip()

    if not email or not code:
        return jsonify({"error": "Email et code requis"}), 400

    try:
        r = requests.post(
            f"{MAKERWORLD_API}/v1/user-service/user/login",
            json={"account": email, "code": code},
            headers={"Content-Type": "application/json", "User-Agent": "BambuStudio/01.09.00.00"},
            timeout=15
        )
        body = r.json()
    except Exception as e:
        return jsonify({"error": f"Erreur réseau : {e}"}), 502

    access_token = body.get("accessToken") or body.get("token")
    if access_token:
        _makerworld_save_token(session['user_id'], email, access_token)
        return jsonify({"success": True}), 200

    msg = body.get("message") or body.get("error") or "Code invalide ou expiré"
    return jsonify({"error": msg}), 401

@app.route('/api/accounts/makerworld/disconnect', methods=['DELETE'])
@login_required
def makerworld_disconnect():
    conn = get_db()
    try:
        conn.execute("DELETE FROM account_credentials WHERE user_id = ? AND platform = 'makerworld'",
                     (session['user_id'],))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"message": "Compte MakerWorld supprimé"}), 200

@app.route('/api/download', methods=['POST'])
@login_required
def api_download_file():
    import threading

    data = request.json or {}
    url = (data.get('url') or '').strip()
    target_source_id = data.get('target_source_id')
    try:
        download_id = int(data.get('download_id', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "download_id invalide"}), 400
    preferred_format = (data.get('preferred_format') or '').lower().strip('.')

    if not url:
        return jsonify({"error": "URL requise"}), 400

    save_dir = None
    if target_source_id:
        try:
            conn = get_db()
            src = conn.execute(
                "SELECT path FROM sources WHERE id = ? AND user_id = ?",
                (target_source_id, session['user_id'])
            ).fetchone()
            conn.close()
            if src:
                save_dir = src['path']
        except Exception:
            pass

    if not save_dir:
        save_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'Stellio')
        os.makedirs(save_dir, exist_ok=True)
        _ensure_download_folder_registered(save_dir, session['user_id'])

    active_downloads[download_id] = {
        "filename": "",
        "percentage": 0,
        "current": 0,
        "total": 0,
    }

    try:
        BROWSER_HEADERS = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        }
        DL_HEADERS = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
        }

        resolved_url = url
        parsed = urlparse(url)

        if 'thingiverse.com' in parsed.netloc:
            m = re.search(r'thing:(\d+)', url)
            if not m:
                active_downloads.pop(download_id, None)
                return jsonify({"error": "URL Thingiverse invalide. Format attendu : https://www.thingiverse.com/thing:XXXXXX"}), 400

            thing_id = m.group(1)

            api_token = None
            try:
                conn = get_db()
                acc_row = conn.execute(
                    "SELECT api_key FROM account_credentials WHERE user_id = ? AND platform = 'thingiverse'",
                    (session['user_id'],)
                ).fetchone()
                conn.close()
                if acc_row and acc_row['api_key']:
                    api_token = decrypt_account_secret(acc_row['api_key'])
            except Exception:
                pass

            download_files_list = []
            if api_token:
                try:
                    api_headers = dict(DL_HEADERS)
                    api_headers['Authorization'] = f"Bearer {api_token}"
                    r_api = requests.get(
                        f"https://api.thingiverse.com/things/{thing_id}/files",
                        headers=api_headers, timeout=15
                    )
                    if r_api.ok:
                        files_data = r_api.json()
                        if isinstance(files_data, list) and files_data:
                            for f_item in files_data:
                                dl_url = f_item.get('download_url') or f_item.get('public_url')
                                fname_item = f_item.get('name', '')
                                if dl_url and any(fname_item.lower().endswith(e) for e in ['.stl','.3mf','.obj','.step','.stp','.amf']):
                                    download_files_list.append((fname_item, dl_url))
                except Exception as api_err:
                    app_logger.warning(f"[Download] Thingiverse API error: {api_err}")

            if download_files_list:
                total_files = len(download_files_list)
                results = []
                for idx, (fname_item, dl_url) in enumerate(download_files_list):
                    fname_item = re.sub(r'[<>:"/\\|?*]', '_', fname_item)
                    dest_path = os.path.join(save_dir, fname_item)
                    active_downloads[download_id]['filename'] = fname_item
                    currently_downloading_paths.add(dest_path.replace('\\', '/'))
                    file_ok = False
                    try:
                        with requests.get(dl_url, headers=dict(DL_HEADERS, Authorization=f"Bearer {api_token}"),
                                          stream=True, timeout=60) as r_dl:
                            r_dl.raise_for_status()
                            total_bytes = int(r_dl.headers.get('Content-Length', 0))
                            downloaded_bytes = 0
                            with open(dest_path, 'wb') as f_out:
                                for chunk in r_dl.iter_content(chunk_size=65536):
                                    if download_id in cancelled_downloads:
                                        break
                                    if chunk:
                                        f_out.write(chunk)
                                        downloaded_bytes += len(chunk)
                                        base_pct = int(idx * 100 / total_files)
                                        file_pct = int(downloaded_bytes * 100 / total_bytes / total_files) if total_bytes else 0
                                        active_downloads[download_id]['percentage'] = base_pct + file_pct
                        file_ok = download_id not in cancelled_downloads
                    except Exception as file_err:
                        app_logger.warning(f"[Download][Thingiverse] Échec sur {fname_item}: {file_err}")
                    finally:
                        if file_ok:
                            mark_download_complete_and_refresh_thumbnail(dest_path)
                            results.append(fname_item)
                            app_logger.info(f"[Download][Thingiverse] {fname_item} → {dest_path}")
                        else:
                            currently_downloading_paths.discard(dest_path.replace('\\', '/'))
                            try:
                                if os.path.exists(dest_path):
                                    os.remove(dest_path)
                            except OSError as cleanup_err:
                                app_logger.warning(f"[Download][Thingiverse] Échec suppression fichier partiel {dest_path}: {cleanup_err}")

                    if download_id in cancelled_downloads:
                        break

                active_downloads.pop(download_id, None)
                if download_id in cancelled_downloads:
                    cancelled_downloads.discard(download_id)
                    return jsonify({"cancelled": True, "download_id": download_id}), 200
                if not results:
                    return jsonify({"error": "Aucun fichier n'a pu être téléchargé (connexion interrompue)."}), 502
                fname = results[0]
                file_size = os.path.getsize(os.path.join(save_dir, fname))
                for rf in results:
                    rp = os.path.join(save_dir, rf)
                    save_download_history(session['user_id'], rf, rp, os.path.getsize(rp) if os.path.exists(rp) else 0, os.path.splitext(rf)[1], url, 'Thingiverse')
                invalidate_cache()

                active_downloads.pop(download_id, None)
                return jsonify({"success": True, "filename": fname, "path": os.path.join(save_dir, fname), "size": file_size})

            else:
                zip_url = f"https://www.thingiverse.com/thing:{thing_id}/zip"
                resolved_url = zip_url

        elif 'printables.com' in parsed.netloc:
            if not any(url.lower().endswith(ext) for ext in ['.stl', '.3mf', '.obj', '.step', '.stp', '.amf', '.ply', '.zip']):
                m_id = re.search(r'/model/(\d+)', parsed.path) or re.search(r'/(\d+)(?:[/-]|$)', parsed.path)
                if not m_id:
                    active_downloads.pop(download_id, None)
                    return jsonify({
                        "error": "URL Printables non reconnue. Colle l'URL complète de la page du modèle (ex: https://www.printables.com/model/12345-mon-modele)"
                    }), 400

                model_id = m_id.group(1)

                printables_files = printables_get_model_files(model_id)
                if not printables_files:
                    active_downloads.pop(download_id, None)
                    return jsonify({
                        "error": "Aucun fichier STL/3D trouvé pour ce modèle Printables (modèle privé, retiré, ou ne contenant que des G-code/résine)."
                    }), 502

                total_files = len(printables_files)
                results = []
                for idx, pf in enumerate(printables_files):
                    dl_link = printables_get_download_link(pf['id'], model_id, pf['file_type'])
                    if not dl_link:
                        app_logger.warning(f"[Download][Printables] Lien introuvable pour {pf['name']}")
                        continue

                    fname_item = re.sub(r'[<>:"/\\|?*]', '_', pf['name']) or f"printables_{model_id}_{idx}.stl"
                    dest_path = os.path.join(save_dir, fname_item)
                    active_downloads[download_id]['filename'] = fname_item
                    currently_downloading_paths.add(dest_path.replace('\\', '/'))

                    file_ok = False
                    try:
                        with requests.get(dl_link, headers=DL_HEADERS, stream=True, timeout=120) as r_dl:
                            r_dl.raise_for_status()
                            total_bytes = int(r_dl.headers.get('Content-Length', 0))
                            downloaded_bytes = 0
                            with open(dest_path, 'wb') as f_out:
                                for chunk in r_dl.iter_content(chunk_size=65536):
                                    if download_id in cancelled_downloads:
                                        break
                                    if chunk:
                                        f_out.write(chunk)
                                        downloaded_bytes += len(chunk)
                                        base_pct = int(idx * 100 / total_files)
                                        file_pct = int(downloaded_bytes * 100 / total_bytes / total_files) if total_bytes else 0
                                        active_downloads[download_id]['percentage'] = base_pct + file_pct
                        file_ok = download_id not in cancelled_downloads
                    except Exception as file_err:
                        app_logger.warning(f"[Download][Printables] Échec sur {fname_item}: {file_err}")
                    finally:
                        if file_ok:
                            mark_download_complete_and_refresh_thumbnail(dest_path)
                            results.append(fname_item)
                            app_logger.info(f"[Download][Printables] {fname_item} → {dest_path}")
                        else:
                            currently_downloading_paths.discard(dest_path.replace('\\', '/'))
                            try:
                                if os.path.exists(dest_path):
                                    os.remove(dest_path)
                            except OSError as cleanup_err:
                                app_logger.warning(f"[Download][Printables] Échec suppression fichier partiel {dest_path}: {cleanup_err}")

                    if download_id in cancelled_downloads:
                        break

                active_downloads.pop(download_id, None)

                if download_id in cancelled_downloads:
                    cancelled_downloads.discard(download_id)
                    return jsonify({"cancelled": True, "download_id": download_id}), 200

                if not results:
                    return jsonify({
                        "error": "Impossible de récupérer les liens de téléchargement Printables pour ce modèle."
                    }), 502

                fname = results[0]
                file_size = os.path.getsize(os.path.join(save_dir, fname))
                for rf in results:
                    rp = os.path.join(save_dir, rf)
                    save_download_history(session['user_id'], rf, rp, os.path.getsize(rp) if os.path.exists(rp) else 0, os.path.splitext(rf)[1], url, 'Printables')
                invalidate_cache()

                active_downloads.pop(download_id, None)
                return jsonify({
                    "success": True,
                    "filename": fname,
                    "path": os.path.join(save_dir, fname),
                    "size": file_size,
                    "count": len(results),
                })

        elif 'makerworld.com' in parsed.netloc:
            m_id = re.search(r'/models/(\d+)', parsed.path)
            if not m_id:
                active_downloads.pop(download_id, None)
                return jsonify({
                    "error": "URL MakerWorld invalide. Format attendu : https://makerworld.com/en/models/XXXXXX"
                }), 400

            model_id = m_id.group(1)

            mw_profile_id = None
            url_fragment = urlparse(url).fragment
            m_prof = re.search(r'profileId[-=](\d+)', url_fragment or '')
            if not m_prof:
                m_prof = re.search(r'profileId[-=](\d+)', url)
            if m_prof:
                mw_profile_id = m_prof.group(1)
                app_logger.info(f"[MakerWorld] ProfileId ciblé depuis URL: {mw_profile_id}")

            mw_token = None
            try:
                conn = get_db()
                acc_row = conn.execute(
                    "SELECT api_key FROM account_credentials WHERE user_id = ? AND platform = 'makerworld'",
                    (session['user_id'],)
                ).fetchone()
                conn.close()
                if acc_row and acc_row['api_key']:
                    mw_token = decrypt_account_secret(acc_row['api_key'])
            except Exception:
                pass

            if not mw_token:
                active_downloads.pop(download_id, None)
                return jsonify({
                    "error": "Compte MakerWorld non configuré. Ajoutez votre compte dans Paramètres → Comptes externes → MakerWorld."
                }), 400

            mw_files = makerworld_get_model_files(model_id, mw_token, profile_id=mw_profile_id, preferred_format=preferred_format)
            if not mw_files:
                active_downloads.pop(download_id, None)
                return jsonify({
                    "error": "Aucun fichier 3D trouvé pour ce modèle MakerWorld. Vérifiez que le modèle est public et que votre compte est bien connecté."
                }), 404

            mw_dl_headers = {
                "User-Agent": "BambuStudio/01.09.00.00",
            }

            total_files = len(mw_files)
            results = []
            for idx, mf in enumerate(mw_files):
                if not mf.get('url'):
                    continue

                fname_item = re.sub(r'[<>:"/\\|?*]', '_', mf['name']) or f"makerworld_{model_id}_{idx}.3mf"
                dest_path = os.path.join(save_dir, fname_item)
                active_downloads[download_id]['filename'] = fname_item
                currently_downloading_paths.add(dest_path.replace('\\', '/'))

                try:
                    import urllib.request as _urllib_req
                    req = _urllib_req.Request(mf['url'], headers=mw_dl_headers)
                    with _urllib_req.urlopen(req, timeout=120) as r_dl:
                        total_bytes = int(r_dl.headers.get('Content-Length') or 0)
                        downloaded_bytes = 0
                        with open(dest_path, 'wb') as f_out:
                            while True:
                                chunk = r_dl.read(65536)
                                if not chunk:
                                    break
                                f_out.write(chunk)
                                downloaded_bytes += len(chunk)
                                base_pct = int(idx * 100 / total_files)
                                file_pct = int(downloaded_bytes * 100 / total_bytes / total_files) if total_bytes else 0
                                active_downloads[download_id]['percentage'] = base_pct + file_pct

                    if fname_item.lower().endswith('.zip') and zipfile.is_zipfile(dest_path):
                        app_logger.info(f"[MakerWorld] ZIP détecté, extraction des fichiers 3D...")
                        extracted = []
                        with zipfile.ZipFile(dest_path, 'r') as zf:
                            for zname in zf.namelist():
                                zext = os.path.splitext(zname)[1].lower()
                                if zext in ('.stl', '.3mf', '.obj'):
                                    safe_zname = re.sub(r'[<>:"/\\|?*]', '_', os.path.basename(zname))
                                    out_path = os.path.join(save_dir, safe_zname)
                                    with zf.open(zname) as zf_src, open(out_path, 'wb') as zf_dst:
                                        shutil.copyfileobj(zf_src, zf_dst)
                                    extracted.append(safe_zname)
                                    app_logger.info(f"[MakerWorld] Extrait: {safe_zname}")
                        os.remove(dest_path)
                        currently_downloading_paths.discard(dest_path.replace('\\', '/'))

                        if extracted:
                            for ef in extracted:
                                ep = os.path.join(save_dir, ef)
                                mark_download_complete_and_refresh_thumbnail(ep)
                                results.append(ef)
                            app_logger.info(f"[MakerWorld] ZIP extrait: {len(extracted)} fichier(s)")
                            continue

                    elif preferred_format == 'stl' and fname_item.lower().endswith('.3mf'):
                        stl_name = os.path.splitext(fname_item)[0] + '.stl'
                        stl_path = os.path.join(save_dir, stl_name)
                        app_logger.info(f"[MakerWorld] Conversion 3MF→STL : {fname_item} → {stl_name}")
                        converted = False
                        try:
                            scene = trimesh.load(dest_path, force='scene')
                            if isinstance(scene, trimesh.Scene):
                                meshes = [g for g in scene.geometry.values()
                                          if isinstance(g, trimesh.Trimesh) and len(g.faces) > 0]
                                combined = trimesh.util.concatenate(meshes) if meshes else trimesh.Trimesh()
                            else:
                                combined = scene
                            combined.export(stl_path, file_type='stl')
                            app_logger.info(f"[MakerWorld] ✅ STL exporté: {stl_name} ({os.path.getsize(stl_path)} octets)")
                            converted = True
                        except Exception as e_conv:
                            app_logger.error(f"[MakerWorld] Erreur conversion 3MF→STL: {e_conv}")
                            app_logger.warning(f"[MakerWorld] Conversion échouée, conservation du 3MF: {fname_item}")

                        if converted:
                            os.remove(dest_path)
                            currently_downloading_paths.discard(dest_path.replace('\\', '/'))
                            mark_download_complete_and_refresh_thumbnail(stl_path)
                            results.append(stl_name)
                            app_logger.info(f"[Download][MakerWorld] {stl_name} → {stl_path}")
                            continue

                    currently_downloading_paths.discard(dest_path.replace('\\', '/'))
                    mark_download_complete_and_refresh_thumbnail(dest_path)
                    results.append(fname_item)
                    app_logger.info(f"[Download][MakerWorld] {fname_item} → {dest_path}")

                except Exception as e_dl:
                    currently_downloading_paths.discard(dest_path.replace('\\', '/'))
                    app_logger.error(f"[MakerWorld] Erreur téléchargement {fname_item}: {e_dl}")
                    try:
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                    except OSError as cleanup_err:
                        app_logger.warning(f"[MakerWorld] Échec suppression fichier partiel {dest_path}: {cleanup_err}")

            if not results:
                return jsonify({'error': 'Aucun fichier téléchargé depuis MakerWorld.'}), 502

            fname = results[0]
            file_size = os.path.getsize(os.path.join(save_dir, fname))
            for rf in results:
                rp = os.path.join(save_dir, rf)
                save_download_history(
                    session['user_id'], rf, rp,
                    os.path.getsize(rp) if os.path.exists(rp) else 0,
                    os.path.splitext(rf)[1], url, 'MakerWorld'
                )
            invalidate_cache()

            active_downloads.pop(download_id, None)
            return jsonify({
                "success": True,
                "filename": fname,
                "path": os.path.join(save_dir, fname),
                "size": file_size,
                "count": len(results),
            })

        with requests.get(resolved_url, headers=DL_HEADERS, stream=True, timeout=120,
                          allow_redirects=True) as r:
            r.raise_for_status()

            content_type = r.headers.get('Content-Type', '')
            if 'text/html' in content_type and 'thingiverse.com' in resolved_url:
                active_downloads.pop(download_id, None)
                return jsonify({
                    "error": "Thingiverse requiert une clé API pour télécharger. Ajoutez votre token dans Paramètres → Comptes externes → Thingiverse."
                }), 400

            cd = r.headers.get('Content-Disposition', '')
            fname = ''
            if 'filename' in cd:
                m_cd = re.search(r"filename\*?=['\"]?(?:UTF-\d['\"]*)?([^;'\"\r\n]+)", cd)
                if m_cd:
                    fname = unquote(m_cd.group(1).strip().strip('"\''))

            if not fname:
                fname = os.path.basename(urlparse(r.url).path) or f'thingiverse_{thing_id if "thingiverse" in url else "model"}.zip'

            fname = re.sub(r'[<>:"/\\|?*]', '_', fname) or 'fichier_3d.stl'

            total = int(r.headers.get('Content-Length', 0))
            active_downloads[download_id]['filename'] = fname
            active_downloads[download_id]['total'] = total

            dest_path = os.path.join(save_dir, fname)
            downloaded = 0
            currently_downloading_paths.add(dest_path.replace('\\', '/'))

            download_completed = False
            try:
                with open(dest_path, 'wb') as f_out:
                    for chunk in r.iter_content(chunk_size=65536):
                        if download_id in cancelled_downloads:
                            break
                        if chunk:
                            f_out.write(chunk)
                            downloaded += len(chunk)
                            pct = int(downloaded * 100 / total) if total else 0
                            active_downloads[download_id]['current'] = downloaded
                            active_downloads[download_id]['percentage'] = pct
                download_completed = download_id not in cancelled_downloads
            finally:
                if download_completed:
                    mark_download_complete_and_refresh_thumbnail(dest_path)
                else:
                    currently_downloading_paths.discard(dest_path.replace('\\', '/'))
                    try:
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                            app_logger.info(f"[Download] Fichier partiel supprimé après échec: {dest_path}")
                    except OSError as cleanup_err:
                        app_logger.warning(f"[Download] Échec suppression fichier partiel {dest_path}: {cleanup_err}")

            if download_id in cancelled_downloads:
                cancelled_downloads.discard(download_id)
                active_downloads.pop(download_id, None)
                return jsonify({"cancelled": True, "download_id": download_id}), 200

            file_size = os.path.getsize(dest_path)
            if file_size < 100:
                os.remove(dest_path)
                active_downloads.pop(download_id, None)
                return jsonify({"error": "Le fichier téléchargé est vide ou invalide. Vérifiez l'URL ou configurez votre clé API."}), 400

            active_downloads.pop(download_id, None)

            platform_name = 'Thingiverse' if 'thingiverse' in url else ('MakerWorld' if 'makerworld' in url else '')
            save_download_history(session['user_id'], fname, dest_path, file_size, os.path.splitext(fname)[1], url, platform_name)
            invalidate_cache()

            app_logger.info(f"[Download] Fichier téléchargé : {fname} ({file_size} octets) → {dest_path}")

            active_downloads.pop(download_id, None)
            return jsonify({
                "success": True,
                "filename": fname,
                "path": dest_path,
                "size": file_size,
            })

    except requests.exceptions.HTTPError as e:
        active_downloads.pop(download_id, None)
        app_logger.error(f"[Download] HTTP Error: {e}")
        status_code = e.response.status_code if e.response is not None else 0
        if status_code == 403:
            return jsonify({"error": "Accès refusé (403). Ce site requiert une authentification. Configurez votre clé API dans les Paramètres."}), 502
        return jsonify({"error": f"Erreur HTTP {status_code} lors du téléchargement."}), 502

    except requests.exceptions.ConnectionError:
        active_downloads.pop(download_id, None)
        return jsonify({"error": "Impossible de se connecter à l'URL fournie. Vérifiez votre connexion internet."}), 502

    except Exception as e:
        active_downloads.pop(download_id, None)
        app_logger.error(f"[Download] Erreur: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


def _ensure_download_folder_registered(path, user_id):
    try:
        normalized = os.path.normpath(path)
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT path FROM sources WHERE user_id = ? AND type = 'folder'",
                (user_id,)
            ).fetchall()
            if any(os.path.normpath(r['path']) == normalized for r in rows):
                return

            name = "Téléchargements"
            existing_names = {r['name'] for r in conn.execute(
                "SELECT name FROM sources WHERE user_id = ?", (user_id,)
            ).fetchall()}
            if name in existing_names:
                suffix = 2
                while f"{name} ({suffix})" in existing_names:
                    suffix += 1
                name = f"{name} ({suffix})"

            conn.execute(
                "INSERT INTO sources (user_id, name, type, path, config) VALUES (?, ?, 'folder', ?, '{}')",
                (user_id, name, normalized)
            )
            conn.commit()
            invalidate_cache()
            app_logger.info(f"[Download] Dossier de téléchargement par défaut enregistré comme source: {normalized}")
        finally:
            conn.close()
    except Exception as e:
        app_logger.warning(f"[Download] Échec enregistrement source dossier par défaut: {e}")


def save_download_history(user_id, file_name, file_path, file_size, file_ext, source_url, platform):
    try:
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO download_history (user_id, file_name, file_path, file_size, file_ext, source_url, platform) VALUES (?,?,?,?,?,?,?)",
                (user_id, file_name, file_path, file_size, file_ext, source_url, platform)
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        app_logger.error(f"[DownloadHistory] Erreur save: {e}")

@app.route('/api/download-history', methods=['GET'])
@login_required
def api_get_download_history():
    try:
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT * FROM download_history WHERE user_id=? ORDER BY downloaded_at DESC",
                (session['user_id'],)
            ).fetchall()
        finally:
            conn.close()
        return jsonify([dict(r) for r in rows]), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/download-history/clear', methods=['DELETE'])
@login_required
def api_clear_download_history():
    try:
        conn = get_db()
        try:
            conn.execute("DELETE FROM download_history WHERE user_id=?", (session['user_id'],))
            conn.commit()
        finally:
            conn.close()
        return jsonify({"message": "Historique vidé"}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/file/data', methods=['GET'])
@login_required
def api_get_file_data():
    file_path = request.args.get('path')
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400

    try:
        file_path = unquote(file_path)
    except:
        pass

    if not os.path.exists(file_path):
        app_logger.info(f"[WARN] Fichier non trouvé: {file_path}")
        return jsonify({"error": "Fichier non trouvé"}), 404

    if not _is_path_within_sources(file_path, session['user_id']):
        app_logger.warning(f"[SECURITY] Tentative de lecture hors sources: {file_path}")
        return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

    if not os.access(file_path, os.R_OK):
        app_logger.info(f"[WARN] Permission refusée: {file_path}")
        return jsonify({"error": "Permission refusée"}), 403

    try:
        return send_file(file_path)
    except Exception as e:
        app_logger.info(f"[ERROR] Erreur envoi fichier: {e}")
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/favorites', methods=['GET'])
@login_required
def api_get_favorites():
    try:
        conn = get_db()
        try:
            favorites = conn.execute(
                "SELECT file_path FROM favorites WHERE user_id = ?",
                (session['user_id'],)
            ).fetchall()
        finally:
            conn.close()

        favorite_paths = [f['file_path'] for f in favorites]
        return jsonify(favorite_paths)

    except Exception as e:
        app_logger.info(f"[ERROR] api_get_favorites: {e}")
        return jsonify([]), 500

@app.route('/api/favorites', methods=['POST'])
@login_required
def api_toggle_favorite():
    try:
        data = request.json
        file_path = data.get('path')
        if not file_path:
            return jsonify({"error": "Chemin requis"}), 400

        conn = get_db()
        existing = conn.execute(
            "SELECT file_path FROM favorites WHERE user_id = ? AND file_path = ?",
            (session['user_id'], file_path)
        ).fetchone()

        if existing:
            conn.execute(
                "DELETE FROM favorites WHERE user_id = ? AND file_path = ?",
                (session['user_id'], file_path)
            )
            conn.commit()
            conn.close()
            return jsonify({"favorited": False, "message": "Retiré des favoris"})
        else:
            conn.execute(
                "INSERT INTO favorites (user_id, file_path) VALUES (?, ?)",
                (session['user_id'], file_path)
            )
            conn.commit()
            conn.close()
            return jsonify({"favorited": True, "message": "Ajouté aux favoris"})

    except Exception as e:
        app_logger.info(f"[ERROR] api_toggle_favorite: {e}")
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/projects', methods=['GET'])
@login_required
def api_get_projects():
    try:
        conn = get_db()
        try:
            projects = conn.execute(
                "SELECT * FROM projects WHERE user_id = ? ORDER BY updated_at DESC",
                (session['user_id'],)
            ).fetchall()

            result = []
            for p in projects:
                pf = conn.execute(
                    "SELECT file_path, quantity_needed, quantity_printed FROM project_files WHERE project_id = ? ORDER BY position, added_at",
                    (p['id'],)
                ).fetchall()
                files = [dict(f) for f in pf]
                total_needed = sum(f['quantity_needed'] for f in files)
                total_printed = sum(min(f['quantity_printed'], f['quantity_needed']) for f in files)
                result.append({
                    "id": p['id'],
                    "name": p['name'],
                    "description": p['description'],
                    "color": p['color'],
                    "status": p['status'],
                    "created_at": p['created_at'],
                    "updated_at": p['updated_at'],
                    "file_count": len(files),
                    "total_needed": total_needed,
                    "total_printed": total_printed,
                    "progress": round((total_printed / total_needed) * 100) if total_needed > 0 else 0,
                    "files": [f['file_path'] for f in files[:4]]
                })
        finally:
            conn.close()
        return jsonify(result)
    except Exception as e:
        app_logger.info(f"[ERROR] api_get_projects: {e}")
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/projects', methods=['POST'])
@login_required
def api_create_project():
    data = request.json or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    color = data.get('color', '#4ea1d3')
    if not name:
        return jsonify({"error": "Nom requis"}), 400

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO projects (user_id, name, description, color) VALUES (?, ?, ?, ?)",
            (session['user_id'], name, description, color)
        )
        conn.commit()
        project_id = cur.lastrowid

        files = data.get('files', [])
        for i, item in enumerate(files):
            file_path = item.get('path') if isinstance(item, dict) else item
            qty = item.get('quantity', 1) if isinstance(item, dict) else 1
            if file_path:
                conn.execute(
                    "INSERT OR IGNORE INTO project_files (project_id, file_path, quantity_needed, position) VALUES (?, ?, ?, ?)",
                    (project_id, file_path, max(1, int(qty)), i)
                )
        conn.commit()
        return jsonify({"id": project_id, "message": "Projet créé"}), 201
    except Exception as e:
        app_logger.info(f"[ERROR] api_create_project: {e}")
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500
    finally:
        conn.close()

@app.route('/api/projects/<int:project_id>', methods=['GET'])
@login_required
def api_get_project(project_id):
    conn = get_db()
    p = conn.execute(
        "SELECT * FROM projects WHERE id = ? AND user_id = ?",
        (project_id, session['user_id'])
    ).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "Introuvable"}), 404

    files = conn.execute(
        "SELECT file_path, quantity_needed, quantity_printed, notes, position FROM project_files WHERE project_id = ? ORDER BY position, added_at",
        (project_id,)
    ).fetchall()
    conn.close()
    return jsonify({
        "id": p['id'],
        "name": p['name'],
        "description": p['description'],
        "color": p['color'],
        "status": p['status'],
        "created_at": p['created_at'],
        "updated_at": p['updated_at'],
        "files": [dict(f) for f in files]
    })

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
@login_required
def api_update_project(project_id):
    data = request.json or {}
    conn = get_db()
    p = conn.execute(
        "SELECT id FROM projects WHERE id = ? AND user_id = ?",
        (project_id, session['user_id'])
    ).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "Introuvable"}), 404
    try:
        fields, params = [], []
        for key in ('name', 'description', 'color', 'status'):
            if key in data:
                fields.append(f"{key} = ?")
                params.append(data[key])
        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.extend([project_id, session['user_id']])
            conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id = ? AND user_id = ?", params)
            conn.commit()
        return jsonify({"message": "Mis à jour"})
    except Exception as e:
        app_logger.info(f"[ERROR] api_update_project: {e}")
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500
    finally:
        conn.close()

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
@login_required
def api_delete_project(project_id):
    conn = get_db()
    p = conn.execute(
        "SELECT id FROM projects WHERE id = ? AND user_id = ?",
        (project_id, session['user_id'])
    ).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "Introuvable"}), 404
    conn.execute("DELETE FROM project_files WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Projet supprimé"})

@app.route('/api/projects/<int:project_id>/files', methods=['POST'])
@login_required
def api_add_project_files(project_id):
    data = request.json or {}
    conn = get_db()
    p = conn.execute(
        "SELECT id FROM projects WHERE id = ? AND user_id = ?",
        (project_id, session['user_id'])
    ).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "Introuvable"}), 404
    try:
        files = data.get('files', [])
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) as m FROM project_files WHERE project_id = ?", (project_id,)
        ).fetchone()['m']
        added = 0
        for i, item in enumerate(files):
            file_path = item.get('path') if isinstance(item, dict) else item
            qty = item.get('quantity', 1) if isinstance(item, dict) else 1
            if not file_path:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO project_files (project_id, file_path, quantity_needed, position) VALUES (?, ?, ?, ?)",
                (project_id, file_path, max(1, int(qty)), max_pos + 1 + i)
            )
            added += 1
        conn.execute("UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project_id,))
        conn.commit()
        return jsonify({"message": f"{added} fichier(s) ajouté(s)", "added": added})
    except Exception as e:
        app_logger.info(f"[ERROR] api_add_project_files: {e}")
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500
    finally:
        conn.close()

@app.route('/api/projects/<int:project_id>/files', methods=['PUT'])
@login_required
def api_update_project_file(project_id):
    data = request.json or {}
    file_path = data.get('path')
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400
    conn = get_db()
    p = conn.execute(
        "SELECT id FROM projects WHERE id = ? AND user_id = ?",
        (project_id, session['user_id'])
    ).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "Introuvable"}), 404
    try:
        fields, params = [], []
        if 'quantity_needed' in data:
            fields.append("quantity_needed = ?")
            params.append(max(1, int(data['quantity_needed'])))
        if 'quantity_printed' in data:
            fields.append("quantity_printed = ?")
            params.append(max(0, int(data['quantity_printed'])))
        if 'notes' in data:
            fields.append("notes = ?")
            params.append(data['notes'])
        if fields:
            params.extend([project_id, file_path])
            conn.execute(f"UPDATE project_files SET {', '.join(fields)} WHERE project_id = ? AND file_path = ?", params)
            conn.execute("UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project_id,))
            conn.commit()
        return jsonify({"message": "Mis à jour"})
    except Exception as e:
        app_logger.info(f"[ERROR] api_update_project_file: {e}")
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500
    finally:
        conn.close()

@app.route('/api/projects/<int:project_id>/files', methods=['DELETE'])
@login_required
def api_remove_project_file(project_id):
    data = request.json or {}
    file_path = data.get('path')
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400
    conn = get_db()
    p = conn.execute(
        "SELECT id FROM projects WHERE id = ? AND user_id = ?",
        (project_id, session['user_id'])
    ).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "Introuvable"}), 404
    conn.execute("DELETE FROM project_files WHERE project_id = ? AND file_path = ?", (project_id, file_path))
    conn.execute("UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Retiré du projet"})


@app.route('/api/accounts/status', methods=['GET'])
@login_required
def api_accounts_status():
    status = {
        'thingiverse': False,
        'makerworld': False,
    }

    conn = get_db()
    try:
        accounts = conn.execute(
            "SELECT platform, email, api_key, last_login FROM account_credentials WHERE user_id = ?",
            (session['user_id'],)
        ).fetchall()
    finally:
        conn.close()

    for acc in accounts:
        platform = acc['platform']
        if platform == 'thingiverse' and acc['api_key']:
            status['thingiverse'] = True
        elif platform == 'makerworld' and acc['api_key']:
            status['makerworld'] = True
            status['makerworld_email'] = acc['email'] or ''

    return jsonify(status)


@app.route('/api/files/repair', methods=['POST'])
@login_required
def api_repair_file():
    data = request.json
    file_path = data.get('path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Fichier non trouvé"}), 404
    if not _is_path_within_sources(file_path, session['user_id']):
        app_logger.warning(f"[SECURITY] Tentative de réparation hors sources: {file_path}")
        return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

    def _load_mesh_to_repair():
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.3mf':
            return load_3mf_mesh(file_path)
        elif ext == '.obj':
            return trimesh.load(file_path, force='mesh', process=False)
        else:
            return trimesh.load(file_path, force='mesh')

    try:
        ext = os.path.splitext(file_path)[1].lower()
        load_timeout = get_integrity_timeout(file_path)
        with ThreadPoolExecutor(max_workers=1) as _load_pool:
            _load_future = _load_pool.submit(_load_mesh_to_repair)
            try:
                mesh = _load_future.result(timeout=load_timeout)
            except FuturesTimeoutError:
                return jsonify({"error": f"Délai dépassé lors de la lecture du fichier (>{load_timeout:.0f}s). "
                                          f"Le fichier semble valide mais le partage réseau est trop lent — "
                                          f"réessayez, ou copiez-le en local avant de le réparer."}), 504

        if isinstance(mesh, trimesh.Scene):
            geoms = [m for m in mesh.geometry.values() if hasattr(m, 'vertices') and len(m.vertices) > 0]
            if not geoms: return jsonify({"error": "Maillage vide"}), 400
            mesh = trimesh.util.concatenate(geoms)

        def _winding_ok(m):
            try:
                return bool(m.is_winding_consistent)
            except Exception:
                return True

        was_watertight_initially = mesh.is_watertight
        if was_watertight_initially and _winding_ok(mesh):
            return jsonify({"success": True, "message": "Déjà valide (watertight)"})

        backup_path = file_path + ".bak"
        if not os.path.exists(backup_path):
            shutil.copy2(file_path, backup_path)

        if was_watertight_initially:
            trimesh.repair.fix_winding(mesh)
            trimesh.repair.fix_normals(mesh, multibody=True)
        else:
            _repair_mesh_inplace(mesh)
            if not mesh.is_watertight:
                trimesh.repair.fix_winding(mesh)
                trimesh.repair.fill_holes(mesh)
                trimesh.repair.fix_normals(mesh)

            if not mesh.is_watertight and HAS_PYMESHFIX:
                try:
                    fixer = pymeshfix.MeshFix(mesh.vertices.copy(), mesh.faces.copy())
                    try:
                        fixer.repair(verbose=False)
                    except TypeError:
                        fixer.repair()
                    if fixer.v is not None and len(fixer.v) > 0:
                        mesh = trimesh.Trimesh(vertices=fixer.v, faces=fixer.f, process=True)
                except Exception as e:
                    app_logger.warning(f"[Repair] Passe pymeshfix échouée pour {file_path}: {e}")

        still_broken = not (mesh.is_watertight and _winding_ok(mesh))

        mark_repair_attempted(file_path)

        if ext in ['.stl', '.obj']:
            mesh.export(file_path, file_type=ext[1:])
        else:
            out_path = os.path.splitext(file_path)[0] + "_repaired.stl"
            mesh.export(out_path, file_type='stl')
            invalidate_cache()
            if still_broken:
                return jsonify({
                    "success": True, "partial": True, "watertight": False,
                    "message": "Exporté en STL, mais le maillage présente encore des problèmes non résolus automatiquement (géométrie complexe non-manifold)",
                    "new_path": out_path
                })
            return jsonify({"success": True, "watertight": True, "message": "Exporté en STL réparé (format original non supporté)", "new_path": out_path})

        invalidate_cache()

        if still_broken:
            return jsonify({
                "success": True, "partial": True, "watertight": False,
                "message": "Réparation partielle : le maillage a été nettoyé mais présente encore des problèmes non résolus automatiquement (trous complexes ou géométrie non-manifold). Une sauvegarde a été conservée (.bak)."
            })

        return jsonify({"success": True, "watertight": True, "message": "Réparé avec succès"})

    except Exception as e:
        app_logger.error(f"[Repair] Erreur: {e}")
        return jsonify({"error": f"Échec: {str(e)}"}), 500


CONVERT_SUPPORTED_FORMATS = ('stl', '3mf', 'obj')
CONVERT_UNIT_TO_MM = {
    'mm': 1.0,
    'cm': 10.0,
    'm': 1000.0,
    'in': 25.4,
    'ft': 304.8,
}


def _repair_mesh_inplace(mesh):
    repaired = {'normals': False, 'holes_filled': False, 'cleaned': False}
    try:
        mesh.merge_vertices()
    except Exception:
        pass
    try:
        trimesh.repair.fix_normals(mesh, multibody=True)
        repaired['normals'] = True
    except Exception:
        pass
    try:
        was_watertight = mesh.is_watertight
        trimesh.repair.fill_holes(mesh)
        repaired['holes_filled'] = (not was_watertight) and mesh.is_watertight
    except Exception:
        pass
    try:
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.update_faces(mesh.unique_faces())
        repaired['cleaned'] = True
    except Exception:
        pass
    return repaired


def _load_mesh_for_conversion(file_path):
    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    if ext == '3mf':
        mesh = load_3mf_mesh(file_path)
    elif ext == 'obj':
        mesh = trimesh.load(file_path, force='mesh', process=False)
    elif ext == 'stl':
        mesh = trimesh.load(file_path, force='mesh')
    else:
        raise ValueError(f"Format d'entrée non supporté: .{ext}")

    if mesh is None:
        raise ValueError("Impossible de lire le maillage")

    if isinstance(mesh, trimesh.Scene):
        geoms = [m for m in mesh.geometry.values() if hasattr(m, 'vertices') and len(m.vertices) > 0]
        if not geoms:
            raise ValueError("Maillage vide")
        mesh = trimesh.util.concatenate(geoms)

    if mesh.is_empty or len(mesh.vertices) == 0:
        raise ValueError("Maillage vide")

    return mesh


def _convert_single_file(file_path, target_format, delete_original, repair=False, source_unit='mm'):
    target_format = (target_format or '').lower().lstrip('.')
    if target_format not in CONVERT_SUPPORTED_FORMATS:
        return {"success": False, "path": file_path, "error": "Format de sortie non supporté"}

    if not file_path or not os.path.exists(file_path):
        return {"success": False, "path": file_path, "error": "Fichier non trouvé"}

    src_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    if src_ext not in CONVERT_SUPPORTED_FORMATS:
        return {"success": False, "path": file_path, "error": "Format d'entrée non supporté"}
    if src_ext == target_format:
        return {"success": False, "path": file_path, "error": "Le fichier est déjà dans ce format"}

    try:
        mesh = _load_mesh_for_conversion(file_path)

        repaired_info = None
        if repair:
            repaired_info = _repair_mesh_inplace(mesh)

        scale_factor = CONVERT_UNIT_TO_MM.get((source_unit or 'mm').lower(), 1.0)
        if scale_factor != 1.0:
            mesh.apply_scale(scale_factor)

        base_dir = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        out_path = os.path.join(base_dir, f"{base_name}.{target_format}")

        counter = 1
        while os.path.exists(out_path):
            out_path = os.path.join(base_dir, f"{base_name} ({counter}).{target_format}")
            counter += 1

        mesh.export(out_path, file_type=target_format)

        original_size = os.path.getsize(file_path)
        new_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        size_reduction_pct = round((1 - new_size / original_size) * 100, 1) if original_size > 0 else 0

        deleted_original = False
        if delete_original:
            try:
                os.remove(file_path)
                deleted_original = True
                normalized_old = file_path.replace('\\', '/')
                old_thumb = os.path.join(THUMBNAILS_DIR, hashlib.md5(normalized_old.encode()).hexdigest() + '.webp')
                if os.path.exists(old_thumb):
                    os.remove(old_thumb)
            except Exception as e:
                app_logger.warning(f"[Convert] Suppression de l'original impossible pour {os.path.basename(file_path)}: {e}")

        invalidate_cache()

        normalized_new = out_path.replace('\\', '/')
        new_thumb_path = os.path.join(THUMBNAILS_DIR, hashlib.md5(normalized_new.encode()).hexdigest() + '.webp')
        _queue_thumb_task(out_path, new_thumb_path, priority='high')

        app_logger.info(
            f"[CONVERT] {os.path.basename(file_path)} → {os.path.basename(out_path)} "
            f"(original {'supprimé' if deleted_original else 'conservé'}"
            f"{', réparé' if repair else ''}"
            f"{f', échelle x{scale_factor}' if scale_factor != 1.0 else ''})"
        )
        return {
            "success": True, "path": file_path, "new_path": out_path,
            "deleted_original": deleted_original,
            "original_size": original_size, "new_size": new_size,
            "size_reduction_pct": size_reduction_pct,
            "repaired": repaired_info,
        }

    except Exception as e:
        app_logger.error(f"[Convert] Erreur pour {os.path.basename(file_path)}: {e}")
        return {"success": False, "path": file_path, "error": f"Échec de la conversion : {str(e)}"}


@app.route('/api/files/convert', methods=['POST'])
@login_required
def api_convert_file():
    data = request.json or {}
    file_path = data.get('path')
    target_format = data.get('target_format')
    delete_original = bool(data.get('delete_original', False))
    repair = bool(data.get('repair', False))
    source_unit = data.get('source_unit', 'mm')

    if not file_path or not _is_path_within_sources(file_path, session['user_id']):
        app_logger.warning(f"[SECURITY] Tentative de conversion hors sources: {file_path}")
        return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

    result = _convert_single_file(file_path, target_format, delete_original, repair=repair, source_unit=source_unit)
    if result.get('success'):
        return jsonify(result)
    return jsonify({"error": result.get('error', 'Échec de la conversion')}), 400


@app.route('/api/files/convert-batch', methods=['POST'])
@login_required
def api_convert_file_batch():
    data = request.json or {}
    paths = data.get('paths')
    target_format = data.get('target_format')
    delete_original = bool(data.get('delete_original', False))
    repair = bool(data.get('repair', False))
    source_unit = data.get('source_unit', 'mm')

    if not paths or not isinstance(paths, list):
        return jsonify({"error": "Liste de chemins requise"}), 400

    for p in paths:
        if not _is_path_within_sources(p, session['user_id']):
            app_logger.warning(f"[SECURITY] Tentative de conversion batch hors sources: {p}")
            return jsonify({"error": "Un ou plusieurs fichiers n'appartiennent à aucune source configurée"}), 403

    results = [_convert_single_file(p, target_format, delete_original, repair=repair, source_unit=source_unit) for p in paths]
    succeeded = sum(1 for r in results if r.get('success'))
    app_logger.info(f"[CONVERT-BATCH] {succeeded}/{len(results)} fichier(s) converti(s) avec succès")
    return jsonify({"success": True, "results": results, "converted": succeeded, "total": len(results)})


INTEGRITY_CHECK_BASE_TIMEOUT = 45
INTEGRITY_CHECK_TIMEOUT_PER_MB = 1.0
INTEGRITY_CHECK_TIMEOUT_MAX = 180
INTEGRITY_CHECK_WORKERS = 4
INTEGRITY_REPORT_FILE = os.path.join(DATA_DIR, "integrity_report.json")


def get_integrity_timeout(file_path):
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
    except Exception:
        return INTEGRITY_CHECK_BASE_TIMEOUT
    timeout = INTEGRITY_CHECK_BASE_TIMEOUT + size_mb * INTEGRITY_CHECK_TIMEOUT_PER_MB
    return min(timeout, INTEGRITY_CHECK_TIMEOUT_MAX)

integrity_check_state = {
    'running': False,
    'total': 0,
    'checked': 0,
    'ok': 0,
    'corrupted': 0,
    'empty': 0,
    'missing': 0,
    'started_at': None,
    'finished_at': None,
    'problems': []
}
integrity_check_lock = threading.Lock()


def compute_file_checksum(file_path, algo='sha256'):
    h = hashlib.new(algo)
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def check_single_file_integrity(file_path):
    result = {'path': file_path, 'status': 'ok', 'error': None, 'checksum': None}

    if not os.path.exists(file_path):
        result['status'] = 'missing'
        result['error'] = "Fichier introuvable sur le disque"
        return result

    try:
        size = os.path.getsize(file_path)
    except Exception as e:
        result['status'] = 'corrupted'
        result['error'] = str(e)[:300]
        return result

    if size == 0:
        result['status'] = 'empty'
        result['error'] = "Fichier vide (0 octet)"
        return result

    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    if ext in CONVERT_SUPPORTED_FORMATS:
        try:
            _load_mesh_for_conversion(file_path)
        except Exception as e:
            result['status'] = 'corrupted'
            result['error'] = str(e)[:300]
            return result
    else:
        try:
            with open(file_path, 'rb') as f:
                f.read(64)
        except Exception as e:
            result['status'] = 'corrupted'
            result['error'] = str(e)[:300]
            return result

    try:
        result['checksum'] = compute_file_checksum(file_path)
    except Exception:
        pass
    return result


def _save_integrity_report():
    try:
        with open(INTEGRITY_REPORT_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'finished_at': integrity_check_state['finished_at'],
                'total': integrity_check_state['total'],
                'ok': integrity_check_state['ok'],
                'corrupted': integrity_check_state['corrupted'],
                'empty': integrity_check_state['empty'],
                'missing': integrity_check_state['missing'],
                'problems': integrity_check_state['problems']
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        app_logger.warning(f"[INTEGRITY] Échec sauvegarde rapport: {e}")


def _run_integrity_check(paths):
    global integrity_check_state
    with integrity_check_lock:
        integrity_check_state.update({
            'running': True, 'total': len(paths), 'checked': 0,
            'ok': 0, 'corrupted': 0, 'empty': 0, 'missing': 0,
            'started_at': time.time(), 'finished_at': None, 'problems': []
        })

    executor = ThreadPoolExecutor(max_workers=INTEGRITY_CHECK_WORKERS)
    paths_iter = iter(paths)
    pending = {}

    def _submit_next():
        try:
            p = next(paths_iter)
        except StopIteration:
            return False
        fut = executor.submit(check_single_file_integrity, p)
        pending[fut] = (p, time.time() + get_integrity_timeout(p))
        return True

    for _ in range(INTEGRITY_CHECK_WORKERS):
        if not _submit_next():
            break

    while pending:
        done, _ = futures_wait(list(pending.keys()), timeout=1, return_when=FIRST_COMPLETED)
        now = time.time()
        to_process = list(done) + [f for f, (p, deadline) in pending.items() if f not in done and now >= deadline]

        for fut in to_process:
            p, deadline = pending.pop(fut)
            if fut.done():
                try:
                    result = fut.result()
                except Exception as e:
                    result = {'path': p, 'status': 'corrupted', 'error': str(e)[:300]}
            else:
                result = {'path': p, 'status': 'corrupted',
                          'error': "Délai dépassé lors de la lecture (fichier probablement corrompu, trop volumineux ou partage réseau lent)"}

            with integrity_check_lock:
                integrity_check_state['checked'] += 1
                status = result.get('status', 'corrupted')
                if status == 'ok':
                    integrity_check_state['ok'] += 1
                else:
                    integrity_check_state[status] = integrity_check_state.get(status, 0) + 1
                    integrity_check_state['problems'].append({
                        'path': p,
                        'name': os.path.basename(p),
                        'status': status,
                        'error': result.get('error')
                    })
            _submit_next()

    executor.shutdown(wait=False)

    with integrity_check_lock:
        integrity_check_state['running'] = False
        integrity_check_state['finished_at'] = time.time()
        _save_integrity_report()

    app_logger.info(
        f"[INTEGRITY] Vérification terminée: {integrity_check_state['ok']} OK, "
        f"{integrity_check_state['corrupted'] + integrity_check_state['empty']} corrompu(s), "
        f"{integrity_check_state['missing']} manquant(s)"
    )


@app.route('/api/integrity/check', methods=['POST'])
@login_required
def api_integrity_check():
    if integrity_check_state['running']:
        return jsonify({"error": "Une vérification est déjà en cours"}), 409

    data = request.json or {}
    paths = data.get('paths')
    if not paths:
        cached = load_file_cache()
        if not cached:
            return jsonify({"error": "Aucun fichier à vérifier. Ouvrez la bibliothèque d'abord."}), 400
        paths = [f['path'] for f in cached if f.get('path')]

    if not isinstance(paths, list) or not paths:
        return jsonify({"error": "Aucun fichier à vérifier"}), 400

    threading.Thread(target=_run_integrity_check, args=(paths,), daemon=True).start()
    app_logger.info(f"[INTEGRITY] 🛡️ Démarrage de la vérification pour {len(paths)} fichier(s)")
    return jsonify({"started": True, "total": len(paths)})


@app.route('/api/integrity/progress', methods=['GET'])
@login_required
def api_integrity_progress():
    with integrity_check_lock:
        return jsonify({
            'running': integrity_check_state['running'],
            'total': integrity_check_state['total'],
            'checked': integrity_check_state['checked'],
            'ok': integrity_check_state['ok'],
            'corrupted': integrity_check_state['corrupted'],
            'empty': integrity_check_state['empty'],
            'missing': integrity_check_state['missing'],
            'problems': integrity_check_state['problems']
        })


BACKUP_MANIFEST_VERSION = 1

BACKUP_CATEGORY_TABLES = {
    'library': ['sources', 'tags', 'file_tags', 'favorites', 'projects', 'project_files'],
    'accounts': ['account_credentials'],
    'printers': ['printers'],
    'history': ['download_history', 'print_history', 'slicer_jobs'],
}
BACKUP_DEFAULT_INCLUDE = {'library': True, 'accounts': True, 'printers': True, 'history': True, 'settings': True}


def build_backup_zip_bytes(include=None):
    include = {**BACKUP_DEFAULT_INCLUDE, **(include or {})}
    tmp_db = None
    try:
        tmp_db = os.path.join(tempfile.gettempdir(), f'stellio_backup_{secrets.token_hex(6)}.db')

        src_conn = sqlite3.connect(DB_PATH)
        dst_conn = sqlite3.connect(tmp_db)
        with dst_conn:
            src_conn.backup(dst_conn)
        src_conn.close()

        tables_to_clear = []
        for category, tables in BACKUP_CATEGORY_TABLES.items():
            if not include.get(category, True):
                tables_to_clear.extend(tables)
        if tables_to_clear:
            cur = dst_conn.cursor()
            for table in tables_to_clear:
                try:
                    cur.execute(f"DELETE FROM {table}")
                except Exception as e:
                    app_logger.warning(f"[BACKUP] Impossible de vider la table {table}: {e}")
            dst_conn.commit()
            try:
                dst_conn.execute("VACUUM")
            except Exception:
                pass
        dst_conn.close()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmp_db, 'stellio.db')

            if include.get('settings', True) and os.path.exists(SETTINGS_FILE):
                zf.write(SETTINGS_FILE, 'app_settings.json')

            if include.get('accounts', True):
                if os.path.exists(KEY_FILE):
                    zf.write(KEY_FILE, 'encryption.key')
                iv_file = KEY_FILE.replace('.key', '.iv')
                if os.path.exists(iv_file):
                    zf.write(iv_file, 'encryption.iv')

            manifest = {
                'app': 'stellio',
                'manifest_version': BACKUP_MANIFEST_VERSION,
                'app_version': get_current_version(),
                'exported_at': datetime.datetime.now().isoformat(),
                'included': include
            }
            zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

        buf.seek(0)
        filename = f'stellio_backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        return buf.getvalue(), filename
    finally:
        if tmp_db and os.path.exists(tmp_db):
            try:
                os.remove(tmp_db)
            except Exception:
                pass


@app.route('/api/backup/export', methods=['POST'])
@login_required
def api_backup_export():
    try:
        data = request.get_json(silent=True) or {}
        include = data.get('include') or {}
        zip_bytes, filename = build_backup_zip_bytes(include=include)
        app_logger.info(f"[BACKUP] 📦 Export de sauvegarde généré: {filename} (inclus: {include})")
        return send_file(io.BytesIO(zip_bytes), mimetype='application/zip', as_attachment=True, download_name=filename)
    except Exception as e:
        app_logger.error(f"[BACKUP] Échec export: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/backup/import', methods=['POST'])
@login_required
def api_backup_import():
    if 'backup' not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    file = request.files['backup']
    if not file.filename.lower().endswith('.zip'):
        return jsonify({"error": "Le fichier doit être une archive .zip"}), 400

    tmp_zip = os.path.join(tempfile.gettempdir(), f'stellio_import_{secrets.token_hex(6)}.zip')
    file.save(tmp_zip)
    backup_dir = None

    try:
        with zipfile.ZipFile(tmp_zip, 'r') as zf:
            names = zf.namelist()
            if 'manifest.json' not in names or 'stellio.db' not in names:
                return jsonify({"error": "Archive invalide : ce n'est pas une sauvegarde Stellio."}), 400

            manifest = json.loads(zf.read('manifest.json').decode('utf-8'))

            backup_dir = os.path.join(DATA_DIR, 'backups', datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
            os.makedirs(backup_dir, exist_ok=True)
            for existing, dest_name in [(DB_PATH, 'stellio.db'), (SETTINGS_FILE, 'app_settings.json'),
                                          (KEY_FILE, 'encryption.key'), (KEY_FILE.replace('.key', '.iv'), 'encryption.iv')]:
                if os.path.exists(existing):
                    shutil.copy2(existing, os.path.join(backup_dir, dest_name))

            zf.extract('stellio.db', DATA_DIR)
            os.replace(os.path.join(DATA_DIR, 'stellio.db'), DB_PATH)

            if 'app_settings.json' in names:
                zf.extract('app_settings.json', DATA_DIR)
                os.replace(os.path.join(DATA_DIR, 'app_settings.json'), SETTINGS_FILE)

            if 'encryption.key' in names and 'encryption.iv' in names:
                zf.extract('encryption.key', DATA_DIR)
                zf.extract('encryption.iv', DATA_DIR)
                os.replace(os.path.join(DATA_DIR, 'encryption.key'), KEY_FILE)
                os.replace(os.path.join(DATA_DIR, 'encryption.iv'), KEY_FILE.replace('.key', '.iv'))

        global _settings_cache
        _settings_cache = {}
        invalidate_cache()

        app_logger.info(f"[BACKUP] ✅ Sauvegarde importée (exportée le {manifest.get('exported_at', '?')}). Copie de sécurité: {backup_dir}")
        return jsonify({"success": True, "restart_required": True, "backed_up_to": backup_dir})
    except zipfile.BadZipFile:
        return jsonify({"error": "Fichier .zip invalide ou corrompu"}), 400
    except Exception as e:
        app_logger.error(f"[BACKUP] Échec import: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500
    finally:
        try:
            os.remove(tmp_zip)
        except Exception:
            pass


_SENSITIVE_SETTINGS_KEYS = (
    'password', 'api_key', 'apikey', 'token', 'secret', 'smtp_password', 'code'
)


def _redact_secrets(obj):
    if isinstance(obj, dict):
        redacted = {}
        for k, v in obj.items():
            if isinstance(k, str) and any(s in k.lower() for s in _SENSITIVE_SETTINGS_KEYS):
                redacted[k] = "***masqué***" if v else v
            else:
                redacted[k] = _redact_secrets(v)
        return redacted
    if isinstance(obj, list):
        return [_redact_secrets(v) for v in obj]
    return obj


def _get_ram_info():
    try:
        if os.name == 'nt':
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return {
                'total_gb': round(stat.ullTotalPhys / (1024 ** 3), 1),
                'available_gb': round(stat.ullAvailPhys / (1024 ** 3), 1),
                'load_percent': stat.dwMemoryLoad,
            }
    except Exception:
        pass
    return None


def _collect_diagnostic_info():
    info = {'generated_at': datetime.datetime.now().isoformat(timespec='seconds')}

    try:
        info['app'] = {
            'version': CURRENT_VERSION,
            'frozen': bool(getattr(sys, 'frozen', False)),
            'data_dir': DATA_DIR,
            'python_version': platform.python_version(),
        }
    except Exception as e:
        info['app_error'] = str(e)

    try:
        info['os'] = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
        }
    except Exception as e:
        info['os_error'] = str(e)

    try:
        info['cpu'] = {'logical_cores': os.cpu_count()}
    except Exception:
        pass

    ram = _get_ram_info()
    if ram:
        info['ram'] = ram

    try:
        total, used, free = shutil.disk_usage(DATA_DIR)
        info['disk_data_dir'] = {
            'total_gb': round(total / (1024 ** 3), 1),
            'used_gb': round(used / (1024 ** 3), 1),
            'free_gb': round(free / (1024 ** 3), 1),
        }
    except Exception:
        pass

    try:
        conn = get_db()
        try:
            user_count = conn.execute("SELECT COUNT(*) c FROM users").fetchone()['c']
            printers = conn.execute("SELECT type, COUNT(*) c FROM printers GROUP BY type").fetchall()
            sources = conn.execute("SELECT type, COUNT(*) c FROM sources GROUP BY type").fetchall()
        finally:
            conn.close()
        info['stellio_db'] = {
            'users': user_count,
            'printers_by_type': {r['type']: r['c'] for r in printers},
            'sources_by_type': {r['type']: r['c'] for r in sources},
        }
    except Exception as e:
        info['stellio_db_error'] = str(e)

    try:
        info['settings'] = _redact_secrets(load_settings() or {})
    except Exception as e:
        info['settings_error'] = str(e)

    try:
        info['installed_slicers'] = sorted(list((get_cached_installed_slicers() or {}).keys()))
    except Exception:
        pass

    try:
        info['python_modules'] = _check_required_modules(log=False)
    except Exception as e:
        info['python_modules_error'] = str(e)

    try:
        info['remote_access_state'] = dict(_remote_state)
    except Exception:
        pass

    return info


def build_diagnostic_zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for suffix in ('', '.1', '.2', '.3'):
            path = LOG_FILE + suffix
            if os.path.exists(path):
                zf.write(path, arcname=f"logs/{os.path.basename(LOG_FILE)}{suffix}")

        diag = _collect_diagnostic_info()
        zf.writestr('diagnostic.json', json.dumps(diag, indent=2, ensure_ascii=False))

    buf.seek(0)
    filename = f"stellio-diagnostic-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    return buf.getvalue(), filename


@app.route('/api/logs/export', methods=['GET'])
@login_required
def api_export_logs():
    try:
        zip_bytes, filename = build_diagnostic_zip_bytes()
        buf = io.BytesIO(zip_bytes)
        return send_file(buf, mimetype='application/zip', as_attachment=True, download_name=filename)
    except Exception as e:
        app_logger.error(f"[LogsExport] Erreur: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


LOG_TAIL_INITIAL_BYTES = 50 * 1024
LOG_TAIL_MAX_CHUNK = 200 * 1024

@app.route('/api/logs/tail', methods=['GET'])
@login_required
def api_logs_tail():
    try:
        offset_param = request.args.get('offset', default='-1')
        try:
            offset = int(offset_param)
        except (TypeError, ValueError):
            offset = -1

        if not os.path.exists(LOG_FILE):
            return jsonify({"lines": "", "offset": 0, "size": 0}), 200

        size = os.path.getsize(LOG_FILE)

        if offset < 0:
            start = max(0, size - LOG_TAIL_INITIAL_BYTES)
        elif offset > size:
            start = 0
        else:
            start = offset

        with open(LOG_FILE, 'rb') as f:
            f.seek(start)
            chunk = f.read(LOG_TAIL_MAX_CHUNK)

        text = chunk.decode('utf-8', errors='replace')
        new_offset = start + len(chunk)

        return jsonify({
            "lines": text,
            "offset": new_offset,
            "size": size,
            "reset": start == 0 and offset > 0
        }), 200
    except Exception as e:
        app_logger.error(f"[LogsTail] Erreur: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/debug/session', methods=['GET'])
@login_required
def api_debug_session_status():
    return jsonify({"active": DEBUG_SESSION_ACTIVE}), 200


@app.route('/api/debug/enable', methods=['POST'])
@login_required
def api_debug_session_enable():
    try:
        with open(DEBUG_FLAG_FILE, 'w', encoding='utf-8') as f:
            f.write(str(int(time.time())))
        app_logger.warning("[DEBUG] Mode debug demandé — sera actif dès le prochain démarrage de l'app.")
        return jsonify({"success": True}), 200
    except Exception as e:
        app_logger.error(f"[DEBUG] Erreur activation du mode debug: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/settings', methods=['GET'])
@login_required
def api_get_settings():
    try:
        settings = load_settings() or {}
        settings.setdefault('default_slicer', 'system_default')
        settings.setdefault('lang', 'fr')
        settings.setdefault('ai_enabled', False)
        settings.setdefault('auto_scan_enabled', True)
        settings.setdefault('auto_scan_interval_minutes', 5)
        settings['launch_at_startup_supported'] = (sys.platform == 'win32')
        settings['launch_at_startup'] = is_startup_enabled()
        settings['launch_minimized'] = is_startup_minimized() if settings['launch_at_startup'] else bool(settings.get('launch_minimized', False))
        return jsonify(settings), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/settings', methods=['POST'])
@login_required
def api_save_settings():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données JSON requises"}), 400

        current_settings = load_settings() or {}
        previous_spoolman_url = (current_settings.get('spoolman_url') or '').strip()

        if 'launch_at_startup' in data or 'launch_minimized' in data:
            startup_enabled = bool(data.get('launch_at_startup', current_settings.get('launch_at_startup', False)))
            startup_minimized = bool(data.get('launch_minimized', current_settings.get('launch_minimized', False)))
            try:
                set_startup_enabled(startup_enabled, minimized=startup_minimized)
            except Exception as e:
                return jsonify({"error": f"Impossible de modifier le démarrage automatique: {e}"}), 500

        current_settings.update(data)
        current_settings['launch_at_startup'] = is_startup_enabled()
        current_settings['launch_minimized'] = is_startup_minimized() if current_settings['launch_at_startup'] else bool(data.get('launch_minimized', current_settings.get('launch_minimized', False)))
        save_settings(current_settings)


        new_spoolman_url = (current_settings.get('spoolman_url') or '').strip()
        if previous_spoolman_url and not new_spoolman_url:
            conn = get_db()
            try:
                conn.execute("DELETE FROM filament_assignments WHERE source_type='spoolman'")
                conn.execute("DELETE FROM spool_assignments")
                conn.commit()
                app_logger.info("[Settings] URL Spoolman supprimée — affectations de filament Spoolman nettoyées")
            finally:
                conn.close()

        return jsonify({"message": "Paramètres sauvegardés", "settings": current_settings}), 200

    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


from packaging import version

GITHUB_REPO = "stellio-app/stellio"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = "0.6.6"

def _fetch_expected_sha256(release_data, target_filename):
    try:
        assets = release_data.get('assets', [])
        dedicated = next((a for a in assets if a['name'] == f"{target_filename}.sha256"), None)
        summary = next((a for a in assets if a['name'].lower() in
                         ('sha256sums', 'sha256sums.txt', 'checksums.txt', 'checksums.sha256')), None)
        checksum_asset = dedicated or summary
        if not checksum_asset:
            return None
        res = requests.get(checksum_asset['browser_download_url'], timeout=10,
                            headers={'User-Agent': f'Stellio-App/{CURRENT_VERSION}'})
        if not res.ok:
            return None
        text = res.text.strip()
        if dedicated:
            first_token = text.split()[0] if text.split() else ''
            return first_token if re.fullmatch(r'[0-9a-fA-F]{64}', first_token) else None
        for line in text.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1].lstrip('*') == target_filename and re.fullmatch(r'[0-9a-fA-F]{64}', parts[0]):
                return parts[0]
        return None
    except Exception as e:
        app_logger.info(f"[UPDATE] Lecture checksum impossible: {e}")
        return None

SUPPORTED_UPDATE_LANGS = ('fr', 'en', 'de', 'es', 'it', 'pt', 'ja', 'zh')

def _extract_release_notes_for_lang(body, lang, fallback='en'):
    if not body:
        return body
    pattern = r"<!--{}-->\s*(.*?)(?=<!--\w{{2}}-->|\Z)"
    for candidate in (lang, fallback):
        match = re.search(pattern.format(re.escape(candidate)), body, re.DOTALL)
        if match:
            return match.group(1).strip()
    return body.strip()

def get_current_app_language():
    try:
        settings = load_settings() or {}
        lang = settings.get('lang', 'fr')
        return lang if lang in SUPPORTED_UPDATE_LANGS else 'fr'
    except Exception:
        return 'fr'

def get_current_version():
    return CURRENT_VERSION

def check_for_updates():
    try:
        app_logger.info("[UPDATE] 🔍 Vérification des mises à jour...")
        response = requests.get(GITHUB_API_URL, timeout=10, headers={
            'User-Agent': f'Stellio-App/{CURRENT_VERSION}'
        })

        if response.status_code != 200:
            app_logger.info(f"[UPDATE] ⚠️ Impossible de vérifier (HTTP {response.status_code})")
            return None

        release_data = response.json()
        latest_version = release_data.get('tag_name', '').replace('v', '')
        current_version = get_current_version()

        app_logger.info(f"[UPDATE] Version actuelle: {current_version} — GitHub: {latest_version}")

        if version.parse(latest_version) <= version.parse(current_version):
            app_logger.info("[UPDATE] ✅ Application à jour")
            return None

        download_url = None
        update_type = 'full'

        for asset in release_data.get('assets', []):
            if '-patch' in asset['name'] and asset['name'].endswith('.zip'):
                download_url = asset['browser_download_url']
                update_type = 'patch'
                app_logger.info(f"[UPDATE] 📦 Patch trouvé: {asset['name']}")
                break

        if not download_url:
            for asset in release_data.get('assets', []):
                if asset['name'].endswith('.exe'):
                    download_url = asset['browser_download_url']
                    update_type = 'full'
                    app_logger.info(f"[UPDATE] 📦 Installateur complet: {asset['name']}")
                    break

        if not download_url:
            app_logger.info("[UPDATE] ⚠️ Aucun asset téléchargeable trouvé (ni patch .zip, ni installeur .exe)")
            return None

        app_logger.info(f"[UPDATE] ✅ Nouvelle version disponible: {latest_version} (type: {update_type})")

        asset_filename = download_url.split("?")[0].rsplit("/", 1)[-1]
        expected_sha256 = _fetch_expected_sha256(release_data, asset_filename)
        if expected_sha256:
            app_logger.info(f"[UPDATE] 🔒 Checksum SHA256 trouvé pour {asset_filename}")
        else:
            app_logger.info(f"[UPDATE] ⚠️ Pas de checksum publié pour {asset_filename} — intégrité vérifiée par HTTPS uniquement")

        raw_body = release_data.get('body', '') or ''
        app_lang = get_current_app_language()
        localized_notes = _extract_release_notes_for_lang(raw_body, app_lang) if raw_body else 'Corrections de bugs et améliorations.'

        return {
            'version': latest_version,
            'current_version': current_version,
            'download_url': download_url,
            'update_type': update_type,
            'release_notes': localized_notes,
            'published_at': release_data.get('published_at', ''),
            'release_url': release_data.get('html_url', ''),
            'expected_sha256': expected_sha256
        }

    except requests.exceptions.SSLError as e:
        app_logger.info(f"[UPDATE] ⚠️ Vérification impossible (SSL/Antivirus) - Ignoré.")
        return None
    except Exception as e:
        app_logger.warning(f"[UPDATE] ⚠️ Impossible de vérifier les mises à jour: {str(e)[:80]}")
        return None

def _find_real_content_dir(base_dir):
    real_files = {'main.py', 'index.html', 'script.js', 'style.css', 'check_deps.py'}
    for root, dirs, files in os.walk(base_dir):
        entries = set(files) | set(dirs)
        matches = real_files.intersection(entries)
        if matches:
            app_logger.info(f"[UPDATE] ✅ Fichiers app trouvés dans: {root} ({matches})")
            return root
    app_logger.info(f"[UPDATE] ⚠️ Aucun fichier app reconnu dans le ZIP, on utilise la racine: {base_dir}")
    return base_dir


def install_update(installer_path):
    try:
        app_logger.info(f"[UPDATE] 🚀 Lancement de la mise à jour: {installer_path}")
        ext = os.path.splitext(installer_path)[1].lower()

        launcher_exe = os.environ.get('STELLIO_LAUNCHER_EXE')

        if sys.platform == 'win32':
            app_exe = launcher_exe
            app_dir = os.path.dirname(app_exe) if app_exe else os.path.dirname(os.path.abspath(sys.argv[0]))
            app_subdir = os.path.join(app_dir, 'app')
            os.makedirs(app_subdir, exist_ok=True)
            exe_name = os.path.basename(app_exe) if app_exe else 'Stellio.exe'

            app_logger.info(f"[UPDATE] 📂 app_dir: {app_dir}")
            app_logger.info(f"[UPDATE]  app_subdir: {app_subdir}")

            batch_path = os.path.join(tempfile.gettempdir(), 'stellio_update_relay.bat')
            log_path = os.path.join(tempfile.gettempdir(), 'stellio_update_relay.log')

            if ext == '.zip':
                extract_dir = os.path.join(tempfile.gettempdir(), 'stellio-patch')
                if os.path.exists(extract_dir):
                    shutil.rmtree(extract_dir, ignore_errors=True)
                os.makedirs(extract_dir, exist_ok=True)

                with zipfile.ZipFile(installer_path, 'r') as z:
                    app_logger.info(f"[UPDATE] 📦 Contenu du ZIP ({len(z.namelist())} entrées):")
                    for name in z.namelist()[:20]:
                        app_logger.info(f"  → {name}")
                    if len(z.namelist()) > 20:
                        app_logger.info(f"  ... et {len(z.namelist()) - 20} autres")
                    safe_extract_zip(z, extract_dir)

                real_content_dir = _find_real_content_dir(extract_dir)
                app_logger.info(f"[UPDATE] 📂 Répertoire source final: {real_content_dir}")
                app_logger.info(f"[UPDATE]  Contenu final: {os.listdir(real_content_dir)[:15]}")

                install_cmd = (
                    f'xcopy /s /y /e /i /q "{real_content_dir}\\*" "{app_subdir}\\" '
                    f'>> "{log_path}" 2>&1'
                )
                app_logger.info(f"[UPDATE] 🔧 Commande: {install_cmd}")

            elif ext == '.exe':
                install_cmd = f'"{installer_path}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART >> "{log_path}" 2>&1'
            elif ext == '.msi':
                install_cmd = f'msiexec /i "{installer_path}" /qn /norestart >> "{log_path}" 2>&1'
            else:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0
                subprocess.Popen(
                    [installer_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    startupinfo=si,
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                )
                app_logger.info("[UPDATE] ✅ Lancement direct, fermeture...")
                time.sleep(1)
                _cleanup_before_exit()
                os._exit(0)
                return

            relaunch_line = f'start /min "" "{app_exe}"' if app_exe else ''

            batch_content = (
                '@echo off\r\n'
                'setlocal\r\n'
                f'echo [Stellio Update] %date% %time% > "{log_path}"\r\n'
                'ping -n 4 127.0.0.1 >nul\r\n'
                f'taskkill /f /im "{exe_name}" >nul 2>&1\r\n'

                'ping -n 3 127.0.0.1 >nul\r\n'
                f'{install_cmd}\r\n'
                f'echo [Stellio Update] Code de sortie : %errorlevel% >> "{log_path}"\r\n'

                'ping -n 2 127.0.0.1 >nul\r\n'
                f'{relaunch_line}\r\n'
                'endlocal\r\n'
                'del "%~f0"\r\n'
            )

            with open(batch_path, 'w', encoding='utf-8') as f:
                f.write(batch_content)

            app_logger.info(f"[UPDATE] 📝 Script relais créé: {batch_path}")

            vbs_path = os.path.join(tempfile.gettempdir(), 'stellio_update_relay.vbs')
            vbs_content = (
                'Set WshShell = CreateObject("WScript.Shell")\r\n'
                f'WshShell.Run "cmd.exe /c ""{batch_path}""", 0, False\r\n'
            )
            with open(vbs_path, 'w', encoding='utf-8') as f:
                f.write(vbs_content)

            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0

            subprocess.Popen(
                ['wscript.exe', '//B', vbs_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                startupinfo=si,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
            app_logger.info("[UPDATE] ✅ Script relais lancé (invisible), fermeture...")
            time.sleep(1)
            _cleanup_before_exit()
            os._exit(0)

        else:


            app_dir = BASE_DIR

            if ext == '.zip':
                extract_dir = os.path.join(tempfile.gettempdir(), 'stellio-patch')
                if os.path.exists(extract_dir):
                    shutil.rmtree(extract_dir, ignore_errors=True)
                os.makedirs(extract_dir, exist_ok=True)

                with zipfile.ZipFile(installer_path, 'r') as z:
                    app_logger.info(f"[UPDATE] 📦 Contenu du ZIP ({len(z.namelist())} entrées)")
                    safe_extract_zip(z, extract_dir)

                real_content_dir = _find_real_content_dir(extract_dir)
                app_logger.info(f"[UPDATE] 📂 Copie de {real_content_dir} vers {app_dir}")


                copied, failed = 0, 0
                for root, dirs, files in os.walk(real_content_dir):
                    rel = os.path.relpath(root, real_content_dir)
                    dest_root = app_dir if rel == '.' else os.path.join(app_dir, rel)
                    os.makedirs(dest_root, exist_ok=True)
                    for fname in files:
                        try:
                            shutil.copy2(os.path.join(root, fname), os.path.join(dest_root, fname))
                            copied += 1
                        except Exception as e:
                            failed += 1
                            app_logger.warning(f"[UPDATE] ⚠️ Échec copie {fname}: {e}")

                app_logger.info(f"[UPDATE] ✅ {copied} fichier(s) copié(s), {failed} échec(s)")
                shutil.rmtree(extract_dir, ignore_errors=True)

            elif ext in ('.exe', '.msi'):
                app_logger.info("[UPDATE] ⚠️ Asset .exe/.msi ignoré (Linux/Pi attend un patch .zip)")
                return False
            else:
                app_logger.info(f"[UPDATE] ⚠️ Type d'asset non géré sur Linux/Pi: {ext}")
                return False

            app_logger.info("[UPDATE] 🔁 Redémarrage du service...")
            _cleanup_before_exit()


            if os.environ.get('INVOCATION_ID'):
                app_logger.info("[UPDATE] Service systemd détecté — arrêt (Restart=always s'occupe du redémarrage)")
                os._exit(0)
            else:
                app_logger.info("[UPDATE] Pas de systemd détecté — redémarrage direct du process")
                os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        app_logger.error(f"[UPDATE] ❌ Erreur installation: {e}")
        import traceback
        traceback.print_exc()
        return False

def download_update(download_url, progress_callback=None, expected_sha256=None):
    try:
        app_logger.info(f"[UPDATE] ⬇️ Téléchargement depuis: {download_url}")
        temp_dir = tempfile.gettempdir()
        url_path = download_url.split("?")[0]
        ext = os.path.splitext(url_path)[1] or '.exe'
        temp_file = os.path.join(temp_dir, f"Stellio-Update-{int(time.time())}{ext}")

        response = requests.get(download_url, stream=True, timeout=60, headers={
            'User-Agent': f'Stellio-App/{CURRENT_VERSION}'
        })
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        hasher = hashlib.sha256()

        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    hasher.update(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        progress = (downloaded / total_size) * 100
                        progress_callback(progress, downloaded, total_size)

        if expected_sha256:
            actual_sha256 = hasher.hexdigest()
            if actual_sha256.lower() != expected_sha256.lower():
                app_logger.error(
                    f"[UPDATE] ❌ Checksum invalide pour {temp_file} — "
                    f"attendu {expected_sha256}, obtenu {actual_sha256}. Fichier supprimé, mise à jour annulée."
                )
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
                return None
            app_logger.info("[UPDATE] 🔒 Checksum SHA256 vérifié avec succès")

        app_logger.info(f"[UPDATE] ✅ Téléchargement terminé: {temp_file}")
        return temp_file

    except Exception as e:
        app_logger.info(f"[UPDATE] ❌ Erreur téléchargement: {e}")
        return None

@app.route('/api/update/check', methods=['GET'])
@login_required
def api_check_update():
    update_info = check_for_updates()
    if update_info:
        return jsonify({
            'update_available': True,
            'version': update_info['version'],
            'current_version': update_info['current_version'],
            'update_type': update_info['update_type'],
            'release_notes': update_info['release_notes'],
            'download_url': update_info['download_url'],
            'published_at': update_info['published_at'],
            'release_url': update_info['release_url']
        }), 200
    else:
        return jsonify({
            'update_available': False,
            'current_version': get_current_version()
        }), 200

@app.route('/api/update/version', methods=['GET'])
def api_get_version():
    return jsonify({
        'version': get_current_version(),
        'app_name': 'Stellio'
    }), 200

@app.route('/api/update/download', methods=['POST'])
@login_required
def api_download_update():
    data = request.json
    download_url = data.get('download_url')
    if not download_url:
        return jsonify({'error': 'URL manquante'}), 400

    expected_sha256 = None
    current_update = check_for_updates()
    if current_update and current_update.get('download_url') == download_url:
        expected_sha256 = current_update.get('expected_sha256')
    else:
        app_logger.warning(f"[UPDATE] URL de téléchargement non reconnue comme asset de release courant: {download_url}")

    installer_path = download_update(download_url, expected_sha256=expected_sha256)
    if installer_path:
        return jsonify({
            'success': True,
            'installer_path': installer_path,
            'checksum_verified': bool(expected_sha256)
        }), 200
    else:
        return jsonify({'error': 'Échec du téléchargement (ou vérification d\'intégrité échouée)'}), 500

@app.route('/api/update/install', methods=['POST'])
@login_required
def api_install_update():
    data = request.json
    installer_path = data.get('installer_path')
    if not installer_path or not os.path.exists(installer_path):
        return jsonify({'error': 'Installateur introuvable'}), 404

    def do_install():
        time.sleep(1)
        install_update(installer_path)

    threading.Thread(target=do_install, daemon=True).start()
    return jsonify({'success': True, 'message': 'Installation en cours'}), 200


@app.route('/api/printers', methods=['GET'])
@login_required
def api_get_printers():
    conn = get_db()
    try:
        printers = conn.execute(
            "SELECT * FROM printers WHERE user_id = ?", (session['user_id'],)
        ).fetchall()
    finally:
        conn.close()
    result = []
    for p in printers:
        pc = parse_printer_config(p)
        if pc.get('api_key'):
            pc['api_key'] = '••••••••'
        result.append(pc)
    return jsonify(result)

@app.route('/api/printers', methods=['POST'])
@login_required
def api_add_printer():
    data = request.json
    name = data.get('name')
    ptype = data.get('type')
    ip = data.get('ip')
    api_key = data.get('api_key', '')
    raw_config = data.get('config', {})

    if ptype == 'bambu':
        code = raw_config.get('code', '')
        serial = raw_config.get('serial', '')
        api_key = code
        raw_config = {'code': code, 'serial': serial}
    elif ptype == 'elegoo_cc2':
        code = raw_config.get('code', '') or '123456'
        api_key = code
        raw_config = {'code': code}
    elif ptype == 'flashforge':
        code = raw_config.get('code', '')
        serial = raw_config.get('serial', '')
        api_key = code
        raw_config = {'code': code, 'serial': serial}

    config = json.dumps(raw_config)

    if not name or not ip or not ptype:
        return jsonify({"error": "Champs requis"}), 400

    conn = get_db()
    try:
        is_connected = printer_hub.connect_printer({
            'id': 0, 'type': ptype, 'ip': ip, 'api_key': api_key,
            'config': json.loads(config) if config else {}
        })

        conn.execute("""
            INSERT INTO printers (user_id, name, type, ip, api_key, config, is_connected)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session['user_id'], name, ptype, ip, encrypt_password(api_key) if api_key else None, config, is_connected))
        conn.commit()

        return jsonify({"message": "Imprimante ajoutée", "connected": is_connected}), 200

    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500
    finally:
        conn.close()

@app.route('/api/printers/<int:pid>/status', methods=['GET'])
@login_required
def api_printer_status(pid):
    conn = get_db()
    p = conn.execute(
        "SELECT * FROM printers WHERE id = ? AND user_id = ?",
        (pid, session['user_id'])
    ).fetchone()
    conn.close()

    if not p:
        return jsonify({"error": "Not found"}), 404

    printer = parse_printer_config(p)
    status = printer_hub.get_status(printer)

    conn = get_db()
    is_online = status.get('status') not in ['error', 'offline', 'timeout']

    now = datetime.datetime.now()
    last_poll_raw = p['last_status_poll_at'] if 'last_status_poll_at' in p.keys() else None
    if status.get('status') == 'printing' and last_poll_raw and p['type'] != 'klipper':
        try:
            last_poll = datetime.datetime.fromisoformat(last_poll_raw)
            delta_hours = (now - last_poll).total_seconds() / 3600
            if 0 < delta_hours < (10 / 60):
                conn.execute("UPDATE printers SET total_print_hours = total_print_hours + ? WHERE id = ?",
                             (delta_hours, pid))
        except Exception:
            pass

    for attempt in range(3):
        try:
            conn.execute("UPDATE printers SET is_connected = ?, last_status_poll_at = ? WHERE id = ?",
                         (is_online, now.isoformat(timespec='seconds'), pid))
            conn.commit()
            break
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower() and attempt < 2:
                time.sleep(0.3 * (attempt + 1))
                continue
            app_logger.warning(f"[PrinterStatus] Écriture ignorée (verrou DB persistant) pour l'imprimante {pid}: {e}")
            break
    conn.close()

    last_print = status.get('last_print') or {}
    if last_print.get('filename') and last_print.get('duration'):
        try:
            _autofill_actual_print_time(session['user_id'], pid, last_print['filename'],
                                         last_print['duration'], last_print.get('finished_at'))
        except Exception as e:
            app_logger.info(f"[PrinterStatus] autofill temps réel ignoré: {e}")

    return jsonify(status)

@app.route('/api/printers/<int:pid>/upload', methods=['POST'])
@login_required
def api_printer_upload(pid):
    data = request.json
    file_path = data.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Fichier non trouvé"}), 404
    if not _is_path_within_sources(file_path, session['user_id']):
        app_logger.warning(f"[SECURITY] Tentative d'upload imprimante hors sources: {file_path}")
        return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

    conn = get_db()
    try:
        p = conn.execute(
            "SELECT * FROM printers WHERE id = ? AND user_id = ?",
            (pid, session['user_id'])
        ).fetchone()
    finally:
        conn.close()

    if not p:
        return jsonify({"error": "Not found"}), 404

    printer = parse_printer_config(p)
    success = printer_hub.upload_file(printer, file_path)

    return jsonify({
        "success": success,
        "message": "Fichier envoyé" if success else "Échec de l'envoi"
    })

@app.route('/api/printers/<int:pid>/brand', methods=['PUT'])
@login_required
def api_printer_set_brand(pid):
    data = request.json or {}
    brand = (data.get('brand') or '').strip()[:50]
    conn = get_db()
    try:
        p = conn.execute(
            "SELECT id FROM printers WHERE id=? AND user_id=?", (pid, session['user_id'])
        ).fetchone()
        if not p:
            return jsonify({"error": "Not found"}), 404
        conn.execute(
            "UPDATE printers SET brand=? WHERE id=? AND user_id=?",
            (brand, pid, session['user_id'])
        )
        conn.commit()
        return jsonify({"message": "Marque enregistrée", "brand": brand}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500
    finally:
        conn.close()

@app.route('/api/printers/<int:pid>/power', methods=['PUT'])
@login_required
def api_printer_set_power(pid):
    data = request.json or {}
    try:
        power_w = int(round(float(data.get('power_w'))))
    except (TypeError, ValueError):
        return jsonify({"error": "power_w invalide"}), 400
    if power_w < 0 or power_w > 10000:
        return jsonify({"error": "power_w hors limites"}), 400
    conn = get_db()
    try:
        p = conn.execute(
            "SELECT id FROM printers WHERE id=? AND user_id=?", (pid, session['user_id'])
        ).fetchone()
        if not p:
            return jsonify({"error": "Not found"}), 404
        conn.execute(
            "UPDATE printers SET power_w=? WHERE id=? AND user_id=?",
            (power_w, pid, session['user_id'])
        )
        conn.commit()
        return jsonify({"message": "Puissance enregistrée", "power_w": power_w}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500
    finally:
        conn.close()

@app.route('/api/printers/<int:pid>/camera/stream')
@login_required
def api_printer_camera_stream(pid):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM printers WHERE id=? AND user_id=?", (pid, session['user_id'])
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return jsonify({"error": "Not found"}), 404

    row = parse_printer_config(row)
    if row.get('type') != 'bambu':
        return jsonify({"error": "Flux disponible uniquement pour Bambu Lab"}), 400

    config = row.get('config') or {}
    access_code = config.get('code') or row.get('api_key') or ''
    ip = row.get('ip')
    if not access_code or not ip:
        return jsonify({"error": "IP ou code d'accès manquant pour cette imprimante"}), 400

    model = (config.get('model') or 'A1').upper()
    if model in BAMBU_RTSP_PORT322_MODELS:
        if not FFMPEG_TOOL:
            return jsonify({"error": "ffmpeg est requis pour le flux caméra des modèles X1/X2/H2 (RTSPS) — placez ffmpeg.exe dans le dossier bin/ de l'app, à côté de UnRAR.exe"}), 500
        return Response(
            _generate_bambu_rtsp_mjpeg_stream(ip, access_code),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )

    return Response(
        _generate_bambu_mjpeg_stream(ip, access_code),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/printers/<int:pid>', methods=['PUT'])
@login_required
def api_edit_printer(pid):
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT * FROM printers WHERE id = ? AND user_id = ?", (pid, session['user_id'])
        ).fetchone()
        if not existing:
            return jsonify({"error": "Imprimante introuvable"}), 404

        data = request.json or {}
        name = data.get('name')
        ptype = data.get('type')
        ip = data.get('ip')
        raw_config = data.get('config', {}) or {}


        has_new_api_key = 'api_key' in data and data.get('api_key')

        if not name or not ip or not ptype:
            return jsonify({"error": "Champs requis"}), 400

        if ptype == 'bambu':
            code = raw_config.get('code', '')
            serial = raw_config.get('serial', '')
            raw_config = {'code': code, 'serial': serial}
            if code:
                has_new_api_key = True
                data['api_key'] = code
        elif ptype == 'elegoo_cc2':
            code = raw_config.get('code', '') or '123456'
            raw_config = {'code': code}
            has_new_api_key = True
            data['api_key'] = code
        elif ptype == 'flashforge':
            code = raw_config.get('code', '')
            serial = raw_config.get('serial', '')
            raw_config = {'code': code, 'serial': serial}
            if code:
                has_new_api_key = True
                data['api_key'] = code

        config = json.dumps(raw_config)
        api_key = data.get('api_key', '') if has_new_api_key else decrypt_account_secret(existing['api_key']) if existing['api_key'] else ''


        _stop_bambu_connection(pid)
        _stop_elegoo_sdcp_connection(pid)
        _stop_elegoo_cc2_connection(pid)
        _stop_creality_connection(pid)
        _stop_flashforge_connection(pid)

        is_connected = printer_hub.connect_printer({
            'id': pid, 'type': ptype, 'ip': ip, 'api_key': api_key,
            'config': json.loads(config) if config else {}
        })

        conn.execute("""
            UPDATE printers SET name = ?, type = ?, ip = ?, api_key = ?, config = ?, is_connected = ?
            WHERE id = ? AND user_id = ?
        """, (name, ptype, ip, encrypt_password(api_key) if api_key else None, config, is_connected, pid, session['user_id']))
        conn.commit()

        return jsonify({"message": "Imprimante mise à jour", "connected": is_connected}), 200

    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500
    finally:
        conn.close()

@app.route('/api/printers/<int:pid>', methods=['DELETE'])
@login_required
def api_delete_printer(pid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM printers WHERE id = ? AND user_id = ?",
                     (pid, session['user_id']))
        conn.commit()
        _stop_bambu_connection(pid)
        _stop_elegoo_sdcp_connection(pid)
        _stop_elegoo_cc2_connection(pid)
        _stop_creality_connection(pid)
        _stop_flashforge_connection(pid)
        return jsonify({"message": "Imprimante supprimée"}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500
    finally:
        conn.close()

@app.route('/api/printers/<int:pid>/camera', methods=['GET'])
@login_required
def api_printer_camera(pid):
    conn = get_db()
    try:
        p = conn.execute(
            "SELECT * FROM printers WHERE id = ? AND user_id = ?",
            (pid, session['user_id'])
        ).fetchone()
    finally:
        conn.close()

    if not p:
        return jsonify({"available": False}), 404

    printer = parse_printer_config(p)
    ptype = printer['type']
    ip = printer['ip']

    camera_info = {"available": False, "stream_url": None, "snapshot_url": None, "name": "Camera"}

    try:
        if ptype == 'klipper':
            port = printer.get('config', {}).get('port', '7125')
            try:
                r = requests.get(f"http://{ip}:{port}/server/webcams/list", timeout=3)
                if r.status_code == 200:
                    webcams = r.json().get('result', {}).get('webcams', [])
                    if webcams:
                        cam = webcams[0]
                        stream_url = cam.get('stream_url', '')
                        snapshot_url = cam.get('snapshot_url', '')

                        if stream_url and stream_url.startswith('/'):
                            webcam_ports = [80, 4408, 8080, 8181]
                            for wport in webcam_ports:
                                test_url = f"http://{ip}:{wport}{stream_url}"
                                try:
                                    test_r = requests.get(test_url, timeout=2, stream=True)
                                    if test_r.status_code == 200:
                                        stream_url = test_url
                                        break
                                except:
                                    continue
                        else:
                            stream_url = f"http://{ip}:80{stream_url}"

                        if snapshot_url and snapshot_url.startswith('/'):
                            snapshot_url = f"http://{ip}:80{snapshot_url}"

                        camera_info.update({
                            "available": True,
                            "stream_url": stream_url,
                            "snapshot_url": snapshot_url,
                            "name": cam.get('name', 'Klipper Camera')
                        })
            except Exception as e:
                pass

        elif ptype == 'octoprint':
            headers = {'X-Api-Key': printer.get('api_key', '')}
            try:
                r = requests.get(f"http://{ip}/api/settings", headers=headers, timeout=3)
                if r.status_code == 200:
                    settings = r.json()
                    webcam = settings.get('webcam', {})
                    if webcam.get('streamUrl'):
                        stream_url = webcam.get('streamUrl')
                        if stream_url.startswith('/'):
                            stream_url = f"http://{ip}{stream_url}"

                        camera_info.update({
                            "available": True,
                            "stream_url": stream_url,
                            "snapshot_url": webcam.get('snapshotUrl', ''),
                            "name": "OctoPrint Camera"
                        })
            except Exception as e:
                pass

        elif ptype == 'bambu':
            config = printer.get('config', {}) or {}
            access_code = config.get('code') or printer.get('api_key') or ''
            if access_code:
                camera_info.update({
                    "available": True,
                    "stream_url": f"{request.host_url.rstrip('/')}/api/printers/{pid}/camera/stream",
                    "snapshot_url": None,
                    "name": "Bambu Lab Camera"
                })

        elif ptype == 'elegoo_sdcp':
            conn = _ensure_elegoo_sdcp_connection(printer)
            if conn:
                video_url, ack = conn.request_video()
                if ack == 0 and video_url:
                    if not video_url.startswith(('http://', 'https://')):
                        video_url = f"http://{video_url}"
                    camera_info.update({
                        "available": True,
                        "stream_url": video_url,
                        "snapshot_url": None,
                        "name": "Elegoo Camera"
                    })
                elif ack == 2:
                    app_logger.info(f"[Elegoo SDCP] Pas de caméra sur cette imprimante (printer #{pid})")
                elif ack is None:
                    app_logger.info(f"[Elegoo SDCP] Pas de réponse Cmd 386 (printer #{pid}), imprimante hors ligne ?")

    except Exception as e:
        pass

    return jsonify(camera_info)


def _fetch_moonraker_total_print_hours(printer):
    try:
        port = printer.get('config', {}).get('port', '7125')
        r = requests.get(f"http://{printer['ip']}:{port}/server/history/totals", timeout=3)
        if r.status_code == 200:
            totals = r.json().get('result', {}).get('job_totals', {})
            total_seconds = totals.get('total_print_time')
            if total_seconds is not None:
                return round(float(total_seconds) / 3600, 2)
    except Exception:
        pass
    return None


def _serialize_maintenance_task(task, printer_total_hours):
    hours_since = None
    days_since = None
    due = False
    progress_ratio = None

    if task['interval_hours']:
        hours_since = round(printer_total_hours - (task['hours_at_last_reset'] or 0), 1)
        ratio = hours_since / task['interval_hours'] if task['interval_hours'] else 0
        progress_ratio = ratio if progress_ratio is None else max(progress_ratio, ratio)
        if hours_since >= task['interval_hours']:
            due = True

    if task['interval_days']:
        try:
            last_reset = datetime.datetime.fromisoformat(task['last_reset_at'])
            days_since = round((datetime.datetime.now() - last_reset).total_seconds() / 86400, 1)
            ratio = days_since / task['interval_days'] if task['interval_days'] else 0
            progress_ratio = ratio if progress_ratio is None else max(progress_ratio, ratio)
            if days_since >= task['interval_days']:
                due = True
        except Exception:
            pass

    return {
        "id": task['id'], "printer_id": task['printer_id'], "name": task['name'],
        "interval_hours": task['interval_hours'], "interval_days": task['interval_days'],
        "hours_since_reset": hours_since, "days_since_reset": days_since,
        "progress_ratio": round(min(progress_ratio, 2.0), 2) if progress_ratio is not None else None,
        "due": due, "last_reset_at": task['last_reset_at'],
    }


@app.route('/api/printers/<int:pid>/maintenance', methods=['GET'])
@login_required
def api_printer_maintenance_list(pid):
    conn = get_db()
    printer_row = conn.execute(
        "SELECT * FROM printers WHERE id=? AND user_id=?",
        (pid, session['user_id'])
    ).fetchone()
    if not printer_row:
        conn.close()
        return jsonify({"error": "Imprimante introuvable"}), 404

    total_hours = printer_row['total_print_hours'] or 0
    hours_source = 'estimated'

    if printer_row['type'] == 'klipper':
        live_hours = _fetch_moonraker_total_print_hours(parse_printer_config(printer_row))
        if live_hours is not None:
            total_hours = live_hours
            hours_source = 'moonraker'
            conn.execute("UPDATE printers SET total_print_hours=? WHERE id=?", (live_hours, pid))
            conn.commit()

    tasks = conn.execute(
        "SELECT * FROM printer_maintenance_tasks WHERE printer_id=? AND user_id=? ORDER BY created_at ASC",
        (pid, session['user_id'])
    ).fetchall()
    conn.close()

    return jsonify({
        "total_print_hours": round(total_hours, 1),
        "hours_source": hours_source,
        "tasks": [_serialize_maintenance_task(t, total_hours) for t in tasks]
    }), 200


@app.route('/api/printers/<int:pid>/maintenance', methods=['POST'])
@login_required
def api_printer_maintenance_create(pid):
    data = request.json or {}
    name = (data.get('name') or '').strip()[:100]
    if not name:
        return jsonify({"error": "Nom de la tâche requis"}), 400

    interval_hours = data.get('interval_hours')
    interval_days = data.get('interval_days')
    try:
        interval_hours = float(interval_hours) if interval_hours not in (None, '') else None
        interval_days = float(interval_days) if interval_days not in (None, '') else None
    except (TypeError, ValueError):
        return jsonify({"error": "Intervalle invalide"}), 400
    if not interval_hours and not interval_days:
        return jsonify({"error": "Renseigne au moins un intervalle (heures ou jours)"}), 400

    conn = get_db()
    printer = conn.execute(
        "SELECT id, total_print_hours FROM printers WHERE id=? AND user_id=?",
        (pid, session['user_id'])
    ).fetchone()
    if not printer:
        conn.close()
        return jsonify({"error": "Imprimante introuvable"}), 404

    conn.execute(
        """INSERT INTO printer_maintenance_tasks
           (printer_id, user_id, name, interval_hours, interval_days, hours_at_last_reset, last_reset_at)
           VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
        (pid, session['user_id'], name, interval_hours, interval_days, printer['total_print_hours'] or 0)
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True}), 201


@app.route('/api/printers/maintenance/<int:task_id>/reset', methods=['POST'])
@login_required
def api_printer_maintenance_reset(task_id):
    conn = get_db()
    task = conn.execute(
        "SELECT * FROM printer_maintenance_tasks WHERE id=? AND user_id=?",
        (task_id, session['user_id'])
    ).fetchone()
    if not task:
        conn.close()
        return jsonify({"error": "Tâche introuvable"}), 404

    printer = conn.execute("SELECT total_print_hours FROM printers WHERE id=?", (task['printer_id'],)).fetchone()
    conn.execute(
        "UPDATE printer_maintenance_tasks SET hours_at_last_reset=?, last_reset_at=CURRENT_TIMESTAMP WHERE id=?",
        ((printer['total_print_hours'] if printer else 0) or 0, task_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True}), 200


@app.route('/api/printers/maintenance/<int:task_id>', methods=['PUT'])
@login_required
def api_printer_maintenance_update(task_id):
    data = request.json or {}
    conn = get_db()
    task = conn.execute(
        "SELECT * FROM printer_maintenance_tasks WHERE id=? AND user_id=?",
        (task_id, session['user_id'])
    ).fetchone()
    if not task:
        conn.close()
        return jsonify({"error": "Tâche introuvable"}), 404

    name = (data.get('name') or task['name']).strip()[:100]
    interval_hours = data.get('interval_hours', task['interval_hours'])
    interval_days = data.get('interval_days', task['interval_days'])
    try:
        interval_hours = float(interval_hours) if interval_hours not in (None, '') else None
        interval_days = float(interval_days) if interval_days not in (None, '') else None
    except (TypeError, ValueError):
        conn.close()
        return jsonify({"error": "Intervalle invalide"}), 400
    if not interval_hours and not interval_days:
        conn.close()
        return jsonify({"error": "Renseigne au moins un intervalle (heures ou jours)"}), 400

    conn.execute(
        "UPDATE printer_maintenance_tasks SET name=?, interval_hours=?, interval_days=? WHERE id=?",
        (name, interval_hours, interval_days, task_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True}), 200


@app.route('/api/printers/maintenance/<int:task_id>', methods=['DELETE'])
@login_required
def api_printer_maintenance_delete(task_id):
    conn = get_db()
    try:
        cur = conn.execute(
            "DELETE FROM printer_maintenance_tasks WHERE id=? AND user_id=?",
            (task_id, session['user_id'])
        )
        conn.commit()
        found = cur.rowcount > 0
    finally:
        conn.close()
    if not found:
        return jsonify({"error": "Tâche introuvable"}), 404
    return jsonify({"success": True}), 200


@app.route('/api/printers/<int:pid>/hours/add', methods=['POST'])
@login_required
def api_printer_add_hours(pid):
    data = request.json or {}
    try:
        hours = float(data.get('hours'))
    except (TypeError, ValueError):
        return jsonify({"error": "Nombre d'heures invalide"}), 400
    if hours <= 0 or hours > 1000:
        return jsonify({"error": "Valeur d'heures hors limites (0-1000)"}), 400

    conn = get_db()
    try:
        cur = conn.execute(
            "UPDATE printers SET total_print_hours = COALESCE(total_print_hours, 0) + ? WHERE id=? AND user_id=?",
            (hours, pid, session['user_id'])
        )
        conn.commit()
        found = cur.rowcount > 0
    finally:
        conn.close()
    if not found:
        return jsonify({"error": "Imprimante introuvable"}), 404
    return jsonify({"success": True}), 200


@app.route('/api/printers/maintenance/due', methods=['GET'])
@login_required
def api_printer_maintenance_due():
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT t.id, t.name, t.interval_hours, t.interval_days, t.hours_at_last_reset, t.last_reset_at,
                      p.id AS printer_id, p.name AS printer_name, p.type AS printer_type,
                      p.ip AS printer_ip, p.config AS printer_config, p.total_print_hours
               FROM printer_maintenance_tasks t
               JOIN printers p ON p.id = t.printer_id
               WHERE t.user_id = ?""",
            (session['user_id'],)
        ).fetchall()

        live_hours_by_printer = {}
        for r in rows:
            pid_ = r['printer_id']
            if r['printer_type'] == 'klipper' and pid_ not in live_hours_by_printer:
                fake_printer = {'ip': r['printer_ip'], 'config': json.loads(r['printer_config'] or '{}')}
                live_hours = _fetch_moonraker_total_print_hours(fake_printer)
                if live_hours is not None:
                    live_hours_by_printer[pid_] = live_hours
                    conn.execute("UPDATE printers SET total_print_hours=? WHERE id=?", (live_hours, pid_))
        conn.commit()
    finally:
        conn.close()

    due = []
    for r in rows:
        total_hours = live_hours_by_printer.get(r['printer_id'], r['total_print_hours'] or 0)
        is_due = False
        if r['interval_hours'] and (total_hours - (r['hours_at_last_reset'] or 0)) >= r['interval_hours']:
            is_due = True
        if r['interval_days']:
            try:
                last_reset = datetime.datetime.fromisoformat(r['last_reset_at'])
                if (datetime.datetime.now() - last_reset).total_seconds() / 86400 >= r['interval_days']:
                    is_due = True
            except Exception:
                pass
        if is_due:
            due.append({"task_id": r['id'], "task_name": r['name'], "printer_id": r['printer_id'], "printer_name": r['printer_name']})

    return jsonify({"due": due}), 200


def _cleanup_before_exit():
    try:
        save_cache_on_exit()
    except Exception:
        pass
    try:
        _release_persistent_renderer()
    except Exception:
        pass
    try:
        stop_remote_access()
    except Exception:
        pass
    global _ollama_process
    if _ollama_process and _ollama_process.poll() is None:
        try:
            _ollama_process.terminate()
            try:
                _ollama_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _ollama_process.kill()
        except Exception:
            pass


_app_window = None

@app.route('/api/app/quit', methods=['POST'])
@login_required
def api_quit_app():
    def do_quit():
        time.sleep(0.5)
        app_logger.info("[APP] 🛑 Fermeture demandée par l'utilisateur")
        _cleanup_before_exit()
        os._exit(0)

    threading.Thread(target=do_quit, daemon=True).start()
    return jsonify({"success": True, "message": "Fermeture en cours"}), 200

@app.route('/api/app/save-cache', methods=['POST'])
@login_required
def api_save_cache():
    try:
        save_cache_on_exit()
        return jsonify({"success": True, "message": "Cache sauvegardé"}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


def get_ollama_base_url():
    settings = load_settings() or {}
    url = (settings.get('ollama_url') or 'http://localhost:11434').strip().rstrip('/')
    return url

def get_user_lang() -> str:
    try:
        settings = load_settings() or {}
        return (settings.get('lang') or 'fr').strip().lower()[:2]
    except Exception:
        return 'fr'

LANG_NAMES = {
    'fr': 'français', 'en': 'English', 'de': 'Deutsch',
    'es': 'español',  'it': 'italiano', 'pt': 'português',
    'nl': 'Nederlands', 'pl': 'polski', 'ru': 'русский',
}

def _ollama_is_reachable(base_url: str, timeout: int = 4) -> bool:
    try:
        return requests.get(f"{base_url}/api/tags", timeout=timeout).ok
    except Exception:
        return False

def _call_ollama(base_url: str, model: str, prompt: str, system: str = "",
                 temperature: float = 0.2, num_predict: int = 200,
                 timeout: int = 300, images: list = None) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False,
               "think": False,
               "options": {"temperature": temperature, "num_predict": num_predict}}
    if system:
        payload["system"] = system
    if images:
        payload["images"] = images
    r = requests.post(f"{base_url}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    text = (data.get('response') or '').strip()
    if not text and (data.get('thinking') or '').strip():
        app_logger.info("[AI] Réponse vide (budget consumé en thinking), nouvel essai avec num_predict élargi")
        payload["options"]["num_predict"] = max(num_predict * 4, 1024)
        r = requests.post(f"{base_url}/api/generate", json=payload, timeout=timeout)
        r.raise_for_status()
        text = (r.json().get('response') or '').strip()
    return text

class AIDisabledError(RuntimeError):
    pass

def is_ai_enabled() -> bool:
    settings = load_settings() or {}
    return settings.get('ai_enabled') is True

OLLAMA_TIMEOUT_SECONDS = 300

def _call_ai(prompt: str, system: str = "",
             num_predict: int = 200, temperature: float = 0.2, images: list = None) -> tuple:
    if not is_ai_enabled():
        raise AIDisabledError("Les fonctionnalités IA sont désactivées dans les Paramètres.")

    settings = load_settings() or {}
    base_url = get_ollama_base_url()
    model    = settings.get('ollama_model') or 'qwen3.5:4b'

    if not _ollama_is_reachable(base_url):
        app_logger.info(f"[AI] ❌ Ollama injoignable ({base_url})")
        raise RuntimeError(
            f"Ollama n'est pas accessible à l'adresse {base_url}. Vérifiez qu'Ollama est bien "
            f"lancé sur cette machine (ou changez l'adresse du serveur dans Paramètres > IA)."
        )

    try:
        text = _call_ollama(base_url, model, prompt, system=system, temperature=temperature,
                            num_predict=num_predict, timeout=OLLAMA_TIMEOUT_SECONDS, images=images)
        if text:
            app_logger.info(f"[AI] ✅ Ollama ({model})")
            return text, 'ollama'
        app_logger.warning("[AI] ⚠️ Ollama a répondu sans contenu exploitable")
        raise RuntimeError("Ollama a répondu, mais sans contenu exploitable. Réessayez.")
    except requests.exceptions.Timeout:
        app_logger.warning(f"[AI] ⚠️ Ollama timeout après {OLLAMA_TIMEOUT_SECONDS}s (modèle: {model})")
        raise RuntimeError(
            f"Ollama met trop de temps à répondre (plus de {OLLAMA_TIMEOUT_SECONDS // 60} minutes). "
            f"Le modèle « {model} » est peut-être trop lourd pour cette machine (CPU seul, sans carte "
            f"graphique dédiée), ou une autre génération est déjà en cours. Essayez un modèle plus "
            f"léger dans Paramètres > IA, ou réessayez dans quelques instants."
        )
    except requests.exceptions.RequestException as e:
        if images:
            app_logger.warning(f"[AI] ⚠️ Échec avec image (modèle probablement non multimodal): {e} — nouvelle tentative en texte seul")
            try:
                text = _call_ollama(base_url, model, prompt, system=system, temperature=temperature,
                                    num_predict=num_predict, timeout=OLLAMA_TIMEOUT_SECONDS, images=None)
                if text:
                    app_logger.info(f"[AI] ✅ Ollama ({model}, sans image)")
                    return text, 'ollama_no_vision'
            except Exception:
                pass
        app_logger.error(f"[AI] ❌ Ollama: {e}")
        raise RuntimeError(f"Erreur de connexion à Ollama : {e}")

@app.route('/api/ollama/models', methods=['GET'])
@login_required
def api_ollama_models():
    base_url = get_ollama_base_url()
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=8)
        r.raise_for_status()
        models = [m.get('name', '') for m in r.json().get('models', []) if m.get('name')]
        return jsonify({"models": models}), 200
    except requests.exceptions.ConnectionError:
        return jsonify({"error_code": "ollama_unreachable", "error_params": {"url": base_url},
                         "error": f"Impossible de joindre Ollama sur {base_url}."}), 502
    except requests.exceptions.Timeout:
        return jsonify({"error_code": "ollama_timeout",
                         "error": "Ollama ne répond pas (timeout)."}), 504
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error_code": "internal_error",
                         "error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

def _detect_hardware():
    info = {
        'cpu_cores': os.cpu_count() or 4,
        'ram_gb': None,
        'gpu_name': None,
        'vram_gb': None,
    }
    try:
        import psutil
        info['ram_gb'] = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except Exception as e:
        app_logger.info(f"[HW] RAM non détectée (psutil manquant ?): {e}")

    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            first_line = result.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in first_line.split(',')]
            if len(parts) >= 2:
                info['gpu_name'] = parts[0]
                info['vram_gb'] = round(float(parts[1]) / 1024, 1)
    except FileNotFoundError:
        pass
    except Exception as e:
        app_logger.info(f"[HW] Détection GPU NVIDIA échouée: {e}")

    if not info['gpu_name'] and sys.platform == 'win32':
        try:
            ps_cmd = (
                "Get-CimInstance Win32_VideoController | "
                "Select-Object Name, AdapterRAM | ConvertTo-Json -Compress"
            )
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_cmd],
                capture_output=True, text=True, timeout=8
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip())
                candidates = data if isinstance(data, list) else [data]
                dedicated = [
                    c for c in candidates
                    if c.get('Name') and (
                        'nvidia' in c['Name'].lower()
                        or ('radeon' in c['Name'].lower() and 'graphics' not in c['Name'].lower())
                    )
                ]
                if dedicated:
                    best = dedicated[0]
                    info['gpu_name'] = best['Name'].strip()
                    ram_bytes = best.get('AdapterRAM') or 0
                    vram_gb = ram_bytes / (1024 ** 3)
                    if 0 < vram_gb <= 32:
                        info['vram_gb'] = round(vram_gb, 1)
                    else:
                        info['vram_gb'] = 4.0
                        app_logger.info(
                            f"[HW] VRAM WMI non fiable pour {info['gpu_name']} "
                            f"(valeur brute {ram_bytes}) → estimation prudente à 4 Go"
                        )
                    app_logger.info(f"[HW] GPU détectée via repli WMI: {info['gpu_name']} (~{info['vram_gb']} Go)")
        except Exception as e:
            app_logger.info(f"[HW] Repli WMI GPU échoué: {e}")

    return info

OLLAMA_MODEL_TIERS = [
    {'min_vram_gb': 16, 'model': 'gemma3:27b',  'vision': True,
     'label_key': 'ollama.rec_gpu_high'},
    {'min_vram_gb': 8,  'model': 'gemma4:12b',  'vision': False,
     'label_key': 'ollama.rec_gpu_good'},
    {'min_vram_gb': 4,  'model': 'llama3.1:8b', 'vision': False,
     'label_key': 'ollama.rec_gpu_modest'},
    {'min_vram_gb': 0, 'min_ram_gb': 16, 'model': 'qwen3.5:4b', 'vision': True,
     'label_key': 'ollama.rec_cpu_ok'},
    {'min_vram_gb': 0, 'min_ram_gb': 0,  'model': 'smollm3:3b', 'vision': False,
     'label_key': 'ollama.rec_cpu_low'},
]

def _recommend_ollama_model(hw):
    vram = hw.get('vram_gb') or 0
    ram = hw.get('ram_gb') if hw.get('ram_gb') is not None else 8

    for tier in OLLAMA_MODEL_TIERS:
        if vram >= tier['min_vram_gb'] and ram >= tier.get('min_ram_gb', 0):
            return {
                'model': tier['model'],
                'vision': tier['vision'],
                'label_key': tier['label_key'],
                'pull_command': f"ollama pull {tier['model']}"
            }
    return {
        'model': 'smollm3:3b', 'vision': False,
        'label_key': 'ollama.rec_cpu_low',
        'pull_command': 'ollama pull smollm3:3b'
    }

@app.route('/api/ollama/recommend-model', methods=['GET'])
@login_required
def api_ollama_recommend_model():
    hw = _detect_hardware()
    rec = _recommend_ollama_model(hw)

    installed = []
    try:
        base_url = get_ollama_base_url()
        r = requests.get(f"{base_url}/api/tags", timeout=5)
        if r.ok:
            installed = [m.get('name', '') for m in r.json().get('models', []) if m.get('name')]
    except Exception:
        pass

    rec['already_installed'] = any(
        installed_name.split(':')[0] == rec['model'].split(':')[0] for installed_name in installed
    )

    return jsonify({'hardware': hw, 'recommendation': rec}), 200



MIN_SAMPLES_FOR_CORRECTION = 3
CORRECTION_FACTOR_BOUNDS = (0.5, 2.0)

def _get_print_time_correction_factor(user_id, printer_id=None, slicer_profile_id=None):
    conn = get_db()
    try:
        def _fetch(where_extra, params_extra):
            query = """SELECT estimated_seconds, actual_seconds FROM print_history
                       WHERE user_id=? AND estimated_seconds IS NOT NULL AND estimated_seconds > 0
                       AND actual_seconds IS NOT NULL AND actual_seconds > 0""" + where_extra
            return conn.execute(query, (user_id, *params_extra)).fetchall()

        rows, scope = [], 'global'
        if printer_id and slicer_profile_id:
            rows = _fetch(" AND printer_id=? AND slicer_profile_id=?", (printer_id, slicer_profile_id))
            scope = 'printer+profile'
        if len(rows) < MIN_SAMPLES_FOR_CORRECTION and printer_id:
            rows = _fetch(" AND printer_id=?", (printer_id,))
            scope = 'printer'
        if len(rows) < MIN_SAMPLES_FOR_CORRECTION:
            rows = _fetch("", ())
            scope = 'global'
    finally:
        conn.close()

    if len(rows) < MIN_SAMPLES_FOR_CORRECTION:
        return {'factor': 1.0, 'confidence': 'low', 'sample_size': len(rows), 'scope': scope}

    ratios = sorted(r['actual_seconds'] / r['estimated_seconds'] for r in rows)
    median = ratios[len(ratios) // 2] if len(ratios) % 2 == 1 else \
        (ratios[len(ratios) // 2 - 1] + ratios[len(ratios) // 2]) / 2
    factor = max(CORRECTION_FACTOR_BOUNDS[0], min(CORRECTION_FACTOR_BOUNDS[1], median))
    confidence = 'high' if len(rows) >= 10 else 'medium'
    return {'factor': round(factor, 3), 'confidence': confidence, 'sample_size': len(rows), 'scope': scope}

def _autofill_actual_print_time(user_id, printer_id, file_name, duration_seconds, finished_at=None):
    if not duration_seconds or duration_seconds < 60 or not file_name:
        return
    conn = get_db()
    try:
        row = conn.execute(
            """SELECT id FROM print_history
               WHERE user_id=? AND file_name=? AND actual_seconds IS NULL
               AND sent_at >= datetime('now', '-72 hours')
               ORDER BY sent_at DESC LIMIT 1""",
            (user_id, file_name)
        ).fetchone()
        if not row:
            return
        conn.execute(
            """UPDATE print_history SET actual_seconds=?, printer_id=COALESCE(printer_id, ?),
               time_recorded_at=CURRENT_TIMESTAMP WHERE id=?""",
            (duration_seconds, printer_id, row['id'])
        )
        conn.commit()
    except Exception as e:
        app_logger.info(f"[AI][PrintTime] autofill ignoré: {e}")
    finally:
        conn.close()

@app.route('/api/ai/predict-print-time', methods=['POST'])
@login_required
def api_ai_predict_print_time():
    data = request.json or {}
    file_path = (data.get('path') or '').strip()
    printer_id = data.get('printer_id')
    slicer_profile_id = data.get('slicer_profile_id')
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400

    estimated_seconds = _get_cached_slice_estimate_seconds(file_path.replace('\\', '/'))
    if estimated_seconds is None:
        return jsonify({"status": "pending",
                         "message": "Estimation du slicer pas encore disponible pour ce fichier."}), 202

    correction = _get_print_time_correction_factor(session['user_id'], printer_id, slicer_profile_id)
    corrected_seconds = int(estimated_seconds * correction['factor'])

    def _fmt(seconds):
        h, m = seconds // 3600, (seconds % 3600) // 60
        return f"{h}h {m}min" if h > 0 else f"{m}min"

    return jsonify({
        "status": "done",
        "estimated_seconds": int(estimated_seconds),
        "estimated_formatted": _fmt(int(estimated_seconds)),
        "corrected_seconds": corrected_seconds,
        "corrected_formatted": _fmt(corrected_seconds),
        "correction_factor": correction['factor'],
        "confidence": correction['confidence'],
        "sample_size": correction['sample_size'],
        "scope": correction['scope'],
    }), 200


@app.route('/api/ollama/auto-tag', methods=['POST'])
@login_required
def api_ollama_auto_tag():
    data          = request.json or {}
    filename      = (data.get('filename') or '').strip()
    existing_tags = data.get('existing_tags') or []

    if not filename:
        return jsonify({"error": "Nom de fichier requis"}), 400

    lang      = get_user_lang()
    lang_name = LANG_NAMES.get(lang, lang)
    existing_str = ', '.join(existing_tags[:15]) if existing_tags else 'none'

    prompt = (
        f"3D file: \"{filename}\"\n"
        f"Existing tags: {existing_str}\n"
        f"Give 3 to 5 short tags separated by commas. "
        f"Reply ONLY with the tags in {lang_name}, nothing else.\n"
        f"Example ({lang_name}): visserie, mecanique, support"
    )
    system = f"You generate short tags for a 3D printing file library. Always reply in {lang_name}."

    try:
        raw_text, source = _call_ai(prompt, system=system, num_predict=60)
        raw_tags = re.split(r'[, \n]', raw_text)
        tags = []
        for t in raw_tags:
            t = re.sub(r'^\d+[\.\)]\s*', '', t.strip().strip('.-•*').strip())
            if t and len(t) <= 30 and t.lower() not in [x.lower() for x in tags]:
                tags.append(t)
                if len(tags) >= 5:
                    break

        if not tags:
            return jsonify({"error": "L'IA n'a retourné aucun tag exploitable", "raw": raw_text}), 502

        return jsonify({"tags": tags, "source": source}), 200

    except AIDisabledError as e:
        return jsonify({"error": str(e), "ai_disabled": True}), 403
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        app_logger.error(f"[AutoTag] {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/ollama/explain-orientation', methods=['POST'])
@login_required
def api_ollama_explain_orientation():
    data = request.json or {}
    filename = (data.get('filename') or '').strip()
    suggestions = data.get('suggestions') or []
    if not suggestions:
        return jsonify({"error": "Aucune suggestion à expliquer"}), 400

    lang = get_user_lang()
    lang_name = LANG_NAMES.get(lang, lang)

    lines = []
    for i, s in enumerate(suggestions[:3]):
        lines.append(
            f"{i+1}. {s.get('key', '?')} — surplomb: {s.get('overhangPct', 0)}%, "
            f"contact plateau: {s.get('contactPct', 0)}%"
        )
    prompt = (
        f"3D print file: \"{filename}\"\n"
        f"Geometric analysis already computed locally (not by you) ranked these plate orientations, "
        f"best first:\n" + "\n".join(lines) +
        f"\nIn 2-3 short sentences, explain in {lang_name} why orientation #1 is the best choice here "
        f"(less overhang = less support material, more bed contact = better adhesion). "
        f"Reply ONLY with the explanation, in {lang_name}, no preamble."
    )
    system = f"You explain 3D printing orientation trade-offs simply, for a hobbyist. Always reply in {lang_name}."

    try:
        text, source = _call_ai(prompt, system=system, num_predict=180)
        return jsonify({"explanation": text, "source": source}), 200
    except AIDisabledError as e:
        return jsonify({"error": str(e), "ai_disabled": True}), 403
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        app_logger.error(f"[ExplainOrientation] {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/file-description', methods=['GET'])
@login_required
def api_get_file_description():
    file_path = request.args.get('path', '').replace('\\', '/')
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT description, generated_at FROM file_descriptions WHERE file_path=? AND user_id=?",
            (file_path, session['user_id'])
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return jsonify({"description": None}), 200
    return jsonify({"description": row["description"], "generated_at": row["generated_at"]}), 200


@app.route('/api/ollama/describe-file', methods=['POST'])
@login_required
def api_ollama_describe_file():
    data = request.json or {}
    file_path = (data.get('path') or '').replace('\\', '/')
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400

    filename = os.path.basename(file_path)
    user_id = session['user_id']

    conn = get_db()
    tag_rows = conn.execute(
        "SELECT t.name FROM file_tags ft JOIN tags t ON ft.tag_id = t.id WHERE ft.file_path=?",
        (file_path,)
    ).fetchall()
    conn.close()
    tags = [r["name"] for r in tag_rows]

    geometry_bits = []
    try:
        analysis = get_cached_3d_analysis(file_path)
        if analysis:
            dims = analysis.get('dimensions') or {}
            if dims:
                geometry_bits.append(f"dimensions {dims.get('x')}x{dims.get('y')}x{dims.get('z')} mm")
            if analysis.get('volume_cm3'):
                geometry_bits.append(f"volume {analysis['volume_cm3']} cm3")
    except Exception:
        pass

    lang = get_user_lang()
    lang_name = LANG_NAMES.get(lang, lang)

    prompt = (
        f"3D printable file named \"{filename}\".\n"
        f"Tags: {', '.join(tags) if tags else 'none'}\n"
        f"Geometry: {', '.join(geometry_bits) if geometry_bits else 'unknown'}\n"
        f"Write a short, useful 1-2 sentence description of what this object likely is and what "
        f"it could be used for. Be concrete, avoid generic filler. Reply ONLY with the description "
        f"in {lang_name}, no preamble."
    )
    system = f"You write short, concrete descriptions for a 3D printing file library. Always reply in {lang_name}."

    try:
        description, source = _call_ai(prompt, system=system, num_predict=120)
        description = description.strip().strip('"')

        conn = get_db()
        conn.execute(
            """INSERT INTO file_descriptions (file_path, user_id, description, generated_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(file_path, user_id) DO UPDATE SET description=excluded.description, generated_at=CURRENT_TIMESTAMP""",
            (file_path, user_id, description)
        )
        conn.commit()
        conn.close()

        return jsonify({"description": description, "source": source}), 200

    except AIDisabledError as e:
        return jsonify({"error": str(e), "ai_disabled": True}), 403
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        app_logger.error(f"[DescribeFile] {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


MATERIAL_RANGES = {
    "PLA":  {"buse": "190-220°C", "plateau": "50-60°C",  "vitesse": "40-60 mm/s", "ventilation": "100%"},
    "PETG": {"buse": "230-250°C", "plateau": "70-80°C",  "vitesse": "30-50 mm/s", "ventilation": "30-50%"},
    "ABS":  {"buse": "230-250°C", "plateau": "95-110°C", "vitesse": "30-50 mm/s", "ventilation": "0-10%"},
    "TPU":  {"buse": "210-230°C", "plateau": "30-50°C",  "vitesse": "15-30 mm/s", "ventilation": "50-100%"},
}

def _material_ref_block(material: str) -> str:
    ref = MATERIAL_RANGES.get((material or "").upper())
    if ref:
        return (f"Normal settings for {material}: nozzle {ref['buse']}, "
                f"bed {ref['plateau']}, speed {ref['vitesse']}, fan {ref['ventilation']}.")
    return f"No known reference ranges for {material}: use general knowledge of this material."

SOSPRINT_SOFT_QUESTIONS = 4
SOSPRINT_HARD_MAX_QUESTIONS = 30

def _sosprint_get_conversation(conv_id, user_id):
    conn = get_db()
    try:
        conv = conn.execute(
            "SELECT * FROM sos_print_conversations WHERE id=? AND user_id=?",
            (conv_id, user_id)
        ).fetchone()
        if not conv:
            return None, []
        messages = conn.execute(
            "SELECT * FROM sos_print_messages WHERE conversation_id=? ORDER BY created_at ASC, id ASC",
            (conv_id,)
        ).fetchall()
        return conv, messages
    finally:
        conn.close()

def _sosprint_touch_conversation(conv_id, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields.keys())
    values = list(fields.values()) + [conv_id]
    conn = get_db()
    try:
        conn.execute(
            f"UPDATE sos_print_conversations SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            values
        )
        conn.commit()
    finally:
        conn.close()

def _sosprint_add_message(conv_id, role, content='', image_filename=None):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO sos_print_messages (conversation_id, role, content, image_filename) VALUES (?, ?, ?, ?)",
            (conv_id, role, content, image_filename)
        )
        conn.commit()
    finally:
        conn.close()

def _sosprint_conversation_photos_b64(conv_id, max_photos=3):
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT image_filename FROM sos_print_messages
               WHERE conversation_id=? AND image_filename IS NOT NULL
               ORDER BY created_at DESC, id DESC LIMIT ?""",
            (conv_id, max_photos)
        ).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        path = os.path.join(SOSPRINT_CONV_PHOTOS_DIR, r['image_filename'])
        try:
            with open(path, 'rb') as f:
                out.append(base64.b64encode(f.read()).decode('utf-8'))
        except Exception:
            continue
    return out

def _sosprint_resolved_reference_cases(user_id, material, description, exclude_conv_id=None, limit=3):
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT id, material, description, resolution_note, last_causes, updated_at
               FROM sos_print_conversations
               WHERE user_id=? AND status='resolved' AND resolution_note != ''
               ORDER BY updated_at DESC LIMIT 40""",
            (user_id,)
        ).fetchall()
    finally:
        conn.close()

    stopwords = {
        'le','la','les','de','des','du','un','une','et','ou','a','au','aux','en','sur','dans',
        'mon','ma','mes','avec','pour','ce','cette','ces','est','sont','plus','moins','tres',
        'the','and','with','for','has','have','this','that'
    }
    desc_words = {
        re.sub(r'[^a-zà-ÿ0-9]', '', w.lower())
        for w in (description or '').split()
    }
    desc_words = {w for w in desc_words if len(w) >= 4 and w not in stopwords}

    scored = []
    for r in rows:
        if exclude_conv_id and r['id'] == exclude_conv_id:
            continue
        score = 0
        if (r['material'] or '').upper() == (material or '').upper():
            score += 2
        row_words = {
            re.sub(r'[^a-zà-ÿ0-9]', '', w.lower())
            for w in (r['description'] or '').split()
        }
        score += len(desc_words & row_words)
        if score > 0:
            scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, r in scored[:limit]:
        try:
            causes = json.loads(r['last_causes']) if r['last_causes'] else []
        except Exception:
            causes = []
        out.append({
            "description": r['description'],
            "resolution_note": r['resolution_note'],
            "causes": causes,
        })
    return out

def _sosprint_reference_cases_block(cases: list) -> str:
    if not cases:
        return ""
    lines = []
    for c in cases:
        lines.append(
            f"- Problem: \"{(c['description'] or '')[:150]}\" → Confirmed working fix: "
            f"\"{(c['resolution_note'] or '')[:200]}\""
        )
    return (
        "Reference: this user has already SOLVED these similar problems before (confirmed fixes, "
        "not just hypotheses). Give them real weight if they match the current case:\n"
        + "\n".join(lines) + "\n"
    )

def _sosprint_section(raw_text: str, start_marker: str, end_marker: str = None) -> str:
    idx = raw_text.upper().find(start_marker.upper())
    if idx == -1:
        return ""
    start = idx + len(start_marker)
    if end_marker:
        end_idx = raw_text.upper().find(end_marker.upper(), start)
        if end_idx != -1:
            return raw_text[start:end_idx].strip()
    return raw_text[start:].strip()

def _sosprint_parse_causes(block: str, max_items: int = 6) -> list:
    causes = []
    for line in block.splitlines():
        line = line.strip()
        line = re.sub(r'^[-*•]\s*', '', line)
        line = re.sub(r'^\d+[\.\)]\s*', '', line)
        line = line.strip(' .')
        if line:
            causes.append(line)
        if len(causes) >= max_items:
            break
    return causes

def _sosprint_parse_eliminated(block: str) -> list:
    first_line = block.splitlines()[0].strip() if block.strip() else ''
    if not first_line or first_line.strip('. ').lower() in ('none', 'aucun', 'aucune'):
        return []
    return [e.strip(' .') for e in first_line.split(',') if e.strip(' .')]

@app.route('/api/ollama/sos-print/questions', methods=['POST'])
@login_required
def api_ollama_sos_print_questions():
    data        = request.json or {}
    material    = (data.get('material') or 'PLA').strip()
    description = (data.get('description') or '').strip()[:600]
    printer_id  = data.get('printer_id') or None
    try:
        printer_id = int(printer_id) if printer_id else None
    except (TypeError, ValueError):
        printer_id = None

    if not description:
        return jsonify({"error": "Merci de décrire le problème rencontré"}), 400

    lang      = get_user_lang()
    lang_name = LANG_NAMES.get(lang, lang)
    ref_block = _material_ref_block(material)

    reference_cases = _sosprint_resolved_reference_cases(session['user_id'], material, description)
    reference_block = _sosprint_reference_cases_block(reference_cases)

    prompt = (
        f"FDM 3D printing expert conducting a diagnostic investigation, like a detective narrowing "
        f"down a list of suspects one clue at a time. Material: {material}. {ref_block}\n"
        f"Problem described by the user: \"{description}\"\n"
        f"{reference_block}"
        f"Step 1 — list 4 to 6 short plausible causes (hypotheses) for this problem, most likely "
        f"first, each as a very short label (3-6 words, no explanation). If a reference case above "
        f"clearly matches, make its confirmed cause one of the top hypotheses.\n"
        f"Step 2 — pick ONE single clarifying question: the one whose answer would rule out the "
        f"most hypotheses above. Ask about something the user didn't already mention (e.g. "
        f"Z-offset, bed leveling, bed surface type, first layer speed, nozzle cleanliness, "
        f"enclosure, humidity storage, retraction settings, print speed, cooling, hotend "
        f"cleaning history). Do not ask about anything already stated in the problem description.\n"
        f"The question must be short and answerable in one line.\n"
        f"Strict format, nothing else:\n"
        f"CAUSES:\n"
        f"- [Cause 1]\n"
        f"- [Cause 2]\n"
        f"- [Cause 3]\n"
        f"- [Cause 4]\n"
        f"QUESTION: [Question]\n"
        f"IMPORTANT: Write your entire response in {lang_name}."
    )
    system = (
        f"You are an expert in 3D printing failure diagnosis conducting a step-by-step "
        f"investigation, one discriminating question at a time. Be concise. Always reply in {lang_name}."
    )

    try:
        raw_text, source = _call_ai(prompt, system=system, num_predict=220, temperature=0.2)

        causes_block = _sosprint_section(raw_text, 'CAUSES:', 'QUESTION:')
        candidate_causes = _sosprint_parse_causes(causes_block)

        question_block = _sosprint_section(raw_text, 'QUESTION:')
        question = question_block.splitlines()[0].strip() if question_block else ''

        conn = get_db()
        try:
            conn.execute(
                """INSERT INTO sos_print_conversations
                   (user_id, printer_id, material, description, title, status, candidate_causes)
                   VALUES (?, ?, ?, ?, ?, 'open', ?)""",
                (session['user_id'], printer_id, material, description,
                 description[:80], json.dumps(candidate_causes))
            )
            conn.commit()
            conversation_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        finally:
            conn.close()
        if question:
            _sosprint_add_message(conversation_id, 'question', question)

        return jsonify({
            "conversation_id": conversation_id,
            "candidate_causes": candidate_causes,
            "question": question,
            "reference_cases": reference_cases,
            "raw": raw_text,
            "source": source
        }), 200
    except AIDisabledError as e:
        return jsonify({"error": str(e), "ai_disabled": True}), 403
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        app_logger.error(f"[SosPrint] {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/ollama/sos-print/next-question', methods=['POST'])
@login_required
def api_ollama_sos_print_next_question():
    data             = request.json or {}
    material         = (data.get('material') or 'PLA').strip()
    description      = (data.get('description') or '').strip()[:600]
    qa_history       = data.get('qa_history') or []
    candidate_causes = data.get('candidate_causes') or []
    conversation_id  = data.get('conversation_id') or None
    user_wants_conclusion = bool(data.get('conclude_now'))

    if not description:
        return jsonify({"error": "Merci de décrire le problème rencontré"}), 400
    if not isinstance(candidate_causes, list):
        candidate_causes = []
    candidate_causes = [str(c).strip()[:120] for c in candidate_causes if str(c).strip()][:8]

    if conversation_id and qa_history:
        last_qa = qa_history[-1]
        if isinstance(last_qa, dict) and last_qa.get('answer'):
            _sosprint_add_message(conversation_id, 'answer', str(last_qa['answer'])[:500])

    qa_lines = []
    for qa in qa_history:
        if isinstance(qa, dict) and qa.get('question') and qa.get('answer'):
            qa_lines.append(f"- {qa['question']} → {qa['answer']}")
    qa_block = "\n".join(qa_lines) if qa_lines else "(none yet)"
    asked_count = len(qa_lines)
    force_conclusion = user_wants_conclusion or asked_count >= SOSPRINT_HARD_MAX_QUESTIONS

    lang      = get_user_lang()
    lang_name = LANG_NAMES.get(lang, lang)
    ref_block = _material_ref_block(material)
    causes_block = "\n".join(f"- {c}" for c in candidate_causes) if candidate_causes else "(none listed yet)"

    if force_conclusion:
        instruction = (
            "Do NOT ask another question — conclude now: decide which hypotheses the answers above "
            "rule out.\n"
        )
    elif asked_count >= SOSPRINT_SOFT_QUESTIONS:
        instruction = (
            f"You have already asked {asked_count} questions. Only ask one more if it would genuinely "
            f"and significantly narrow down the remaining hypotheses; otherwise conclude now rather than "
            f"asking for the sake of it.\n"
        )
    else:
        instruction = (
            "Decide whether you now have enough information to conclude with confidence, or whether "
            "one more clarifying question would meaningfully rule out more hypotheses.\n"
        )

    prompt = (
        f"FDM 3D printing expert continuing a step-by-step diagnostic investigation. "
        f"Material: {material}. {ref_block}\n"
        f"Problem described by the user: \"{description}\"\n"
        f"Current suspect list (hypotheses):\n{causes_block}\n"
        f"Questions already asked and answered so far:\n{qa_block}\n"
        f"{instruction}"
        f"Strict format, nothing else. If concluding, write exactly:\n"
        f"STATUS: DONE\n"
        f"ELIMINATED: [comma-separated hypotheses from the suspect list ruled out by the answers "
        f"above, or 'none']\n"
        f"If asking another question, write exactly:\n"
        f"STATUS: QUESTION\n"
        f"ELIMINATED: [comma-separated hypotheses from the suspect list ruled out so far by the "
        f"answers above, or 'none']\n"
        f"QUESTION: [one short new clarifying question, not already asked, whose answer would rule "
        f"out the most remaining hypotheses]\n"
        f"IMPORTANT: Write your entire response in {lang_name}."
    )
    system = (
        f"You are an expert in 3D printing failure diagnosis, conducting an investigation and "
        f"eliminating hypotheses one answer at a time, like ruling out suspects. Be concise. "
        f"Always reply in {lang_name}."
    )

    try:
        raw_text, source = _call_ai(prompt, system=system, num_predict=200, temperature=0.2)

        status_block = _sosprint_section(raw_text, 'STATUS:', 'ELIMINATED:')
        is_done = force_conclusion or 'DONE' in status_block.upper()

        eliminated_block = _sosprint_section(
            raw_text, 'ELIMINATED:', None if is_done else 'QUESTION:'
        )
        eliminated = [
            e for e in _sosprint_parse_eliminated(eliminated_block)
            if any(e.lower() in c.lower() or c.lower() in e.lower() for c in candidate_causes)
        ] or [e for e in _sosprint_parse_eliminated(eliminated_block)]
        remaining_causes = [c for c in candidate_causes if c not in eliminated] or candidate_causes

        if conversation_id:
            _sosprint_touch_conversation(
                conversation_id,
                candidate_causes=json.dumps(remaining_causes),
                eliminated_causes=json.dumps(eliminated),
            )

        if not is_done:
            question_block = _sosprint_section(raw_text, 'QUESTION:')
            question = question_block.splitlines()[0].strip() if question_block else ''
            if question:
                if conversation_id:
                    _sosprint_add_message(conversation_id, 'question', question)
                return jsonify({
                    "status": "question",
                    "question": question,
                    "eliminated": eliminated,
                    "candidate_causes": remaining_causes,
                    "conversation_id": conversation_id,
                    "source": source
                }), 200

        return jsonify({
            "status": "done",
            "eliminated": eliminated,
            "candidate_causes": remaining_causes,
            "conversation_id": conversation_id,
            "source": source
        }), 200
    except AIDisabledError as e:
        return jsonify({"error": str(e), "ai_disabled": True}), 403
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        app_logger.error(f"[SosPrint] {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

SOSPRINT_PHOTO_MAX_DIM = 1024

def _prepare_sosprint_photo_b64(file_storage) -> str:
    try:
        img = Image.open(file_storage.stream)
        img = img.convert('RGB')
        img.thumbnail((SOSPRINT_PHOTO_MAX_DIM, SOSPRINT_PHOTO_MAX_DIM), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        app_logger.warning(f"[SosPrint] Photo illisible, ignorée: {e}")
        return None

def _save_sosprint_conversation_photo(file_storage) -> str:
    ext = os.path.splitext(file_storage.filename or '')[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        ext = '.jpg'
    image_filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(SOSPRINT_CONV_PHOTOS_DIR, image_filename)
    try:
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream).convert('RGB')
        img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        img.save(dest_path, format='JPEG', quality=85)
        return image_filename
    except Exception as e:
        app_logger.warning(f"[SosPrint] Échec sauvegarde photo conversation: {e}")
        return None

@app.route('/api/ollama/sos-print', methods=['POST'])
@login_required
def api_ollama_sos_print():
    image_b64 = None
    is_multipart = request.content_type and 'multipart/form-data' in request.content_type
    conversation_id = None
    saved_photo_filename = None

    if is_multipart:
        material    = (request.form.get('material') or 'PLA').strip()
        description = (request.form.get('description') or '').strip()[:600]
        printer_id  = request.form.get('printer_id') or None
        conversation_id = request.form.get('conversation_id') or None
        try:
            answers = json.loads(request.form.get('answers') or '[]')
        except Exception:
            answers = []
        try:
            candidate_causes = json.loads(request.form.get('candidate_causes') or '[]')
        except Exception:
            candidate_causes = []
        photo = request.files.get('photo')
        if photo and photo.filename:
            photo.stream.seek(0)
            image_b64 = _prepare_sosprint_photo_b64(photo)
            photo.stream.seek(0)
            saved_photo_filename = _save_sosprint_conversation_photo(photo)
    else:
        data             = request.json or {}
        material         = (data.get('material') or 'PLA').strip()
        description      = (data.get('description') or '').strip()[:600]
        answers          = data.get('answers') or []
        printer_id       = data.get('printer_id') or None
        candidate_causes = data.get('candidate_causes') or []
        conversation_id  = data.get('conversation_id') or None

    if not isinstance(candidate_causes, list):
        candidate_causes = []
    candidate_causes = [str(c).strip()[:120] for c in candidate_causes if str(c).strip()][:8]

    if not description:
        return jsonify({"error": "Merci de décrire le problème rencontré"}), 400

    try:
        conversation_id = int(conversation_id) if conversation_id else None
    except (TypeError, ValueError):
        conversation_id = None

    printer_name = None
    if printer_id:
        try:
            printer_id = int(printer_id)
        except (TypeError, ValueError):
            printer_id = None
        if printer_id:
            conn = get_db()
            try:
                prow = conn.execute(
                    "SELECT name FROM printers WHERE id=? AND user_id=?",
                    (printer_id, session['user_id'])
                ).fetchone()
            finally:
                conn.close()
            if not prow:
                printer_id = None
            else:
                printer_name = prow['name']

    past_diagnostics = []
    if printer_id:
        conn = get_db()
        try:
            rows = conn.execute(
                """SELECT description, causes, created_at FROM sos_print_diagnostics
                   WHERE user_id=? AND printer_id=? AND created_at >= datetime('now', '-90 days')
                   ORDER BY created_at DESC LIMIT 5""",
                (session['user_id'], printer_id)
            ).fetchall()
        finally:
            conn.close()
        for r in rows:
            try:
                causes_list = json.loads(r['causes']) if r['causes'] else []
            except Exception:
                causes_list = []
            past_diagnostics.append({
                "description": r['description'],
                "causes": causes_list,
                "created_at": r['created_at']
            })

    history_block = ""
    if past_diagnostics:
        hist_lines = []
        for d in past_diagnostics:
            first_cause = d['causes'][0] if d['causes'] else ''
            hist_lines.append(f"- \"{d['description'][:150]}\" → {first_cause[:150]}")
        history_block = (
            f"Context: this same printer ({printer_name}) had {len(past_diagnostics)} other diagnosed "
            f"issue(s) in the last 90 days:\n" + "\n".join(hist_lines) + "\n"
            f"If the current problem looks related to this history (same root cause not actually fixed), "
            f"say so explicitly and prioritize that hypothesis.\n"
        )

    lang      = get_user_lang()
    lang_name = LANG_NAMES.get(lang, lang)
    ref_block = _material_ref_block(material)

    qa_block = ""
    if answers:
        qa_lines = []
        for a in answers:
            if isinstance(a, dict) and a.get('question') and a.get('answer'):
                qa_lines.append(f"- {a['question']} → {a['answer']}")
        if qa_lines:
            qa_block = "Additional clarifications from the user:\n" + "\n".join(qa_lines) + "\n"

    if conversation_id and saved_photo_filename:
        _sosprint_add_message(conversation_id, 'photo', '', image_filename=saved_photo_filename)

    conversation_images = []
    if conversation_id:
        conversation_images = _sosprint_conversation_photos_b64(conversation_id, max_photos=3)
    if not conversation_images and image_b64:
        conversation_images = [image_b64]

    reference_cases = _sosprint_resolved_reference_cases(
        session['user_id'], material, description, exclude_conv_id=conversation_id
    )
    reference_block = _sosprint_reference_cases_block(reference_cases)

    photo_instruction = (
        "One or more photos of the failed/problematic print are attached — examine them carefully "
        "and factor in what you visually observe (layer adhesion, warping, stringing, blobs, "
        "geometry issues, etc.) into your diagnosis.\n" if conversation_images else ""
    )

    investigation_block = ""
    if candidate_causes:
        investigation_block = (
            f"The clarifying investigation above already narrowed the likely hypotheses down to: "
            f"{', '.join(candidate_causes)}. Prioritize your final diagnosis among these unless the "
            f"description, answers, or photo clearly point elsewhere.\n"
        )

    prompt = (
        f"FDM 3D printing expert. Material: {material}. {ref_block}\n"
        f"Problem described by the user: \"{description}\"\n"
        f"{qa_block}"
        f"{investigation_block}"
        f"{reference_block}"
        f"{history_block}"
        f"{photo_instruction}"
        f"Give the 3 most likely causes, ranked by likelihood, each with a concrete fix. "
        f"Strict format, nothing else, one cause per line:\n"
        f"1. [Cause]: [Concrete fix]\n"
        f"2. [Cause]: [Concrete fix]\n"
        f"3. [Cause]: [Concrete fix]\n"
        f"IMPORTANT: Write your entire response in {lang_name}."
    )
    system = f"You are an expert in 3D printing failure diagnosis. Be concise and concrete. Always reply in {lang_name}."

    try:
        raw_text, source = _call_ai(
            prompt, system=system, num_predict=400, temperature=0.2,
            images=conversation_images or None
        )
        causes = []
        for b in re.split(r'\n?\s*(?=\d+[\.\)]\s)', raw_text):
            b = b.strip()
            m = re.match(r'^\d+[\.\)]\s*(.+)$', b, re.DOTALL)
            if m:
                causes.append(m.group(1).strip())
            if len(causes) >= 3:
                break
        if not causes:
            causes = [raw_text] if raw_text else []
        if not causes:
            return jsonify({"error": "L'IA n'a retourné aucun diagnostic exploitable"}), 502

        had_photo_final = bool(conversation_images) and source != 'ollama_no_vision'

        try:
            conn = get_db()
            try:
                conn.execute(
                    """INSERT INTO sos_print_diagnostics
                       (user_id, printer_id, material, description, causes, had_photo)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (session['user_id'], printer_id, material, description,
                     json.dumps(causes), had_photo_final)
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            app_logger.warning(f"[SosPrint] Échec enregistrement historique: {e}")

        if conversation_id:
            _sosprint_add_message(conversation_id, 'diagnosis', json.dumps(causes))
            _sosprint_touch_conversation(conversation_id, last_causes=json.dumps(causes))

        return jsonify({
            "causes": causes,
            "raw": raw_text,
            "source": source,
            "had_photo": had_photo_final,
            "photo_ignored": bool(conversation_images) and source == 'ollama_no_vision',
            "recurring": len(past_diagnostics) >= 2,
            "recurring_history": past_diagnostics if len(past_diagnostics) >= 2 else [],
            "printer_name": printer_name,
            "conversation_id": conversation_id,
            "reference_cases": reference_cases
        }), 200
    except AIDisabledError as e:
        return jsonify({"error": str(e), "ai_disabled": True}), 403
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        app_logger.error(f"[SosPrint] {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

def _sosprint_serialize_conversation(conv, messages=None):
    def _jl(v):
        try:
            return json.loads(v) if v else []
        except Exception:
            return []
    out = {
        "id": conv["id"],
        "printer_id": conv["printer_id"],
        "material": conv["material"],
        "description": conv["description"],
        "title": conv["title"] or conv["description"][:80],
        "status": conv["status"],
        "candidate_causes": _jl(conv["candidate_causes"]),
        "eliminated_causes": _jl(conv["eliminated_causes"]),
        "last_causes": _jl(conv["last_causes"]),
        "resolution_note": conv["resolution_note"],
        "created_at": conv["created_at"],
        "updated_at": conv["updated_at"],
        "resolved_at": conv["resolved_at"],
    }
    if messages is not None:
        out["messages"] = [
            {
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "image_url": f"/api/sos-print/conversations/photo/{m['image_filename']}" if m["image_filename"] else None,
                "created_at": m["created_at"],
            }
            for m in messages
        ]
    return out


@app.route('/api/sos-print/conversations', methods=['GET'])
@login_required
def api_sos_print_conversations_list():
    status_filter = (request.args.get('status') or '').strip().lower()
    conn = get_db()
    try:
        if status_filter in ('open', 'resolved'):
            rows = conn.execute(
                """SELECT * FROM sos_print_conversations WHERE user_id=? AND status=?
                   ORDER BY updated_at DESC LIMIT 100""",
                (session['user_id'], status_filter)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM sos_print_conversations WHERE user_id=?
                   ORDER BY updated_at DESC LIMIT 200""",
                (session['user_id'],)
            ).fetchall()
    finally:
        conn.close()
    return jsonify({"conversations": [_sosprint_serialize_conversation(r) for r in rows]}), 200


@app.route('/api/sos-print/conversations/<int:conv_id>', methods=['GET'])
@login_required
def api_sos_print_conversation_get(conv_id):
    conv, messages = _sosprint_get_conversation(conv_id, session['user_id'])
    if not conv:
        return jsonify({"error": "Conversation introuvable"}), 404
    return jsonify(_sosprint_serialize_conversation(conv, messages)), 200


@app.route('/api/sos-print/conversations/<int:conv_id>', methods=['DELETE'])
@login_required
def api_sos_print_conversation_delete(conv_id):
    conn = get_db()
    try:
        conv = conn.execute(
            "SELECT id FROM sos_print_conversations WHERE id=? AND user_id=?",
            (conv_id, session['user_id'])
        ).fetchone()
        if not conv:
            return jsonify({"error": "Conversation introuvable"}), 404
        photo_rows = conn.execute(
            "SELECT image_filename FROM sos_print_messages WHERE conversation_id=? AND image_filename IS NOT NULL",
            (conv_id,)
        ).fetchall()
        conn.execute("DELETE FROM sos_print_messages WHERE conversation_id=?", (conv_id,))
        conn.execute("DELETE FROM sos_print_conversations WHERE id=?", (conv_id,))
        conn.commit()
    finally:
        conn.close()
    for r in photo_rows:
        try:
            os.remove(os.path.join(SOSPRINT_CONV_PHOTOS_DIR, r['image_filename']))
        except Exception:
            pass
    return jsonify({"success": True}), 200


@app.route('/api/sos-print/conversations/photo/<path:filename>', methods=['GET'])
@login_required
def api_sos_print_conversation_photo(filename):
    filename = os.path.basename(filename)
    conn = get_db()
    try:
        owned = conn.execute(
            """SELECT 1 FROM sos_print_messages m
               JOIN sos_print_conversations c ON c.id = m.conversation_id
               WHERE m.image_filename=? AND c.user_id=? LIMIT 1""",
            (filename, session['user_id'])
        ).fetchone()
    finally:
        conn.close()
    if not owned:
        return jsonify({"error": "Introuvable"}), 404
    img_path = os.path.join(SOSPRINT_CONV_PHOTOS_DIR, filename)
    if not os.path.exists(img_path):
        return jsonify({"error": "Fichier image manquant"}), 404
    return send_file(img_path)


@app.route('/api/sos-print/conversations/<int:conv_id>/photo', methods=['POST'])
@login_required
def api_sos_print_conversation_add_photo(conv_id):
    conv, _ = _sosprint_get_conversation(conv_id, session['user_id'])
    if not conv:
        return jsonify({"error": "Conversation introuvable"}), 404

    photo = request.files.get('photo')
    if not photo or not photo.filename:
        return jsonify({"error": "Image requise"}), 400

    note = (request.form.get('note') or '').strip()[:300]
    saved_filename = _save_sosprint_conversation_photo(photo)
    if not saved_filename:
        return jsonify({"error": "Photo illisible ou format non supporté"}), 400

    _sosprint_add_message(conv_id, 'photo', note, image_filename=saved_filename)
    _sosprint_touch_conversation(conv_id)

    return jsonify({
        "success": True,
        "image_url": f"/api/sos-print/conversations/photo/{saved_filename}"
    }), 201


@app.route('/api/sos-print/conversations/<int:conv_id>/resolve', methods=['POST'])
@login_required
def api_sos_print_conversation_resolve(conv_id):
    conv, _ = _sosprint_get_conversation(conv_id, session['user_id'])
    if not conv:
        return jsonify({"error": "Conversation introuvable"}), 404

    data = request.json or {}
    resolution_note = (data.get('resolution_note') or '').strip()[:500]
    if not resolution_note:
        try:
            last_causes = json.loads(conv['last_causes']) if conv['last_causes'] else []
        except Exception:
            last_causes = []
        resolution_note = last_causes[0][:500] if last_causes else "Résolu"

    _sosprint_touch_conversation(conv_id, status='resolved', resolution_note=resolution_note)
    conn = get_db()
    try:
        conn.execute(
            "UPDATE sos_print_conversations SET resolved_at=CURRENT_TIMESTAMP WHERE id=?",
            (conv_id,)
        )
        conn.commit()
    finally:
        conn.close()
    if resolution_note:
        _sosprint_add_message(conv_id, 'note', resolution_note)

    return jsonify({"success": True}), 200


@app.route('/api/sos-print/conversations/<int:conv_id>/reopen', methods=['POST'])
@login_required
def api_sos_print_conversation_reopen(conv_id):
    conv, _ = _sosprint_get_conversation(conv_id, session['user_id'])
    if not conv:
        return jsonify({"error": "Conversation introuvable"}), 404
    _sosprint_touch_conversation(conv_id, status='open')
    return jsonify({"success": True}), 200


@app.route('/api/ollama/semantic-search', methods=['POST'])
@login_required
def api_ollama_semantic_search():
    data  = request.json or {}
    query = (data.get('query') or '').strip()
    files = data.get('files') or []
    if not query:
        return jsonify({"error": "Requête vide"}), 400
    if not files:
        return jsonify({"results": []}), 200

    lang      = get_user_lang()
    lang_name = LANG_NAMES.get(lang, lang)

    STOP_WORDS = {'pour', 'dans', 'avec', 'une', 'des', 'les', 'mon', 'mes',
                  'que', 'qui', 'quoi', 'cherche', 'voudrais', 'veux', 'faire',
                  'truc', 'chose', 'objet', 'quelque', 'genre', 'type',
                  'the', 'for', 'with', 'and', 'that', 'this', 'have', 'from'}
    query_words = [w for w in re.findall(r'[a-zA-Zàâéèêëîïôùûüç]+', query.lower())
                   if len(w) > 3 and w not in STOP_WORDS]

    MAX_CANDIDATES = 50
    if query_words:
        candidates = [f for f in files if any(
            w in ' '.join([f.get('name',''),
                           ' '.join(t.get('name','') for t in (f.get('tags') or [])),
                           f.get('source','')]).lower()
            for w in query_words
        )]
        candidates = (candidates or files)[:MAX_CANDIDATES]
    else:
        candidates = files[:MAX_CANDIDATES]

    file_lines = '\n'.join(
        f"{i}|{f.get('name','')}|{','.join(t.get('name','') for t in (f.get('tags') or []))}"
        for i, f in enumerate(candidates)
    )
    prompt = (
        f"3D printing files (INDEX|name|tags):\n{file_lines}\n\n"
        f"User query ({lang_name}): \"{query}\"\n"
        f"Return ONLY a JSON array of relevant INDEX numbers (max 15). Example: [3,7,12]\n"
        f"Reply with the JSON array only, nothing else."
    )
    system = "You are a semantic search engine for 3D files. Reply only with a JSON array of indices."

    try:
        raw_text, source = _call_ai(prompt, system=system, num_predict=120, temperature=0.1)
        match = re.search(r'\[[\d,\s]*\]', raw_text, re.DOTALL)
        if not match:
            return jsonify({"results": [f['path'] for f in candidates], "fallback": True}), 200
        indices = [int(i) for i in json.loads(match.group()) if 0 <= int(i) < len(candidates)]
        matched = [candidates[i]['path'] for i in indices[:15]]
        extras  = [f['path'] for f in candidates if f['path'] not in set(matched)]
        return jsonify({"results": matched + extras, "count": len(matched), "source": source}), 200
    except AIDisabledError as e:
        return jsonify({"error": str(e), "ai_disabled": True}), 403
    except RuntimeError as e:
        return jsonify({"results": [f['path'] for f in candidates], "fallback": True}), 200
    except Exception as e:
        app_logger.error(f"[SemanticSearch] {e}")
        return jsonify({"results": [f['path'] for f in candidates], "fallback": True}), 200


SLICER_PROFILES_FILE = os.path.join(DATA_DIR, "slicer_profiles.json")
_slicer_profiles_cache = None

def load_slicer_profiles():
    global _slicer_profiles_cache
    if _slicer_profiles_cache is None:
        try:
            with open(SLICER_PROFILES_FILE, 'r', encoding='utf-8') as f:
                _slicer_profiles_cache = json.load(f)
        except Exception:
            _slicer_profiles_cache = []
    return _slicer_profiles_cache

def save_slicer_profiles(profiles):
    global _slicer_profiles_cache
    _slicer_profiles_cache = profiles
    with open(SLICER_PROFILES_FILE, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)


def _parse_kv_text(content):
    kv = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith(';') or line.startswith('['):
            continue
        if '=' not in line:
            continue
        key, _, value = line.partition('=')
        kv[key.strip().lower()] = value.strip().strip('"')
    return kv


def _first_num(value):
    if value is None:
        return None
    m = re.search(r'-?\d+(?:\.\d+)?', str(value))
    return float(m.group()) if m else None


def _first_str(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
        if value is None:
            return None
    s = str(value).split(',')[0].strip().strip('"').strip("'")
    return s or None


def _to_bool(value):
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ('1', 'true', 'yes', 'on'):
        return True
    if s in ('0', 'false', 'no', 'off'):
        return False
    return None


def _pick(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, ''):
            return d[k]
    return None


def _extract_compatible_printers(raw):
    val = raw.get('compatible_printers')
    if not val:
        return []
    if isinstance(val, list):
        items = val
    else:
        s = str(val)
        sep = ';' if ';' in s else (',' if ',' in s else None)
        items = s.split(sep) if sep else [s]
    return [str(v).strip().strip('"') for v in items if str(v).strip()]


def _extract_printer_from_label(label):
    if not label or '@' not in label:
        return []
    suffix = label.split('@', 1)[1].strip()
    return [suffix] if suffix else []


def _extract_printer_from_prefix(label):
    if not label or ' - ' not in label:
        return []
    prefix = label.split(' - ', 1)[0].strip()
    return [prefix] if prefix else []


def _guess_compatible_printer_names(raw, name, source_filename):
    names = _extract_compatible_printers(raw)
    if names:
        return names

    ptype = str(raw.get('type') or '').strip().lower()

    if ptype in ('machine', 'printer'):
        label = (name or source_filename or '').split('@', 1)[0].strip()
        return [label] if label else []

    names = _extract_printer_from_label(name) or _extract_printer_from_label(source_filename)
    if names:
        return names

    return _extract_printer_from_prefix(name) or _extract_printer_from_prefix(source_filename)


def _classify_profile_type(raw, hint=None):
    ptype = str(raw.get('type') or '').strip().lower()
    if ptype in ('machine', 'printer'):
        return 'printer'
    if ptype == 'filament':
        return 'filament'
    if ptype in ('process', 'print'):
        return 'process'
    if hint in ('printer', 'filament', 'process'):
        return hint
    if raw.get('filament_type') or raw.get('material_type') or raw.get('material'):
        return 'filament'
    return 'process'

def _guess_material_type(name, raw_material):
    if raw_material:
        return str(raw_material).strip()
    if not name:
        return None
    name_lower = str(name).lower()
    materials = ['pla', 'petg', 'abs', 'tpu', 'asa', 'nylon', 'pc', 'hips', 'pva']
    for mat in materials:
        if mat in name_lower:
            return mat.upper()
    return None

def _normalize_profile(raw, slicer, name, source_filename, source_path=None, type_hint=None):
    def g(*keys):
        return _pick(raw, list(keys))

    wall_count   = _first_num(g('perimeters', 'wall_line_count', 'wall_loops'))
    top_layers   = _first_num(g('top_solid_layers', 'top_layers', 'top_shell_layers'))
    bottom_layers = _first_num(g('bottom_solid_layers', 'bottom_layers', 'bottom_shell_layers'))

    compatible_printers = _guess_compatible_printer_names(raw, name, source_filename)

    raw_material = _first_str(g('filament_type', 'material_type', 'material'))
    guessed_material = _guess_material_type(name, raw_material)

    return {
        "id": secrets.token_hex(8),
        "name": (name or source_filename or "Profil").strip(),
        "slicer": slicer,
        "source_filename": source_filename,
        "source_path": source_path,
        "source_mtime": (lambda: (os.path.getmtime(source_path) if source_path and os.path.isfile(source_path) else None))(),
        "imported_at": datetime.datetime.now().isoformat(timespec='seconds'),
        "printer_id": None,
        "printer_match_confirmed": False,
        "profile_type": _classify_profile_type(raw, hint=type_hint),
        "compatible_printers": compatible_printers,
        "layer_height": _first_num(g('layer_height')),
        "nozzle_diameter": _first_num(g('nozzle_diameter')),
        "material_type": guessed_material,
        "infill_density": _first_num(g('fill_density', 'infill_sparse_density', 'sparse_infill_density')),
        "infill_pattern": _first_str(g('fill_pattern', 'infill_pattern', 'sparse_infill_pattern')),
        "wall_count": int(wall_count) if wall_count is not None else None,
        "top_layers": int(top_layers) if top_layers is not None else None,
        "bottom_layers": int(bottom_layers) if bottom_layers is not None else None,
        "supports_enabled": _to_bool(g('support_material', 'support_enable', 'enable_support')),
        "print_speed": _first_num(g('perimeter_speed', 'speed_print', 'outer_wall_speed')),
        "nozzle_temp": _first_num(g('temperature', 'material_print_temperature', 'nozzle_temperature')),
        "bed_temp": _first_num(g('bed_temperature', 'material_bed_temperature', 'hot_plate_temp')),
    }


def _persist_profile_bytes(content_bytes, suggested_name):
    safe_base = re.sub(r'[^A-Za-z0-9._-]+', '_', os.path.basename(suggested_name or 'profil'))[:80] or 'profil'
    unique_name = f"{secrets.token_hex(6)}_{safe_base}"
    dest_path = os.path.join(IMPORTED_PROFILES_DIR, unique_name)
    try:
        with open(dest_path, 'wb') as f:
            f.write(content_bytes)
        return dest_path
    except Exception as e:
        app_logger.debug(f"[SlicerProfiles] Impossible de persister le profil {suggested_name}: {e}")
        return None


def _parse_zip_bundle(filename, content_bytes, slicer_hint, type_hint=None):
    try:
        zf = zipfile.ZipFile(io.BytesIO(content_bytes))
    except Exception as e:
        raise ValueError(f"Archive invalide : {e}")

    profiles = []
    json_marker_keys = ('layer_height', 'fill_density', 'sparse_infill_density',
                         'filament_type', 'nozzle_diameter', 'nozzle_temperature')

    for entry_name in zf.namelist():
        base = os.path.basename(entry_name)
        low = entry_name.lower()
        if not base:
            continue

        if low.endswith('.json'):
            try:
                entry_bytes = zf.read(entry_name)
                raw = json.loads(entry_bytes.decode('utf-8-sig', errors='ignore'))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            raw_lower = {str(k).lower(): v for k, v in raw.items()}
            if not any(k in raw_lower for k in json_marker_keys):
                continue
            name = raw.get('name') or os.path.splitext(base)[0]
            source_path = _persist_profile_bytes(entry_bytes, base)
            profiles.append(_normalize_profile(raw_lower, slicer_hint or 'orcaslicer', name, f"{filename}::{base}", source_path=source_path, type_hint=type_hint))

        elif low.endswith('.cfg'):
            try:
                entry_bytes = zf.read(entry_name)
                text = entry_bytes.decode('utf-8-sig', errors='ignore')
            except Exception:
                continue
            raw = _parse_kv_text(text)
            if not raw:
                continue
            name = raw.get('name') or os.path.splitext(base.replace('.inst', ''))[0]
            source_path = _persist_profile_bytes(entry_bytes, base)
            profiles.append(_normalize_profile(raw, slicer_hint or 'cura', name, f"{filename}::{base}", source_path=source_path, type_hint=type_hint))

    if not profiles:
        raise ValueError("Aucun profil exploitable trouvé dans cette archive")
    return profiles


SLICER_ZIP_EXTENSIONS = {
    'orca_filament': 'orcaslicer',
    'orca_printer': 'orcaslicer',
    'orca_process': 'orcaslicer',
    'bbscfg': 'bambustudio',
    'bbsflmt': 'bambustudio',
    'curaprofile': 'cura',
    'zip': None,
}

SLICER_EXT_TYPE_HINTS = {
    'orca_filament': 'filament',
    'orca_printer': 'printer',
    'orca_process': 'process',
    'bbscfg': 'process',
    'bbsflmt': 'filament',
}

SLICER_SUBDIR_TYPE_HINTS = {
    'process': 'process',
    'print': 'process',
    'filament': 'filament',
    'machine': 'printer',
    'printer': 'printer',
}


def _parse_slicer_profile_file(filename, content_bytes, slicer_hint=None, source_path=None, type_hint=None):
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    base_name = os.path.splitext(os.path.basename(filename))[0]
    resolved_type_hint = type_hint or SLICER_EXT_TYPE_HINTS.get(ext)

    if ext in SLICER_ZIP_EXTENSIONS:
        return _parse_zip_bundle(filename, content_bytes, SLICER_ZIP_EXTENSIONS[ext] or slicer_hint, type_hint=resolved_type_hint)

    try:
        text = content_bytes.decode('utf-8-sig')
    except Exception:
        text = content_bytes.decode('latin-1', errors='ignore')

    resolved_path = source_path or _persist_profile_bytes(content_bytes, filename)

    if ext == 'json':
        try:
            raw = json.loads(text)
        except Exception as e:
            raise ValueError(f"JSON invalide : {e}")
        if not isinstance(raw, dict):
            raise ValueError("Format JSON inattendu")
        name = raw.get('name') or base_name
        raw_lower = {str(k).lower(): v for k, v in raw.items()}
        return [_normalize_profile(raw_lower, slicer_hint or 'orcaslicer', name, filename, source_path=resolved_path, type_hint=resolved_type_hint)]

    if ext in ('ini', 'cfg'):
        raw = _parse_kv_text(text)
        if not raw:
            raise ValueError("Aucun paramètre reconnu dans ce fichier")
        if slicer_hint:
            slicer = slicer_hint
        else:
            is_cura = 'wall_line_count' in raw or 'infill_sparse_density' in raw or '[general]' in text.lower()
            slicer = 'cura' if is_cura else 'prusaslicer'
        name = raw.get('name') or base_name
        return [_normalize_profile(raw, slicer, name, filename, source_path=resolved_path, type_hint=resolved_type_hint)]

    raise ValueError(f"Extension non supportée : .{ext} (attendu : .ini, .json, .cfg, .orca_filament, .orca_printer ou .zip)")


def _guess_printer_for_profile(compatible_names, printers):
    if not compatible_names or not printers:
        return None, False

    compat_lower = [c.lower() for c in compatible_names]

    for p in printers:
        aliases = [a.lower() for a in (p.get('config') or {}).get('slicer_profile_aliases', [])]
        if any(c in aliases for c in compat_lower):
            return p['id'], True

    best_id, best_score = None, 0.0
    for p in printers:
        pname = (p.get('name') or '').lower().strip()
        if not pname:
            continue
        for c in compat_lower:
            score = 0.92 if (pname in c or c in pname) else difflib.SequenceMatcher(None, pname, c).ratio()
            if score > best_score:
                best_score, best_id = score, p['id']

    return (best_id, False) if best_id and best_score >= 0.55 else (None, False)


def _apply_printer_autoguess(profiles_subset, user_id):
    try:
        conn = get_db()
        try:
            rows = conn.execute("SELECT * FROM printers WHERE user_id = ?", (user_id,)).fetchall()
        finally:
            conn.close()
        printers = [parse_printer_config(r) for r in rows]
    except Exception as e:
        app_logger.debug(f"[SlicerProfiles] Impossible de charger les imprimantes pour l'auto-assignation: {e}")
        return
    for prof in profiles_subset:
        if prof.get('printer_id'):
            continue
        pid, confirmed = _guess_printer_for_profile(prof.get('compatible_printers') or [], printers)
        if pid:
            prof['printer_id'] = pid
            prof['printer_match_confirmed'] = confirmed


def _remember_printer_alias(printer_id, user_id, names):
    if not printer_id or not names:
        return
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT config FROM printers WHERE id = ? AND user_id = ?", (printer_id, user_id)
        ).fetchone()
        if not row:
            conn.close()
            return
        try:
            config = json.loads(row['config'] or '{}')
        except Exception:
            config = {}
        existing = config.get('slicer_profile_aliases', [])
        existing_lower = {a.lower() for a in existing}
        changed = False
        for name in names:
            if name and name.lower() not in existing_lower:
                existing.append(name)
                existing_lower.add(name.lower())
                changed = True
        if changed:
            config['slicer_profile_aliases'] = existing
            conn.execute("UPDATE printers SET config = ? WHERE id = ?", (json.dumps(config), printer_id))
            conn.commit()
        conn.close()
    except Exception as e:
        app_logger.debug(f"[SlicerProfiles] Échec mémorisation alias imprimante: {e}")


def _scan_dir_for_profiles(dir_path, already_imported, imported_out, slicer_hint=None, type_hint=None):
    if not dir_path or not os.path.isdir(dir_path):
        return
    try:
        entries = os.listdir(dir_path)
    except Exception as e:
        app_logger.debug(f"[SlicerProfiles] Dossier illisible {dir_path}: {e}")
        return
    for fname in entries:
        if fname in already_imported:
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in ('.ini', '.json', '.cfg', '.orca_filament', '.orca_printer', '.orca_process',
                       '.bbscfg', '.bbsflmt', '.curaprofile', '.zip'):
            continue
        fpath = os.path.join(dir_path, fname)
        try:
            if not os.path.isfile(fpath):
                continue
            with open(fpath, 'rb') as f:
                content = f.read()


            new_profiles = _parse_slicer_profile_file(fname, content, slicer_hint=slicer_hint, source_path=fpath, type_hint=type_hint)
            imported_out.extend(new_profiles)
            already_imported.add(fname)
        except Exception as e:
            app_logger.debug(f"[SlicerProfiles] Ignoré {fpath}: {e}")


def _refresh_stale_slicer_profiles(profiles):
    updated_count = 0
    errors = []
    for p in profiles:
        source_path = p.get('source_path')
        if not source_path or not os.path.isfile(source_path):
            continue
        try:
            if os.path.commonpath([os.path.normpath(source_path), os.path.normpath(IMPORTED_PROFILES_DIR)]) == os.path.normpath(IMPORTED_PROFILES_DIR):
                continue  
        except ValueError:
            pass  

        try:
            current_mtime = os.path.getmtime(source_path)
        except OSError:
            continue
        if p.get('source_mtime') is not None and abs(current_mtime - p['source_mtime']) < 1:
            continue  

        try:
            with open(source_path, 'rb') as f:
                content = f.read()
            fresh_versions = _parse_slicer_profile_file(
                os.path.basename(source_path), content,
                slicer_hint=p.get('slicer'), source_path=source_path,
                type_hint=p.get('profile_type')
            )
            if not fresh_versions:
                continue
            fresh = fresh_versions[0]
            for key in ('name', 'layer_height', 'nozzle_diameter', 'material_type', 'infill_density',
                        'infill_pattern', 'wall_count', 'top_layers', 'bottom_layers',
                        'supports_enabled', 'print_speed', 'nozzle_temp', 'bed_temp'):
                if fresh.get(key) is not None:
                    p[key] = fresh[key]
            p['source_mtime'] = current_mtime
            p['last_synced_at'] = datetime.datetime.now().isoformat(timespec='seconds')
            updated_count += 1
        except Exception as e:
            errors.append({'profile': p.get('name'), 'error': str(e)})
            app_logger.debug(f"[SlicerProfiles] Rafraîchissement échoué pour {p.get('name')}: {e}")

    if updated_count:
        save_slicer_profiles(profiles)
    return updated_count, errors


@app.route('/api/slicer-profiles', methods=['GET'])
@login_required
def api_slicer_profiles_list():
    profiles = load_slicer_profiles()
    _refresh_stale_slicer_profiles(profiles)  
    try:
        _autodetect_new_slicer_profiles(profiles, session['user_id'])  
    except Exception as e:
        app_logger.debug(f"[SlicerProfiles] Auto-détection silencieuse ignorée: {e}")
    return jsonify({"profiles": profiles}), 200


@app.route('/api/slicer-profiles/import', methods=['POST'])
@login_required
def api_slicer_profiles_import():
    files = request.files.getlist('profiles')
    if not files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    printer_id_raw = request.form.get('printer_id')
    printer_id = _safe_int(printer_id_raw)

    profiles = load_slicer_profiles()
    imported, errors = [], []

    for file in files:
        if not file or not file.filename:
            continue
        try:
            content = file.read()
            new_profiles = _parse_slicer_profile_file(file.filename, content)
            for np in new_profiles:
                if printer_id:
                    np['printer_id'] = printer_id
                    np['printer_match_confirmed'] = True
            profiles.extend(new_profiles)
            imported.extend(new_profiles)
        except Exception as e:
            errors.append({"filename": file.filename, "error": str(e)})

    if imported:
        if not printer_id:
            _apply_printer_autoguess(imported, session['user_id'])
        save_slicer_profiles(profiles)
        app_logger.info(f"[SlicerProfiles] {len(imported)} profil(s) importé(s) manuellement")

    if not imported:
        return jsonify({"error": "Aucun profil valide importé", "errors": errors}), 400

    return jsonify({"imported": imported, "errors": errors, "profiles": profiles}), 200


@app.route('/api/slicer-profiles/<profile_id>/printer', methods=['PATCH'])
@login_required
def api_slicer_profiles_assign_printer(profile_id):
    data = request.json or {}
    printer_id_raw = data.get('printer_id')
    printer_id = _safe_int(printer_id_raw)

    profiles = load_slicer_profiles()
    target = None
    for p in profiles:
        if p.get('id') == profile_id:
            p['printer_id'] = printer_id
            p['printer_match_confirmed'] = bool(printer_id)
            target = p
            break
    if not target:
        return jsonify({"error": "Profil introuvable"}), 404

    save_slicer_profiles(profiles)

    if printer_id and target.get('compatible_printers'):
        _remember_printer_alias(printer_id, session['user_id'], target['compatible_printers'])

    return jsonify({"success": True, "profiles": profiles}), 200


@app.route('/api/slicer-profiles/<profile_id>/type', methods=['PATCH'])
@login_required
def api_slicer_profiles_assign_type(profile_id):
    data = request.json or {}
    new_type = str(data.get('profile_type') or '').strip().lower()
    if new_type not in ('printer', 'filament', 'process'):
        return jsonify({"error": "Type de profil invalide (attendu : printer, filament ou process)"}), 400

    profiles = load_slicer_profiles()
    target = None
    for p in profiles:
        if p.get('id') == profile_id:
            p['profile_type'] = new_type


            p['profile_type_confirmed'] = True
            target = p
            break
    if not target:
        return jsonify({"error": "Profil introuvable"}), 404

    save_slicer_profiles(profiles)
    return jsonify({"success": True, "profiles": profiles}), 200


@app.route('/api/slicer-profiles/<profile_id>', methods=['DELETE'])
@login_required
def api_slicer_profiles_delete(profile_id):
    profiles = load_slicer_profiles()
    new_profiles = [p for p in profiles if p.get('id') != profile_id]
    if len(new_profiles) == len(profiles):
        return jsonify({"error": "Profil introuvable"}), 404
    save_slicer_profiles(new_profiles)
    return jsonify({"success": True, "profiles": new_profiles}), 200


SLICER_AUTODETECT_DIRS = {
    'prusaslicer': ('PrusaSlicer', ['print', 'filament', 'printer']),
    'superslicer': ('SuperSlicer', ['print', 'filament', 'printer']),
}

SLICER_VERSIONED_USER_DIRS = {
    'orcaslicer':  ('OrcaSlicer\\user', ['process', 'filament', 'machine']),
    'bambustudio': ('BambuStudio\\user', ['process', 'filament', 'machine']),
}

SLICER_CURA_FAMILY_DIRS = {
    'cura': 'cura',
    'anycubic_slicer_next': 'Anycubic Slicer Next',
}


def _scan_versioned_user_dir(base_path, subdirs, already_imported, imported_out, slicer_hint=None):
    if not os.path.isdir(base_path):
        return
    try:
        entries = os.listdir(base_path)
    except Exception as e:
        app_logger.debug(f"[SlicerProfiles] Dossier illisible {base_path}: {e}")
        return
    for entry in entries:
        versioned = os.path.join(base_path, entry)
        if not os.path.isdir(versioned):
            continue
        for sd in subdirs:
            _scan_dir_for_profiles(os.path.join(versioned, sd), already_imported, imported_out, slicer_hint=slicer_hint,
                                    type_hint=SLICER_SUBDIR_TYPE_HINTS.get(sd))


def _scan_creality_print_dir(base_path, already_imported, imported_out):
    if not os.path.isdir(base_path):
        return
    try:
        versions = os.listdir(base_path)
    except Exception as e:
        app_logger.debug(f"[SlicerProfiles] Dossier illisible {base_path}: {e}")
        return
    for version in versions:
        user_dir = os.path.join(base_path, version, 'user')
        if not os.path.isdir(user_dir):
            continue
        try:
            user_ids = os.listdir(user_dir)
        except Exception as e:
            app_logger.debug(f"[SlicerProfiles] Dossier illisible {user_dir}: {e}")
            continue
        for uid in user_ids:
            uid_dir = os.path.join(user_dir, uid)
            if not os.path.isdir(uid_dir):
                continue
            for sd in ('process', 'filament', 'machine'):
                _scan_dir_for_profiles(os.path.join(uid_dir, sd), already_imported, imported_out, slicer_hint='creality_print',
                                        type_hint=SLICER_SUBDIR_TYPE_HINTS.get(sd))


@app.route('/api/slicer-profiles/refresh', methods=['POST'])
@login_required
def api_slicer_profiles_refresh():
    profiles = load_slicer_profiles()
    updated_count, errors = _refresh_stale_slicer_profiles(profiles)
    return jsonify({"updated": updated_count, "total": len(profiles), "profiles": profiles, "errors": errors}), 200


def _autodetect_new_slicer_profiles(profiles, user_id):
    appdata = os.environ.get('APPDATA')
    if not appdata:
        return [] 

    already_imported = {p.get('source_filename') for p in profiles}
    imported = []

    for slicer, (base_rel, subdirs) in SLICER_AUTODETECT_DIRS.items():
        base_path = os.path.join(appdata, base_rel)
        for sd in subdirs:
            _scan_dir_for_profiles(os.path.join(base_path, sd), already_imported, imported, slicer_hint=slicer,
                                    type_hint=SLICER_SUBDIR_TYPE_HINTS.get(sd))

    for slicer, (base_rel, subdirs) in SLICER_VERSIONED_USER_DIRS.items():
        _scan_versioned_user_dir(os.path.join(appdata, base_rel), subdirs, already_imported, imported, slicer_hint=slicer)

    for slicer, folder_name in SLICER_CURA_FAMILY_DIRS.items():
        family_base = os.path.join(appdata, folder_name)
        if not os.path.isdir(family_base):
            continue
        try:
            versions = os.listdir(family_base)
        except Exception as e:
            versions = []
            app_logger.debug(f"[SlicerProfiles] Dossier {folder_name} illisible: {e}")
        for entry in versions:
            versioned = os.path.join(family_base, entry)
            if os.path.isdir(versioned):
                _scan_dir_for_profiles(os.path.join(versioned, 'quality_changes'), already_imported, imported, slicer_hint=slicer,
                                        type_hint='process')
                _scan_dir_for_profiles(os.path.join(versioned, 'user'), already_imported, imported, slicer_hint=slicer)

    _scan_creality_print_dir(os.path.join(appdata, 'Creality', 'Creality Print'), already_imported, imported)

    seen_cura_keys = set()
    deduped = []
    for p in imported:
        if p.get('slicer') == 'cura':
            key = (p.get('name', '').strip().lower(), p.get('profile_type'))
            if key in seen_cura_keys:
                continue
            seen_cura_keys.add(key)
        deduped.append(p)
    imported = deduped

    if imported:
        _apply_printer_autoguess(imported, user_id)
        profiles.extend(imported)
        save_slicer_profiles(profiles)
        app_logger.info(f"[SlicerProfiles] {len(imported)} profil(s) importé(s) automatiquement (tous slicers)")

    return imported


@app.route('/api/slicer-profiles/auto-detect', methods=['POST'])
@login_required
def api_slicer_profiles_autodetect():
    try:
        profiles = load_slicer_profiles()
        imported = _autodetect_new_slicer_profiles(profiles, session['user_id'])
        if not os.environ.get('APPDATA'):
            return jsonify({"error": "Dossier AppData introuvable (fonction disponible sous Windows uniquement)"}), 400
        return jsonify({"imported": imported, "count": len(imported), "profiles": profiles}), 200
    except Exception as e:
        app_logger.error(f"[SlicerProfiles] Auto-détection échouée: {e}", exc_info=True)
        return jsonify({"error": f"Échec de la détection automatique : {e}"}), 500


def _analyze_mesh_for_recommendation(mesh):
    bounds = mesh.bounds
    dims = (bounds[1] - bounds[0]).tolist()
    try:
        volume = float(mesh.volume) if mesh.is_watertight else float(mesh.convex_hull.volume)
    except Exception:
        volume = 0.0
    bbox_volume = float(dims[0] * dims[1] * dims[2]) if all(d > 0 for d in dims) else 0
    fill_ratio = round(volume / bbox_volume, 3) if bbox_volume > 0 else None

    try:
        normals = mesh.face_normals
        downward = normals[:, 2] < -0.4
        overhang_ratio = round(float(np.sum(downward)) / len(normals), 3) if len(normals) else 0.0
    except Exception:
        overhang_ratio = None

    return {
        "dimensions_mm": [round(d, 1) for d in dims],
        "volume_mm3": round(volume, 1),
        "fill_ratio": fill_ratio,
        "overhang_ratio": overhang_ratio,
        "is_watertight": bool(mesh.is_watertight),
    }


MIN_RATING_SAMPLES = 3

def _get_profile_success_stats(user_id):
    try:
        conn = get_db()
        try:
            rows = conn.execute(
                """SELECT slicer_profile_id, result, failure_reason FROM print_history
                   WHERE user_id=? AND slicer_profile_id != '' AND result != ''""",
                (user_id,)
            ).fetchall()
        finally:
            conn.close()
    except Exception as e:
        app_logger.warning(f"[ProfileStats] {e}")
        return {}

    raw = {}
    for r in rows:
        pid = r['slicer_profile_id']
        entry = raw.setdefault(pid, {'success': 0, 'failed': 0, 'partial': 0, 'reasons': {}})
        if r['result'] in ('success', 'failed', 'partial'):
            entry[r['result']] += 1
        if r['result'] == 'failed' and r['failure_reason']:
            entry['reasons'][r['failure_reason']] = entry['reasons'].get(r['failure_reason'], 0) + 1

    stats = {}
    for pid, entry in raw.items():
        total = entry['success'] + entry['failed'] + entry['partial']
        if total == 0:
            continue
        top_reason, top_count = (max(entry['reasons'].items(), key=lambda kv: kv[1])
                                  if entry['reasons'] else (None, 0))
        has_enough_samples = total >= MIN_RATING_SAMPLES
        stats[pid] = {
            'success_count': entry['success'], 'failed_count': entry['failed'], 'partial_count': entry['partial'],
            'sample_size': total,
            'confidence': 'high' if has_enough_samples else 'low',
            'success_rate': round(entry['success'] / total, 2) if has_enough_samples else None,
            'common_issue': top_reason if top_count >= 2 else None,
        }
    return stats


def _build_slim_profiles_with_history(profiles, user_id):
    success_stats = _get_profile_success_stats(user_id)
    slim = []
    for p in profiles:
        entry = {k: v for k, v in p.items() if k not in ('id', 'source_filename', 'imported_at') and v is not None}
        st = success_stats.get(p['id'])
        if st:
            entry['historique_reussite'] = st
        slim.append(entry)
    return slim


def _resolve_recommended_profile_id(result, profiles):
    name = (result.get('profil_recommande') or '').strip().lower()
    if not name:
        return None
    for p in profiles:
        if (p.get('name') or '').strip().lower() == name:
            return p.get('id')
    return None


def _profile_matches_printer(p, printer_id):
    if p.get('profile_type') == 'filament':
        return p.get('printer_id') in (None, printer_id)
    return p.get('printer_id') == printer_id


def _filter_profiles_by_selection(profiles, printer_id, material_type):
    filtered = profiles
    if printer_id is not None:
        filtered = [p for p in filtered if _profile_matches_printer(p, printer_id)]
    if material_type:
        filtered = [
            p for p in filtered
            if p.get('profile_type') != 'filament' or (p.get('material_type') or '').strip().lower() == material_type.strip().lower()
        ]
    return filtered


def _find_selected_filament_profile(profiles, material_type):
    if not material_type:
        return None
    return next(
        (p for p in profiles
         if p.get('profile_type') == 'filament'
         and (p.get('material_type') or '').strip().lower() == material_type.strip().lower()),
        None
    )


def _build_filament_context_note(filament_profile):
    if not filament_profile:
        return ""
    bits = [f"name={filament_profile.get('name')}"]
    if filament_profile.get('material_type'):
        bits.append(f"material={filament_profile['material_type']}")
    if filament_profile.get('nozzle_temp'):
        bits.append(f"nozzle_temp={filament_profile['nozzle_temp']}°C")
    if filament_profile.get('bed_temp'):
        bits.append(f"bed_temp={filament_profile['bed_temp']}°C")
    return (
        f"\nSelected filament ({', '.join(bits)}). This is the ACTUAL filament that will be used — "
        f"if the chosen process profile's temperature/material settings differ from this filament's, "
        f"include a modification to align them (nozzle_temp / bed_temp / material_type), with a reason "
        f"mentioning the filament by name.\n"
    )


@app.route('/api/ollama/recommend-profile', methods=['POST'])
@login_required
def api_ollama_recommend_profile():
    data = request.json or {}
    file_path = data.get('path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Fichier introuvable"}), 404
    if not _is_path_within_sources(file_path, session['user_id']):
        app_logger.warning(f"[SECURITY] Tentative de recommandation IA hors sources: {file_path}")
        return jsonify({"error": "Ce fichier n'appartient à aucune source configurée"}), 403

    profiles = load_slicer_profiles()
    if not profiles:
        return jsonify({
            "error": "Aucun profil importé. Ajoutez vos profils dans Paramètres > Slicer.",
            "no_profiles": True
        }), 400

    printer_id_raw = data.get('printer_id')
    printer_id = _safe_int(printer_id_raw)
    material_type = (data.get('material_type') or '').strip() or None

    if printer_id is not None or material_type:
        filtered_profiles = _filter_profiles_by_selection(profiles, printer_id, material_type)
        if not filtered_profiles:
            return jsonify({
                "error": "Aucun profil ne correspond à l'imprimante et/ou au filament sélectionné.",
                "no_profiles": True
            }), 400
        profiles = filtered_profiles

    try:
        mesh = _load_mesh_for_conversion(file_path)
        piece = _analyze_mesh_for_recommendation(mesh)
    except Exception as e:
        return jsonify({"error": f"Analyse du fichier impossible : {e}"}), 500

    piece['filename'] = os.path.basename(file_path)

    lang = get_user_lang()
    lang_name = LANG_NAMES.get(lang, lang)

    slim_profiles = _build_slim_profiles_with_history(profiles, session['user_id'])
    filament_note = _build_filament_context_note(_find_selected_filament_profile(profiles, material_type))

    prompt = (
        f"3D piece to print:\n{json.dumps(piece, ensure_ascii=False)}\n\n"
        f"Available user slicer profiles:\n{json.dumps(slim_profiles, ensure_ascii=False)}\n"
        f"{filament_note}\n"
        f"Some profiles include an 'historique_reussite' field summarizing REAL past print outcomes on "
        f"this user's machine: sample_size (number of rated prints), confidence ('high' if sample_size >= 3, "
        f"else 'low'), success_rate (0-1, only present when confidence is 'high'), and common_issue (a recurring "
        f"failure cause, only set if it happened at least twice — never a single incident). Strongly prefer "
        f"profiles with a good track record when confidence is 'high'. When confidence is 'low' (few or no "
        f"ratings yet), do NOT treat the small sample as a reliable signal — do not say a profile is bad or "
        f"risky based on 1-2 data points; rely on the piece's geometry instead and only mention the limited "
        f"history as a minor aside if relevant.\n\n"
        f"Pick the single best matching profile (by its 'name' field) for this piece, then list the specific "
        f"parameter changes you would recommend on top of it (e.g. infill_density, supports_enabled, wall_count), "
        f"each with a short reason tied to this piece's geometry (dimensions, fill_ratio, overhang_ratio) "
        f"and/or to the profile's track record.\n"
        f"Reply ONLY with strict JSON, no markdown formatting, no text outside the JSON object:\n"
        f'{{"profil_recommande": "<profile name>", "modifications": '
        f'[{{"parametre": "<field>", "valeur_actuelle": <value or null>, "valeur_suggeree": <value>, "raison": "<short reason>"}}]}}\n'
        f"If the picked profile needs no changes, return an empty modifications array.\n"
        f"IMPORTANT: write every 'raison' text in {lang_name}."
    )
    system = (
        f"You are an expert 3D printing assistant helping a maker pick the best slicer profile "
        f"for a piece from their own saved profiles, informed by their real print history when available. "
        f"Always reply with valid JSON only. Write all 'raison' text in {lang_name}."
    )

    try:
        raw_text, source = _call_ai(prompt, system=system, num_predict=400, temperature=0.2)
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not match:
            return jsonify({"error": "Réponse IA illisible", "raw": raw_text}), 502
        result = json.loads(match.group())
        result['source'] = source
        result['piece'] = piece
        result['profil_recommande_id'] = _resolve_recommended_profile_id(result, profiles)
        return jsonify(result), 200
    except AIDisabledError as e:
        return jsonify({"error": str(e), "ai_disabled": True}), 403
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except json.JSONDecodeError:
        return jsonify({"error": "Réponse IA invalide (JSON malformé)"}), 502
    except Exception as e:
        app_logger.error(f"[RecommendProfile] {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


def _pack_footprints_shelf(items, bed_w, bed_h, spacing=0.0):
    sorted_items = sorted(items, key=lambda it: max(it['w'], it['h']), reverse=True)

    placed = []
    unplaced = []
    cursor_x, cursor_y = 0.0, 0.0
    shelf_h = 0.0

    for it in sorted_items:
        w, h = it['w'], it['h']
        rotated = False
        if w > bed_w and h <= bed_w:
            w, h = h, w
            rotated = True
        if w > bed_w or h > bed_h:
            unplaced.append(it['id'])
            continue

        if cursor_x + w > bed_w:
            cursor_x = 0.0
            cursor_y += shelf_h + spacing
            shelf_h = 0.0

        if cursor_y + h > bed_h:
            unplaced.append(it['id'])
            continue

        placed.append({'id': it['id'], 'x': round(cursor_x, 1), 'y': round(cursor_y, 1), 'rotated': rotated,
                        'w': round(w, 1), 'h': round(h, 1)})
        cursor_x += w + spacing
        shelf_h = max(shelf_h, h)

    return placed, unplaced


def _pack_footprints(items, bed_w, bed_h, spacing=0.0):
    if not HAS_RECTPACK:
        return _pack_footprints_shelf(items, bed_w, bed_h, spacing)

    original_dims = {it['id']: (it['w'], it['h']) for it in items}

    packer = newPacker(pack_algo=MaxRectsBssf, sort_algo=SORT_AREA, rotation=True)
    packer.add_bin(bed_w, bed_h)
    for it in items:
        packer.add_rect(it['w'], it['h'], rid=it['id'])
    packer.pack()

    placed = []
    placed_ids = set()
    for abin in packer:
        for rect in abin:
            orig_w, orig_h = original_dims[rect.rid]
            rotated = abs(rect.width - orig_w) > 0.01
            placed.append({
                'id': rect.rid, 'x': round(rect.x, 1), 'y': round(rect.y, 1),
                'w': round(rect.width, 1), 'h': round(rect.height, 1), 'rotated': rotated
            })
            placed_ids.add(rect.rid)

    unplaced = [it['id'] for it in items if it['id'] not in placed_ids]
    return placed, unplaced


def _get_polygon_footprint(mesh):
    pts_xy = mesh.vertices[:, :2]
    hull = MultiPoint([tuple(p) for p in pts_xy]).convex_hull
    if hull.geom_type != 'Polygon':
        hull = hull.buffer(0.5)
    minx, miny, maxx, maxy = hull.bounds
    return shapely_affinity.translate(hull, xoff=-minx, yoff=-miny)


def _pack_polygons(items, bed_w, bed_h, spacing=0.0):
    sorted_items = sorted(items, key=lambda it: it['polygon'].area, reverse=True)
    grid_step = max(2.0, min(bed_w, bed_h) / 80)

    placed_polys, placed_bounds, placed = [], [], []
    unplaced = []

    def frange(start, stop, step):
        v = start
        while v <= stop + 1e-9:
            yield round(v, 2)
            v += step

    def collides(poly, bounds):
        ex = (bounds[0] - spacing, bounds[1] - spacing, bounds[2] + spacing, bounds[3] + spacing)
        for other, ob in zip(placed_polys, placed_bounds):
            if ex[2] < ob[0] or ex[0] > ob[2] or ex[3] < ob[1] or ex[1] > ob[3]:
                continue
            if poly.distance(other) < spacing:
                return True
        return False

    for it in sorted_items:
        base_poly = it['polygon']
        found = False
        for rotation_deg in (0, 90, 180, 270):
            rotated = shapely_affinity.rotate(base_poly, rotation_deg, origin=(0, 0), use_radians=False)
            minx, miny, maxx, maxy = rotated.bounds
            norm = shapely_affinity.translate(rotated, xoff=-minx, yoff=-miny)
            w, h = maxx - minx, maxy - miny
            if w > bed_w or h > bed_h:
                continue
            for y in frange(0, bed_h - h, grid_step):
                for x in frange(0, bed_w - w, grid_step):
                    candidate = shapely_affinity.translate(norm, xoff=x, yoff=y)
                    cbounds = (x, y, x + w, y + h)
                    if collides(candidate, cbounds):
                        continue
                    placed_polys.append(candidate)
                    placed_bounds.append(cbounds)
                    placed.append({
                        'id': it['id'], 'x': round(x, 1), 'y': round(y, 1),
                        'w': round(w, 1), 'h': round(h, 1), 'rotation_deg': rotation_deg
                    })
                    found = True
                    break
                if found:
                    break
            if found:
                break
        if not found:
            unplaced.append(it['id'])

    return placed, unplaced


@app.route('/api/nesting/arrange', methods=['POST'])
@login_required
def api_nesting_arrange():
    data = request.json or {}
    paths = data.get('paths') or []
    bed_w = float(data.get('bed_width') or 220)
    bed_h = float(data.get('bed_height') or 220)
    bed_z = float(data.get('bed_height_z') or 250)
    spacing = max(float(data.get('spacing') or 3.0), 0.5)

    if len(paths) < 2:
        return jsonify({"error": "Sélectionne au moins 2 fichiers à nester"}), 400

    items, meshes, piece_stats, errors = [], {}, {}, []

    for path in paths:
        if not os.path.exists(path):
            errors.append({"path": path, "error": "Fichier introuvable"})
            continue
        try:
            mesh = _load_mesh_for_conversion(path)
            bounds = mesh.bounds
            dims = bounds[1] - bounds[0]
            if float(dims[2]) > bed_z:
                errors.append({
                    "path": path,
                    "error": f"Trop haute pour ce plateau : {round(float(dims[2]), 1)}mm > {bed_z}mm de hauteur max"
                })
                continue
            mesh.apply_translation([-bounds[0][0], -bounds[0][1], -bounds[0][2]])
            meshes[path] = mesh
            if HAS_SHAPELY:
                items.append({'id': path, 'polygon': _get_polygon_footprint(mesh)})
            else:
                items.append({'id': path, 'w': float(dims[0]) + spacing, 'h': float(dims[1]) + spacing})
            stats = _analyze_mesh_for_recommendation(mesh)
            stats['filename'] = os.path.basename(path)
            piece_stats[path] = stats
        except Exception as e:
            errors.append({"path": path, "error": str(e)})

    if len(items) < 2:
        return jsonify({"error": "Pas assez de fichiers exploitables pour nester", "errors": errors}), 400

    if HAS_SHAPELY:
        placed, unplaced_ids = _pack_polygons(items, bed_w, bed_h, spacing=spacing)
    else:
        placed, unplaced_ids = _pack_footprints(items, bed_w, bed_h, spacing=0)
        for p in placed:
            p['rotation_deg'] = 90 if p['rotated'] else 0

    if placed:
        group_min_x = min(p['x'] for p in placed)
        group_min_y = min(p['y'] for p in placed)
        group_max_x = max(p['x'] + p['w'] for p in placed)
        group_max_y = max(p['y'] + p['h'] for p in placed)
        offset_x = (bed_w - (group_max_x - group_min_x)) / 2 - group_min_x
        offset_y = (bed_h - (group_max_y - group_min_y)) / 2 - group_min_y
        for p in placed:
            p['x'] = round(p['x'] + offset_x, 1)
            p['y'] = round(p['y'] + offset_y, 1)

    combined_parts, placement_result = [], []
    for p in placed:
        path = p['id']
        mesh = meshes[path].copy()
        rotation_deg = p['rotation_deg']
        if rotation_deg:
            mesh.apply_transform(tra.rotation_matrix(np.radians(rotation_deg), [0, 0, 1]))
            b = mesh.bounds
            mesh.apply_translation([-b[0][0], -b[0][1], 0])
        offset = 0 if HAS_SHAPELY else spacing / 2
        mesh.apply_translation([p['x'] + offset, p['y'] + offset, 0])
        combined_parts.append(mesh)
        placement_result.append({
            "filename": os.path.basename(path), "path": path,
            "x": round(p['x'] + offset, 1), "y": round(p['y'] + offset, 1),
            "w": p['w'], "h": p['h'], "rotated": bool(rotation_deg), "rotation_deg": rotation_deg
        })

    try:
        combined = trimesh.util.concatenate(combined_parts)
        out_dir = os.path.join(DATA_DIR, "nesting_output")
        os.makedirs(out_dir, exist_ok=True)
        out_name = f"stellio_nest_{secrets.token_hex(4)}.3mf"
        out_path = os.path.join(out_dir, out_name)
        combined.export(out_path)
    except Exception as e:
        return jsonify({"error": f"Échec de la génération du plateau combiné : {e}"}), 500

    unplaced = [{"filename": os.path.basename(pid), "path": pid} for pid in unplaced_ids]

    return jsonify({
        "output_path": out_path,
        "output_filename": out_name,
        "placed": placement_result,
        "unplaced": unplaced,
        "bed_width": bed_w, "bed_height": bed_h, "bed_height_z": bed_z,
        "piece_stats": list(piece_stats.values()),
        "errors": errors
    }), 200


@app.route('/api/ollama/recommend-profile-batch', methods=['POST'])
@login_required
def api_ollama_recommend_profile_batch():
    data = request.json or {}
    pieces = data.get('pieces') or []
    if not pieces:
        return jsonify({"error": "Aucune pièce fournie"}), 400

    profiles = load_slicer_profiles()
    if not profiles:
        return jsonify({
            "error": "Aucun profil importé. Ajoutez vos profils dans Paramètres > Slicer.",
            "no_profiles": True
        }), 400

    printer_id_raw = data.get('printer_id')
    printer_id = _safe_int(printer_id_raw)
    material_type = (data.get('material_type') or '').strip() or None

    if printer_id is not None or material_type:
        filtered_profiles = _filter_profiles_by_selection(profiles, printer_id, material_type)
        if not filtered_profiles:
            return jsonify({
                "error": "Aucun profil ne correspond à l'imprimante et/ou au filament sélectionné.",
                "no_profiles": True
            }), 400
        profiles = filtered_profiles

    lang = get_user_lang()
    lang_name = LANG_NAMES.get(lang, lang)

    slim_profiles = _build_slim_profiles_with_history(profiles, session['user_id'])
    filament_note = _build_filament_context_note(_find_selected_filament_profile(profiles, material_type))

    plate_summary = {
        "piece_count": len(pieces),
        "max_overhang_ratio": max((p.get('overhang_ratio') or 0) for p in pieces),
        "total_volume_mm3": round(sum((p.get('volume_mm3') or 0) for p in pieces), 1),
        "pieces": pieces,
    }

    prompt = (
        f"Plate with multiple 3D pieces to print together in the same job:\n"
        f"{json.dumps(plate_summary, ensure_ascii=False)}\n\n"
        f"Available user slicer profiles:\n{json.dumps(slim_profiles, ensure_ascii=False)}\n"
        f"{filament_note}\n"
        f"Some profiles include an 'historique_reussite' field summarizing REAL past print outcomes on "
        f"this user's machine: sample_size (number of rated prints), confidence ('high' if sample_size >= 3, "
        f"else 'low'), success_rate (0-1, only present when confidence is 'high'), and common_issue (a recurring "
        f"failure cause, only set if it happened at least twice — never a single incident). Strongly prefer "
        f"profiles with a good track record when confidence is 'high'. When confidence is 'low' (few or no "
        f"ratings yet), do NOT treat the small sample as a reliable signal — do not say a profile is bad or "
        f"risky based on 1-2 data points; rely on the piece's geometry instead and only mention the limited "
        f"history as a minor aside if relevant.\n\n"
        f"Pick the single best matching profile (by its 'name' field) that works for the WHOLE plate "
        f"(all pieces printed together in one job), then list the specific parameter changes you would "
        f"recommend, each with a short reason. Consider that supports (if any) must suit the piece with "
        f"the highest overhang_ratio, and infill/speed/temperature must be a sensible compromise for ALL pieces.\n"
        f"Reply ONLY with strict JSON, no markdown formatting, no text outside the JSON object:\n"
        f'{{"profil_recommande": "<profile name>", "modifications": '
        f'[{{"parametre": "<field>", "valeur_actuelle": <value or null>, "valeur_suggeree": <value>, "raison": "<short reason>"}}]}}\n'
        f"IMPORTANT: write every 'raison' text in {lang_name}."
    )
    system = (
        f"You are an expert 3D printing assistant helping a maker pick the best slicer profile "
        f"for a full plate of several pieces printed together in the same job, from their own saved "
        f"profiles, informed by their real print history when available. Always reply with valid JSON only. "
        f"Write all 'raison' text in {lang_name}."
    )

    try:
        raw_text, source = _call_ai(prompt, system=system, num_predict=400, temperature=0.2)
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not match:
            return jsonify({"error": "Réponse IA illisible", "raw": raw_text}), 502
        result = json.loads(match.group())
        result['source'] = source
        result['plate'] = plate_summary
        result['profil_recommande_id'] = _resolve_recommended_profile_id(result, profiles)
        return jsonify(result), 200
    except AIDisabledError as e:
        return jsonify({"error": str(e), "ai_disabled": True}), 403
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except json.JSONDecodeError:
        return jsonify({"error": "Réponse IA invalide (JSON malformé)"}), 502
    except Exception as e:
        app_logger.error(f"[RecommendProfileBatch] {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500


@app.route('/api/spoolman/spools', methods=['GET'])
@login_required
def api_spoolman_spools():
    url = request.args.get('url', '').rstrip('/')
    if not url:
        return jsonify({"error": "URL manquante"}), 400
    try:
        app_logger.info(f"[Spoolman] GET {url}/api/v1/spool")
        res = requests.get(f"{url}/api/v1/spool", timeout=8, headers={"Accept": "application/json"})
        app_logger.info(f"[Spoolman] Status: {res.status_code}")
        if res.status_code == 404:
            res2 = requests.get(f"{url}/api/spool", timeout=5, headers={"Accept": "application/json"})
            if res2.ok:
                data = res2.json()
                return jsonify(data.get('items', data) if isinstance(data, dict) else data), 200
            return jsonify({"error": f"Endpoint introuvable sur {url}"}), 404
        if not res.ok:
            return jsonify({"error": f"Spoolman a répondu {res.status_code}"}), res.status_code
        data = res.json()
        return jsonify(data.get('items', data) if isinstance(data, dict) and 'items' in data else data), 200
    except requests.exceptions.ConnectionError:
        return jsonify({"error": f"Connexion refusée — Spoolman démarré sur {url} ?"}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout"}), 504
    except Exception as e:
        app_logger.error(f"[Spoolman] Erreur: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

def _get_spool_remaining_g(source_type, source_id, user_id):
    if source_type == 'manual':
        try:
            conn = get_db()
            row = conn.execute(
                "SELECT remaining_g FROM manual_filament_spools WHERE id=? AND user_id=?",
                (int(source_id), user_id)
            ).fetchone()
            conn.close()
            return row['remaining_g'] if row and row['remaining_g'] is not None else None
        except Exception:
            return None
    elif source_type == 'spoolman':
        try:
            conn = get_db()
            row = conn.execute(
                """SELECT spoolman_url FROM filament_assignments
                   WHERE source_type='spoolman' AND source_id=? AND user_id=?
                   ORDER BY assigned_at DESC LIMIT 1""",
                (str(source_id), user_id)
            ).fetchone()
            conn.close()
            if not row or not row['spoolman_url']:
                return None
            r = requests.get(f"{row['spoolman_url']}/api/v1/spool/{source_id}", timeout=5,
                              headers={"Accept": "application/json"})
            if not r.ok:
                return None
            return r.json().get('remaining_weight')
        except Exception:
            return None
    return None

def _check_restock_for_files(file_paths, user_id):
    conn = get_db()
    try:
        needs = {}
        for fp in file_paths:
            norm = fp.replace('\\', '/')
            assignment = conn.execute(
                "SELECT source_type, source_id, source_label, material FROM filament_assignments WHERE file_path=? AND user_id=?",
                (norm, user_id)
            ).fetchone()
            if not assignment:
                continue
            required_g, _ = _get_required_weight_for_file(norm)
            if not required_g:
                continue
            key = (assignment['source_type'], assignment['source_id'])
            entry = needs.setdefault(key, {
                'source_type': assignment['source_type'], 'source_id': assignment['source_id'],
                'label': assignment['source_label'] or assignment['material'] or 'Bobine',
                'required_g': 0, 'files': []
            })
            entry['required_g'] += required_g
            entry['files'].append(os.path.basename(norm))
    finally:
        conn.close()

    alerts = []
    for (source_type, source_id), entry in needs.items():
        remaining_g = _get_spool_remaining_g(source_type, source_id, user_id)
        if remaining_g is not None and remaining_g < entry['required_g']:
            alerts.append({
                'label': entry['label'],
                'required_g': round(entry['required_g'], 1),
                'remaining_g': round(remaining_g, 1),
                'missing_g': round(entry['required_g'] - remaining_g, 1),
                'files': entry['files']
            })
    return alerts

@app.route('/api/ai/restock-check', methods=['GET'])
@login_required
def api_ai_restock_check():
    conn = get_db()
    try:
        favorite_paths = [r['file_path'] for r in conn.execute(
            "SELECT file_path FROM favorites WHERE user_id=?", (session['user_id'],)
        ).fetchall()]
    finally:
        conn.close()

    alerts = _check_restock_for_files(favorite_paths, session['user_id'])
    return jsonify({"alerts": alerts, "checked_files": len(favorite_paths)}), 200

def _get_required_weight_for_file(file_path):
    with slice_estimate_lock:
        precise = slice_estimate_results.get(file_path)
    if precise and precise.get('status') == 'done' and precise.get('data', {}).get('weight_g') is not None:
        return precise['data']['weight_g'], precise['data'].get('slicer_name', 'slicer')

    if is_virtual_archive_path(file_path):
        return None, None
    try:
        normalized_path = file_path.replace('\\', '/')
        cache_key = f"analysis_{hashlib.md5(normalized_path.encode()).hexdigest()}"
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            cached = cache.get(cache_key)
            if cached and cached.get('weights', {}).get('pla') is not None:
                return cached['weights']['pla'], 'geometric'
    except Exception:
        pass
    return None, None

def _compute_estimated_cost(file_path, weight_g_hint=None):
    material_cost = elec_cost = total_cost = None
    try:
        settings = load_settings() or {}

        weight_g = weight_g_hint
        if weight_g is None:
            weight_g, _src = _get_required_weight_for_file(file_path.replace('\\', '/'))

        if weight_g:
            spools = settings.get('print_cost_spools') or []
            default_spool_id = settings.get('print_cost_default_spool_id')
            default_spool = next((s for s in spools if s.get('id') == default_spool_id), None) or (spools[0] if spools else None)

            if default_spool:
                spool_price = float(default_spool.get('price') or 0)
                spool_weight = float(default_spool.get('weight') or 0)
            else:
                spool_price = float(settings.get('print_cost_spool_price') or 0)
                spool_weight = float(settings.get('print_cost_spool_weight') or 0)

            if spool_price > 0 and spool_weight > 0:
                price_per_gram = spool_price / spool_weight
                material_cost = round(weight_g * price_per_gram, 4)

            elec_price_raw = settings.get('print_cost_elec_price')
            if elec_price_raw not in (None, ''):
                try:
                    elec_price = float(elec_price_raw)
                except (TypeError, ValueError):
                    elec_price = 0
                if elec_price > 0:
                    time_seconds = None
                    with slice_estimate_lock:
                        precise = slice_estimate_results.get(file_path.replace('\\', '/'))
                    if precise and precise.get('status') == 'done':
                        time_seconds = precise.get('data', {}).get('time_seconds')
                    if time_seconds:
                        printer_power = None
                        printer_id = settings.get('print_cost_printer_id')
                        if printer_id:
                            try:
                                user_id = session.get('user_id')
                            except RuntimeError:
                                user_id = None
                            if user_id:
                                conn = get_db()
                                try:
                                    row = conn.execute(
                                        "SELECT power_w FROM printers WHERE id=? AND user_id=?",
                                        (printer_id, user_id)
                                    ).fetchone()
                                finally:
                                    conn.close()
                                if row and row['power_w'] is not None:
                                    printer_power = float(row['power_w'])
                        if printer_power is None:
                            printer_power = float(settings.get('print_cost_printer_power') or 120)
                        time_hours = time_seconds / 3600
                        elec_cost = round(time_hours * (printer_power / 1000) * elec_price, 4)

            if material_cost is not None or elec_cost is not None:
                total_cost = round((material_cost or 0) + (elec_cost or 0), 4)
    except Exception as e:
        app_logger.info(f"[Cost] Erreur calcul coût pour {file_path}: {e}")

    return material_cost, elec_cost, total_cost, weight_g


MATERIAL_CO2_FACTORS_KG_PER_KG = {
    'pla': 1.4, 'petg': 2.0, 'abs': 2.6, 'asa': 2.7, 'tpu': 2.5,
    'nylon': 5.0, 'pa': 5.0, 'pc': 3.5, 'pva': 2.2, 'hips': 2.4,
}
DEFAULT_MATERIAL_CO2_FACTOR_KG_PER_KG = 2.0  

def _get_material_for_file(file_path, user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT source_type, source_id, material FROM filament_assignments WHERE file_path=? AND user_id=?",
            (file_path.replace('\\', '/'), user_id)
        ).fetchone()
        if not row:
            return None
        if row['material']:
            return row['material']
        if row['source_type'] == 'manual':
            spool = conn.execute(
                "SELECT material FROM manual_filament_spools WHERE id=? AND user_id=?",
                (row['source_id'], user_id)
            ).fetchone()
            return spool['material'] if spool else None
        return None
    finally:
        conn.close()

def _compute_eco_estimate(file_path, user_id, weight_g_hint=None):
    norm = file_path.replace('\\', '/')
    weight_g = weight_g_hint
    if weight_g is None:
        weight_g, _src = _get_required_weight_for_file(norm)
    if not weight_g:
        return None

    material = (_get_material_for_file(norm, user_id) or '').strip().lower()
    factor = MATERIAL_CO2_FACTORS_KG_PER_KG.get(material, DEFAULT_MATERIAL_CO2_FACTOR_KG_PER_KG)
    material_co2_g = round((weight_g / 1000) * factor * 1000, 1)

    elec_co2_g = None
    settings = load_settings() or {}
    co2_factor_raw = settings.get('eco_elec_co2_g_per_kwh')
    if co2_factor_raw not in (None, ''):
        try:
            co2_factor = float(co2_factor_raw)
        except (TypeError, ValueError):
            co2_factor = 0
        if co2_factor > 0:
            time_seconds = None
            with slice_estimate_lock:
                precise = slice_estimate_results.get(norm)
            if precise and precise.get('status') == 'done':
                time_seconds = precise.get('data', {}).get('time_seconds')
            if time_seconds:
                printer_power = float(settings.get('print_cost_printer_power') or 120)
                kwh = (time_seconds / 3600) * (printer_power / 1000)
                elec_co2_g = round(kwh * co2_factor, 1)

    return {
        "material": material or None,
        "material_co2_g": material_co2_g,
        "elec_co2_g": elec_co2_g,
        "total_co2_g": round(material_co2_g + (elec_co2_g or 0), 1),
        "weight_g": round(weight_g, 1),
        "co2_factor_used": factor,
    }

@app.route('/api/eco/estimate', methods=['GET'])
@login_required
def api_eco_estimate():
    file_path = (request.args.get('path') or '').strip()
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400
    estimate = _compute_eco_estimate(file_path, session['user_id'])
    if estimate is None:
        return jsonify({"status": "pending",
                         "message": "Poids pas encore disponible pour ce fichier."}), 202
    return jsonify({"status": "done", **estimate}), 200


def _consume_spool_filament(spoolman_url, spool_id, weight_g):
    try:
        res = requests.post(
            f"{spoolman_url}/api/v1/spool/{spool_id}/use",
            json={"use_weight": round(float(weight_g), 1)},
            timeout=8, headers={"Accept": "application/json"}
        )
        if res.ok:
            app_logger.info(f"[Spoolman] Bobine #{spool_id} décrémentée de {weight_g}g")
            return True
        app_logger.warning(f"[Spoolman] Échec décrément bobine #{spool_id}: {res.status_code}")
        return False
    except Exception as e:
        app_logger.warning(f"[Spoolman] Erreur décrément bobine #{spool_id}: {e}")
        return False


def _get_bambu_ams_slots(user_id):
    slots = []
    try:
        conn = get_db()
        try:
            printers = conn.execute(
                "SELECT * FROM printers WHERE user_id=? AND type='bambu'", (user_id,)
            ).fetchall()
        finally:
            conn.close()
    except Exception as e:
        app_logger.warning(f"[FilamentBridge] Lecture imprimantes Bambu impossible: {e}")
        return slots

    for p in printers:
        try:
            printer = parse_printer_config(p)
            status = printer_hub._get_bambu_status(printer, {})
            ams_list = status.get('ams') or []
            for tray in ams_list:
                material = (tray.get('material') or '').strip()
                if not material:
                    continue
                color = tray.get('color') or ''
                slots.append({
                    'source_type': 'bambu_ams',
                    'source_id': f"{printer['id']}:{tray.get('id')}",
                    'name': f"AMS {tray.get('id')} — {printer.get('name', 'Bambu')}",
                    'material': material,
                    'color_hex': f"#{color}" if color and not color.startswith('#') else (color or '#888888'),
                    'remaining_g': tray.get('remaining_g'),
                    'capacity_g': tray.get('tray_weight', 1000),
                    'printer_id': printer['id'],
                    'printer_name': printer.get('name', 'Bambu')
                })
        except Exception as e:
            app_logger.info(f"[FilamentBridge] AMS indisponible pour {p['name'] if p else '?'}: {e}")
    return slots

def _get_manual_filament_slots(user_id):
    slots = []
    try:
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT id, name, material, color_hex, remaining_g, capacity_g, source_label FROM manual_filament_spools WHERE user_id=? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
        finally:
            conn.close()
        for r in rows:
            slots.append({
                'source_type': 'manual',
                'source_id': str(r['id']),
                'name': r['name'],
                'material': r['material'] or '',
                'color_hex': r['color_hex'] or '#888888',
                'remaining_g': r['remaining_g'],
                'capacity_g': r['capacity_g'] or 1000,
                'source_label': r['source_label'] or 'Manuel'
            })
    except Exception as e:
        app_logger.warning(f"[FilamentBridge] Lecture bobines manuelles impossible: {e}")
    return slots

def _get_spoolman_slots(url):
    slots = []
    if not url:
        return slots, None
    try:
        res = requests.get(f"{url}/api/v1/spool", timeout=8, headers={"Accept": "application/json"})
        if not res.ok:
            return slots, f"Spoolman a répondu {res.status_code}"
        data = res.json()
        spools = data.get('items', data) if isinstance(data, dict) and 'items' in data else data
        for s in spools:
            if s.get('archived'):
                continue
            filament = s.get('filament', {}) or {}
            vendor = filament.get('vendor', {}) or {}
            color = filament.get('color_hex')
            slots.append({
                'source_type': 'spoolman',
                'source_id': str(s.get('id')),
                'name': filament.get('name') or vendor.get('name') or f"Bobine #{s.get('id')}",
                'material': filament.get('material') or '',
                'color_hex': f"#{str(color).replace('#', '')}" if color else '#888888',
                'remaining_g': s.get('remaining_weight'),
                'capacity_g': filament.get('weight') or s.get('initial_weight') or 1000,
                'spoolman_url': url
            })
    except requests.exceptions.ConnectionError:
        return slots, f"Connexion refusée — Spoolman démarré sur {url} ?"
    except Exception as e:
        return slots, str(e)
    return slots, None

@app.route('/api/files/pre-print-check', methods=['POST'])
@login_required
def api_pre_print_check():
    data = request.json or {}
    file_path = (data.get('path') or '').replace('\\', '/')
    printer_id = data.get('printer_id')
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400

    warnings = []
    user_id = session['user_id']

    try:
        analysis = get_cached_3d_analysis(file_path)
    except Exception:
        analysis = None
    if analysis and analysis.get('needs_repair'):
        warnings.append({
            "level": "warning",
            "code": "non_manifold",
            "message": "Maillage non-manifold détecté — le slicer devra le réparer automatiquement (résultat parfois imprévisible)."
        })

    if analysis and analysis.get('dimensions') and printer_id:
        try:
            conn = get_db()
            printer = conn.execute("SELECT config FROM printers WHERE id=? AND user_id=?", (printer_id, user_id)).fetchone()
            conn.close()
            bed = json.loads(printer["config"]) if printer and printer["config"] else {}
            bed_x = float(bed.get('bed_x') or 220)
            bed_y = float(bed.get('bed_y') or 220)
            bed_z = float(bed.get('bed_z') or 250)
            dims = sorted([analysis['dimensions']['x'], analysis['dimensions']['y']])
            bed_xy = sorted([bed_x, bed_y])
            if dims[0] > bed_xy[0] or dims[1] > bed_xy[1] or analysis['dimensions']['z'] > bed_z:
                warnings.append({
                    "level": "error",
                    "code": "oversized",
                    "message": f"Pièce ({analysis['dimensions']['x']}×{analysis['dimensions']['y']}×{analysis['dimensions']['z']} mm) plus grande que le plateau ({bed_x}×{bed_y}×{bed_z} mm)."
                })
        except Exception:
            pass

    try:
        required_g, _src = _get_required_weight_for_file(file_path)
        conn = get_db()
        row = conn.execute(
            "SELECT source_type, source_id FROM filament_assignments WHERE file_path=? AND user_id=?",
            (file_path, user_id)
        ).fetchone()
        conn.close()
        if row and required_g is not None:
            source_type, source_id = row[0], row[1]
            remaining = None
            slot_name = None
            if source_type == 'manual':
                conn = get_db()
                spool = conn.execute("SELECT name, remaining_g FROM manual_filament_spools WHERE id=? AND user_id=?", (source_id, user_id)).fetchone()
                conn.close()
                if spool:
                    remaining, slot_name = spool["remaining_g"], spool["name"]
            elif source_type == 'bambu_ams':
                for slot in _get_bambu_ams_slots(user_id):
                    if str(slot.get('source_id')) == str(source_id):
                        remaining, slot_name = slot.get('remaining_g'), slot.get('name')
                        break
            elif source_type == 'spoolman':
                settings = load_settings() or {}
                url = (settings.get('spoolman_url') or '').rstrip('/')
                spools, _err = _get_spoolman_slots(url)
                for slot in spools:
                    if str(slot.get('source_id')) == str(source_id):
                        remaining, slot_name = slot.get('remaining_g'), slot.get('name')
                        break
            if isinstance(remaining, (int, float)) and remaining < required_g:
                warnings.append({
                    "level": "error",
                    "code": "insufficient_filament",
                    "message": f"Filament assigné ({slot_name or '?'}) : {round(remaining,1)}g restants pour {round(required_g,1)}g nécessaires."
                })
    except Exception as e:
        app_logger.info(f"[PrePrintCheck] Vérif filament ignorée: {e}")

    return jsonify({"warnings": warnings}), 200


@app.route('/api/filament/compatibility', methods=['GET'])
@login_required
def api_filament_compatibility():
    file_path = (request.args.get('path') or '').strip()
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400
    norm_path = file_path.replace('\\', '/')

    url = (request.args.get('url') or '').strip().rstrip('/')
    if not url:
        try:
            settings = load_settings() or {}
            if settings.get('spoolman_url'):
                url = settings['spoolman_url'].rstrip('/')
        except Exception:
            pass

    required_g, weight_source = _get_required_weight_for_file(norm_path)

    all_slots = []
    errors = []
    spoolman_slots, spoolman_err = _get_spoolman_slots(url)
    all_slots.extend(spoolman_slots)
    if spoolman_err:
        errors.append(spoolman_err)
    all_slots.extend(_get_bambu_ams_slots(session['user_id']))
    all_slots.extend(_get_manual_filament_slots(session['user_id']))

    for slot in all_slots:
        remaining = slot.get('remaining_g')
        if required_g is not None and isinstance(remaining, (int, float)):
            slot['compatible'] = remaining >= required_g
        else:
            slot['compatible'] = None

    all_slots.sort(key=lambda s: (not s.get('compatible', False), s.get('remaining_g') is None, -(s.get('remaining_g') or 0)))

    assigned = None
    try:
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT source_type, source_id FROM filament_assignments WHERE file_path=? AND user_id=?",
                (norm_path, session['user_id'])
            ).fetchone()
        finally:
            conn.close()
        if row:
            assigned = {"source_type": row[0], "source_id": row[1]}
    except Exception:
        pass

    return jsonify({
        "required_weight_g": required_g,
        "weight_source": weight_source,
        "assigned": assigned,
        "slots": all_slots,
        "errors": errors
    }), 200

@app.route('/api/files/assign-filament', methods=['POST'])
@login_required
def api_assign_filament():
    data = request.json or {}
    file_path = (data.get('path') or '').strip()
    source_type = (data.get('source_type') or '').strip()
    source_id = str(data.get('source_id', '')).strip()
    if not file_path or not source_type or not source_id:
        return jsonify({"error": "Paramètres manquants"}), 400
    try:
        conn = get_db()
        conn.execute("""
            INSERT INTO filament_assignments (file_path, user_id, source_type, source_id, source_label, material, color_hex, spoolman_url, printer_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path, user_id) DO UPDATE SET
                source_type=excluded.source_type, source_id=excluded.source_id, source_label=excluded.source_label,
                material=excluded.material, color_hex=excluded.color_hex, spoolman_url=excluded.spoolman_url,
                printer_id=excluded.printer_id, assigned_at=CURRENT_TIMESTAMP
        """, (
            file_path.replace('\\', '/'), session['user_id'], source_type, source_id,
            (data.get('name') or '').strip(), (data.get('material') or '').strip(),
            (data.get('color_hex') or '').strip(), (data.get('spoolman_url') or '').strip(),
            data.get('printer_id')
        ))
        conn.commit()
        conn.close()
        if source_type == 'spoolman' and data.get('spoolman_url'):
            try:
                conn = get_db()
                conn.execute("""
                    INSERT INTO spool_assignments (file_path, user_id, spoolman_url, spool_id, spool_name, spool_material, spool_color_hex)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(file_path, user_id) DO UPDATE SET
                        spoolman_url=excluded.spoolman_url, spool_id=excluded.spool_id, spool_name=excluded.spool_name,
                        spool_material=excluded.spool_material, spool_color_hex=excluded.spool_color_hex, assigned_at=CURRENT_TIMESTAMP
                """, (
                    file_path.replace('\\', '/'), session['user_id'], data.get('spoolman_url').rstrip('/'),
                    int(source_id), (data.get('name') or '').strip(), (data.get('material') or '').strip(),
                    (data.get('color_hex') or '').strip()
                ))
                conn.commit()
                conn.close()
            except Exception:
                pass
        return jsonify({"success": True}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/files/filament-assignment', methods=['GET'])
@login_required
def api_get_filament_assignment():
    file_path = (request.args.get('path') or '').strip()
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400
    try:
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT source_type, source_id, source_label, material, color_hex, spoolman_url, printer_id FROM filament_assignments WHERE file_path=? AND user_id=?",
                (file_path.replace('\\', '/'), session['user_id'])
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return jsonify({"assignment": None}), 200
        return jsonify({"assignment": {
            "source_type": row[0], "source_id": row[1], "name": row[2],
            "material": row[3], "color_hex": row[4], "spoolman_url": row[5], "printer_id": row[6]
        }}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/files/unassign-filament', methods=['POST'])
@login_required
def api_unassign_filament():
    data = request.json or {}
    file_path = (data.get('path') or '').strip()
    if not file_path:
        return jsonify({"error": "Chemin requis"}), 400
    try:
        norm = file_path.replace('\\', '/')
        conn = get_db()
        try:
            conn.execute("DELETE FROM filament_assignments WHERE file_path=? AND user_id=?", (norm, session['user_id']))
            conn.execute("DELETE FROM spool_assignments WHERE file_path=? AND user_id=?", (norm, session['user_id']))
            conn.commit()
        finally:
            conn.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/filament/manual', methods=['GET'])
@login_required
def api_list_manual_spools():
    try:
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT id, name, material, color_hex, remaining_g, capacity_g, vendor, price, diameter_mm, notes, archived, storage_location "
                "FROM manual_filament_spools WHERE user_id=? ORDER BY archived ASC, created_at DESC",
                (session['user_id'],)
            ).fetchall()
        finally:
            conn.close()
        return jsonify([dict(r) for r in rows]), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/filament/manual', methods=['POST'])
@login_required
def api_create_manual_spool():
    data = request.json or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"error": "Nom requis"}), 400
    try:
        conn = get_db()
        try:
            cur = conn.execute("""
                INSERT INTO manual_filament_spools
                    (user_id, name, material, color_hex, remaining_g, capacity_g, source_label, vendor, price, diameter_mm, notes, storage_location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session['user_id'], name, (data.get('material') or '').strip(),
                (data.get('color_hex') or '#888888').strip(),
                data.get('remaining_g'), data.get('capacity_g') or 1000,
                (data.get('source_label') or 'Manuel').strip(),
                (data.get('vendor') or '').strip(),
                data.get('price') if data.get('price') not in ('', None) else None,
                data.get('diameter_mm') or 1.75,
                (data.get('notes') or '').strip(),
                (data.get('storage_location') or '').strip(),
            ))
            conn.commit()
            new_id = cur.lastrowid
        finally:
            conn.close()
        return jsonify({"success": True, "id": new_id}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/filament/manual/<int:spool_id>', methods=['PUT'])
@login_required
def api_update_manual_spool(spool_id):
    data = request.json or {}
    fields, params = [], []
    for key, col in (('name', 'name'), ('material', 'material'), ('color_hex', 'color_hex'),
                      ('remaining_g', 'remaining_g'), ('capacity_g', 'capacity_g'),
                      ('vendor', 'vendor'), ('price', 'price'), ('diameter_mm', 'diameter_mm'),
                      ('notes', 'notes'), ('archived', 'archived'),
                      ('storage_location', 'storage_location')):
        if key in data:
            fields.append(f"{col} = ?")
            params.append(data[key])
    if not fields:
        return jsonify({"error": "Rien à mettre à jour"}), 400
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.extend([spool_id, session['user_id']])
    try:
        conn = get_db()
        try:
            conn.execute(f"UPDATE manual_filament_spools SET {', '.join(fields)} WHERE id=? AND user_id=?", params)
            conn.commit()
        finally:
            conn.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

@app.route('/api/filament/manual/<int:spool_id>', methods=['DELETE'])
@login_required
def api_delete_manual_spool(spool_id):
    try:
        conn = get_db()
        try:
            conn.execute("DELETE FROM manual_filament_spools WHERE id=? AND user_id=?", (spool_id, session['user_id']))
            conn.commit()
        finally:
            conn.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        app_logger.error(f"[API] Erreur non gérée: {e}")
        return jsonify({"error": "Une erreur interne est survenue lors du traitement de la requête"}), 500

def _consume_filament_slot(source_type, source_id, weight_g, user_id):
    if source_type == 'spoolman':
        try:
            conn = get_db()
            row = conn.execute(
                "SELECT spoolman_url FROM filament_assignments WHERE source_type='spoolman' AND source_id=? AND user_id=? ORDER BY assigned_at DESC LIMIT 1",
                (str(source_id), user_id)
            ).fetchone()
            conn.close()
            if row and row[0]:
                return _consume_spool_filament(row[0], source_id, weight_g)
        except Exception as e:
            app_logger.warning(f"[FilamentBridge] Décrément Spoolman impossible: {e}")
        return False
    elif source_type == 'manual':
        try:
            conn = get_db()
            conn.execute(
                "UPDATE manual_filament_spools SET remaining_g = MAX(0, COALESCE(remaining_g, 0) - ?) WHERE id=? AND user_id=?",
                (weight_g, int(source_id), user_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            app_logger.warning(f"[FilamentBridge] Décrément bobine manuelle impossible: {e}")
            return False
    elif source_type == 'bambu_ams':
        app_logger.info(f"[FilamentBridge] AMS Bambu {source_id} : pas d'écriture de stock possible via l'API Bambu, décrément ignoré.")
        return False
    return False


def get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

@app.route('/manifest.json')
def pwa_manifest():
    ip = get_local_ip()
    port = 5000
    start_url = f'http://{ip}:{port}/'
    manifest = {
        "name": "Stellio 3D",
        "short_name": "Stellio",
        "description": "Gestionnaire de fichiers 3D",
        "start_url": start_url,
        "display": "standalone",
        "background_color": "#1a1d2e",
        "theme_color": "#1a1d2e",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": f"http://{ip}:{port}/assets/logo-stellio.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": f"http://{ip}:{port}/assets/logo-stellio.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    from flask import Response
    return Response(
        json.dumps(manifest, ensure_ascii=False),
        mimetype='application/manifest+json'
    )


_remote_lock = threading.Lock()
_remote_state = {
    "status": "disabled",
    "url": None,
    "error": None,
    "mode": "quick",
}
_remote_process = None
_ollama_process = None
_remote_generation = 0

REMOTE_CLOUDFLARED_DOWNLOAD_URLS = {
    "windows": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
    "linux": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
    "darwin": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz",
}

_REMOTE_URL_RE = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
_REMOTE_READY_HINTS = ("registered tunnel connection", "connection established")
_REMOTE_ERROR_HINTS = ("failed to parse token", "invalid tunnel", "unauthorized", "connection refused")


def get_remote_state():
    with _remote_lock:
        return dict(_remote_state)


def _set_remote_state(**kwargs):
    with _remote_lock:
        _remote_state.update(kwargs)


def _get_cloudflared_path(data_dir, logger=None):
    bin_dir = os.path.join(data_dir, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    exe_name = "cloudflared.exe" if os.name == "nt" else "cloudflared"
    exe_path = os.path.join(bin_dir, exe_name)

    if os.path.isfile(exe_path) and os.path.getsize(exe_path) > 1_000_000:
        return exe_path

    system = platform.system().lower()
    url = REMOTE_CLOUDFLARED_DOWNLOAD_URLS.get(system)
    if not url:
        raise RuntimeError(f"Plateforme non supportée pour l'accès distant : {system}")

    if logger:
        logger.info(f"[RemoteAccess] Téléchargement de cloudflared ({system})...")

    resp = requests.get(url, timeout=60, stream=True)
    resp.raise_for_status()
    tmp_path = exe_path + ".tmp"
    with open(tmp_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=262144):
            if chunk:
                f.write(chunk)
    os.replace(tmp_path, exe_path)
    if os.name != "nt":
        os.chmod(exe_path, 0o755)

    if logger:
        logger.info(f"[RemoteAccess] cloudflared prêt : {exe_path}")
    return exe_path


def start_remote_access(data_dir, local_port=5000, logger=None, token=None, fixed_url=None):
    global _remote_process, _remote_generation
    with _remote_lock:
        _remote_generation += 1
        my_generation = _remote_generation

    mode = "fixed" if token else "quick"
    _set_remote_state(status="starting", url=None, error=None, mode=mode)

    try:
        exe_path = _get_cloudflared_path(data_dir, logger)
    except Exception as e:
        _set_remote_state(status="error", error=str(e), mode=mode)
        if logger:
            logger.error(f"[RemoteAccess] Échec préparation cloudflared : {e}")
        return

    if mode == "fixed":
        cmd = [exe_path, "tunnel", "run", "--token", token]
    else:
        cmd = [exe_path, "tunnel", "--url", f"http://127.0.0.1:{local_port}", "--no-autoupdate"]

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )
        _remote_process = proc
    except Exception as e:
        _set_remote_state(status="error", error=str(e), mode=mode)
        if logger:
            logger.error(f"[RemoteAccess] Échec lancement cloudflared : {e}")
        return

    def _read_output():
        found = False
        try:
            for line in proc.stdout:
                with _remote_lock:
                    if my_generation != _remote_generation:
                        return
                if logger:
                    logger.info(f"[cloudflared] {line.strip()}")
                low = line.lower()

                if mode == "quick" and not found:
                    m = _REMOTE_URL_RE.search(line)
                    if m:
                        found = True
                        _set_remote_state(status="ready", url=m.group(0), error=None, mode=mode)
                        if logger:
                            logger.info(f"[RemoteAccess] ✅ URL publique : {m.group(0)}")

                elif mode == "fixed" and not found:
                    if any(hint in low for hint in _REMOTE_ERROR_HINTS):
                        found = True
                        _set_remote_state(status="error", error="Token Cloudflare invalide ou tunnel introuvable", mode=mode)
                        if logger:
                            logger.error("[RemoteAccess] ❌ Token/tunnel Cloudflare invalide")
                    elif any(hint in low for hint in _REMOTE_READY_HINTS):
                        found = True
                        _set_remote_state(status="ready", url=fixed_url, error=None, mode=mode)
                        if logger:
                            logger.info(f"[RemoteAccess] ✅ Tunnel fixe actif : {fixed_url}")
        except Exception:
            pass

        with _remote_lock:
            if my_generation != _remote_generation:
                return
        if not found:
            _set_remote_state(status="error", error="cloudflared s'est arrêté sans confirmer la connexion", mode=mode)

    threading.Thread(target=_read_output, daemon=True).start()

    if mode == "fixed":
        def _fallback_ready():
            time.sleep(12)
            with _remote_lock:
                if my_generation != _remote_generation:
                    return
                still_running = proc.poll() is None
                current_status = _remote_state["status"]
            if still_running and current_status == "starting":
                _set_remote_state(status="ready", url=fixed_url, error=None, mode=mode)
                if logger:
                    logger.info(f"[RemoteAccess] ✅ Tunnel fixe présumé actif : {fixed_url}")
        threading.Thread(target=_fallback_ready, daemon=True).start()


def restart_remote_access(data_dir, local_port=5000, logger=None, token=None, fixed_url=None):
    stop_remote_access()
    time.sleep(0.5)
    start_remote_access(data_dir, local_port=local_port, logger=logger, token=token, fixed_url=fixed_url)


def _kill_orphan_cloudflared(data_dir, logger=None):
    if os.name != "nt":
        return
    exe_path = os.path.join(data_dir, "bin", "cloudflared.exe")
    if not os.path.isfile(exe_path):
        return
    try:
        ps_cmd = (
            "Get-CimInstance Win32_Process -Filter \"Name='cloudflared.exe'\" | "
            f"Where-Object {{ $_.ExecutablePath -eq '{exe_path}' }} | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=10
        )
        if logger:
            logger.info("[RemoteAccess] Nettoyage des processus cloudflared orphelins de Stellio effectué")
    except Exception as e:
        if logger:
            logger.debug(f"[RemoteAccess] Nettoyage cloudflared orphelin ignoré: {e}")


def stop_remote_access():
    global _remote_process
    if _remote_process and _remote_process.poll() is None:
        try:
            _remote_process.terminate()
            try:
                _remote_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _remote_process.kill()
                _remote_process.wait(timeout=3)
        except Exception:
            pass
    _set_remote_state(status="disabled", url=None, error=None)


atexit.register(stop_remote_access)


@app.route('/api/qrcode', methods=['GET'])
@login_required
def api_qrcode():
    try:
        import qrcode
        import io, base64
        source = request.args.get('source', 'local')

        if source == 'remote':
            state = get_remote_state()
            if state['status'] != 'ready' or not state['url']:
                return jsonify({'error': "Accès distant non disponible pour le moment"}), 503
            url = state['url']
        else:
            ip = get_local_ip()
            port = 5000
            url = f'http://{ip}:{port}/'

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#1a1d2e', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode('utf-8')
        return jsonify({'qr_image': b64, 'url': url}), 200
    except ImportError:
        return jsonify({'error': "Module 'qrcode' manquant. Installez-le : pip install qrcode[pil]"}), 500
    except Exception as e:
        app_logger.error(f"[QRCode] Erreur: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/remote-access', methods=['GET'])
@login_required
def api_remote_access():
    state = get_remote_state()
    state['enabled'] = bool((load_settings() or {}).get('remote_access_enabled', False))
    return jsonify(state)


@app.route('/api/remote-access/toggle', methods=['POST'])
@login_required
def api_remote_access_toggle():
    data = request.json or {}
    enabled = bool(data.get('enabled'))

    current_settings = load_settings() or {}
    current_settings['remote_access_enabled'] = enabled
    save_settings(current_settings)

    if enabled:
        threading.Thread(
            target=start_remote_access,
            args=(DATA_DIR, SERVER_PORT, app_logger),
            kwargs={
                'token': current_settings.get('cloudflare_tunnel_token') or None,
                'fixed_url': current_settings.get('cloudflare_fixed_url') or None,
            },
            daemon=True
        ).start()
        return jsonify({"message": "Accès à distance activé, connexion en cours…", "enabled": True}), 200
    else:
        stop_remote_access()
        _set_remote_state(status="disabled", url=None, error=None, mode="quick")
        return jsonify({"message": "Accès à distance désactivé", "enabled": False}), 200


@app.route('/api/remote-access/configure', methods=['POST'])
@login_required
def api_remote_access_configure():
    data = request.json or {}
    token = (data.get('token') or '').strip()
    fixed_url = (data.get('url') or '').strip()

    if not token or not fixed_url:
        return jsonify({"error": "Le token et l'URL sont requis"}), 400
    if not fixed_url.startswith('http://') and not fixed_url.startswith('https://'):
        fixed_url = 'https://' + fixed_url

    current_settings = load_settings() or {}
    current_settings['cloudflare_tunnel_token'] = token
    current_settings['cloudflare_fixed_url'] = fixed_url
    save_settings(current_settings)

    threading.Thread(
        target=restart_remote_access,
        args=(DATA_DIR, 5000, app_logger),
        kwargs={'token': token, 'fixed_url': fixed_url},
        daemon=True
    ).start()

    return jsonify({"message": "Configuration enregistrée, connexion en cours…"}), 200


@app.route('/api/remote-access/disable-fixed', methods=['POST'])
@login_required
def api_remote_access_disable_fixed():
    current_settings = load_settings() or {}
    current_settings['cloudflare_tunnel_token'] = ''
    current_settings['cloudflare_fixed_url'] = ''
    save_settings(current_settings)

    threading.Thread(
        target=restart_remote_access,
        args=(DATA_DIR, 5000, app_logger),
        kwargs={'token': None, 'fixed_url': None},
        daemon=True
    ).start()

    return jsonify({"message": "Retour au mode rapide, connexion en cours…"}), 200


if __name__ in ('__main__', 'stellio_main'):
    import sys, os, threading, time, urllib.request, json

    STELLIO_HEADLESS = os.environ.get('STELLIO_HEADLESS', '').strip().lower() in ('1', 'true', 'yes')
    if not STELLIO_HEADLESS and sys.platform != 'win32' and not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
        STELLIO_HEADLESS = True

    STELLIO_START_MINIMIZED = (
        '--minimized' in sys.argv
        or os.environ.get('STELLIO_START_MINIMIZED', '').strip().lower() in ('1', 'true', 'yes')
    )

    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    SERVER_URL = os.environ.get('STELLIO_SERVER_URL', 'http://127.0.0.1:5000')
    SERVER_PORT = int(os.environ.get('STELLIO_PORT', '5000'))
    app_logger.info("[*] Démarrage Stellio...")

    def ensure_ollama_running():
        try:
            if requests.get('http://localhost:11434/api/tags', timeout=2).ok:
                app_logger.info("[Ollama] ✅ Service déjà actif")
                return
        except Exception:
            pass

        ollama_candidates = [
            os.path.join(os.environ.get('PROGRAMFILES', r'C:\Program Files'), 'Ollama', 'ollama.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Ollama', 'ollama.exe'),
            shutil.which('ollama') or '',
        ]
        ollama_exe = next((p for p in ollama_candidates if p and os.path.isfile(p)), None)

        if not ollama_exe:
            app_logger.info("[Ollama] ⚠️  Introuvable localement — tags IA désactivés (configurez 'ollama_url' dans les paramètres pour un serveur distant/conteneur)")
            return

        try:
            app_logger.info(f"[Ollama] 🚀 Démarrage : {ollama_exe}")
            global _ollama_process
            _ollama_process = subprocess.Popen(
                [ollama_exe, 'serve'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
            for _ in range(20):
                time.sleep(0.5)
                try:
                    if requests.get('http://localhost:11434/api/tags', timeout=1).ok:
                        app_logger.info("[Ollama] ✅ Service prêt")
                        return
                except Exception:
                    pass
            app_logger.info("[Ollama] ⚠️  Service démarré mais pas encore prêt")
        except Exception as e:
            app_logger.error(f"[Ollama] ❌ Erreur démarrage : {e}")

    def run_backend_startup(on_status=None):
        try:
            if on_status:
                on_status('database')
            process_generation_queue()
            process_slice_estimate_queue()
            threading.Thread(target=_auto_scan_scheduler, daemon=True).start()
            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, 'r', encoding='utf-8') as f: json.load(f)
                except Exception: invalidate_cache()

            _migrate_file_cache_schema()
            _backfill_multiplate_tags()

            threading.Thread(target=ensure_ollama_running, daemon=True).start()
            threading.Thread(target=lambda: _kill_orphan_cloudflared(DATA_DIR, app_logger), daemon=True).start()
            if on_status:
                on_status('server')

            def run_server():
                try:
                    from waitress import serve
                    serve(app, host='0.0.0.0', port=SERVER_PORT, threads=16, channel_timeout=300)
                except ImportError:
                    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False)
            threading.Thread(target=run_server, daemon=True).start()

            server_ready = False
            for _ in range(30):
                try:
                    urllib.request.urlopen(SERVER_URL, timeout=1)
                    server_ready = True
                    break
                except Exception:
                    time.sleep(0.5)

            if server_ready:
                if on_status:
                    on_status('thumbnails')

                def _background_library_prep():
                    try:
                        cached_count = 0
                        if os.path.exists(CACHE_FILE):
                            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                                cached_count = len(json.load(f).get('files', []))
                        if cached_count == 0:
                            conn_startup = get_db()
                            startup_sources = [dict(s) for s in conn_startup.execute("SELECT * FROM sources").fetchall()]
                            conn_startup.close()
                            if startup_sources:
                                app_logger.info("[STARTUP] Cache vide/absent avec des sources configurées — scan en arrière-plan...")
                                _do_background_scan(startup_sources, None, blocking=False)

                        recon = reconcile_thumbnails_with_disk()
                        if recon['total']:
                            app_logger.info(
                                f"[STARTUP] 📊 Fichiers: {recon['total']} — Miniatures présentes: {recon['with_thumb']} — "
                                f"Manquantes: {recon['without_thumb']} (dont {recon['requeued']} remises en génération)"
                            )

                        pregenerate_thumbnails_on_startup(limit=30)
                    except Exception as e:
                        app_logger.info(f"[STARTUP] Préparation bibliothèque (arrière-plan) ignorée: {e}")

                threading.Thread(target=_background_library_prep, daemon=True).start()

                if HAS_MQTT:
                    try:
                        conn_bambu = get_db()
                        bambu_printers = conn_bambu.execute("SELECT * FROM printers WHERE type = 'bambu'").fetchall()
                        conn_bambu.close()
                        for p in bambu_printers:
                            _ensure_bambu_connection(parse_printer_config(p))
                        if bambu_printers:
                            app_logger.info(f"[STARTUP] {len(bambu_printers)} connexion(s) MQTT Bambu persistante(s) démarrée(s)")
                    except Exception as e:
                        app_logger.info(f"[STARTUP] Démarrage connexions Bambu ignoré: {e}")

                if HAS_WEBSOCKET:
                    try:
                        conn_elg1 = get_db()
                        elegoo_sdcp_printers = conn_elg1.execute("SELECT * FROM printers WHERE type = 'elegoo_sdcp'").fetchall()
                        conn_elg1.close()
                        for p in elegoo_sdcp_printers:
                            _ensure_elegoo_sdcp_connection(parse_printer_config(p))
                        if elegoo_sdcp_printers:
                            app_logger.info(f"[STARTUP] {len(elegoo_sdcp_printers)} connexion(s) WebSocket Elegoo SDCP démarrée(s)")
                    except Exception as e:
                        app_logger.info(f"[STARTUP] Démarrage connexions Elegoo SDCP ignoré: {e}")

                if HAS_MQTT:
                    try:
                        conn_elg2 = get_db()
                        elegoo_cc2_printers = conn_elg2.execute("SELECT * FROM printers WHERE type = 'elegoo_cc2'").fetchall()
                        conn_elg2.close()
                        for p in elegoo_cc2_printers:
                            _ensure_elegoo_cc2_connection(parse_printer_config(p))
                        if elegoo_cc2_printers:
                            app_logger.info(f"[STARTUP] {len(elegoo_cc2_printers)} connexion(s) MQTT Elegoo CC2 démarrée(s)")
                    except Exception as e:
                        app_logger.info(f"[STARTUP] Démarrage connexions Elegoo CC2 ignoré: {e}")

                if HAS_WEBSOCKET:
                    try:
                        conn_crea = get_db()
                        creality_printers = conn_crea.execute("SELECT * FROM printers WHERE type = 'creality'").fetchall()
                        conn_crea.close()
                        for p in creality_printers:
                            _ensure_creality_connection(parse_printer_config(p))
                        if creality_printers:
                            app_logger.info(f"[STARTUP] {len(creality_printers)} connexion(s) WebSocket Creality démarrée(s)")
                    except Exception as e:
                        app_logger.info(f"[STARTUP] Démarrage connexions Creality ignoré: {e}")

                if HAS_FLASHFORGE:
                    try:
                        conn_ff = get_db()
                        flashforge_printers = conn_ff.execute("SELECT * FROM printers WHERE type = 'flashforge'").fetchall()
                        conn_ff.close()
                        for p in flashforge_printers:
                            _ensure_flashforge_connection(parse_printer_config(p))
                        if flashforge_printers:
                            app_logger.info(f"[STARTUP] {len(flashforge_printers)} connexion(s) FlashForge démarrée(s)")
                    except Exception as e:
                        app_logger.info(f"[STARTUP] Démarrage connexions FlashForge ignoré: {e}")

                _remote_settings = load_settings() or {}
                if _remote_settings.get('remote_access_enabled', False):
                    threading.Thread(
                        target=start_remote_access,
                        args=(DATA_DIR, SERVER_PORT, app_logger),
                        kwargs={
                            'token': _remote_settings.get('cloudflare_tunnel_token') or None,
                            'fixed_url': _remote_settings.get('cloudflare_fixed_url') or None,
                        },
                        daemon=True
                    ).start()
            return server_ready
        except Exception as e:
            app_logger.info(f"[Startup Error] Le démarrage a rencontré un problème: {e}")
            import traceback; traceback.print_exc()
            return False


    if STELLIO_HEADLESS:
        app_logger.info("[*] Mode headless détecté — pas d'interface graphique (Docker/serveur)")
        ready = run_backend_startup(on_status=lambda key: app_logger.info(f"[STARTUP] {key}..."))
        if ready:
            app_logger.info(f"[OK] ✅ Stellio est prêt et écoute sur {SERVER_URL}")
        else:
            app_logger.error("[ERREUR] ❌ Le serveur n'a pas démarré correctement, voir les logs ci-dessus")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            app_logger.info("[INFO] Arrêt propre.")


    else:
        import tkinter as tk
        from tkinter import ttk

        def load_splash_translations():
            lang = 'fr'
            try:
                if os.path.exists(SETTINGS_FILE):
                    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                    lang = settings.get('lang', 'fr')
            except:
                pass
            translations = {}
            lang_file = os.path.join(BASE_DIR, 'languages', f'{lang}.json')
            fallback_file = os.path.join(BASE_DIR, 'languages', 'fr.json')
            for file_path in [lang_file, fallback_file]:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            translations.update(json.load(f))
                        if file_path == lang_file:
                            break
                    except:
                        pass
            return {
                'init': translations.get('splash.init', 'Initialisation du moteur 3D...'),
                'database': translations.get('splash.database', 'Chargement de la base de données...'),
                'server': translations.get('splash.server', 'Démarrage du serveur web...'),
                'thumbnails': translations.get('splash.thumbnails', 'Préparation des miniatures 3D...'),
                'version': translations.get('splash.version', 'Version {version}')
            }

        SPLASH_TEXTS = load_splash_translations()
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.configure(bg='#1a1d23')
        width, height = 650, 500
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        root.geometry(f"{width}x{height}+{x}+{y}")
        logo_path = os.path.join(BASE_DIR, 'assets', 'logo-nom-stellio.png')
        if os.path.exists(logo_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(logo_path)
                photo = ImageTk.PhotoImage(img)
                lbl_logo = tk.Label(root, image=photo, bg='#1a1d23')
                lbl_logo.image = photo
                lbl_logo.pack(pady=(40, 10))
            except Exception as e:
                app_logger.info(f"[Splash] Erreur chargement logo: {e}")
        tk.Label(root, text=SPLASH_TEXTS['version'].format(version=CURRENT_VERSION),
                 font=("Segoe UI", 10), fg="#9ca3af", bg='#1a1d23').pack(pady=(5, 20))
        lbl_status = tk.Label(root, text=SPLASH_TEXTS['init'],
                              font=("Segoe UI", 11), fg="#e6e6e6", bg='#1a1d23')
        lbl_status.pack(pady=10)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor='#2a2f3a',
                        background='#4ea1d3',
                        thickness=8)
        progress = ttk.Progressbar(root, style="Custom.Horizontal.TProgressbar",
                                   mode='indeterminate', length=400)
        progress.pack(pady=15)
        progress.start(20)

        def heavy_backend_startup():
            def on_status(key):
                root.after(0, lambda: lbl_status.config(text=SPLASH_TEXTS[key]))
            ready = run_backend_startup(on_status=on_status)
            root.after(1500 if ready else 5000, root.destroy)

        threading.Thread(target=heavy_backend_startup, daemon=True).start()
        root.mainloop()
        app_logger.info("[OK] Splash fermé, lancement de l'interface principale...")
        try:
            import webview

            class StellioDesktopAPI:

                def save_backup(self, include=None):
                    try:
                        zip_bytes, suggested_name = build_backup_zip_bytes(include=include)
                    except Exception as e:
                        app_logger.error(f"[BACKUP] Échec génération pour Enregistrer sous : {e}")
                        return {"success": False, "error": str(e)}

                    try:
                        result = webview.windows[0].create_file_dialog(
                            webview.SAVE_DIALOG,
                            directory=str(Path.home() / 'Downloads'),
                            save_filename=suggested_name,
                            file_types=('Archive ZIP (*.zip)', 'Tous les fichiers (*.*)')
                        )
                    except Exception as e:
                        app_logger.error(f"[BACKUP] Échec ouverture boîte de dialogue : {e}")
                        return {"success": False, "error": str(e)}

                    if not result:
                        return {"success": False, "cancelled": True}

                    dest_path = result[0] if isinstance(result, (list, tuple)) else result
                    try:
                        with open(dest_path, 'wb') as f:
                            f.write(zip_bytes)
                        app_logger.info(f"[BACKUP] 📦 Sauvegarde enregistrée : {dest_path}")
                        return {"success": True, "path": dest_path}
                    except Exception as e:
                        app_logger.error(f"[BACKUP] Échec écriture fichier : {e}")
                        return {"success": False, "error": str(e)}

                def save_diagnostic_logs(self):
                    try:
                        zip_bytes, filename = build_diagnostic_zip_bytes()
                    except Exception as e:
                        app_logger.error(f"[LogsExport] Échec génération : {e}")
                        return {"success": False, "error": str(e)}

                    try:
                        downloads_dir = Path.home() / 'Downloads'
                        downloads_dir.mkdir(parents=True, exist_ok=True)

                        dest_path = downloads_dir / filename
                        counter = 1
                        stem, suffix = dest_path.stem, dest_path.suffix
                        while dest_path.exists():
                            dest_path = downloads_dir / f"{stem}_{counter}{suffix}"
                            counter += 1

                        with open(dest_path, 'wb') as f:
                            f.write(zip_bytes)
                        app_logger.info(f"[LogsExport] 📋 Logs exportés : {dest_path}")
                        return {"success": True, "path": str(dest_path)}
                    except Exception as e:
                        app_logger.error(f"[LogsExport] Échec écriture fichier : {e}")
                        return {"success": False, "error": str(e)}

            _window_kwargs = dict(
                width=1280,
                height=800,
                resizable=True,
                text_select=True,
                background_color='#1a1d23',
                min_size=(1024, 768),
                maximized=not STELLIO_START_MINIMIZED,
                confirm_close=True,
                js_api=StellioDesktopAPI()
            )
            try:
                window = webview.create_window('Stellio', SERVER_URL, **_window_kwargs)
            except TypeError as e:
                app_logger.warning(f"[INFO] pywebview ne supporte pas drag_drop ({e}) — fenêtre lancée sans glisser-déposer natif. Mets à jour pywebview (pip install -U pywebview) pour l'activer.")
                window = webview.create_window('Stellio', SERVER_URL, **_window_kwargs)
            _app_window = window

            def _on_window_closing():
                def _do_close():
                    try:
                        _cleanup_before_exit()
                    except Exception:
                        pass
                    os._exit(0)
                threading.Thread(target=_do_close, daemon=True).start()

            try:
                window.events.closing += _on_window_closing
            except Exception as ex:
                app_logger.info(f"[INFO] Binding closing event impossible: {ex}")

            if STELLIO_START_MINIMIZED:
                def _minimize_on_shown():
                    try:
                        window.minimize()
                        app_logger.info("[INFO] Démarrage en mode réduit")
                    except Exception as ex:
                        app_logger.info(f"[INFO] Minimisation au démarrage impossible: {ex}")
                try:
                    window.events.shown += _minimize_on_shown
                except Exception as ex:
                    app_logger.info(f"[INFO] Binding shown event impossible: {ex}")

            def _bind_drag_drop(win):
                try:
                    from webview.dom import DOMEventHandler
                except ImportError:
                    app_logger.info("[DragDrop] webview.dom indisponible (pywebview trop ancien) — glisser-déposer natif désactivé.")
                    return

                def on_drop(e):
                    try:
                        files = (e.get('dataTransfer') or {}).get('files') or []
                        paths = [f.get('pywebviewFullPath') for f in files if f.get('pywebviewFullPath')]
                        if not paths:
                            return
                        win.evaluate_js(
                            f"window.__stellioHandleDroppedPaths && window.__stellioHandleDroppedPaths({json.dumps(paths)})"
                        )
                    except Exception as ex:
                        app_logger.error(f"[DragDrop] Erreur traitement drop: {ex}")

                try:
                    win.dom.document.events.drop += DOMEventHandler(on_drop, True, True)
                except Exception as ex:
                    app_logger.info(f"[DragDrop] Binding impossible: {ex}")

            webview.start(_bind_drag_drop, window, debug=False, private_mode=False)
            app_logger.info("[INFO] Stellio s'est arrêté.")
        except Exception as e:
            app_logger.info(f"[WARN] PyWebView échec ({type(e).__name__}: {e})")
            app_logger.info("[INFO] Ouverture de secours dans le navigateur par défaut...")
            import webbrowser
            webbrowser.open(SERVER_URL)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                app_logger.info("\n[INFO] Arrêt propre.")