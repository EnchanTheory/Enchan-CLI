def get_social_context(broker) -> dict:
    return {"following": broker.get_following(), "followers": broker.get_followers()}
