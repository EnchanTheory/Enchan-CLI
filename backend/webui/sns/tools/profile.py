def get_mascot_profile(broker) -> dict:
    mascot_id, mascot = broker._get_active_mascot_record()
    return {"mascot_id": mascot_id, "name": mascot.get("name", "AI"), "personality": mascot.get("personality", ""), "interests": mascot.get("interests", [])}
