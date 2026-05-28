export type PopupState = "unauthenticated" | "idle" | "loading" | "result" | "error";

export type ErrorType =
  | "auth_failure"
  | "rate_limit"
  | "empty_result"
  | "server_error"
  | "lyrics_unavailable";

export interface PlaylistItem {
  id: string;
  name: string;
  trackCount: number | null;
  imageUrl: string | null;
  isLikedSongs: boolean;
}

export interface GenerateResult {
  playlistUrl: string;
  playlistName: string;
  trackCount: number;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}
