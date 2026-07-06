#!/usr/bin/env python3
"""
bio-news-educator → bio-keywords 자동 동기화 스크립트
새로 생성된 기사를 분류 페이지(index.html)에 반영합니다.
"""

import re
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from datetime import date as dt_date

BASE_URL = "https://bio1ta0920-coder.github.io/bio-news-educator/"
INDEX_FILE = Path(__file__).parent / "index.html"

CATEGORY_MAP = {
    "암·종양학": "oncology",
    "신약개발·제약": "drug",
    "유전자편집·유전자치료": "gene",
    "유전자편집·치료": "gene",
    "생식과 유전": "gene",
    "재생의학·줄기세포": "regen",
    "면역학·면역치료": "immuno",
    "신경과학": "neuro",
    "감염병·백신": "infect",
    "생태학·환경과학": "ecology",
    "생태학·환경": "ecology",
    "합성생물학·AI생물정보학": "synbio",
    "합성생물학·AI생물정보": "synbio",
    "합성생물학·AI": "synbio",
    "통합과학2 - '과학과 미래' 단원": "synbio",
    "RNA치료제": "rna",
    "RNA 치료제": "rna",
    "내분비·대사질환": "endo",
    "영양학·대사": "nutrition",
    "진화·고생물학": "evo",
    "의료정책·규제": "policy",
    "세포생물학·이미징": "cellbio",
    "세포와 물질대사: 세포의 특성": "cellbio",
    "세포와 물질대사": "cellbio",
}

BADGE_COLORS = {
    "oncology": "#c62828",
    "drug":     "#1565c0",
    "gene":     "#6a1b9a",
    "regen":    "#e65100",
    "immuno":   "#2e7d32",
    "neuro":    "#37474f",
    "infect":   "#00695c",
    "ecology":  "#33691e",
    "synbio":   "#5c6bc0",
    "rna":      "#880e4f",
    "endo":     "#f57f17",
    "nutrition":"#558b2f",
    "evo":      "#4e342e",
    "policy":   "#455a64",
    "cellbio":  "#00838f",
}

SECTION_NAMES = {
    "oncology": "암·종양학",
    "drug":     "신약개발·제약",
    "gene":     "유전자편집·유전자치료",
    "regen":    "재생의학·줄기세포",
    "immuno":   "면역학·면역치료",
    "neuro":    "신경과학",
    "infect":   "감염병·백신",
    "ecology":  "생태학·환경과학",
    "synbio":   "합성생물학·AI 생물정보학",
    "rna":      "RNA 치료제",
    "endo":     "내분비·대사질환",
    "nutrition":"영양학·대사",
    "evo":      "진화·고생물학",
    "policy":   "의료정책·규제",
    "cellbio":  "세포생물학·이미징",
}


def fetch_html(url):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"[ERROR] {url}: {e}", file=sys.stderr)
        return None


def get_existing_urls(index_html):
    pattern = r'href="(https://bio1ta0920-coder\.github\.io/bio-news-educator/\d{4}-\d{2}-\d{2}-\d+\.html)"'
    return set(re.findall(pattern, index_html))


def get_available_dates():
    html = fetch_html(BASE_URL)
    if not html:
        return []
    return sorted(set(re.findall(r'href="(\d{4}-\d{2}-\d{2})\.html"', html)))


MAX_TITLE_LEN = 100


def clean_title(title):
    """소스 목록 페이지가 제목 대신 본문 문단을 통째로 넣어두는 경우가 있어,
    지나치게 긴 텍스트는 첫 문장(또는 적당한 길이) 선에서 잘라낸다."""
    title = title.strip()
    if len(title) <= MAX_TITLE_LEN:
        return title
    first_sentence = re.split(r"(?<=[.!?다])\s", title)[0]
    if len(first_sentence) <= MAX_TITLE_LEN:
        return first_sentence
    return title[:MAX_TITLE_LEN].rsplit(" ", 1)[0] + "…"


def get_articles_for_date(date):
    html = fetch_html(f"{BASE_URL}{date}.html")
    if not html:
        return []

    articles = []
    for li in re.findall(r'<li[^>]*>(.*?)</li>', html, re.DOTALL):
        link_m = re.search(r'href="(\d{4}-\d{2}-\d{2}-\d+\.html)"', li)
        title_m = re.search(r'<a [^>]*>(.*?)</a>', li, re.DOTALL)
        cat_m   = re.search(r'<span[^>]*>([^<]+)</span>', li)
        if link_m and title_m:
            raw_title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip()
            articles.append({
                "url":      BASE_URL + link_m.group(1),
                "title":    clean_title(raw_title),
                "category": cat_m.group(1).strip() if cat_m else "",
                "date":     date,
            })
    return articles


def get_article_details(url):
    html = fetch_html(url)
    if not html:
        return "", []

    # 핵심 요약: '기사 요약' 섹션의 첫 번째 <p>
    summary = ""
    m = re.search(r'기사 요약[\s\S]*?<div[^>]*font-size[^>]*>([\s\S]*?)</div>', html)
    if m:
        p = re.search(r'<p>([\s\S]*?)</p>', m.group(1))
        if p:
            summary = re.sub(r"<[^>]+>", "", p.group(1)).strip()
            if len(summary) > 210:
                summary = summary[:210].rsplit(" ", 1)[0] + "…"

    # 핵심 개념어에서 태그 추출 (괄호 앞 한국어 용어만)
    tags = []
    km = re.search(r'핵심 개념어([\s\S]*?)(?:탐구 질문|윤리 쟁점|실제 산업|미래 전망)', html)
    if km:
        for term in re.findall(r'<strong>([^<(（]+?)(?:\(|（|</strong>)', km.group(1)):
            term = term.strip()
            if term and len(term) < 20:
                tags.append(term)
            if len(tags) >= 4:
                break

    return summary, tags


def make_card(article, summary, tags, section_id):
    color = BADGE_COLORS.get(section_id, "#37474f")
    name  = SECTION_NAMES.get(section_id, "")
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in tags)
    return (
        f'    <div class="card">\n'
        f'      <span class="date-badge">{article["date"]}</span>\n'
        f'      <span class="cat-badge" style="font-size:0.68rem;color:#fff;background:{color};'
        f'display:inline-block;padding:2px 8px;border-radius:12px;width:fit-content;">{name}</span>\n'
        f'      <a class="title" href="{article["url"]}">{article["title"]}</a>\n'
        f'      <p class="summary">{summary}</p>\n'
        f'      <div class="tags">{tags_html}</div>\n'
        f'    </div>'
    )


def add_card_to_section(html, section_id, card_html):
    pattern = rf'(<section id="{section_id}"[\s\S]*?<div class="cards">)([\s\S]*?)(\n  </div>\n</section>)'
    def replacer(m):
        return m.group(1) + m.group(2) + "\n\n" + card_html + m.group(3)
    return re.sub(pattern, replacer, html)


def sort_all_sections(html):
    def sort_cards(m):
        block = m.group(0)
        cards = re.findall(r'    <div class="card">[\s\S]*?    </div>', block)
        if not cards:
            return block
        def date_key(c):
            d = re.search(r'date-badge">(\d{4}-\d{2}-\d{2})<', c)
            return d.group(1) if d else "0000-00-00"
        return "\n\n" + "\n\n".join(sorted(cards, key=date_key, reverse=True)) + "\n\n"
    return re.sub(r'(?<=<div class="cards">)([\s\S]*?)(?=\n  </div>\n</section>)', sort_cards, html)


def update_counts(html):
    for sid in SECTION_NAMES:
        m = re.search(rf'<section id="{sid}"([\s\S]*?)</section>', html)
        if not m:
            continue
        count = len(re.findall(r'<div class="card">', m.group(1)))
        html = re.sub(
            rf'(<section id="{sid}"[\s\S]*?<span class="count">\()(\d+건)(\)</span>)',
            lambda mo, c=count: mo.group(1) + f'{c}건' + mo.group(3),
            html,
        )
    return html


def update_footer_date(html):
    today = dt_date.today()
    date_str = f"{today.year}년 {today.month}월 {today.day}일"
    return re.sub(r'최종 업데이트: \d{4}년 \d+월 \d+일', f'최종 업데이트: {date_str}', html)


def main():
    index_html = INDEX_FILE.read_text(encoding="utf-8")
    existing = get_existing_urls(index_html)

    all_dates = get_available_dates()
    if not all_dates:
        print("날짜 목록을 가져올 수 없습니다.")
        sys.exit(1)

    new_count = 0
    for date in all_dates:
        for article in get_articles_for_date(date):
            if article["url"] in existing:
                continue

            section_id = CATEGORY_MAP.get(article["category"])
            if not section_id:
                print(f"[SKIP] 알 수 없는 분류 '{article['category']}': {article['url']}")
                continue

            print(f"[ADD] {article['date']} [{article['category']}] {article['title']}")
            summary, tags = get_article_details(article["url"])
            if not summary:
                print(f"  [WARN] 요약 추출 실패, 건너뜀")
                continue

            card = make_card(article, summary, tags, section_id)
            index_html = add_card_to_section(index_html, section_id, card)
            existing.add(article["url"])
            new_count += 1

    if new_count == 0:
        print("추가할 새 기사 없음.")
        return

    index_html = sort_all_sections(index_html)
    index_html = update_counts(index_html)
    index_html = update_footer_date(index_html)

    INDEX_FILE.write_text(index_html, encoding="utf-8")
    print(f"완료: {new_count}건 추가됨.")


if __name__ == "__main__":
    main()
