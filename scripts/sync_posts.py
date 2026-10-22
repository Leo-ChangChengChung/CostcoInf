"""從今購百科「賣場目擊情報」抓最近文章，只留下正文圖片網址。"""

import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = (
    "https://www.daybuy.tw/wp-json/wp/v2/posts"
    "?categories=283&per_page=30&_fields=id,date,link,title,content"
)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "posts.json"
TAIPEI = timezone(timedelta(hours=8))
WEEK = "一二三四五六日"
SKIP = re.compile(r"logo|favicon|avatar|penci-icon|cropped-cropped|/themes/|/plugins/", re.I)
RESIZED = re.compile(r"-\d+x\d+(?=\.[A-Za-z]+$)")
IMG_SRC = re.compile(r"""<img\b[^>]*?\bsrc=["']([^"']+)["']""", re.I)

YEAR_THEN_RANGE = re.compile(
    r"(20\d{2})\s+(\d{1,2})[./](\d{1,2})\s*[（(]([一二三四五六日天])[)）]"
    r"\s*[~～\-–—]\s*"
    r"(\d{1,2})[./](\d{1,2})\s*[（(]([一二三四五六日天])[)）]"
)
RANGE_NO_YEAR = re.compile(
    r"(\d{1,2})[./](\d{1,2})\s*[（(]([一二三四五六日天])[)）]"
    r"\s*[~～\-–—]\s*"
    r"(\d{1,2})[./](\d{1,2})\s*[（(]([一二三四五六日天])[)）]"
)
FULL_RANGE = re.compile(
    r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})"
    r"\s*[~～\-–—]\s*"
    r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})"
)
FULL_SINGLE = re.compile(
    r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})"
    r"(?:\s*[（(]([一二三四五六日天])[)）]|\s*(週[一二三四五六日天]))?"
)
SHORT = re.compile(
    r"(?<!\d)(\d{1,2})[./](\d{1,2})\s*[（(]([一二三四五六日天])[)）]"
)


def fetch_posts():
    request = urllib.request.Request(
        API,
        headers={"User-Agent": "CostcoInf/1.0 (personal image reader)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if not isinstance(payload, list) or not payload:
        raise RuntimeError("API 沒有回傳文章")
    return payload


def plain_title(rendered):
    text = re.sub(r"<[^>]+>", "", rendered or "")
    return html.unescape(text).strip()


def weekday_name(day):
    if day == "天":
        day = "日"
    return "週" + day


def weekday_from_date(year, month, day):
    return "週" + WEEK[datetime(year, month, day).weekday()]


def iso_date(year, month, day):
    return f"{year:04d}-{month:02d}-{day:02d}"


def range_label(month1, day1, week1, month2, day2, week2):
    return (
        f"{month1}月{day1}日（{week1}）–{month2}月{day2}日（{week2}）"
    )


def single_label(month, day, week):
    return f"{month}月{day}日 {week}"


def date_label(title, published):
    """標題裡的賣場日期優先，沒有再改用文章發布日。"""
    match = YEAR_THEN_RANGE.search(title)
    if match:
        year, month1, day1, week1, month2, day2, week2 = match.groups()
        month1, day1, month2, day2 = map(int, (month1, day1, month2, day2))
        return (
            range_label(month1, day1, week1, month2, day2, week2),
            iso_date(int(year), month1, day1),
        )

    match = RANGE_NO_YEAR.search(title)
    if match:
        month1, day1, week1, month2, day2, week2 = match.groups()
        month1, day1, month2, day2 = map(int, (month1, day1, month2, day2))
        return (
            range_label(month1, day1, week1, month2, day2, week2),
            iso_date(published.year, month1, day1),
        )

    match = FULL_RANGE.search(title)
    if match:
        year1, month1, day1, _year2, month2, day2 = match.groups()
        year1, month1, day1, month2, day2 = map(int, (year1, month1, day1, month2, day2))
        label = f"{month1}月{day1}日–{month2}月{day2}日"
        return label, iso_date(year1, month1, day1)

    match = FULL_SINGLE.search(title)
    if match:
        year, month, day, paren, full = match.groups()
        year, month, day = int(year), int(month), int(day)
        if full:
            week = weekday_name(full[-1])
        elif paren:
            week = weekday_name(paren)
        else:
            week = weekday_from_date(year, month, day)
        return single_label(month, day, week), iso_date(year, month, day)

    match = SHORT.search(title)
    if match:
        month, day, paren = match.groups()
        month, day = int(month), int(day)
        return single_label(month, day, weekday_name(paren)), iso_date(published.year, month, day)

    return (
        single_label(published.month, published.day, weekday_from_date(published.year, published.month, published.day)),
        iso_date(published.year, published.month, published.day),
    )


def image_base(url):
    path = url.split("?", 1)[0]
    return RESIZED.sub("", path)


def extract_images(content_html):
    urls = []
    seen = set()
    for match in IMG_SRC.finditer(content_html or ""):
        url = html.unescape(match.group(1)).strip()
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith("http"):
            continue
        if SKIP.search(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)

    full_bases = {image_base(url) for url in urls if not RESIZED.search(url.split("?", 1)[0])}
    kept = []
    used = set()
    for url in urls:
        path = url.split("?", 1)[0]
        key = image_base(url)
        if RESIZED.search(path) and key in full_bases:
            continue
        if key in used:
            continue
        used.add(key)
        kept.append(url)
    return kept


def build_post(raw):
    title = plain_title(raw.get("title", {}).get("rendered", ""))
    published = datetime.strptime(raw["date"][:19], "%Y-%m-%dT%H:%M:%S")
    label, day = date_label(title, published)
    content = raw.get("content", {}).get("rendered", "")
    return {
        "id": raw["id"],
        "title": title,
        "date": day,
        "dateLabel": label,
        "link": raw.get("link", ""),
        "images": extract_images(content),
    }


def main():
    try:
        raw_posts = fetch_posts()
    except Exception as error:
        print(f"抓取失敗，保留舊資料：{error}", file=sys.stderr)
        return 1

    posts = [build_post(raw) for raw in raw_posts]
    fresh = json.dumps(posts, ensure_ascii=False, sort_keys=True)
    if OUT.exists():
        try:
            current = json.loads(OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = None
        if current and json.dumps(current.get("posts"), ensure_ascii=False, sort_keys=True) == fresh:
            print(f"內容沒變，{len(posts)} 篇")
            return 0

    payload = {
        "updated": datetime.now(TAIPEI).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "source": "https://www.daybuy.tw/costco/hypermarket-news/",
        "posts": posts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"寫入 {OUT} ，{len(posts)} 篇")
    for post in posts:
        print(f"{post['dateLabel']}  {len(post['images'])} 張  {post['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
