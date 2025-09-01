import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  TextInput,
  Alert,
} from 'react-native'
import { MaterialIcons, Feather } from '@expo/vector-icons'
import DateTimePicker from '@react-native-community/datetimepicker'
import { Picker } from '@react-native-picker/picker'
import { apiGetComContexto } from '../utils/api'
import BuscaVendedorInput from '../components/BuscaVendedorInput'

export default function ControleVisitaFilters({
  filters,
  onApply,
  onClear,
  onClose,
  etapas, // Agora recebe etapas do backend
}) {
  const [localFilters, setLocalFilters] = useState({
    ...filters,
    proxima_visita: filters.proxima_visita || false,
  })
  const [showDatePicker, setShowDatePicker] = useState({
    field: null,
    show: false,
  })
  const [vendedores, setVendedores] = useState([])

  useEffect(() => {
    carregarVendedores()
  }, [])

  const carregarVendedores = async () => {
    try {
      const response = await apiGetComContexto('entidades/', {
        enti_tipo: 'V', // Vendedores
        limit: 1000,
      })
      // Ensure vendedores is always an array
      const vendedoresData = response?.results || response || []
      setVendedores(Array.isArray(vendedoresData) ? vendedoresData : [])
    } catch (error) {
      console.error('Erro ao carregar vendedores:', error)
      setVendedores([]) // Set empty array on error
    }
  }

  const handleDateChange = (event, selectedDate) => {
    setShowDatePicker({ field: null, show: false })

    if (selectedDate && showDatePicker.field) {
      const formattedDate = selectedDate.toISOString().split('T')[0]
      setLocalFilters({
        ...localFilters,
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

  const handleApply = () => {
    onApply(localFilters)
  }

  const handleClear = () => {
    const clearedFilters = {
      etapa: '',
      vendedor: '',
      data_inicio: '',
      data_fim: '',
      cliente_nome: '',
      proxima_visita: false,
    }
    setLocalFilters(clearedFilters)
    onClear()
  }

  const handleVendedorSelect = (vendedor) => {
    setLocalFilters({
      ...localFilters,
      vendedor: vendedor?.enti_clie || '',
    })
  }

  // Função para obter nome do vendedor selecionado
  const getSelectedVendedorName = () => {
    if (!localFilters.vendedor) return ''
    const vendedor = vendedores.find(
      (v) => v.enti_id === parseInt(localFilters.vendedor)
    )
    return vendedor ? vendedor.enti_nome : ''
  }

  // Função para obter descrição da etapa selecionada
  const getSelectedEtapaName = () => {
    if (!localFilters.etapa) return ''
    const etapa = etapas.find((e) => e.etap_id === parseInt(localFilters.etapa))
    return etapa ? etapa.etap_descricao : ''
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.closeButton} onPress={onClose}>
          <MaterialIcons name="close" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Filtros</Text>
        <TouchableOpacity style={styles.clearButton} onPress={handleClear}>
          <Text style={styles.clearButtonText}>Limpar</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {/* Filtro de Nome do Cliente */}
        <View style={styles.filterSection}>
          <Text style={styles.filterLabel}>Nome do Cliente</Text>
          <TextInput
            style={styles.textInput}
            placeholder="Digite o nome do cliente"
            placeholderTextColor="#666"
            value={localFilters.cliente_nome}
            onChangeText={(text) =>
              setLocalFilters({ ...localFilters, cliente_nome: text })
            }
          />
        </View>

        {/* Filtro de Etapa */}
        <View style={styles.filterSection}>
          <Text style={styles.filterLabel}>Etapa</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={localFilters.etapa}
              onValueChange={(value) =>
                setLocalFilters({ ...localFilters, etapa: value })
              }
              style={styles.picker}>
              <Picker.Item label="Todas as etapas" value="" color="#000" />
              {etapas.map((etapa) => (
                <Picker.Item
                  key={etapa.etap_id}
                  label={etapa.etap_descricao}
                  value={etapa.etap_id.toString()}
                  color="#000"
                />
              ))}
            </Picker>
          </View>
        </View>

        {/* Filtro de Vendedor */}
        <View style={styles.filterSection}>
          <Text style={styles.filterLabel}>Vendedor</Text>
          <View style={styles.vendedorInput}>
            <BuscaVendedorInput
              value={getSelectedVendedorName()}
              onSelect={handleVendedorSelect}
              placeholder="Selecione um vendedor"
            />
          </View>
        </View>

        {/* NOVO: Filtro de Próxima Visita */}
        <View style={styles.filterSection}>
          <TouchableOpacity
            style={[
              styles.checkboxContainer,
              localFilters.proxima_visita && styles.checkboxContainerActive,
            ]}
            onPress={() =>
              setLocalFilters({
                ...localFilters,
                proxima_visita: !localFilters.proxima_visita,
              })
            }>
            <MaterialIcons
              name={
                localFilters.proxima_visita
                  ? 'check-box'
                  : 'check-box-outline-blank'
              }
              size={24}
              color={localFilters.proxima_visita ? '#2ecc71' : '#666'}
            />
            <Text
              style={[
                styles.checkboxLabel,
                localFilters.proxima_visita && styles.checkboxLabelActive,
              ]}>
              Apenas próximas visitas
            </Text>
          </TouchableOpacity>
          <Text style={styles.checkboxDescription}>
            Mostrar apenas visitas agendadas para hoje ou datas futuras
          </Text>
        </View>

        {/* Filtro de Data de Início */}
        <View style={styles.filterSection}>
          <Text style={styles.filterLabel}>Data de Início</Text>
          <TouchableOpacity
            style={styles.dateButton}
            onPress={() => showDatePickerModal('data_inicio')}>
            <Feather name="calendar" size={20} color="#2ecc71" />
            <Text style={styles.dateButtonText}>
              {localFilters.data_inicio
                ? formatDateForDisplay(localFilters.data_inicio)
                : 'Selecionar data'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Filtro de Data de Fim */}
        <View style={styles.filterSection}>
          <Text style={styles.filterLabel}>Data de Fim</Text>
          <TouchableOpacity
            style={styles.dateButton}
            onPress={() => showDatePickerModal('data_fim')}>
            <Feather name="calendar" size={20} color="#2ecc71" />
            <Text style={styles.dateButtonText}>
              {localFilters.data_fim
                ? formatDateForDisplay(localFilters.data_fim)
                : 'Selecionar data'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Resumo dos Filtros Ativos */}
        {(localFilters.cliente_nome ||
          localFilters.etapa ||
          localFilters.vendedor ||
          localFilters.data_inicio ||
          localFilters.data_fim ||
          localFilters.proxima_visita) && (
          <View style={styles.summarySection}>
            <Text style={styles.summaryTitle}>Filtros Ativos:</Text>
            {localFilters.cliente_nome && (
              <View style={styles.summaryItem}>
                <Text style={styles.summaryKey}>Cliente:</Text>
                <Text style={styles.summaryValue}>
                  {localFilters.cliente_nome}
                </Text>
              </View>
            )}
            {localFilters.etapa && (
              <View style={styles.summaryItem}>
                <Text style={styles.summaryKey}>Etapa:</Text>
                <Text style={styles.summaryValue}>
                  {getSelectedEtapaName()}
                </Text>
              </View>
            )}
            {localFilters.vendedor && (
              <View style={styles.summaryItem}>
                <Text style={styles.summaryKey}>Vendedor:</Text>
                <Text style={styles.summaryValue}>
                  {getSelectedVendedorName()}
                </Text>
              </View>
            )}
            {localFilters.proxima_visita && (
              <View style={styles.summaryItem}>
                <Text style={styles.summaryKey}>Tipo:</Text>
                <Text style={styles.summaryValue}>Próximas visitas</Text>
              </View>
            )}
            {localFilters.data_inicio && (
              <View style={styles.summaryItem}>
                <Text style={styles.summaryKey}>Data início:</Text>
                <Text style={styles.summaryValue}>
                  {formatDateForDisplay(localFilters.data_inicio)}
                </Text>
              </View>
            )}
            {localFilters.data_fim && (
              <View style={styles.summaryItem}>
                <Text style={styles.summaryKey}>Data fim:</Text>
                <Text style={styles.summaryValue}>
                  {formatDateForDisplay(localFilters.data_fim)}
                </Text>
              </View>
            )}
          </View>
        )}
      </ScrollView>

      {/* Botões de Ação */}
      <View style={styles.footer}>
        <TouchableOpacity style={styles.cancelButton} onPress={onClose}>
          <Text style={styles.cancelButtonText}>Cancelar</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.applyButton} onPress={handleApply}>
          <Text style={styles.applyButtonText}>Aplicar Filtros</Text>
        </TouchableOpacity>
      </View>

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

// Adicionar novos estilos
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
  },
  closeButton: {
    padding: 8,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  clearButton: {
    padding: 8,
  },
  clearButtonText: {
    color: '#e74c3c',
    fontSize: 16,
    fontWeight: '600',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  filterSection: {
    marginBottom: 24,
  },
  filterLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 8,
  },
  textInput: {
    backgroundColor: '#1a252f',
    borderRadius: 12,
    padding: 16,
    color: '#fff',
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#2a3441',
  },
  pickerContainer: {
    backgroundColor: '#1a252f',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#2a3441',
  },
  picker: {
    color: '#fff',
    backgroundColor: 'transparent',
  },
  vendedorInput: {
    backgroundColor: '#1a252f',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#2a3441',
  },
  dateButton: {
    backgroundColor: '#1a252f',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2a3441',
  },
  dateButtonText: {
    color: '#fff',
    fontSize: 16,
    marginLeft: 12,
  },
  summarySection: {
    backgroundColor: '#1a252f',
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
    borderWidth: 1,
    borderColor: '#2a3441',
  },
  summaryTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2ecc71',
    marginBottom: 12,
  },
  summaryItem: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  summaryKey: {
    fontSize: 14,
    color: '#666',
    minWidth: 100,
  },
  summaryValue: {
    fontSize: 14,
    color: '#fff',
    flex: 1,
  },
  footer: {
    flexDirection: 'row',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#2a3441',
    gap: 12,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#2a3441',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  applyButton: {
    flex: 1,
    backgroundColor: '#2ecc71',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  applyButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a252f',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2a3441',
  },
  checkboxContainerActive: {
    borderColor: '#2ecc71',
    backgroundColor: '#1a2f1f',
  },
  checkboxLabel: {
    fontSize: 16,
    color: '#fff',
    marginLeft: 12,
    flex: 1,
  },
  checkboxLabelActive: {
    color: '#2ecc71',
    fontWeight: '600',
  },
  checkboxDescription: {
    fontSize: 12,
    color: '#666',
    marginTop: 8,
    fontStyle: 'italic',
  },
})
