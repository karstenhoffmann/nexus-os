"""Category normalization rules for documents."""

# Map plural forms (from Export API) to singular
PLURAL_TO_SINGULAR = {
    "articles": "article",
    "podcasts": "podcast",
    "tweets": "tweet",
    "books": "book",
}


def normalize_category(category: str | None, url: str | None = None) -> str:
    """Normalize category to singular lowercase, apply URL-based rules.

    Rules (in order):
    1. LinkedIn: URL contains 'linkedin.com' -> 'linkedin'
    2. Lowercase and strip whitespace
    3. Plural -> singular (articles -> article, tweets -> tweet)
    4. Default: 'article' for None/empty

    Args:
        category: Raw category from Readwise API
        url: Original URL for synthetic category detection

    Returns:
        Normalized category string
    """
    # LinkedIn rule takes priority (synthetic category based on URL)
    if url and "linkedin.com" in url.lower():
        return "linkedin"

    if not category:
        return "article"

    cat = category.strip().lower()
    return PLURAL_TO_SINGULAR.get(cat, cat)
