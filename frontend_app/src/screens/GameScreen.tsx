import React, { useEffect, useState } from 'react';
import { View, Text, Image, TextInput, TouchableOpacity, ScrollView, Platform, PanResponder, KeyboardAvoidingView, Keyboard, useWindowDimensions } from 'react-native';
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
    Search,
    PlusCircle,
    Flag,
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
        errorMessage,
        setErrorMessage,
        searchQuery,
        searchResults,
        startGame,
        selectActor,
        search,
    } = useGame();

    const [timeLeft, setTimeLeft] = useState(3);
    const { height: screenHeight } = useWindowDimensions();

    useEffect(() => {
        let interval: ReturnType<typeof setInterval>;
        if (errorMessage) {
            setTimeLeft(3);
            interval = setInterval(() => {
                setTimeLeft((prev: number) => {
                    if (prev <= 1) {
                        setErrorMessage(null);
                        return 3;
                    }
                    return prev - 1;
                });
            }, 1000);
        }
        return () => clearInterval(interval);
    }, [errorMessage, setErrorMessage]);

    // Simple swipe detection
    const panResponder = React.useRef(
        PanResponder.create({
            onStartShouldSetPanResponder: () => true,
            onMoveShouldSetPanResponder: (_, gestureState) => {
                // Determine if it's a horizontal swipe
                return Math.abs(gestureState.dx) > 20;
            },
            onPanResponderRelease: (_, gestureState) => {
                if (gestureState.dx < -50) {
                    // Swipe Left -> Dismiss
                    setErrorMessage(null);
                }
            },
        })
    ).current;

    const scrollViewRef = React.useRef<ScrollView>(null);
    const slotOffsets = React.useRef<{ [key: string]: number }>({});
    const measuredSlotsCount = React.useRef(0); // Count how many slots have been measured
    const scrollY = React.useRef(0);
    const savedScrollY = React.useRef(0);
    const focusedScrollY = React.useRef(0); // Position we scrolled to when focusing
    const isProgrammaticScroll = React.useRef(false); // Flag to prevent snap-back loops
    const lastFocusedIndex = React.useRef<number | null>(null);

    // Dynamic GAP Calculation
    const HEADER_HEIGHT = 70; // Header + Padding
    const CARD_HEIGHT = 160; // Card + Margins
    const SAFE_AREA_VERTICAL = 90; // Top + Bottom Safe Area approx
    const CHAIN_PADDING_VERTICAL = 20; // top + bottom padding of chain container

    // Space available for the ACTOR SLOTS only
    const availableForChain = screenHeight - HEADER_HEIGHT - CARD_HEIGHT - SAFE_AREA_VERTICAL - CHAIN_PADDING_VERTICAL;
    const slotHeight = 64; // h-16 = 64px
    const totalSlotsHeight = chain.length * slotHeight;

    // Calculate gap to fill the space
    const calculatedGap = (availableForChain - totalSlotsHeight) / (Math.max(1, chain.length - 1));
    // Clamp gap: minimum 12 (readable), maximum 40 (don't float too much if few items)
    const dynamicGap = Math.max(12, Math.min(40, calculatedGap));

    // Height to add when focused to allow scrolling any item to top
    // Must be full screen height so last slot can reach first slot position
    const EXTRA_SCROLL_HEIGHT = screenHeight;

    // Used to trigger re-render for padding
    const [paddingBottom, setPaddingBottom] = useState(100);

    const isSwitchingFocus = React.useRef(false);

    const handleSlotPress = (index: number) => {
        isSwitchingFocus.current = true;
        setFocusedIndex(index);
        // Reset flag after a delay in case keyboard didn't hide/show as expected
        setTimeout(() => {
            isSwitchingFocus.current = false;
        }, 500);
    };

    const handleScroll = (event: any) => {
        scrollY.current = event.nativeEvent.contentOffset.y;
    };

    // Scroll to put focused slot at the position of first slot
    const scrollToSlot = (index: number) => {
        // Use measured position - scroll so this slot appears at top (where slot 0 is)
        const targetSlotY = slotOffsets.current[index];
        const firstSlotY = slotOffsets.current[0];

        console.log('=== SCROLL DEBUG ===');
        console.log('First slot (0) position:', firstSlotY);
        console.log('Target slot (' + index + ') position:', targetSlotY);
        console.log('All slot offsets:', JSON.stringify(slotOffsets.current));

        if (targetSlotY !== undefined && firstSlotY !== undefined) {
            // Scroll by the DIFFERENCE to put target slot where first slot was
            const scrollOffset = targetSlotY - firstSlotY;
            console.log('Scrolling to offset:', scrollOffset);

            // SAVE this position so we can return to it after manual swipes
            focusedScrollY.current = scrollOffset;
            // Mark as programmatic scroll to prevent snap-back loop
            isProgrammaticScroll.current = true;
            scrollViewRef.current?.scrollTo({ y: scrollOffset, animated: true });
            // Reset flag after animation
            setTimeout(() => { isProgrammaticScroll.current = false; }, 400);
        }
    };

    // Restore scroll to original position
    const restoreScroll = () => {
        scrollViewRef.current?.scrollTo({ y: savedScrollY.current, animated: true });
        setTimeout(() => setPaddingBottom(100), 300);
    };

    // Keyboard listener - detect when keyboard hides (for ANY reason)
    useEffect(() => {
        const keyboardHideListener = Keyboard.addListener(
            Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide',
            () => {
                // Only restore if we're not switching between slots
                if (!isSwitchingFocus.current && focusedIndex !== null) {
                    setFocusedIndex(null);
                }
            }
        );

        return () => {
            keyboardHideListener.remove();
        };
    }, [focusedIndex, setFocusedIndex]);

    // Handle focus changes
    useEffect(() => {
        if (focusedIndex !== null) {
            // ENTERING FOCUS or SWITCHING FOCUS
            if (lastFocusedIndex.current === null) {
                // First time entering focus - save current scroll position
                savedScrollY.current = scrollY.current;
            }

            // 1. Expand scrollable area immediately
            setPaddingBottom(EXTRA_SCROLL_HEIGHT);

            // 2. Scroll to target after a tick to let layout update
            setTimeout(() => {
                scrollToSlot(focusedIndex);
            }, 50);

        } else {
            // EXITING FOCUS (keyboard hidden)
            if (lastFocusedIndex.current !== null) {
                restoreScroll();
            }
        }
        lastFocusedIndex.current = focusedIndex;
    }, [focusedIndex]);

    return (
        <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            className="flex-1 bg-[#F5F3FF]"
        >
            <View className="flex-1 relative overflow-hidden">
                {/* Decorative Icon - Yellow Star */}
                <View className="absolute top-12 left-8 z-0">
                    <Star size={48} color="rgba(251, 191, 36, 0.2)" fill="rgba(251, 191, 36, 0.2)" />
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

                    {/* Challenge Card - OUTSIDE ScrollView */}
                    <View className="px-6 mb-4">
                        <View className="bg-white rounded-3xl p-5 shadow-lg border-2 border-[#C4B5FD] relative overflow-hidden">
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
                    </View>


                    {/* Main Content */}
                    <ScrollView
                        ref={scrollViewRef}
                        className="flex-1 px-6 relative z-10"
                        showsVerticalScrollIndicator={false}
                        keyboardShouldPersistTaps="handled"
                        contentContainerStyle={{ flexGrow: 1, paddingTop: 12, paddingBottom: 20 }}
                        onScroll={handleScroll}
                        scrollEventThrottle={16}
                        onScrollEndDrag={() => {
                            // After user releases swipe, snap back
                            if (!isProgrammaticScroll.current) {
                                isProgrammaticScroll.current = true;
                                // If focused, snap to focused position; otherwise snap to 0
                                const targetY = focusedIndex !== null ? focusedScrollY.current : 0;
                                scrollViewRef.current?.scrollTo({ y: targetY, animated: true });
                                setTimeout(() => { isProgrammaticScroll.current = false; }, 400);
                            }
                        }}
                        onMomentumScrollEnd={() => {
                            // After momentum scroll ends, snap back
                            if (!isProgrammaticScroll.current) {
                                isProgrammaticScroll.current = true;
                                // If focused, snap to focused position; otherwise snap to 0
                                const targetY = focusedIndex !== null ? focusedScrollY.current : 0;
                                scrollViewRef.current?.scrollTo({ y: targetY, animated: true });
                                setTimeout(() => { isProgrammaticScroll.current = false; }, 400);
                            }
                        }}
                    >
                        {/* Chain */}
                        <View
                            className="relative pl-4 pr-2 py-2"
                            style={{ gap: dynamicGap }}
                            onLayout={(event) => {
                                slotOffsets.current['container'] = event.nativeEvent.layout.y;
                            }}
                        >


                            {chain.map((actor, index) => {
                                const isStart = index === 0;
                                const isTarget = index === chain.length - 1;
                                const isFocused = focusedIndex === index;

                                return (
                                    <View
                                        key={index}
                                        onLayout={(event) => {
                                            // Store slot position only ONCE - check if this slot already measured
                                            if (slotOffsets.current[index] === undefined) {
                                                slotOffsets.current[index] = event.nativeEvent.layout.y;
                                                measuredSlotsCount.current++;
                                                console.log('Slot', index, 'measured at Y:', event.nativeEvent.layout.y);
                                            }
                                        }}
                                    >
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
                                                        onPress={() => handleSlotPress(index)}
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
                        {/* Dynamic Padding */}
                        <View style={{ height: paddingBottom }} />
                    </ScrollView>
                </SafeAreaView>

                {/* Error Toast Notification */}
                {errorMessage && (
                    <View className="absolute bottom-10 left-4 right-4 z-50" {...panResponder.panHandlers}>
                        <View className="bg-[#EF4444] p-4 rounded-2xl shadow-xl border border-red-300 flex-row items-center justify-between">
                            <View className="flex-row items-center gap-3 flex-1">
                                <XCircle size={24} color="white" fill="white" />
                                <Text className="text-white font-bold flex-1">{errorMessage}</Text>
                            </View>
                            <TouchableOpacity onPress={() => setErrorMessage(null)}>
                                <Text className="text-white/80 font-bold text-xs uppercase ml-2">Dismiss ({timeLeft})</Text>
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
        </KeyboardAvoidingView>
    );
};
