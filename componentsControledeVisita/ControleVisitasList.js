import React, { useState, useEffect, useCallback, onRefresh } from 'react'
import { useFocusEffect } from '@react-navigation/native'

import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  Alert,
  RefreshControl,
  Modal,
  StyleSheet,
  TextInput,
} from 'react-native'
import Toast from 'react-native-toast-message'
import { MaterialIcons, Feather } from '@expo/vector-icons'
import { apiGetComContexto, apiDeleteComContexto } from '../utils/api'
import ControleVisitaCard from './ControleVisitaCard'
import ControleVisitaFilters from './ControleVisitaFilters'

export default function ControleVisitasList({ navigation }) {
  const [visitas, setVisitas] = useState([])
  const [etapas, setEtapas] = useState([])
  const [stats, setStats] = useState([])
  const [estatisticasGerais, setEstatisticasGerais] = useState({
    etapas: {},
    top_vendedores: {},
    total_visitas: 0,
  })
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({
    etapa: '',
    vendedor: '',
    data_inicio: '',
    data_fim: '',
    cliente_nome: '',
    proxima_visita: false, // Novo filtro
  })

  // Mover esta função para ANTES de carregarVisitas
  const getEtapaColor = (etapaId) => {
    const colors = ['#3498db', '#e74c3c', '#f39c12', '#2ecc71', '#9b59b6']
    return colors[etapaId % colors.length] || '#95a5a6'
  }

  const extrairEtapasDasVisitas = (visitas) => {
    const etapasUnicas = new Map()

    visitas.forEach((visita) => {
      if (visita.ctrl_etapa && visita.etapa_descricao) {
        etapasUnicas.set(visita.ctrl_etapa, {
          etap_id: visita.ctrl_etapa,
          etap_descricao: visita.etapa_descricao,
          etap_cor: getEtapaColor(visita.ctrl_etapa),
        })
      }
    })

    return Array.from(etapasUnicas.values())
  }

  // Função corrigida para aplicar filtros
  const carregarVisitas = useCallback(
    async (filtrosAplicados = {}) => {
      setLoading(true)
      try {
        // Se for filtro de próxima visita, usar endpoint específico
        if (filtrosAplicados.proxima_visita) {
          const response = await apiGetComContexto(
            'controledevisitas/controle-visitas/proximas/',
            {
              limit: 1000,
            }
          )

          const proximasVisitas = response?.proximas_visitas || []

          const data = proximasVisitas.map((visita) => ({
            ctrl_id: visita.ctrl_id,
            ctrl_numero: visita.ctrl_numero,
            ctrl_data: visita.ctrl_data_original,
            ctrl_prox_visi: visita.ctrl_prox_visi,
            ctrl_etapa: visita.etapa?.id,
            etapa_descricao: visita.etapa?.nome,
            ctrl_cliente: visita.cliente?.id,
            cliente_nome: visita.cliente?.nome,
            ctrl_vendedor: visita.vendedor?.id,
            vendedor_nome: visita.vendedor?.nome,
            ctrl_contato: visita.contato,
            ctrl_fone: visita.telefone,
            ctrl_obse: visita.observacoes,
            dias_restantes: visita.dias_restantes,
            urgencia: visita.urgencia,
          }))

          setVisitas(data)

          // Extrair etapas
          const etapasExtraidas = extrairEtapasDasVisitas(data)
          setEtapas(etapasExtraidas)

          // Calcular stats
          const total = data.length
          const estatisticasCalculadas = etapasExtraidas.map((etapa) => {
            const visitasEtapa = data.filter(
              (v) => v.ctrl_etapa === etapa.etap_id
            )
            return {
              id: etapa.etap_id,
              label: etapa.etap_descricao,
              value: etapa.etap_id,
              color: etapa.etap_cor,
              count: visitasEtapa.length,
              percentage:
                total > 0
                  ? ((visitasEtapa.length / total) * 100).toFixed(1)
                  : '0',
            }
          })

          setStats(estatisticasCalculadas)

          Toast.show({
            type: 'success',
            text1: `${data.length} próximas visitas carregadas!`,
          })

          return
        }

        // Construir parâmetros da query com filtros para endpoint normal
        const queryParams = {
          limit: 1000,
        }

        // Aplicar filtros se existirem
        if (filtrosAplicados.etapa) {
          queryParams.etapa = filtrosAplicados.etapa
        }
        if (filtrosAplicados.vendedor) {
          queryParams.ctrl_vendedor = filtrosAplicados.vendedor
        }
        if (filtrosAplicados.data_inicio) {
          queryParams.data_inicio = filtrosAplicados.data_inicio
        }
        if (filtrosAplicados.data_fim) {
          queryParams.data_fim = filtrosAplicados.data_fim
        }
        if (filtrosAplicados.cliente_nome) {
          queryParams.cliente_nome = filtrosAplicados.cliente_nome
        }

        // Aplicar busca por texto se existir
        if (searchText.trim()) {
          queryParams.search = searchText.trim()
        }

        const response = await apiGetComContexto(
          'controledevisitas/controle-visitas/',
          queryParams
        )

        // Garantir que data seja um array
        const data = response?.results || response || []
        if (!Array.isArray(data)) {
          console.warn('API retornou dados em formato inesperado:', data)
          setVisitas([])
          return
        }

        setVisitas(data)

        // Extrair etapas
        const etapasExtraidas = extrairEtapasDasVisitas(data)
        setEtapas(etapasExtraidas)

        // Calcular stats
        const total = data.length
        const estatisticasCalculadas = etapasExtraidas.map((etapa) => {
          const visitasEtapa = data.filter(
            (v) => v.ctrl_etapa === etapa.etap_id
          )
          return {
            id: etapa.etap_id,
            label: etapa.etap_descricao,
            value: etapa.etap_id,
            color: etapa.etap_cor,
            count: visitasEtapa.length,
            percentage:
              total > 0
                ? ((visitasEtapa.length / total) * 100).toFixed(1)
                : '0',
          }
        })

        setStats(estatisticasCalculadas)

        Toast.show({
          type: 'success',
          text1: `${data.length} visitas carregadas!`,
        })
      } catch (error) {
        console.error('Erro ao carregar visitas:', error)
        Toast.show({
          type: 'error',
          text1: 'Erro ao carregar visitas',
          text2: error.message,
        })
      } finally {
        setLoading(false)
      }
    },
    [searchText]
  )

  // useEffect para carregar visitas inicialmente
  useEffect(() => {
    carregarVisitas(filters)
  }, [])

  // useEffect para aplicar filtros quando mudarem
  useEffect(() => {
    if (Object.values(filters).some((f) => f)) {
      carregarVisitas(filters)
    }
  }, [filters, carregarVisitas])

  // useEffect para busca por texto
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      carregarVisitas(filters)
    }, 500) // Debounce de 500ms

    return () => clearTimeout(timeoutId)
  }, [searchText, carregarVisitas])

  useFocusEffect(
    useCallback(() => {
      carregarVisitas(filters)
    }, [filters, carregarVisitas])
  )

  const handleEdit = (visita) => {
    navigation.navigate('ControleVisitaForm', {
      visitaId: visita.ctrl_id,
      mode: 'edit',
      visita: visita,
      cliente: {
        id: visita.ctrl_cliente,
        nome: visita.cliente_nome,
      },
      vendedor: {
        id: visita.ctrl_vendedor,
        nome: visita.vendedor_nome,
      },
    })
  }

  const handleDelete = async (visita) => {
    Alert.alert(
      'Confirmar Exclusão',
      `Deseja realmente excluir a visita ${visita.ctrl_numero}?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Excluir',
          style: 'destructive',
          onPress: async () => {
            try {
              // CORRIGIDO: endpoint duplicado
              await apiDeleteComContexto(
                `controledevisitas/controle-visitas/${visita.ctrl_id}/`
              )
              Alert.alert('Sucesso', 'Visita excluída com sucesso')
              carregarVisitas()
            } catch (error) {
              console.error('Erro ao excluir visita:', error)
              Alert.alert('Erro', 'Não foi possível excluir a visita')
            }
          },
        },
      ]
    )
  }

  const handleView = (visita) => {
    navigation.navigate('ControleVisitaDetalhes', { visitaId: visita.ctrl_id })
  }

  const applyFilters = (newFilters) => {
    setFilters(newFilters)
    setShowFilters(false)
    // carregarVisitas será chamado automaticamente pelo useEffect
  }

  const clearFilters = () => {
    const filtrosLimpos = {
      etapa: '',
      vendedor: '',
      data_inicio: '',
      data_fim: '',
      cliente_nome: '',
      proxima_visita: false,
    }
    setFilters(filtrosLimpos)
    setSearchText('')
    setShowFilters(false)
    // carregarVisitas será chamado automaticamente pelo useEffect
  }
  useFocusEffect(
    useCallback(() => {
      carregarVisitas(filters)
    }, [filters, carregarVisitas])
  )

  const renderStatsCard = () => {
    if (!etapas || etapas.length === 0) {
      return (
        <View style={styles.statsContainer}>
          <Text style={styles.statsTitle}>Funil de Vendas</Text>
          <Text style={styles.statLabel}>Carregando etapas...</Text>
        </View>
      )
    }

    if (!stats || stats.length === 0) {
      return (
        <View style={styles.statsContainer}>
          <Text style={styles.statsTitle}>Funil de Vendas</Text>
          <Text style={styles.statLabel}>Calculando estatísticas...</Text>
        </View>
      )
    }

    return (
      <View style={styles.statsContainer}>
        <Text style={styles.statsTitle}>Funil de Vendas</Text>
        <View style={styles.statsGrid}>
          {stats.map((etapa) => (
            <TouchableOpacity
              key={etapa.id}
              style={[styles.statCard, { borderLeftColor: etapa.color }]}
              onPress={() => setFilters({ ...filters, etapa: etapa.value })}>
              <Text style={styles.statNumber}>{etapa.count}</Text>
              <Text style={styles.statLabel}>{etapa.label}</Text>
              <Text style={styles.statPercentage}>{etapa.percentage}%</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
    )
  }

  const renderHeader = () => (
    <View style={styles.header}>
      <View style={styles.searchContainer}>
        <Feather
          name="search"
          size={20}
          color="#666"
          style={styles.searchIcon}
        />
        <TextInput
          style={styles.searchInput}
          placeholder="Buscar por cliente, vendedor..."
          value={searchText}
          onChangeText={setSearchText}
          placeholderTextColor="#666"
        />
        <TouchableOpacity
          style={styles.filterButton}
          onPress={() => setShowFilters(true)}>
          <Feather name="filter" size={20} color="#2ecc71" />
        </TouchableOpacity>
      </View>

      {renderStatsCard()}

      <View style={styles.actionButtons}>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() =>
            navigation.navigate('ControleVisitaForm', { mode: 'create' })
          }>
          <MaterialIcons name="add" size={24} color="#fff" />
          <Text style={styles.addButtonText}>Nova Visita</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.dashboardButton}
          onPress={() => navigation.navigate('ControleVisitaDashboard')}>
          <MaterialIcons name="dashboard" size={24} color="#fff" />
          <Text style={styles.dashboardButtonText}>Dashboard</Text>
        </TouchableOpacity>
      </View>
    </View>
  )

  const renderVisita = ({ item }) => (
    <ControleVisitaCard
      visita={item}
      onEdit={handleEdit}
      onDelete={handleDelete}
      onView={handleView}
      etapas={etapas}
    />
  )

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <MaterialIcons name="business-center" size={64} color="#666" />
      <Text style={styles.emptyTitle}>Nenhuma visita encontrada</Text>
      <Text style={styles.emptySubtitle}>
        {searchText || Object.values(filters).some((f) => f)
          ? 'Tente ajustar os filtros de busca'
          : 'Comece criando sua primeira visita'}
      </Text>
      <TouchableOpacity
        style={styles.emptyButton}
        onPress={() =>
          navigation.navigate('ControleVisitaForm', { mode: 'create' })
        }>
        <Text style={styles.emptyButtonText}>Criar Primeira Visita</Text>
      </TouchableOpacity>
    </View>
  )

  return (
    <View style={styles.container}>
      <FlatList
        data={visitas}
        renderItem={renderVisita}
        keyExtractor={(item, index) => {
          if (item.ctrl_id) return item.ctrl_id.toString()
          if (item.id) return item.id.toString()
          return index.toString()
        }}
        ListHeaderComponent={renderHeader}
        ListEmptyComponent={!loading ? renderEmpty : null}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={['#2ecc71']}
            tintColor="#2ecc71"
          />
        }
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
      />

      <Modal
        visible={showFilters}
        animationType="slide"
        presentationStyle="pageSheet">
        <ControleVisitaFilters
          filters={filters}
          onApply={applyFilters}
          onClear={clearFilters}
          onClose={() => setShowFilters(false)}
          etapas={etapas}
        />
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0d1421',
  },
  listContainer: {
    flexGrow: 1,
    padding: 16,
  },
  header: {
    marginBottom: 16,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a252f',
    borderRadius: 12,
    paddingHorizontal: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#2a3441',
  },
  searchIcon: {
    marginRight: 12,
  },
  searchInput: {
    flex: 1,
    height: 48,
    color: '#fff',
    fontSize: 16,
  },
  filterButton: {
    padding: 8,
  },
  statsContainer: {
    backgroundColor: '#1a252f',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#2a3441',
  },
  statsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
    textAlign: 'center',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statCard: {
    backgroundColor: '#0d1421',
    borderRadius: 8,
    padding: 12,
    width: '48%',
    marginBottom: 8,
    borderLeftWidth: 4,
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  statPercentage: {
    fontSize: 10,
    color: '#2ecc71',
    marginTop: 2,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  addButton: {
    flex: 1,
    backgroundColor: '#2ecc71',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  addButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  dashboardButton: {
    flex: 1,
    backgroundColor: '#3498db',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  dashboardButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 16,
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 24,
    paddingHorizontal: 32,
  },
  emptyButton: {
    backgroundColor: '#2ecc71',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 24,
  },
  emptyButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
})
