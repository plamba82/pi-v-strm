def extract_video_id(url: str) -> str:
    return url.split("/")[-1].split("?")[0]