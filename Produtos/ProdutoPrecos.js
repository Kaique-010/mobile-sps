import React, { useState, useEffect } from 'react'
import {
  View,
  TextInput,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native'
import { useNavigation, useRoute } from '@react-navigation/native'
import AsyncStorage from '@react-native-async-storage/async-storage'
import Toast from 'react-native-toast-message'
import { apiPutComContexto, apiPostComContexto } from '../utils/api'

export default function ProdutoPrecos({ atualizarProduto: propAtualizarProduto }) {
  const navigation = useNavigation()
  const { params } = useRoute()
  const { produto = {}, slug = {}, atualizarProduto: paramAtualizarProduto } = params || {}
  
  // Use the function from params if available, otherwise use the prop
  const atualizarProduto = paramAtualizarProduto || propAtualizarProduto
  
  const [precoCompra, setPrecoCompra] = useState('')
  const [percentualAVista, setPercentualAVista] = useState('10')
  const [percentualAPrazo, setPercentualAPrazo] = useState('20')
  const [precoCusto, setPrecoCusto] = useState('')
  const [aVista, setAVista] = useState('')
  const [aPrazo, setAPrazo] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!produto || !produto.prod_codi) return

    const carregarOuIniciarCampos = async () => {
      const cacheKey = `precos-produto-${produto.prod_codi}`
      let tabela

      try {
        // tenta do AsyncStorage
        const json = await AsyncStorage.getItem(cacheKey)
        if (json) {
          tabela = JSON.parse(json)
        } else {
          // tenta da prop
          tabela = produto.precos?.[0] || null
        }

        if (!tabela) return

        // Setar valores básicos
        setPrecoCompra(String(tabela.tabe_prco || ''))
        setPrecoCusto(String(tabela.tabe_cuge || ''))
        setAVista(String(tabela.tabe_avis || ''))
        setAPrazo(String(tabela.tabe_apra || ''))

        // Se temos percentuais salvos, usar eles
        if (tabela.percentual_avis !== undefined) {
          setPercentualAVista(String(tabela.percentual_avis))
        } else if (tabela.tabe_prco && tabela.tabe_avis) {
          // Senão, calcular a partir dos preços
          const percAVista = ((tabela.tabe_avis / tabela.tabe_prco - 1) * 100).toFixed(2)
          setPercentualAVista(String(percAVista))
        }

        if (tabela.percentual_apra !== undefined) {
          setPercentualAPrazo(String(tabela.percentual_apra))
        } else if (tabela.tabe_prco && tabela.tabe_apra) {
          const percAPrazo = ((tabela.tabe_apra / tabela.tabe_prco - 1) * 100).toFixed(2)
          setPercentualAPrazo(String(percAPrazo))
        }
      } catch (error) {
        console.error('Erro ao carregar dados:', error)
        Toast.show({
          type: 'error',
          text1: 'Erro',
          text2: 'Não foi possível carregar os dados dos preços',
        })
      }
    }

    carregarOuIniciarCampos()
  }, [produto])

  useEffect(() => {
    const preco = parseFloat(precoCompra.replace(',', '.')) || 0
    const pVista = parseFloat(percentualAVista.replace(',', '.')) || 0
    const pPrazo = parseFloat(percentualAPrazo.replace(',', '.')) || 0

    setPrecoCusto(preco.toFixed(2))
    setAVista((preco * (1 + pVista / 100)).toFixed(2))
    setAPrazo((preco * (1 + pPrazo / 100)).toFixed(2))
  }, [precoCompra, percentualAVista, percentualAPrazo])

  const validarCampos = () => {
    if (!precoCompra || parseFloat(precoCompra) <= 0) {
      Toast.show({
        type: 'error',
        text1: 'Erro',
        text2: 'O preço de compra deve ser maior que zero',
      })
      return false
    }

    if (!percentualAVista || parseFloat(percentualAVista) < 0) {
      Toast.show({
        type: 'error',
        text1: 'Erro',
        text2: 'O percentual à vista deve ser maior ou igual a zero',
      })
      return false
    }

    if (!percentualAPrazo || parseFloat(percentualAPrazo) < 0) {
      Toast.show({
        type: 'error',
        text1: 'Erro',
        text2: 'O percentual a prazo deve ser maior ou igual a zero',
      })
      return false
    }

    return true
  }

  const salvar = async () => {
    if (!validarCampos()) return
    
    setLoading(true)
  
    const payload = {
      tabe_empr: parseInt(slug?.empresa) || 1,
      tabe_fili: parseInt(slug?.filial) || 1,
      tabe_prod: String(produto.prod_codi), // Garantir que seja string
      tabe_prco: parseFloat(precoCompra.replace(',', '.')) || 0,
      tabe_cuge: parseFloat(precoCusto.replace(',', '.')) || 0,
      percentual_avis: parseFloat(percentualAVista.replace(',', '.')) || 0,
      percentual_apra: parseFloat(percentualAPrazo.replace(',', '.')) || 0,
    }
  
    const chave = `${payload.tabe_empr}-${payload.tabe_fili}-${payload.tabe_prod}`
  
    try {
      let response
      // tenta PUT (atualizar)
      try {
        response = await apiPutComContexto(`produtos/tabelapreco/${chave}/`, payload)
      } catch (error) {
        if (error?.response?.status === 404) {
          // se não existe, cria com POST
          response = await apiPostComContexto(`produtos/tabelapreco/`, payload)
        } else {
          throw error
        }
      }
  
      // Atualizar o cache com os dados retornados da API
      const dadosAtualizados = response?.data || response || payload
      
      // Verificar se dadosAtualizados não é undefined antes de armazenar
      if (dadosAtualizados) {
        await AsyncStorage.setItem(
          `precos-produto-${produto.prod_codi}`,
          JSON.stringify(dadosAtualizados)
        )
      }
  
      Toast.show({
        type: 'success',
        text1: 'Sucesso!',
        text2: 'Preços atualizados com sucesso',
      })
  
      // Atualizar o produto com os preços calculados pelo backend
      atualizarProduto({ ...produto, precos: [dadosAtualizados] })
      setTimeout(() => navigation.goBack(), 1000)
    } catch (error) {
      console.error('Erro ao salvar preços:', error)
      Toast.show({
        type: 'error',
        text1: 'Erro',
        text2: error?.response?.data?.detail || 'Não foi possível salvar os preços',
      })
    } finally {
      setLoading(false)
    }
  }

  const formatarNumero = (valor) => {
    // Remove caracteres não numéricos exceto vírgula
    const numero = valor.replace(/[^\d,]/g, '')
    // Garante apenas uma vírgula
    const partes = numero.split(',')
    if (partes.length > 2) {
      return partes[0] + ',' + partes[1]
    }
    return numero
  }

  return (
    <View style={styles.container}>
      <Campo
        label="Preço de Compra"
        value={precoCompra}
        onChange={(valor) => setPrecoCompra(formatarNumero(valor))}
        placeholder="0,00"
      />
      <Campo
        label="Percentual à Vista (%)"
        value={percentualAVista}
        onChange={(valor) => setPercentualAVista(formatarNumero(valor))}
        placeholder="0,00"
      />
      <Campo
        label="Percentual a Prazo (%)"
        value={percentualAPrazo}
        onChange={(valor) => setPercentualAPrazo(formatarNumero(valor))}
        placeholder="0,00"
      />
      <Campo 
        label="Preço à Vista" 
        value={aVista} 
        editable={false} 
        dark 
        placeholder="0,00"
      />
      <Campo 
        label="Preço a Prazo" 
        value={aPrazo} 
        editable={false} 
        dark 
        placeholder="0,00"
      />

      <TouchableOpacity
        onPress={salvar}
        style={[styles.button, loading && { opacity: 0.6 }]}
        disabled={loading}>
        {loading ? (
          <ActivityIndicator size="small" color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Salvar</Text>
        )}
      </TouchableOpacity>
    </View>
  )
}

function Campo({ label, value, onChange, editable = true, dark = false, placeholder }) {
  return (
    <>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChange}
        editable={editable}
        keyboardType="decimal-pad"
        placeholder={placeholder}
        placeholderTextColor={dark ? '#666' : '#999'}
        style={[
          styles.input,
          !editable && {
            backgroundColor: dark ? '#333' : '#eee',
            color: dark ? '#fff' : '#000',
          },
        ]}
      />
    </>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 35,
    backgroundColor: '#0B141A',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    marginBottom: 12,
    padding: 10,
    fontSize: 16,
    color: 'white',
  },
  label: {
    marginBottom: 4,
    fontWeight: 'bold',
    fontSize: 14,
    color: '#fff',
  },
  button: {
    backgroundColor: '#0058A2',
    padding: 12,
    borderRadius: 8,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 20,
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
  },
})