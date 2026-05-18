import json
import requests
import time

from utils.log import logger

__OSV_QUERY_URL = "https://api.osv.dev/v1/query"
__OSV_QUERYBATCH_URL = "https://api.osv.dev/v1/querybatch"

__SEVERITY_DICT = {
    "UNKNOWN": 1,
    "NONE": 1,
    "LOW": 3,
    "MODERATE": 5,
    "MEDIUM": 5,
    "HIGH": 7,
    "CRITICAL": 10,
}

# 默认超时时间（秒）
_DEFAULT_TIMEOUT = 10
# 重试次数
_MAX_RETRIES = 2
# 重试间隔（秒）
_RETRY_DELAY = 1


def _request_with_retry(method, url, **kwargs):
    """带重试机制的 HTTP 请求封装，防止 API 调用失败导致扫描中断"""
    kwargs.setdefault("timeout", _DEFAULT_TIMEOUT)
    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            return requests.request(method, url, **kwargs)
        except requests.exceptions.RequestException as e:
            last_exc = e
            logger.warning("[OSV API] 请求失败 (第{}次): {} {}".format(attempt + 1, url, str(e)))
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY)
    logger.error("[OSV API] 请求最终失败: {} {}".format(url, str(last_exc)))
    raise last_exc


def _osv_severity_to_score(vuln):
    dbs = vuln.get("database_specific", {}) if isinstance(vuln, dict) else {}
    sev = dbs.get("severity")
    if isinstance(sev, str):
        return __SEVERITY_DICT.get(sev.upper(), 5)

    return 5


def _osv_references(vuln):
    refs = []
    for r in vuln.get("references", []) if isinstance(vuln, dict) else []:
        url = r.get("url")
        if url:
            refs.append(url)

    if not refs:
        return ""
    if len(refs) == 1:
        return refs[0]
    return json.dumps(refs)


def _osv_cves(vuln):
    aliases = vuln.get("aliases", []) if isinstance(vuln, dict) else []
    cves = [a for a in aliases if isinstance(a, str) and a.upper().startswith("CVE-")]
    return json.dumps(cves)


def _osv_to_vuln_dict(vuln, version):
    vuln_id = vuln.get("id", "")
    title = vuln.get("summary") or vuln_id
    description = vuln.get("details", "")

    return {
        "vuln_id": vuln_id,
        "title": title or "",
        "reference": _osv_references(vuln),
        "description": description or "",
        "cves": _osv_cves(vuln),
        "severity": _osv_severity_to_score(vuln),
        "affected_versions": [version],
    }


def query_osv_batch(ecosystem, items, timeout=_DEFAULT_TIMEOUT, chunk_size=100):
    result = {}
    items = [(n, v) for (n, v) in items if n and v]
    if not items:
        return result

    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        body = {
            "queries": [
                {
                    "package": {"ecosystem": ecosystem, "name": name},
                    "version": version
                } for (name, version) in chunk
            ]
        }

        try:
            resp = _request_with_retry("POST", __OSV_QUERYBATCH_URL, json=body, timeout=timeout)
        except requests.exceptions.RequestException:
            for k in chunk:
                result[k] = []
            continue

        if resp.status_code != 200:
            for k in chunk:
                result[k] = []
            continue

        try:
            data = json.loads(resp.content)
        except (json.JSONDecodeError, ValueError):
            logger.warning("[OSV API] 响应解析失败")
            for k in chunk:
                result[k] = []
            continue

        results = data.get("results", [])
        for (name, version), one in zip(chunk, results):
            vulns = []
            for v in one.get("vulns", []) if isinstance(one, dict) else []:
                if isinstance(v, dict):
                    vulns.append(_osv_to_vuln_dict(v, version))
            result[(name, version)] = vulns

    return result


def get_vulns_from_osv(ecosystem, package_name, version):
    r = query_osv_batch(ecosystem, [(package_name, version)], timeout=_DEFAULT_TIMEOUT, chunk_size=1)
    return r.get((package_name, version), [])


def query_osv_single(ecosystem, package_name, version, timeout=_DEFAULT_TIMEOUT):
    body = {"package": {"ecosystem": ecosystem, "name": package_name}, "version": version}

    try:
        resp = _request_with_retry("POST", __OSV_QUERY_URL, json=body, timeout=timeout)
    except requests.exceptions.RequestException:
        return []

    if resp.status_code != 200:
        return []

    try:
        data = json.loads(resp.content)
    except (json.JSONDecodeError, ValueError):
        return []

    vulns = []
    for v in data.get("vulns", []) if isinstance(data, dict) else []:
        if isinstance(v, dict):
            vulns.append(_osv_to_vuln_dict(v, version))
    return vulns
