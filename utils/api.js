import AsyncStorage from '@react-native-async-storage/async-storage'

// Use 10.0.2.2 for Android Emulator, localhost for iOS Simulator
// Or your machine's IP address for physical device
export const BASE_URL = 'http://10.0.2.2:8000' 

export const safeSetItem = async (key, value) => {
  try {
    await AsyncStorage.setItem(key, value)
  } catch (e) {
    console.error('Error saving to AsyncStorage', e)
  }
}

export const fetchSlugMap = async () => {
  try {
    const response = await fetch(`${BASE_URL}/licencas.json`)
    if (!response.ok) return {}
    return await response.json()
  } catch (e) {
    console.error('Error fetching slug map', e)
    return {}
  }
}
