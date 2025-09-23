import os

import requests

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")


def api(session: requests.Session, method: str, path: str, **kwargs):
    url = f"{BASE}{path}"
    resp = session.request(method, url, **kwargs)
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    return resp.status_code, data, resp


def ensure_user(session: requests.Session, username: str, password: str):
    sc, data, resp = api(
        session,
        "POST",
        "/api/auth/signup",
        json={"username": username, "password": password},
    )
    if sc == 201:
        print("Signed up & logged in as:", data)
        return True
    elif sc == 409:
        sc, data, resp = api(
            session,
            "POST",
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        if sc == 200:
            print("Logged in as:", data)
            return True
        else:
            print("Login failed:", sc, data)
            return False
    else:
        print("Signup failed:", sc, data)
        return False


def get_csrf_from_cookies(session: requests.Session):
    for c in session.cookies:
        if c.name == os.environ.get("CSRF_COOKIE_NAME", "app_csrf"):
            return c.value
    return None


def main():
    s = requests.Session()
    username = os.environ.get("SMOKE_USER", "demo_user")
    password = os.environ.get("SMOKE_PASS", "demo_pass")

    # Health
    sc, data, _ = api(s, "GET", "/api/health")
    print("Health:", sc, data)

    if not ensure_user(s, username, password):
        return

    # Me
    sc, data, _ = api(s, "GET", "/api/auth/me")
    print("Me:", sc, data)

    # Portfolio
    sc, data, _ = api(s, "GET", "/api/portfolio")
    print("Portfolio:", sc, data)

    # Pick a symbol via instruments search
    symbol = os.environ.get("SYMBOL", "INDUSTOWER-EQ")
    sc, search_data, _ = api(s, "GET", "/api/instruments/search", params={"q": symbol})
    if sc == 200 and isinstance(search_data, list) and search_data:
        first = search_data[0]
        if isinstance(first, dict) and "symbol" in first:
            symbol = str(first["symbol"])
    print("Using symbol:", symbol)

    # CSRF
    csrf = get_csrf_from_cookies(s)
    headers = {"X-CSRF-Token": csrf} if csrf else {}

    # BUY trade
    sc, t1, _ = api(
        s,
        "POST",
        "/api/trades",
        json={"symbol": symbol, "side": "BUY", "quantity": 2},
        headers=headers,
    )
    print("BUY trade:", sc, t1)

    # SELL trade
    sc, t2, _ = api(
        s,
        "POST",
        "/api/trades",
        json={"symbol": symbol, "side": "SELL", "quantity": 1},
        headers=headers,
    )
    print("SELL trade:", sc, t2)

    # Recent trades
    sc, lst, _ = api(s, "GET", "/api/trades/recent", params={"limit": 5})
    print("Recent trades:", sc, lst)

    # Logout
    sc, out, _ = api(s, "POST", "/api/auth/logout")
    print("Logout:", sc, out)


if __name__ == "__main__":
    main()
