import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  RefreshControl,
} from 'react-native'
import { MaterialIcons } from '@expo/vector-icons'
import { PieChart, BarChart } from 'react-native-chart-kit'
import { apiGetComContexto } from '../utils/api'
import { showToast } from '../config/toastConfig'
import Toast from 'react-native-toast-message'

const { width, height } = Dimensions.get('window')

export default function ControleVisitaDashboard({ navigation }) {
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [etapas, setEtapas] = useState([])
  const [dashboardData, setDashboardData] = useState({
    totalVisitas: 0,
    visitasHoje: 0,
    visitasSemana: 0,
    visitasMes: 0,
    etapasData: [],
    vendedoresData: [],
    proximasVisitas: [],
    kmPercorrido: 0,
  })

  useEffect(() => {
    carregarDashboard()
  }, [])

  const carregarEtapas = async () => {
    try {
      const response = await apiGetComContexto(
        'controledevisitas/etapas-visita/'
      )
      const etapasData = Array.isArray(response)
        ? response
        : response?.results || []

      const etapasComCores = etapasData.map((etapa, index) => ({
        ...etapa,
        etap_cor: etapa.etap_cor || getEtapaColorPastel(index),
      }))

      setEtapas(etapasComCores)
      return etapasComCores
    } catch (error) {
      console.error('Erro ao carregar etapas:', error)
      return []
    }
  }

  const carregarDashboard = async () => {
    try {
      setLoading(true)
      console.log('Iniciando carregamento do dashboard...')

      const etapasData = await carregarEtapas()

      let visitasResponse, estatisticas, proximasVisitas

      try {
        visitasResponse = await apiGetComContexto(
          'controledevisitas/controle-visitas/',
          { limit: 10000 }
        )
        Toast.show({
          type: 'success',
          text1: `${visitasResponse?.results?.length} Visitas carregadas com sucesso!`,
        })
      } catch (error) {
        console.error(
          'Erro ao carregar visitas:',
          error.response?.data || error.message
        )
        visitasResponse = { results: [] }
      }

      try {
        estatisticas = await apiGetComContexto(
          'controledevisitas/controle-visitas/estatisticas/'
        )
      } catch (error) {
        console.log('Endpoint de estatísticas não disponível')
        estatisticas = []
      }

      try {
        proximasVisitas = await apiGetComContexto(
          'controledevisitas/controle-visitas/proximas/',
          { limit: 10000 }
        )
        Toast.show({
          type: 'success',
          text1: `${
            proximasVisitas?.proximas_visitas?.length || 0
          } Próximas Visitas carregadas com sucesso!`,
        })
      } catch (error) {
        console.log('Endpoint de próximas visitas não disponível')
        proximasVisitas = { proximas_visitas: [] }
      }

      const visitas = Array.isArray(visitasResponse)
        ? visitasResponse
        : Array.isArray(visitasResponse?.results)
        ? visitasResponse.results
        : []

      console.log('Visitas processadas:', visitas.length)

      // Processar dados das etapas com validação
      const etapasCount = {}
      if (visitas && visitas.length > 0) {
        visitas.forEach((visita) => {
          const etapa =
            visita.etapa_descricao || visita.etapa_display || 'Não definida'
          etapasCount[etapa] = (etapasCount[etapa] || 0) + 1
        })
      }

      // Melhorar formatação dos dados do gráfico de pizza - SEM LEGENDAS
      const etapasDataChart =
        Object.entries(etapasCount).length > 0
          ? Object.entries(etapasCount).map(([name, population], index) => {
              const etapaInfo = etapasData.find(
                (e) => e.etap_descricao === name || e.etvi_descricao === name
              )
              // Nome muito curto para não quebrar
              const shortName = name.length > 8 ? name.substring(0, 8) : name
              return {
                name: shortName,
                population,
                color:
                  etapaInfo?.etvi_cor ||
                  etapaInfo?.etap_cor ||
                  getEtapaColorVibrant(index),
                legendFontColor: '#ffffff',
                legendFontSize: 10,
              }
            })
          : []

      // Processar dados dos vendedores com validação
      const vendedoresCount = {}
      if (visitas && visitas.length > 0) {
        visitas.forEach((visita) => {
          const vendedor = visita.vendedor_nome || 'Não definido'
          vendedoresCount[vendedor] = (vendedoresCount[vendedor] || 0) + 1
        })
      }

      // Preparar dados dos vendedores
      const topVendedores = Object.entries(vendedoresCount).slice(0, 5)
      const vendedoresNomesCompletos = topVendedores.map(([nome]) => nome)

      const vendedoresData = {
        labels: topVendedores.map(([label]) => {
          // Pegar apenas as iniciais ou primeiros 6 caracteres para o gráfico
          const words = label.split(' ')
          if (words.length > 1) {
            return words
              .map((w) => w.charAt(0))
              .join('')
              .substring(0, 3) // Iniciais
          }
          return label.substring(0, 6) // Primeiros 6 caracteres
        }),
        datasets: [
          {
            data:
              topVendedores.map(([, count]) => count).length > 0
                ? topVendedores.map(([, count]) => count)
                : [0],
            colors: topVendedores.map(
              (_, index) => () => getVendedorColor(index)
            ),
          },
        ],
        // Armazenar os nomes completos para usar na legenda
        nomesCompletos: vendedoresNomesCompletos,
      }

      // Calcular KM percorrido com validação
      const kmTotal =
        visitas && visitas.length > 0
          ? visitas.reduce((total, visita) => {
              const km = parseFloat(visita.km_percorrido) || 0
              return total + km
            }, 0)
          : 0

      const proximasArray = Array.isArray(proximasVisitas?.proximas_visitas)
        ? proximasVisitas.proximas_visitas
        : []

      // Calcular estatísticas
      const totalVisitas = visitas ? visitas.length : 0
      const visitasHoje =
        visitas && visitas.length > 0
          ? visitas.filter((v) => isToday(v.ctrl_data)).length
          : 0
      const visitasSemana =
        visitas && visitas.length > 0
          ? visitas.filter((v) => isThisWeek(v.ctrl_data)).length
          : 0
      const visitasMes =
        visitas && visitas.length > 0
          ? visitas.filter((v) => isThisMonth(v.ctrl_data)).length
          : 0

      setDashboardData({
        totalVisitas,
        visitasHoje,
        visitasSemana,
        visitasMes,
        etapasData: etapasDataChart,
        vendedoresData,
        proximasVisitas: proximasArray.slice(0, 5).map((visita) => ({
          ctrl_id: visita.ctrl_id,
          cliente_nome: visita.cliente?.nome || visita.cliente_nome,
          ctrl_prox_visi: visita.ctrl_prox_visi,
          vendedor_nome: visita.vendedor?.nome || visita.vendedor_nome,
        })),
        kmPercorrido: kmTotal,
      })
    } catch (error) {
      console.error('Erro ao carregar dashboard:', error)
      showToast('Erro ao carregar dados do dashboard', 'error')

      setDashboardData({
        totalVisitas: 0,
        visitasHoje: 0,
        visitasSemana: 0,
        visitasMes: 0,
        etapasData: [],
        vendedoresData: { labels: [], datasets: [{ data: [] }] },
        proximasVisitas: [],
        kmPercorrido: 0,
      })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const onRefresh = () => {
    setRefreshing(true)
    carregarDashboard()
  }

  // Cores mais vibrantes e modernas
  const getEtapaColorVibrant = (index) => {
    const coresVibrantes = [
      '#FF6B6B', // Vermelho coral
      '#4ECDC4', // Turquesa
      '#45B7D1', // Azul claro
      '#FFA07A', // Salmão
      '#98D8C8', // Verde menta
      '#F7DC6F', // Amarelo dourado
      '#BB8FCE', // Roxo claro
      '#85C1E9', // Azul bebê
      '#F8C471', // Laranja claro
      '#82E0AA', // Verde claro
    ]
    return coresVibrantes[index % coresVibrantes.length]
  }

  const getEtapaColorPastel = (index) => {
    const coresPasteis = [
      '#FFB3BA', // Rosa pastel
      '#FFDFBA', // Pêssego pastel
      '#FFFFBA', // Amarelo pastel
      '#BAFFC9', // Verde pastel
      '#BAE1FF', // Azul pastel
      '#E1BAFF', // Roxo pastel
      '#FFBAE1', // Magenta pastel
      '#C9FFBA', // Verde claro pastel
    ]
    return coresPasteis[index % coresPasteis.length]
  }

  // Cores para o gráfico de barras dos vendedores
  const getVendedorColor = (index) => {
    const cores = [
      '#FF6B6B', // Vermelho
      '#4ECDC4', // Turquesa
      '#45B7D1', // Azul
      '#FFA07A', // Salmão
      '#98D8C8', // Verde
    ]
    return cores[index % cores.length]
  }

  const isToday = (date) => {
    const today = new Date()
    const visitaDate = new Date(date)
    return visitaDate.toDateString() === today.toDateString()
  }

  const isThisWeek = (date) => {
    const today = new Date()
    const visitaDate = new Date(date)
    const weekStart = new Date(today.setDate(today.getDate() - today.getDay()))
    return visitaDate >= weekStart
  }

  const isThisMonth = (date) => {
    const today = new Date()
    const visitaDate = new Date(date)
    return (
      visitaDate.getMonth() === today.getMonth() &&
      visitaDate.getFullYear() === today.getFullYear()
    )
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('pt-BR')
  }

  // Configuração melhorada dos gráficos - SIMPLIFICADA
  const chartConfig = {
    backgroundColor: '#1a252f',
    backgroundGradientFrom: '#1a252f',
    backgroundGradientTo: '#2c3e50',
    decimalPlaces: 0,
    color: (opacity = 1) => `rgba(78, 205, 196, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
    style: {
      borderRadius: 16,
    },
    propsForLabels: {
      fontSize: 8, // Menor
      fontWeight: '400',
    },
    propsForVerticalLabels: {
      fontSize: 8, // Muito menor
      fontWeight: '400',
    },
    propsForHorizontalLabels: {
      fontSize: 8, // Muito menor
      fontWeight: '400',
    },
  }

  // Dimensões responsivas dos gráficos - MENORES E MAIS SIMPLES
  const getChartDimensions = () => {
    const screenWidth = width
    const chartWidth = screenWidth - 64 // Mais margem
    const pieHeight = 200 // Fixo e menor
    const barHeight = 180 // Fixo e menor

    return {
      width: chartWidth,
      pieHeight: pieHeight,
      barHeight: barHeight,
    }
  }

  const { width: chartWidth, pieHeight, barHeight } = getChartDimensions()

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <MaterialIcons name="analytics" size={48} color="#4ECDC4" />
        <Text style={styles.loadingText}>Carregando dashboard...</Text>
      </View>
    )
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Dashboard CRM</Text>
        <Text style={styles.subtitle}>Controle de Visitas</Text>
      </View>

      {/* Cards de Resumo */}
      <View style={styles.cardsContainer}>
        <View style={styles.cardRow}>
          <View style={[styles.card, styles.cardPrimary]}>
            <MaterialIcons name="visibility" size={24} color="#fff" />
            <Text style={styles.cardNumber}>{dashboardData.totalVisitas}</Text>
            <Text style={styles.cardLabel}>Total de Visitas</Text>
          </View>
          <View style={[styles.card, styles.cardSuccess]}>
            <MaterialIcons name="today" size={24} color="#fff" />
            <Text style={styles.cardNumber}>{dashboardData.visitasHoje}</Text>
            <Text style={styles.cardLabel}>Hoje</Text>
          </View>
        </View>
        <View style={styles.cardRow}>
          <View style={[styles.card, styles.cardWarning]}>
            <MaterialIcons name="date-range" size={24} color="#fff" />
            <Text style={styles.cardNumber}>{dashboardData.visitasSemana}</Text>
            <Text style={styles.cardLabel}>Esta Semana</Text>
          </View>
          <View style={[styles.card, styles.cardInfo]}>
            <MaterialIcons name="calendar-month" size={24} color="#fff" />
            <Text style={styles.cardNumber}>{dashboardData.visitasMes}</Text>
            <Text style={styles.cardLabel}>Este Mês</Text>
          </View>
        </View>
        <View style={styles.cardRow}>
          <View style={[styles.card, styles.cardDanger, { flex: 1 }]}>
            <MaterialIcons name="speed" size={24} color="#fff" />
            <Text style={styles.cardNumber}>
              {(dashboardData.kmPercorrido || 0).toFixed(0)} km
            </Text>
            <Text style={styles.cardLabel}>KM Percorrido</Text>
          </View>
        </View>
      </View>

      {/* Gráfico de Etapas - SIMPLIFICADO */}
      {dashboardData.etapasData && dashboardData.etapasData.length > 0 && (
        <View style={styles.chartContainer}>
          <View style={styles.chartHeader}>
            <MaterialIcons name="pie-chart" size={40} color="#4ECDC4" />
            <Text style={styles.chartTitle}>Visitas por Etapa</Text>
          </View>
          <View style={styles.chartWrapper}>
            <PieChart
              data={dashboardData.etapasData}
              width={chartWidth}
              height={pieHeight}
              chartConfig={chartConfig}
              accessor="population"
              backgroundColor="transparent"
              paddingLeft="60"
              hasLegend={false} // SEM LEGENDA para evitar bagunça
              avoidFalseZero={true}
            />
          </View>
          {/* Legenda customizada embaixo */}
          <View style={styles.customLegend}>
            {dashboardData.etapasData.slice(0, 10).map((item, index) => (
              <View key={index} style={styles.legendItem}>
                <View
                  style={[styles.legendColor, { backgroundColor: item.color }]}
                />
                <Text style={styles.legendText}>
                  {item.name}: {item.population}
                </Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* Gráfico de Vendedores - SIMPLIFICADO */}
      {dashboardData.vendedoresData.labels?.length > 0 &&
        dashboardData.vendedoresData.datasets[0].data.some(
          (value) => value > 0
        ) && (
          <View style={styles.chartContainer}>
            <View style={styles.chartHeader}>
              <MaterialIcons name="bar-chart" size={30} color="#4ECDC4" />
              <Text style={styles.chartTitle}>Top 5 Vendedores</Text>
            </View>
            <View style={styles.chartWrapper}>
              <BarChart
                data={dashboardData.vendedoresData}
                width={chartWidth}
                height={barHeight}
                chartConfig={chartConfig}
                verticalLabelRotation={0}
                showValuesOnTopOfBars={false} // Sem valores nas barras
                fromZero={true}
                showBarTops={false}
                flatColor={true}
                withInnerLines={false} // Sem linhas internas
                withHorizontalLabels={false} // Sem labels horizontais
              />
            </View>
            {/* Mostrar os nomes completos embaixo */}
            <View style={styles.vendedoresLegend}>
              {dashboardData.vendedoresData.nomesCompletos?.map(
                (nomeCompleto, index) => {
                  const visitas =
                    dashboardData.vendedoresData.datasets[0].data[index]
                  return (
                    <Text key={index} style={styles.vendedorLegendText}>
                      {nomeCompleto}: {visitas} visitas
                    </Text>
                  )
                }
              )}
            </View>
          </View>
        )}

      {/* Mensagem quando não há dados para gráficos */}
      {(!dashboardData.etapasData || dashboardData.etapasData.length === 0) &&
        (!dashboardData.vendedoresData.labels ||
          dashboardData.vendedoresData.labels.length === 0) && (
          <View style={styles.chartContainer}>
            <View style={styles.emptyChartContainer}>
              <MaterialIcons name="analytics" size={48} color="#666" />
              <Text style={styles.emptyChartText}>
                Nenhum dado disponível para gráficos
              </Text>
              <Text style={styles.emptyChartSubtext}>
                Adicione algumas visitas para visualizar estatísticas
              </Text>
            </View>
          </View>
        )}

      {/* Próximas Visitas */}
      <View style={styles.proximasContainer}>
        <View style={styles.proximasHeader}>
          <View style={styles.proximasTitleContainer}>
            <MaterialIcons name="schedule" size={20} color="#4ECDC4" />
            <Text style={styles.proximasTitle}>Próximas Visitas</Text>
          </View>
          <TouchableOpacity
            onPress={() => navigation.navigate('ControleVisitas')}
            style={styles.verTodosButton}>
            <Text style={styles.verTodosText}>Ver Todas</Text>
            <MaterialIcons name="arrow-forward" size={16} color="#4ECDC4" />
          </TouchableOpacity>
        </View>

        {dashboardData.proximasVisitas.length > 0 ? (
          dashboardData.proximasVisitas.map((visita, index) => (
            <TouchableOpacity
              key={index}
              style={styles.proximaVisitaCard}
              onPress={() =>
                navigation.navigate('ControleVisitaDetalhes', {
                  visitaId: visita.ctrl_id,
                })
              }>
              <View style={styles.proximaVisitaInfo}>
                <Text style={styles.proximaVisitaCliente}>
                  {visita.cliente_nome}
                </Text>
                <Text style={styles.proximaVisitaData}>
                  {formatDate(visita.ctrl_prox_visi)}
                </Text>
                <Text style={styles.proximaVisitaVendedor}>
                  {visita.vendedor_nome}
                </Text>
              </View>
              <MaterialIcons name="chevron-right" size={24} color="#666" />
            </TouchableOpacity>
          ))
        ) : (
          <View style={styles.emptyProximas}>
            <MaterialIcons name="event-available" size={48} color="#666" />
            <Text style={styles.emptyProximasText}>
              Nenhuma visita agendada
            </Text>
          </View>
        )}
      </View>

      {/* Botões de Ação */}
      <View style={styles.actionsContainer}>
        <TouchableOpacity
          style={[styles.actionButton, styles.actionPrimary]}
          onPress={() => navigation.navigate('ControleVisitaForm')}>
          <MaterialIcons name="add" size={24} color="#fff" />
          <Text style={styles.actionButtonText}>Nova Visita</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, styles.actionSecondary]}
          onPress={() => navigation.navigate('ControleVisitas')}>
          <MaterialIcons name="list" size={24} color="#fff" />
          <Text style={styles.actionButtonText}>Ver Todas</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0d1421',
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#fff',
    fontSize: 16,
    marginTop: 16,
  },
  header: {
    padding: 20,
    alignItems: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
  },
  cardsContainer: {
    paddingHorizontal: 16,
    marginBottom: 20,
  },
  cardRow: {
    flexDirection: 'row',
    marginBottom: 12,
    gap: 12,
  },
  card: {
    flex: 1,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    minHeight: 100,
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  cardPrimary: {
    backgroundColor: '#3498db',
  },
  cardSuccess: {
    backgroundColor: '#4ECDC4', // Cor turquesa moderna
  },
  cardWarning: {
    backgroundColor: '#f39c12',
  },
  cardInfo: {
    backgroundColor: '#9b59b6',
  },
  cardDanger: {
    backgroundColor: '#FF6B6B', // Cor vermelha moderna
  },
  cardNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginVertical: 8,
  },
  cardLabel: {
    fontSize: 12,
    color: '#fff',
    textAlign: 'center',
    fontWeight: '500',
  },
  chartContainer: {
    backgroundColor: '#1a252f',
    margin: 16,
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4.65,
    elevation: 8,
  },
  chartHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#2c3e50',
  },
  chartTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginLeft: 8,
  },
  chartWrapper: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyChartContainer: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyChartText: {
    color: '#666',
    fontSize: 16,
    marginTop: 12,
    textAlign: 'center',
  },
  emptyChartSubtext: {
    color: '#555',
    fontSize: 14,
    marginTop: 6,
    textAlign: 'center',
  },
  proximasContainer: {
    margin: 16,
    backgroundColor: '#1a252f',
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4.65,
    elevation: 8,
  },
  proximasHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#2c3e50',
  },
  proximasTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  proximasTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginLeft: 8,
  },
  verTodosButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: 'rgba(78, 205, 196, 0.1)',
  },
  verTodosText: {
    color: '#4ECDC4',
    fontSize: 14,
    fontWeight: '600',
  },
  proximaVisitaCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#2c3e50',
    padding: 16,
    borderRadius: 12,
    marginBottom: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#4ECDC4',
  },
  proximaVisitaInfo: {
    flex: 1,
  },
  proximaVisitaCliente: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  proximaVisitaData: {
    fontSize: 14,
    color: '#4ECDC4',
    marginBottom: 2,
    fontWeight: '500',
  },
  proximaVisitaVendedor: {
    fontSize: 12,
    color: '#999',
  },
  emptyProximas: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  emptyProximasText: {
    color: '#666',
    fontSize: 16,
    marginTop: 12,
  },
  actionsContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingBottom: 32,
    gap: 12,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  actionPrimary: {
    backgroundColor: '#4ECDC4',
  },
  actionSecondary: {
    backgroundColor: '#45B7D1',
  },
  customLegend: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginTop: 16,
    paddingHorizontal: 8,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    margin: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    backgroundColor: '#2c3e50',
    borderRadius: 8,
  },
  legendColor: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 6,
  },
  legendText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '500',
  },
  vendedoresLegend: {
    marginTop: 12,
    paddingHorizontal: 8,
  },
  vendedorLegendText: {
    color: '#fff',
    fontSize: 11,
    marginBottom: 4,
    textAlign: 'center',
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
})
