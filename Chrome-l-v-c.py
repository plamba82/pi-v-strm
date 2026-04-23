#!/usr/bin/env python3
"""
Chrome-l-v-c.py

Drive Google Chrome on macOS via osascript + System Events:
 - Open YouTube (or default_url), perform in-page YouTube search (not omnibox),
 - Find first search-result by looking for a visible element containing "watch" and click it,
 - On the opened page, find and click the first Shorts link, wait, post a comment ("Jai ho") best-effort,
 - Attempt playback with robust JS and native Space fallback.
 - AFTER playback: wait 2s, click <div class="ytSpecTouchFeedbackShapeFill"></div>, wait 1s, click it again,
   wait 1s, fill popup modal with "Nice " and submit (best-effort).

Usage:
  python3 Chrome-l-v-c.py --config profiles.json [--verbose]

Notes:
 - macOS only. Ensure Terminal/Python has Accessibility & Automation permissions.
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
    logger.debug("run_applescript preview: %s", repr(script[:300]))
    try:
        return subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=timeout
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
    if s is None:
        return ""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def run_js_in_active_tab(js_code: str) -> Tuple[int, str, str]:
    """
    Execute JS in the active Chrome tab via AppleScript. Returns (rc, stdout, stderr).
    stdout is prefixed with "OK||" or "ERR||" by the AppleScript wrapper.
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
    res = run_applescript(script)
    out = res.stdout or ""
    err = res.stderr or ""
    logger.debug(
        "run_js_in_active_tab: rc=%s out_len=%d err_len=%d",
        res.returncode,
        len(out),
        len(err),
    )
    return res.returncode, out.strip(), err.strip()


def wait_for_page_ready(
    timeout: float = 10.0, poll: float = 0.5, verbose: bool = False
) -> bool:
    """
    Poll document.readyState + body length until ready.
    """
    check_js = r"""(function(){
        try {
            var r = document.readyState || '';
            var bodyLen = (document.body && document.body.innerText) ? document.body.innerText.length : 0;
            return r + "||" + bodyLen;
        } catch(e) { return "error||0"; }
    })()"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        rc, out, err = run_js_in_active_tab(check_js)
        out_s = (out or "").strip().lower()
        if verbose:
            logger.debug(
                "wait_for_page_ready raw: rc=%s out=%s err=%s",
                rc,
                repr(out_s),
                repr(err),
            )
        if out_s.startswith("ok||"):
            payload = out_s[4:].strip()
        else:
            payload = out_s
        if payload.startswith("complete||"):
            try:
                _, body_len_s = payload.split("||", 1)
                if int(body_len_s) > 20:
                    if verbose:
                        logger.debug(
                            "wait_for_page_ready: ready (body len %s)", body_len_s
                        )
                    return True
            except Exception:
                pass
        time.sleep(poll)
    if verbose:
        logger.debug("wait_for_page_ready timed out after %.1f seconds", timeout)
    return False


# ------------------ Activate Chrome ------------------ #
def activate_chrome(verbose: bool = False):
    logger.debug("activate_chrome: activating Chrome")
    res = run_applescript('tell application "Google Chrome" to activate')
    if res.returncode != 0 and verbose:
        logger.warning(
            "activate_chrome: osascript rc=%s stderr=%s",
            res.returncode,
            repr(res.stderr),
        )


# ------------------ Perform YouTube in-page search ------------------ #
def perform_youtube_search_in_page(
    search_query: str, verbose: bool = False, attempts: int = 4, delay: float = 1.0
) -> bool:
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
            if verbose:
                logger.info(
                    "perform_youtube_search_in_page: submitted (payload=%s)", payload
                )
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
        d_out_s = (d_out or "").strip()
        logger.info(
            "perform_youtube_search_in_page: final diagnostics -> %s (stderr=%s)",
            d_out_s,
            repr(d_err),
        )
    return False


# ------------------ Click helpers ------------------ #
def click_first_shorts_in_active_tab(verbose: bool = False) -> bool:
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
    if verbose:
        logger.debug(
            "click_first_shorts_in_active_tab raw rc=%s out=%s err=%s",
            rc,
            repr(out_s),
            repr(err),
        )
    payload = out_s
    if payload.lower().startswith("ok||"):
        payload = payload[4:].strip().lower()
    else:
        payload = payload.strip().lower()
    if payload.startswith("err||"):
        if verbose:
            logger.warning(
                "click_first_shorts_in_active_tab: AppleScript error: %s", payload[5:]
            )
        return False
    success = "clicked" in payload
    if success:
        logger.info("click_first_shorts_in_active_tab: clicked")
        return True
    if verbose:
        logger.info("click_first_shorts_in_active_tab: not clicked -> %s", payload)
    return False


# ------------------ Playback helper ------------------ #
def play_current_video_in_active_tab(verbose: bool = False) -> bool:
    js = r"""
    (function(){
        try {
            var v = document.querySelector('video');
            if (v) {
                try { v.play(); return 'played'; } catch(e) {}
            }
            var sel = [
                'button.ytp-large-play-button',
                'button.ytp-play-button',
                'yt-icon-button.ytp-big-play-button',
                '#movie_player .ytp-large-play-button'
            ];
            for (var i=0;i<sel.length;i++){
                var b = document.querySelector(sel[i]);
                if (b) {
                    try { b.scrollIntoView({behavior:'auto', block:'center'}); } catch(e){}
                    try { b.click(); } catch(e){}
                    var v2 = document.querySelector('video');
                    if (v2 && !v2.paused) return 'played';
                }
            }
            return 'notplayed';
        } catch(e) { return 'error'; }
    })();
    """
    rc, out, err = run_js_in_active_tab(js)
    out_s = (out or "").strip()
    if verbose:
        logger.debug(
            "play_current_video_in_active_tab: rc=%s out=%s err=%s",
            rc,
            repr(out_s),
            repr(err),
        )
    if out_s.lower().startswith("ok||"):
        payload = out_s[4:].strip().lower()
    else:
        payload = out_s.strip().lower()
    return payload.startswith("played") or payload.startswith("played-muted")


# ------------------ Comment helper (existing best-effort) ------------------ #
def add_comment_to_short(comment: str, verbose: bool = False) -> bool:
    """
    Best-effort: try to add a public comment to the Shorts page.
    Requires the user to be signed in and comments enabled.
    Returns True on 'commented'.

    CHANGE: This implementation waits 5 seconds after typing the comment
    before clicking the submit button, and waits 1 second after clicking.
    The JS is async and returns the final status string.
    """
    js = f"""
    (async function(){{
        try {{
            var commentText = {json.dumps(comment)};
            // Prefer exact id first (your reported element)
            var input = document.querySelector('#contenteditable-root') ||
                        document.querySelector('ytd-comment-simplebox-renderer #placeholder-area') ||
                        document.querySelector('ytd-comment-simplebox-renderer div[contenteditable]') ||
                        document.querySelector('div[aria-label*="Add a public comment"]') ||
                        document.querySelector('textarea') ||
                        document.querySelector('div[contenteditable="true"]');

            if (!input) {{
                var all = Array.from(document.querySelectorAll('div[contenteditable="true"], textarea, input'));
                for (var i=0;i<all.length;i++) {{
                    var el = all[i];
                    var label = (el.getAttribute && (el.getAttribute('aria-label') || el.placeholder)) || '';
                    if (/comment/i.test(label) || /add a public comment/i.test(label)) {{ input = el; break; }}
                }}
            }}
            if (!input) return 'noinput';
            try {{ input.focus(); }} catch(e){{}}
            if (input.contentEditable == "true" || input.isContentEditable) {{
                try {{
                    input.innerText = commentText;
                    input.dispatchEvent(new InputEvent('input', {{bubbles:true}}));
                    input.dispatchEvent(new Event('change', {{bubbles:true}}));
                }} catch(e){{ }}
            }} else {{
                try {{
                    input.value = commentText;
                    input.dispatchEvent(new Event('input', {{bubbles:true}}));
                    input.dispatchEvent(new Event('change', {{bubbles:true}}));
                }} catch(e){{ }}
            }}

            // WAIT 5 seconds between typing and clicking submit (per request)
            await new Promise(function(r){{ setTimeout(r, 5000); }});

            // Try to find submit-like buttons and click (wait 1s after click)
            var submitSelectors = [
                'ytd-button-renderer#submit-button',
                'tp-yt-paper-button#submit',
                '#submit-button',
                'button[aria-label*="Comment"]',
                'button#submit',
                'button[aria-label*="Post"]',
                'button[title*="Post"]'
            ];
            for (var s=0;s<submitSelectors.length;s++) {{
                try {{
                    var btn = document.querySelector(submitSelectors[s]);
                    if (btn) {{
                        try {{ btn.click(); await new Promise(function(r){{ setTimeout(r,1000); }}); return 'commented'; }} catch(e){{/* continue */}}
                    }}
                }} catch(e){{}}
            }}

            // Fallback: visible buttons containing 'post'/'submit'/'ok'/'send'/'comment'
            var buttons = Array.from(document.querySelectorAll('button, tp-yt-paper-button, a'));
            for (var j=0;j<buttons.length;j++) {{
                try {{
                    var b = buttons[j];
                    var t = (b.innerText || (b.getAttribute && b.getAttribute('aria-label')) || '').toLowerCase();
                    if (/post|submit|ok|send|comment/i.test(t) && b.offsetParent !== null) {{
                        try {{ b.click(); await new Promise(function(r){{ setTimeout(r,1000); }}); return 'commented'; }} catch(e){{}}
                    }}
                }} catch(e){{}}
            }}
            return 'nosubmit';
        }} catch(e) {{ return 'error||' + String(e); }}
    }})();"""
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


# ------------------ NEW: Post-play interactions (click ytSpecTouchFeedbackShapeFill twice, fill modal) ------------------ #
def perform_post_play_actions(
    comment_text: str = "Nice ", verbose: bool = False
) -> bool:
    """
    Steps:
      1) Click first div.ytSpecTouchFeedbackShapeFill once
      2) wait 1s, click it again (to open modal)
      3) wait 1s, locate modal input with id '#contenteditable-root' or contenteditable and set value to comment_text,
         WAIT 5s between typing and submit, then click submit and wait 1s.
    Returns True on observed 'submitted' / success, False otherwise.
    """
    if verbose:
        logger.info(
            "perform_post_play_actions: starting, comment_text=%r", comment_text
        )

    # JS to click the ytSpecTouchFeedbackShapeFill element (first visible)
    click_js = r"""(function(){
        try {
            function isVisible(el){
                try {
                    var cs = window.getComputedStyle(el);
                    var r = el.getBoundingClientRect();
                    return cs && cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity||1) > 0 && r.width>0 && r.height>0;
                } catch(e){ return false; }
            }
            var nodes = Array.from(document.querySelectorAll('div.ytSpecTouchFeedbackShapeFill'));
            for (var i=0;i<nodes.length;i++){
                try {
                    var n = nodes[i];
                    if (!n) continue;
                    if (!isVisible(n)) continue;
                    try { n.scrollIntoView({behavior:'auto', block:'center', inline:'center'}); } catch(e){}
                    try { n.dispatchEvent(new MouseEvent('pointerdown',{bubbles:true})); } catch(e){}
                    try { n.dispatchEvent(new MouseEvent('mousedown',{bubbles:true})); } catch(e){}
                    try { n.dispatchEvent(new MouseEvent('mouseup',{bubbles:true})); } catch(e){}
                    try { n.dispatchEvent(new MouseEvent('click',{bubbles:true})); } catch(e){}
                    try { n.click(); } catch(e){}
                    return 'clicked';
                } catch(e){}
            }
            return 'notfound';
        } catch(e) {
            return 'error||'+String(e);
        }
    })();"""

    # JS to fill and submit modal input (prioritize '#contenteditable-root'), with waits
    fill_js_template = r"""(async function(commentText){
        try {
            function isVisible(el){
                try {
                    var cs = window.getComputedStyle(el);
                    var r = el.getBoundingClientRect();
                    return cs && cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity||1) > 0 && r.width>0 && r.height>0;
                } catch(e){ return false; }
            }

            // Prefer exact id used in your modal
            var input = document.querySelector('#contenteditable-root');
            if (!input) {
                // try common dialog selectors first
                var dialogSelectors = ['tp-yt-paper-dialog','ytm-dialog-renderer','div[role=\"dialog\"]','.yt-dialog','.modal','ytm-popup-renderer'];
                var dialog = null;
                for (var i=0;i<dialogSelectors.length;i++){
                    try {
                        var d = document.querySelector(dialogSelectors[i]);
                        if (d && isVisible(d)) { dialog = d; break; }
                    } catch(e){}
                }
                if (dialog) {
                    // prefer dialog-contained editables
                    input = dialog.querySelector('#contenteditable-root') || dialog.querySelector('textarea, input[type=\"text\"], div[contenteditable=\"true\"]');
                }
                if (!input) {
                    input = document.querySelector('textarea, input[type=\"text\"], div[contenteditable=\"true\"]');
                }
            }
            if (!input) return 'noinput';

            try { input.focus(); } catch(e){}
            // handle contenteditable nodes vs plain inputs
            if (input.contentEditable === "true" || input.isContentEditable) {
                try { input.innerText = commentText; input.dispatchEvent(new InputEvent('input',{bubbles:true})); input.dispatchEvent(new Event('change',{bubbles:true})); } catch(e){}
            } else {
                try { input.value = commentText; input.dispatchEvent(new Event('input',{bubbles:true})); input.dispatchEvent(new Event('change',{bubbles:true})); } catch(e){}
            }

            // WAIT 5 seconds between typing and clicking submit (per request)
            await new Promise(function(r){ setTimeout(r, 5000); });

            // find submit-like buttons (dialog first, then global)
            var submitSelectors = [
                'button[aria-label*=\"Post\"]',
                'button[aria-label*=\"Send\"]',
                'button[aria-label*=\"Submit\"]',
                'button[aria-label*=\"Comment\"]',
                'button#submit',
                'tp-yt-paper-button#submit',
                'ytd-button-renderer#submit-button'
            ];
            for (var s=0;s<submitSelectors.length;s++){
                try {
                    var btn = (document.querySelector(submitSelectors[s]));
                    if (btn && isVisible(btn)) { try { btn.click(); await new Promise(function(r){ setTimeout(r,1000); }); return 'submitted'; } catch(e){} }
                } catch(e){}
            }
            // fallback: visible buttons with text 'post'/'submit'/'ok'/'send'/'comment'
            var buttons = Array.from(document.querySelectorAll('button, a, tp-yt-paper-button'));
            for (var k=0;k<buttons.length;k++){
                try {
                    var b = buttons[k];
                    var t = (b.innerText || (b.getAttribute && b.getAttribute('aria-label')) || '').toLowerCase();
                    if (/post|submit|ok|send|comment/i.test(t) && isVisible(b)) {
                        try { b.click(); await new Promise(function(r){ setTimeout(r,1000); }); return 'submitted'; } catch(e){} 
                    }
                } catch(e){}
            }
            return 'nosubmit';
        } catch(e) {
            return 'error||'+String(e);
        }
    })(%s);""" % json.dumps(
        comment_text
    )

    # Step 1: click once
    rc1, out1, err1 = run_js_in_active_tab(click_js)
    out1_s = (out1 or "").strip()
    if out1_s.lower().startswith("ok||"):
        p1 = out1_s[4:].strip().lower()
    else:
        p1 = out1_s.strip().lower()
    if verbose:
        logger.debug(
            "perform_post_play_actions: first-click rc=%s out=%s err=%s",
            rc1,
            repr(out1_s),
            repr(err1),
        )
    # wait 1s after first click
    time.sleep(1.0)

    # Step 2: click again
    rc2, out2, err2 = run_js_in_active_tab(click_js)
    out2_s = (out2 or "").strip()
    if out2_s.lower().startswith("ok||"):
        p2 = out2_s[4:].strip().lower()
    else:
        p2 = out2_s.strip().lower()
    if verbose:
        logger.debug(
            "perform_post_play_actions: second-click rc=%s out=%s err=%s",
            rc2,
            repr(out2_s),
            repr(err2),
        )
    # wait 1s for modal to appear
    time.sleep(1.0)

    # Step 3: fill and submit comment in modal (with 5s typing->click and 1s post-click)
    rc3, out3, err3 = run_js_in_active_tab(fill_js_template)
    out3_s = (out3 or "").strip()
    if out3_s.lower().startswith("ok||"):
        p3 = out3_s[4:].strip().lower()
    else:
        p3 = out3_s.strip().lower()
    if verbose:
        logger.debug(
            "perform_post_play_actions: fill/submit rc=%s out=%s err=%s",
            rc3,
            repr(out3_s),
            repr(err3),
        )

    success = p3.startswith("submitted")
    if success:
        logger.info("perform_post_play_actions: comment submitted")
    else:
        logger.warning(
            "perform_post_play_actions: did not submit comment (result=%s). p1=%s p2=%s",
            p3,
            p1,
            p2,
        )
    return success


# ------------------ Diagnostics for play button/player ------------------ #
def diag_play_button_and_player(verbose: bool = False) -> str:
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


# ------------------ Main flow: search -> open first result -> click Shorts -> comment & play -> post-play actions ------------------ #
def chrome_search_and_click(
    search_query: str, default_url: Optional[str] = None, verbose: bool = False
) -> bool:
    logger.info(
        "chrome_search_and_click: START search_query=%s default_url=%s",
        search_query,
        default_url,
    )
    esc_default = applescript_escape(default_url) if default_url else ""
    default_line = f'keystroke "{esc_default}"' if default_url else ""

    # Navigate to default_url quickly (omnibox keystroke / enter) to ensure Chrome front tab is set
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

    # Wait until youtube page loads
    if default_url:
        if not wait_for_page_ready(timeout=12.0, poll=0.6, verbose=verbose):
            if verbose:
                logger.warning("default_url did not reach ready state within timeout")

    # Step: perform YouTube in-page search (strict: do NOT use omnibox)
    if not perform_youtube_search_in_page(search_query, verbose=verbose):
        logger.warning(
            "perform_youtube_search_in_page failed; aborting search flow (no omnibox fallback)"
        )
        return False

    # Wait for search results to load
    if not wait_for_page_ready(timeout=12.0, poll=0.6, verbose=verbose):
        if verbose:
            logger.warning("search results did not reach ready state within timeout")

    # Open first search result (tabbing best-effort)
    script_open_first = """
    tell application "System Events"
        tell process "Google Chrome"
            try
                repeat 23 times
                    key code 48 -- TAB
                    delay 0.12
                end repeat
                key code 36 -- ENTER
            end try
        end tell
    end tell
    """
    res_open = run_applescript(script_open_first)
    if verbose:
        logger.info(
            "DEBUG: attempted to open first result, rc=%s stdout=%s stderr=%s",
            res_open.returncode,
            repr(res_open.stdout[:400]),
            repr(res_open.stderr[:400]),
        )

    # Wait for opened page to be ready
    if not wait_for_page_ready(timeout=12.0, poll=0.6, verbose=verbose):
        if verbose:
            logger.warning("first-result page did not reach ready state within timeout")

    # Click first Shorts with retries
    shorts_clicked = False
    for attempt in range(3):
        logger.info("attempting shorts click attempt %d/3", attempt + 1)
        shorts_clicked = click_first_shorts_in_active_tab(verbose=verbose)
        if shorts_clicked:
            break
        time.sleep(2)
    logger.info("SHORTS clicked final=%s", shorts_clicked)

    # If clicked, wait and then comment/play
    played = False
    if shorts_clicked:
        time.sleep(5.0)
        try:
            commented = add_comment_to_short("Jai ho", verbose=verbose)
            logger.info("add_comment_to_short -> %s", commented)
        except Exception as e:
            logger.warning("add_comment_to_short exception: %s", e)
        for p_attempt in range(6):
            played = play_current_video_in_active_tab(verbose=verbose)
            if played:
                break
            time.sleep(1.5)
        logger.info("Playback started final=%s", played)

        # NEW: after playback, perform the two clicks + modal comment "Nice "
        if played:
            # Wait 2 seconds after playback (per your request)
            logger.debug("Pausing 2.0s after playback before post-play interactions")
            time.sleep(2.0)
            try:
                post_ok = perform_post_play_actions("Nice ", verbose=verbose)
                logger.info("perform_post_play_actions -> %s", post_ok)
            except Exception as e:
                logger.warning("perform_post_play_actions exception: %s", e)

    return (
        (res_open.returncode == 0)
        and shorts_clicked
        and (played if shorts_clicked else True)
    )


# ------------------ Profile handler, runner, CLI ------------------ #
def open_chrome_profile(
    profile_name: str, url: Optional[str], verbose: bool = False, close_after: int = 0
):
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
            "open_direct rc=%s stdout=%s stderr=%s",
            res.returncode,
            repr(res.stdout[:200]),
            repr(res.stderr[:200]),
        )
        if verbose:
            logger.info("🌐 Opened URL: %s", url)
    if close_after > 0:
        time.sleep(close_after)
        run_applescript('tell application "Google Chrome" to close front window')
        logger.info("❌ Closed window for profile %s", profile_name)


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
            "spawning thread for profile=%s url=%s duration=%s", name, url, duration
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


def main():
    parser = argparse.ArgumentParser(
        description="Drive Chrome from profiles.json using YouTube on-page search"
    )
    parser.add_argument(
        "--config", default="profiles.json", help="Path to JSON config file"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s: %(message)s")
    run_profiles(args.config, args.verbose)


if __name__ == "__main__":
    main()
