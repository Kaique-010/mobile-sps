import React, { useEffect, useState } from 'react'
import {
  View,
  Text,
  FlatList,
  Switch,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
} from 'react-native'
import {
  apiGetComContexto,
  apiPatchComContexto,
  apiFetch,
} from '../../utils/api'
import AsyncStorage from '@react-native-async-storage/async-storage'
import Toast from 'react-native-toast-message'

const ParametrosEstoque = () => {
  const [parametros, setParametros] = useState([])
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    buscarParametros()
  }, [])

  const buscarParametros = async () => {
    try {
      console.log('[ParametrosEstoque] Iniciando busca de parâmetros...')

      // Log dos dados do AsyncStorage
      const slug = await AsyncStorage.getItem('slug')
      const empresaId = await AsyncStorage.getItem('empresaId')
      const filialId = await AsyncStorage.getItem('filialId')
      const usuario_id = await AsyncStorage.getItem('usuario_id')

      console.log('[ParametrosEstoque] Dados do AsyncStorage:', {
        slug,
        empresaId,
        filialId,
        usuario_id,
      })

      // Endpoint específico para parâmetros de estoque
      const endpoint = 'parametros-admin/parametros_estoque/'
      console.log('[ParametrosEstoque] Endpoint:', endpoint)
      console.log(
        '[ParametrosEstoque] URL completa será:',
        `/api/${slug}/${endpoint}`
      )

      // A função apiGetComContexto já retorna response.data
      const data = await apiGetComContexto(
        'parametros-admin/parametros-sistema/parametros_estoque/'
      )

      console.log('[ParametrosEstoque] Resposta da API:', data)

      // Verificar se data.parametros existe antes de mapear
      if (!data || !data.parametros) {
        console.error('[ParametrosEstoque] Estrutura de dados inválida:', data)
        throw new Error(
          'Dados de parâmetros não encontrados na resposta da API'
        )
      }

      // Mapear os parâmetros retornados pela API
      const parametrosEstoqueLista = data.parametros.map((param) => ({
        nome: param.descricao,
        chave: param.nome,
        ativo: param.valor === true || param.valor === 'true',
      }))

      console.log(
        '[ParametrosEstoque] Parâmetros processados:',
        parametrosEstoqueLista
      )
      setParametros(parametrosEstoqueLista)
    } catch (error) {
      console.error('[ParametrosEstoque] Erro completo:', error)
      console.error('[ParametrosEstoque] Erro response:', error.response)
      console.error('[ParametrosEstoque] Erro status:', error.response?.status)
      console.error('[ParametrosEstoque] Erro data:', error.response?.data)
      console.error('[ParametrosEstoque] Erro config:', error.config)

      Alert.alert(
        'Erro',
        `Erro ao carregar parâmetros de estoque: ${error.message}`
      )
    } finally {
      setLoading(false)
    }
  }

  const alternarParametro = (chave) => {
    setParametros((prev) =>
      prev.map((param) => {
        if (param.chave === chave) {
          return { ...param, ativo: !param.ativo }
        }
        return param
      })
    )
  }

  const salvarParametros = async () => {
    try {
      console.log('[ParametrosEstoque] Iniciando salvamento...')
      setSalvando(true)

      // Obter dados do AsyncStorage
      const empresaId = await AsyncStorage.getItem('empresaId')
      const filialId = await AsyncStorage.getItem('filialId')

      // Construir payload com os parâmetros e IDs obrigatórios
      const payload = {
        empresa_id: parseInt(empresaId),
        filial_id: parseInt(filialId),
      }

      parametros.forEach((param) => {
        if (param.ativo !== undefined) {
          payload[param.chave] = param.ativo
        }
      })

      console.log('[ParametrosEstoque] Payload para salvar:', payload)

      // Usar apiFetch diretamente para ter controle total
      const response = await apiFetch(
        'api/casaa/parametros-admin/parametros-sistema/parametros_estoque/',
        'patch',
        payload
      )

      console.log(
        '[ParametrosEstoque] Parâmetros salvos com sucesso:',
        response.data
      )
      Alert.alert('Sucesso', 'Parâmetros salvos com sucesso!')
    } catch (error) {
      console.error('[ParametrosEstoque] Erro ao salvar:', error)
      console.error('[ParametrosEstoque] Erro response:', error.response)
      console.error('[ParametrosEstoque] Erro status:', error.response?.status)
      console.error('[ParametrosEstoque] Erro data:', error.response?.data)

      Alert.alert(
        'Erro',
        `Erro ao salvar parâmetros: ${
          error.response?.data?.error || error.message
        }`
      )
    } finally {
      setSalvando(false)
    }
  }

  const renderItem = ({ item }) => (
    <View
      style={{
        backgroundColor: '#2f3e52',
        padding: 15,
        marginBottom: 10,
        borderRadius: 10,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.3,
        shadowRadius: 3,
        elevation: 4,
      }}>
      <Text style={{ color: '#fff', fontSize: 16, fontWeight: '600', flex: 1 }}>
        {item.nome}
      </Text>
      <Switch
        value={item.ativo}
        onValueChange={() => alternarParametro(item.chave)}
        trackColor={{ false: '#777', true: '#34d399' }}
        thumbColor={item.ativo ? '#22c55e' : '#ccc'}
      />
    </View>
  )

  if (loading) {
    return (
      <View
        style={{
          flex: 1,
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: '#243242',
        }}>
        <ActivityIndicator size="large" color="#0ea5e9" />
      </View>
    )
  }

  return (
    <View style={{ flex: 1, padding: 16, backgroundColor: '#243242' }}>
      <FlatList
        data={parametros}
        keyExtractor={(item) => item.chave}
        renderItem={renderItem}
        contentContainerStyle={{ paddingBottom: 30 }}
      />

      <TouchableOpacity
        onPress={salvarParametros}
        style={{
          backgroundColor: salvando ? '#555' : '#0ea5e9',
          padding: 15,
          borderRadius: 8,
          marginTop: 20,
        }}
        disabled={salvando}>
        <Text
          style={{
            color: '#fff',
            textAlign: 'center',
            fontWeight: 'bold',
            fontSize: 16,
          }}>
          {salvando ? 'Salvando...' : 'Salvar Parâmetros'}
        </Text>
      </TouchableOpacity>
    </View>
  )
}

export default ParametrosEstoque
