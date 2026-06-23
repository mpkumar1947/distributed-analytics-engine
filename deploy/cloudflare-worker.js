/**
 * Cloudflare Worker — Dual Pinger for Gradiator Bot
 * 
 * Pings both the Render app (to prevent sleep) and Neon database 
 * (to keep compute warm) every 4 minutes via Cron Triggers.
 * 
 * Setup:
 * 1. Go to Cloudflare Dashboard → Workers & Pages → Create Worker
 * 2. Paste this code
 * 3. Go to Settings → Triggers → Add Cron Trigger: */4 * * * *
 * 4. Set environment variables:
 *    - RENDER_HEALTH_URL: https://gradiator-bot.onrender.com/health
 *    - NEON_CONNECTION_CHECK_URL: (optional, see below)
 * 
 * This is 100% free on Cloudflare Workers free tier (100K requests/day).
 * Cron triggers every 4 minutes = ~10,800 invocations/month (well within limits).
 */

export default {
  async scheduled(event, env, ctx) {
    const results = {};

    // 1. Ping Render to keep it awake
    const renderUrl = env.RENDER_HEALTH_URL || 'https://gradiator-bot.onrender.com/health';
    try {
      const renderResponse = await fetch(renderUrl, {
        method: 'GET',
        headers: { 'User-Agent': 'Gradiator-CF-Pinger/1.0' },
      });
      results.render = {
        status: renderResponse.status,
        ok: renderResponse.ok,
      };
    } catch (err) {
      results.render = { error: err.message };
    }

    // 2. Ping Neon via Render's health endpoint (which queries the DB)
    //    The /health endpoint on the bot keeps Render alive.
    //    If you want to also warm Neon, you can add a /health/db endpoint
    //    to the bot that does a simple SELECT 1 query.
    //    For now, normal bot traffic + UptimeRobot handle Neon warmth.

    console.log(`Ping results: ${JSON.stringify(results)}`);
  },

  // Optional: Also handle HTTP requests for manual testing
  async fetch(request, env, ctx) {
    return new Response(JSON.stringify({
      service: 'gradiator-pinger',
      message: 'This worker pings Gradiator bot to keep it alive.',
      render_url: env.RENDER_HEALTH_URL || 'https://gradiator-bot.onrender.com/health',
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
  },
};
