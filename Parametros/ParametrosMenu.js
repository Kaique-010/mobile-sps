import React from 'react'
import { View, Text, TouchableOpacity, ScrollView } from 'react-native'
import { Feather } from '@expo/vector-icons'
import { parametrosStyles } from './styles/parametrosStyles'

const ParametrosMenu = ({ navigation }) => {
  const menuItems = [
    {
      id: 'modulos-sistema',
      title: 'Módulos do Sistema',
      description: 'Gerenciar permissões de módulos',
      icon: 'grid',
      color: '#007bff',
      route: 'Modulos',
    },

    {
      id: 'parametros',
      title: 'Parâmetros',
      description: 'Ativar/inativar parâmetros ',
      icon: 'layers',
      color: '#6f42c1',
      route: 'Parametros',
    },
  ]

  const handleNavigate = (route) => {
    navigation.navigate(route)
  }

  return (
    <View style={parametrosStyles.container}>
      <View style={parametrosStyles.header}>
        <Text style={parametrosStyles.headerTitle}>Parâmetros do Sistema</Text>
        <Text style={parametrosStyles.headerSubtitle}>
          Configure permissões e comportamentos do sistema
        </Text>
      </View>

      <ScrollView
        style={parametrosStyles.menuContainer}
        showsVerticalScrollIndicator={false}>
        <View style={parametrosStyles.menuGrid}>
          {menuItems.map((item) => (
            <TouchableOpacity
              key={item.id}
              style={[
                parametrosStyles.menuCard,
                { borderLeftColor: item.color },
              ]}
              onPress={() => handleNavigate(item.route)}>
              <View style={parametrosStyles.menuCardHeader}>
                <Feather
                  name={item.icon}
                  size={24}
                  color={item.color}
                  style={parametrosStyles.menuIcon}
                />
                <View style={parametrosStyles.menuContent}>
                  <Text style={parametrosStyles.menuTitle}>{item.title}</Text>
                  <Text style={parametrosStyles.menuDescription}>
                    {item.description}
                  </Text>
                </View>
                <Feather name="chevron-right" size={20} color="#ccc" />
              </View>
            </TouchableOpacity>
          ))}
        </View>

        <View style={parametrosStyles.infoContainer}>
          <Text style={parametrosStyles.infoTitle}>
            Sobre o Sistema de Permissões
          </Text>
          <Text style={parametrosStyles.infoText}>
            O sistema de permissões permite controlar o acesso a módulos, telas
            e operações específicas por empresa e filial. As configurações são
            aplicadas automaticamente em todo o sistema.
          </Text>

          <View style={parametrosStyles.infoFeatures}>
            <Text style={parametrosStyles.infoFeatureTitle}>
              Funcionalidades:
            </Text>
            <Text style={parametrosStyles.infoFeature}>
              • Liberação/bloqueio de módulos
            </Text>
            <Text style={parametrosStyles.infoFeature}>
              • Controle granular de telas
            </Text>
            <Text style={parametrosStyles.infoFeature}>
              • Permissões por operação (CRUD)
            </Text>
            <Text style={parametrosStyles.infoFeature}>
              • Configurações de estoque
            </Text>
            <Text style={parametrosStyles.infoFeature}>
              • Configurações financeiras
            </Text>
            <Text style={parametrosStyles.infoFeature}>
              • Auditoria de alterações
            </Text>
          </View>
        </View>
      </ScrollView>
    </View>
  )
}

export default ParametrosMenu
