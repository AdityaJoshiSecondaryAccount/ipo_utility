import requests
from bs4 import BeautifulSoup
import re

def fetch_free_proxies():
    """Fetches a fresh list of free HTTP/HTTPS proxies dynamically."""
    print("Fetching fresh public proxy list...")
    # Using ProxyScrape's public API to get fresh HTTP proxies
    api_url = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text&protocol=http"
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            # Clean up the output to return a list of proxy addresses
            proxies = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
            print(f"Successfully retrieved {len(proxies)} proxies.")
            return proxies
    except Exception as e:
        print(f"Failed to fetch proxy list: {e}")
    return []

def PurvaDropDown():
    url = 'https://www.purvashare.com/investor-service/ipo-query'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }

    proxy_list = fetch_free_proxies()
    
    if not proxy_list:
        print("No proxies available. Attempting direct connection (likely to fail)...")
        # Fallback to a direct attempt if the proxy API fails
        proxy_list = [None]

    for proxy_url in proxy_list:
        proxies = None
        if proxy_url:
            # Handle formats where protocol might not be prepended properly
            if not proxy_url.startswith('http'):
                proxy_url = f"http://{proxy_url}"
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            print(f"Testing proxy: {proxy_url}")

        try:
            # Reduced timeout to 5 seconds so it skips dead public proxies quickly
            response = requests.get(url, headers=headers, proxies=proxies, verify=True, timeout=5)
            
            if response.status_code == 200:
                print(f"Success! Connected via proxy: {proxy_url if proxy_url else 'Direct'}")
                html_content = response.text
                
                # Parse the response data
                soup = BeautifulSoup(html_content, 'html.parser')
                dropdown_options = soup.select('#company_id option')
                data = [option.text.strip() for option in dropdown_options]
                data2 = [option.get('value', '') for option in dropdown_options]

                dropdown_dict = dict(zip(data, data2))
                normalized_dict = {
                    re.sub(r'\s+', ' ', key.strip()): value
                    for key, value in dropdown_dict.items()
                }
                return normalized_dict
            else:
                print(f"Proxy rejected with Status Code: {response.status_code}")
                continue
                
        except requests.RequestException:
            # Silent fail for individual proxies since public proxies are often offline
            continue

    print("All available proxies failed to bypass the firewall.")
    return None

print(PurvaDropDown())