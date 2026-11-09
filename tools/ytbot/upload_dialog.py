"""Schedule a video from the YouTube upload dialog."""

from __future__ import annotations

import json

from . import logic


def schedule_in_dialog(page, slot) -> None:
    page.evaluate("()=>{const b=document.querySelector('#step-badge-3'); if(b)b.click()}")
    page.wait_for_timeout(3000)
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
    page.wait_for_timeout(5000)
    body = page.locator("body").inner_text().lower()
    if "programado" not in body and "scheduled" not in body:
        raise RuntimeError("YouTube did not confirm the schedule")
