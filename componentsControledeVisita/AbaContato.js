import React from 'react'
import { View, Text, TextInput } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { styles } from './styles/AbaStyles'

export default function AbaContato({ formData, setFormData }) {
  return (
    <View style={styles.tabContent}>
      <Text style={styles.tabTitle}>Contato & Observações</Text>
      
      <View style={styles.fieldGroup}>
        <View style={styles.fieldIcon}>
          <Ionicons name="person-circle" size={20} color="#9b59b6" />
        </View>
        <View style={styles.fieldContent}>
          <Text style={styles.fieldLabel}>Nome do Contato</Text>
          <TextInput
            style={styles.textInput}
            placeholder="Nome da pessoa de contato"
            placeholderTextColor="#666"
            value={formData.ctrl_contato}
            onChangeText={(text) =>
              setFormData({ ...formData, ctrl_contato: text })
            }
          />
        </View>
      </View>

      <View style={styles.fieldGroup}>
        <View style={styles.fieldIcon}>
          <Ionicons name="call" size={20} color="#9b59b6" />
        </View>
        <View style={styles.fieldContent}>
          <Text style={styles.fieldLabel}>Telefone</Text>
          <TextInput
            style={styles.textInput}
            placeholder="(00) 00000-0000"
            placeholderTextColor="#666"
            value={formData.ctrl_fone}
            onChangeText={(text) =>
              setFormData({ ...formData, ctrl_fone: text })
            }
            keyboardType="phone-pad"
          />
        </View>
      </View>

      <View style={styles.fieldGroup}>
        <View style={styles.fieldIcon}>
          <Ionicons name="document-text" size={20} color="#9b59b6" />
        </View>
        <View style={styles.fieldContent}>
          <Text style={styles.fieldLabel}>Observações</Text>
          <TextInput
            style={[styles.textInput, styles.textArea]}
            placeholder="Observações sobre a visita..."
            placeholderTextColor="#666"
            value={formData.ctrl_obse}
            onChangeText={(text) =>
              setFormData({ ...formData, ctrl_obse: text })
            }
            multiline
            numberOfLines={4}
            textAlignVertical="top"
          />
        </View>
      </View>
    </View>
  )
}