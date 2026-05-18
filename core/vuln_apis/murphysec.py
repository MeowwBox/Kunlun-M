#!/usr/bin/env python
# encoding: utf-8
"""
@author: LoRexxar
@contact: lorexxar@gmail.com
@file: mofei.py
@time: 2021/9/27 11:47
@desc:

"""

import json
import time
import requests

from Kunlun_M.settings import MURPHYSEC_TOKEN
from utils.log import logger

__MURPHYSECAPI = "https://api.murphysec.com/cert/v1/check"
__MURPHYSECVULAPI = "https://api.murphysec.com/cert/v1/latest"

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
            logger.warning("[Murphysec API] 请求失败 (第{}次): {} {}".format(attempt + 1, url, str(e)))
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY)
    logger.error("[Murphysec API] 请求最终失败: {} {}".format(url, str(last_exc)))
    raise last_exc


def get_vulns_from_murphysec(language, package_name, version):
    datas = {
        "comp_name": package_name,
        "version": version,
        "language": language,
        "filter":{
            "level": "严重|高危"
        }
    }

    headers = {
        "Authorization": "Bearer {}".format(MURPHYSEC_TOKEN),
        "Content-Type": "application/json"
    }
    result = []

    try:
        r = _request_with_retry("POST", url=__MURPHYSECAPI, headers=headers, data=json.dumps(datas))
    except requests.exceptions.RequestException:
        return result

    if r.status_code == 200:
        try:
            data = json.loads(r.content)
        except (json.JSONDecodeError, ValueError):
            logger.warning("[Murphysec API] 响应解析失败")
            return result

        if data.get("code") == 400:
            logger.warning("[Vendor][Murphysec Scan] QPS limit.")
            return result

        elif data.get("code") == 401:
            logger.error("[Vendor][Murphysec Scan] Api Token error.")
            return result

        vuls = data.get("data", {}).get("vuln_info", [])

        for vul in vuls:
            vuln = {}
            vuln["vuln_id"] = vul["no"]
            vuln["title"] = vul["title"]
            # reference
            urls = []
            for u in vul.get("references", []):
                urls.append(u["url"])

            vuln["reference"] = json.dumps(urls)
            vuln["description"] = """{}

受影响的版本范围: {}
存在危害的相关代码片段:\n {}
""".format(vul.get("description", ""), vul.get("effect", [{}])[0].get("affected_version", ""), vul.get("vuln_code_usage", ""))

            # get cve
            cves = [vul.get("cve_id", ""), vul.get("cnvd_id", "")]
            vuln["cves"] = json.dumps(cves)
            # get severity

            # 如果非强烈建议修复，则减3分
            severity = int(vul.get("cvss", 5))
            if vul.get("suggest") != "强烈建议修复":
                severity -= 3

            vuln["severity"] = severity

            # affected_versions
            vuln["affected_versions"] = [version]

            result.append(vuln)

    return result
