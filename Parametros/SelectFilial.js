import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  Alert, // Importando Alert para mostrar mensagens de erro
} from 'react-native'
import { BASE_URL, fetchSlugMap, safeSetItem } from '../utils/api'
import axios from 'axios'
import { getModulosComPermissao } from '../utils/modulosComPermissao'
import AsyncStorage from '@react-native-async-storage/async-storage'
import styles from '../styles/loginStyles'

export default function SelectFilial({ route, navigation }) {
  const { empresaId, empresaNome } = route.params
  const [filiais, setFiliais] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchFiliais() {
      try {
        const accessToken = await AsyncStorage.getItem('access')
        const docu = await AsyncStorage.getItem('docu')

        const slugMap = await fetchSlugMap()

        // Acessando diretamente o slug usando o CNPJ como chave
        const slug = slugMap[docu]

        if (!accessToken) {
          console.error('[ERROR] Token de acesso não encontrado.')
          return
        }

        if (!slug) {
          // Corrigindo a condição aqui
          console.error('[ERROR] Slug não encontrado para o CNPJ.')
          Alert.alert('Erro', 'CNPJ não encontrado no mapa de licenças.')
          setLoading(false)
          return
        }

        // Ajuste na URL para refletir o parâmetro correto
        const response = await axios.get(
          `${BASE_URL}/api/${slug}/licencas/filiais/?empresa_id=${empresaId}`,
          {
            headers: {
              Authorization: `Bearer ${accessToken}`,
              'X-CNPJ': docu,
            },
          }
        )

        setFiliais(response.data)
      } catch (error) {
        console.error(
          'Erro ao carregar filiais:',
          error.response?.data || error.message
        )
        Alert.alert('Erro', 'Erro ao carregar filiais. Tente novamente.')
      } finally {
        setLoading(false)
      }
    }

    fetchFiliais()
  }, [empresaId])

  const [botaoDesabilitado, setBotaoDesabilitado] = useState(false)

  const handleSelectFilial = async (filialId, filialNome) => {
    if (botaoDesabilitado) return setBotaoDesabilitado(true)

    try {
      await AsyncStorage.multiSet([
        ['empresaId', empresaId.toString()],
        ['empresaNome', empresaNome],
        ['filialId', filialId.toString()],
        ['filialNome', filialNome],
      ])

      const modulosPermitidos = await getModulosComPermissao()

      if (modulosPermitidos && modulosPermitidos.length > 0) {
        await safeSetItem('modulos', JSON.stringify(modulosPermitidos))

        // Verificar se foram salvos corretamente
        const modulosSalvos = await AsyncStorage.getItem('modulos')
      } else {
        await safeSetItem('modulos', JSON.stringify([]))
      }

      navigation.navigate('MainApp')
    } catch (error) {
      console.error('Erro ao salvar filial selecionada:', error)
      Alert.alert('Erro', 'Erro ao salvar filial. Tente novamente.')
    }
  }

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" />
      </View>
    )
  }

  return (
    <View style={styles.container}>
      <Text style={styles.text}>Selecione a Filial</Text>
      <FlatList
        data={filiais}
        keyExtractor={(item) =>
          item.empr_codi ? item.empr_codi.toString() : 'default-key'
        } // Verificando se existe empr_codi
        renderItem={({ item }) => (
          <TouchableOpacity
            disabled={botaoDesabilitado}
            onPress={() => handleSelectFilial(item.empr_codi, item.empr_nome)}
            style={[styles.button, botaoDesabilitado && styles.buttonDisabled]}>
            <Text style={styles.buttonText}>
              {item.empr_codi} - {item.empr_nome}
            </Text>
          </TouchableOpacity>
        )}
      />
    </View>
  )
}
