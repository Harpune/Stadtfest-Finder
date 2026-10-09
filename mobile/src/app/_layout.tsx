import {
  Outfit_300Light,
  Outfit_400Regular,
  Outfit_500Medium,
  Outfit_600SemiBold,
  Outfit_700Bold,
} from '@expo-google-fonts/outfit';
import {YoungSerif_400Regular} from '@expo-google-fonts/young-serif';
import {BottomSheetModalProvider} from '@gorhom/bottom-sheet';
import {QueryClientProvider} from '@tanstack/react-query';
import {useFonts} from 'expo-font';
import {Stack} from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import {StatusBar} from 'expo-status-bar';
import React, {useEffect, useState} from 'react';
import {GestureHandlerRootView} from 'react-native-gesture-handler';
import {SafeAreaProvider} from 'react-native-safe-area-context';

import {createQueryClient} from '@/api/client';
import {ToastProvider} from '@/components';
import {AuthProvider} from '@/features/auth/AuthProvider';
import {PushProvider} from '@/features/notifications/PushProvider';
import {ThemeProvider, useTheme} from '@/theme';

SplashScreen.preventAutoHideAsync().catch(() => undefined);

/** Deep links into /f/{id} get the map as stack base, so "Zurück" leads to it (R04-US6). */
export const unstable_settings = {initialRouteName: 'index'};

function ThemedStack() {
  const theme = useTheme();
  return (
    <>
      <StatusBar style={theme.scheme === 'dark' ? 'light' : 'dark'} />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: {backgroundColor: theme.colors.background},
          animation: 'slide_from_right',
        }}
      >
        {/* Login entry slides up as full screen (R05-US1, 380 ms). */}
        <Stack.Screen
          name="login"
          options={{
            presentation: 'fullScreenModal',
            animation: 'slide_from_bottom',
            animationDuration: theme.motion.login.duration,
          }}
        />
        <Stack.Screen name="auth" options={{animation: 'none'}} />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [queryClient] = useState(createQueryClient);
  const [fontsLoaded, fontError] = useFonts({
    YoungSerif_400Regular,
    Outfit_300Light,
    Outfit_400Regular,
    Outfit_500Medium,
    Outfit_600SemiBold,
    Outfit_700Bold,
  });

  useEffect(() => {
    if (fontsLoaded || fontError) {
      SplashScreen.hideAsync().catch(() => undefined);
    }
  }, [fontsLoaded, fontError]);

  if (!fontsLoaded && !fontError) {
    return null;
  }

  return (
    <GestureHandlerRootView style={{flex: 1}}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider>
            <ToastProvider>
              <BottomSheetModalProvider>
                <AuthProvider>
                  <PushProvider>
                    <ThemedStack />
                  </PushProvider>
                </AuthProvider>
              </BottomSheetModalProvider>
            </ToastProvider>
          </ThemeProvider>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
