import urllib.request, json
req = urllib.request.Request('http://localhost:11434/api/embeddings', method='POST')
req.add_header('Content-Type', 'application/json')
data = json.dumps({"model": "nomic-embed-text", "prompt": "merhaba"})
try:
    with urllib.request.urlopen(req, data=data.encode()) as res:
        print(res.status, "Success")
except Exception as e:
    print("Error:", getattr(e, 'code', str(e)), getattr(e, 'read', lambda: b'')().decode())
