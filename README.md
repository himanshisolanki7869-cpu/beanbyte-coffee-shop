# BeanByte Coffee Shop - Flask Backend

This project includes a minimal Flask backend to serve the static frontend files and provide simple APIs for menu, contact, and orders.

Quick start:

1. (Optional) Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the server:

```bash
python app.py
```

The app will listen on port `5000` by default. Open `http://localhost:5000` to view the site.

APIs:
- `GET /api/menu` - returns menu items
- `POST /api/contact` - accepts JSON or form data `{name,email,message}`
- `POST /api/order` - accepts JSON `{items: [...], total: ...}`
- `GET /api/orders` - list submitted orders
- `POST /api/login` - login with `{username,password}`
- `POST /api/forgot-password` - creates a one-hour reset token for a user
- `POST /api/reset-password` - resets a password with `{token,password}`
- `GET /admin` - view saved orders and contact messages

Backend storage:
- Data is persisted in the SQLite database file `beanbyte.db` in the project root.
- A demo admin user is created automatically: username `admin`, email `admin@beanbyte.com`, password `coffee123`.

Notes:
- This backend uses SQLite by default. For production use, switch to MySQL and add secure authentication.

Deployment:
1. Push the project to GitHub.
2. Create an app on a host such as Railway, Render, or Heroku.
3. Set the root folder to this project.
4. Use `python-3.12.0` as the runtime and `web: gunicorn app:app` as the start command.
5. Install dependencies with `pip install -r requirements.txt`.

Once deployed, the public URL can be submitted to Google Search Console for indexing.
