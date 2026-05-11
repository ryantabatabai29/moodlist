import { generateCodeChallenge, generateCodeVerifier } from "./pkce";

const CLIENT_ID = import.meta.env.VITE_SPOTIFY_CLIENT_ID as string;
const SCOPES = [
  "playlist-read-private",
  "playlist-read-collaborative",
  "user-library-read",
  "playlist-modify-private",
].join(" ");

export async function startAuthFlow(): Promise<void> {
  const verifier = generateCodeVerifier();
  const challenge = await generateCodeChallenge(verifier);
  const redirectUri = chrome.runtime.getURL("callback.html");

  await chrome.storage.local.set({ pkce_verifier: verifier });

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    response_type: "code",
    redirect_uri: redirectUri,
    scope: SCOPES,
    code_challenge_method: "S256",
    code_challenge: challenge,
  });

  chrome.tabs.create({ url: `https://accounts.spotify.com/authorize?${params}` });
}

export async function exchangeCode(code: string): Promise<void> {
  const { pkce_verifier: verifier } = await chrome.storage.local.get("pkce_verifier");
  const redirectUri = chrome.runtime.getURL("callback.html");

  const resp = await fetch("https://accounts.spotify.com/api/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      redirect_uri: redirectUri,
      client_id: CLIENT_ID,
      code_verifier: verifier as string,
    }),
  });

  if (!resp.ok) throw new Error("Token exchange failed");

  const data = await resp.json();
  await chrome.storage.local.set({
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: Date.now() + (data.expires_in as number) * 1000,
    pkce_verifier: null,
  });
}

export async function getAccessToken(): Promise<string | null> {
  const stored = await chrome.storage.local.get(["access_token", "refresh_token", "expires_at"]);
  if (!stored.access_token) return null;

  if (Date.now() > (stored.expires_at as number) - 5 * 60 * 1000) {
    return refreshAccessToken(stored.refresh_token as string);
  }

  return stored.access_token as string;
}

async function refreshAccessToken(refreshToken: string): Promise<string | null> {
  try {
    const resp = await fetch("https://accounts.spotify.com/api/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: refreshToken,
        client_id: CLIENT_ID,
      }),
    });

    if (!resp.ok) {
      await chrome.storage.local.clear();
      return null;
    }

    const data = await resp.json();
    await chrome.storage.local.set({
      access_token: data.access_token,
      refresh_token: (data.refresh_token as string | undefined) ?? refreshToken,
      expires_at: Date.now() + (data.expires_in as number) * 1000,
    });

    return data.access_token as string;
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  await chrome.storage.local.clear();
}
