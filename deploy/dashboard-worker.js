/**
 * Gradiator Admin Dashboard Secure Proxy
 * Runs on Cloudflare Workers
 * 
 * Environment Variables Required:
 * 1. DASHBOARD_SECRET - Must match the SHA-256 hash of your password
 * 2. RENDER_BASE_URL - The URL of your Render backend (e.g., https://gradiator.onrender.com)
 */

const corsHeaders = {
  'Access-Control-Allow-Origin': '*', // For Pages dev URLs. Can be locked down to your specific pages.dev URL in production
  'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-Dashboard-Secret',
};

export default {
  async fetch(request, env, ctx) {
    // Handle CORS preflight requests
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // Ensure required env vars exist
    if (!env.RENDER_BASE_URL || !env.DASHBOARD_SECRET) {
      return new Response(JSON.stringify({ error: "Worker not configured properly." }), {
        status: 500,
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    // Verify Secret
    const clientSecret = request.headers.get('X-Dashboard-Secret');
    if (clientSecret !== env.DASHBOARD_SECRET) {
      return new Response(JSON.stringify({ error: "Unauthorized access" }), {
        status: 401,
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    // Parse the URL
    const url = new URL(request.url);
    const targetUrl = new URL(env.RENDER_BASE_URL);
    
    // Construct the backend URL (ensure we keep the /admin/dashboard path)
    targetUrl.pathname = url.pathname;
    targetUrl.search = url.search;

    // Create a new request to send to Render
    // We copy all valid headers, but forcefully inject our trusted secret
    const modifiedRequest = new Request(targetUrl.toString(), {
      method: request.method,
      headers: new Headers(request.headers),
      body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
      redirect: 'follow'
    });

    // Explicitly set the secret header for Render to validate
    modifiedRequest.headers.set('X-Dashboard-Secret', env.DASHBOARD_SECRET);
    
    try {
      const response = await fetch(modifiedRequest);
      
      // Copy the response and add CORS headers
      const newResponse = new Response(response.body, response);
      for (const [key, value] of Object.entries(corsHeaders)) {
        newResponse.headers.set(key, value);
      }
      return newResponse;
      
    } catch (e) {
      return new Response(JSON.stringify({ error: "Failed to connect to backend", details: e.message }), {
        status: 502,
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }
  },
};
