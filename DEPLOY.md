# Deploying Form Saathi

The backend (FastAPI) goes on Render and the frontend (React) goes on Vercel. Both have free plans; check their current limits. You need your code on GitHub first.

## 1. Backend on Render

1. Sign in to [render.com](https://render.com) with GitHub.
2. Choose **New → Blueprint** and pick the `form-saathi` repository. Render reads `render.yaml` from the repo.
3. It asks for two values:
   - `GROQ_API_KEY`: your key from [console.groq.com/keys](https://console.groq.com/keys).
   - `CORS_ORIGINS`: put `http://localhost:5173` for now. You'll change it in step 3.
4. Deploy. When it finishes, open `https://<your-service>.onrender.com/api/health`. You should see `"llm": "groq"` and `"langgraph": true`.

The free plan sleeps after a while with no visitors, so the first request after that can take up to a minute. Open the health link before a demo to wake it up.

Sessions are stored in memory on purpose, for privacy. A restart or redeploy clears any form in progress.

## 2. Frontend on Vercel

1. Sign in to [vercel.com](https://vercel.com) with GitHub, then **Add New → Project** and pick the repo.
2. Set **Root Directory** to `frontend`. Vercel detects Vite by itself.
3. Under **Environment Variables**, add `VITE_API_BASE` = `https://<your-service>.onrender.com`, with no slash at the end.
4. Deploy. You'll get a link like `https://form-saathi.vercel.app`.

## 3. Connect the two

On Render, open the service, go to **Environment**, set `CORS_ORIGINS` to your Vercel link (for example `https://form-saathi.vercel.app`), and save. Render redeploys automatically.

Open the Vercel link, choose a language, and fill a form.

## 4. Install it on a phone

The deployed site uses HTTPS, so it can be installed:

- **Android (Chrome):** open the link, tap the ⋮ menu, then **Add to Home screen** (or **Install app**).
- **iPhone (Safari):** open the link, tap **Share**, then **Add to Home Screen**.

It then opens full-screen with its own icon, like a normal app.

## Testing on your phone before deploying

With the backend running on your laptop:

```bash
cd frontend
npm run dev -- --host
```

Vite prints a "Network" address like `http://192.168.1.5:5173`. Open it on a phone connected to the same Wi-Fi.

Phones only allow the microphone, read-aloud voices and installing on HTTPS sites, and this local address is plain HTTP. Typing and tapping work, but **voice and installing only work on the deployed HTTPS link.** To test voice before deploying, a tunnel such as `cloudflared tunnel --url http://localhost:5173` gives you a temporary HTTPS link.

## Checklist before putting the link on your resume

- [ ] The health check shows `"llm": "groq"`.
- [ ] Filled one form end to end in Tamil on a real phone.
- [ ] Tried "Speak and listen" on an Android phone.
- [ ] Downloaded the PDF.
- [ ] Woke the backend up just before sharing the link.
