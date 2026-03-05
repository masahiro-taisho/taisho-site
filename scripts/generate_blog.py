from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ====== Settings ======
BASE = "/taisho-site"  # Project Pages の basePath。User Pagesなら "" にする
SITE_TITLE = "タイショーとは何者なのか"
SITE_TAGLINE = "渋くて、ゆるい。好きなものの置き場。"
LATEST_COUNT = 3
RELATED_COUNT = 3

ROOT = Path(__file__).resolve().parents[1]  # repo root
BLOG_DIR = ROOT / "blog"

STYLE_CSS = f"{BASE}/assets/style.css"
HEADER_HTML = f"{BASE}/header.html"
FOOTER_HTML = f"{BASE}/footer.html"

# カテゴリ表示名（必要に応じて増やしてOK）
CATEGORY_LABEL: Dict[str, str] = {
    "gadget": "ガジェット",
    "youtube": "YouTube",
    "gundam": "ガンダム",
    "diary": "日記",
    "movies": "映画／TV／映像作品",
    "books": "小説／漫画",
    "music": "音楽",
    "software": "ソフト",
}

# カテゴリの並び順（未定義カテゴリは後ろに回す）
# まずはタイショー指定：ガジェット → YouTube → ガンダム → 日記
CATEGORY_ORDER: List[str] = [
    "gadget",
    "youtube",
    "gundam",
    "diary",
    "movies",
    "music",
    "software",
    "books",
]

# 記事メタ（HTMLコメント）：
# <!--
# title: ...
# date: 2026-03-05
# category: gadget
# thumb: /taisho-site/assets/images/thumb/xxx.jpg
# excerpt: ...
# -->
META_RE = re.compile(r"^\s*<!--\s*(.*?)\s*-->\s*", re.DOTALL)
KV_RE = re.compile(r"^\s*([a-zA-Z0-9_-]+)\s*:\s*(.*?)\s*$")


@dataclass(frozen=True)
class Post:
    title: str
    date: str  # YYYY-MM-DD
    category: str
    thumb: str
    excerpt: str
    href: str  # /taisho-site/blog/<category>/<file>.html
    source_path: Path  # repo内の実ファイルパス


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_meta(html: str) -> Dict[str, str]:
    m = META_RE.match(html)
    if not m:
        return {}
    block = m.group(1)
    meta: Dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        km = KV_RE.match(line)
        if not km:
            continue
        key = km.group(1).strip().lower()
        val = km.group(2).strip()
        meta[key] = val
    return meta


def valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except Exception:
        return False


def category_label(cat: str) -> str:
    return CATEGORY_LABEL.get(cat, cat)


def sort_key(post: Post) -> Tuple[str, str]:
    # 新しい順
    return (post.date, post.title)


def ordered_categories(cats: List[str]) -> List[str]:
    s = set(cats)
    ordered = [c for c in CATEGORY_ORDER if c in s]
    rest = sorted([c for c in s if c not in set(CATEGORY_ORDER)])
    return ordered + rest


def discover_posts() -> List[Post]:
    posts: List[Post] = []
    if not BLOG_DIR.exists():
        return posts

    # blog/<category>/*.html を対象（index.html は除外）
    for html_path in BLOG_DIR.glob("*/*.html"):
        if html_path.name == "index.html":
            continue

        html = read_text(html_path)
        meta = parse_meta(html)

        # メタが無い記事はスキップ（sample等の混入を防ぐ）
        if not meta:
            continue

        # category は「フォルダ名」を優先（メタcategoryより強い）
        cat = html_path.parent.name

        title = meta.get("title", "").strip()
        date = meta.get("date", "").strip()
        thumb = meta.get("thumb", "").strip()
        excerpt = meta.get("excerpt", "").strip()

        # 最低限チェック
        if not title:
            print(f"[skip] title missing: {html_path}")
            continue
        if not date or not valid_date(date):
            print(f"[skip] invalid date: {html_path}  date={date!r}")
            continue
        if not thumb:
            thumb = f"{BASE}/assets/images/thumb/placeholder.jpg"
        if not excerpt:
            excerpt = "（本文より）"

        # href は basePath + 相対
        rel = html_path.relative_to(ROOT).as_posix()  # blog/xxx/yyy.html
        href = f"{BASE}/{rel}"

        posts.append(
            Post(
                title=title,
                date=date,
                category=cat,
                thumb=thumb,
                excerpt=excerpt,
                href=href,
                source_path=html_path,
            )
        )

    # 新しい順
    posts.sort(key=sort_key, reverse=True)
    return posts


def common_head(page_title: str) -> str:
    full = f"{page_title} | {SITE_TITLE}"
    return f"""\
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{full}</title>
<link rel="stylesheet" href="{STYLE_CSS}">
"""


def common_header_loader() -> str:
    return f"""\
<div id="site-header"></div>
<script>
fetch("{HEADER_HTML}")
  .then(r => r.text())
  .then(html => document.getElementById("site-header").innerHTML = html)
  .catch(() => {{}});
</script>
"""


def common_footer_loader() -> str:
    return f"""\
<div id="site-footer"></div>
<script>
fetch("{FOOTER_HTML}")
  .then(r => r.text())
  .then(html => document.getElementById("site-footer").innerHTML = html)
  .catch(() => {{}});
</script>
"""


def render_layout(page_title: str, main_html: str) -> str:
    return f"""\
<!doctype html>
<html lang="ja">
<head>
{common_head(page_title)}
</head>
<body>
{common_header_loader()}

<main class="container">
{main_html}
</main>

{common_footer_loader()}
</body>
</html>
"""


def render_category_sidebar(counts: Dict[str, int]) -> str:
    cats = ordered_categories(list(counts.keys()))
    items: List[str] = []
    for c in cats:
        label = category_label(c)
        n = counts.get(c, 0)
        href = f"{BASE}/blog/{c}/index.html"
        items.append(
            f'<li><a class="cat-link" href="{href}">{label}<span class="cat-count">({n})</span></a></li>'
        )
    return f"""\
<aside class="home-side">
  <div class="side-box">
    <h2 class="side-title">カテゴリ</h2>
    <ul class="cat-list">
      {''.join(items)}
    </ul>
  </div>
</aside>
"""


def render_post_cards(posts: List[Post]) -> str:
    cards: List[str] = []
    for p in posts:
        label = category_label(p.category)
        cards.append(
            f"""\
<article class="blog-card" data-category="{label}">
  <a href="{p.href}">
    <img src="{p.thumb}" alt="" loading="lazy" decoding="async">
    <div class="blog-card-body">
      <h2>{p.title}</h2>
      <p class="blog-meta">{p.date} / {label}</p>
      <p class="blog-excerpt">{p.excerpt}</p>
    </div>
  </a>
</article>
"""
        )
    return "\n".join(cards)


def build_root_index(posts: List[Post], counts: Dict[str, int]) -> str:
    latest = posts[:LATEST_COUNT]
    latest_cards: List[str] = []
    for p in latest:
        label = category_label(p.category)
        latest_cards.append(
            f"""\
<article class="home-card">
  <a class="home-card-link" href="{p.href}">
    <img class="home-thumb" src="{p.thumb}" alt="{p.title}" decoding="async" fetchpriority="high">
    <div class="home-card-body">
      <h2 class="home-card-title">{p.title}</h2>
      <p class="home-meta">{p.date} / {label}</p>
      <p class="home-excerpt">{p.excerpt}</p>
    </div>
  </a>
</article>
"""
        )

    main = f"""\
<section class="home-hero">
  <div class="home-hero-inner">
    <p class="home-kicker">{SITE_TITLE}</p>
    <h1 class="home-title">{SITE_TAGLINE}</h1>
    <p class="home-lead">映画、音楽、ガジェット、YouTube、AI。思いついたら書く。合わない人はそっと閉じてOK。</p>
    <p class="home-cta"><a class="btn" href="{BASE}/blog/index.html">ブログ一覧へ</a></p>
  </div>
</section>

<section class="home-grid">
  <div class="home-main">
    <h2 class="section-title">最新記事</h2>
    {''.join(latest_cards)}
  </div>

  {render_category_sidebar(counts)}
</section>
"""
    return render_layout("トップ", main)


def build_blog_index(posts: List[Post], counts: Dict[str, int]) -> str:
    main = f"""\
<section class="blog-hero">
  <div class="blog-hero-inner">
    <h1 class="page-title">ブログ一覧</h1>
    <p class="page-lead">新しい順。カテゴリ別にも見れる。</p>
  </div>
</section>

<section class="home-grid">
  <div class="home-main">
    {render_post_cards(posts)}
  </div>

  {render_category_sidebar(counts)}
</section>
"""
    return render_layout("ブログ一覧", main)


def build_category_index(category: str, posts: List[Post], counts: Dict[str, int]) -> str:
    label = category_label(category)
    main = f"""\
<section class="blog-hero">
  <div class="blog-hero-inner">
    <h1 class="page-title">{label}</h1>
    <p class="page-lead">カテゴリ「{label}」の記事一覧。</p>
    <p class="page-lead"><a class="text-link" href="{BASE}/blog/index.html">← ブログ一覧へ戻る</a></p>
  </div>
</section>

<section class="home-grid">
  <div class="home-main">
    {render_post_cards(posts)}
  </div>

  {render_category_sidebar(counts)}
</section>
"""
    return render_layout(label, main)


# ====== Related posts insertion ======
RELATED_START = "<!-- related posts:start -->"
RELATED_END = "<!-- related posts:end -->"
RELATED_MARKER = "<!-- related posts -->"


def build_related_section(current: Post, all_posts: List[Post], limit: int = RELATED_COUNT) -> str:
    # 同カテゴリから自分以外を新しい順で抽出
    related = [p for p in all_posts if p.category == current.category and p.href != current.href]
    related = related[:limit]
    if not related:
        return ""

    return f"""\
<section class="related-posts">
  <h2 class="section-title">関連記事</h2>
  <div class="blog-grid related-grid">
    {render_post_cards(related)}
  </div>
</section>
"""


def upsert_related_into_post(html: str, related_html: str) -> str:
    # すでに start/end があるなら、その中身を差し替える
    if RELATED_START in html and RELATED_END in html:
        pre, rest = html.split(RELATED_START, 1)
        _, post = rest.split(RELATED_END, 1)
        return pre + RELATED_START + "\n" + related_html + "\n" + RELATED_END + post

    # marker があるなら、start/end に昇格させて差し込む
    if RELATED_MARKER in html:
        block = f"{RELATED_START}\n{related_html}\n{RELATED_END}"
        return html.replace(RELATED_MARKER, block)

    # 何もなければ触らない
    return html


def main() -> None:
    posts = discover_posts()

    # カウント
    counts: Dict[str, int] = {}
    for p in posts:
        counts[p.category] = counts.get(p.category, 0) + 1

    # 生成：トップ / ブログ一覧
    write_text(ROOT / "index.html", build_root_index(posts, counts))
    write_text(BLOG_DIR / "index.html", build_blog_index(posts, counts))

    # 生成：カテゴリ一覧
    for cat in ordered_categories(list(counts.keys())):
        cat_posts = [p for p in posts if p.category == cat]
        write_text(BLOG_DIR / cat / "index.html", build_category_index(cat, cat_posts, counts))

    # 生成：関連記事を各記事へ差し込み（markerがある記事だけ）
    for p in posts:
        html = read_text(p.source_path)
        related_html = build_related_section(p, posts, limit=RELATED_COUNT)
        new_html = upsert_related_into_post(html, related_html)
        if new_html != html:
            write_text(p.source_path, new_html)

    print("[ok] generated:")
    print(f" - {ROOT / 'index.html'}")
    print(f" - {BLOG_DIR / 'index.html'}")
    for cat in ordered_categories(list(counts.keys())):
        print(f" - {BLOG_DIR / cat / 'index.html'}")
    print(" - related posts inserted (only files with marker/start-end)")


if __name__ == "__main__":
    main()