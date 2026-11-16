from pathlib import Path
import hashlib
import os
import subprocess
import tempfile
import unittest

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE
if not (ROOT / "toolbox/helpers/install-scraper-assets.sh").exists() and not (ROOT / "install-scraper-assets.sh").exists():
    ROOT = HERE.parent
HELPER = ROOT / "toolbox/helpers/install-scraper-assets.sh"
if not HELPER.exists():
    HELPER = ROOT / "install-scraper-assets.sh"


class ScraperAssetsTests(unittest.TestCase):
    def test_media_roles_and_legacy_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "assets"
            src.mkdir()
            for name, color in (("screenshot.jpg", "red"), ("box2d.jpg", "blue"),
                                ("fanart.jpg", "green"), ("logo.png", "white")):
                fmt = "PNG" if name.endswith(".png") else "JPEG"
                Image.new("RGB", (24, 32), color).save(src / name, fmt)

            ports = base / "ports"
            ports.mkdir()
            state = base / "state"
            backups = base / "backups"
            legacy_rel = "media/images/umu-runner-toolbox.png"
            legacy_file = ports / legacy_rel
            legacy_file.parent.mkdir(parents=True)
            legacy_file.write_bytes(b"managed old box art")
            old_hash = hashlib.sha256(legacy_file.read_bytes()).hexdigest()
            (state / "scraper-assets.sha256").parent.mkdir(parents=True)
            (state / "scraper-assets.sha256").write_text(f"{old_hash} {legacy_rel}\n")
            (ports / "gamelist.xml").write_text(
                '<?xml version="1.0"?><gameList><game><path>./UMU Runner Toolbox.sh</path>'
                '<image>./media/images/umu-runner-toolbox.png</image>'
                '<boxart>./media/box2d/umu-runner-toolbox.png</boxart>'
                '<thumbnail>./media/thumbnails/umu-runner-toolbox.png</thumbnail>'
                '</game></gameList>', encoding="utf-8")

            env = dict(os.environ, SCRAPER_PORTS_DIR=str(ports),
                       SCRAPER_ES_RUNNING="0", SCRAPER_ES_URL="http://127.0.0.1:1")
            subprocess.run(["bash", str(HELPER), str(src), "umu-runner-toolbox",
                            "UMU Runner Toolbox.sh", "UMU Runner Toolbox", "desc fr",
                            "desc en", str(state), str(backups)], check=True, env=env,
                           capture_output=True, text=True)

            self.assertFalse(legacy_file.exists())
            xml = (ports / "gamelist.xml").read_text(encoding="utf-8")
            self.assertIn("./media/images/umu-runner-toolbox.jpg", xml)
            self.assertIn("./media/box2d/umu-runner-toolbox.jpg", xml)
            self.assertIn("./media/thumbnails/umu-runner-toolbox.jpg", xml)
            self.assertIn("./media/fanarts/umu-runner-toolbox.jpg", xml)
            self.assertIn("./media/marquee/umu-runner-toolbox.png", xml)
            self.assertEqual((ports / "media/box2d/umu-runner-toolbox.jpg").read_bytes(),
                             (ports / "media/thumbnails/umu-runner-toolbox.jpg").read_bytes())


if __name__ == "__main__":
    unittest.main()
