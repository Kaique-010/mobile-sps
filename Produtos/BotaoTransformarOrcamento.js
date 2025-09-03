// src/components/BotaoTransformarOrcamento.js
import React, { useState } from 'react'
import { TouchableOpacity, Text, ActivityIndicator, Alert } from 'react-native'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { apiPostComContexto } from '../utils/api'
import Toast from 'react-native-toast-message'

export default function BotaoTransformarOrcamento({ orcamentoId, onSuccess }) {
  const [loading, setLoading] = useState(false)

  const transformar = async () => {
    setLoading(true)

    // Debug logs
    console.log('[DEBUG] Iniciando transformação do orçamento')
    console.log('[DEBUG] ID do orçamento:', orcamentoId)

    try {
      const empresaId = await AsyncStorage.getItem('empresaId')
      const filialId = await AsyncStorage.getItem('filialId')
      
      // Usar URL com chave composta
      const endpoint = `orcamentos/orcamentos/${empresaId}/${filialId}/${orcamentoId}/transformar-em-pedido/`
      console.log('[DEBUG] Endpoint completo:', endpoint)
      
      const data = await apiPostComContexto(endpoint, {})

      console.log('[DEBUG] Resposta da API:', data)

      if (
        data &&
        (data.message || data.pedido_numero || data.orcamento_numero)
      ) {
        Toast.show({
          type: 'success',
          text1: 'Sucesso',
          text2: 'Orçamento transformado em pedido!',
        })
        onSuccess?.(data)
      } else {
        throw new Error('Resposta inesperada da API')
      }
    } catch (error) {
      console.error('[ERROR] Erro completo:', error)
      console.error('[ERROR] Resposta do erro:', error.response?.data)
      console.error('[ERROR] Status do erro:', error.response?.status)
      console.error('[ERROR] URL do erro:', error.config?.url)

      Toast.show({
        type: 'error',
        text1: 'Erro',
        text2: `Não foi possível transformar o orçamento.\nDetalhes: ${
          error.response?.data?.detail || error.message
        }`,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <TouchableOpacity
      onPress={transformar}
      disabled={loading}
      style={{
        backgroundColor: '#4CAF5045',
        padding: 12,
        borderRadius: 6,
        alignItems: 'center',
        marginVertical: 4,
      }}>
      {loading ? (
        <ActivityIndicator color="#FFF" />
      ) : (
        <Text style={{ color: '#FFF', fontWeight: 'bold' }}>
          Transformar em Pedido
        </Text>
      )}
    </TouchableOpacity>
  )
}
