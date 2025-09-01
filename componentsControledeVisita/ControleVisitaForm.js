import React, { useState, useEffect, useRef } from 'react'
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Animated,
  Dimensions,
} from 'react-native'
import { MaterialIcons, Feather, Ionicons } from '@expo/vector-icons'
import DateTimePicker from '@react-native-community/datetimepicker'
import {
  apiGetComContexto,
  apiPostComContexto,
  apiPutComContexto,
  addContextoControleVisita,
} from '../utils/api'
import useContextoApp from '../hooks/useContextoApp'
import Toast from 'react-native-toast-message'

// Importar componentes das abas
import AbaDadosBasicos from './AbaDadosBasicos'
import AbaContato from './AbaContato'
import AbaAtividades from './AbaAtividades'
import AbaExtras from './AbaExtras'
import AbaItens from './AbaItens'

const { width } = Dimensions.get('window')

export default function ControleVisitaForm({ route, navigation }) {
  const { visitaId, mode = 'create', cliente, vendedor } = route.params || {}
  const isEdit = mode === 'edit' && visitaId

  // Adicionar estado para visitaId
  const [currentVisitaId, setCurrentVisitaId] = useState(visitaId)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState(0)
  const [showDatePicker, setShowDatePicker] = useState({
    field: null,
    show: false,
  })

  const scrollX = useRef(new Animated.Value(0)).current
  const scrollViewRef = useRef(null)

  const { empresaId, filialId } = useContextoApp()

  const [formData, setFormData] = useState({
    ctrl_empresa: empresaId,
    ctrl_filial: filialId,
    ctrl_numero: null,
    ctrl_cliente: '',
    ctrl_data: new Date().toISOString().split('T')[0],
    ctrl_vendedor: '',
    ctrl_etapa: 1,
    ctrl_contato: '',
    ctrl_fone: '',
    ctrl_obse: '',
    ctrl_km_inic: '',
    ctrl_km_fina: '',
    ctrl_prox_visi: '',
    ctrl_novo: 0,
    ctrl_base: 0,
    ctrl_prop: 0,
    ctrl_leva: 0,
    ctrl_proj: 0,
    ctrl_nume_orca: '',
  })

  const [selectedCliente, setSelectedCliente] = useState(null)
  const [selectedVendedor, setSelectedVendedor] = useState(null)
  const [etapas, setEtapas] = useState([])

  // Configuração das abas
  // Adicionar nova aba na configuração
  const tabs = [
    {
      id: 0,
      title: 'Dados Básicos',
      icon: 'person-outline',
      color: '#3498db',
      component: AbaDadosBasicos,
    },
    {
      id: 1,
      title: 'Contato',
      icon: 'call-outline',
      color: '#9b59b6',
      component: AbaContato,
    },
    {
      id: 2,
      title: 'Atividades',
      icon: 'checkmark-circle-outline',
      color: '#e74c3c',
      component: AbaAtividades,
    },
    {
      id: 3,
      title: 'Itens',
      icon: 'list-outline',
      color: '#27ae60',
      component: AbaItens,
    },
    {
      id: 4,
      title: 'Extras',
      icon: 'settings-outline',
      color: '#f39c12',
      component: AbaExtras,
    },
  ]

  useEffect(() => {
    carregarEtapas()
    if (isEdit) {
      carregarVisita()
    }
  }, [isEdit, visitaId])

  const carregarEtapas = async () => {
    try {
      const response = await apiGetComContexto(
        'controledevisitas/etapas-visita/'
      )
      const etapasData = response?.results || response || []
      setEtapas(Array.isArray(etapasData) ? etapasData : [])
    } catch (error) {
      console.error('Erro ao carregar etapas:', error)
      setEtapas([])
    }
  }

  const carregarVisita = async () => {
    try {
      setLoading(true)
      const response = await apiGetComContexto(
        `controledevisitas/controle-visitas/${visitaId}/`
      )

      setFormData({
        ...response,
        ctrl_data: response.ctrl_data || new Date().toISOString().split('T')[0],
        ctrl_prox_visi: response.ctrl_prox_visi || '',
        ctrl_km_inic: response.ctrl_km_inic?.toString() || '',
        ctrl_km_fina: response.ctrl_km_fina?.toString() || '',
        ctrl_nume_orca: response.ctrl_nume_orca?.toString() || '',
        ctrl_numero: response.ctrl_numero || null,
        ctrl_etapa: response.ctrl_etapa || 1,
        ctrl_empresa: response.ctrl_empresa || null,
        ctrl_filial: response.ctrl_filial || null,
      })

      if (response.ctrl_cliente) {
        setSelectedCliente({
          enti_clie: response.ctrl_cliente,
          enti_nome: response.cliente_nome,
        })
      }

      if (response.ctrl_vendedor) {
        setSelectedVendedor({
          enti_clie: response.ctrl_vendedor,
          enti_nome: response.vendedor_nome,
        })
      }
    } catch (error) {
      console.error('Erro ao carregar visita:', error)
      Alert.alert('Erro', 'Não foi possível carregar os dados da visita')
      navigation.goBack()
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      if (!selectedCliente || !selectedCliente.enti_clie) {
        Alert.alert('Erro', 'Selecione um cliente')
        return
      }

      if (!selectedVendedor || !selectedVendedor.enti_clie) {
        Alert.alert('Erro', 'Selecione um vendedor')
        return
      }

      if (!formData.ctrl_etapa) {
        Alert.alert('Erro', 'Selecione uma etapa')
        return
      }

      const kmInic = parseFloat(formData.ctrl_km_inic) || 0
      const kmFina = parseFloat(formData.ctrl_km_fina) || 0

      if (kmInic > 0 && kmFina > 0 && kmFina < kmInic) {
        Alert.alert('Erro', 'KM final deve ser maior que KM inicial')
        return
      }

      setLoading(true)

      const dataToSave = {
        ...formData,
        ctrl_cliente: selectedCliente.enti_clie,
        ctrl_vendedor: selectedVendedor.enti_clie,
        ctrl_empresa: formData.ctrl_empresa
          ? parseInt(formData.ctrl_empresa)
          : null,
        ctrl_filial: formData.ctrl_filial
          ? parseInt(formData.ctrl_filial)
          : null,
        ctrl_numero: formData.ctrl_numero
          ? parseInt(formData.ctrl_numero)
          : null,
        ctrl_km_inic: formData.ctrl_km_inic
          ? parseFloat(formData.ctrl_km_inic)
          : null,
        ctrl_km_fina: formData.ctrl_km_fina
          ? parseFloat(formData.ctrl_km_fina)
          : null,
        ctrl_nume_orca: formData.ctrl_nume_orca
          ? parseInt(formData.ctrl_nume_orca)
          : null,
        ctrl_prox_visi: formData.ctrl_prox_visi || null,
      }
      
      // Incluir ctrl_id apenas em edições
      if (isEdit && formData.ctrl_id) {
        dataToSave.ctrl_id = formData.ctrl_id
      }
      if (isEdit) {
        const dataWithContext = await addContextoControleVisita(dataToSave)
        await apiPutComContexto(
          `controledevisitas/controle-visitas/${visitaId}/`,
          dataWithContext
        )
        Toast.show({
          type: 'success',
          text1: 'Sucesso',
          text2: 'Visita atualizada com sucesso',
        })
      } else {
        const dataWithContext = await addContextoControleVisita(dataToSave)
        const response = await apiPostComContexto(
          'controledevisitas/controle-visitas/',
          dataWithContext
        )
        
        // Capturar o ID da visita criada
        if (response && response.ctrl_numero) {
          setCurrentVisitaId(response.ctrl_numero)
        }
        
        Toast.show({
          type: 'success',
          text1: 'Sucesso',
          text2: 'Visita criada com sucesso',
        })
      }

      navigation.goBack()
    } catch (error) {
      console.error('Erro ao salvar visita:', error)
      Toast.show({
        type: 'error',
        text1: 'Erro',
        text2: 'Não foi possível salvar a visita',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDateChange = (event, selectedDate) => {
    setShowDatePicker({ field: null, show: false })

    if (selectedDate && showDatePicker.field) {
      const formattedDate = selectedDate.toISOString().split('T')[0]
      setFormData({
        ...formData,
        [showDatePicker.field]: formattedDate,
      })
    }
  }

  const showDatePickerModal = (field) => {
    setShowDatePicker({ field, show: true })
  }

  const formatDateForDisplay = (dateString) => {
    if (!dateString) return 'Selecionar data'
    const date = new Date(dateString + 'T00:00:00')
    return date.toLocaleDateString('pt-BR')
  }

  const handleClienteSelect = (cliente) => {
    setSelectedCliente(cliente)
    setFormData({
      ...formData,
      ctrl_cliente: cliente?.enti_clie || '',
    })
  }

  const handleVendedorSelect = (vendedor) => {
    setSelectedVendedor(vendedor)
    setFormData({
      ...formData,
      ctrl_vendedor: vendedor?.enti_clie || '',
    })
  }

  useEffect(() => {
    if (cliente && !isEdit) {
      setSelectedCliente({
        enti_clie: cliente.id,
        enti_nome: cliente.nome,
      })
      setFormData((prev) => ({
        ...prev,
        ctrl_cliente: cliente.id,
      }))
    }

    if (vendedor && !isEdit) {
      setSelectedVendedor({
        enti_clie: vendedor.id,
        enti_nome: vendedor.nome,
      })
      setFormData((prev) => ({
        ...prev,
        ctrl_vendedor: vendedor.id,
      }))
    }
  }, [cliente, vendedor, isEdit])

  const changeTab = (tabIndex) => {
    setActiveTab(tabIndex)
    scrollViewRef.current?.scrollTo({
      x: tabIndex * width,
      animated: true,
    })
  }

  const onScroll = Animated.event(
    [{ nativeEvent: { contentOffset: { x: scrollX } } }],
    {
      useNativeDriver: false,
      listener: (event) => {
        const offsetX = event.nativeEvent.contentOffset.x
        const tabIndex = Math.round(offsetX / width)
        if (tabIndex !== activeTab) {
          setActiveTab(tabIndex)
        }
      },
    }
  )

  const renderTabContent = (tab, index) => {
    const TabComponent = tab.component
    const commonProps = {
      formData,
      setFormData,
      onDatePress: showDatePickerModal,
      formatDateForDisplay,
    }

    switch (index) {
      case 0:
        return (
          <TabComponent
            {...commonProps}
            selectedCliente={selectedCliente}
            selectedVendedor={selectedVendedor}
            etapas={etapas}
            onClienteSelect={handleClienteSelect}
            onVendedorSelect={handleVendedorSelect}
          />
        )
      case 1:
        return <TabComponent {...commonProps} />
      case 2:
        return (
          <TabComponent
            {...commonProps}
            scrollX={scrollX}
            activeTab={activeTab}
            width={width}
          />
        )
      case 3:
        return (
          <TabComponent 
            {...commonProps} 
            visitaId={currentVisitaId}
            empresaId={formData.ctrl_empresa}
            filialId={formData.ctrl_filial}
          />
        )
      default:
        return null
    }
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Feather name="arrow-left" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>
          {isEdit ? 'Editar Visita' : 'Nova Visita'}
        </Text>
        <TouchableOpacity onPress={handleSave} disabled={loading}>
          <Feather name="check" size={24} color="#2ecc71" />
        </TouchableOpacity>
      </View>

      {/* Tab Navigation */}
      <View style={styles.tabNavigation}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.tabScrollContainer}>
          {tabs.map((tab, index) => {
            const isActive = activeTab === index
            return (
              <TouchableOpacity
                key={tab.id}
                style={[
                  styles.tabButton,
                  isActive && {
                    ...styles.tabButtonActive,
                    borderBottomColor: tab.color,
                  },
                ]}
                onPress={() => changeTab(index)}>
                <Animated.View
                  style={[
                    styles.tabIconContainer,
                    {
                      backgroundColor: isActive
                        ? tab.color + '20'
                        : 'transparent',
                    },
                  ]}>
                  <Ionicons
                    name={tab.icon}
                    size={20}
                    color={isActive ? tab.color : '#666'}
                  />
                </Animated.View>
                <Text
                  style={[
                    styles.tabText,
                    isActive && { color: tab.color, fontWeight: '600' },
                  ]}>
                  {tab.title}
                </Text>
              </TouchableOpacity>
            )
          })}
        </ScrollView>
      </View>

      {/* Tab Content */}
      <ScrollView
        ref={scrollViewRef}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={onScroll}
        scrollEventThrottle={16}
        style={styles.tabContentContainer}>
        {tabs.map((tab, index) => (
          <ScrollView
            key={tab.id}
            style={[styles.tabScrollView, { width }]}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.tabScrollContent}>
            {renderTabContent(tab, index)}
          </ScrollView>
        ))}
      </ScrollView>

      {/* Progress Indicator */}
      <View style={styles.progressContainer}>
        {tabs.map((tab, index) => {
          const isActive = activeTab === index
          return (
            <Animated.View
              key={tab.id}
              style={[
                styles.progressDot,
                {
                  backgroundColor: isActive ? tab.color : '#2a3441',
                  transform: [
                    {
                      scale: isActive ? 1.2 : 1,
                    },
                  ],
                },
              ]}
            />
          )
        })}
      </View>

      {/* Floating Action Button */}
      <Animated.View
        style={[
          styles.fabContainer,
          {
            transform: [
              {
                scale: scrollX.interpolate({
                  inputRange: [0, width * (tabs.length - 1)],
                  outputRange: [1, 1],
                  extrapolate: 'clamp',
                }),
              },
            ],
          },
        ]}>
        <TouchableOpacity
          style={[styles.fab, loading && styles.fabDisabled]}
          onPress={handleSave}
          disabled={loading}>
          <MaterialIcons
            name={loading ? 'hourglass-empty' : 'save'}
            size={24}
            color="#fff"
          />
        </TouchableOpacity>
      </Animated.View>

      {/* Date Picker Modal */}
      {showDatePicker.show && (
        <DateTimePicker
          value={new Date()}
          mode="date"
          display="default"
          onChange={handleDateChange}
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0d1421',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#2a3441',
    backgroundColor: '#0d1421',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  tabNavigation: {
    backgroundColor: '#1a252f',
    borderBottomWidth: 1,
    borderBottomColor: '#2a3441',
  },
  tabScrollContainer: {
    paddingHorizontal: 8,
  },
  tabButton: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginHorizontal: 4,
    borderBottomWidth: 3,
    borderBottomColor: 'transparent',
    alignItems: 'center',
    minWidth: 80,
  },
  tabButtonActive: {
    borderBottomWidth: 3,
  },
  tabIconContainer: {
    padding: 6,
    borderRadius: 12,
    marginBottom: 4,
  },
  tabText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
  tabContentContainer: {
    flex: 1,
  },
  tabScrollView: {
    flex: 1,
  },
  tabScrollContent: {
    padding: 16,
    paddingBottom: 100,
  },
  progressContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 16,
    backgroundColor: '#1a252f',
    borderTopWidth: 1,
    borderTopColor: '#2a3441',
  },
  progressDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginHorizontal: 4,
  },
  fabContainer: {
    position: 'absolute',
    bottom: 80,
    right: 20,
  },
  fab: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#2ecc71',
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.3,
    shadowRadius: 4.65,
  },
  fabDisabled: {
    backgroundColor: '#666',
  },
})
