#!/usr/bin/env python3
"""Build a small, separate Chrome extension without touching the Firefox manifest."""

import json
import shutil
import zipfile
from pathlib import Path


def build_chrome(root: Path) -> Path:
    target = root / 'dist' / 'chrome'
    target.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / 'manifest.chrome.json').read_text())
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    sources = [*sorted((root / 'src' / 'chrome').glob('*.js')),
               *sorted((root / 'src' / 'chrome').glob('*.html')),
               root / 'src' / 'shared' / 'constants.js', root / 'src' / 'popup.js',
               *sorted((root / 'icons').glob('icon-*.png'))]
    for source in sources:
        destination = target / source.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    popup = (root / 'popup.html').read_text()
    popup = popup.replace('<script src="src/popup.js"',
                          '<script src="src/chrome/browser-api.js"></script>\n'
                          '  <script type="module" src="src/chrome/recorder-popup.js"></script>\n'
                          '  <script src="src/popup.js"')
    (target / 'popup.html').write_text(popup)
    shutil.copy2(root / 'docs' / 'CHROME-EXTENSION.md', target / 'README.md')
    archive = root / 'dist' / f'chatgpt-audio-capture-chrome-v{manifest["version"]}.zip'
    packaged = ['manifest.json', 'popup.html', 'README.md']
    packaged += [str(source.relative_to(root)) for source in sources]
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
        for name in packaged:
            package.write(target / name, name)
    print(f'[chrome-build] Load unpacked folder: {target}')
    print(f'[chrome-build] Archive: {archive}')
    return target


if __name__ == '__main__':
    build_chrome(Path(__file__).resolve().parent.parent)
