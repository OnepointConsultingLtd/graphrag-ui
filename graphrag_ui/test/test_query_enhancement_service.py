from graphrag_ui.service.query_enhancement_service import (
    find_intent,
    find_intent_as_string,
    QueryMetadata,
)


def test_find_intent():
    intent_list = find_intent("I want to know the weather in Tokyo.")
    assert isinstance(intent_list, QueryMetadata)
    assert len(intent_list.intents) > 0
    assert "weather" in intent_list.intents[0].intent.lower()
    assert len(intent_list.keywords) > 0


def test_find_intent_as_string():
    intent_list_str = find_intent_as_string("Who was Albert Einstein?")
    assert isinstance(intent_list_str, str)
    assert len(intent_list_str) > 0
    assert "einstein" in intent_list_str.lower()
