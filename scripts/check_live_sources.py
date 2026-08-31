#!/usr/bin/env python3
"""Check the public V3 source entry points used by live smoke tests."""

from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone


SOURCES = [
    ("北京大学迎新网", "https://fresh.pku.edu.cn/"),
    ("本科新生服务平台", "https://apply.pku.edu.cn/freshman/login"),
    ("教务部", "https://dean.pku.edu.cn/"),
    ("教务部信息下载", "https://dean.pku.edu.cn/web/download.php"),
    ("教务部学生服务", "https://dean.pku.edu.cn/web/student.php"),
    ("学生管理信息公开", "https://xxgk.pku.edu.cn/gksx/xsgl/xjgl/index.htm"),
    ("北京大学图书馆", "https://www.lib.pku.edu.cn/index.htm"),
    ("图书馆空间布局", "https://www.lib.pku.edu.cn/3wxbz/index.htm"),
    ("北京大学总务部", "https://zwb.pku.edu.cn/"),
    ("北京大学餐饮中心", "https://cyzx.pku.edu.cn/"),
    ("北京大学医院", "https://hospital.pku.edu.cn/"),
    ("北京大学保卫部", "https://www.bwb.pku.edu.cn/"),
    ("北京大学学生资助中心", "https://www.sfao.pku.edu.cn/"),
    ("北京大学计算中心", "https://cc.pku.edu.cn/"),
    ("正版软件说明", "https://its.pku.edu.cn/download_software.jsp"),
]


def check(name: str, url: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": "pku-freshman-navigator-source-check/3.0"})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=12, context=context) as response:
            return {"name": name, "url": url, "status": response.status, "ok": 200 <= response.status < 400}
    except urllib.error.HTTPError as exc:
        return {"name": name, "url": url, "status": exc.code, "ok": 200 <= exc.code < 400}
    except Exception as exc:  # Network failures must be visible, not fatal to report generation.
        return {"name": name, "url": url, "status": None, "ok": False, "error": type(exc).__name__}


def main() -> int:
    results = [check(name, url) for name, url in SOURCES]
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "passed": sum(bool(item["ok"]) for item in results),
        "total": len(results),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
