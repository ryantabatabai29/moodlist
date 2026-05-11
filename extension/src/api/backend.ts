import type { ErrorType, GenerateResult, PlaylistItem } from "../types";

const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? "http://localhost:8000";

function makeError(type: ErrorType, message: string): Error {
  return Object.assign(new Error(message), { errorType: type });
}

export async function getPlaylists(accessToken: string): Promise<PlaylistItem[]> {
  const resp = await fetch(`${BACKEND_URL}/playlists`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (resp.status === 401) throw makeError("auth_failure", "Spotify token expired");
  if (!resp.ok) throw makeError("server_error", "Failed to fetch playlists");

  const data = (await resp.json()) as Array<{
    id: string;
    name: string;
    track_count: number;
    image_url: string | null;
    is_liked_songs: boolean;
  }>;

  return data.map((p) => ({
    id: p.id,
    name: p.name,
    trackCount: p.track_count,
    imageUrl: p.image_url,
    isLikedSongs: p.is_liked_songs,
  }));
}

export async function generatePlaylist(
  accessToken: string,
  playlistId: string,
  prompt: string,
  size: number,
): Promise<GenerateResult> {
  const resp = await fetch(`${BACKEND_URL}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ playlist_id: playlistId, prompt, size, access_token: accessToken }),
  });

  if (resp.status === 401) throw makeError("auth_failure", "Spotify token expired");
  if (resp.status === 429) throw makeError("rate_limit", "Spotify rate limit — please wait");
  if (resp.status === 422) throw makeError("empty_result", "No tracks matched your prompt");
  if (!resp.ok) throw makeError("server_error", "Generation failed");

  const data = (await resp.json()) as {
    playlist_url: string;
    playlist_name: string;
    track_count: number;
  };

  return {
    playlistUrl: data.playlist_url,
    playlistName: data.playlist_name,
    trackCount: data.track_count,
  };
}

export async function submitFeedback(
  playlistId: string,
  prompt: string,
  resultTrackIds: string[],
  rating: "up" | "down",
): Promise<void> {
  await fetch(`${BACKEND_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      playlist_id: playlistId,
      prompt,
      result_track_ids: resultTrackIds,
      rating,
    }),
  });
}
