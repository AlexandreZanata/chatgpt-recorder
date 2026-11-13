import unittest

from tools.ytbot import channels, config


class ChannelProfileTests(unittest.TestCase):
    def tearDown(self):
        channels.apply("fallem-prince")

    def test_every_profile_has_prompts(self):
        for channel in channels.CHANNELS.values():
            for name in ("article_header.txt", "metadata.txt", "thumbnail.txt", "topics.txt"):
                path = config.PROMPTS_ROOT / channel.prompts / name
                self.assertTrue(path.is_file(), path)

    def test_whispers_profile(self):
        channels.apply("whispers-from-heaven")
        self.assertEqual(config.CHANNEL_NAME, "Whispers From Heaven")
        self.assertEqual(config.THUMBNAIL_THEME, "whispers_from_heaven")
        self.assertEqual(config.MIN_ARTICLE_CHARS, 11000)
        self.assertEqual(config.PROMPTS.name, "whispers_from_heaven")

    def test_unknown_channel_fails(self):
        with self.assertRaises(SystemExit):
            channels.get("does-not-exist")


if __name__ == "__main__":
    unittest.main()
