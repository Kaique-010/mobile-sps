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
import { apiGetComContexto, apiPatchComContexto } from '../../utils/api'
import AsyncStorage from '@react-native-async-storage/async-storage'
import Toast from 'react-native-toast-message'

const ParametrosVendas = () => {
  const [parametros, setParametros] = useState([])
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    buscarParametros()
  }, [])

  const buscarParametros = async () => {
    try {
      console.log('[ParametrosVendas] Iniciando busca de parâmetros...')

      // Log dos dados do AsyncStorage
      const slug = await AsyncStorage.getItem('slug')
      const empresaId = await AsyncStorage.getItem('empresaId')
      const filialId = await AsyncStorage.getItem('filialId')
      const usuario_id = await AsyncStorage.getItem('usuario_id')

      console.log('[ParametrosVendas] Dados do AsyncStorage:', {
        slug,
        empresaId,
        filialId,
        usuario_id,
      })

      // Log da URL que será chamada
      const endpoint = 'orcamentos/orcamentos/parametros-desconto/'
      console.log('[ParametrosVendas] Endpoint:', endpoint)
      console.log(
        '[ParametrosVendas] URL completa será:',
        `/api/${slug}/${endpoint}`
      )

      // A função apiGetComContexto já adiciona empr e fili automaticamente
      const data = await apiGetComContexto(endpoint)

      console.log('[ParametrosVendas] Resposta da API:', data)

      const parametrosDescontoOrcamentoLista = [
        {
          nome: 'Desconto Item em Orçamento',
          chave: 'desconto_item_disponivel',
          ativo: data.desconto_item_disponivel || false,
        },
        {
          nome: 'Desconto Total em Orçamento',
          chave: 'desconto_total_disponivel',
          ativo: data.desconto_total_disponivel || false,
        },
        {
          nome: 'Desconto Item em Pedido',
          chave: 'desconto_item_orcamento',
          ativo: data.desconto_item_orcamento || false,
        },

        {
          nome: 'Desconto Item em Pedido',
          chave: 'desconto_item_pedido',
          ativo: data.desconto_item_pedido || false,
        },
        {
          nome: 'Desconto Total em Pedido',
          chave: 'desconto_total_pedido',
          ativo: data.desconto_total_pedido || false,
        },
        {
          nome: 'Desconto Total em Pedido',
          chave: 'desconto_pedido',
          ativo: data.desconto_pedido || false,
        },

        {
          nome: 'Usar Preço a Prazo',
          chave: 'usar_preco_prazo',
          ativo: data.usar_preco_prazo || false,
        },
        {
          nome: 'Usar Último Preço',
          chave: 'usar_ultimo_preco',
          ativo: data.usar_ultimo_preco || false,
        },

        {
          nome: 'Pedido Volta Estoque',
          chave: 'pedido_volta_estoque',
          ativo: data.pedido_volta_estoque || false,
        },
        {
          nome: 'Validar Estoque no Pedido',
          chave: 'validar_estoque_pedido',
          ativo: data.validar_estoque_pedido || false,
        },
        {
          nome: 'Calcular Frete Automático',
          chave: 'calcular_frete_automatico',
          ativo: data.calcular_frete_automatico || false,
        },
      ]

      console.log(
        '[ParametrosVendas] Parâmetros processados:',
        parametrosDescontoOrcamentoLista
      )
      setParametros(parametrosDescontoOrcamentoLista)
    } catch (error) {
      console.error('[ParametrosVendas] Erro completo:', error)
      console.error('[ParametrosVendas] Erro response:', error.response)
      console.error('[ParametrosVendas] Erro status:', error.response?.status)
      console.error('[ParametrosVendas] Erro data:', error.response?.data)
      console.error('[ParametrosVendas] Erro config:', error.config)

      Alert.alert(
        'Erro',
        `Erro ao carregar parâmetros de vendas: ${error.message}`
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
    setSalvando(true)
    try {
      console.log('[ParametrosVendas] Iniciando salvamento...')

      const payload = {}

      parametros.forEach((param) => {
        payload[param.chave] = param.ativo
      })

      console.log('[ParametrosVendas] Payload para salvar:', payload)

      // A função apiPatchComContexto já adiciona empr e fili automaticamente
      const result = await apiPatchComContexto(
        'orcamentos/orcamentos/parametros-desconto/',
        payload
      )
      console.log('[ParametrosdeOrçamento] Payload enviado:', payload)

      console.log('[ParametrosdeOrçamento] Resultado do salvamento:', result)
      Toast.show({
        type: 'success',
        text1: 'Sucesso',
        text2: 'Parâmetros de Vendas salvos com sucesso!',
      })
    } catch (error) {
      console.error('[ParametrosVendas] Erro ao salvar:', error)
      console.error('[ParametrosVendas] Erro response:', error.response)
      console.error('[ParametrosVendas] Erro status:', error.response?.status)
      console.error('[ParametrosVendas] Erro data:', error.response?.data)

      Toast.show({
        type: 'error',
        text1: 'Erro',
        text2: `Erro ao salvar parâmetros: ${error.message}`,
      })
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
      <Text style={{ color: '#fff', fontSize: 16, fontWeight: '600' }}>
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

export default ParametrosVendas
