import React from 'react'
import { View, Text, TouchableOpacity } from 'react-native'
import { Feather, Ionicons } from '@expo/vector-icons'
import { Picker } from '@react-native-picker/picker'
import BuscaClienteInput from '../components/BuscaClienteInput'
import BuscaVendedorInput from '../components/BuscaVendedorInput'
import { styles } from './styles/AbaStyles'

export default function AbaDadosBasicos({
  formData,
  setFormData,
  selectedCliente,
  selectedVendedor,
  etapas,
  onClienteSelect,
  onVendedorSelect,
  onDatePress,
  formatDateForDisplay,
}) {
  return (
    <View style={styles.tabContent}>
      <Text style={styles.tabTitle}>Informações Básicas</Text>
      
      <View style={styles.fieldGroup}>
        <View style={styles.fieldIcon}>
          <Ionicons name="person" size={20} color="#3498db" />
        </View>
        <View style={styles.fieldContent}>
          <Text style={styles.fieldLabel}>Cliente *</Text>
          <BuscaClienteInput
            onSelect={onClienteSelect}
            placeholder="Selecionar cliente"
            value={selectedCliente?.enti_nome || ''}
            style={styles.input}
          />
        </View>
      </View>

      <View style={styles.fieldGroup}>
        <View style={styles.fieldIcon}>
          <Ionicons name="calendar" size={20} color="#3498db" />
        </View>
        <View style={styles.fieldContent}>
          <Text style={styles.fieldLabel}>Data da Visita *</Text>
          <TouchableOpacity
            style={styles.dateButton}
            onPress={() => onDatePress('ctrl_data')}>
            <Feather name="calendar" size={20} color="#2ecc71" />
            <Text style={styles.dateButtonText}>
              {formatDateForDisplay(formData.ctrl_data)}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.fieldGroup}>
        <View style={styles.fieldIcon}>
          <Ionicons name="briefcase" size={20} color="#3498db" />
        </View>
        <View style={styles.fieldContent}>
          <Text style={styles.fieldLabel}>Vendedor *</Text>
          <BuscaVendedorInput
            onSelect={onVendedorSelect}
            placeholder="Selecionar vendedor"
            value={selectedVendedor?.enti_nome || ''}
            style={styles.input}
          />
        </View>
      </View>

      <View style={styles.fieldGroup}>
        <View style={styles.fieldIcon}>
          <Ionicons name="flag" size={20} color="#3498db" />
        </View>
        <View style={styles.fieldContent}>
          <Text style={styles.fieldLabel}>Etapa *</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={formData.ctrl_etapa}
              onValueChange={(value) =>
                setFormData({ ...formData, ctrl_etapa: value })
              }
              style={styles.picker}>
              <Picker.Item
                label="Selecione uma etapa"
                value=""
                color="#999"
              />
              {etapas.map((etapa) => (
                <Picker.Item
                  key={etapa.etap_id}
                  label={etapa.etap_descricao}
                  value={etapa.etap_id}
                  color="#000"
                />
              ))}
            </Picker>
          </View>
        </View>
      </View>
    </View>
  )
}