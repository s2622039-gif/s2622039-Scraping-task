import csv
import time
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# 設定項目
BASE_URL = "https://www.musashino-u.ac.jp/"
DOMAIN = urlparse(BASE_URL).netloc.lower()
SLEEP_TIME = 1.0  # サーバー負荷軽減用の待機時間（秒）
OUTPUT_CSV = "site_map.csv"
MAX_PAGES = 200

# 巡回済みURLの管理用セットと結果格納用辞書
visited_urls = set()
site_data = {}  # key: URL, value: title


def normalize_url(url):
    """重複や断片識別子を含むURLを正規化して比較しやすくする"""
    if not url:
        return ""

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""

    # URL中の断片識別子は無視し、ホスト名は小文字化して比較対象を揃える
    normalized = parsed._replace(fragment="", netloc=parsed.netloc.lower())
    return normalized.geturl().rstrip("/") or normalized.geturl()


def is_same_domain(url):
    """対象URLが同一ドメイン内かどうかを判定する"""
    parsed = urlparse(url)
    return parsed.netloc.lower() == DOMAIN


def scrape_site(start_url):
    """同一ドメイン内のURLを非再帰的に巡回してタイトルを取得する"""
    queue = deque([start_url])
    session = requests.Session()

    while queue:
        url = queue.popleft()
        normalized_url = normalize_url(url)
        if not normalized_url or normalized_url in visited_urls:
            continue
        if not is_same_domain(normalized_url):
            continue

        visited_urls.add(normalized_url)

        # 相手サーバーへの負荷軽減のために必ずsleepを実行
        time.sleep(SLEEP_TIME)

        try:
            response = session.get(normalized_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code >= 400:
                continue

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                continue

            response.encoding = response.apparent_encoding or "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
            site_data[normalized_url] = title
            print(f"取得成功: {normalized_url} -> {title}")

            if len(site_data) >= MAX_PAGES:
                break

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if href.startswith(("javascript:", "mailto:", "tel:")):
                    continue

                next_url = urljoin(normalized_url, href)
                parsed = urlparse(next_url)
                if parsed.scheme not in ("http", "https"):
                    continue

                next_url = normalize_url(next_url.split("#", 1)[0])
                if next_url and next_url not in visited_urls:
                    queue.append(next_url)

        except requests.RequestException as exc:
            print(f"エラー発生 ({normalized_url}): {exc}")
        except Exception as exc:
            print(f"エラー発生 ({normalized_url}): {exc}")


def save_to_csv(data, filename):
    """辞書型変数をCSVファイルに保存する関数"""
    with open(filename, mode="w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["URL", "Title"])
        for url, title in data.items():
            writer.writerow([url, title])


if __name__ == "__main__":
    print("スクレイピングを開始します...")
    scrape_site(BASE_URL)

    print(f"取得完了。計 {len(site_data)} 件のデータをCSVに保存します...")
    save_to_csv(site_data, OUTPUT_CSV)
    print(f"保存完了: {OUTPUT_CSV}")