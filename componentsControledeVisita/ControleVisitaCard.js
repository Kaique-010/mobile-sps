import React from 'react'
import { View, Text, TouchableOpacity, StyleSheet} from 'react-native'

import { MaterialIcons, Feather } from '@expo/vector-icons'
import { formatDate } from '../utils/formatters'

export default function ControleVisitaCard({
  visita,
  onEdit,
  onDelete,
  onView,
  etapas,
}) {

  
  const etapa = etapas.find((e) => e.etap_id === visita.ctrl_etapa)
  const etapaColor = etapa?.etap_cor || '#666'
  const etapaLabel = etapa?.etap_descricao || visita.etapa_descricao || 'Não definida'

  const formatDateSafe = (dateString) => {
    if (!dateString) return 'Não informado'
    return formatDate(dateString)
  }

  const getStatusIcon = () => {
    if (!etapa) return 'help-circle'

    // Mapear ícones baseado na descrição da etapa
    const iconMap = {
      1: 'search',
      2: 'check-circle',
      3: 'file-text',
      4: 'trending-up',
      5: 'award',
    }

    return iconMap[etapa.etap_id] || 'help-circle'
  }

  return (
    <TouchableOpacity
      style={styles.container}
      onPress={() => onView(visita)}
      activeOpacity={0.7}>
      {/* Header do Card */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View
            style={[styles.statusIndicator, { backgroundColor: etapaColor }]}>
            <Feather name={getStatusIcon()} size={16} color="#fff" />
          </View>
          <View style={styles.headerInfo}>
            <Text style={styles.visitaNumero}>
              Visita #{visita.ctrl_numero}
            </Text>
            <Text style={styles.visitaData}>
              {formatDateSafe(visita.ctrl_data)}
            </Text>
          </View>
        </View>
        <View style={styles.headerRight}>
          <View style={[styles.etapaBadge, { backgroundColor: etapaColor }]}>
            <Text style={styles.etapaText}>{etapaLabel}</Text>
          </View>
        </View>
      </View>

      {/* Informações do Cliente */}
      <View style={styles.clienteSection}>
        <View style={styles.infoRow}>
          <Feather name="user" size={16} color="#2ecc71" />
          <Text style={styles.infoLabel}>Cliente:</Text>
          <Text style={styles.infoValue} numberOfLines={1}>
            {visita.cliente_nome || 'Não informado'}
          </Text>
        </View>

        <View style={styles.infoRow}>
          <Feather name="briefcase" size={16} color="#3498db" />
          <Text style={styles.infoLabel}>Vendedor:</Text>
          <Text style={styles.infoValue} numberOfLines={1}>
            {visita.vendedor_nome || 'Não informado'}
          </Text>
        </View>

        <View style={styles.infoRow}>
          <Feather name="phone" size={16} color="#3498db" />
          <Text style={styles.infoLabel}>Contato:</Text>
          <Text style={styles.infoValue} numberOfLines={1}>
            {visita.ctrl_contato || 'Não informado'}
          </Text>
        </View>
      </View>

      {/* Observações */}
      {visita.ctrl_obse && (
        <View style={styles.observacoesSection}>
          <Text style={styles.observacoesLabel}>Observações:</Text>
          <Text style={styles.observacoesText} numberOfLines={2}>
            {visita.ctrl_obse}
          </Text>
        </View>
      )}

      {/* Próxima Visita */}
      {visita.ctrl_prox_visi && (
        <View style={styles.proximaVisitaSection}>
          <Feather name="calendar" size={16} color="#e74c3c" />
          <Text style={styles.proximaVisitaLabel}>Próxima visita:</Text>
          <Text style={styles.proximaVisitaData}>
            {formatDateSafe(visita.ctrl_prox_visi)}
          </Text>
        </View>
      )}

      {/* KM Percorrido */}
      {visita.km_percorrido && (
        <View style={styles.kmSection}>
          <Feather name="navigation" size={16} color="#9b59b6" />
          <Text style={styles.kmLabel}>KM percorrido:</Text>
          <Text style={styles.kmValue}>
            {(visita.km_percorrido || 0).toFixed(2)} km
          </Text>
        </View>
      )}

      {/* Botões de Ação */}
      <View style={styles.actionsContainer}>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => onView(visita)}>
          <Feather name="eye" size={18} color="#3498db" />
          <Text style={styles.actionButtonText}>Ver</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => onEdit(visita)}>
          <Feather name="edit" size={18} color="#2ecc71" />
          <Text style={styles.actionButtonText}>Editar</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => onDelete(visita)}>
          <Feather name="trash-2" size={18} color="#e74c3c" />
          <Text style={styles.actionButtonText}>Excluir</Text>
        </TouchableOpacity>
      </View>
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#1a252f',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#2a3441',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  statusIndicator: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  headerInfo: {
    flex: 1,
  },
  visitaNumero: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
  },
  visitaData: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  headerRight: {
    alignItems: 'flex-end',
  },
  etapaBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  etapaText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  clienteSection: {
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  infoLabel: {
    fontSize: 14,
    color: '#666',
    marginLeft: 8,
    marginRight: 8,
    minWidth: 70,
  },
  infoValue: {
    fontSize: 14,
    color: '#fff',
    flex: 1,
  },
  observacoesSection: {
    backgroundColor: '#0d1421',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  observacoesLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  observacoesText: {
    fontSize: 14,
    color: '#fff',
    lineHeight: 20,
  },
  proximaVisitaSection: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2c1810',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  proximaVisitaLabel: {
    fontSize: 14,
    color: '#e74c3c',
    marginLeft: 8,
    marginRight: 8,
  },
  proximaVisitaData: {
    fontSize: 14,
    color: '#fff',
    fontWeight: 'bold',
  },
  kmSection: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1525',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  kmLabel: {
    fontSize: 14,
    color: '#9b59b6',
    marginLeft: 8,
    marginRight: 8,
  },
  kmValue: {
    fontSize: 14,
    color: '#fff',
    fontWeight: 'bold',
  },
  actionsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    borderTopWidth: 1,
    borderTopColor: '#2a3441',
    paddingTop: 12,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  actionButtonText: {
    fontSize: 14,
    color: '#666',
    marginLeft: 6,
  },
})
