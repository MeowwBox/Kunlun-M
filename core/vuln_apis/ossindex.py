import json
import time
import requests

from utils.log import logger

__OSSINDEXAPI = "https://ossindex.sonatype.org/api/v3/component-report"

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
            logger.warning("[OSSIndex API] 请求失败 (第{}次): {} {}".format(attempt + 1, url, str(e)))
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY)
    logger.error("[OSSIndex API] 请求最终失败: {} {}".format(url, str(last_exc)))
    raise last_exc


def get_vulns_from_ossindex_batch(ecosystem, items, timeout=_DEFAULT_TIMEOUT, chunk_size=100):
    result = {}
    items = [(n, v) for (n, v) in items if n and v]
    if not items:
        return result

    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        coordinates = [
            "pkg:{ecosystem}/{package}@{version}".format(ecosystem=ecosystem, package=package_name, version=version)
            for (package_name, version) in chunk
        ]
        body = {"coordinates": coordinates}

        try:
            resp = _request_with_retry("POST", __OSSINDEXAPI, json=body, timeout=timeout)
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
            logger.warning("[OSSIndex API] 响应解析失败")
            for k in chunk:
                result[k] = []
            continue

        for comp, (package_name, version) in zip(data, chunk):
            vulns = []
            for advisorie in comp.get("vulnerabilities", []) if isinstance(comp, dict) else []:
                vuln = {}
                vuln["vuln_id"] = advisorie.get("displayName", "")
                vuln["title"] = advisorie.get("title", "")
                vuln["reference"] = advisorie.get("reference", "")
                vuln["description"] = advisorie.get("description", "")

                cves = []
                cve = advisorie.get("cve", "")
                if cve:
                    cves.append(cve)
                vuln["cves"] = json.dumps(cves)

                cvss3_score = advisorie.get("cvssScore", -1.0)
                try:
                    vuln["severity"] = int(float(cvss3_score))
                except Exception:
                    vuln["severity"] = 5

                vuln["affected_versions"] = [version]
                vulns.append(vuln)

            result[(package_name, version)] = vulns

    return result


def get_vulns_from_ossindex(ecosystem, package_name, version):
    r = get_vulns_from_ossindex_batch(ecosystem, [(package_name, version)], timeout=_DEFAULT_TIMEOUT, chunk_size=1)
    return r.get((package_name, version), [])
