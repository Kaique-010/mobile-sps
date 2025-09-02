import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
  Switch,
  ActivityIndicator,
  Picker,
} from 'react-native'
import { Feather } from '@expo/vector-icons'
import {
  getModulosLiberados,
  getPermissoesUsuario,
  updatePermissaoModulo,
  sincronizarLicenca,
  getConfiguracaoCompleta,
} from '../services/parametrosService'
import { getStoredData } from '../services/storageService'
import { parametrosStyles } from './styles/parametrosStyles'

const SistemaPermissoes = ({ navigation }) => {
  const [empresasFiliais, setEmpresasFiliais] = useState([])
  const [empresaSelecionada, setEmpresaSelecionada] = useState(null)
  const [filialSelecionada, setFilialSelecionada] = useState(null)
  const [modulos, setModulos] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    carregarDados()
  }, [])

  useEffect(() => {
    if (empresaSelecionada && filialSelecionada) {
      carregarModulosEmpresa()
    }
  }, [empresaSelecionada, filialSelecionada])

  const carregarDados = async () => {
    try {
      setLoading(true)

      // Carregar empresas/filiais do usuário
      const response = await getModulosLiberados()
      setEmpresasFiliais(response)

      // Selecionar primeira empresa/filial por padrão
      if (response.length > 0) {
        setEmpresaSelecionada(response[0].empresa_id)
        setFilialSelecionada(response[0].filial_id)
      }
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
      Alert.alert('Erro', 'Falha ao carregar dados')
    } finally {
      setLoading(false)
    }
  }

  const carregarModulosEmpresa = async () => {
    try {
      const empresaFilial = empresasFiliais.find(
        (ef) =>
          ef.empresa_id === empresaSelecionada &&
          ef.filial_id === filialSelecionada
      )

      if (empresaFilial) {
        setModulos(empresaFilial.modulos)
      }
    } catch (error) {
      console.error('Erro ao carregar módulos:', error)
    }
  }

  const alternarModulo = async (moduloCodigo) => {
    try {
      const modulosAtualizados = modulos.map((mod) =>
        mod.codigo === moduloCodigo ? { ...mod, ativo: !mod.ativo } : mod
      )

      setModulos(modulosAtualizados)

      // Salvar no backend
      await updatePermissaoModulo({
        empresa_id: empresaSelecionada,
        filial_id: filialSelecionada,
        modulos: modulosAtualizados,
      })
    } catch (error) {
      console.error('Erro ao atualizar módulo:', error)
      Alert.alert('Erro', 'Falha ao atualizar permissão')
      // Reverter mudança em caso de erro
      carregarModulosEmpresa()
    }
  }

  const renderSeletorEmpresa = () => {
    const empresasUnicas = [
      ...new Set(empresasFiliais.map((ef) => ef.empresa_id)),
    ].map((empresaId) => {
      const empresa = empresasFiliais.find((ef) => ef.empresa_id === empresaId)
      return { id: empresa.empresa_id, nome: empresa.empresa_nome }
    })

    return (
      <View style={parametrosStyles.selectorContainer}>
        <Text style={parametrosStyles.selectorLabel}>Empresa:</Text>
        <Picker
          selectedValue={empresaSelecionada}
          onValueChange={(value) => {
            setEmpresaSelecionada(value)
            // Reset filial quando empresa muda
            const filiaisEmpresa = empresasFiliais.filter(
              (ef) => ef.empresa_id === value
            )
            if (filiaisEmpresa.length > 0) {
              setFilialSelecionada(filiaisEmpresa[0].filial_id)
            }
          }}
          style={parametrosStyles.picker}>
          {empresasUnicas.map((empresa) => (
            <Picker.Item
              key={empresa.id}
              label={empresa.nome}
              value={empresa.id}
            />
          ))}
        </Picker>
      </View>
    )
  }

  const renderSeletorFilial = () => {
    const filiaisEmpresa = empresasFiliais.filter(
      (ef) => ef.empresa_id === empresaSelecionada
    )

    return (
      <View style={parametrosStyles.selectorContainer}>
        <Text style={parametrosStyles.selectorLabel}>Filial:</Text>
        <Picker
          selectedValue={filialSelecionada}
          onValueChange={setFilialSelecionada}
          style={parametrosStyles.picker}>
          {filiaisEmpresa.map((filial) => (
            <Picker.Item
              key={filial.filial_id}
              label={filial.filial_nome}
              value={filial.filial_id}
            />
          ))}
        </Picker>
      </View>
    )
  }

  if (loading) {
    return (
      <View style={parametrosStyles.loadingContainer}>
        <ActivityIndicator size="large" color="#007bff" />
        <Text style={parametrosStyles.loadingText}>
          Carregando permissões...
        </Text>
      </View>
    )
  }

  return (
    <View style={parametrosStyles.container}>
      <View style={parametrosStyles.header}>
        <Text style={parametrosStyles.headerTitle}>Sistema de Permissões</Text>
        <Text style={parametrosStyles.headerSubtitle}>
          Gerencie módulos por empresa e filial
        </Text>
      </View>

      {renderSeletorEmpresa()}
      {renderSeletorFilial()}

      <ScrollView
        style={parametrosStyles.modulosContainer}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={carregarDados} />
        }>
        {modulos.map((modulo) => (
          <View key={modulo.codigo} style={parametrosStyles.moduloCard}>
            <View style={parametrosStyles.moduloInfo}>
              <Text style={parametrosStyles.moduloNome}>{modulo.nome}</Text>
              <Text style={parametrosStyles.moduloDesc}>
                {modulo.descricao}
              </Text>
            </View>
            <Switch
              value={modulo.ativo}
              onValueChange={() => alternarModulo(modulo.codigo)}
              trackColor={{ false: '#767577', true: '#81b0ff' }}
              thumbColor={modulo.ativo ? '#007bff' : '#f4f3f4'}
            />
          </View>
        ))}
      </ScrollView>
    </View>
  )
}

export default SistemaPermissoes
