"""Schedule a video from the YouTube upload dialog."""

from __future__ import annotations

import json

from . import logic


def answer_audience(page) -> None:
    radio = page.locator('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]')
    if not radio.count():
        return
    for _ in range(3):
        try:
            radio.first.click(force=True)
        except Exception:
            pass
        page.wait_for_timeout(700)
        checked = page.evaluate(
            "()=>document.querySelector('tp-yt-paper-radio-button[name=\"VIDEO_MADE_FOR_KIDS_NOT_MFK\"]')?.hasAttribute('checked')")
        if checked:
            return
    raise RuntimeError("could not answer the audience question")


def _show_visibility(page) -> None:
    page.evaluate("()=>{const b=document.querySelector('#step-badge-3'); if(b)b.click()}")
    page.wait_for_timeout(2500)
    for _ in range(3):
        if page.locator("#datepicker-trigger").is_visible():
            return
        button = page.locator("#next-button")
        if button.count() and button.first.is_visible() and button.first.get_attribute("aria-disabled") != "true":
            button.first.click()
        page.wait_for_timeout(2500)


def schedule_in_dialog(page, slot) -> None:
    answer_audience(page)
    _show_visibility(page)
    if not page.locator("#datepicker-trigger").is_visible():
        page.evaluate("()=>{const b=document.querySelector('#second-container-expand-button'); if(b)b.click()}")
        page.wait_for_timeout(1500)
    page.evaluate("()=>{const b=document.querySelector('#datepicker-trigger'); if(b)b.click()}")
    page.wait_for_timeout(1200)
    date_input = page.locator("ytcp-date-picker input")
    date_input.first.fill(logic.format_pt_date(slot.date()))
    date_input.first.press("Enter")
    page.wait_for_timeout(1000)
    time_input = page.locator("#time-of-day-container input")
    time_input.first.fill(slot.strftime("%H:%M"))
    time_input.first.press("Enter")
    page.wait_for_timeout(1200)
    model = page.evaluate(
        "()=>document.querySelector('#publish-from-private-non-sponsor-selector')?.getAttribute('model')")
    if not model:
        raise RuntimeError("schedule model was not created")
    parsed = json.loads(model)
    expected = {"year": slot.year, "month": slot.month - 1, "day": slot.day}
    if parsed.get("date") != expected or parsed.get("selectedTimeOfDayValue") != slot.hour * 3600:
        raise RuntimeError(f"schedule model mismatch: {model}")
    page.evaluate("()=>{const b=document.querySelector('#done-button'); if(b)b.click()}")
    page.wait_for_timeout(8000)


def fill_editable(page, index: int, text: str) -> None:
    page.evaluate("(i)=>{const e=document.querySelectorAll('#textbox')[i]; if(e)e.focus()}", index)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.keyboard.insert_text(text)
    page.wait_for_timeout(350)


def ensure_title(page, title: str) -> None:
    for _ in range(3):
        current = page.evaluate("()=>document.querySelectorAll('#textbox')[0]?.innerText || ''")
        if current.strip() == title.strip():
            return
        fill_editable(page, 0, title)
        page.wait_for_timeout(800)
    raise RuntimeError("YouTube overwrote the video title")
