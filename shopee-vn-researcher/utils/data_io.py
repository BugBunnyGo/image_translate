"""
数据读写工具
"""
import json
import csv
import os
from datetime import datetime
from typing import Any


RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def save_json(data: list[dict], filename: str):
    ensure_results_dir()
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  -> 已保存 {len(data)} 条数据到 {path}")


def load_json(filename: str) -> list[dict]:
    path = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_csv(data: list[dict], filename: str):
    if not data:
        print(f"  -> 无数据可保存到 {filename}")
        return
    ensure_results_dir()
    path = os.path.join(RESULTS_DIR, filename)
    fieldnames = list(data[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"  -> 已保存 {len(data)} 条数据到 {path}")


def save_markdown(content: str, filename: str):
    ensure_results_dir()
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  -> 已生成报告 {path}")
