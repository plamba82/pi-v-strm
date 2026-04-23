#!/usr/bin/env python3
"""
Chrome-l-v-c.py

Drive Google Chrome on macOS via osascript + System Events:
 - Open YouTube (or default_url), perform in-page YouTube search (not omnibox),
 - Find first search-result by looking for a visible element containing "watch" and click it,
 - On the opened page, find and click the first Shorts link, wait, post a comment ("Jai ho") best-effort,
 - Attempt playback with robust JS and native Space fallback.

Usage:
  python3 Chrome-l-v-c.py --config profiles.json [--verbose]

Notes:
 - macOS only. Ensure Terminal/Python has Accessibility & Automation permissions (System Settings → Privacy & Security).
 - Google Chrome must be installed and accessible.
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
import threading
from typing import Optional, Tuple

# ------------------ Logging ------------------ #
logger = logging.getLogger(__name__)


# ------------------ AppleScript Runner ------------------ #
def run_applescript(script: str, timeout: float = 20.0) -> subprocess.CompletedProcess:
    """
    Run an AppleScript snippet via osascript and return the CompletedProcess.
    """
    logger.debug(
        "run_applescript: executing osascript (truncated preview): %s",
        repr(script[:300]),
    )
    try:
        return subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        logger.warning("run_applescript: osascript timed out")
        return subprocess.CompletedProcess(
            e.cmd,
            returncode=124,
            stdout=(e.stdout or ""),
            stderr=(e.stderr or "Timeout"),
        )


# ------------------ Helpers ------------------ #
def applescript_escape(s: Optional[str]) -> str:
    """
    Escape backslashes and double-quotes so the string can be safely embedded
    inside a double-quoted AppleScript string literal.
    """
    if s is None:
        return ""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def run_js_in_active_tab(js_code: str) -> Tuple[int, str, str]:
    """
    Execute `js_code` in the active tab of the front Google Chrome window.
    Returns (returncode, stdout, stderr).
    stdout is guaranteed to contain "OK||<value>" on success or "ERR||<message>" on AppleScript error.
    This avoids silent empty stdout cases.
    """
    esc = applescript_escape(js_code)
    script = f"""
    tell application "Google Chrome"
        try
            tell active tab of front window
                set _res to execute javascript "{esc}"
            end tell
            return "OK||" & (_res as string)
        on error errMsg number errNum
            return "ERR||" & errMsg
        end try
    end tell
    """
    logger.debug(
        "run_js_in_active_tab: running JS (truncated preview): %s", repr(js_code[:300])
    )
    res = run_applescript(script)
    out = res.stdout or ""
    err = res.stderr or ""
    logger.debug(
        "run_js_in_active_tab: rc=%s out=%s err=%s",
        res.returncode,
        repr(out[:400]),
        repr(err[:400]),
    )
    return res.returncode, out, err


def wait_for_page_ready(
    timeout: float = 10.0, poll: float = 0.5, verbose: bool = False
) -> bool:
    """
    Poll the active tab's document state until it appears rendered.
    Criteria: document.readyState === "complete" AND document.body has some content.
    Returns True when ready, False on timeout.
    """
    check_js = r"""(function(){
        try {
            var r = document.readyState || '';
            var bodyLen = (document.body && document.body.innerText) ? document.body.innerText.length : 0;
            return r + "||" + bodyLen;
        } catch(e) {
            return "error||0";
        }
    })()"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        rc, out, err = run_js_in_active_tab(check_js)
        out_s = (out or "").strip()
        if verbose:
            logger.debug(
                "wait_for_page_ready raw: rc=%s out=%s err=%s",
                rc,
                repr(out_s),
                repr(err),
            )
        payload = out_s
        if payload.lower().startswith("ok||"):
            payload = payload[4:]
        payload = payload.strip().lower()
        if payload.startswith("complete||"):
            try:
                _, body_len_s = payload.split("||", 1)
                if int(body_len_s) > 20:
                    return True
            except Exception:
                pass
        time.sleep(poll)
    if verbose:
        logger.debug("wait_for_page_ready timed out after %.1f seconds", timeout)
    return False


def wait_for_player_ready(
    timeout: float = 12.0, poll: float = 0.5, verbose: bool = False
) -> bool:
    """
    Poll the active tab for a Shorts/video player to be present (heuristics).
    Returns True when an element that likely indicates the player is mounted is found:
      - <video> element present
      - .ytp-cued-thumbnail-overlay present
      - #movie_player present
    """
    check_js = r"""(function(){
        try {
            if (document.querySelector('video')) return 'video';
            if (document.querySelector('.ytp-cued-thumbnail-overlay')) return 'overlay';
            if (document.querySelector('#movie_player')) return 'player';
            return '';
        } catch(e) {
            return 'error';
        }
    })();"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        rc, out, err = run_js_in_active_tab(check_js)
        out_s = (out or "").strip()
        if verbose:
            logger.debug(
                "wait_for_player_ready raw: rc=%s out=%s err=%s",
                rc,
                repr(out_s),
                repr(err),
            )
        if out_s.lower().startswith("ok||"):
            payload = out_s[4:].strip().lower()
        else:
            payload = out_s.strip().lower()
        if payload in ("video", "overlay", "player"):
            if verbose:
                logger.debug("wait_for_player_ready: detected player token=%s", payload)
            return True
        if payload.startswith("err||") or payload == "error":
            if verbose:
                logger.debug(
                    "wait_for_player_ready: page-side error detected: %s", payload
                )
        time.sleep(poll)
    if verbose:
        logger.debug("wait_for_player_ready timed out after %.1f seconds", timeout)
    return False


# ------------------ Activate Chrome ------------------ #
def activate_chrome(verbose: bool = False):
    logger.debug("activate_chrome: telling Chrome to activate")
    res = run_applescript('tell application "Google Chrome" to activate')
    if res.returncode != 0:
        logger.warning(
            "activate_chrome: osascript returncode=%s stderr=%s",
            res.returncode,
            repr(res.stderr),
        )


# ------------------ YouTube in-page search (robust) ------------------ #
def perform_youtube_search_in_page(
    search_query: str, verbose: bool = False, attempts: int = 4, delay: float = 1.0
) -> bool:
    """
    Perform search using YouTube's on-page search box (not omnibox).
    Tries multiple selectors, dispatches input/change events and synthesizes Enter.
    """
    q_js = json.dumps(search_query)
    js_template = f"""
    (function(q){{
        try {{
            var inputs = [
                'input#search',
                'ytd-searchbox input',
                'input[aria-label=\"Search\"]',
                'input[placeholder*=\"Search\"]',
                'input[name=\"search_query\"]'
            ];
            function dispatchEvents(el) {{
                try {{
                    el.focus && el.focus();
                    el.value = q;
                    el.dispatchEvent(new InputEvent('input', {{bubbles:true}}));
                    el.dispatchEvent(new Event('change', {{bubbles:true}}));
                    var kd = new KeyboardEvent('keydown', {{key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true}});
                    var ku = new KeyboardEvent('keyup', {{key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true}});
                    el.dispatchEvent(kd);
                    el.dispatchEvent(ku);
                }} catch(e){{}}
            }}
            for (var i=0;i<inputs.length;i++) {{
                try {{
                    var sel = inputs[i];
                    var input = document.querySelector(sel);
                    if (!input) continue;
                    dispatchEvents(input);
                    var btn = document.querySelector('button#search-icon-legacy') || document.querySelector('button[aria-label=\"Search\"]') || document.querySelector('ytd-searchbox button');
                    if (btn) {{
                        try {{ btn.click(); return 'submitted'; }} catch(e){{}}
                    }}
                    var form = input.closest('form');
                    if (form) {{
                        try {{ form.submit(); return 'submitted'; }} catch(e){{}}
                    }}
                    return 'submitted';
                }} catch(e){{}}
            }}
            return 'notfound';
        }} catch(e) {{
            return 'error||' + String(e);
        }}
    }})({q_js});
    """
    for attempt in range(1, attempts + 1):
        if verbose:
            logger.info(
                "perform_youtube_search_in_page: attempt %d/%d for query=%r",
                attempt,
                attempts,
                search_query,
            )
        rc, out, err = run_js_in_active_tab(js_template)
        out_s = (out or "").strip()
        if verbose:
            logger.debug(
                "perform_youtube_search_in_page: raw rc=%s out=%s err=%s",
                rc,
                repr(out_s),
                repr(err),
            )
        if out_s.lower().startswith("ok||"):
            payload = out_s[4:].strip().lower()
        else:
            payload = out_s.strip().lower()
        if payload.startswith("submitted"):
            return True
        if payload.startswith("err||") or payload.startswith("error||"):
            if verbose:
                logger.warning(
                    "perform_youtube_search_in_page: page-side error: %s", payload
                )
        if attempt < attempts:
            time.sleep(delay * attempt)
    if verbose:
        diag_js = r"""(function(){ try { var found = {}; found.input = !!(document.querySelector('input#search')||document.querySelector('ytd-searchbox input')||document.querySelector('input[aria-label="Search"]')); found.button = !!(document.querySelector('button#search-icon-legacy')||document.querySelector('button[aria-label="Search"]')); return JSON.stringify(found); } catch(e){ return 'error'; } })();"""
        d_rc, d_out, d_err = run_js_in_active_tab(diag_js)
        logger.info(
            "perform_youtube_search_in_page: final diagnostics -> %s (stderr=%s)",
            (d_out or "").strip(),
            repr(d_err),
        )
    return False


# ------------------ NEW: click first visible element containing 'watch' ------------------ #
def click_first_watch_on_page(verbose: bool = False) -> bool:
    """
    Find first visible element whose innerText matches /watch/i and click it.
    Prefers the closest anchor (target.closest('a')) if present.
    Returns True when click dispatched.
    """
    js = r"""
    (function(){
        try {
            function isVisible(el){
                try {
                    var cs = window.getComputedStyle(el);
                    var r = el.getBoundingClientRect();
                    return cs && cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity||1) > 0 && r.width>0 && r.height>0;
                } catch(e){ return false; }
            }
            var nodes = Array.from(document.querySelectorAll('a, button, div, span, p, li'));
            for (var i=0;i<nodes.length;i++){
                try {
                    var n = nodes[i];
                    if (!n) continue;
                    var text = (n.innerText || '').trim();
                    if (!text) continue;
                    if (/watch/i.test(text)) {
                        var target = n.closest('a') || n;
                        try { target.scrollIntoView({behavior:'auto', block:'center', inline:'center'}); } catch(e){}
                        try {
                            // robust click sequence
                            target.dispatchEvent(new MouseEvent('pointerdown',{bubbles:true}));
                        } catch(e){}
                        try {
                            target.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));
                        } catch(e){}
                        try {
                            target.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));
                        } catch(e){}
                        try {
                            target.dispatchEvent(new MouseEvent('click',{bubbles:true}));
                            return 'clicked';
                        } catch(e) {}
                        try { target.click(); return 'clicked'; } catch(e){}
                        return 'notclicked';
                    }
                } catch(e){}
            }
            return 'notfound';
        } catch(e) { return 'error||' + String(e); }
    })();
    """
    rc, out, err = run_js_in_active_tab(js)
    out_s = (out or "").strip()
    if verbose:
        logger.debug(
            "click_first_watch_on_page: rc=%s out=%s err=%s", rc, repr(out_s), repr(err)
        )
    if out_s.lower().startswith("ok||"):
        payload = out_s[4:].strip().lower()
    else:
        payload = out_s.strip().lower()
    return payload.startswith("clicked")


# ------------------ Click first Shorts in active tab ------------------ #
def click_first_shorts_in_active_tab(verbose: bool = False) -> bool:
    """
    Find and click the first link pointing to '/shorts/' or fallback heuristics.
    Returns True if clicked.
    """
    logger.info("click_first_shorts_in_active_tab: START")
    js = r"""
    (function() {
        function dispatchClick(el) {
            if (!el) return 'notfound';
            try {
                el.scrollIntoView({behavior: 'auto', block: 'center', inline: 'center'});
                var ev = new MouseEvent('click', {view: window, bubbles: true, cancelable: true});
                el.dispatchEvent(ev);
                return 'clicked';
            } catch (e) { return 'error'; }
        }
        var a = document.querySelector('a[href*="/shorts/"]');
        if (a) return dispatchClick(a);
        var all = Array.from(document.querySelectorAll('a'));
        for (var i = 0; i < all.length; i++) {
            var href = all[i].href || '';
            if (href.indexOf('/shorts/') !== -1) return dispatchClick(all[i]);
        }
        var candidates = Array.from(document.querySelectorAll('ytd-rich-item-renderer, ytd-video-renderer, ytd-grid-video-renderer, a, div'));
        for (var j = 0; j < candidates.length; j++) {
            try {
                var candidate = candidates[j];
                if (!candidate || !candidate.querySelector) continue;
                var inner = candidate.querySelector('a[href*="/shorts/"]');
                if (inner) return dispatchClick(inner);
            } catch (e) {}
        }
        var nodes = Array.from(document.querySelectorAll('*'));
        for (var k = 0; k < nodes.length; k++) {
            try {
                var n = nodes[k];
                if (n && n.innerText && /shorts/i.test(n.innerText)) {
                    var anc = n.closest('a');
                    if (anc) return dispatchClick(anc);
                }
            } catch (e) {}
        }
        return 'notfound';
    })();
    """
    rc, out, err = run_js_in_active_tab(js)
    out_s = (out or "").strip()
    if out_s.lower().startswith("ok||"):
        payload = out_s[4:].strip().lower()
    else:
        payload = out_s.strip().lower()
    if payload.startswith("clicked"):
        logger.info("click_first_shorts_in_active_tab: SHORTS clicked successfully")
        return True
    # Diagnostics on failure
    logger.warning(
        "click_first_shorts_in_active_tab: SHORTS not clicked (out=%s). Running diagnostics...",
        repr(payload),
    )
    diag_js = r"""
    (function(){
        try {
            var anchors = Array.from(document.querySelectorAll('a'));
            var count = anchors.length;
            var sample = anchors.slice(0,10).map(function(a){ return (a.href || '').slice(0,200) + "###" + (a.innerText || '').slice(0,80);});
            return JSON.stringify({count: count, sample: sample});
        } catch(e) {
            return JSON.stringify({count:0, sample:[]});
        }
    })();
    """
    d_rc, d_out, d_err = run_js_in_active_tab(diag_js)
    d_out_s = (d_out or "").strip()
    if verbose:
        logger.info("DIAGNOSTICS: anchor-sample=%s", d_out_s)
    return False


# ------------------ Playback helper (Hardened) ------------------ #
def play_current_video_in_active_tab(verbose: bool = False) -> bool:
    """
    Try to start playback in the current active tab via JS and verify it actually started.
    Strategy:
      - Try HTMLVideoElement.play() and verify paused/currentTime progression
      - Try overlay play button selectors and dispatch robust events
      - Try muting trick
      - Fallback: bring Chrome to front and send Space key via System Events
    Returns True when playback is observed.
    """
    js = r"""
    (async function(timeoutMs=7000, poll=200){
        function sleep(ms){ return new Promise(r=>setTimeout(r, ms)); }
        var deadline = Date.now() + timeoutMs;
        function verifyPlaying(v) {
            try {
                if (!v) return false;
                if (!v.paused) return true;
                return false;
            } catch(e) { return false; }
        }
        while (Date.now() < deadline) {
            try {
                var v = document.querySelector('video');
                if (v) {
                    try { v.play(); } catch(e) {}
                    await sleep(200);
                    if (verifyPlaying(v)) return 'played';
                    var t0 = v.currentTime || 0;
                    await sleep(300);
                    var t1 = v.currentTime || 0;
                    if (t1 > t0 + 0.05) return 'played';
                    try { v.muted = true; v.play(); } catch(e){}
                    await sleep(300);
                    if (verifyPlaying(v)) return 'played-muted';
                }
                var sel = 'button.ytp-large-play-button.ytp-button[aria-label="Play"], .ytp-cued-thumbnail-overlay button.ytp-large-play-button, button.ytp-large-play-button';
                var btn = document.querySelector(sel);
                if (btn) {
                    try { btn.scrollIntoView({block:'center',inline:'center'}); } catch(e){}
                    try { btn.click(); } catch(e){}
                    try { btn.dispatchEvent(new MouseEvent('pointerdown',{bubbles:true})); } catch(e){}
                    try { btn.dispatchEvent(new MouseEvent('click',{bubbles:true})); } catch(e){}
                    await sleep(250);
                    var v2 = document.querySelector('video');
                    if (v2 && !v2.paused) return 'played';
                }
            } catch(e){}
            await sleep(poll);
        }
        return 'notfound';
    })();
    """
    rc, out, err = run_js_in_active_tab(js)
    out_s = (out or "").strip()
    if out_s.lower().startswith("ok||"):
        payload = out_s[4:].strip()
    else:
        payload = out_s
    if verbose:
        logger.debug(
            "play_current_video_in_active_tab: raw rc=%s payload=%s err=%s",
            rc,
            repr(payload),
            repr(err),
        )
    if payload.startswith("played") or payload.startswith("played-muted"):
        logger.info(
            "play_current_video_in_active_tab: playback successful -> %s", payload
        )
        return True

    # Fallback: focus Chrome and send Space key via System Events
    logger.warning(
        "play_current_video_in_active_tab: initial play attempt failed (%s). Trying focus + Space key fallback...",
        payload,
    )
    try:
        run_applescript('tell application "Google Chrome" to activate')
        time.sleep(0.35)
        run_applescript('tell application "System Events" to key code 49')  # space
        time.sleep(0.6)
        probe_js = r"""(function(){ try { var v=document.querySelector('video'); if(!v) return 'no-video'; return (v.paused ? 'paused' : 'playing') + '||' + (v.currentTime || 0); } catch(e){ return 'err||'+String(e);} })();"""
        prc, pout, perr = run_js_in_active_tab(probe_js)
        pout_s = (pout or "").strip()
        if pout_s.lower().startswith("ok||"):
            pout_s = pout_s[4:].strip()
        if pout_s.startswith("playing"):
            logger.info(
                "play_current_video_in_active_tab: playback confirmed after Space fallback -> %s",
                pout_s,
            )
            return True
        logger.warning(
            "play_current_video_in_active_tab: Space fallback did not start playback -> %s",
            pout_s,
        )
    except Exception as e:
        logger.debug(
            "play_current_video_in_active_tab: Space fallback exception: %s", e
        )

    logger.warning(
        "play_current_video_in_active_tab: playback failed, final payload=%s", payload
    )
    return False


# ------------------ Comment helper (best-effort) ------------------ #
def add_comment_to_short(comment: str, verbose: bool = False) -> bool:
    """
    Best-effort: try to add a public comment to the Shorts page.
    Requires the user to be signed in and comments enabled.
    Returns True on 'commented'.
    """
    safe = comment.replace("\\", "\\\\").replace('"', '\\"')
    js = f"""
    (function(){{
        try {{
            var input = document.querySelector('ytd-comment-simplebox-renderer #placeholder-area, ytd-comment-simplebox-renderer div[contenteditable], div[aria-label*="Add a public comment"], textarea, div[contenteditable="true"]');
            if (!input) {{
                var all = Array.from(document.querySelectorAll('div[contenteditable="true"], textarea, input'));
                for (var i=0;i<all.length;i++) {{
                    var el = all[i];
                    var label = (el.getAttribute && (el.getAttribute('aria-label') || el.placeholder)) || '';
                    if (/comment/i.test(label) || /add a public comment/i.test(label)) {{ input = el; break; }}
                }}
            }}
            if (!input) return 'noinput';
            input.focus();
            if (input.contentEditable == "true") {{
                input.innerText = "{safe}";
                input.dispatchEvent(new InputEvent('input', {{bubbles:true}}));
            }} else {{
                input.value = "{safe}";
                input.dispatchEvent(new Event('input', {{bubbles:true}}));
            }}
            var btn = document.querySelector('ytd-button-renderer#submit-button, tp-yt-paper-button#submit, #submit-button, button[aria-label*="Comment"], button#submit');
            if (btn) {{ btn.click(); return 'commented'; }}
            var buttons = Array.from(document.querySelectorAll('button, tp-yt-paper-button, a'));
            for (var j=0;j<buttons.length;j++) {{
                var b = buttons[j];
                var t = (b.innerText||'').toLowerCase();
                if (t.indexOf('comment')!==-1 || t.indexOf('post')!==-1) {{ try {{ b.click(); return 'commented'; }} catch(e){{}} }}
            }}
            return 'nosubmit';
        }} catch(e) {{ return 'error'; }}
    }})();
    """
    rc, out, err = run_js_in_active_tab(js)
    out_s = (out or "").strip()
    if out_s.lower().startswith("ok||"):
        out_s = out_s[4:].strip().lower()
    else:
        out_s = out_s.strip().lower()
    if verbose:
        logger.debug(
            "add_comment_to_short: rc=%s out=%s err=%s", rc, repr(out_s), repr(err)
        )
    return out_s.startswith("commented")


# ------------------ Main flow: search -> open first result -> click Shorts -> comment & play ------------------ #
def chrome_search_and_click(
    search_query: str, default_url: Optional[str] = None, verbose: bool = False
) -> bool:
    """
    Perform in-page YouTube search, open the first result by clicking the first visible "watch" element,
    then click the first Shorts shown on that page, comment "Jai ho" and attempt playback.
    """
    logger.info(
        "chrome_search_and_click: START search_query=%s default_url=%s",
        search_query,
        default_url,
    )

    # Step A: optionally navigate to default_url quickly via omnibox to ensure Chrome front tab is set
    esc_default = applescript_escape(default_url) if default_url else ""
    default_line = f'keystroke "{esc_default}"' if default_url else ""
    script_nav = f"""
    tell application "Google Chrome"
        activate
        if (count of windows) = 0 then make new window
    end tell

    delay 1

    tell application "System Events"
        tell process "Google Chrome"
            keystroke "l" using command down
            delay 0.8
            {default_line}
            key code 36
            delay 1
        end tell
    end tell
    """
    res_nav = run_applescript(script_nav)
    if verbose:
        logger.info(
            "DEBUG: navigated to default_url step, rc=%s stdout=%s stderr=%s",
            res_nav.returncode,
            repr(res_nav.stdout[:400]),
            repr(res_nav.stderr[:400]),
        )

    if default_url:
        if not wait_for_page_ready(timeout=8.0, poll=0.5, verbose=verbose):
            if verbose:
                logger.warning(
                    "chrome_search_and_click: default_url did not reach ready state within timeout"
                )

    # Step B: perform YouTube in-page search (strict)
    if not perform_youtube_search_in_page(search_query, verbose=verbose):
        logger.warning(
            "chrome_search_and_click: perform_youtube_search_in_page failed; aborting search flow"
        )
        return False

    # Wait for search results to load
    if not wait_for_page_ready(timeout=12.0, poll=0.6, verbose=verbose):
        if verbose:
            logger.warning(
                "chrome_search_and_click: search results did not reach ready state within timeout"
            )

    # Step C: open first result by clicking first visible "watch" item (no tabs)
    if verbose:
        logger.info(
            "chrome_search_and_click: attempting to open first result by searching for label 'watch' on page"
        )
    watch_clicked = click_first_watch_on_page(verbose=verbose)
    res_open_ok = bool(watch_clicked)
    if verbose:
        logger.info(
            "chrome_search_and_click: click_first_watch_on_page -> %s", watch_clicked
        )

    # Wait for the opened result to load
    if not wait_for_page_ready(timeout=12.0, poll=0.6, verbose=verbose):
        if verbose:
            logger.warning(
                "chrome_search_and_click: first-result page did not reach ready state within timeout"
            )

    # Step D: Try clicking first Shorts with retries
    shorts_clicked = False
    for attempt in range(3):
        logger.info(
            "chrome_search_and_click: attempting shorts click attempt %d/3", attempt + 1
        )
        shorts_clicked = click_first_shorts_in_active_tab(verbose=verbose)
        logger.debug(
            "chrome_search_and_click: attempt %d -> shorts_clicked=%s",
            attempt + 1,
            shorts_clicked,
        )
        if shorts_clicked:
            break
        time.sleep(2)
    logger.info("chrome_search_and_click: SHORTS clicked final=%s", shorts_clicked)

    # If clicked, wait, attempt comment "Jai ho", then play
    played = False
    if shorts_clicked:
        init_delay = 5.0  # give player time to mount
        logger.debug(
            "chrome_search_and_click: waiting %.1fs for Shorts player to initialize",
            init_delay,
        )
        time.sleep(init_delay)

        player_ready = wait_for_player_ready(timeout=12.0, poll=0.6, verbose=verbose)
        if not player_ready:
            logger.warning(
                "chrome_search_and_click: player did not appear within timeout; proceeding but play may fail"
            )
        else:
            logger.debug(
                "chrome_search_and_click: player detected, proceeding to comment/play steps"
            )

        if not wait_for_page_ready(timeout=10.0, poll=0.5, verbose=verbose):
            if verbose:
                logger.warning(
                    "chrome_search_and_click: Shorts page did not reach ready state within timeout"
                )

        try:
            commented = add_comment_to_short("Jai ho", verbose=verbose)
            logger.info(
                "chrome_search_and_click: add_comment_to_short -> %s", commented
            )
        except Exception as e:
            logger.warning(
                "chrome_search_and_click: add_comment_to_short exception: %s", e
            )

        for p_attempt in range(6):
            logger.info(
                "chrome_search_and_click: attempting playback attempt %d/6",
                p_attempt + 1,
            )
            played = play_current_video_in_active_tab(verbose=verbose)
            logger.debug(
                "chrome_search_and_click: playback attempt %d result=%s",
                p_attempt + 1,
                played,
            )
            if played:
                break
            time.sleep(1.5 + (p_attempt * 0.5))
        logger.info("chrome_search_and_click: Playback started final=%s", played)

        if not played and verbose:
            diag = diag_play_button_and_player(verbose=verbose)
            logger.warning("chrome_search_and_click: PLAY diagnostics: %s", diag)

    return res_open_ok and shorts_clicked and (played if shorts_clicked else True)


# ------------------ Diagnostics for play button/player ------------------ #
def diag_play_button_and_player(verbose: bool = False) -> str:
    """
    Inspect play button(s), overlays and <video> element and return JSON diagnostic payload.
    """
    js = r"""
    (function(){
        try {
            function trim(s,n){ return s? (s.length>n? s.slice(0,n)+'…': s) : ''; }
            var selectors = [
                'button.ytp-large-play-button.ytp-button[aria-label="Play"]',
                '.ytp-cued-thumbnail-overlay button.ytp-large-play-button',
                'button.ytp-large-play-button',
                'button.ytp-play-button',
                '#movie_player .ytp-large-play-button'
            ];
            var candidates = [];
            for (var i=0;i<selectors.length;i++){
                try {
                    var el = document.querySelector(selectors[i]);
                    if (el) {
                        var r = el.getBoundingClientRect();
                        var cs = window.getComputedStyle(el);
                        candidates.push({
                            selector: selectors[i],
                            exists: true,
                            visible: (cs.display!=='none' && cs.visibility!=='hidden' && parseFloat(cs.opacity||1)>0 && r.width>0 && r.height>0),
                            rect: {x:r.x,y:r.y,w:r.width,h:r.height},
                            styles: {display:cs.display,visibility:cs.visibility,opacity:cs.opacity,pointerEvents:cs.pointerEvents,zIndex:cs.zIndex},
                            outerHTML: trim(el.outerHTML.replace(/\s+/g,' '),500)
                        });
                    } else {
                        candidates.push({selector: selectors[i], exists:false});
                    }
                } catch(e){ candidates.push({selector:selectors[i], error:String(e)}); }
            }
            var overlays = Array.from(document.querySelectorAll('.ytp-cued-thumbnail-overlay, .ytp-bezel, .ytp-spinner')).map(function(o){
                try { var cs = window.getComputedStyle(o); var r = o.getBoundingClientRect(); return {outer: trim(o.outerHTML.replace(/\s+/g,' '),300), visible:(cs.display!=='none'&&cs.visibility!=='hidden'&&r.width>0&&r.height>0), styles:{display:cs.display,visibility:cs.visibility,opacity:cs.opacity}}; } catch(e){ return {error:String(e)}; }
            });
            var v = document.querySelector('video');
            var videoInfo = v? {exists:true, paused:!!v.paused, currentTime:v.currentTime||0, readyState:v.readyState||0, src:(v.currentSrc||v.src||'').slice(0,400), muted:!!v.muted, controls:!!v.controls} : {exists:false};
            return JSON.stringify({candidates:candidates, overlays:overlays, video:videoInfo, viewport:{w:window.innerWidth,h:window.innerHeight}});
        } catch(e){
            return "ERR||" + String(e);
        }
    })();
    """
    rc, out, err = run_js_in_active_tab(js)
    out_s = (out or "").strip()
    if out_s.lower().startswith("ok||"):
        out_s = out_s[4:]
    if verbose:
        logger.info("DIAG: play-button payload=%s", out_s)
        if err:
            logger.debug("DIAG: run_js stderr: %s", repr(err))
    return out_s


# ------------------ Profile handler ------------------ #
def open_chrome_profile(
    profile_name: str, url: Optional[str], verbose: bool = False, close_after: int = 0
):
    """
    Per-profile worker executed in a thread.
    url may be:
      - "search:terms" => perform search flow
      - any full URL => open directly via 'open -a "Google Chrome" <url>'
      - None => fallback to global_url
    """
    logger.info(
        "open_chrome_profile: START profile=%s url=%s close_after=%s",
        profile_name,
        url,
        close_after,
    )
    activate_chrome(verbose=verbose)
    time.sleep(0.8)
    logger.info("✅ Chrome opened: %s", profile_name)

    if url and url.startswith("search:"):
        search_term = url.split("search:", 1)[1]
        ok = chrome_search_and_click(
            search_query=search_term,
            default_url="https://www.youtube.com/?",
            verbose=verbose,
        )
        logger.info("🔍 Search '%s' → %s", search_term, "OK" if ok else "FAILED")
    elif url:
        res = subprocess.run(
            ["open", "-a", "Google Chrome", url], capture_output=True, text=True
        )
        logger.debug(
            "open_chrome_profile: open direct rc=%s stdout=%s stderr=%s",
            res.returncode,
            repr(res.stdout[:200]),
            repr(res.stderr[:200]),
        )
        if verbose:
            logger.info("🌐 Opened URL: %s", url)

    if close_after > 0:
        logger.debug("open_chrome_profile: sleeping for close_after=%s", close_after)
        time.sleep(close_after)
        run_applescript('tell application "Google Chrome" to close front window')
        logger.info("❌ Closed window for profile %s", profile_name)


# ------------------ Runner ------------------ #
def run_profiles(config_path: str, verbose: bool = False):
    logger.info("run_profiles: loading config %s", config_path)
    with open(config_path, "r") as f:
        config = json.load(f)
    global_url = config.get("global_url")
    profiles = config.get("profiles", [])
    threads = []
    for prof in profiles:
        name = prof.get("profile_name", "profile")
        url = prof.get("url", global_url)
        duration = prof.get("duration", 10)
        logger.info(
            "run_profiles: spawning thread for profile=%s url=%s duration=%s",
            name,
            url,
            duration,
        )
        t = threading.Thread(
            target=open_chrome_profile,
            args=(name, url, verbose, duration),
            daemon=False,
        )
        t.start()
        threads.append(t)
        time.sleep(1.5)
    for t in threads:
        t.join()
    logger.info("run_profiles: all threads joined")


# ------------------ CLI ------------------ #
def main():
    parser = argparse.ArgumentParser(
        description="Drive Google Chrome from profiles.json"
    )
    parser.add_argument(
        "--config", default="profiles.json", help="Path to JSON config file"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logger.info("Starting Chrome-l-v-c.py (verbose=%s)", args.verbose)
    run_profiles(args.config, args.verbose)


if __name__ == "__main__":
    main()
