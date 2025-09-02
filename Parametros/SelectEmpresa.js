import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  FlatList,
  Modal,
  ActivityIndicator,
} from 'react-native'
import axios from 'axios'
import { BASE_URL, fetchSlugMap, safeSetItem } from '../utils/api'
import AsyncStorage from '@react-native-async-storage/async-storage'
import styles from '../styles/loginStyles'

export default function SelectEmpresa({ navigation }) {
  const [empresas, setEmpresas] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedEmpresa, setSelectedEmpresa] = useState(null)
  const [botaoDesabilitado, setBotaoDesabilitado] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchEmpresas() {
      try {
        // Recupera o token de acesso e o CNPJ do AsyncStorage
        const accessToken = await AsyncStorage.getItem('access')
        const docu = await AsyncStorage.getItem('docu')

        if (!accessToken || !docu) {
          console.error('[ERROR] Token de acesso ou CNPJ não encontrado.')
          setError('Token de acesso ou CNPJ não encontrado.')
          return
        }

        const slugMap = await fetchSlugMap()

        // Acessando diretamente o slug usando o CNPJ como chave
        const slug = slugMap[docu]

        if (slug) {
          console.log('[DEBUG] SLUG:', slug)
          if (!slug) {
            console.error('[ERROR] Slug não encontrado para o CNPJ:', docu)
            setError('CNPJ não encontrado no mapa de licenças.')
            setLoading(false)
            return
          }

          // agora usa o slug aqui embaixo:
          const response = await axios.get(
            `${BASE_URL}/api/${slug}/licencas/empresas/?limit=50&offset=50`,
            {
              headers: {
                Authorization: `Bearer ${accessToken}`,
                'X-CNPJ': docu,
              },
            }
          )

          if (response.data && Array.isArray(response.data)) {
            setEmpresas(response.data)
          } else {
            setError('Nenhuma empresa encontrada.')
          }
        } else {
          console.error('CNPJ não encontrado no mapa')
          setError('CNPJ não encontrado no mapa de licenças.')
        }
      } catch (error) {
        console.error(
          'Erro ao carregar empresas:',
          error.response || error.message
        )
        setError('Erro ao carregar empresas. Tente novamente.')
      } finally {
        setLoading(false)
      }
    }

    fetchEmpresas()
  }, []) // Recarrega as empresas uma vez quando a tela for montada

  const handleSelectEmpresa = async (item) => {
    const empresaId = item.empr_codi
    const empresaNome = item.empr_nome
    setBotaoDesabilitado(true)

    try {
      // Salvando a empresa selecionada no AsyncStorage
      await safeSetItem('empresaId', empresaId.toString())
      await safeSetItem('empresaNome', empresaNome) // Salvando o nome também

      // Navega para a próxima tela após salvar a empresa
      navigation.navigate('SelectFilial', {
        empresaId,
        empresaNome,
      })
    } catch (error) {
      console.error('Erro ao salvar empresa:', error)
      setError('Erro ao salvar a empresa. Tente novamente.')
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
      <Text style={styles.text}>Selecione a Empresa</Text>
      {/* Exibindo erro, caso haja algum */}
      {error && <Text style={styles.errorText}>{error}</Text>}

      <FlatList
        data={empresas}
        keyExtractor={(item) => item.empr_codi.toString()}
        renderItem={({ item }) => (
          <TouchableOpacity
            disabled={botaoDesabilitado}
            onPress={() => handleSelectEmpresa(item)}
            style={styles.button}>
            <Text style={styles.buttonText}>
              {item.empr_codi} - {item.empr_nome}
            </Text>
          </TouchableOpacity>
        )}
      />
    </View>
  )
}
