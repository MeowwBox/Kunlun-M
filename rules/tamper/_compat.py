# -*- coding: utf-8 -*-
"""
Legacy tamper compatibility module.

Provides detection, scanning, and wrapping for old-format tamper files
that live directly under rules/tamper/ (pre-restructure flat layout).

Old format (Format 1 - framework tamper):
    wordpress = {"esc_url": [1000, 10001], ...}
    wordpress_controlled = []

This module wraps them to expose the same attributes as new-format modules
(FILTER_FUNCTIONS, CONTROLLED_SOURCES, EXTRA_SINKS, FRAMEWORK_NAME) so that
all downstream loaders can consume them uniformly.
"""

import os
import importlib
import importlib.util
import logging
import types

logger = logging.getLogger(__name__)

# SVID number ranges -> language identifier
SVID_LANG_MAP = [
    (5000, 5999, 'java'),
    (6000, 6999, 'javascript'),
    (7000, 7999, 'python'),
    (8000, 8999, 'go'),
    (9000, 9999, 'c'),
    (10000, 19999, 'php'),  # PHP vendor vulns (CVI 10001, 10002, etc.)
    (1000, 1999, 'php'),    # PHP core vulns
]

# Filenames that are NOT legacy tampers (infrastructure files)
_SKIP_FILES = frozenset({
    '__init__.py', '_loader.py', '_compat.py',
})


def _infer_language_from_svids(svids):
    """Infer language from svid number ranges."""
    for svid in svids:
        for lo, hi, lang in SVID_LANG_MAP:
            if lo <= svid <= hi:
                return lang
    return None


def _infer_language_from_controlled(controlled):
    """Infer language from controlled source patterns."""
    for src in controlled:
        src_lower = src.lower()
        if src.startswith('$_') or src.startswith('$HTTP_'):
            return 'php'
        if src.startswith('request.') or src.startswith('flask.'):
            return 'python'
        if 'r.' in src or src.startswith('c.Query') or src.startswith('c.Default'):
            return 'go'
        if 'System.' in src or src.startswith('req.'):
            return 'java'
        if 'req.' in src or src.startswith('ctx.') or src.startswith('app.'):
            return 'javascript'
    return None


def is_legacy_tamper_file(filepath):
    """
    Check whether a file looks like a legacy Format-1 tamper.

    Returns (is_legacy: bool, tamper_name: str|None).
    """
    fname = os.path.basename(filepath)
    if fname in _SKIP_FILES or fname.startswith('_') or not fname.endswith('.py'):
        return False, None

    # demo*.py files are Format-2 (base config), already replaced by _base.py
    stem = fname[:-3]
    if stem.startswith('demo'):
        return False, None

    # Try to load the module via spec to avoid package import conflicts
    try:
        spec = importlib.util.spec_from_file_location(
            '_legacy_tamper_{}'.format(stem), filepath)
        if spec is None or spec.loader is None:
            return False, None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        logger.debug("[TAMPER-COMPAT] Failed to load {}: {}".format(filepath, e))
        return False, None

    # Format 1 check: has <stem> dict attribute
    repair_attr = getattr(mod, stem, None)
    if isinstance(repair_attr, dict):
        return True, stem

    return False, None


def scan_legacy_tampers(tamper_dir):
    """
    Scan the root of rules/tamper/ for legacy-format files.

    Returns list of (module, tamper_name, inferred_language) tuples.
    """
    results = []
    if not os.path.isdir(tamper_dir):
        return results

    for fname in sorted(os.listdir(tamper_dir)):
        filepath = os.path.join(tamper_dir, fname)

        # Only consider root-level .py files (not in subdirectories)
        if not os.path.isfile(filepath) or not fname.endswith('.py'):
            continue
        if fname in _SKIP_FILES or fname.startswith('_'):
            continue
        # Skip language sub-package directories (not files)
        stem = fname[:-3]
        if stem.startswith('demo'):
            continue

        is_legacy, name = is_legacy_tamper_file(filepath)
        if not is_legacy:
            continue

        # Load the module
        try:
            spec = importlib.util.spec_from_file_location(
                '_legacy_tamper_{}'.format(name), filepath)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            logger.warning("[TAMPER-COMPAT] Failed to import legacy tamper {}: {}".format(name, e))
            continue

        # Infer language from svids
        repair_dict = getattr(mod, name, {})
        all_svids = []
        for svids in repair_dict.values():
            if isinstance(svids, (list, tuple)):
                all_svids.extend(svids)

        language = _infer_language_from_svids(all_svids)
        if not language:
            # Try from controlled list
            controlled = getattr(mod, name + '_controlled', [])
            language = _infer_language_from_controlled(controlled)
        if not language:
            language = 'php'  # all known legacy framework tampers are PHP

        logger.info("[TAMPER-COMPAT] Legacy tamper found: {} (language: {})".format(name, language))
        results.append((mod, name, language, filepath))

    return results


def wrap_legacy_module(mod, name, language, filepath):
    """
    Wrap a legacy tamper module into a new-format compatible object.

    The returned object has:
    - FRAMEWORK_NAME (str)
    - FILTER_FUNCTIONS (dict: func -> {'safe_for': [svids]})
    - CONTROLLED_SOURCES (list)
    - EXTRA_SINKS (list)
    - DEPENDENCIES (dict)
    - detect (None)
    """
    repair_dict = getattr(mod, name, {})
    controlled = getattr(mod, name + '_controlled', [])
    if not isinstance(controlled, list):
        controlled = []

    # Convert {func: [svids]} -> {func: {'safe_for': [svids]}}
    filter_functions = {}
    for func_name, svids in repair_dict.items():
        if isinstance(svids, list):
            filter_functions[func_name] = {'safe_for': svids}
        elif isinstance(svids, dict):
            filter_functions[func_name] = svids
        else:
            filter_functions[func_name] = {'safe_for': []}

    wrapped = types.SimpleNamespace(
        FRAMEWORK_NAME=name,
        FILTER_FUNCTIONS=filter_functions,
        CONTROLLED_SOURCES=controlled,
        EXTRA_SINKS=[],
        DEPENDENCIES={},
        detect=None,
        __file__=filepath,
        __name__='rules.tamper._legacy_{}'.format(name),
        _legacy_language=language,
    )
    return wrapped
