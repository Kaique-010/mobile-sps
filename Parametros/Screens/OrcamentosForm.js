import React, { useState, useEffect } from 'react'
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Text,
  ActivityIndicator,
  ScrollView,
} from 'react-native'
import { MaterialIcons } from '@expo/vector-icons'
import AsyncStorage from '@react-native-async-storage/async-storage'
import OrcamentoHeader from '../componentsOrcamentos/OrcamentoHeader'
import ItensList from '../componentsOrcamentos/ItensLista'
import ItensModal from '../componentsOrcamentos/ItensModal'
import ResumoOrcamento from '../componentsOrcamentos/ResumoOrcamento'
import { apiGetComContexto, safeSetItem } from '../utils/api'

const ORCAMENTO_CACHE_ID = 'orcamento-edicao-cache'

export default function TelaOrcamento({ route, navigation }) {
  const orcamentoParam = route.params?.orcamento || null
  

  const [orcamento, setOrcamento] = useState({
    pedi_empr: null,
    pedi_fili: null,
    pedi_forn: null,
    pedi_vend: null,
    pedi_data: new Date().toISOString().split('T')[0],
    pedi_obse: null,
    itens_input: [],
    itens_removidos: [],
    pedi_desc: 0,
    desconto_geral_aplicado: true,
    desconto_geral_tipo: 'percentual',
    desconto_geral_percentual: 0,
    desconto_geral_valor: 0,
    pedi_topr: 0,
    pedi_tota: 0,
  })

  const carregarContexto = async () => {
    try {
      const [empresaId, filialId] = await Promise.all([
        AsyncStorage.getItem('empresaId'),
        AsyncStorage.getItem('filialId'),
      ])
      return { empresaId, filialId }
    } catch (error) {
      console.error('Erro ao carregar contexto:', error)
      return { empresaId: null, filialId: null }
    }
  }

  const [modalVisivel, setModalVisivel] = useState(false)
  const [carregando, setCarregando] = useState(true)
  const [itemEditando, setItemEditando] = useState(null)

  const calcularTotal = (itens) =>
    itens ? itens.reduce((acc, i) => acc + (Number(i.iped_tota) || 0), 0) : 0

  useEffect(() => {
    const carregarOrcamento = async () => {
      setCarregando(true)
      try {
        const { empresaId, filialId } = await carregarContexto()

        if (orcamentoParam && orcamentoParam.pedi_nume) {
          const data = await apiGetComContexto(
            `orcamentos/orcamentos/${orcamentoParam.pedi_empr}/${orcamentoParam.pedi_fili}/${orcamentoParam.pedi_nume}/`
          )
          const itens = data.itens || []

          setOrcamento({
            ...data,
            pedi_empr: data.pedi_empr || empresaId, // Garante que empresaId seja usado se data.pedi_empr for nulo
            pedi_fili: data.pedi_fili || filialId,   // Garante que filialId seja usado se data.pedi_fili for nulo
            itens_input: itens,
            pedi_tota: calcularTotal(itens),
          })

          await safeSetItem(
            ORCAMENTO_CACHE_ID,
            JSON.stringify({
              ...data,
              pedi_empr: data.pedi_empr || empresaId,
              pedi_fili: data.pedi_fili || filialId,
              itens_input: itens,
              pedi_tota: calcularTotal(itens),
            })
          )
        } else {
          await AsyncStorage.removeItem(ORCAMENTO_CACHE_ID)
          setOrcamento({
            pedi_empr: empresaId,
            pedi_fili: filialId,
            pedi_forn: null,
            pedi_vend: null,
            pedi_data: new Date().toISOString().split('T')[0],
            pedi_obse: 'orcamento Enviado por Mobile',
            itens_input: [],
            itens_removidos: [],
            pedi_desc: 0,
            desconto_geral_aplicado: true,
            desconto_geral_tipo: 'percentual',
            desconto_geral_percentual: 0,
            desconto_geral_valor: 0,
            pedi_topr: 0,
            pedi_tota: 0,
          })
        }
      } catch (error) {
        console.error('Erro ao carregar Orçamento:', error)
      } finally {
        setCarregando(false)
      }
    }

    carregarOrcamento()
  }, [orcamentoParam])

  const handleAdicionarOuEditarItem = (novoItem, itemAnterior = null) => {
    let novosItens = [...orcamento.itens_input]

    const index = itemAnterior
      ? novosItens.findIndex((i) => i.iped_prod === itemAnterior.iped_prod)
      : novosItens.findIndex((i) => i.iped_prod === novoItem.iped_prod)

    if (index !== -1) {
      novosItens[index] = novoItem
    } else {
      novosItens.push(novoItem)
    }

    const novoTotal = calcularTotal(novosItens)

    setOrcamento((prev) => ({
      ...prev,
      itens_input: novosItens,
      pedi_tota: novoTotal,
    }))

    setItemEditando(null)
    setModalVisivel(false)
  }

  const handleRemoverItem = (item) => {
    const novosItens = orcamento.itens_input.filter(
      (i) => i.iped_prod !== item.iped_prod
    )

    const novosRemovidos = item.idExistente
      ? [...orcamento.itens_removidos, item.iped_prod]
      : orcamento.itens_removidos

    const novoTotal = calcularTotal(novosItens)

    setOrcamento((prev) => ({
      ...prev,
      itens_input: novosItens,
      itens_removidos: novosRemovidos,
      pedi_tota: novoTotal,
    }))
  }

  if (carregando) {
    return (
      <View style={styles.carregandoContainer}>
        <ActivityIndicator size="large" color="#10a2a7" />
        <Text style={styles.carregandoTexto}>Carregando orçamento...</Text>
      </View>
    )
  }

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}>
        <View style={styles.headerContainer}>
          <MaterialIcons
            name="description"
            marginHorizontal={10}
            marginBottom={10}
            marginLeft={80}
            size={20}
            color="#10a2a7"
          />
          <Text style={styles.pageTitle}>
            {orcamentoParam ? 'Editar Orçamento' : 'Novo Orçamento'}
          </Text>
        </View>

        <OrcamentoHeader orcamento={orcamento} setOrcamento={setOrcamento} />

        <View style={styles.itensSection}>
          <View style={styles.itensSectionHeader}>
            <MaterialIcons name="list" size={20} color="#10a2a7" />
            <Text style={styles.sectionTitle}>Itens do Orçamento</Text>
            <Text style={styles.itensCount}>
              {orcamento.itens_input?.length || 0}{' '}
              {orcamento.itens_input?.length === 1 ? 'item' : 'itens'}
            </Text>
          </View>

          <TouchableOpacity
            style={styles.botaoAdicionarItem}
            onPress={() => setModalVisivel(true)}
            activeOpacity={0.8}>
            <MaterialIcons name="add-circle" size={24} color="#fff" />
            <Text style={styles.textoBotaoAdicionar}>Adicionar Item</Text>
          </TouchableOpacity>

          <ItensList
            itens={orcamento.itens_input}
            onEdit={(item) => {
              setItemEditando(item)
              setModalVisivel(true)
            }}
            onRemove={handleRemoverItem}
          />
        </View>
      </ScrollView>

      <ResumoOrcamento total={orcamento.pedi_tota} orcamento={orcamento} />

      <ItensModal
        visivel={modalVisivel}
        onFechar={() => {
          setModalVisivel(false)
          setItemEditando(null)
        }}
        onAdicionar={handleAdicionarOuEditarItem}
        onRemove={handleRemoverItem}
        itemEditando={itemEditando}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0e1c25',
  },
  scrollView: {
    flex: 1,
  },
  carregandoContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0e1c25',
  },
  carregandoTexto: {
    color: '#faebd7',
    marginTop: 16,
    fontSize: 16,
  },
  headerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#1a252f',
    borderBottomWidth: 1,
    borderBottomColor: '#2a3441',
  },
  pageTitle: {
    color: '#faebd7',
    fontSize: 20,
    fontWeight: 'bold',
    marginLeft: 12,
  },
  itensSection: {
    flex: 1,
    padding: 8,
  },
  itensSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
    paddingHorizontal: 8,
  },
  sectionTitle: {
    color: '#faebd7',
    fontSize: 18,
    fontWeight: '600',
    flex: 1,
    marginLeft: 8,
  },
  itensCount: {
    color: '#10a2a7',
    fontSize: 14,
    fontWeight: '600',
    backgroundColor: '#1a252f',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  botaoAdicionarItem: {
    backgroundColor: '#10a2a7',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    borderRadius: 12,
    marginBottom: 16,
    marginHorizontal: 4,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  textoBotaoAdicionar: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
    marginLeft: 8,
  },
})
