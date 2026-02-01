import os
import sys
import logging
import httpx
from pathlib import Path

# Add backend to sys.path
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.env import load_env_if_present

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("debug_proxy")

def debug_fetch(url: str, proxy_url: str = None):
    logger.info(f"Target URL: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    proxies = None
    if proxy_url:
        logger.info(f"Using Proxy: {proxy_url}")
        proxies = {"http://": proxy_url, "https://": proxy_url}
    else:
        logger.info("Using Direct Connection (No Proxy)")

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True, proxies=proxies) as client:
            resp = client.get(url, headers=headers)
            
            logger.info(f"Response Status: {resp.status_code}")
            logger.info(f"Response Headers: {resp.headers}")
            
            snippet = resp.text[:500].replace("\n", " ")
            logger.info(f"Body Response (First 500 chars): {snippet}...")
            
            if resp.status_code == 403:
                logger.warning("BLOCKED (403). Cloudflare or WAF rejected the request.")
                if "cf-ray" in resp.headers:
                    logger.warning(f"Cloudflare Ray ID: {resp.headers['cf-ray']}")

    except Exception as e:
        logger.error(f"Request Failed: {e}")

if __name__ == "__main__":
    load_env_if_present()
    
    target_url = input("Enter URL to test (default: https://www.coindesk.com/arc/outboundfeeds/rss/): ").strip()
    if not target_url:
        target_url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
        
    # Standard format for C87_PROXY_URL is comma separated
    proxy_env = os.environ.get("C87_PROXY_URL", "")
    proxy_single = None
    
    if proxy_env:
        proxies_list = [p.strip() for p in proxy_env.split(",") if p.strip()]
        if proxies_list:
            print(f"Found {len(proxies_list)} proxies in env.")
            use_proxy = input("Use proxy? (y/n, default: y): ").lower().strip()
            if use_proxy != 'n':
                # Pick first one for test
                proxy_single = proxies_list[0]
    else:
        print("No C87_PROXY_URL found in environment.")
        
    debug_fetch(target_url, proxy_single)
