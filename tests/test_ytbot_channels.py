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
        self.assertEqual(config.MIN_ARTICLE_CHARS, 13000)
        self.assertEqual(config.PROMPTS.name, "whispers_from_heaven")

    def test_unknown_channel_fails(self):
        with self.assertRaises(SystemExit):
            channels.get("does-not-exist")

    def test_zaflas_uses_portuguese_and_the_confirmed_channel_identity(self):
        # Contract: the requested Zaflas profile targets this channel, in Portuguese.
        channel = channels.apply("zaflas")
        self.assertEqual(channel.language, "pt-BR")
        self.assertEqual(config.CHANNEL_NAME, "Zaflas")
        self.assertEqual(config.CHANNEL_ID, "UCi2aftoK7vlS3A6OozMHXKg")
        self.assertEqual(config.CHANNEL_HANDLE, "https://www.youtube.com/@zaflas/videos")

    def test_zaflas_isolates_assets_and_data(self):
        # Contract: use the existing agro background and keep other channels separate.
        channels.apply("zaflas")
        self.assertEqual(config.THUMBNAIL_THEME, "agro")
        self.assertEqual(config.PROMPTS.name, "zaflas_agro")
        self.assertEqual(config.DATA_DIR, config.DATA / "channels" / "zaflas")
        self.assertEqual(config.CATALOG.parent, config.DATA_DIR)
        self.assertEqual(config.TOPICS.parent, config.DATA_DIR)


if __name__ == "__main__":
    unittest.main()
