# Stockroom

A small inventory app. You sign in, see a shared list of products, and add, edit and delete the
ones you own. Product details (brand, quantity, Nutri-Score, photo) can be pulled in from the
[Open Food Facts](https://world.openfoodfacts.org) API.

- **Frontend:** React + Vite (two routes: sign-in and a protected products page)
- **Backend:** Flask API with in-memory storage and cookie sessions
- **Tests:** 136 backend tests (pytest) and 23 frontend tests (Vitest)

## Contents

1. [Features](#features)
2. [Project structure](#project-structure)
3. [What you need](#what-you-need)
4. [Run the app](#run-the-app)
5. [Demo account](#demo-account)
6. [How it works](#how-it-works)
7. [API reference](#api-reference)
8. [Open Food Facts](#open-food-facts)
9. [Run the tests](#run-the-tests)
10. [Settings](#settings)
11. [Troubleshooting](#troubleshooting)
12. [Limits and next steps](#limits-and-next-steps)

## Features

| Requirement | Where it lives |
|---|---|
| Sign-in route with email and password | `/signin`, with a "Create an account" form (password + confirm password) |
| Protected route, only for signed-in users | `/products`; visitors who aren't signed in are sent to `/signin` |
| A list of information | Products table: name, category, price, stock, who added it |
| A form to add and edit | One form on `/products`, with validation |
| Edit and Delete buttons | On every row you own |
| RESTful CRUD routes | `GET/POST /inventory`, `GET/PATCH/DELETE /inventory/<id>` |
| In-memory storage | Plain Python lists in `Backend/data.py` |
| Session tracking the logged-in user | Flask signed-cookie session (`/auth/login`, `/auth/me`, `/auth/logout`) |
| `user_id` on every record | Set by the server from the session when an item is created |
| Open Food Facts details | "Look up" button, `GET /inventory/lookup`, `POST /inventory/<id>/enrich` |

## Project structure

```
summative-lab/
├── README.md
├── Backend/                    Flask API
│   ├── app.py                  creates the app, session settings, registers routes
│   ├── auth.py                 register, login, logout, me + the login check
│   ├── routes.py               /inventory CRUD + Open Food Facts routes
│   ├── validation.py           checks request bodies for items
│   ├── off_client.py           talks to the Open Food Facts API
│   ├── data.py                 in-memory storage (users and items), demo data
│   ├── requirements.txt        what the app needs
│   ├── requirements-dev.txt    + pytest
│   ├── pytest.ini
│   └── tests/                  backend tests
└── Frontend/                   React app
    ├── index.html
    ├── package.json
    ├── vite.config.js          dev server + proxy to Flask + test settings
    └── src/
        ├── main.jsx
        ├── App.jsx             the two routes
        ├── index.css
        ├── api/
        │   ├── client.js       fetch wrapper (errors, expired sessions)
        │   └── products.js     calls for the inventory routes
        ├── context/AuthContext.jsx   who is signed in; sign in/up/out
        ├── components/ProtectedRoute.jsx
        └── pages/
            ├── SignIn.jsx      sign in, register, demo button
            └── Products.jsx    list, form, Edit / Delete / Look up
```

## What you need

- **Python 3.10 or newer** (check with `python --version`)
- **Node.js 18 or newer** (check with `node --version`)
- A terminal. The commands below are for **Windows PowerShell**, with the Mac/Linux version where it differs.

## Run the app

You need **two terminals**: one for the backend, one for the frontend. Start the backend first.

### Terminal 1: backend (Flask, port 5000)

```powershell
cd Backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Mac/Linux: activate with `source .venv/bin/activate` instead.

If PowerShell says running scripts is disabled, run this once in that window, then activate again:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

When it works, your prompt starts with `(.venv)` and Flask prints `Running on http://127.0.0.1:5000`.
Leave it running. (Later runs only need the activate line and `python app.py`.)

### Terminal 2: frontend (Vite, port 5173)

```powershell
cd Frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

## Demo account

| Email | Password |
|---|---|
| `demo@example.com` | `password123` |

The sign-in page also has a **Try the demo account** button. The demo account owns the three starting
products. You can also register your own account: the form asks for your email, a password
(6+ characters) and the password again to confirm it.

The backend keeps everything in memory, so **restarting it resets all accounts and products** back to
the demo account and its three items.

## How it works

```
Browser ──► Vite dev server (:5173) ──proxy──► Flask API (:5000)
              serves the React app          /auth/*  and  /inventory/*
```

- **One origin.** The React app only talks to Vite. `vite.config.js` forwards `/auth` and `/inventory`
  to Flask, so the session cookie works without any CORS setup.
- **Sessions.** Logging in or registering stores your user id in a signed, HTTP-only cookie. On every
  page load the frontend asks `GET /auth/me` who you are, so a refresh keeps you signed in.
- **Protection, twice.** The frontend's `ProtectedRoute` sends signed-out visitors to `/signin`, and
  the backend returns **401** for every `/inventory` request without a session. The backend is the one
  that really enforces it.
- **`user_id`.** When you add an item, the server stamps it with your user id from the session. A
  `user_id` sent in a request is ignored, and it can't be changed later.
- **Ownership.** Everyone signed in can *see* every item, but only the person who added an item can
  edit, delete or look it up (others get **403**). The list shows who added each item, and the buttons
  are greyed out on items that aren't yours.
- **Passwords** are stored as hashes, never as plain text.
- **Expired sessions.** If a request comes back 401 while you're using the app, you're sent to the
  sign-in page.

## API reference

All `/inventory` routes need a logged-in session. Errors are JSON: `{ "error": "message" }`.

### Auth

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| POST | `/auth/register` | `email`, `password`, `confirm_password` | 201 `{user}` and signed in | 400 invalid or passwords differ, 409 email taken |
| POST | `/auth/login` | `email`, `password` | 200 `{user}` | 400 invalid, 401 wrong email or password |
| POST | `/auth/logout` | none | 204 | |
| GET | `/auth/me` | none | 200 `{user}` | 401 not signed in |

### Inventory

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | `/inventory` | 200, list of items | 401 |
| GET | `/inventory/<id>` | 200, one item | 401, 404 |
| POST | `/inventory` | 201, the new item (+ `Location` header) | 400, 401 |
| PATCH | `/inventory/<id>` | 200, the updated item | 400, 401, 403, 404 |
| DELETE | `/inventory/<id>` | 204 | 401, 403, 404 |
| GET | `/inventory/lookup?barcode=…` or `?name=…` | 200, list of matches (empty if none) | 400, 401, 502 |
| POST | `/inventory/<id>/enrich` | 200, item with `details` | 401, 403, 404, 502 |

An item looks like this (`added_by` is added to responses for display):
```json
{ "id": 1, "name": "Ceramic pour-over set", "category": "Kitchen", "price": 38.0, "stock": 14,
  "user_id": 1, "added_by": "demo@example.com",
  "barcode": "3274080005003", "details": { "brands": "Cristaline", "nutriscore_grade": "a" } }
```
- **POST** needs `name`, `category`, `price` (number, 0 or more) and `stock` (whole number, 0 or more).
  `barcode` (8 to 14 digits) is optional.
- **PATCH** accepts any of those fields, but at least one.

### Trying the API by hand

Cookies matter here, so keep the session between calls.

PowerShell:
```powershell
Invoke-RestMethod -Method Post http://localhost:5000/auth/login -ContentType "application/json" `
  -Body '{"email":"demo@example.com","password":"password123"}' -SessionVariable s
Invoke-RestMethod http://localhost:5000/inventory -WebSession $s
Invoke-RestMethod -Method Patch http://localhost:5000/inventory/1 -ContentType "application/json" `
  -Body '{"stock":10}' -WebSession $s
```
Mac/Linux:
```bash
curl -c jar.txt -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"password123"}' localhost:5000/auth/login
curl -b jar.txt localhost:5000/inventory
```
(In PowerShell use `Invoke-RestMethod`, not `curl`, which is a different command there.)

## Open Food Facts

`Backend/off_client.py` calls the free [Open Food Facts API](https://world.openfoodfacts.org) (no key needed):

- **By barcode:** exact match, `GET /api/v2/product/<barcode>.json`.
- **By name:** a text search that returns the closest matches.

The **Look up** button calls `POST /inventory/<id>/enrich`, which searches by, in order: a barcode or
name in the request, the item's saved barcode, the item's name. The best match is saved on the item as
`details` (brand, quantity, categories, ingredients, Nutri-Score, image), and its barcode is saved too if
the item had none.

- **Add a barcode** to an item for an exact match. A name search just takes the first hit, so a "Linen
  apron" can come back as something unrelated.
- Try the barcode `3274080005003` (Cristaline spring water).
- A **502** means Open Food Facts couldn't be reached or answered badly; a **404** means nothing matched.
- It's a free public service with rate limits. Requests time out after 10 seconds.

## Run the tests

Backend (from `Backend`, venv active):
```powershell
pip install -r requirements-dev.txt
pytest
```
136 tests covering registration (including password confirmation), login/logout, sessions, the login
requirement, CRUD, validation, `user_id` and ownership, and Open Food Facts. The Open Food Facts tests use
a fake, so they run offline. Handy options: `pytest -q`, `pytest tests/test_auth.py`, `pytest -k enrich`.

Frontend (from `Frontend`):
```powershell
npm test
```
23 tests covering the sign-in and register form (including confirm password and the demo button), the
protected route, and the API client's error handling. `npm run test:watch` re-runs as you edit.

## Settings

| Setting | Default | Notes |
|---|---|---|
| `SECRET_KEY` (backend environment variable) | a dev-only value | Signs the session cookie. Set your own for anything beyond local use: `$env:SECRET_KEY="long-random-text"` in PowerShell, `export SECRET_KEY=...` on Mac/Linux. |
| Backend port | 5000 | `app.run(..., port=5000)` in `Backend/app.py` |
| Proxy target | `http://localhost:5000` | `flask` constant in `Frontend/vite.config.js`. Change it if you change the backend port. |
| Session length | 8 hours | `PERMANENT_SESSION_LIFETIME` in `Backend/app.py` |

## Troubleshooting

| Problem | Fix |
|---|---|
| `source : The term 'source' is not recognized` | That's a Mac/Linux command. In PowerShell use `.venv\Scripts\Activate.ps1`. |
| "running scripts is disabled on this system" | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`, then activate again. |
| `&&` is "not a valid statement separator" | Older PowerShell. Run the commands on separate lines. |
| `ModuleNotFoundError: No module named 'flask'` (or `requests`) | The venv isn't active, or you skipped `pip install -r requirements.txt`. |
| A new route returns `{"error": "Not found."}` | The server is running old code. Press Ctrl+C and run `python app.py` again. |
| Page shows "Can't reach the server" | The Flask backend isn't running on port 5000. Start it (Terminal 1). |
| Port 5000 is already in use | Close the other program, or change the port in `app.py` and in `vite.config.js`. On macOS, AirPlay Receiver can hold 5000. |
| You're signed out after restarting the backend | Expected. Storage is in memory, so accounts are wiped on restart. Register again or use the demo account. |
| Look up shows "Open Food Facts took too long" or "could not get a valid response" | No internet, or their service is busy. Try again. |
| Look up finds the wrong product | Add the item's barcode and look up again. |

## Limits and next steps

- Storage is **in memory** and resets on restart. A real database (for example SQLite) would be the next step.
- Flask's built-in server and Vite's dev server are for development, not production.
- There's no rate limiting on login, password reset, or email verification.
- Every signed-in user can see every item. Change this in `Backend/routes.py` if your rules differ
  (the ownership check is the `get_owned` function).
