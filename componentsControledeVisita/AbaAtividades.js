import React from 'react'
import { View, Text, Switch, Animated } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { styles } from './styles/AbaStyles'

const SwitchField = ({ label, field, description, icon, formData, setFormData, scrollX, activeTab, width }) => (
  <Animated.View style={[
    styles.switchContainer,
    {
      transform: [{
        scale: scrollX.interpolate({
          inputRange: [(activeTab - 1) * width, activeTab * width, (activeTab + 1) * width],
          outputRange: [0.95, 1, 0.95],
          extrapolate: 'clamp',
        })
      }]
    }
  ]}>
    <View style={styles.switchContent}>
      <View style={styles.switchIcon}>
        <Ionicons name={icon} size={24} color="#2ecc71" />
      </View>
      <View style={styles.switchInfo}>
        <Text style={styles.switchLabel}>{label}</Text>
        {description && (
          <Text style={styles.switchDescription}>{description}</Text>
        )}
      </View>
      <Switch
        value={!!formData[field]}
        onValueChange={(value) =>
          setFormData({ ...formData, [field]: value ? 1 : 0 })
        }
        trackColor={{ false: '#2a3441', true: '#2ecc71' }}
        thumbColor={formData[field] ? '#fff' : '#666'}
        ios_backgroundColor="#2a3441"
      />
    </View>
  </Animated.View>
)

export default function AbaAtividades({ formData, setFormData, scrollX, activeTab, width }) {
  const atividades = [
    {
      label: 'Cliente Novo',
      field: 'ctrl_novo',
      description: 'Marque se é um cliente novo',
      icon: 'person-add'
    },
    {
      label: 'Levantamento de Base',
      field: 'ctrl_base',
      description: 'Foi feito levantamento da base do cliente',
      icon: 'analytics'
    },
    {
      label: 'Proposta Apresentada',
      field: 'ctrl_prop',
      description: 'Foi apresentada uma proposta',
      icon: 'document'
    },
    {
      label: 'Levantamento Técnico',
      field: 'ctrl_leva',
      description: 'Foi feito levantamento técnico',
      icon: 'construct'
    },
    {
      label: 'Projeto Elaborado',
      field: 'ctrl_proj',
      description: 'Foi elaborado um projeto',
      icon: 'library'
    }
  ]

  return (
    <View style={styles.tabContent}>
      <Text style={styles.tabTitle}>Atividades Realizadas</Text>
      
      {atividades.map((atividade) => (
        <SwitchField
          key={atividade.field}
          label={atividade.label}
          field={atividade.field}
          description={atividade.description}
          icon={atividade.icon}
          formData={formData}
          setFormData={setFormData}
          scrollX={scrollX}
          activeTab={activeTab}
          width={width}
        />
      ))}
    </View>
  )
}