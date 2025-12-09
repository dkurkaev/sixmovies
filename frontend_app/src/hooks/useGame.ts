import { useState, useCallback, useEffect } from 'react';
import { Actor, GameState } from '../types';
import { tmdbService } from '../services/TMDBService';

const DUMMY_ACTOR: Actor = { id: 0, name: 'Loading...', profilePath: null, popularity: 0 };

export const useGame = () => {
    const [chain, setChain] = useState<(Actor | null)[]>([]);
    const [focusedIndex, setFocusedIndex] = useState<number | null>(null); // Which slot is being edited
    const [gameState, setGameState] = useState<GameState>(GameState.Playing);
    const [loading, setLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<Actor[]>([]);

    const startGame = useCallback(async () => {
        setLoading(true);
        try {
            const { start, target, handshakes } = await tmdbService.selectRandomActors();
            // handshakes = degrees (links). Actors = degrees + 1
            const chainLength = handshakes + 1;
            const newChain = new Array(chainLength).fill(null);
            newChain[0] = start;
            newChain[chainLength - 1] = target;

            setChain(newChain);
            setFocusedIndex(null); // Or 1? No, let user choose.
            setGameState(GameState.Playing);
            setErrorMessage(null);
            setSearchQuery('');
            setSearchResults([]);
        } catch (error) {
            setErrorMessage("Failed to start game");
            console.error(error);
        } finally {
            setLoading(false);
        }
    }, []);

    const validateConnection = async (actor1: Actor, actor2: Actor): Promise<boolean> => {
        return await tmdbService.checkConnection(actor1, actor2);
    };

    const replaceAnchor = async (actor: Actor, index: number) => {
        // Reset chain but keep the new anchor and the *other* anchor
        if (index !== 0 && index !== chain.length - 1) return; // Should allow replacing intermediates? Yes, handled in selectActor

        setLoading(true);
        const newChain = new Array(chain.length).fill(null);

        if (index === 0) {
            newChain[0] = actor;
            newChain[chain.length - 1] = chain[chain.length - 1]; // Keep Target
        } else {
            newChain[0] = chain[0]; // Keep Start
            newChain[chain.length - 1] = actor;
        }

        setChain(newChain);
        setSearchQuery('');
        setSearchResults([]);
        setFocusedIndex(null);
        setGameState(GameState.Playing);
        setLoading(false);
    };

    const selectActor = useCallback(async (actor: Actor) => {
        if (focusedIndex === null) return;

        // Cannot replace Start or Target via normal select, they use replaceAnchor
        if (focusedIndex === 0 || focusedIndex === chain.length - 1) {
            // Should verify if this flow allows editing start/target? 
            // Plan says "Slot 0 (Start): Show Actor + 'Edit' button."
            // If we use the SAME search flow, we need to handle it.
            // But for safety, distinct function for anchors is better to warn about reset.
            // Let's assume selectActor is for filling empty slots or replacing intermediates.
            // If focusedIndex IS 0/Target, we treat it as "Connect to NEW anchor", which implies reset.
            // Let's handle generic replacement here, but triggering reset if index is 0 or len-1.
            await replaceAnchor(actor, focusedIndex);
            return;
        }

        setLoading(true);
        setErrorMessage(null);

        try {
            // Validate with Left Node (if exists/filled)
            const leftIndex = focusedIndex - 1;
            if (leftIndex >= 0 && chain[leftIndex]) {
                const isConnected = await validateConnection(chain[leftIndex]!, actor);
                if (!isConnected) {
                    setErrorMessage(`No connection found between ${chain[leftIndex]!.name} and ${actor.name}.`);
                    setLoading(false);
                    return;
                }
            }

            // Validate with Right Node (if exists/filled)
            const rightIndex = focusedIndex + 1;
            if (rightIndex < chain.length && chain[rightIndex]) {
                const isConnected = await validateConnection(actor, chain[rightIndex]!);
                if (!isConnected) {
                    // Logic: If user is filling a bridge, it must connect to both.
                    setErrorMessage(`No connection found between ${actor.name} and ${chain[rightIndex]!.name}.`);
                    setLoading(false);
                    return;
                }
            }

            // If valid, update chain
            const newChain = [...chain];
            newChain[focusedIndex] = actor;
            setChain(newChain);
            setSearchQuery('');
            setSearchResults([]);
            setFocusedIndex(null); // Deselect

            // Check Win Condition
            if (newChain.every(a => a !== null)) {
                // If all filled, simplified check (since we validated on entry)
                // But we should double check the whole chain integrity just in case? 
                // Since we validate neighbours on insert, it should be fine.
                setGameState(GameState.Won);
            }

        } catch (error) {
            setErrorMessage("Error validating connection");
            console.error(error);
        } finally {
            setLoading(false);
        }
    }, [chain, focusedIndex]);

    const search = useCallback(async (query: string) => {
        setSearchQuery(query);
        if (query.length < 3) {
            setSearchResults([]);
            return;
        }
        try {
            const results = await tmdbService.searchActors(query);
            // Filter out already in chain
            const usedIds = new Set(chain.filter(a => a !== null).map(a => a!.id));
            setSearchResults(results.filter(a => !usedIds.has(a.id)));
        } catch (error) {
            console.error("Search error", error);
        }
    }, [chain]);

    // Initial start
    useEffect(() => {
        startGame();
    }, []); // eslint-ignore-line react-hooks/exhaustive-deps

    return {
        chain,
        focusedIndex,
        setFocusedIndex,
        gameState,
        loading,
        errorMessage,
        setErrorMessage, // Export setter for dismissing toast
        searchQuery,
        searchResults,
        startGame,
        selectActor,
        search,
    };
};
