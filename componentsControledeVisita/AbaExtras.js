import React from 'react'
import { View, Text, TextInput, TouchableOpacity } from 'react-native'
import { Feather, Ionicons } from '@expo/vector-icons'
import { styles } from './styles/AbaStyles'

export default function AbaExtras({
  formData,
  setFormData,
  onDatePress,
  formatDateForDisplay,
}) {
  return (
    <View style={styles.tabContent}>
      <Text style={styles.tabTitle}>Informações Extras</Text>
      
      <View style={styles.fieldGroup}>
        <View style={styles.fieldIcon}>
          <Ionicons name="speedometer" size={20} color="#f39c12" />
        </View>
        <View style={styles.fieldContent}>
          <Text style={styles.fieldLabel}>KM Inicial</Text>
          <TextInput
            style={styles.textInput}
            placeholder="0.00"
            placeholderTextColor="#666"
            value={formData.ctrl_km_inic}
            onChangeText={(text) =>
              setFormData({ ...formData, ctrl_km_inic: text })
            }
            keyboardType="numeric"
          />
        </View>
      </View>

      <View style={styles.fieldGroup}>
        <View style={styles.fieldIcon}>
          <Ionicons name="speedometer" size={20} color="#f39c12" />
        </View>
        <View style={styles.fieldContent}>
          <Text style={styles.fieldLabel}>KM Final</Text>
          <TextInput
            style={styles.textInput}
            placeholder="0.00"
            placeholderTextColor="#666"
            value={formData.ctrl_km_fina}
            onChangeText={(text) =>
              setFormData({ ...formData, ctrl_km_fina: text })
            }
            keyboardType="numeric"
          />
        </View>
      </View>

      <View style={styles.fieldGroup}>
        <View style={styles.fieldIcon}>
          <Ionicons name="receipt" size={20} color="#f39c12" />
        </View>
        <View style={styles.fieldContent}>
          <Text style={styles.fieldLabel}>Número do Orçamento</Text>
          <TextInput
            style={styles.textInput}
            placeholder="Número do orçamento"
            placeholderTextColor="#666"
            value={formData.ctrl_nume_orca}
            onChangeText={(text) =>
              setFormData({ ...formData, ctrl_nume_orca: text })
            }
            keyboardType="numeric"
          />
        </View>
      </View>

      <View style={styles.fieldGroup}>
        <View style={styles.fieldIcon}>
          <Ionicons name="calendar-outline" size={20} color="#f39c12" />
        </View>
        <View style={styles.fieldContent}>
          <Text style={styles.fieldLabel}>Próxima Visita</Text>
          <TouchableOpacity
            style={styles.dateButton}
            onPress={() => onDatePress('ctrl_prox_visi')}>
            <Feather name="calendar" size={20} color="#2ecc71" />
            <Text style={styles.dateButtonText}>
              {formatDateForDisplay(formData.ctrl_prox_visi)}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  )
}