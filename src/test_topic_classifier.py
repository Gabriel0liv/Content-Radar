from types import SimpleNamespace

from src.services.topic_classifier import TopicClassifier


def make_item(**overrides):
    data = dict(
        youtube_category_name="Gaming",
        youtube_tags_json=[],
        youtube_topics_json=[],
        title="",
        description="",
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_minecraft_can_be_detected_without_minecraft_in_title():
    item = make_item(
        title="We should never have opened that door",
        youtube_tags_json=["SMP", "creeper", "redstone"],
        youtube_topics_json=["Gaming"],
    )

    results = TopicClassifier().classify_content_item(item)
    minecraft = next(result for result in results if result.topic == "Minecraft")

    assert minecraft.confidence >= 0.7
    assert any(signal.source == "youtube_tag" for signal in minecraft.signals)


def test_analog_horror_and_roleplay_can_coexist():
    item = make_item(
        youtube_tags_json=["analog horror", "roleplay", "smp"],
        description="A found-footage story told inside a server.",
    )

    names = {result.topic for result in TopicClassifier().classify_content_item(item)}
    assert "Analog Horror" in names
    assert "Roleplay" in names
    assert "SMP" in names


def test_single_incidental_minecraft_mention_is_not_high_confidence():
    item = make_item(
        title="Ten games that changed the industry",
        description="We briefly compare one mechanic to Minecraft before moving on.",
    )

    results = TopicClassifier().classify_content_item(item)
    minecraft = next((result for result in results if result.topic == "Minecraft"), None)

    assert minecraft is None or minecraft.confidence < 0.7
