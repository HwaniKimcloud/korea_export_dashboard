import truststore
truststore.inject_into_ssl()

import requests
import urllib.parse

url = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)

params = {
    "serviceKey": SERVICE_KEY,
    "strtYymm": "202509",
    "endYymm": "202608",
    "hsSgn": "8542"
}

response = requests.get(url, params=params)

print(response.url)
print()
print(response.text[:3000])