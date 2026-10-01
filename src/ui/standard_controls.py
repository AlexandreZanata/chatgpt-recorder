"""Optional subtitles and mutually exclusive particle checkboxes for Standard mode."""

from PySide6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWidget

from src.engine.standard_backgrounds import BACKGROUND_THEMES


def create_standard_controls(image_widget):
    """Keep custom images available whenever all particle themes are unchecked."""
    subtitles = QCheckBox("Include synchronized subtitles")
    subtitles.setChecked(True)
    subtitles.setToolTip("Transcribe narration and display subtitles in the video. Uncheck to skip.")
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    checks = {key: QCheckBox(label) for key, (label, _) in BACKGROUND_THEMES.items()}
    hint = QLabel("Select a particle theme. Shorts automatically uses its portrait background.")
    hint.setWordWrap(True)

    def on_selection(key, checked):
        if checked:
            for other, control in checks.items():
                if other != key:
                    control.setChecked(False)
        image_widget.setEnabled(not any(control.isChecked() for control in checks.values()))

    for key, check in checks.items():
        check.toggled.connect(lambda checked, key=key: on_selection(key, checked))
        layout.addWidget(check)
    layout.addWidget(hint)
    return subtitles, panel, checks


def selected_standard_theme(fields) -> str:
    """Return the single checked theme, or an empty string for a custom image."""
    return next((key for key, check in fields["background_checks"].items() if check.isChecked()), "")
