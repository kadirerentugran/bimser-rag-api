import urllib.request
req = urllib.request.Request('http://localhost:8001/embeddings/reindex', method='POST')
req.add_header('x-api-key', '14531453')
try:
    with urllib.request.urlopen(req) as res:
        print(res.status)
except Exception as e:
    pass
