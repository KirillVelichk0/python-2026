import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, UTC
import os
from typing import List, Optional, Tuple
import re

BASE_URL = "https://www.ngdc.noaa.gov/dscovr/data"

def list_files(url: str) -> List[str]:
    resp = requests.get(url, timeout=10)

    if resp.status_code != 200:
        raise RuntimeError(f"{url} -> {resp.status_code}")

    soup = BeautifulSoup(resp.text, "html.parser")

    files: List[str] = []

    for link in soup.find_all("a"):
        href = link.get("href")

        if isinstance(href, str) and href.endswith(".nc.gz"):
            files.append(href)

    return files


def download_file(url: str, out_dir: str) -> None:
    filename = url.split("/")[-1]
    path = os.path.join(out_dir, filename)

    if os.path.exists(path):
        print(f"[SKIP] {filename}")
        return

    print(f"[DOWN] {filename}")

    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()

        with open(path, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)


def extract_publish_datetime(name: str) -> Optional[datetime]:
    """
    Извлекаем pYYYYMMDDHHMMSS
    """
    m = re.search(r"p(20\d{12})", name)
    if not m:
        return None

    return datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=UTC)

def find_latest_month(max_lookback: int = 6) -> List[Tuple[int, int]]:
    """
    Возвращаем список доступных месяцев (свежие → старые)
    """
    today = datetime.now(UTC)

    months = []

    for i in range(max_lookback):
        dt = today - timedelta(days=30 * i)

        url = f"{BASE_URL}/{dt:%Y/%m}/"
        print(f"[CHECK] {url}")

        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                print(f"[OK] {dt:%Y-%m}")
                months.append((dt.year, dt.month))
        except Exception:
            pass

    if not months:
        raise RuntimeError("No available months found")

    return months


def collect_latest_files(limit_days: int = 7) -> List[Tuple[str, str]]:
    """
    Собираем файлы за последние доступные дни
    """
    months = find_latest_month()

    all_files: List[Tuple[str, datetime]] = []

    for year, month in months:
        base = f"{BASE_URL}/{year:04d}/{month:02d}/"
        print(f"[SCAN] {base}")

        try:
            files = list_files(base)
        except Exception:
            continue

        for f in files:
            dt = extract_publish_datetime(f)
            if dt:
                all_files.append((base + f, dt))

    if not all_files:
        raise RuntimeError("No files found")

    # сортируем по дате публикации (новые сверху)
    all_files.sort(key=lambda x: x[1], reverse=True)

    # выбираем последние N уникальных дней
    selected: List[Tuple[str, str]] = []
    seen_days = set()

    for url, dt in all_files:
        day = dt.strftime("%Y%m%d")

        if day not in seen_days:
            seen_days.add(day)
            selected.append((url, day))

        if len(seen_days) >= limit_days:
            break

    return selected


def download_last_available_week(out_dir: str = "data") -> None:
    os.makedirs(out_dir, exist_ok=True)

    selected = collect_latest_files(limit_days=7)

    print("\n[SELECTED DAYS]")
    for _, d in selected:
        print(d)

    print()

    for url, _ in selected:
        download_file(url, out_dir)


if __name__ == "__main__":
    download_last_available_week()
