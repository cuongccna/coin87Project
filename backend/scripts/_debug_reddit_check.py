import httpx

url='https://reddit.com/r/CryptoCurrency/comments/1qsh69f/bitcoins_hashrate_crashed_12_worst_since_chinas/'
for u in [url, 'https://old.reddit.com'+url.split('reddit.com')[-1], url.rstrip('/')+'.json']:
    try:
        r=httpx.get(u, follow_redirects=True, timeout=15)
        print('URL:',u)
        print('STATUS', r.status_code)
        print('LEN', len(r.text))
        print('HEAD START:', r.text[:400].replace('\n',' '))
    except Exception as e:
        print('EXC', e)
    print('-'*60)
