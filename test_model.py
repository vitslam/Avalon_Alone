#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最小 OpenAI Chat Completions 兼容请求：火山方舟 base_url + .env 中的 API_KEY / MODEL。"""

import json
import os
import sys
from pathlib import Path

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://ark.cn-beijing.volces.com/api/plan/v3"


def _load_dotenv(path):
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, val)


def main():
    _load_dotenv(Path(__file__).resolve().parent / ".env")
    api_key = os.environ.get("API_KEY")
    model = os.environ.get("MODEL")
    if not api_key:
        sys.exit("缺少 API_KEY：请在 .env 中设置 API_KEY=...")
    if not model:
        sys.exit("缺少 MODEL：请在 .env 中设置 MODEL=<推理接入点 Endpoint ID>")

    url = BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "请问你是什么模型？"},
        ],
        "max_tokens": 256,
    }
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as e:
        sys.stderr.write(e.read().decode("utf-8", errors="replace") + "\n")
        raise SystemExit(e.code)
    except URLError as e:
        raise SystemExit("请求失败: %s" % e.reason)

    obj = json.loads(body)
    try:
        print(obj["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        print(body)


if __name__ == "__main__":
    main()
