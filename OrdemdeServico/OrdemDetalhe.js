import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Modal,
} from 'react-native'
import AbaPecas from '../componentsOs/AbaPecas'
import AbaServicos from '../componentsOs/AbaServicos'
import AbaFotos from '../componentsOs/AbaForos'
import AbaTotais from '../componentsOs/AbaTotais'
import WorkflowButton from '../componentsOs/WorkflowButton'
import { apiGetComContexto, apiPatchComContexto } from '../utils/api'
import useContextoApp from '../hooks/useContextoApp'

const OrdemDetalhe = ({ route }) => {
  const { ordem } = route.params
  const { usuarioId } = useContextoApp()
  const [abaAtiva, setAbaAtiva] = useState('detalhes')
  const [pecas, setPecas] = useState([])
  const [servicos, setServicos] = useState([])
  const [ordemAtual, setOrdemAtual] = useState(ordem)
  const [prioridade, setPrioridade] = useState(ordemAtual.orde_prio)

  const STATUS_OPTIONS = [
    { label: 'Todas', value: null },
    { label: 'Aberta', value: 0 },
    { label: 'Orçamento gerado', value: 1 },
    { label: 'Aguardando Liberação', value: 2 },
    { label: 'Liberada', value: 3 },
    { label: 'Finalizada', value: 4 },
    { label: 'Reprovada', value: 5 },
    { label: 'Faturada parcial', value: 20 },
    { label: 'Em atraso', value: 21 },
  ]

  const prioridadeValor =
    typeof prioridade === 'string' ? parseInt(prioridade, 10) : prioridade
  const prioridadeLabel =
    prioridadeValor === 0
      ? 'Normal'
      : prioridadeValor === 1
      ? 'Alerta'
      : prioridadeValor === 2
      ? 'Urgente'
      : '-'

  const alterarPrioridade = async (nova) => {
    setPrioridade(nova)
    try {
      const resp = await apiPatchComContexto(
        `ordemdeservico/ordens/${ordemAtual.orde_nume}/atualizar-prioridade/`,
        { orde_prio: nova }
      )
      console.log('✅ Prioridade atualizada:', resp.mensagem)
    } catch (err) {
      console.error('❌ Erro ao atualizar prioridade', err)
    }
  }

  const modalAlterarPrioridade = () => {
    setModalVisible(true)
  }

  const [modalVisible, setModalVisible] = useState(false)

  useEffect(() => {
    carregarPecas()
    carregarServicos()
  }, [])

  useEffect(() => {
    if (abaAtiva === 'totais') {
      carregarPecas()
      carregarServicos()
    }
  }, [abaAtiva])

  const carregarPecas = async () => {
    try {
      const response = await apiGetComContexto('ordemdeservico/pecas/', {
        peca_orde: ordemAtual.orde_nume,
        peca_empr: ordemAtual.orde_empr,
        peca_fili: ordemAtual.orde_fili,
      })
      setPecas(response?.results || [])
    } catch (error) {
      console.error('Erro ao carregar peças:', error)
    }
  }

  const carregarServicos = async () => {
    try {
      const response = await apiGetComContexto('ordemdeservico/servicos/', {
        serv_orde: ordemAtual.orde_nume,
        serv_empr: ordemAtual.orde_empr,
        serv_fili: ordemAtual.orde_fili,
      })
      setServicos(response?.results || [])
    } catch (error) {
      console.error('Erro ao carregar serviços:', error)
    }
  }

  const handleOrdemAtualizada = (ordemAtualizada) => {
    setOrdemAtual(ordemAtualizada)
  }

  const renderDetalhes = () => (
    <ScrollView style={styles.detalhesContainer}>
      <View style={styles.infoCard}>
        <Text style={styles.cardTitle}>Informações Gerais</Text>

        <View style={styles.infoRow}>
          <Text style={styles.label}>Tipo:</Text>
          <Text style={styles.value}>{ordem.orde_tipo || '-'}</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.label}>Status:</Text>
          <Text style={styles.value}>
            {STATUS_OPTIONS.find(
              (item) => item.value === ordemAtual.orde_stat_orde
            )?.label || '-'}
          </Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.label}>Prioridade:</Text>
          <TouchableOpacity
            onPress={modalAlterarPrioridade}
            style={styles.valueRow}>
            <View
              style={[
                styles.priorityDot,
                styles.priorityDotInline,
                prioridadeValor === 0
                  ? styles.priorityDotBaixa
                  : prioridadeValor === 1
                  ? styles.priorityDotMedia
                  : prioridadeValor === 2
                  ? styles.priorityDotAlta
                  : null,
              ]}>
              <Text style={styles.priorityDotInlineText}>
                {Number.isFinite(prioridadeValor) ? prioridadeValor : '-'}
              </Text>
            </View>
            <Text style={styles.value}>{prioridadeLabel}</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.label}>Total:</Text>
          <Text style={[styles.value, styles.totalValue]}>
            R$ {Number(ordemAtual.orde_tota || 0).toFixed(2)}
          </Text>
        </View>
      </View>

      <View style={styles.infoCard}>
        <Text style={styles.cardTitle}>Datas</Text>

        <View style={styles.infoRow}>
          <Text style={styles.label}>Abertura:</Text>
          <Text style={styles.value}>{ordemAtual.orde_data_aber || '-'}</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.label}>Fechamento:</Text>
          <Text style={styles.value}>{ordemAtual.orde_data_fech || '-'}</Text>
        </View>
      </View>

      <View style={styles.infoCard}>
        <Text style={styles.cardTitle}>Descrições</Text>

        <View style={styles.descriptionRow}>
          <Text style={styles.label}>Problema:</Text>
          <Text style={styles.value}>{ordemAtual.orde_prob || '-'}</Text>
        </View>

        <View style={styles.descriptionRow}>
          <Text style={styles.label}>Defeito:</Text>
          <Text style={styles.value}>{ordemAtual.orde_defe_desc || '-'}</Text>
        </View>

        <View style={styles.descriptionRow}>
          <Text style={styles.label}>Observações:</Text>
          <Text style={styles.value}>{ordemAtual.orde_obse || '-'}</Text>
        </View>
        <View style={styles.descriptionRow}>
          <Text style={styles.label}>Setor:</Text>
          <Text style={styles.value}>{ordemAtual.setor_nome || '-'}</Text>
        </View>
      </View>

      <WorkflowButton
        style={styles.workflowButton}
        ordem={ordemAtual}
        onOrdemAtualizada={handleOrdemAtualizada}
      />
    </ScrollView>
  )


  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>OS #{ordemAtual.orde_nume}</Text>
        <Text style={styles.subtitle}>Cliente: {ordemAtual.cliente_nome}</Text>
      </View>

      <View style={styles.tabs}>
        {['detalhes', 'pecas', 'servicos', 'fotos'].map((aba) => (
          <TouchableOpacity
            key={aba}
            onPress={() => setAbaAtiva(aba)}
            style={[styles.tab, abaAtiva === aba && styles.tabActive]}>
            <Text
              style={[
                styles.tabText,
                abaAtiva === aba && styles.tabTextActive,
              ]}>
              {aba.charAt(0).toUpperCase() + aba.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.content}>
        {abaAtiva === 'detalhes' && renderDetalhes()}
        {abaAtiva === 'pecas' && (
          <AbaPecas
            pecas={pecas}
            setPecas={setPecas}
            orde_nume={ordemAtual.orde_nume}
          />
        )}
        {abaAtiva === 'servicos' && (
          <AbaServicos
            servicos={servicos}
            setServicos={setServicos}
            orde_nume={ordemAtual.orde_nume}
          />
        )}
        {abaAtiva === 'fotos' && (
          <AbaFotos
            fotos={[]}
            setFotos={() => {}}
            orde_nume={ordemAtual.orde_nume}
            codTecnico={usuarioId}
          />
        )}
        {abaAtiva === 'totais' && (
          <AbaTotais
            pecas={pecas}
            servicos={servicos}
            orde_nume={ordemAtual.orde_nume}
            orde_clie={ordemAtual.orde_enti}
            orde_empr={ordemAtual.orde_empr}
            orde_fili={ordemAtual.orde_fili}
          />
        )}
      </View>
      {modalVisible && (
        <Modal
          animationType="slide"
          transparent={true}
          visible={modalVisible}
          onRequestClose={() => setModalVisible(false)}
        >
          <View style={styles.modalContainer}>
            <View style={styles.modalContent}>
              <Text style={styles.modalTitle}>Alterar Prioridade</Text>
              <TouchableOpacity
                style={styles.modalButton}
                onPress={() => {
                  alterarPrioridade(0)
                  setModalVisible(false)
                }}>
                <View style={styles.modalButtonContent}>
                  <View style={[styles.priorityDot, styles.priorityDotBaixa]}>
                    <Text style={styles.priorityDotText}>0</Text>
                  </View>
                  <Text style={styles.modalButtonText}>Alerta</Text>
                </View>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalButton}
                onPress={() => {
                  alterarPrioridade(1)
                  setModalVisible(false)
                }}>
                <View style={styles.modalButtonContent}>
                  <View style={[styles.priorityDot, styles.priorityDotMedia]}>
                    <Text style={styles.priorityDotText}>1</Text>
                  </View>
                  <Text style={styles.modalButtonText}>Urgente</Text>
                </View>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalButton}
                onPress={() => {
                  alterarPrioridade(2)
                  setModalVisible(false)
                }}>
                <View style={styles.modalButtonContent}>
                  <View style={[styles.priorityDot, styles.priorityDotAlta]}>
                    <Text style={styles.priorityDotText}>2</Text>
                  </View>
                  <Text style={styles.modalButtonText}>Alta</Text>
                </View>
              </TouchableOpacity>
            </View>
          </View>
        </Modal>
      )}
    </View>
  )
}


const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a2f3d',
  },
  header: {
    padding: 20,
    backgroundColor: '#232935',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#10a2a7',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 20,
    color: '#faebd7',
    opacity: 0.8,
  },
  tabs: {
    flexDirection: 'row',
    backgroundColor: '#232935',
    paddingHorizontal: 10,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: '#10a2a7',
  },
  tabText: {
    color: '#faebd7',
    opacity: 0.7,
  },
  tabTextActive: {
    color: '#10a2a7',
    opacity: 1,
    fontWeight: 'bold',
  },
  content: {
    flex: 1,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#232935',
    borderRadius: 8,
    padding: 20,
    width: '90%',
  },
  modalTitle: {
    color: '#10a2a7',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
    textAlign: 'center',
  },
  modalButton: {
    backgroundColor: '#10a2a7',
    paddingVertical: 12,
    borderRadius: 6,
    marginTop: 10,
  },
  modalButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  modalButtonContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  priorityDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: '#10a2a7',
    marginRight: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  priorityDotBaixa: {
    backgroundColor: 'rgba(16, 162, 167, 0.25)',
  },
  priorityDotMedia: {
    backgroundColor: 'rgba(16, 162, 167, 0.55)',
  },
  priorityDotAlta: {
    backgroundColor: '#10a2a7',
  },
  priorityDotText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  valueRow: {
    flex: 2,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
  },
  priorityDotInline: {
    width: 18,
    height: 18,
    borderRadius: 9,
    marginRight: 8,
  },
  priorityDotInlineText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  detalhesContainer: {
    padding: 15,
    paddingBottom: 100,
    marginBottom: 50,
  },
  infoCard: {
    backgroundColor: '#232935',
    borderRadius: 8,
    padding: 15,
    marginBottom: 15,
  },
  cardTitle: {
    color: '#10a2a7',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#1a2f3d',
  },
  descriptionRow: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#1a2f3d',
  },
  label: {
    color: '#faebd7',
    opacity: 0.7,
    flex: 1,
  },
  value: {
    color: '#fff',
    flex: 2,
    textAlign: 'right',
  },
  totalValue: {
    color: '#10a2a7',
    fontWeight: 'bold',
    fontSize: 16,
  },
  workflowButton: {
    marginBottom: 0,
    marginTop: 20,
    paddingHorizontal: 15,

    alignSelf: 'flex-end',
  },
})

export default OrdemDetalhe
