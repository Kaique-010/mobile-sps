import React, { useEffect, useState } from 'react'
import {
  View,
  Text,
  FlatList,
  Switch,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
} from 'react-native'
import { apiGetComContexto, apiPatchComContexto } from '../../utils/api'
import AsyncStorage from '@react-native-async-storage/async-storage'

const ParametrosFinanceiro = () => {
  const [modulos, setModulos] = useState([])
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    buscarModulos()
  }, [])

  const buscarModulos = async () => {
    try {
      const data = await apiGetComContexto(
        'parametros-admin/atualizapermissoes/'
      )
      setModulos(data)
    } catch (error) {
      console.error('Erro ao buscar módulos:', error)
    } finally {
      setLoading(false)
    }
  }

  const alternarModulo = (nome) => {
    setModulos((prev) =>
      prev.map((mod) =>
        mod.nome === nome ? { ...mod, ativo: !mod.ativo } : mod
      )
    )
  }

  const salvarPermissoes = async () => {
    setSalvando(true)
    try {
      const usuario = await AsyncStorage.getItem('usuario_id')

      const payload = {
        usuario,
        modulos: modulos.map(({ nome, ativo }) => ({ nome, ativo })),
      }

      await apiPatchComContexto('parametros-admin/atualizapermissoes/', payload)
      Alert.alert('Sucesso', 'Permissões salvas com sucesso!')
    } catch (error) {
      console.error('Erro ao salvar permissões:', error)
      Alert.alert('Erro', 'Erro ao salvar permissões.')
    } finally {
      setSalvando(false)
    }
  }

  const renderItem = ({ item }) => (
    <View
      style={{
        backgroundColor: '#2f3e52',
        padding: 15,
        marginBottom: 10,
        borderRadius: 10,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.3,
        shadowRadius: 3,
        elevation: 4,
      }}>
      <Text style={{ color: '#fff', fontSize: 16, fontWeight: '600' }}>
        {item.nome}
      </Text>
      <Switch
        value={item.ativo}
        onValueChange={() => alternarModulo(item.nome)}
        trackColor={{ false: '#777', true: '#34d399' }}
        thumbColor={item.ativo ? '#22c55e' : '#ccc'}
      />
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
    <View style={{ flex: 1, padding: 16, backgroundColor: '#243242' }}>
      <FlatList
        data={modulos}
        keyExtractor={(item) => item.nome}
        renderItem={renderItem}
        contentContainerStyle={{ paddingBottom: 30 }}
      />

      <TouchableOpacity
        onPress={salvarPermissoes}
        style={{
          backgroundColor: salvando ? '#555' : '#0ea5e9',
          padding: 15,
          borderRadius: 8,
          marginTop: 20,
        }}
        disabled={salvando}>
        <Text
          style={{
            color: '#fff',
            textAlign: 'center',
            fontWeight: 'bold',
            fontSize: 16,
          }}>
          {salvando ? 'Salvando...' : 'Salvar Permissões'}
        </Text>
      </TouchableOpacity>
    </View>
  )
}

export default ParametrosFinanceiro
