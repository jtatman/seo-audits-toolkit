from usp.tree import sitemap_tree_for_homepage

MAX_URLS = 2000


def extract_urls(url, max_urls=MAX_URLS):
    tree = sitemap_tree_for_homepage(url)

    urls = []
    for page in tree.all_pages():
        urls.append(
            {
                "url": page.url,
                "last_modified": page.last_modified.isoformat()
                if page.last_modified
                else None,
            }
        )
        if len(urls) >= max_urls:
            break

    return {"urls": urls, "total": len(urls)}
