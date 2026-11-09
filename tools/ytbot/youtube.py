"""YouTube Studio upload, end screen and scheduled publishing."""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from . import config, logic, runtime, upload_dialog


def log(message: str) -> None:
    print(f"[youtube] {message}", flush=True)


def click_text(page, names: list[str]) -> bool:
    for name in names:
        locator = page.get_by_text(name, exact=True)
        if locator.count():
            locator.first.click()
            return True
    return False


def video_id_from(page) -> str:
    body = page.locator("body").inner_text()
    match = re.search(r"(?:Link do vídeo|Video link)\s*(https://youtu\.be/[A-Za-z0-9_-]+)", body, re.I)
    if not match:
        match = re.search(r"https://youtu\.be/([A-Za-z0-9_-]+)", body)
        return match.group(1) if match else ""
    return match.group(1).rsplit("/", 1)[-1]


def fill_editable(page, index: int, text: str) -> None:
    page.evaluate("(i)=>{const e=document.querySelectorAll('#textbox')[i]; if(e)e.focus()}", index)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.keyboard.insert_text(text)
    page.wait_for_timeout(350)


def upload_video(context, run_dir: Path, meta: dict, slot) -> str:
    page = context.new_page()
    page.goto(config.STUDIO_UPLOAD, timeout=90000)
    runtime.select_channel(page)
    try:
        page.get_by_role("button", name="Criar", exact=True).first.click()
    except Exception:
        page.get_by_role("button", name="Create", exact=True).first.click()
    page.wait_for_timeout(1200)
    click_text(page, ["Enviar vídeos", "Upload videos"])
    page.wait_for_timeout(1500)
    page.wait_for_selector('input[type=file][name="Filedata"]', state="attached", timeout=60000)
    upload_file = run_dir / f"upload-{run_dir.name}.mp4"
    upload_file.unlink(missing_ok=True)
    shutil.copy2(run_dir / "video.mp4", upload_file)
    dialog_input = page.locator('ytcp-uploads-file-picker input[type=file]')
    if dialog_input.count() == 0:
        dialog_input = page.locator('input[type=file][name="Filedata"]')
    dialog_input.last.set_input_files(str(upload_file))
    page.wait_for_selector("#textbox", state="attached", timeout=120000)
    page.wait_for_timeout(4000)
    fill_editable(page, 0, meta["title"])
    fill_editable(page, 1, meta["description"])
    page.wait_for_selector('input[type=file][accept*="image"]', state="attached", timeout=60000)
    page.locator('input[type=file][accept*="image"]').last.set_input_files(str(run_dir / "thumbnail.png"))
    page.wait_for_timeout(4000)
    page.evaluate("()=>{const b=document.querySelector('#toggle-button'); if(b)b.click()}")
    page.wait_for_timeout(1200)
    if page.evaluate("""()=>{const i=document.querySelector('input[aria-label="Tags"]'); if(!i)return false; i.focus(); return true;}"""):
        page.keyboard.insert_text(meta["tags"])
        page.keyboard.press("Enter")
        page.wait_for_timeout(800)
    page.evaluate("""()=>{const r=document.querySelector('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]'); if(r)r.click()}""")
    page.wait_for_timeout(800)
    deadline = time.time() + 1800
    while time.time() < deadline:
        body = page.locator("body").inner_text()
        if "Envio concluído" in body or "Upload complete" in body or "processamento vai começar" in body:
            break
        page.wait_for_timeout(3000)
    video_id = video_id_from(page)
    log(f"uploaded video id: {video_id}")
    if not video_id:
        raise RuntimeError("could not read the uploaded video id")
    upload_dialog.schedule_in_dialog(page, slot)
    log(f"scheduled {video_id} at {logic.slot_label(slot)}")
    page.close()
    upload_file.unlink(missing_ok=True)
    return video_id


def open_edit(context, video_id: str):
    page = context.new_page()
    page.goto(config.STUDIO_EDIT.format(video_id=video_id), timeout=90000)
    page.wait_for_timeout(8000)
    return page


def add_end_screen(page) -> None:
    page.get_by_text("Tela final", exact=True).last.click()
    page.wait_for_timeout(4000)
    page.locator("#add-element-menu-button").first.click()
    page.wait_for_timeout(1000)
    page.evaluate("""()=>{const els=[...document.querySelectorAll('tp-yt-paper-item')]; const v=els.find(e=>(e.innerText||'').trim()==='Vídeo'); if(v)v.click()}""")
    page.wait_for_timeout(1800)
    page.evaluate("""()=>{const r=[...document.querySelectorAll('tp-yt-paper-radio-button')].find(e=>/melhor para o espectador/i.test(e.innerText||'')); if(r)r.click()}""")
    page.wait_for_timeout(1200)
    log("end screen video element set to best for viewer")
    page.locator("#add-element-menu-button").first.click()
    page.wait_for_timeout(1000)
    page.evaluate("""()=>{const els=[...document.querySelectorAll('tp-yt-paper-item')]; const v=els.find(e=>(e.innerText||'').trim()==='Inscrever-se'); if(v)v.click()}""")
    page.wait_for_timeout(1200)
    page.evaluate("""()=>{const modal=document.querySelector('ytve-endscreen-modal')||document; const b=[...modal.querySelectorAll('#save-button, button, ytcp-button')].filter(e=>e.offsetWidth>0 && /salvar|save/i.test((e.innerText||''))).pop(); if(b)b.click()}""")
    page.wait_for_timeout(4000)
    log("end screen saved")


def wait_for_checks(page, timeout: int = 1800) -> None:
    deadline = time.time() + timeout
    stable = 0
    while time.time() < deadline:
        body = page.locator("body").inner_text()
        match = re.search(r"Verifica[çc][ãa]o\s+(\d+)%", body)
        if match:
            stable = 0
            page.wait_for_timeout(20000)
            continue
        stable += 1
        if stable >= 2:
            return
        page.wait_for_timeout(20000)


def write_result(run_dir: Path, result: dict) -> None:
    (run_dir / "upload.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


def upload_and_schedule_with_context(context, run_dir: Path, meta: dict, slot) -> dict:
    video_id = upload_video(context, run_dir, meta, slot)
    result = {"videoId": video_id, "url": f"https://youtu.be/{video_id}",
              "slot": logic.slot_label(slot), "visibility": "scheduled", "endScreen": False}
    write_result(run_dir, result)
    page = open_edit(context, video_id)
    try:
        wait_for_checks(page)
        add_end_screen(page)
    finally:
        page.close()
    result["endScreen"] = True
    write_result(run_dir, result)
    return result


def upload_and_schedule(run_dir: Path, meta: dict, slot) -> dict:
    with sync_playwright() as playwright:
        context = runtime.launch_upload_context(playwright)
        try:
            return upload_and_schedule_with_context(context, run_dir, meta, slot)
        finally:
            context.close()
