# troubleshooting_internetwithviet

## install
```bash
python3.11 -m venv venv
venv/bin/pip install pdm
venv/bin/pdm install
venv/bin/litestar --app src.app:app run --debug --reload
```

## Run
```bash
venv/bin/litestar --app src.app:app run --debug --reload 
```

## Examples of route working and not working
Not working:
```
curl -X 'GET' \
  'http://127.0.0.1:8000/api/quote/all-not-working' \
  -H 'accept: application/json'
```

Working:
```
curl -X 'GET' \
  'http://127.0.0.1:8000/api/quote/all' \
  -H 'accept: application/json'
```
