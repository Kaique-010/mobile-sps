import { StyleSheet } from 'react-native'

export const parametrosStyles = StyleSheet.create({
  // Container principal
  container: {
    flex: 1,
    backgroundColor: '#233138',
  },

  // Loading
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  // Botões
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 10,
    margin: 25,
    borderRadius: 5,
    backgroundColor: '#dfb018',
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    marginLeft: 5,
  },
  // Texto
  text: {
    fontSize: 16,
    color: '#333',
    margin: 10,
  },
})
