import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  FlatList,
  Alert,
  Modal,
  TextInput,
  ActivityIndicator,
  ScrollView,
} from 'react-native'
import { Ionicons, MaterialIcons } from '@expo/vector-icons'
import { styles } from './styles/AbaStyles'
import {
  apiGetComContexto,
  apiPostComContexto,
  apiDeleteComContexto,
  apiPutComContexto,
} from '../utils/api'
import BuscaProdutoInput from '../components/BuscaProdutosInput'
import BuscaServicoInput from '../components/BuscaServicoInput'

const ItemVisitaCard = ({ item, onEdit, onDelete }) => (
  <View style={localStyles.itemCard}>
    <View style={localStyles.itemHeader}>
      <Text style={localStyles.itemProduto}>{item.item_prod}</Text>
      <View style={localStyles.itemActions}>
        <TouchableOpacity
          onPress={() => onEdit(item)}
          style={localStyles.editButton}>
          <Ionicons name="pencil" size={16} color="#fff" />
        </TouchableOpacity>
        <TouchableOpacity
          onPress={() => onDelete(item)}
          style={localStyles.deleteButton}>
          <Ionicons name="trash" size={16} color="#fff" />
        </TouchableOpacity>
      </View>
    </View>

    {item.item_desc_prod && (
      <Text style={localStyles.itemDescricao}>{item.item_desc_prod}</Text>
    )}

    <View style={localStyles.itemDetalhes}>
      <Text style={localStyles.itemQuantidade}>Qtd: {item.item_quan}</Text>
      <Text style={localStyles.itemUnidade}>Un: {item.item_unli}</Text>
      <Text style={localStyles.itemValor}>
        R$ {(parseFloat(item.item_unit) || 0).toFixed(2)}
      </Text>
      <Text style={localStyles.itemTotal}>
        Total: R$ {(parseFloat(item.item_tota) || 0).toFixed(2)}
      </Text>
    </View>
  </View>
)

export default function AbaItens({ visitaId, formData, empresaId, filialId }) {
  const [itens, setItens] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [tipoItem, setTipoItem] = useState('produto')
  const [itemForm, setItemForm] = useState({
    item_prod: '',
    item_desc_prod: '',
    item_quan: '',
    item_unit: '',
    item_unli: 'UN',
    item_desc: '0',
    item_obse: '',
    item_codigo: '',
  })

  useEffect(() => {
    if (visitaId) {
      carregarItens()
    }
  }, [visitaId])

  const carregarItens = async () => {
    try {
      setLoading(true)
      const response = await apiGetComContexto(
        `controledevisitas/itens-visita/?item_visita=${visitaId}`
      )
      setItens(response?.results || response || [])
    } catch (error) {
      console.error('Erro ao carregar itens:', error)
      Alert.alert('Erro', 'Não foi possível carregar os itens')
    } finally {
      setLoading(false)
    }
  }

  const salvarItem = async () => {
    try {
      if (!itemForm.item_prod.trim()) {
        Alert.alert('Erro', 'Produto/Serviço é obrigatório')
        return
      }

      // Validar produto duplicado
      const produtoExistente = itens.find(
        (item) =>
          item.item_prod.toLowerCase() ===
            itemForm.item_prod.trim().toLowerCase() &&
          (!editingItem || item.item_id !== editingItem.item_id)
      )

      if (produtoExistente) {
        Alert.alert(
          'Produto Duplicado',
          `O produto "${itemForm.item_prod}" já foi adicionado à esta visita.\n\nDeseja editar o item existente?`,
          [
            { text: 'Cancelar', style: 'cancel' },
            {
              text: 'Editar Existente',
              onPress: () => {
                editarItem(produtoExistente)
              },
            },
          ]
        )
        return
      }

      const quantidade = parseFloat(itemForm.item_quan)
      const valorUnit = parseFloat(itemForm.item_unit)
      const desconto = parseFloat(itemForm.item_desc) || 0

      if (!quantidade || quantidade <= 0) {
        Alert.alert('Erro', 'Quantidade deve ser maior que zero')
        return
      }

      if (!valorUnit || valorUnit <= 0) {
        Alert.alert('Erro', 'Valor unitário deve ser maior que zero')
        return
      }

      // Validar se visitaId e formData existem
      if (!visitaId) {
        Alert.alert('Erro', 'ID da visita não encontrado')
        return
      }

      // Usar os props passados ou fallback para formData
      const empresaIdToUse = empresaId || formData?.ctrl_empresa
      const filialIdToUse = filialId || formData?.ctrl_filial

      if (!visitaId) {
        Alert.alert('Erro', 'Salve a visita antes de adicionar itens')
        return
      }

      if (!empresaIdToUse || !filialIdToUse) {
        Alert.alert('Erro', 'Dados da empresa/filial não encontrados')
        return
      }

      const itemData = {
        item_prod: itemForm.item_prod.trim(),
        item_desc_prod: itemForm.item_desc_prod?.trim() || '',
        item_quan: quantidade,
        item_unit: valorUnit,
        item_desc: desconto,
        item_unli: itemForm.item_unli || 'UN',
        item_obse: itemForm.item_obse?.trim() || '',
        item_visita: parseInt(visitaId),
        item_empr: parseInt(empresaIdToUse),
        item_fili: parseInt(filialIdToUse),
      }

      console.log('Dados enviados:', itemData) // Para debug

      if (editingItem) {
        await apiPutComContexto(
          `controledevisitas/itens-visita/${editingItem.item_id}/`,
          itemData
        )
      } else {
        await apiPostComContexto('controledevisitas/itens-visita/', itemData)
      }

      setModalVisible(false)
      resetForm()
      carregarItens()
    } catch (error) {
      console.error('Erro ao salvar item:', error)
      console.error('Detalhes do erro:', error.response?.data)
      Alert.alert(
        'Erro',
        `Não foi possível salvar o item: ${
          error.response?.data?.detail || error.message
        }`
      )
    }
  }

  const editarItem = (item) => {
    setEditingItem(item)
    setItemForm({
      item_prod: item.item_prod,
      item_desc_prod: item.item_desc_prod || '',
      item_quan: item.item_quan?.toString() || '',
      item_unit: item.item_unit?.toString() || '',
      item_unli: item.item_unli || 'UN',
      item_desc: item.item_desc?.toString() || '0',
      item_obse: item.item_obse || '',
      item_codigo: item.item_codigo || '',
    })
    setModalVisible(true)
  }

  const excluirItem = (item) => {
    Alert.alert(
      'Confirmar Exclusão',
      `Deseja excluir o item "${item.item_prod}"?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Excluir',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiDeleteComContexto(
                `controledevisitas/itens-visita/${item.item_id}/`
              )
              carregarItens()
            } catch (error) {
              Alert.alert('Erro', 'Não foi possível excluir o item')
            }
          },
        },
      ]
    )
  }

  const exportarParaOrcamento = () => {
    if (itens.length === 0) {
      Alert.alert('Aviso', 'Adicione itens antes de exportar para orçamento')
      return
    }

    Alert.alert(
      'Exportar para Orçamento',
      'Deseja criar um orçamento com os itens desta visita?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Exportar',
          onPress: async () => {
            try {
              setLoading(true)
              const response = await apiPostComContexto(
                'controledevisitas/itens-visita/exportar-para-orcamento/',
                { visita_id: visitaId }
              )

              Alert.alert(
                'Sucesso',
                `Orçamento ${response.orcamento_numero} criado com ${
                  response.total_itens
                } itens.\nValor total: R$ ${response.valor_total.toFixed(2)}`
              )
            } catch (error) {
              Alert.alert('Erro', 'Não foi possível exportar para orçamento')
            } finally {
              setLoading(false)
            }
          },
        },
      ]
    )
  }

  const resetForm = () => {
    setEditingItem(null)
    setTipoItem('produto')
    setItemForm({
      item_prod: '',
      item_desc_prod: '',
      item_quan: '',
      item_unit: '',
      item_unli: 'UN',
      item_desc: '0',
      item_obse: '',
      item_codigo: '',
    })
  }

  const handleSelecionarProduto = (produto) => {
    setItemForm({
      ...itemForm,
      item_prod: produto.prod_codi,
      item_desc_prod: produto.prod_nome,
      item_unit: produto.prod_preco_vista?.toString() || '0',
      item_codigo: produto.prod_codi,
    })
  }

  const handleSelecionarServico = (servico) => {
    setItemForm({
      ...itemForm,
      item_prod: servico.serv_nome,
      item_desc_prod: '',
      item_unit: servico.serv_preco?.toString() || '0',
      item_codigo: servico.serv_prod,
    })
  }

  const valorTotal = Array.isArray(itens)
    ? itens.reduce((total, item) => {
        const itemTotal = parseFloat(item.item_tota) || 0
        return total + itemTotal
      }, 0)
    : 0

  return (
    <View style={styles.tabContent}>
      <View style={localStyles.headerItens}>
        <Text style={styles.tabTitle}>Itens da Visita (Pré-Orçamento)</Text>
        <Text style={localStyles.valorTotal}>
          Total: R$ {Number(valorTotal).toFixed(2)}
        </Text>
      </View>

      <View style={localStyles.actionsContainer}>
        <TouchableOpacity
          style={localStyles.addButton}
          onPress={() => {
            resetForm()
            setModalVisible(true)
          }}>
          <Ionicons name="add" size={20} color="#fff" />
          <Text style={localStyles.addButtonText}>Adicionar Item</Text>
        </TouchableOpacity>

        {itens.length > 0 && (
          <TouchableOpacity
            style={localStyles.exportButton}
            onPress={exportarParaOrcamento}>
            <MaterialIcons name="file-download" size={20} color="#fff" />
            <Text style={localStyles.exportButtonText}>
              Exportar p/ Orçamento
            </Text>
          </TouchableOpacity>
        )}
      </View>

      {loading ? (
        <ActivityIndicator
          size="large"
          color="#10a2a7"
          style={localStyles.loading}
        />
      ) : (
        <FlatList
          data={itens}
          keyExtractor={(item) => item.item_id?.toString()}
          renderItem={({ item }) => (
            <ItemVisitaCard
              item={item}
              onEdit={editarItem}
              onDelete={excluirItem}
            />
          )}
          ListEmptyComponent={
            <Text style={localStyles.emptyText}>Nenhum item adicionado</Text>
          }
          showsVerticalScrollIndicator={false}
        />
      )}

      {/* Modal seguindo padrão do projeto */}
      <Modal
        visible={modalVisible}
        animationType="slide"
        transparent={true}
        onRequestClose={() => {
          setModalVisible(false)
          resetForm()
        }}>
        <View style={localStyles.modalContainer}>
          <View style={localStyles.modalContent}>
            <View style={localStyles.modalHeader}>
              <Text style={localStyles.modalTitle}>
                {editingItem ? 'Editar Item' : 'Adicionar Item'}
              </Text>
              <TouchableOpacity
                onPress={() => {
                  setModalVisible(false)
                  resetForm()
                }}
                style={localStyles.closeButton}>
                <Ionicons name="close" size={24} color="#10a2a7" />
              </TouchableOpacity>
            </View>

            <ScrollView
              style={localStyles.scrollContent}
              showsVerticalScrollIndicator={false}>
              {/* Seletor de tipo */}
              <View style={localStyles.tipoSelector}>
                <TouchableOpacity
                  style={[
                    localStyles.tipoButton,
                    tipoItem === 'produto' && localStyles.tipoButtonActive,
                  ]}
                  onPress={() => {
                    setTipoItem('produto')
                    setItemForm({
                      ...itemForm,
                      item_prod: '',
                      item_unit: '',
                      item_codigo: '',
                    })
                  }}>
                  <Text
                    style={[
                      localStyles.tipoButtonText,
                      tipoItem === 'produto' &&
                        localStyles.tipoButtonTextActive,
                    ]}>
                    Produto
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[
                    localStyles.tipoButton,
                    tipoItem === 'servico' && localStyles.tipoButtonActive,
                  ]}
                  onPress={() => {
                    setTipoItem('servico')
                    setItemForm({
                      ...itemForm,
                      item_prod: '',
                      item_unit: '',
                      item_codigo: '',
                    })
                  }}>
                  <Text
                    style={[
                      localStyles.tipoButtonText,
                      tipoItem === 'servico' &&
                        localStyles.tipoButtonTextActive,
                    ]}>
                    Serviço
                  </Text>
                </TouchableOpacity>
              </View>

              {/* Campo de busca */}
              <View style={styles.fieldGroup}>
                <View style={styles.fieldIcon}>
                  <Ionicons name="search" size={20} color="#10a2a7" />
                </View>
                <View style={styles.fieldContent}>
                  <Text style={styles.fieldLabel}>
                    {tipoItem === 'produto'
                      ? 'Buscar Produto'
                      : 'Buscar Serviço'}
                  </Text>
                  {tipoItem === 'produto' ? (
                    <BuscaProdutoInput
                      onSelect={handleSelecionarProduto}
                      initialValue={itemForm.item_prod}
                    />
                  ) : (
                    <BuscaServicoInput
                      onSelect={handleSelecionarServico}
                      valorAtual={itemForm.item_prod}
                    />
                  )}
                </View>
              </View>

              {/* Descrição adicional */}
              <View style={styles.fieldGroup}>
                <View style={styles.fieldIcon}>
                  <Ionicons name="document-text" size={20} color="#10a2a7" />
                </View>
                <View style={styles.fieldContent}>
                  <Text style={styles.fieldLabel}>Descrição Adicional</Text>
                  <TextInput
                    style={[styles.textInput, styles.textArea]}
                    placeholder="Descrição adicional do item"
                    placeholderTextColor="#666"
                    value={itemForm.item_desc_prod}
                    onChangeText={(text) =>
                      setItemForm({ ...itemForm, item_desc_prod: text })
                    }
                    multiline
                    numberOfLines={3}
                  />
                </View>
              </View>

              {/* Quantidade e Unidade */}
              <View style={localStyles.row}>
                <View style={[styles.fieldGroup, { flex: 1, marginRight: 8 }]}>
                  <View style={styles.fieldIcon}>
                    <Ionicons name="calculator" size={20} color="#10a2a7" />
                  </View>
                  <View style={styles.fieldContent}>
                    <Text style={styles.fieldLabel}>Quantidade *</Text>
                    <TextInput
                      style={styles.textInput}
                      placeholder="0"
                      placeholderTextColor="#666"
                      value={itemForm.item_quan}
                      onChangeText={(text) =>
                        setItemForm({ ...itemForm, item_quan: text })
                      }
                      keyboardType="numeric"
                    />
                  </View>
                </View>
                <View style={[styles.fieldGroup, { flex: 1, marginLeft: 8 }]}>
                  <View style={styles.fieldIcon}>
                    <Ionicons name="cube" size={20} color="#10a2a7" />
                  </View>
                  <View style={styles.fieldContent}>
                    <Text style={styles.fieldLabel}>Unidade</Text>
                    <TextInput
                      style={styles.textInput}
                      placeholder="UN"
                      placeholderTextColor="#666"
                      value={itemForm.item_unli}
                      onChangeText={(text) =>
                        setItemForm({ ...itemForm, item_unli: text })
                      }
                    />
                  </View>
                </View>
              </View>

              {/* Valor e Desconto */}
              <View style={localStyles.row}>
                <View style={[styles.fieldGroup, { flex: 1, marginRight: 8 }]}>
                  <View style={styles.fieldIcon}>
                    <Ionicons name="cash" size={20} color="#10a2a7" />
                  </View>
                  <View style={styles.fieldContent}>
                    <Text style={styles.fieldLabel}>Valor Unitário *</Text>
                    <TextInput
                      style={styles.textInput}
                      placeholder="0,00"
                      placeholderTextColor="#666"
                      value={itemForm.item_unit}
                      onChangeText={(text) =>
                        setItemForm({ ...itemForm, item_unit: text })
                      }
                      keyboardType="numeric"
                    />
                  </View>
                </View>
                <View style={[styles.fieldGroup, { flex: 1, marginLeft: 8 }]}>
                  <View style={styles.fieldIcon}>
                    <Ionicons name="pricetag" size={20} color="#10a2a7" />
                  </View>
                  <View style={styles.fieldContent}>
                    <Text style={styles.fieldLabel}>Desconto (%)</Text>
                    <TextInput
                      style={styles.textInput}
                      placeholder="0"
                      placeholderTextColor="#666"
                      value={itemForm.item_desc}
                      onChangeText={(text) =>
                        setItemForm({ ...itemForm, item_desc: text })
                      }
                      keyboardType="numeric"
                    />
                  </View>
                </View>
              </View>

              {/* Observações */}
              <View style={styles.fieldGroup}>
                <View style={styles.fieldIcon}>
                  <Ionicons name="chatbox" size={20} color="#10a2a7" />
                </View>
                <View style={styles.fieldContent}>
                  <Text style={styles.fieldLabel}>Observações</Text>
                  <TextInput
                    style={[styles.textInput, styles.textArea]}
                    placeholder="Observações sobre o item"
                    placeholderTextColor="#666"
                    value={itemForm.item_obse}
                    onChangeText={(text) =>
                      setItemForm({ ...itemForm, item_obse: text })
                    }
                    multiline
                    numberOfLines={2}
                  />
                </View>
              </View>
            </ScrollView>

            {/* Botões do modal */}
            <View style={localStyles.modalButtons}>
              <TouchableOpacity
                style={localStyles.modalButtonCancel}
                onPress={() => {
                  setModalVisible(false)
                  resetForm()
                }}>
                <Text style={localStyles.modalButtonCancelText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={localStyles.modalButtonSave}
                onPress={salvarItem}>
                <Text style={localStyles.modalButtonSaveText}>
                  {editingItem ? 'Atualizar' : 'Adicionar'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  )
}

// Estilos locais seguindo o padrão do projeto
const localStyles = {
  headerItens: {
    marginBottom: 20,
  },
  valorTotal: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#10a2a7',
    textAlign: 'center',
    marginTop: 8,
  },
  actionsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  addButton: {
    backgroundColor: '#10a2a7',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 12,
    flex: 1,
    marginRight: 8,
    justifyContent: 'center',
  },
  addButtonText: {
    color: '#fff',
    fontWeight: '600',
    marginLeft: 8,
  },
  exportButton: {
    backgroundColor: '#e67e22',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 12,
    flex: 1,
    marginLeft: 8,
    justifyContent: 'center',
  },
  exportButtonText: {
    color: '#fff',
    fontWeight: '600',
    marginLeft: 8,
  },
  loading: {
    marginVertical: 40,
  },
  emptyText: {
    color: '#666',
    fontSize: 16,
    textAlign: 'center',
    marginVertical: 40,
  },
  // Novos estilos para os itens da lista
  itemCard: {
    backgroundColor: '#1a252f',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#2a3441',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  itemProduto: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    flex: 1,
    marginRight: 12,
  },
  itemDescricao: {
    fontSize: 14,
    color: '#ccc',
    marginBottom: 12,
    fontStyle: 'italic',
  },
  itemDetalhes: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  itemQuantidade: {
    fontSize: 14,
    color: '#10a2a7',
    fontWeight: '600',
  },
  itemUnidade: {
    fontSize: 14,
    color: '#10a2a7',
    fontWeight: '600',
  },
  itemValor: {
    fontSize: 14,
    color: '#e67e22',
    fontWeight: '600',
  },
  itemTotal: {
    fontSize: 16,
    color: '#27ae60',
    fontWeight: 'bold',
  },
  itemActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  editButton: {
    backgroundColor: '#3498db',
    borderRadius: 8,
    padding: 8,
    marginRight: 8,
  },
  deleteButton: {
    backgroundColor: '#e74c3c',
    borderRadius: 8,
    padding: 8,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#232935',
    borderRadius: 16,
    maxHeight: '90%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#2a3441',
  },
  modalTitle: {
    color: '#10a2a7',
    fontSize: 20,
    fontWeight: 'bold',
  },
  closeButton: {
    padding: 4,
  },
  scrollContent: {
    padding: 20,
  },
  tipoSelector: {
    flexDirection: 'row',
    marginBottom: 20,
    backgroundColor: '#1a252f',
    borderRadius: 12,
    padding: 4,
  },
  tipoButton: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderRadius: 8,
  },
  tipoButtonActive: {
    backgroundColor: '#10a2a7',
  },
  tipoButtonText: {
    color: '#666',
    fontWeight: '600',
  },
  tipoButtonTextActive: {
    color: '#fff',
  },
  row: {
    flexDirection: 'row',
  },
  modalButtons: {
    flexDirection: 'row',
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#2a3441',
  },
  modalButtonCancel: {
    flex: 1,
    backgroundColor: '#666',
    paddingVertical: 14,
    borderRadius: 12,
    marginRight: 8,
    alignItems: 'center',
  },
  modalButtonCancelText: {
    color: '#fff',
    fontWeight: '600',
  },
  modalButtonSave: {
    flex: 1,
    backgroundColor: '#10a2a7',
    paddingVertical: 14,
    borderRadius: 12,
    marginLeft: 8,
    alignItems: 'center',
  },
  modalButtonSaveText: {
    color: '#fff',
    fontWeight: '600',
  },
}
