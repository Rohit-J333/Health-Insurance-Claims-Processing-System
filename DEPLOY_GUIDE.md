# Deployment Guide — Railway (backend) + Vercel (frontend)

**Time to complete: ~20 minutes.**  
Both platforms connect directly to your GitHub repo — no Docker, no CLI required.

---

## Before you start — what you need

- Your GitHub repo is pushed and public (see `GIT_GUIDE.md`)
- Your Gemini API key (from Google AI Studio)
- A Railway account: https://railway.com (sign up with GitHub)
- A Vercel account: https://vercel.com (sign up with GitHub)

**Railway pricing note:** New accounts get a **$5 free trial credit** (expires in 30 days). The Hobby plan is $5/month after that. For a submission demo that runs for 1–2 weeks, the free credit is more than enough. A FastAPI app with low traffic uses roughly $0.10–$0.30/day.

---

## Part 1 — Deploy the Backend on Railway

### Step 1 — Create a new project

1. Go to https://railway.com and log in
2. Click **New Project**
3. Choose **Deploy from GitHub repo**
4. Find and select your `Health-Insurance-Claims-Processing-System` repo
5. Click **Add service** → **GitHub Repo**

### Step 2 — Set the root directory

Railway needs to know your Python app is inside `backend/`, not the repo root.

1. Click on the service that was just created
2. Go to **Settings** tab
3. Under **Source**, find **Root Directory**
4. Type: `backend`
5. Click **Save**

Railway will re-detect the app. It will find `pyproject.toml` and `Procfile` inside `backend/` and know it's a Python web app.

### Step 3 — Add environment variables

1. Click the **Variables** tab on your service
2. Add these one by one using the **+ New Variable** button:

| Variable | Value |
|----------|-------|
| `GEMINI_API_KEY` | your Gemini API key (paste the full key) |
| `GEMINI_MODEL` | `gemini-2.0-flash` |
| `ALLOWED_ORIGINS` | `*` (change this to your Vercel URL after Step 9) |

> **Do not** put the API key in your code or `.env` file in the repo. Railway's Variables tab is the right place.

### Step 4 — Deploy

1. Go to the **Deploy** tab (or click **Deploy** button)
2. Railway will build and deploy automatically — takes ~2–3 minutes
3. Watch the build logs — you should see:
   ```
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:XXXX
   ```

### Step 5 — Get your backend URL

1. Click the **Settings** tab
2. Under **Networking**, find **Public Networking**
3. Click **Generate Domain** if no domain exists yet
4. Copy the URL — it will look like: `https://your-app-name.up.railway.app`

### Step 6 — Test the backend

Open this in your browser (replace with your Railway URL):
```
https://your-app-name.up.railway.app/api/policy
```

You should see the policy JSON response. If you see `{"detail":"Not Found"}` something is wrong — double-check the root directory is set to `backend`.

Also test the health of the API:
```
https://your-app-name.up.railway.app/docs
```

This opens the auto-generated FastAPI docs UI — you can test any endpoint from here.

---

## Part 2 — Deploy the Frontend on Vercel

### Step 7 — Import your repo

1. Go to https://vercel.com and log in
2. Click **Add New** → **Project**
3. Find your `Health-Insurance-Claims-Processing-System` repo and click **Import**

### Step 8 — Configure the project

On the configuration screen:

| Setting | Value |
|---------|-------|
| **Framework Preset** | Vite (auto-detected) |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` (auto-filled) |
| **Output Directory** | `dist` (auto-filled) |

> **Important:** Set the Root Directory to `frontend`. Click the pencil icon next to "Root Directory" to edit it.

### Step 9 — Add environment variables

Still on the configuration screen, expand **Environment Variables** and add:

| Name | Value |
|------|-------|
| `VITE_API_URL` | `https://your-app-name.up.railway.app` |

This is your Railway backend URL from Step 5 — **without a trailing slash, without `/api`**.

### Step 10 — Deploy

Click **Deploy**. Vercel will:
1. Install npm dependencies
2. Run `npm run build`
3. Serve the static output from `dist/`

Takes about 1–2 minutes. When it finishes you'll see a preview URL like `https://health-insurance-claims.vercel.app`.

### Step 11 — Update Railway CORS

Now that you have your Vercel URL, go back to Railway and update the `ALLOWED_ORIGINS` variable:

1. Railway → your service → **Variables**
2. Edit `ALLOWED_ORIGINS` from `*` to your Vercel URL:
   ```
   https://health-insurance-claims.vercel.app
   ```
3. Railway will automatically redeploy with the new variable.

### Step 12 — Test the full stack

Open your Vercel URL and:
1. The Dashboard should load and show "No claims yet"
2. Go to Submit Claim — fill in a claim and submit
3. You should get a decision back with a full trace
4. The claim appears in the Dashboard

If the form submits but nothing comes back, open browser DevTools → Network tab to see if the API call is reaching Railway correctly.

---

## Your submission links

After both deployments succeed:

```
Repository:  https://github.com/YOUR_USERNAME/Health-Insurance-Claims-Processing-System
Frontend:    https://your-project.vercel.app
Backend API: https://your-app.up.railway.app/docs
Eval report: eval/EVAL_REPORT.md (in the repo)
```

---

## Troubleshooting

### Railway build fails with "No start command found"
Make sure the root directory is set to `backend` (not `backend/` with a slash). Check the **Settings → Source → Root Directory** field.

### Railway build fails with "ModuleNotFoundError: No module named 'app'"
The start command is running from the wrong directory. Verify root directory is `backend` and the `Procfile` is present in `backend/Procfile`.

### Railway app starts but `/api/policy` returns 500
The `policy_terms.json` file isn't being found. Check the build logs for a `FileNotFoundError`. Make sure `backend/policy_terms.json` exists in your repo (it should — check `git ls-files backend/`).

### Vercel build fails with "Cannot find module"
Make sure the **Root Directory** is set to `frontend` in Vercel's project settings. If it was deployed without this setting, go to **Project Settings → General → Root Directory** and change it, then redeploy.

### Frontend loads but API calls fail (CORS error in browser console)
1. Check `VITE_API_URL` in Vercel has no trailing slash
2. Check `ALLOWED_ORIGINS` in Railway exactly matches your Vercel domain
3. Redeploy Railway after changing `ALLOWED_ORIGINS`

### Frontend loads but claims don't save between refreshes
SQLite on Railway is fine for demos — but Railway's filesystem is ephemeral. Claims persist as long as the service is running. If Railway restarts (e.g., after inactivity on the free tier), the `claims.db` resets. This is a known limitation documented in `LIMITATIONS.md`. For the submission demo this is fine.

### Railway service keeps sleeping
Free trial services don't sleep — they stay up until your credit runs out. If you upgrade to Hobby, services also stay up. Only the old "Starter" plan (discontinued) had sleep behavior.

---

## Updating the deployment

After any code change, just push to GitHub:

```bash
git add <changed files>
git commit -m "fix: ..."
git push
```

Both Railway and Vercel watch your `main` branch and redeploy automatically within 2–3 minutes.

---

## Add a custom domain (optional, not required for submission)

**Vercel:** Project Settings → Domains → Add → follow DNS instructions  
**Railway:** Service Settings → Networking → Custom Domain → follow DNS instructions

Not needed for the assignment — the default `.vercel.app` and `.up.railway.app` URLs are fine.
