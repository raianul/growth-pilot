def test_parse_intent_budget():
    from app.services.discover import parse_intent_from_response
    raw = '{"cuisine": null, "budget_max_bdt": 1000, "party_size": 2, "vibe": "dine-in", "area": null, "keywords": ["dine in"]}'
    intent = parse_intent_from_response(raw)
    assert intent["budget_max_bdt"] == 1000
    assert intent["party_size"] == 2

def test_parse_intent_cuisine():
    from app.services.discover import parse_intent_from_response
    raw = '{"cuisine": "burger", "budget_max_bdt": null, "party_size": null, "vibe": null, "area": "Uttara", "keywords": ["burger", "best"]}'
    intent = parse_intent_from_response(raw)
    assert intent["cuisine"] == "burger"
    assert intent["area"] == "Uttara"

def test_parse_intent_malformed():
    from app.services.discover import parse_intent_from_response
    raw = "not json at all"
    intent = parse_intent_from_response(raw)
    assert intent == {}

def test_area_to_postcodes():
    from app.services.discover import _area_to_postcodes
    assert _area_to_postcodes("Uttara") == ["1230"]
    assert _area_to_postcodes("dhanmondi") == ["1205", "1209"]
    assert _area_to_postcodes(None) == []
    assert _area_to_postcodes("Unknown") == []

def test_nearby_postcodes():
    from app.services.discover import _nearby_postcodes
    nearby = _nearby_postcodes("Uttara")
    assert "1213" in nearby  # Banani
    assert "1216" in nearby  # Mirpur
    assert _nearby_postcodes(None) == []
