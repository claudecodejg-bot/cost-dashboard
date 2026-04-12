# Cost Dashboard

This repo contains the generator for a static OpenClaw cost dashboard. The real dashboard is built from JG's local session logs and deployed directly from the local machine, so the large generated HTML file and raw session data never need to be committed.

## Public URL

After the one-time Cloudflare Pages setup, the dashboard will be available at:

`https://<your-cloudflare-pages-project>.pages.dev`

The deploy script also prints the exact URL after each deploy.

## Repo Layout

- `generate-dashboard.py`: builds the standalone dashboard HTML.
- `index.html`: small tracked placeholder page for the repo.
- `dist/index.html`: ignored real output used for deployment.
- `deploy.sh`: generates the dashboard locally and uploads it to Cloudflare Pages.

## One-Time Setup

1. Install Wrangler: `npm install -g wrangler`
2. Log into Cloudflare: `wrangler login`
3. Create a Pages project once: `wrangler pages project create <your-cloudflare-pages-project>`

## Update The Dashboard

Deploy the real dashboard from the machine that has the local OpenClaw session logs:

```bash
cd /Users/claudecodejg/.openclaw/workspace/projects/cost-dashboard
CLOUDFLARE_PROJECT_NAME=<your-cloudflare-pages-project> ./deploy.sh
```

That command:

1. Reads `~/.openclaw/agents/main/sessions/*.jsonl`
2. Writes the generated site to `dist/index.html`
3. Uploads `dist/` directly to Cloudflare Pages
4. Prints the public URL

## Safe Preview Deploy

If you want a public preview without any real session data, deploy mock data instead:

```bash
cd /Users/claudecodejg/.openclaw/workspace/projects/cost-dashboard
CLOUDFLARE_PROJECT_NAME=<your-cloudflare-pages-project> USE_MOCK_DATA=1 ./deploy.sh
```

## Notes

- The public site is static HTML with all dashboard data embedded client-side.
- Real data comes from JG's local OpenClaw session logs at deploy time.
- `dist/` is ignored so generated output is not committed by default.

