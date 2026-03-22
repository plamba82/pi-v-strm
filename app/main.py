from locust import HttpUser, task, between
import random
import time
import re
import uuid
import os

# 🔟 Modern browser agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13) Chrome/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) Chrome/119.0",
    "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) Safari/604.1",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0"
]

VIDEO_PLAYLISTS = [
    "/playlist?list=PLLOO94tdyRSCdBtWI3VS-cC_b-1Wu3vQ9&si=gB7CF7uVjnPz0-jo",
    "/playlist?list=PLLOO94tdyRSBiztpHHGTAF78qecmhcmVK&si=f77zLS8rLSNXjhBN"
]

VIEWPORTS = [360, 768, 1366, 1920]

class HLSUser(HttpUser):
    # Configure for remote site connection
    host = os.getenv("TARGET_HOST", "https://youtube.com")
    
    # Connection settings for remote site
    connection_timeout = 30.0
    network_timeout = 30.0
    wait_time = between(2, 5)

    def on_start(self):
        # Unique session
        self.session_id = str(uuid.uuid4())

        # Random browser identity
        self.user_agent = random.choice(USER_AGENTS)
        self.viewport = random.choice(VIEWPORTS)

        self.base_headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": random.choice([
                "en-US,en;q=0.9",
                "en-GB,en;q=0.8",
                "en-IN,en;q=0.9"
            ]),
            "Connection": "keep-alive",
            "Viewport-Width": str(self.viewport),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }

        self.client_hints = {
            "sec-ch-ua": '"Chromium";v="122", "Not:A-Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": random.choice(['"Windows"', '"macOS"', '"Android"', '"iOS"'])
        }

        # Simulate cookie/session
        self.client.cookies.set("session_id", self.session_id)
        # Test connectivity to remote site
        self.validate_connection()

    def validate_connection(self):
        """Validate connection to remote site"""
        try:
            response = self.client.get(
                "/",
                headers={
                    **self.base_headers,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                },
                timeout=self.connection_timeout,
                name="Connection Test"
            )
            if response.status_code >= 400:
                print(f"Warning: Remote site returned {response.status_code}")
        except Exception as e:
            print(f"Connection validation failed: {e}")

    @task
    def watch_video(self):
        # 🏠 Homepage with enhanced error handling
        try:
            home_response = self.client.get(
                "/",
                headers={
                    **self.base_headers,
                    **self.client_hints,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-User": "?1",
                    "Sec-Fetch-Dest": "document"
                },
                timeout=self.network_timeout,
                name="Home"
            )
            
            if home_response.status_code >= 400:
                print(f"Homepage failed with status {home_response.status_code}")
                return
                
        except Exception as e:
            print(f"Homepage request failed: {e}")
            return

        time.sleep(random.uniform(1, 2))

        # 🎯 Choose video
        playlist_url = random.choice(VIDEO_PLAYLISTS)
        # 📃 Master playlist with retry logic
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                master_res = self.client.get(
                    playlist_url,
                    headers={
                        **self.base_headers,
                        "Accept": "application/vnd.apple.mpegurl,*/*",
                        "Referer": f"{self.host}/@BhaktiSangeetPlu",
                        "Sec-Fetch-Mode": "cors"
                    },
                    timeout=self.network_timeout,
                    name="Master Playlist"
                )

                if master_res.status_code == 200:
                    break
                elif master_res.status_code >= 500:
                    retry_count += 1
                    time.sleep(random.uniform(1, 3))
                    continue
                else:
                    return
                    
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"Master playlist failed after {max_retries} retries: {e}")
                    return
                time.sleep(random.uniform(1, 3))        
        variants = re.findall(r'(.+\.m3u8)', master_res.text)
        print(f"Selected variant: {master_res.text})")

        if not variants:
            return

        current_variant = random.choice(variants)
        print(f"Selected variant: {current_variant} (from {len(variants)} available variants)")

        watch_time = random.randint(20, 60)
        start_time = time.time()
        playing = True

        self.log_event("play")

        while time.time() - start_time < watch_time:

            try:
                # 🎚 Variant playlist with timeout
                variant_res = self.client.get(
                    current_variant,
                    headers={
                        **self.base_headers,
                        "Accept": "application/vnd.apple.mpegurl,*/*",
                        "Referer": playlist_url
                    },
                    timeout=self.network_timeout,
                    name="Variant Playlist"
                )

                if variant_res.status_code != 200:
                    break

                segments = re.findall(r'(.+\.ts|.+\.m4s)', variant_res.text)
                if not segments:
                    break

                for segment in segments:
                    if time.time() - start_time > watch_time:
                        break

                    # ▶️ Resume if paused
                    if not playing:
                        self.log_event("resume")
                        playing = True

                    try:
                        # 🎬 Segment request with timeout
                        self.client.get(
                            segment,
                            headers={
                                **self.base_headers,
                                "Accept": "*/*",
                                "Referer": current_variant,
                                "Origin": self.host,
                                "Sec-Fetch-Dest": "video"
                            },
                            timeout=self.network_timeout,
                            name="Video Segment"
                        )
                    except Exception as e:
                        print(f"Segment request failed: {e}")
                        # Continue with next segment instead of breaking
                        continue

                    time.sleep(random.uniform(0.5, 1.5))

                    # ⏸ Pause
                    if random.random() < 0.05:
                        self.log_event("pause")
                        playing = False
                        time.sleep(random.uniform(1, 3))

                    # ⏩ Seek
                    if random.random() < 0.03:
                        self.log_event("seek")
                        break

                    # 🔄 ABR switch
                    if random.random() < 0.1:
                        new_variant = random.choice(variants)
                        if new_variant != current_variant:
                            self.log_event("quality_change")
                            current_variant = new_variant
                            break

                    # ⏳ Buffering
                    if random.random() < 0.08:
                        self.log_event("buffering")
                        time.sleep(random.uniform(1, 2.5))
                        
            except Exception as e:
                print(f"Variant playlist request failed: {e}")
                break

        self.log_event("stop")

    def log_event(self, event_type):
        print(f"Analytics logging failed for event: {event_type}")