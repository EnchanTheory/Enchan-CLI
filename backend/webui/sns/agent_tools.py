"""SNS-scoped tool implementations. These are not added to global agent_tools."""
from .tools.context import get_current_context
from .tools.history import get_own_tweet_history


def execute_sns_tool(name: str, args: dict, broker):
    if name == "sns_get_own_tweet_history":
        return {"tool": name, "ok": True, "observation": get_own_tweet_history(broker, int(args.get("max_posts", 30)), int(args.get("token_budget", 6000)))}
    if name == "sns_get_current_context":
        return {"tool": name, "ok": True, "observation": get_current_context()}
    if name == "sns_get_regional_trends":
        from .tools.rss_news import get_top_news
        result = get_top_news(limit=5, locale=args.get("locale"))
        return {"tool": name, "ok": bool(result.get("ok")), "observation": result}
    return {"tool": name, "ok": False, "observation": f"Unknown SNS tool: {name}"}
