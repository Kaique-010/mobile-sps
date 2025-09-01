import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Alert,
  StyleSheet,
  ActivityIndicator,
  TextInput,
} from 'react-native'
import { MaterialIcons, Feather } from '@expo/vector-icons'
import { apiGetComContexto, apiDeleteComContexto } from '../utils/api'
import { formatDate, formatNumber } from '../utils/formatters'

export default function ControleVisitaDetalhes({ route, navigation }) {
  const { visitaId } = route.params
  const [visita, setVisita] = useState(null)
  const [etapas, setEtapas] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    carregarDados()
  }, [])

  const carregarDados = async () => {
    try {
      setLoading(true)
      
      // Carregar etapas e visita em paralelo
      const [etapasResponse, visitaResponse] = await Promise.all([
        apiGetComContexto('controledevisitas/etapas-visita/'),
        apiGetComContexto(`controledevisitas/controle-visitas/${visitaId}/`)
      ])
      
      const etapasData = Array.isArray(etapasResponse) ? etapasResponse : etapasResponse?.results || []
      setEtapas(etapasData)
      setVisita(visitaResponse)
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
      Alert.alert('Erro', 'Não foi possível carregar os dados')
      navigation.goBack()
    } finally {
      setLoading(false)
    }
  }

  const getEtapaInfo = (etapaId) => {
    const etapa = etapas.find(e => e.etvi_codigo === etapaId)
    if (!etapa) return { label: 'N/A', icon: 'help', color: '#666' }
    
    // Mapear ícones baseado na descrição
    const iconMap = {
      'Prospecção': 'search',
      'Qualificação': 'assignment',
      'Proposta': 'description', 
      'Negociação': 'handshake',
      'Fechamento': 'check-circle'
    }
    
    return {
      label: etapa.etvi_descricao,
      icon: iconMap[etapa.etvi_descricao] || 'help',
      color: etapa.etvi_cor || '#666'
    }
  }

  const handleEdit = () => {
    navigation.navigate('ControleVisitaForm', {
      visitaId: visita.ctrl_id,
      visita: visita,
      cliente: {
        id: visita.ctrl_cliente,
        nome: visita.cliente_nome
      },
      vendedor: {
        id: visita.ctrl_vendedor,
        nome: visita.vendedor_nome
      }
    })
  }

  // Calcular KM percorrido de forma segura
  const calcularKmPercorrido = () => {
    if (!visita?.ctrl_km_inic || !visita?.ctrl_km_fina) return null
    const inicial = parseFloat(visita.ctrl_km_inic) || 0
    const final = parseFloat(visita.ctrl_km_fina) || 0
    return final > inicial ? final - inicial : null
  }

  

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#2ecc71" />
        <Text style={styles.loadingText}>Carregando detalhes...</Text>
      </View>
    )
  }

  if (!visita) {
    return (
      <View style={styles.errorContainer}>
        <MaterialIcons name="error" size={64} color="#e74c3c" />
        <Text style={styles.errorText}>Visita não encontrada</Text>
      </View>
    )
  }

  const etapaInfo = getEtapaInfo(visita.ctrl_etapa)
  const kmPercorrido = calcularKmPercorrido()

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <MaterialIcons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Detalhes da Visita</Text>
        <TouchableOpacity onPress={handleEdit}>
          <MaterialIcons name="edit" size={24} color="#2ecc71" />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Card Principal */}
        <View style={styles.mainCard}>
          <View style={styles.mainCardHeader}>
            <View style={styles.numeroContainer}>
              <Text style={styles.numeroLabel}>Visita</Text>
              <Text style={styles.numeroText}>#{visita.ctrl_numero || 'N/A'}</Text>
            </View>
            <View
              style={[styles.etapaBadge, { backgroundColor: etapaInfo.color }]}>
              <MaterialIcons name={etapaInfo.icon} size={20} color="#fff" />
              <Text style={styles.etapaText}>{etapaInfo.label}</Text>
            </View>
          </View>

          <View style={styles.dataContainer}>
            <MaterialIcons name="calendar-today" size={20} color="#2ecc71" />
            <Text style={styles.dataText}>{formatDate(visita.ctrl_data)}</Text>
          </View>
        </View>

        {/* Informações do Cliente */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Cliente</Text>
          <View style={styles.infoCard}>
            <View style={styles.infoRow}>
              <MaterialIcons name="person" size={20} color="#2ecc71" />
              <Text style={styles.infoText}>
                {visita.cliente_nome || 'Cliente não informado'}
              </Text>
            </View>
            {visita.ctrl_contato && (
              <View style={styles.infoRow}>
                <MaterialIcons name="contact-phone" size={20} color="#666" />
                <Text style={styles.infoText}>{visita.ctrl_contato}</Text>
              </View>
            )}
            {visita.ctrl_fone && (
              <View style={styles.infoRow}>
                <MaterialIcons name="call" size={20} color="#2ecc71" />
                <Text style={styles.infoText}>{visita.ctrl_fone}</Text>
              </View>
            )}
          </View>
        </View>

        {/* Informações do Vendedor */}
        {visita.vendedor_nome && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Vendedor</Text>
            <View style={styles.infoCard}>
              <View style={styles.infoRow}>
                <MaterialIcons
                  name="person-outline"
                  size={20}
                  color="#2ecc71"
                />
                <Text style={styles.infoText}>{visita.vendedor_nome}</Text>
              </View>
            </View>
          </View>
        )}

        {/* Quilometragem */}
        {(visita.ctrl_km_inic || visita.ctrl_km_fina) && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Quilometragem</Text>
            <View style={styles.infoCard}>
              <View style={styles.kmContainer}>
                <View style={styles.kmItem}>
                  <Text style={styles.kmLabel}>KM Inicial</Text>
                  <Text style={styles.kmValue}>
                    {visita.ctrl_km_inic
                      ? formatNumber(visita.ctrl_km_inic)
                      : 'N/A'}
                  </Text>
                </View>
                <MaterialIcons name="arrow-forward" size={20} color="#666" />
                <View style={styles.kmItem}>
                  <Text style={styles.kmLabel}>KM Final</Text>
                  <Text style={styles.kmValue}>
                    {visita.ctrl_km_fina
                      ? formatNumber(visita.ctrl_km_fina)
                      : 'N/A'}
                  </Text>
                </View>
              </View>
              {kmPercorrido && (
                <View style={styles.kmPercorridoContainer}>
                  <MaterialIcons
                    name="directions-car"
                    size={20}
                    color="#2ecc71"
                  />
                  <Text style={styles.kmPercorridoText}>
                    Percorrido: {formatNumber(kmPercorrido)} km
                  </Text>
                </View>
              )}
            </View>
          </View>
        )}

        {/* Informações Adicionais */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Informações Adicionais</Text>
          <View style={styles.infoCard}>
            <View style={styles.checkboxGrid}>
              {[
                { field: 'ctrl_novo', label: 'Cliente Novo' },
                { field: 'ctrl_base', label: 'Base' },
                { field: 'ctrl_prop', label: 'Proposta' },
                { field: 'ctrl_leva', label: 'Levantamento' },
                { field: 'ctrl_proj', label: 'Projeto' },
              ].map((item) => (
                <View key={item.field} style={styles.checkboxItem}>
                  <MaterialIcons
                    name={
                      visita[item.field]
                        ? 'check-circle'
                        : 'radio-button-unchecked'
                    }
                    size={20}
                    color={visita[item.field] ? '#2ecc71' : '#666'}
                  />
                  <Text
                    style={[
                      styles.checkboxLabel,
                      visita[item.field] && styles.checkboxLabelActive,
                    ]}>
                    {item.label}
                  </Text>
                </View>
              ))}
            </View>
          </View>
        </View>

        {/* Próxima Visita */}
        {visita.ctrl_prox_visi && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Próxima Visita</Text>
            <View style={styles.infoCard}>
              <View style={styles.infoRow}>
                <MaterialIcons name="schedule" size={20} color="#f39c12" />
                <Text style={styles.infoText}>
                  {formatDate(visita.ctrl_prox_visi)}
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* Observações */}
        {visita.ctrl_obse && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Observações</Text>
            <View style={styles.infoCard}>
              <Text style={styles.observacoesText}>{visita.ctrl_obse}</Text>
            </View>
          </View>
        )}

        {/* Informações do Sistema */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Informações do Sistema</Text>
          <View style={styles.infoCard}>
            {visita.field_log_data && (
              <View style={styles.infoRow}>
                <MaterialIcons name="access-time" size={20} color="#666" />
                <Text style={styles.infoText}>
                  Criado em: {formatDate(visita.field_log_data)}
                </Text>
              </View>
            )}
            {visita.ctrl_nume_orca && (
              <View style={styles.infoRow}>
                <MaterialIcons name="description" size={20} color="#666" />
                <Text style={styles.infoText}>
                  Orçamento: #{visita.ctrl_nume_orca}
                </Text>
              </View>
            )}
          </View>
        </View>
      </ScrollView>
      <TouchableOpacity style={styles.editButton} onPress={handleEdit}>
        <MaterialIcons name="edit" size={20} color="#fff" />
        <Text style={styles.editButtonText}>Editar Visita</Text>
      </TouchableOpacity>
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
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#1a252f',
    borderBottomWidth: 1,
    borderBottomColor: '#2ecc71',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  mainCard: {
    backgroundColor: '#1a252f',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#2ecc71',
  },
  mainCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  numeroContainer: {
    alignItems: 'flex-start',
  },
  numeroLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  numeroText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2ecc71',
  },
  etapaBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 6,
  },
  etapaText: {
    fontSize: 14,
    color: '#fff',
    fontWeight: 'bold',
  },
  dataContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  dataText: {
    fontSize: 18,
    color: '#fff',
    fontWeight: '500',
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
  },
  infoCard: {
    backgroundColor: '#1a252f',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2c3e50',
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  infoText: {
    fontSize: 16,
    color: '#fff',
    flex: 1,
  },
  kmContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  kmItem: {
    alignItems: 'center',
    flex: 1,
  },
  kmLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  kmValue: {
    fontSize: 18,
    color: '#fff',
    fontWeight: 'bold',
  },
  kmPercorridoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#2c3e50',
  },
  kmPercorridoText: {
    fontSize: 16,
    color: '#2ecc71',
    fontWeight: 'bold',
  },
  checkboxGrid: {
    gap: 12,
  },
  checkboxItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  checkboxLabel: {
    fontSize: 16,
    color: '#666',
  },
  checkboxLabelActive: {
    color: '#fff',
    fontWeight: '500',
  },
  observacoesText: {
    fontSize: 16,
    color: '#fff',
    lineHeight: 24,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0d1421',
  },
  loadingText: {
    color: '#fff',
    marginTop: 16,
    fontSize: 16,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0d1421',
  },
  errorText: {
    color: '#e74c3c',
    marginTop: 16,
    fontSize: 18,
    textAlign: 'center',
  },
})
