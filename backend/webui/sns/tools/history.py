def get_own_tweet_history(broker, max_posts: int = 30, token_budget: int = 6000) -> list[dict]:
    """Return only this mascot's dated, like-counted history for self-review."""
    return broker.get_self_review_history(max_posts=max_posts, token_budget=token_budget)
