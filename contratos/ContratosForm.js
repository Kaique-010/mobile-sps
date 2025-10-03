import React, { useEffect, useState } from 'react'
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  Alert,
  KeyboardAvoidingView,
  Keyboard,
  Platform,
  TouchableWithoutFeedback,
} from 'react-native'
import Toast from 'react-native-toast-message'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { apiPostComContexto, apiPutComContexto, apiPatchComContexto } from '../utils/api'
import BuscaClienteInput from '../components/BuscaClienteInput'
import BuscaProdutosInput from '../components/BuscaProdutosInput'
import styles from '../styles/ContratoStyles'
import { getStoredData } from '../services/storageService'

export default function ContratosForm({ route, navigation }) {
  const { contratos } = route.params || {}

  const [clienteSelecionadoTexto, setClienteSelecionadoTexto] = useState('')

  const [form, setForm] = useState({
    cont_data: new Date().toISOString().split('T')[0],
    cont_clie: '',
    cont_tota: '0',
    cont_empr: null,
    cont_fili: null,
    cont_prod: '',
    cont_unit: '0',
    cont_quan: '1',
  })

  const [slug, setSlug] = useState('')

  const carregarContexto = async () => {
    try {
      const [empresaId, filialId] = await Promise.all([
        AsyncStorage.getItem('empresaId'),
        AsyncStorage.getItem('filialId'),
      ])

      setForm((prev) => ({
        ...prev,
        cont_empr: empresaId,
        cont_fili: filialId,
      }))
    } catch (error) {
      console.error('Erro ao carregar contexto:', error)
    }
  }

  useEffect(() => {
    const carregarSlug = async () => {
      try {
        const { slug } = await getStoredData()
        if (slug) setSlug(slug)
        else console.warn('Slug não encontrado')
      } catch (err) {
        console.error('Erro ao carregar slug:', err.message)
      }
    }
    carregarSlug()
  }, [])

  useEffect(() => {
    const init = async () => {
      await carregarContexto()
    }
    init()
  }, [])

  useEffect(() => {
    if (contratos) {
      setForm({
        cont_data:
          contratos.cont_data || new Date().toISOString().split('T')[0],
        cont_clie: contratos.cont_clie || '',
        cont_tota: contratos.cont_tota || '0',
        cont_empr: contratos.cont_empr || null,
        cont_fili: contratos.cont_fili || null,
        cont_prod: contratos.cont_prod || '',
        cont_unit:
          contratos.cont_unit != null ? String(contratos.cont_unit) : '0',
        cont_quan:
          contratos.cont_quan != null ? String(contratos.cont_quan) : '1',
      })
      setClienteSelecionadoTexto(
        `${contratos.cont_clie} - ${contratos.cliente_nome || ''}`
      )
    } else {
      setClienteSelecionadoTexto('')
      setForm((prev) => ({
        ...prev,
        cont_clie: '',
        cont_data: new Date().toISOString().split('T')[0],
        cont_tota: '0',
        cont_prod: '',
        cont_unit: '0',
        cont_quan: '1',
      }))
    }
  }, [contratos])

  const handleChange = (field, value) => {
    let updatedForm = { ...form, [field]: value }

    // Recalcula o total automaticamente
    const quan =
      parseFloat(field === 'cont_quan' ? value : updatedForm.cont_quan) || 0
    const unit =
      parseFloat(field === 'cont_unit' ? value : updatedForm.cont_unit) || 0

    updatedForm.cont_tota = (quan * unit).toFixed(2)

    setForm(updatedForm)
  }

  const salvarcontratos = async () => {
    if (!form.cont_clie || !form.cont_data) {
      Alert.alert('Erro', 'Preencha os campos obrigatórios.')
      return
    }

    try {
      const payload = { ...form }
      // Inclui o identificador do contrato no payload ao atualizar
      if (contratos?.cont_cont) {
        payload.cont_cont = contratos.cont_cont
      }
      console.log('📦 Payload enviado:', payload)

      if (contratos?.cont_cont) {
        await apiPatchComContexto(
          `contratos/contratos-vendas/${contratos.cont_cont}/`,
          payload
        )
        Toast.show({
          type: 'success',
          text1: 'Sucesso!',
          text2: `Contrato Atualizado com sucesso 👌`,
        })
        navigation.navigate('Contratos', {
          contratosId: contratos.cont_cont,
          clienteId: contratos.cont_clie,
          empresaId: contratos.cont_empr,
          filialId: contratos.cont_fili,
          cont_clie: clienteSelecionadoTexto,
        })
      } else {
        const novocontrato = await apiPostComContexto(
          `contratos/contratos-vendas/`,
          payload
        )
        Toast.show({
          type: 'success',
          text1: 'Sucesso!',
          text2: `Contrato criado com sucesso 👌`,
        })
        navigation.navigate('Contratos', {
          mensagemSucesso: `Contrato criado com sucesso 👌`,
        })
      }
    } catch (error) {
      console.error(
        '❌ Erro ao salvar contrato:',
        error.message,
        error.response?.data
      )
      Alert.alert('Erro', 'Falha ao salvar o contrato.')
    }
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.contratosiner}>
      <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
        <View style={styles.inner}>
          <Text style={styles.label}>Cliente</Text>
          <BuscaClienteInput
            onSelect={(item) => {
              setClienteSelecionadoTexto(
                `${item.enti_clie} - ${item.enti_nome}`
              )
              setForm((prev) => ({
                ...prev,
                cont_clie: item.enti_clie,
              }))
            }}
            initialValue={clienteSelecionadoTexto}
          />

          <Text style={styles.label}>Data</Text>
          <TextInput
            style={styles.forminput}
            value={form.cont_data}
            onChangeText={(text) => handleChange('cont_data', text)}
            placeholder="YYYY-MM-DD"
          />

          <Text style={styles.label}>Produto</Text>
          <BuscaProdutosInput
            onSelect={(produto) => {
              const unit = parseFloat(produto.prod_prec_venda) || 0
              const quan = parseFloat(form.cont_quan) || 1
              const tota = unit * quan
              setForm((prev) => ({
                ...prev,
                cont_prod: produto.prod_codi,
                cont_unit: unit.toFixed(2),
                cont_tota: tota.toFixed(2),
              }))
            }}
            initialValue={form.cont_prod}
          />

          <Text style={styles.label}>Quantidade</Text>
          <TextInput
            style={styles.forminput}
            keyboardType="numeric"
            value={form.cont_quan}
            onChangeText={(text) => handleChange('cont_quan', text)}
            placeholder="Quantidade"
          />

          <Text style={styles.label}>Valor Unitário</Text>
          <TextInput
            style={styles.forminput}
            keyboardType="numeric"
            value={form.cont_unit}
            onChangeText={(text) => handleChange('cont_unit', text)}
            placeholder="Valor unitário"
          />

          <Text style={styles.label}>Total</Text>
          <TextInput
            style={styles.forminput}
            value={form.cont_tota}
            editable={false}
          />

          <TouchableOpacity
            style={styles.incluirButton}
            onPress={salvarcontratos}>
            <Text style={styles.incluirButtonText}>
              {contratos ? 'Salvar Alterações' : 'Criar Contrato'}
            </Text>
          </TouchableOpacity>
        </View>
      </TouchableWithoutFeedback>
    </KeyboardAvoidingView>
  )
}
