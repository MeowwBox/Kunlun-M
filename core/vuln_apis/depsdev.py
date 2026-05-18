import json
import time
import requests
from urllib.parse import quote

from utils.log import logger

__DEPSDEVAPIURL = "https://deps.dev/_/s/{ecosystem}/p/{package}/v/{version}/dependencies"
__DEPSDEVADVISORYURL = "https://deps.dev/_/advisory/{source}/{source_id}"
__SEVERITY_DICT = {
    "UNKNOWN": 1,
    "NONE": 1,
    "LOW": 3,
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
            logger.warning("[DepsDev API] 请求失败 (第{}次): {} {}".format(attempt + 1, url, str(e)))
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY)
    logger.error("[DepsDev API] 请求最终失败: {} {}".format(url, str(last_exc)))
    raise last_exc


def get_vulns_from_depsdev(ecosystem, package_name, version):
    result = []

    package_name = quote(package_name, safe='')
    url = __DEPSDEVAPIURL.format(ecosystem=ecosystem, package=package_name, version=version)

    try:
        resp = _request_with_retry("GET", url, timeout=8)
    except requests.exceptions.RequestException:
        return result

    if resp.status_code == 200:
        try:
            data = json.loads(resp.content)
        except (json.JSONDecodeError, ValueError):
            logger.warning("[DepsDev API] 响应解析失败")
            return result

        if "dependencies" in data.keys():
            for pack in data['dependencies']:
                if len(pack['advisories']) > 0:
                    for advisory in pack['advisories']:
                        vul = {"vuln_id": advisory["sourceID"], "title": advisory["title"],
                               "severity": __SEVERITY_DICT[advisory["severity"]],
                               "description": advisory["description"]}

                        if "CVEs" in advisory and advisory["CVEs"]:
                            cves = [cve for cve in advisory["CVEs"]]
                            vul["cves"] = json.dumps(cves)
                        vul["reference"] = advisory["sourceURL"]
                        # 获取全部影响版本
                        source = advisory["source"]
                        affected_versions = __get_affected_versions(package_name, source, vul["vuln_id"])
                        vul["affected_versions"] = affected_versions

                        result.append(vul)
    return result


def __get_affected_versions(package_name, source, source_id):
    result = []

    url = __DEPSDEVADVISORYURL.format(source=source, source_id=source_id)
    try:
        resp = _request_with_retry("GET", url)
    except requests.exceptions.RequestException:
        return result

    if resp.status_code == 200:
        try:
            data = json.loads(resp.content)
        except (json.JSONDecodeError, ValueError):
            logger.warning("[DepsDev API] Advisory 响应解析失败")
            return result

        for pkg in data.get("packages", []):
            if pkg["package"]["name"] != package_name:
                continue

            if len(pkg["versionsAffected"]) > 0:
                for version in pkg["versionsAffected"]:
                    result.append(version["version"])
    return result
