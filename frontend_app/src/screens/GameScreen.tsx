import React, { useEffect } from 'react';
import { View, Text, Image, TextInput, TouchableOpacity, ScrollView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import LinearGradient from 'react-native-linear-gradient';
import {
    Star,
    Film,
    Video,
    Settings,
    Clock,
    Play,
    XCircle,
    Menu,
    Search,
    PlusCircle,
    Flag,
    Link2,
    BadgeCheck,
} from 'lucide-react-native';
import { Actor, GameState } from '../types';
import { useGame } from '../hooks/useGame';

const IMAGE_BASE_URL = 'https://ggrhecslgdflloszjkwl.supabase.co/storage/v1/object/public/generation-assets/photos/artists-portfolios/portrait/3.webp'; // Placeholder fallback
// In real app, use actor.profilePath with TMDB image base url

const TMDB_IMAGE_URL = 'https://image.tmdb.org/t/p/w185';

const ActorImage = ({ path }: { path: string | null }) => {
    const uri = path ? `${TMDB_IMAGE_URL}${path}` : IMAGE_BASE_URL;
    return (
        <Image
            source={{ uri }}
            className="w-full h-full object-cover"
            resizeMode="cover"
        />
    );
};

export const GameScreen = () => {
    const {
        chain,
        focusedIndex,
        setFocusedIndex,
        gameState,
        loading,
        errorMessage,
        setErrorMessage,
        searchQuery,
        searchResults,
        startGame,
        selectActor,
        search,
    } = useGame();

    useEffect(() => {
        if (errorMessage) {
            // Auto dismiss after 3 seconds if not dismissed manually (optional, but requested behavior was swipe/manual, let's just make it a visual popup)
            const timer = setTimeout(() => setErrorMessage(null), 4000);
            return () => clearTimeout(timer);
        }
    }, [errorMessage, setErrorMessage]);

    return (
        <View className="flex-1 bg-[#F5F3FF] relative overflow-hidden">
            {/* Background Gradient */}
            <View className="absolute top-0 left-0 w-full h-64 z-0 pointer-events-none">
                <LinearGradient
                    colors={['rgba(124,58,237,0.1)', 'transparent']}
                    style={{ width: '100%', height: '100%' }}
                />
            </View>

            {/* Decorative Icons */}
            <View className="absolute top-12 left-8 z-0">
                <Star size={48} color="rgba(251, 191, 36, 0.2)" fill="rgba(251, 191, 36, 0.2)" />
            </View>
            <View className="absolute top-24 right-6 z-0">
                <Star size={32} color="rgba(251, 191, 36, 0.3)" fill="rgba(251, 191, 36, 0.3)" />
            </View>
            <View className="absolute bottom-20 -left-6 z-0 transform rotate-12">
                <Film size={128} color="rgba(124, 58, 237, 0.05)" />
            </View>

            <SafeAreaView edges={['top']} className="flex-1">
                {/* Header */}
                <View className="relative z-10 px-6 pt-4 pb-4 flex-row items-center justify-between">
                    <View className="flex-row items-center gap-2">
                        <View className="bg-[#7C3AED] p-2 rounded-xl shadow-sm">
                            <Video size={24} color="white" fill="white" />
                        </View>
                        <Text className="text-2xl font-bold text-[#2E1065]">CineLink</Text>
                    </View>
                    <View className="flex-row items-center gap-3">
                        <TouchableOpacity onPress={startGame} className="bg-white px-3 py-1.5 rounded-full border border-[#C4B5FD] shadow-sm flex-row items-center gap-1">
                            <Play size={14} color="#7C3AED" fill="#7C3AED" />
                            <Text className="font-bold text-xs text-[#7C3AED]">New Game</Text>
                        </TouchableOpacity>
                        <View className="flex-row items-center gap-1 bg-white px-3 py-1.5 rounded-full border border-[#C4B5FD] shadow-sm">
                            <Star size={16} color="#FBBF24" fill="#FBBF24" />
                            <Text className="font-bold text-sm text-[#2E1065]">1,250</Text>
                        </View>
                    </View>
                </View>

                {/* Main Content */}
                <ScrollView
                    className="flex-1 px-6 pb-24 relative z-10"
                    showsVerticalScrollIndicator={false}
                    keyboardShouldPersistTaps="handled"
                    contentContainerStyle={{ paddingBottom: 100, flexGrow: 1 }}
                >
                    {/* Challenge Card */}
                    <View className="bg-white rounded-3xl p-5 shadow-lg border-2 border-[#C4B5FD] mb-8 relative overflow-hidden">
                        <View className="absolute top-0 left-0 w-full h-2">
                            <LinearGradient
                                start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
                                colors={['#FBBF24', '#F472B6', '#7C3AED']}
                                style={{ flex: 1 }}
                            />
                        </View>

                        <View className="flex-row justify-between items-start mb-2 mt-2">
                            <View className="bg-[#EDE9FE] px-3 py-1 rounded-full">
                                <Text className="text-xs font-bold uppercase tracking-wider text-[#6D28D9]">Daily Challenge</Text>
                            </View>
                            <View className="flex-row items-center gap-1">
                                <Clock size={14} color="#6D28D9" />
                                <Text className="text-xs font-medium text-[#6D28D9]">12h left</Text>
                            </View>
                        </View>

                        <View className="mt-4 flex-row justify-center">
                            <Text className="text-[#6D28D9] font-medium text-center">
                                Connect <Text className="font-bold">{chain[0]?.name}</Text> to <Text className="font-bold">{chain[chain.length - 1]?.name}</Text> using <Text className="font-bold">{chain.length - 1}</Text> handshakes
                            </Text>
                        </View>
                    </View>

                    {/* Chain */}
                    <View className="relative pl-4 pr-2 flex-1 justify-evenly min-h-[50%]">
                        {/* Dotted Line */}
                        <View className="absolute left-[3.25rem] top-8 bottom-12 w-3 bg-[#E9D5FF] rounded-full -z-10 flex-col items-center py-2 gap-2 overflow-hidden opacity-50">
                            {/* Visual guide */}
                        </View>

                        {chain.map((actor, index) => {
                            const isStart = index === 0;
                            const isTarget = index === chain.length - 1;
                            const isFocused = focusedIndex === index;

                            return (
                                <View key={index} className="mb-4">
                                    <View className="flex-row items-center gap-4">
                                        {/* Avatar Circle */}
                                        <View className={`relative z-10 w-16 h-16 rounded-full border-4 ${isFocused ? 'border-[#7C3AED]' : 'border-white'} ${actor ? '' : 'bg-[#F3F0FF] border-dashed'} shadow-lg flex items-center justify-center`}>
                                            {actor ? (
                                                <View className="rounded-full overflow-hidden w-full h-full">
                                                    <ActorImage path={actor.profilePath} />
                                                </View>
                                            ) : (
                                                <Text className="text-xl font-bold text-[#C4B5FD]">{index}</Text>
                                            )}

                                            {/* Indicators */}
                                            {isStart && (
                                                <View className="absolute -top-1 -left-1 bg-[#FBBF24] rounded-full p-1 border-2 border-white">
                                                    <Play size={12} color="#451A03" fill="#451A03" />
                                                </View>
                                            )}
                                            {isTarget && (
                                                <View className="absolute -top-1 -left-1 bg-[#7C3AED] rounded-full p-1 border-2 border-white">
                                                    <Flag size={12} color="white" fill="white" />
                                                </View>
                                            )}
                                        </View>

                                        {/* Content Box */}
                                        <View className="flex-1">
                                            {/* If focused, show Search Input */}
                                            {isFocused ? (
                                                <View className="relative z-20">
                                                    <TextInput
                                                        value={searchQuery}
                                                        onChangeText={search}
                                                        placeholder={isStart || isTarget ? "Replace actor..." : "Search actor..."}
                                                        placeholderTextColor="#C4B5FD"
                                                        className="w-full pl-4 pr-10 py-3.5 bg-white border-2 border-[#7C3AED] rounded-2xl shadow-md text-[#2E1065] font-medium"
                                                        autoFocus
                                                    />
                                                    <View className="absolute right-3 top-3.5">
                                                        {searchQuery.length > 0 ? (
                                                            <TouchableOpacity onPress={() => search('')} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
                                                                <XCircle size={20} color="#7C3AED" fill="#E9D5FF" />
                                                            </TouchableOpacity>
                                                        ) : (
                                                            <Search size={20} color="#7C3AED" />
                                                        )}
                                                    </View>

                                                    {/* Dropdown */}
                                                    {searchResults.length > 0 && (
                                                        <View className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl shadow-xl border border-[#E9D5FF] overflow-hidden z-50 max-h-60">
                                                            <ScrollView nestedScrollEnabled keyboardShouldPersistTaps="always">
                                                                {searchResults.map((result) => (
                                                                    <TouchableOpacity
                                                                        key={result.id}
                                                                        onPress={() => selectActor(result)}
                                                                        className="flex-row items-center gap-3 p-3 border-b border-gray-100 active:bg-[#F3F0FF]"
                                                                    >
                                                                        <View className="w-8 h-8 rounded-full bg-gray-200 overflow-hidden">
                                                                            <ActorImage path={result.profilePath} />
                                                                        </View>
                                                                        <View className="flex-1">
                                                                            <Text className="font-bold text-sm text-[#2E1065]">{result.name}</Text>
                                                                        </View>
                                                                        <PlusCircle size={20} color="#7C3AED" />
                                                                    </TouchableOpacity>
                                                                ))}
                                                            </ScrollView>
                                                        </View>
                                                    )}
                                                </View>
                                            ) : (
                                                /* If NOT focused, show Card or Empty State Action */
                                                <TouchableOpacity
                                                    onPress={() => setFocusedIndex(index)}
                                                    className={`px-4 py-3 rounded-2xl shadow-sm border ${actor ? 'bg-white border-[#E9D5FF]' : 'bg-[#F9FAFB] border-dashed border-[#C4B5FD]'} flex-row items-center justify-between`}
                                                >
                                                    <View>
                                                        {actor ? (
                                                            <>
                                                                <Text className="font-bold text-[#2E1065]">{actor.name}</Text>
                                                                <Text className="text-xs text-[#6D28D9]">
                                                                    {isStart ? "Start Actor" : isTarget ? "Target Actor" : "Connected"}
                                                                </Text>
                                                            </>
                                                        ) : (
                                                            <Text className="text-[#7C3AED] font-medium">Tap to select actor</Text>
                                                        )}
                                                    </View>

                                                    {/* Action Icon: Edit or Add */}
                                                    {actor ? (
                                                        <Settings size={18} color="#C4B5FD" />
                                                    ) : (
                                                        <PlusCircle size={20} color="#7C3AED" />
                                                    )}
                                                </TouchableOpacity>
                                            )}
                                        </View>
                                    </View>
                                </View>
                            );
                        })}
                    </View>
                </ScrollView>
            </SafeAreaView>

            {/* Error Toast Notification */}
            {errorMessage && (
                <View className="absolute bottom-10 left-4 right-4 z-50 animate-in fade-in slide-in-from-bottom-5">
                    <View className="bg-[#EF4444] p-4 rounded-2xl shadow-xl border border-red-300 flex-row items-center justify-between">
                        <View className="flex-row items-center gap-3 flex-1">
                            <XCircle size={24} color="white" fill="white" />
                            <Text className="text-white font-bold flex-1">{errorMessage}</Text>
                        </View>
                        <TouchableOpacity onPress={() => setErrorMessage(null)}>
                            <Text className="text-white/80 font-bold text-xs uppercase ml-2">Dismiss</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            )}

            {/* Win Overlay (Simple for now) */}
            {gameState === GameState.Won && (
                <View className="absolute bottom-10 left-4 right-4 z-50">
                    <View className="bg-green-500 p-4 rounded-2xl shadow-xl flex-row items-center justify-center gap-2">
                        <BadgeCheck size={28} color="white" fill="white" />
                        <Text className="text-white font-black text-xl">YOU WON!</Text>
                    </View>
                </View>
            )}
        </View>
    );
};
