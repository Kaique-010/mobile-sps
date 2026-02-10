import React, { useState, useMemo } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  Dimensions,
} from 'react-native'
import { MaterialIcons } from '@expo/vector-icons'
import { BarChart, PieChart } from 'react-native-chart-kit'

import styles from '../stylesDash/PedidosVendaStyles'

const { width: screenWidth } = Dimensions.get('window')

export default function DashPedidosPisosGrafico({ route, navigation }) {
  const { dados = [], resumo = {}, filtros = {} } = route.params || {}
  const [tipoGrafico, setTipoGrafico] = useState('barras')

  const dadosGraficoBarras = useMemo(() => {
    const vendedores = Object.entries(resumo.totalPorVendedor || {})
      .sort(([, a], [, b]) => b - a)
      .slice(0, 6)

    return {
      labels: vendedores.map(([nome]) => {
        const parts = nome.split(' ')
        if (parts.length >= 2) {
          return `${parts[0]} ${parts[1][0]}.`
        }
        return nome.length > 10 ? nome.substring(0, 10) + '...' : nome
      }),
      datasets: [
        {
          data: vendedores.map(([, valor]) => valor),
        },
      ],
    }
  }, [resumo.totalPorVendedor])

  const dadosGraficoPizza = useMemo(() => {
    const vendedores = Object.entries(resumo.totalPorVendedor || {})
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)

    const cores = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']

    return vendedores.map(([nome, valor], index) => ({
      name: nome.length > 12 ? nome.substring(0, 12) + '...' : nome,
      population: valor,
      color: cores[index % cores.length],
      legendFontColor: '#7F7F7F',
      legendFontSize: 12,
    }))
  }, [resumo.totalPorVendedor])

  const chartConfig = {
    backgroundColor: '#ffffff',
    backgroundGradientFrom: '#ffffff',
    backgroundGradientTo: '#ffffff',
    decimalPlaces: 0,
    color: (opacity = 1) => `rgba(52, 152, 219, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(44, 62, 80, ${opacity})`,
    barPercentage: 0.7,
    fillShadowGradient: '#3498db',
    fillShadowGradientOpacity: 1,
    style: {
      borderRadius: 16,
    },
    propsForDots: {
      r: '6',
      strokeWidth: '2',
      stroke: '#3498db',
    },
  }

  const renderGrafico = () => {
    if (tipoGrafico === 'barras') {
      return (
        <BarChart
          data={dadosGraficoBarras}
          width={screenWidth - 40}
          height={220}
          chartConfig={chartConfig}
          verticalLabelRotation={0}
          showValuesOnTopOfBars
          fromZero
          yAxisLabel="R$ "
          yAxisSuffix=""
        />
      )
    } else {
      return (
        <PieChart
          data={dadosGraficoPizza}
          width={screenWidth - 40}
          height={220}
          chartConfig={chartConfig}
          accessor="population"
          backgroundColor="transparent"
          paddingLeft="15"
          absolute
        />
      )
    }
  }

  const KPICard = ({ title, value, icon, color, isMoney }) => (
    <View
      style={{
        width: '48%',
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        elevation: 2,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
        flexDirection: 'row',
        alignItems: 'center',
      }}>
      <View
        style={{
          backgroundColor: `${color}20`,
          padding: 10,
          borderRadius: 8,
          marginRight: 12,
        }}>
        <MaterialIcons name={icon} size={24} color={color} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={{ fontSize: 12, color: '#7f8c8d', marginBottom: 4 }}>
          {title}
        </Text>
        <Text style={{ fontSize: 16, fontWeight: 'bold', color: '#2c3e50' }}>
          {isMoney
            ? value.toLocaleString('pt-BR', {
                style: 'currency',
                currency: 'BRL',
              })
            : value.toLocaleString('pt-BR')}
        </Text>
      </View>
    </View>
  )

  const FilterBadge = ({ label, icon }) => (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#f1f2f6',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 20,
        marginRight: 8,
      }}>
      <MaterialIcons
        name={icon}
        size={14}
        color="#7f8c8d"
        style={{ marginRight: 6 }}
      />
      <Text style={{ fontSize: 12, color: '#2c3e50' }}>{label}</Text>
    </View>
  )

  return (
    <ScrollView style={[styles.container, { backgroundColor: '#f5f6fa' }]}>
      <View style={[styles.header, { elevation: 0, borderBottomWidth: 0 }]}>
        <TouchableOpacity
          style={styles.botaoVoltar}
          onPress={() => navigation.goBack()}>
          <MaterialIcons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <View style={styles.headerContent}>
          <Text style={styles.headerTitle}>📊 Dashboard Pisos</Text>
          <Text style={styles.headerSubtitle}>Visão Gerencial de Vendas</Text>
        </View>
      </View>

      {/* Barra de Filtros */}
      <View
        style={{
          backgroundColor: '#fff',
          paddingVertical: 12,
          paddingHorizontal: 16,
          marginBottom: 16,
          elevation: 2,
        }}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <FilterBadge
            icon="date-range"
            label={`${filtros.dataInicio} até ${filtros.dataFim}`}
          />
          {filtros.vendedor && (
            <FilterBadge icon="person" label={filtros.vendedor} />
          )}
          {filtros.cliente && (
            <FilterBadge icon="business" label={filtros.cliente} />
          )}
          {filtros.item && <FilterBadge icon="category" label={filtros.item} />}
        </ScrollView>
      </View>

      {/* Grid de KPIs */}
      <View
        style={{
          flexDirection: 'row',
          flexWrap: 'wrap',
          justifyContent: 'space-between',
          paddingHorizontal: 16,
        }}>
        <KPICard
          title="Total Pedidos"
          value={resumo.quantidadePedidos}
          icon="receipt"
          color="#3498db"
        />
        <KPICard
          title="Total Itens"
          value={resumo.quantidadeItens}
          icon="inventory"
          color="#9b59b6"
        />
        <KPICard
          title="Volume de Vendas"
          value={resumo.totalGeral}
          icon="attach-money"
          color="#27ae60"
          isMoney
        />
        <KPICard
          title="Ticket Médio"
          value={resumo.ticketMedio}
          icon="trending-up"
          color="#f39c12"
          isMoney
        />
      </View>

      {/* Seção do Gráfico */}
      <View
        style={{
          backgroundColor: '#fff',
          margin: 16,
          borderRadius: 16,
          padding: 20,
          elevation: 4,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 2 },
          shadowOpacity: 0.1,
          shadowRadius: 8,
        }}>
        <View
          style={{
            flexDirection: 'row',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 24,
          }}>
          <View>
            <Text
              style={{ fontSize: 18, fontWeight: 'bold', color: '#2c3e50' }}>
              Desempenho por Vendedor
            </Text>
            <Text style={{ fontSize: 12, color: '#95a5a6' }}>
              Top 6 Vendedores
            </Text>
          </View>

          {/* Seletor de Tipo de Gráfico */}
          <View
            style={{
              flexDirection: 'row',
              backgroundColor: '#f1f2f6',
              borderRadius: 8,
              padding: 4,
            }}>
            <TouchableOpacity
              onPress={() => setTipoGrafico('barras')}
              style={{
                paddingHorizontal: 12,
                paddingVertical: 6,
                backgroundColor:
                  tipoGrafico === 'barras' ? '#fff' : 'transparent',
                borderRadius: 6,
                elevation: tipoGrafico === 'barras' ? 2 : 0,
              }}>
              <MaterialIcons
                name="bar-chart"
                size={20}
                color={tipoGrafico === 'barras' ? '#3498db' : '#95a5a6'}
              />
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => setTipoGrafico('pizza')}
              style={{
                paddingHorizontal: 12,
                paddingVertical: 6,
                backgroundColor:
                  tipoGrafico === 'pizza' ? '#fff' : 'transparent',
                borderRadius: 6,
                elevation: tipoGrafico === 'pizza' ? 2 : 0,
              }}>
              <MaterialIcons
                name="pie-chart"
                size={20}
                color={tipoGrafico === 'pizza' ? '#3498db' : '#95a5a6'}
              />
            </TouchableOpacity>
          </View>
        </View>

        {renderGrafico()}
      </View>
    </ScrollView>
  )
}
