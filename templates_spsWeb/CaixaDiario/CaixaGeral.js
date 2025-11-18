import React, { useState, useEffect } from 'react'
import Icon from 'react-native-vector-icons/Feather'
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
} from 'react-native'
import Toast from 'react-native-toast-message'
import AsyncStorage from '@react-native-async-storage/async-storage'
import BuscaCaixa from '../components/BuscaCaixaInput'
import styles from '../styles/caixaStyle'
import { apiPostComContexto, apiGetComContexto } from '../utils/api'

export default function CaixaGeralScreen({ route, navigation }) {
  const [caixa, setCaixa] = useState({
    caix_empr: null,
    caix_fili: null,
    caix_caix: '',
    caix_data: new Date().toISOString().slice(0, 10),
    caix_aber: 'A',
    caix_oper: null,
    caix_valo: 0,
    caix_orig: '',
  })

  const [caixaAberto, setCaixaAberto] = useState(false)

  useEffect(() => {
    checarCaixaAberto()
  }, [])

  const carregarContexto = async () => {
    try {
      const [usuarioRaw, empresaId, filialId] = await Promise.all([
        AsyncStorage.getItem('usuario'),
        AsyncStorage.getItem('empresaId'),
        AsyncStorage.getItem('filialId'),
      ])
      const usuarioObj = usuarioRaw ? JSON.parse(usuarioRaw) : null
      return {
        caix_oper: Number(usuarioObj?.usuario_id ?? 0),
        caix_empr: Number(empresaId),
        caix_fili: Number(filialId),
      }
    } catch (error) {
      console.error('Erro ao carregar contexto:', error)
    }
  }

  const checarCaixaAberto = async () => {
    const ctx = await carregarContexto()
    if (!ctx) return
    try {
      const response = await apiGetComContexto(
        `caixadiario/caixageral/?caix_empr=${ctx.caix_empr}&caix_fili=${ctx.caix_fili}&caix_oper=${ctx.caix_oper}&caix_aber=A`
      )
      if (response?.results?.length > 0) {
        const caixaAbertoData = response.results[0]
        setCaixaAberto(true)
        setCaixa((prev) => ({ ...prev, ...caixaAbertoData }))
        navigation.navigate('MoviCaixa', { caixa: caixaAbertoData })
      }
    } catch (err) {
      console.error('Erro ao verificar caixa aberto:', err)
    }
  }

  const abrirCaixa = async () => {
    try {
      const ctx = await carregarContexto()
      const payload = { ...caixa, ...ctx }
      await apiPostComContexto('caixadiario/caixageral/', payload)
      Toast.show({ type: 'success', text1: 'Sucesso', text2: 'Caixa aberto!' })
      setCaixaAberto(true)
      setCaixa(payload)
      navigation.navigate('MoviCaixa', { caixa: payload })
    } catch (e) {
      Toast.show({
        type: 'error',
        text1: 'Erro',
        text2: e.message || 'Falha na comunicação',
      })
    }
  }

  const irParaMovimentacao = () => {
    navigation.navigate('MoviCaixa', { caixa })
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <Icon name="dollar-sign" size={36} color="#00cc66" />
        <Text style={styles.title}>CAIXA DIÁRIO</Text>
      </View>

      <Text style={styles.label}>Caixa</Text>
      <BuscaCaixa
        onSelect={(item) =>
          item?.id &&
          setCaixa((prev) => ({ ...prev, caix_caix: Number(item.id) }))
        }
        value={String(caixa.caix_caix)}
        style={styles.input}
      />

      <Text style={styles.label}>Origem</Text>
      <BuscaCaixa
        onSelect={(item) =>
          item?.id &&
          setCaixa((prev) => ({ ...prev, caix_orig: Number(item.id) }))
        }
        value={String(caixa.caix_orig)}
        style={styles.input}
      />

      <Text style={styles.label}>Data de Abertura</Text>
      <Text style={[styles.input, { backgroundColor: '#222' }]}>
        {caixa.caix_data}
      </Text>

      <Text style={styles.label}>Valor Inicial</Text>
      <TextInput
        keyboardType="numeric"
        onChangeText={(val) =>
          setCaixa((prev) => ({ ...prev, caix_valo: Number(val) }))
        }
        value={String(caixa.caix_valo)}
        style={styles.input}
        editable={!caixaAberto}
      />

      <View style={styles.buttonGroup}>
        <TouchableOpacity
          onPress={abrirCaixa}
          style={[styles.button, caixaAberto && styles.buttonDisabled]}
          disabled={caixaAberto}>
          <Icon name="log-in" size={18} color="#fff" />
          <Text style={styles.buttonText}>Abrir Caixa</Text>
        </TouchableOpacity>

        {caixaAberto && (
          <TouchableOpacity onPress={irParaMovimentacao} style={styles.button}>
            <Icon name="arrow-right-circle" size={18} color="#fff" />
            <Text style={styles.buttonText}>Movimentações</Text>
          </TouchableOpacity>
        )}
      </View>
    </ScrollView>
  )
}
