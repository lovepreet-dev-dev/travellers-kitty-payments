import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import NextPaymentScreen from './src/NextPaymentScreen';

export default function App() {
  return (
    <SafeAreaProvider>
      <NextPaymentScreen />
      <StatusBar style="dark" />
    </SafeAreaProvider>
  );
}
