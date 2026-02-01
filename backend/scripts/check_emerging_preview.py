import requests

URL = 'http://127.0.0.1:8000/v1/market/intel?mock=true'
HEADERS = {'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1aSIsInJvbGUiOiJSRUFEX09OTFkiLCJleHAiOjE3Njk4OTQyMjV9.mBeUQPbuEGDtTq1yIwgqtQfIXtMsjzZk2mbloASV6qM'}


def main():
    r = requests.get(URL, headers=HEADERS)
    js = r.json()
    signals = js.get('signals', [])
    print('total_signals:', len(signals))
    EMERGING_THRESHOLD = 0.3
    ACTIVE_THRESHOLD = 0.6
    emerging = [s for s in signals if s['reliability_score'] < ACTIVE_THRESHOLD*10 and s['reliability_score'] >= EMERGING_THRESHOLD*10]
    print('emerging_count:', len(emerging))
    for i,s in enumerate(emerging,1):
        print(i, s['title'], s['reliability_score'])


if __name__ == '__main__':
    main()
