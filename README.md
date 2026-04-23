# pi-v-strm
docker build -t hello-world-app .

docker run --rm hello-world-app

#UI Mode
docker run -p 8081:8081 hello-world-app --host=https://www.abc.com

#Headlesss
docker run locust-hls-test \
  --headless \
  -u 10000 \
  -r 200 \
  --host=https://yourdomain.com


# Master container
docker run -p 8089:8089 locust-hls-test \
  --master \
  --host=https://yourdomain.com
# Worker containers
(Replace <MASTER_IP> with your machine IP)
docker run locust-hls-test \
  --worker \
  --master-host=<MASTER_IP>

docker run locust-hls-test --worker --master-host=<MASTER_IP>
docker run locust-hls-test --worker --master-host=<MASTER_IP>
docker run locust-hls-test --worker --master-host=<MASTER_IP>

Docker YML:

version: "3"

services:
  master:
    build: .
    command: locust -f locustfile.py --master --host=https://yourdomain.com
    ports:
      - "8089:8089"

  worker:
    build: .
    command: locust -f locustfile.py --worker --master-host=master
    depends_on:
      - master
    deploy:
      replicas: 3

Run:

docker compose up --scale worker=5


docker stats



Core requirement: Create a Python automation tool that opens Safari browser windows with specific user profiles using AppleScript integration.

Extend this tools to support closing the open window with a duration configuration, Also it should now implement a sequence of steps just not opening one URL.

it should open first URL as "https://www.youtube.com", then after 5 seconds it should perform a search with keywiord "BhaktiSangeetPlus Channel" in the same window and after another 5 seconds it should perform a keywird search in the page with name "Bhakti Sangeet | भक्ति संगीत" and clicked on this URL. Once the URL is loaded which has a video player. It should play the video and wait for it compltetion. Once video is paused, it should close that window.

Requirements
Core Functionality:

Automate Safari profile selection through macOS System Events and AppleScript
Support JSON configuration for multiple profiles with custom URLs and durations
Implement automatic window closing after specified time periods
Technical Specifications:

Use AppleScript via osascript subprocess calls to interact with Safari's menu system
Navigate File → New Window → New [Profile] Window menu hierarchy
Handle multiple automation methods with fallback strategies
Support concurrent profile launches with threading
Provide verbose debugging output for troubleshooting
Configuration Format:

json





{
  "global_url": "default_url_for_all_profiles",
  "profiles": [
    {
      "profile_name": "profile_display_name",
      "url": "optional_profile_specific_url", 
      "duration": 15
    }
  ]
}
Key Features to Implement:

Profile Detection: Automatically find and click profile-specific menu items
Window Management: Track window counts before/after operations
URL Loading: Open specified URLs in newly created profile windows
Auto-Close: Schedule automatic window closure after duration expires
Error Handling: Graceful handling of permission issues and AppleScript failures
Threading: Support launching multiple profiles with staggered timing
Command Line Interface:

--config/-c: Path to JSON configuration file (default: profiles.json)
--method/-m: Automation method selection (auto, file)
--verbose/-v: Enable debug output
macOS Integration Requirements:

Request Accessibility/Automation permissions for Terminal/Python
Handle Safari activation and focus management
Implement proper delays for UI interaction timing
Support AppleScript error detection and reporting
Expected Behavior:

Launch Safari profiles sequentially with 3-second delays
Display success/failure status with emoji indicators
Provide helpful error messages for common permission issues
Clean up resources and handle threading properly
Error Scenarios to Handle:

Missing Safari application
Insufficient system permissions
Non-existent profile names
Network connectivity issues for URL loading
AppleScript execution failures
This tool should be robust enough for automated testing scenarios while providing clear feedback for debugging automation issues.

Sources-Repos/Files: