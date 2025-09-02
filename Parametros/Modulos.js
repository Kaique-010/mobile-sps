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
import { Picker } from '@react-native-picker/picker'
import { apiGetComContexto, apiPatchComContexto } from '../utils/api'
import AsyncStorage from '@react-native-async-storage/async-storage'

const PermissoesModulos = () => {
  const [modulos, setModulos] = useState([])
  const [empresas, setEmpresas] = useState([])
  const [filiais, setFiliais] = useState([])
  const [empresaSelecionada, setEmpresaSelecionada] = useState('')
  const [filialSelecionada, setFilialSelecionada] = useState('')
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    buscarEmpresas()
  }, [])

  useEffect(() => {
    if (empresaSelecionada) {
      buscarFiliais(empresaSelecionada)
    }
  }, [empresaSelecionada])

  useEffect(() => {
    if (empresaSelecionada && filialSelecionada) {
      buscarModulos()
    }
  }, [empresaSelecionada, filialSelecionada])

  const buscarEmpresas = async () => {
    try {
      const data = await apiGetComContexto('licencas/empresas/')
      setEmpresas(data)
      if (data.length > 0) {
        setEmpresaSelecionada(data[0].empr_codi.toString())
      }
    } catch (error) {
      console.error('Erro ao buscar empresas:', error)
      Alert.alert('Erro', 'Erro ao carregar empresas')
    }
  }

  const buscarFiliais = async (empresaId) => {
    try {
      const data = await apiGetComContexto(
        `licencas/filiais/?empresa_id=${empresaId}`
      )
      setFiliais(data)
      if (data.length > 0) {
        const primeiraFilial = data[0]
        
        // Lógica robusta: tenta as três propriedades na ordem de prioridade
        const filialId = 
          primeiraFilial.fili_codi ||     // ✅ Propriedade correta (prioridade 1)
          primeiraFilial.empr_empr ||     // ✅ Espelho da empresa (prioridade 2)
          primeiraFilial.filial_id ||     // ✅ Alternativa (prioridade 3)
          primeiraFilial.id               // ✅ Fallback final
        
        if (filialId) {
          setFilialSelecionada(filialId.toString())
          console.log('🏢 [DEBUG] Filial selecionada:', filialId)
        } else {
          console.warn('⚠️ [DEBUG] Nenhuma propriedade de filial encontrada:', primeiraFilial)
        }
      }
    } catch (error) {
      console.error('Erro ao buscar filiais:', error)
      Alert.alert('Erro', 'Erro ao carregar filiais')
    }
  }

  const buscarModulos = async () => {
    try {
      setLoading(true)
      console.log('🔍 [DEBUG] Buscando módulos para:', {
        empresa: empresaSelecionada,
        filial: filialSelecionada,
      })

      if (!empresaSelecionada || !filialSelecionada) {
        console.log('❌ [DEBUG] Empresa ou filial não selecionada')
        setModulos([])
        return
      }

      const data = await apiGetComContexto(
        `parametros-admin/atualizapermissoes/?empresa_id=${empresaSelecionada}&filial_id=${filialSelecionada}`
      )

      console.log('✅ [DEBUG] Módulos recebidos:', data)
      setModulos(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Erro ao buscar módulos:', error)
      setModulos([])
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
    if (!empresaSelecionada || !filialSelecionada) {
      Alert.alert('Atenção', 'Selecione empresa e filial')
      return
    }

    setSalvando(true)
    try {
      const usuario = await AsyncStorage.getItem('usuario_id')

      const payload = {
        usuario,
        empresa_id: empresaSelecionada,
        filial_id: filialSelecionada,
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

  return (
    <View style={{ flex: 1, padding: 16, backgroundColor: '#243242' }}>
      {/* Seleção de Empresa */}
      <View style={{ marginBottom: 15 }}>
        <Text style={{ color: '#fff', fontSize: 16, marginBottom: 8 }}>
          Empresa:
        </Text>
        <View style={{ backgroundColor: '#2f3e52', borderRadius: 8 }}>
          <Picker
            selectedValue={empresaSelecionada}
            onValueChange={setEmpresaSelecionada}
            style={{ color: '#fff' }}
            dropdownIconColor="#fff">
            {empresas.map((empresa, index) => (
              <Picker.Item
                key={empresa.empr_codi || `empresa-${index}`}
                label={empresa.empr_nome}
                value={(empresa.empr_codi || index).toString()}
              />
            ))}
          </Picker>
        </View>
      </View>

      {/* Seleção de Filial */}
      <View style={{ marginBottom: 20 }}>
        <Text style={{ color: '#fff', fontSize: 16, marginBottom: 8 }}>
          Filial:
        </Text>
        <View style={{ backgroundColor: '#2f3e52', borderRadius: 8 }}>
          <Picker
            selectedValue={filialSelecionada}
            onValueChange={setFilialSelecionada}
            style={{ color: '#fff' }}
            dropdownIconColor="#fff">
            {filiais.map((filial, index) => (
              <Picker.Item
                key={
                  filial.filial_id ||
                  filial.empr_empr ||
                  filial.id ||
                  `filial-${index}`
                }
                label={filial.filial_nome || filial.empr_nome}
                value={
                  (
                    filial.filial_id ||
                    filial.empr_empr ||
                    filial.id
                  )?.toString() || index.toString()
                }
              />
            ))}
          </Picker>
        </View>
      </View>

      {loading ? (
        <View
          style={{
            flex: 1,
            justifyContent: 'center',
            alignItems: 'center',
          }}>
          <ActivityIndicator size="large" color="#0ea5e9" />
          <Text style={{ color: '#fff', marginTop: 10 }}>
            Carregando módulos...
          </Text>
        </View>
      ) : (
        <>
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
        </>
      )}
    </View>
  )
}

export default PermissoesModulos
