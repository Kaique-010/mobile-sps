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
import PedidoHeader from '../componentsPedidos/PedidoHeader'
import ItensList from '../componentsPedidos/ItensLista'
import ItensModal from '../componentsPedidos/ItensModal'
import ResumoPedido from '../componentsPedidos/ResumoPedido'
import ResumoPedidoComFinanceiro from '../componentsPedidos/ResumoPedidoComFinanceiro'
import { apiGetComContexto, safeSetItem } from '../utils/api'

const PEDIDO_CACHE_ID = 'pedido-edicao-cache'

export default function TelaPedidoVenda({ route, navigation }) {
  const pedidoParam = route.params?.pedido || null

  const [pedido, setPedido] = useState({
    pedi_empr: null,
    pedi_fili: null,
    pedi_forn: null,
    pedi_vend: null,
    pedi_data: new Date().toISOString().split('T')[0],
    pedi_fina: '0',
    status: 0,
    pedi_obse: 'Pedido Enviado por Mobile',
    itens_input: [],
    itens_removidos: [],
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
    const carregarPedido = async () => {
      setCarregando(true)
      try {
        const { empresaId, filialId } = await carregarContexto()

        if (pedidoParam && pedidoParam.pedi_nume) {
          const data = await apiGetComContexto(
            `pedidos/pedidos/${pedidoParam.pedi_empr}/${pedidoParam.pedi_fili}/${pedidoParam.pedi_nume}/`
          )
          const itens = data.itens || []

          // Mapear corretamente os campos de desconto
          const pedidoMapeado = {
            ...data,
            itens_input: itens.map((item) => ({
              ...item,
              desconto_item_disponivel: !!item.desconto_item_disponivel,
              percentual_desconto: Number(item.percentual_desconto || 0),
              desconto_valor: Number(item.desconto_valor || 0),
            })),
            pedi_tota: calcularTotal(itens),
            // Mapear campos de desconto geral
            desconto_geral_aplicado: !!data.desconto_geral_aplicado,
            desconto_geral_tipo: data.desconto_geral_tipo || 'percentual',
            desconto_geral_percentual: Number(
              data.desconto_geral_percentual || 0
            ),
            desconto_geral_valor: Number(data.desconto_geral_valor || 0),
            pedi_desc: Number(data.pedi_desc || 0),
          }

          setPedido(pedidoMapeado)

          await safeSetItem(PEDIDO_CACHE_ID, JSON.stringify(pedidoMapeado))
        } else {
          await AsyncStorage.removeItem(PEDIDO_CACHE_ID)
          setPedido({
            pedi_empr: empresaId,
            pedi_fili: filialId,
            pedi_forn: null,
            pedi_vend: null,
            pedi_data: new Date().toISOString().split('T')[0],
            pedi_fina: '0',
            status: 0,
            pedi_obse: 'Pedido Enviado por Mobile',
            itens_input: [],
            itens_removidos: [],
            pedi_tota: 0,
            desconto_geral_aplicado: false,
            desconto_geral_tipo: 'percentual',
            desconto_geral_percentual: 0,
            desconto_geral_valor: 0,
            pedi_desc: 0,
          })
        }
      } catch (error) {
        console.error('Erro ao carregar pedido:', error)
      } finally {
        setCarregando(false)
      }
    }

    carregarPedido()
  }, [pedidoParam])

  const handleAdicionarOuEditarItem = (novoItem, itemAnterior = null) => {
    let novosItens = [...pedido.itens_input]

    const index = itemAnterior
      ? novosItens.findIndex((i) => i.iped_prod === itemAnterior.iped_prod)
      : novosItens.findIndex((i) => i.iped_prod === novoItem.iped_prod)

    if (index !== -1) {
      novosItens[index] = novoItem
    } else {
      novosItens.push(novoItem)
    }

    const novoTotal = calcularTotal(novosItens)

    setPedido((prev) => ({
      ...prev,
      itens_input: novosItens,
      pedi_tota: novoTotal,
    }))

    setItemEditando(null)
    setModalVisivel(false)
  }

  const handleRemoverItem = (item) => {
    const novosItens = pedido.itens_input.filter(
      (i) => i.iped_prod !== item.iped_prod
    )

    const novosRemovidos = item.idExistente
      ? [...pedido.itens_removidos, item.iped_prod]
      : pedido.itens_removidos

    const novoTotal = calcularTotal(novosItens)

    setPedido((prev) => ({
      ...prev,
      itens_input: novosItens,
      itens_removidos: novosRemovidos,
      pedi_tota: novoTotal,
    }))
  }

  if (carregando) {
    return (
      <View style={styles.carregandoContainer}>
        <ActivityIndicator size="large" color="#18b7df" />
        <Text style={styles.carregandoTexto}>Carregando pedido...</Text>
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
            name="shopping-cart"
            marginHorizontal={10}
            marginBottom={10}
            marginLeft={80}
            size={20}
            color="#18b7df"
          />

          <Text style={styles.pageTitle}>
            {pedidoParam ? 'Editar Pedido' : 'Novo Pedido'}
          </Text>
        </View>

        <PedidoHeader pedido={pedido} setPedido={setPedido} />

        <View style={styles.itensSection}>
          <View style={styles.itensSectionHeader}>
            <MaterialIcons name="list" size={20} color="#18b7df" />
            <Text style={styles.sectionTitle}>Itens do Pedido</Text>
            <Text style={styles.itensCount}>
              {pedido.itens_input?.length || 0}{' '}
              {pedido.itens_input?.length === 1 ? 'item' : 'itens'}
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
            itens={pedido.itens_input}
            onEdit={(item) => {
              setItemEditando(item)
              setModalVisivel(true)
            }}
            onRemove={handleRemoverItem}
          />
        </View>
      </ScrollView>

      <ResumoPedidoComFinanceiro
        total={pedido.pedi_tota}
        pedido={pedido}
        setPedido={setPedido}
      />

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
    textAlign: 'center',
    alignContent: 'center',
    justifyContent: 'center',
    marginBottom: 4,
    marginLeft: 15,
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
    color: '#18b7df',
    fontSize: 14,
    fontWeight: '600',
    backgroundColor: '#1a252f',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  botaoAdicionarItem: {
    backgroundColor: '#18b7df',
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
