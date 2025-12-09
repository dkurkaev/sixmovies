export interface Actor {
    id: number;
    name: string;
    profilePath: string | null;
    popularity: number;
}

export interface Movie {
    id: number; // TMDB uses int IDs usually
    title: string;
    releaseDate?: string;
}

export enum GameState {
    Playing = 'playing',
    Won = 'won',
    Lost = 'lost',
}

export interface TMDBResponse<T> {
    page: number;
    results: T[];
    total_pages: number;
    total_results: number;
}

export type ActorResponse = TMDBResponse<{
    id: number;
    name: string;
    profile_path: string | null;
    popularity: number;
}>;

export type MovieResponse = TMDBResponse<{
    id: number;
    title: string;
    release_date: string;
    cast?: any[];
}>;
