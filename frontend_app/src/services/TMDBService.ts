import { Actor, ActorResponse, MovieResponse } from '../types';

import { TMDB_API_KEY } from '@env';

// const API_KEY = process.env.TMDB_API_KEY; // react-native-dotenv uses import
const BASE_URL = "https://api.themoviedb.org/3";

export class TMDBService {
    // Configuration
    private topActorsCount = 100;
    private minHandshakes = 2;
    private maxHandshakes = 6;

    private cachedPopularActors: Actor[] | null = null;

    private async fetch<T>(endpoint: string): Promise<T | null> {
        try {
            const response = await fetch(`${BASE_URL}${endpoint}`, {
                headers: {
                    'Authorization': `Bearer ${TMDB_API_KEY}`,
                    'accept': 'application/json'
                }
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error(`Error fetching ${endpoint}:`, error);
            return null;
        }
    }

    async searchActors(query: string): Promise<Actor[]> {
        if (!query) return [];
        const encodedQuery = encodeURIComponent(query);
        const data = await this.fetch<ActorResponse>(`/search/person?query=${encodedQuery}`);
        if (!data) return [];

        return data.results.map(r => ({
            id: r.id,
            name: r.name,
            profilePath: r.profile_path,
            popularity: r.popularity
        }));
    }

    async checkConnection(from: Actor, to: Actor): Promise<boolean> {
        const data = await this.fetch<MovieResponse>(`/discover/movie?with_cast=${from.id},${to.id}`);
        if (!data) return false;
        return data.results.length > 0;
    }

    async getPopularActors(): Promise<Actor[]> {
        if (this.cachedPopularActors) return this.cachedPopularActors;

        let allActors: Actor[] = [];
        let currentPage = 1;
        const maxPages = 25;

        while (allActors.length < this.topActorsCount && currentPage <= maxPages) {
            const data = await this.fetch<ActorResponse>(`/person/popular?page=${currentPage}`);
            if (!data) break;

            const actors = data.results.map(r => ({
                id: r.id,
                name: r.name,
                profilePath: r.profile_path,
                popularity: r.popularity
            }));

            allActors = [...allActors, ...actors];
            currentPage++;
            // standard fetch doesn't need sleep as much as swift loop, but let's be nice
        }

        // Sort by popularity and take top
        this.cachedPopularActors = allActors
            .sort((a, b) => b.popularity - a.popularity)
            .slice(0, this.topActorsCount);

        return this.cachedPopularActors;
    }

    async selectRandomActors(): Promise<{ start: Actor, target: Actor, handshakes: number }> {
        const actors = await this.getPopularActors();

        if (actors.length < 2) {
            return {
                start: { id: 1, name: "Actor 1", profilePath: null, popularity: 0 },
                target: { id: 2, name: "Actor 2", profilePath: null, popularity: 0 },
                handshakes: 2
            };
        }

        const start = actors[Math.floor(Math.random() * actors.length)];
        let target = actors[Math.floor(Math.random() * actors.length)];

        while (target.id === start.id) {
            target = actors[Math.floor(Math.random() * actors.length)];
        }

        // Logic from swift: random handshakes between min and max
        // Note: The swift code picked random actors then ASSIGNED a random handshake count.
        // It did NOT verify a path exists of that length in selectRandomActors (it just returns start, target, handshakes).
        // The previous swift code removed path validation.
        const handshakes = Math.floor(Math.random() * (this.maxHandshakes - this.minHandshakes + 1)) + this.minHandshakes;

        return { start, target, handshakes };
    }
}

export const tmdbService = new TMDBService();
