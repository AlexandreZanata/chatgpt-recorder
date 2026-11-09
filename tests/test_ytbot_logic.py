import unittest
from datetime import date, datetime

from tools.ytbot import logic


META = """TITLE OPTIONS:

1. Why Your Mind Fears Silence — More Than You Realize
2. Second title
3. Third title

DESCRIPTION:

First paragraph with an em dash — like this.

#psychology #silence #mind #philosophy #neuroscience

TAGS: one, two, three, four
"""


class MetadataTests(unittest.TestCase):
    def test_title_has_no_em_dash(self):
        parsed = logic.parse_metadata(META)
        self.assertNotIn("—", parsed["title"])
        self.assertNotIn("–", parsed["title"])
        self.assertIn(":", parsed["title"])
        self.assertNotIn(" :", parsed["title"])

    def test_description_matches_channel_pattern(self):
        parsed = logic.parse_metadata(META)
        self.assertIn("#psychology", parsed["description"])
        self.assertIn("TAGS: one, two, three, four", parsed["description"])
        self.assertNotIn("—", parsed["description"])

    def test_tags_limit(self):
        parsed = logic.parse_metadata(META)
        self.assertLessEqual(len(parsed["tags"]), 425)


class ScheduleTests(unittest.TestCase):
    def test_existing_scheduled_times(self):
        payload = {"x": {"scheduledPublishingDetails": {"scheduledPublishings": [
            {"scheduledTimeSeconds": "1796227200"}]}}}
        slots = logic.scheduled_slots(payload)
        self.assertEqual(len(slots), 1)
        day, hour = next(iter(slots))
        self.assertEqual((day.month, day.day, hour), (12, 2, 12))

    def test_fills_missing_slot_and_skips_occupied(self):
        start = datetime(2026, 11, 9, 9, 0)
        occupied = {(date(2026, 11, 9), 12)}
        slots = logic.next_slots(3, occupied, start=start, lead_minutes=60)
        labels = [logic.slot_label(slot) for slot in slots]
        self.assertEqual(labels, ["2026-11-10 00:00", "2026-11-10 12:00", "2026-11-11 00:00"])

    def test_portuguese_date(self):
        self.assertEqual(logic.format_pt_date(date(2026, 12, 2)), "2 de dez. de 2026")


class TopicTests(unittest.TestCase):
    def test_similar_topic_detection(self):
        catalog = [{"title": "Why We Fall in Love With People Who Are Wrong for Us"}]
        self.assertTrue(logic.similar_topics("Why We Fall in Love With the Wrong Person", catalog))
        self.assertFalse(logic.similar_topics("The Mathematics of Loneliness", catalog))


if __name__ == "__main__":
    unittest.main()
