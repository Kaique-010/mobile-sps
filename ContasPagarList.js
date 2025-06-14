import React, { useEffect, useState } from 'react'
import {
  View,
  Text,
  FlatList,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native'
import { getStoredData } from '../services/storageService'
import { apiDeleteComContexto, apiGetComContexto } from '../utils/api'
import styles from '../styles/listaContasStyles'

const formatarData = (data) => {
  if (!data) return '-'
  const [ano, mes, dia] = data.split('-')
  return `${dia}/${mes}/${ano}`
}

const formatarMoeda = (valor) => {
  if (!valor) return 'R$ 0,00'
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(valor)
}

export default function ContasPagarList({ navigation }) {
  const [contas, setContas] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchFornecedor, setSearchFornecedor] = useState('')
  const [searchTitulo, setSearchtitulo] = useState('')

  const [searchStatus, setSearchStatus] = useState('')
  const statusMap = {
    A: 'Aberto',
    T: 'Pago Total',
    P: 'Pago Parcialmente',
  }
  const [isSearching, setIsSearching] = useState(false)

  const [slug, setSlug] = useState('')

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
    if (slug) buscarContas()
  }, [slug])

  const buscarContas = async () => {
    setIsSearching(true)
    try {
      const filtros = {}
      if (searchFornecedor) filtros.fornecedor_nome = searchFornecedor
      if (searchTitulo) filtros.titu_titu = searchTitulo
      if (searchStatus) filtros.titu_aber = searchStatus

      const data = await apiGetComContexto(
        `contas_a_pagar/titulos-pagar/`,
        filtros
      )
      setContas(data.results || data)
    } catch (error) {
      console.log('❌ Erro ao buscar contas:', error.message)
      Alert.alert('Erro', 'Falha ao carregar contas a pagar')
    } finally {
      setIsSearching(false)
      setLoading(false)
    }
  }
  const excluirConta = (item) => {
    Alert.alert('Confirmação', 'Excluir esta conta a pagar?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Excluir',
        style: 'destructive',
        onPress: async () => {
          try {
            await apiDeleteComContexto(
              `contas_a_pagar/titulos-pagar/${item.titu_empr}/${item.titu_fili}/${item.titu_forn}/${item.titu_titu}/${item.titu_seri}/${item.titu_parc}/`,
              {},
              'DELETE'
            )
            setContas((prev) =>
              prev.filter(
                (conta) =>
                  conta.titu_empr !== item.titu_empr ||
                  conta.titu_fili !== item.titu_fili ||
                  conta.titu_forn !== item.titu_forn ||
                  conta.titu_titu !== item.titu_titu ||
                  conta.titu_seri !== item.titu_seri ||
                  conta.titu_parc !== item.titu_parc
              )
            )
          } catch (error) {
            console.log('❌ Erro ao excluir conta:', error.message)
            Alert.alert('Erro', 'Erro ao excluir a conta')
          }
        },
      },
    ])
  }

  const formMap = {
    '00': 'Duplicata',
    '01': 'Cheque',
    '02': 'Promissória',
    '03': 'Recibo',
    50: 'cheque pré-datado',
    51: 'Cartão de crédito',
    52: 'Cartão de débito',
    53: 'Boleto bancário',
    54: 'Dinheiro',
    55: 'Deposito em conta',
    56: 'Venda à vista',
    60: 'PIX',
  }

  const renderItem = ({ item }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle}>Titulo: {item.titu_titu}</Text>
        <Text style={[styles.badge, { backgroundColor: '#007bff' }]}>
          {formMap[item.titu_form_reci] || item.titu_form_reci}
        </Text>
      </View>

      <View style={styles.cardBody}>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Fornecedor:</Text>
          <Text style={styles.infoValue}>{item.titu_forn}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Nome Fornecedor:</Text>
          <Text style={styles.infoValue}>{item.fornecedor_nome || '-'}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Vencimento:</Text>
          <Text style={styles.infoValue}>{formatarData(item.titu_venc)}</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Valor:</Text>
          <Text style={[styles.infoValue, styles.valorDestaque]}>
            {formatarMoeda(item.titu_valo)}
          </Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Status:</Text>
          <Text style={[styles.infoValue, styles.valorDestaqueStatus]}>
            {statusMap[item.titu_aber] || item.titu_aber}
          </Text>
        </View>
      </View>

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.botao, styles.botaoEditar]}
          onPress={() =>
            navigation.navigate('ContaPagarForm', { contaExistente: item })
          }>
          <Text style={styles.botaoTexto}>💵 Pagar</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.botao, styles.botaoEditar]}
          onPress={() =>
            navigation.navigate('ContaPagarForm', { contaExistente: item })
          }>
          <Text style={styles.botaoTexto}>✏️ Editar</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.botao, styles.botaoExcluir]}
          onPress={() => excluirConta(item)}>
          <Text style={styles.botaoTexto}>🗑️ Excluir</Text>
        </TouchableOpacity>
      </View>
    </View>
  )

  if (loading) {
    return (
      <ActivityIndicator
        size="large"
        color="#007bff"
        style={{ marginTop: 50 }}
      />
    )
  }

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.incluirButton}
        onPress={() => navigation.navigate('ContaPagarForm')}>
        <Text style={styles.incluirButtonText}>+ Nova Conta</Text>
      </TouchableOpacity>

      <View style={styles.searchContainer}>
        <View
          style={{
            flexDirection: 'row',
            justifyContent: 'space-between',
            marginBottom: 10,
          }}>
          <TextInput
            placeholder="nome fornecedor"
            placeholderTextColor="#777"
            style={[styles.input, { flex: 1, marginRight: 5 }]}
            value={searchFornecedor}
            onChangeText={setSearchFornecedor}
          />
          <TextInput
            placeholder="por status"
            placeholderTextColor="#777"
            style={[styles.input, { flex: 1, marginRight: 5 }]}
            value={searchStatus}
            onChangeText={setSearchStatus}
          />
          <TextInput
            placeholder="por título"
            placeholderTextColor="#777"
            style={[styles.input, { flex: 1 }]}
            value={searchTitulo}
            onChangeText={setSearchtitulo}
          />
        </View>
        <TouchableOpacity
          style={[styles.searchButton, { width: '100%' }]}
          onPress={buscarContas}>
          <Text style={styles.searchButtonText}>
            {isSearching ? '🔍...' : 'Buscar'}
          </Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={contas}
        renderItem={renderItem}
        keyExtractor={(item) =>
          `${item.titu_empr}_${item.titu_fili}_${item.titu_forn}_${item.titu_titu}_${item.titu_seri}_${item.titu_parc}`
        }
        ListEmptyComponent={() => (
          <Text style={{ textAlign: 'center', marginTop: 20 }}>
            Nenhuma conta encontrada
          </Text>
        )}
      />

      <Text style={styles.footerText}>
        {contas.length} conta{contas.length !== 1 ? 's' : ''} encontrada
        {contas.length !== 1 ? 's' : ''}
      </Text>
    </View>
  )
}
