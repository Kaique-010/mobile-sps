//Ordem de Serviço da Eletrocometa

import React, { useEffect, useState, useMemo, useCallback } from 'react'
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Image,
  ScrollView,
  TextInput,
} from 'react-native'
import { apiGetComContextoos } from '../utils/api'
import { Ionicons } from '@expo/vector-icons'
import commonStyles from '../styles/painelOsCommon'
import desktopStyles from '../styles/painelOsDesktop'
import mobileStyles from '../styles/painelOsMobile'
import debounce from 'lodash.debounce'

const STATUS_OPTIONS = [
  { label: 'Todas', value: null },
  { label: 'Aberta', value: 0 },
  { label: 'Orçamento gerado', value: 1 },
  { label: 'Aguardando Liberação', value: 2 },
  { label: 'Liberada', value: 3 },
  { label: 'Finalizada', value: 4 },
  { label: 'Reprovada', value: 5 },
  { label: 'Faturada parcial', value: 20 },
  { label: 'Em atraso', value: 21 },
]

const statusColors = {
  0: '#d1ecf1',
  1: '#fff3cd',
  21: '#f5c6cb',
  3: '#d1ecf1',
  4: '#d4edda',
  5: '#f5c6cb',
  20: '#bee5eb',
}

const PRIORIDADE_OPTIONS = [
  { label: 'Todas', value: null },
  { label: 'Normal', value: 'normal' },
  { label: 'Alerta', value: 'alerta' },
  { label: 'Urgente', value: 'urgente' },
]

const prioridadeColors = {
  normal: '#d1ecf1',
  alerta: '#ffc107',
  urgente: '#dc3545',
}

const PainelAcompanhamento = ({ navigation }) => {
  const [ordens, setOrdens] = useState([])
  const [loading, setLoading] = useState(false)
  const [filtroStatus, setFiltroStatus] = useState(null)
  const [filtroPrioridade, setFiltroPrioridade] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [searchValue, setSearchValue] = useState('')
  const [modoMobile, setModoMobile] = useState(false)
  const [ordenacao, setOrdenacao] = useState({ campo: null, direcao: 'asc' })
  const [contadores, setContadores] = useState({
    abertas: 0,
    atrasadas: 0,
    concluidas: 0,
    total: 0,
  })

  // Função para combinar estilos baseado no modo
  const getStyles = () => {
    return {
      ...commonStyles,
      ...(modoMobile ? mobileStyles : desktopStyles),
    }
  }

  const styles = getStyles()

  const getStatusText = (status) => {
    const option = STATUS_OPTIONS.find((opt) => opt.value === status)
    return option ? option.label : '-'
  }

  const calcularContadores = (ordensData) => {
    const hoje = new Date()

    const abertas = ordensData.filter((o) => o.orde_stat_orde === 0).length
    const concluidas = ordensData.filter((o) => o.orde_stat_orde === 4).length
    const atrasadas = ordensData.filter((o) => o.orde_stat_orde === 21).length

    return { abertas, atrasadas, concluidas, total: ordensData.length }
  }

  const debouncedSetSearchValue = useCallback(
    debounce((val) => {
      setSearchValue(val)
    }, 600),
    []
  )

  const fetchOrdens = async (filtros = {}) => {
    setLoading(true)
    try {
      const params = new URLSearchParams()

      // Usar cliente_nome para busca específica por nome do cliente
      if (filtros.cliente_nome || searchValue) {
        params.append('cliente_nome', filtros.cliente_nome || searchValue)
      }

      const queryString = params.toString()
      const url = `ordemdeservico/ordens/${queryString ? `?${queryString}` : ''}`

      console.log('🔍 FRONTEND - URL da requisição:', url)
      console.log('🔍 FRONTEND - Filtros aplicados:', { cliente_nome: filtros.cliente_nome || searchValue })

      const response = await apiGetComContextoos(url)

      console.log('📡 FRONTEND - Status da resposta:', response?.status || 'N/A')
      console.log('📡 FRONTEND - Response completa:', response)

      // Processar diferentes estruturas de resposta
      let ordensData = []

      if (Array.isArray(response)) {
        ordensData = response
      } else if (response && response.data && Array.isArray(response.data)) {
        ordensData = response.data
      } else if (response && response.results && Array.isArray(response.results)) {
        ordensData = response.results
      } else if (response && typeof response === 'object') {
        const possibleArrays = Object.values(response).filter(Array.isArray)
        if (possibleArrays.length > 0) {
          ordensData = possibleArrays[0]
        }
      }

      console.log('📊 FRONTEND - Total de registros recebidos:', ordensData.length)
      console.log('📊 FRONTEND - Primeiros 3 registros:', ordensData.slice(0, 3))

      setOrdens(ordensData)
      setContadores(calcularContadores(ordensData))

      console.log('💾 FRONTEND - Dados salvos no estado:', ordensData.length, 'registros')
    } catch (error) {
      console.error('❌ FRONTEND - Erro ao buscar ordens:', error)
      setOrdens([])
    } finally {
      setLoading(false)
    }
  }

  const ordensFiltradasLocalmente = useMemo(() => {
    let ordensFiltradasLocalmente = [...ordens]

    // Filtro por status - converter string para number se necessário
    if (filtroStatus !== null && filtroStatus !== 'Todas') {
      const statusNumerico =
        typeof filtroStatus === 'string'
          ? parseInt(filtroStatus, 10)
          : filtroStatus
      ordensFiltradasLocalmente = ordensFiltradasLocalmente.filter(
        (ordem) => ordem.orde_stat_orde === statusNumerico
      )
    }

    // Filtro por prioridade - manter como string
    if (filtroPrioridade !== null) {
      ordensFiltradasLocalmente = ordensFiltradasLocalmente.filter(
        (ordem) => ordem.orde_prio === filtroPrioridade
      )
    }

    // Filtro por cliente agora é feito no backend, não precisa filtrar localmente

    // Ordenação
    if (ordenacao.campo) {
      ordensFiltradasLocalmente.sort((a, b) => {
        let valorA, valorB

        switch (ordenacao.campo) {
          case 'os':
            valorA = a.orde_nume
            valorB = b.orde_nume
            break
          case 'cliente':
            valorA = a.cliente_nome || ''
            valorB = b.cliente_nome || ''
            break
          case 'status':
            valorA = getStatusText(a.orde_stat_orde)
            valorB = getStatusText(b.orde_stat_orde)
            break
          case 'setor':
            valorA = a.setor_nome || a.orde_seto || ''
            valorB = b.setor_nome || b.orde_seto || ''
            break
          default:
            return 0
        }

        if (typeof valorA === 'string' && typeof valorB === 'string') {
          valorA = valorA.toLowerCase()
          valorB = valorB.toLowerCase()
        }

        if (valorA < valorB) return ordenacao.direcao === 'asc' ? -1 : 1
        if (valorA > valorB) return ordenacao.direcao === 'asc' ? 1 : -1
        return 0
      })
    }

    return ordensFiltradasLocalmente
  }, [ordens, filtroStatus, filtroPrioridade, ordenacao])

  useEffect(() => {
    fetchOrdens()
  }, [])

  useEffect(() => {
    setContadores(calcularContadores(ordens))
  }, [ordens])

  useEffect(() => {
    if (searchValue) {
      fetchOrdens({ cliente_nome: searchValue })
    } else {
      fetchOrdens()
    }
  }, [searchValue])

  const handleOrdenacao = (campo) => {
    if (ordenacao.campo === campo) {
      // Se já está ordenando por este campo, inverte a direção
      setOrdenacao({
        campo,
        direcao: ordenacao.direcao === 'asc' ? 'desc' : 'asc',
      })
    } else {
      // Se é um novo campo, ordena em ordem crescente
      setOrdenacao({
        campo,
        direcao: 'asc',
      })
    }
  }

  const renderTableHeader = () => (
    <View style={styles.tableHeader}>
      <TouchableOpacity
        style={[
          styles.tableHeaderButton,
          modoMobile ? styles.colOSMobile : styles.colOS,
        ]}
        onPress={() => modoMobile && handleOrdenacao('os')}>
        <Text style={styles.tableHeaderText}>OS</Text>
        {modoMobile && ordenacao.campo === 'os' && (
          <Ionicons
            name={ordenacao.direcao === 'asc' ? 'chevron-up' : 'chevron-down'}
            size={12}
            color="#fff"
          />
        )}
      </TouchableOpacity>

      <TouchableOpacity
        style={[
          styles.tableHeaderButton,
          modoMobile ? styles.colClienteMobile : styles.colCliente,
        ]}
        onPress={() => modoMobile && handleOrdenacao('cliente')}>
        <Text style={styles.tableHeaderText}>Cliente</Text>
        {modoMobile && ordenacao.campo === 'cliente' && (
          <Ionicons
            name={ordenacao.direcao === 'asc' ? 'chevron-up' : 'chevron-down'}
            size={12}
            color="#fff"
          />
        )}
      </TouchableOpacity>

      <TouchableOpacity
        style={[
          styles.tableHeaderButton,
          modoMobile ? styles.colStatusMobile : styles.colStatus,
        ]}
        onPress={() => modoMobile && handleOrdenacao('status')}>
        <Text style={styles.tableHeaderText}>Status</Text>
        {modoMobile && ordenacao.campo === 'status' && (
          <Ionicons
            name={ordenacao.direcao === 'asc' ? 'chevron-up' : 'chevron-down'}
            size={12}
            color="#fff"
          />
        )}
      </TouchableOpacity>

      <TouchableOpacity
        style={[
          styles.tableHeaderButton,
          modoMobile ? styles.colSetorMobile : styles.colPrioridade,
        ]}
        onPress={() => modoMobile && handleOrdenacao('setor')}>
        <Text style={styles.tableHeaderText}>
          {modoMobile ? 'Setor' : 'Prioridade'}
        </Text>
        {modoMobile && ordenacao.campo === 'setor' && (
          <Ionicons
            name={ordenacao.direcao === 'asc' ? 'chevron-up' : 'chevron-down'}
            size={12}
            color="#fff"
          />
        )}
      </TouchableOpacity>

      {!modoMobile && (
        <Text style={[styles.tableHeaderText, styles.colSetor]}>Setor</Text>
      )}
      {!modoMobile && (
        <Text style={[styles.tableHeaderText, styles.colData]}>Data</Text>
      )}
      {!modoMobile && (
        <Text style={[styles.tableHeaderText, styles.colProblema]}>
          Problema
        </Text>
      )}
    </View>
  )

  const renderTableRow = ({ item }) => (
    <TouchableOpacity
      style={[
        styles.tableRow,
        {
          backgroundColor: statusColors[item.orde_stat_orde] || '#fff',
          borderLeftColor: prioridadeColors[item.orde_prio] || '#aaa',
        },
      ]}
      activeOpacity={0.7}
      onPress={() => navigation.navigate('OrdemDetalhe', { ordem: item })}>
      <Text
        style={[
          styles.tableCellText,
          modoMobile ? styles.colOSMobile : styles.colOS,
          styles.osNumber,
        ]}>
        #{item.orde_nume}
      </Text>

      <Text
        style={[
          styles.tableCellText,
          modoMobile ? styles.colClienteMobile : styles.colCliente,
        ]}
        numberOfLines={2}>
        {item.cliente_nome || 'Cliente não informado'}
      </Text>

      <Text
        style={[
          styles.tableCellText,
          modoMobile ? styles.colStatusMobile : styles.colStatus,
        ]}
        numberOfLines={1}>
        {getStatusText(item.orde_stat_orde)}
      </Text>

      {modoMobile ? (
        <Text
          style={[styles.tableCellText, styles.colSetorMobile]}
          numberOfLines={1}>
          {item.setor_nome || item.orde_seto || '-'}
        </Text>
      ) : (
        <View style={[styles.colPrioridade, styles.prioridadeCellContainer]}>
          <View
            style={[
              styles.prioridadeBadge,
              { backgroundColor: prioridadeColors[item.orde_prio] || '#aaa' },
            ]}>
            <Text style={styles.prioridadeBadgeText}>
              {item.orde_prio === 'normal'
                ? 'Normal'
                : item.orde_prio === 'alerta'
                ? 'Alerta'
                : item.orde_prio === 'urgente'
                ? 'Urgente'
                : '-'}
            </Text>
          </View>
        </View>
      )}
      {!modoMobile && (
        <Text style={[styles.tableCellText, styles.colSetor]} numberOfLines={1}>
          {item.setor_nome || item.orde_seto || '-'}
        </Text>
      )}

      {!modoMobile && (
        <Text style={[styles.tableCellText, styles.colData]}>
          {item.orde_data_aber || '-'}
        </Text>
      )}

      {!modoMobile && (
        <Text
          style={[styles.tableCellText, styles.colProblema]}
          numberOfLines={2}>
          {item.orde_prob || 'Sem descrição do problema'}
        </Text>
      )}
    </TouchableOpacity>
  )

  const renderItem = ({ item }) => (
    <TouchableOpacity
      style={[
        styles.card,
        {
          backgroundColor: statusColors[item.orde_stat_orde] || '#eee',
          borderLeftColor: prioridadeColors[item.orde_prio] || '#aaa',
        },
      ]}
      activeOpacity={0.7}
      onPress={() => navigation.navigate('OrdemDetalhe', { ordem: item })}>
      <View style={styles.cardHeader}>
        <View style={styles.numeroContainer}>
          <Text style={styles.numeroLabel}>OS</Text>
          <Text style={styles.numero}>#{item.orde_nume}</Text>
        </View>
        <View
          style={[
            styles.prioridadeContainer,
            { backgroundColor: prioridadeColors[item.orde_prio] || '#aaa' },
          ]}>
          <Text style={styles.prioridade}>
            {item.orde_prio === 'normal'
              ? 'Normal'
              : item.orde_prio === 'alerta'
              ? 'Alerta'
              : item.orde_prio === 'urgente'
              ? 'Urgente'
              : '-'}
          </Text>
        </View>
      </View>

      <View style={styles.cardBody}>
        <Text style={styles.clienteNome} numberOfLines={1}>
          {item.cliente_nome || 'Cliente não informado'}
        </Text>

        <View style={styles.infoRow}>
          <View style={styles.statusContainer}>
            <Text style={styles.statusLabel}>Status:</Text>
            <Text style={styles.status}>
              {getStatusText(item.orde_stat_orde)}
            </Text>
          </View>
          <Text style={styles.data}>{item.orde_data_aber || '-'}</Text>
        </View>

        <View style={styles.setorRow}>
          <Text style={styles.setorLabel}>Setor: </Text>
          <Text style={styles.setor} numberOfLines={1}>
            {item.setor_nome || item.orde_seto || '-'}
          </Text>
        </View>

        <Text style={styles.problema} numberOfLines={2}>
          {item.orde_prob || 'Sem descrição do problema'}
        </Text>
      </View>
    </TouchableOpacity>
  )

  const renderIndicador = (label, valor, bgColor) => (
    <View
      style={[
        modoMobile ? styles.indicadorMobile : styles.indicador,
        { backgroundColor: bgColor },
      ]}>
      <Text
        style={
          modoMobile ? styles.indicadorLabelMobile : styles.indicadorLabel
        }>
        {label}
      </Text>
      <Text
        style={
          modoMobile ? styles.indicadorValorMobile : styles.indicadorValor
        }>
        {valor}
      </Text>
    </View>
  )

  return (
    <View style={modoMobile ? styles.containerMobile : styles.container}>
      {/* Header com Logo e Refresh */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}></Text>
        <View style={styles.headerRight}>
          <Image
            source={require('../assets/eletro.png')}
            style={modoMobile ? styles.logoMobile : styles.logo}
          />

          {/* Botão para alternar modo */}
          <TouchableOpacity
            style={styles.modeButton}
            onPress={() => setModoMobile(!modoMobile)}
            activeOpacity={0.7}>
            <Ionicons
              name={modoMobile ? 'tv' : 'phone-portrait'}
              size={20}
              color="#fff"
            />
            <Text style={styles.modeButtonText}>
              {modoMobile ? 'TV' : 'Mobile'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.refreshButton}
            onPress={fetchOrdens}
            activeOpacity={0.7}>
            <Ionicons name="refresh" size={20} color="#fff" />
          </TouchableOpacity>
        </View>
      </View>

      <View style={modoMobile ? styles.indicadoresMobile : styles.indicadores}>
        {renderIndicador('Abertas', contadores.abertas, '#d1ecf1')}
        {renderIndicador('Atrasadas', contadores.atrasadas, '#f8d7da')}
        {renderIndicador('Concluídas', contadores.concluidas, '#d4edda')}
        {renderIndicador('Total', contadores.total, '#eee')}
        <TouchableOpacity
          style={modoMobile ? styles.botaoCriarMobile : styles.botaoCriar}
          activeOpacity={0.7}
          onPress={() => navigation.navigate('OsCriacao')}>
          <Ionicons name="add-circle" size={20} color="#fff" />
          <Text
            style={
              modoMobile ? styles.botaoCriarTextMobile : styles.botaoCriarTexto
            }>
            Nova O.S.
          </Text>
        </TouchableOpacity>
      </View>

      <View style={modoMobile ? styles.filtrosMobile : styles.filtros}>
        <View style={styles.filtroSection}>
          <Text style={styles.filtroLabel}>Status</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.filtroScroll}>
            {STATUS_OPTIONS.map(({ label, value }) => (
              <TouchableOpacity
                key={label}
                style={[
                  modoMobile ? styles.filtroButtonMobile : styles.filtroButton,
                  {
                    backgroundColor:
                      value !== null
                        ? statusColors[value] || '#f0f0f0'
                        : '#f0f0f0',
                    borderColor:
                      filtroStatus === value ? '#284665' : 'transparent',
                    borderWidth: filtroStatus === value ? 3 : 1,
                  },
                ]}
                onPress={() => setFiltroStatus(value)}
                activeOpacity={0.7}>
                <Text
                  style={[
                    modoMobile
                      ? styles.filtroButtonTextMobile
                      : styles.filtroButtonText,
                    { fontWeight: filtroStatus === value ? 'bold' : 'normal' },
                  ]}>
                  {label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        <View style={styles.filtroSection}>
          <Text style={styles.filtroLabel}>Prioridade</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.filtroScroll}>
            {PRIORIDADE_OPTIONS.map(({ label, value }) => (
              <TouchableOpacity
                key={label}
                style={[
                  modoMobile ? styles.filtroButtonMobile : styles.filtroButton,
                  {
                    backgroundColor:
                      value !== null
                        ? prioridadeColors[value] || '#f0f0f0'
                        : '#f0f0f0',
                    borderColor:
                      filtroPrioridade === value ? '#284665' : 'transparent',
                    borderWidth: filtroPrioridade === value ? 3 : 1,
                  },
                ]}
                onPress={() => setFiltroPrioridade(value)}
                activeOpacity={0.7}>
                <Text
                  style={[
                    modoMobile
                      ? styles.filtroButtonTextMobile
                      : styles.filtroButtonText,
                    {
                      fontWeight:
                        filtroPrioridade === value ? 'bold' : 'normal',
                      color: value === 'urgente' ? '#fff' : '#333',
                    },
                  ]}>
                  {label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
        <Text style={modoMobile ? styles.filtrosMobile : styles.titulo}>
          Filtragem por Cliente
        </Text>
        <View style={styles.searchContainer}>
          <TextInput
            placeholder="Buscar por nome do cliente..."
            placeholderTextColor="#777"
            style={styles.input}
            value={searchTerm}
            onChangeText={(text) => {
              setSearchTerm(text)
              debouncedSetSearchValue(text)
            }}
            returnKeyType="search"
            onSubmitEditing={() => setSearchValue(searchTerm)}
          />
          <TouchableOpacity
            style={styles.searchButton}
            onPress={() => setSearchValue(searchTerm)}>
            <Text style={styles.searchButtonText}>Buscar</Text>
          </TouchableOpacity>
        </View>
      </View>
      <View></View>
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#284665" />
          <Text style={styles.loadingText}>Carregando ordens...</Text>
        </View>
      ) : (
        <View style={styles.tableContainer}>
          {renderTableHeader()}
          <ScrollView
            style={styles.tableScrollView}
            showsVerticalScrollIndicator={false}>
            {ordensFiltradasLocalmente.length === 0 ? (
              <View style={styles.emptyContainer}>
                <Text style={styles.emptyText}>Nenhuma ordem encontrada</Text>
              </View>
            ) : (
              ordensFiltradasLocalmente.map((item, index) => (
                <View
                  key={`${item.orde_empr || 'emp'}-${item.orde_fili || 'fil'}-${
                    item.orde_nume || 'num'
                  }-${item.cliente_codigo || 'cli'}-${index}`}>
                  {renderTableRow({ item })}
                </View>
              ))
            )}
          </ScrollView>
        </View>
      )}
    </View>
  )
}

export default PainelAcompanhamento
