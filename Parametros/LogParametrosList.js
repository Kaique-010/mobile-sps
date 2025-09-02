import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  FlatList,
  RefreshControl,
  TextInput,
  ActivityIndicator,
} from 'react-native'
import { Feather } from '@expo/vector-icons'
import { getLogsParametros } from '../services/parametrosService'

const LogParametrosList = () => {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [filteredLogs, setFilteredLogs] = useState([])

  useEffect(() => {
    loadLogs()
  }, [])

  useEffect(() => {
    filterLogs()
  }, [logs, searchText])

  const loadLogs = async () => {
    try {
      setLoading(true)
      const response = await getLogsParametros({ ordering: '-data_alteracao' })

      let logs = []
      if (response?.data?.results) logs = response.data.results
      else if (Array.isArray(response?.data)) logs = response.data

      setLogs(logs)
    } catch (error) {
      console.error('Erro ao carregar logs:', error)
      setLogs([])
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const filterLogs = () => {
    if (!searchText.trim()) return setFilteredLogs(logs)

    const texto = searchText.toLowerCase()
    const filtered = logs.filter(
      (log) =>
        log.parametro_nome?.toLowerCase().includes(texto) ||
        log.usuario_nome?.toLowerCase().includes(texto) ||
        log.acao?.toLowerCase().includes(texto)
    )
    setFilteredLogs(filtered)
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleString('pt-BR')
  }

  const getActionColor = (action) => {
    switch (action?.toLowerCase()) {
      case 'criacao':
        return '#22c55e'
      case 'edicao':
        return '#facc15'
      case 'exclusao':
        return '#ef4444'
      default:
        return '#3b82f6'
    }
  }

  const renderLogItem = ({ item }) => (
    <View
      style={{
        backgroundColor: '#2f3e52',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
      }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
        <Text style={{ color: '#fff', fontSize: 16, fontWeight: 'bold' }}>
          {item.parametro_nome}
        </Text>
        <View
          style={{
            backgroundColor: getActionColor(item.acao),
            paddingHorizontal: 8,
            paddingVertical: 2,
            borderRadius: 6,
          }}>
          <Text style={{ color: '#000', fontWeight: 'bold' }}>
            {item.acao?.toUpperCase()}
          </Text>
        </View>
      </View>

      <Text style={{ color: '#aaa', marginTop: 6 }}>
        Usuário: <Text style={{ color: '#fff' }}>{item.usuario_nome}</Text>
      </Text>
      <Text style={{ color: '#aaa' }}>
        Data:{' '}
        <Text style={{ color: '#fff' }}>{formatDate(item.data_alteracao)}</Text>
      </Text>

      {item.valor_anterior && (
        <Text style={{ color: '#f87171', marginTop: 6 }}>
          ↓ Valor anterior: {item.valor_anterior}
        </Text>
      )}
      {item.valor_novo && (
        <Text style={{ color: '#4ade80' }}>
          ↑ Valor novo: {item.valor_novo}
        </Text>
      )}
      {item.observacoes && (
        <Text style={{ color: '#c084fc', marginTop: 4 }}>
          Obs: {item.observacoes}
        </Text>
      )}
    </View>
  )

  if (loading) {
    return (
      <View
        style={{
          flex: 1,
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: '#243242',
        }}>
        <ActivityIndicator size="large" color="#0ea5e9" />
      </View>
    )
  }

  return (
    <View style={{ flex: 1, backgroundColor: '#243242', padding: 16 }}>
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          backgroundColor: '#2f3e52',
          paddingHorizontal: 12,
          borderRadius: 10,
          marginBottom: 16,
        }}>
        <Feather name="search" size={20} color="#aaa" />
        <TextInput
          style={{
            flex: 1,
            marginLeft: 8,
            color: '#fff',
            height: 40,
          }}
          placeholder="Buscar logs..."
          placeholderTextColor="#888"
          value={searchText}
          onChangeText={setSearchText}
        />
      </View>

      <FlatList
        data={filteredLogs}
        keyExtractor={(item) => item.id.toString()}
        renderItem={renderLogItem}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={loadLogs}
            tintColor="#fff"
          />
        }
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={{ alignItems: 'center', marginTop: 60 }}>
            <Feather name="file-text" size={48} color="#666" />
            <Text style={{ color: '#999', marginTop: 8 }}>
              {searchText ? 'Nenhum log encontrado' : 'Nenhum log disponível'}
            </Text>
          </View>
        }
      />
    </View>
  )
}

export default LogParametrosList
