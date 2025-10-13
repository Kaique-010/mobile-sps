import React, { useState, useEffect } from 'react'
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native'
import { MaterialIcons } from '@expo/vector-icons'
import BuscaProdutosInput from '../components/BuscaProdutosInput'
import { apiGetComContexto, apiPostComContexto } from '../utils/api'

export default function ItensModalPisos({
  visible,
  onClose,
  onSave,
  item = null,
  pedido = {},
}) {
  const [produto, setProduto] = useState(null)
  const [quantidade, setQuantidade] = useState('')
  const [precoUnitario, setPrecoUnitario] = useState('')
  const [areaM2, setAreaM2] = useState('')
  const [observacoes, setObservacoes] = useState('')
  const [carregandoProduto, setCarregandoProduto] = useState(false)
  const [calculandoMetragem, setCalculandoMetragem] = useState(false)
  const [dadosCalculo, setDadosCalculo] = useState(null)
  const [quebra, setQuebra] = useState('0')
  const [condicaoPagamento, setCondicaoPagamento] = useState('0')

  useEffect(() => {
    if (item) {
      // Editando item existente
      setProduto({
        prod_codi: item.item_prod,
        prod_nome: item.produto_nome,
        prod_prec: item.item_unit,
      })
      setQuantidade(String(item.item_quan || ''))
      setPrecoUnitario(String(item.item_unit || ''))
      setAreaM2(String(item.area_m2 || ''))
      setObservacoes(item.observacoes || '')
    } else {
      // Novo item
      limparCampos()
    }
  }, [item, visible])

  const limparCampos = () => {
    setProduto(null)
    setQuantidade('')
    setPrecoUnitario('')
    setAreaM2('')
    setObservacoes('')
    setDadosCalculo(null)
    setQuebra('')
    setCondicaoPagamento('0')
  }

  const buscarDadosProduto = async (produtoSelecionado) => {
    if (!produtoSelecionado?.prod_codi) return

    setCarregandoProduto(true)
    try {
      // Corrigir: usar POST e enviar dados no body
      const response = await apiPostComContexto(
        'pisos/produtos-pisos/calcular_metragem/',
        {
          produto_id: produtoSelecionado.prod_codi,
          tamanho_m2: parseFloat(areaM2) || 0,
          percentual_quebra: parseFloat(quebra) || 0,
          cliente_id: pedido.pedi_clie,
          condicao: condicaoPagamento,
        }
      )

      if (response) {
        setProduto({
          ...produtoSelecionado,
          prod_prec: response.preco_unitario || produtoSelecionado.prod_prec,
        })
        setPrecoUnitario(
          String(response.preco_unitario || produtoSelecionado.prod_prec || '')
        )
      } else {
        setProduto(produtoSelecionado)
        setPrecoUnitario(String(produtoSelecionado.prod_prec || ''))
      }
    } catch (error) {
      console.error('Erro ao buscar dados do produto:', error)
      setProduto(produtoSelecionado)
      setPrecoUnitario(String(produtoSelecionado.prod_prec || ''))
    } finally {
      setCarregandoProduto(false)
    }
  }

  const calcularMetragem = async () => {
    if (!produto?.prod_codi || !areaM2 || !pedido?.pedi_clie) {
      Alert.alert(
        'Atenção',
        'Selecione um produto, informe a área e certifique-se de que há um cliente selecionado'
      )
      return
    }

    setCalculandoMetragem(true)
    try {
      // Corrigir: usar POST e enviar dados no body
      const response = await apiPostComContexto(
        'pisos/produtos-pisos/calcular_metragem/',
        {
          produto_id: produto.prod_codi,
          tamanho_m2: parseFloat(areaM2),
          percentual_quebra: parseFloat(quebra) || 0,
          cliente_id: pedido.pedi_clie,
          condicao: condicaoPagamento,
        }
      )

      if (response) {
        setDadosCalculo(response)
        const caixasCalc = Number(response.caixas_necessarias) || 0
        setQuantidade(String(caixasCalc))
        setPrecoUnitario(String(response.preco_unitario))
      }
    } catch (error) {
      console.error('Erro ao calcular metragem:', error)
      Alert.alert(
        'Erro',
        'Não foi possível calcular a metragem. Verifique os dados do produto.'
      )
    } finally {
      setCalculandoMetragem(false)
    }
  }

  const calcularTotal = () => {
    const preco = Number(precoUnitario) || 0
    // Quando houver dados de cálculo, calcular o total por m² (m2_por_caixa * caixas)
    if (dadosCalculo && (Number(dadosCalculo?.m2_por_caixa) || 0) > 0) {
      const m2PorCaixa = Number(dadosCalculo?.m2_por_caixa) || 0
      const caixas = Number(dadosCalculo?.caixas_necessarias) || 0
      const m2Total = m2PorCaixa * caixas
      return m2Total * preco
    }
    // Fallback: usar a área informada (m²) quando não houver cálculo de caixas
    const m2 = Number(areaM2) || 0
    return m2 * preco
  }

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(valor || 0)
  }

  const validarCampos = () => {
    if (!produto?.prod_codi) {
      Alert.alert('Erro', 'Selecione um produto')
      return false
    }
    if (!areaM2 || Number(areaM2) <= 0) {
      Alert.alert('Erro', 'Informe a metragem do ambiente (m²)')
      return false
    }
    if (!precoUnitario || Number(precoUnitario) < 0) {
      Alert.alert('Erro', 'Informe um preço unitário válido')
      return false
    }
    return true
  }

  const handleSalvar = () => {
    if (!validarCampos()) return

    // Determinar caixas a partir da metragem do ambiente quando houver dados de cálculo
    const caixasCalculadas = dadosCalculo
      ? Number(dadosCalculo?.caixas_necessarias) || 0
      : Number(quantidade) || 0

    const itemData = {
      // Campos obrigatórios do modelo
      item_empr: pedido.pedi_empr,
      item_fili: pedido.pedi_fili,
      item_pedi: pedido.pedi_nume || '0', // Usar '0' em vez de null
      item_prod: produto.prod_codi,

      // Campos existentes (mantendo compatibilidade)
      produto_nome: produto.prod_nome,
      // Quantidade será o número de caixas calculadas
      item_caix: caixasCalculadas,
      // Metragem (m²) informada pelo usuário deve ser preservada
      item_m2: Number(areaM2) || 0,
      // Quantidade em m² (se desejar usar como total de m2)
      item_quan: (Number(dadosCalculo?.m2_por_caixa) || 0) * caixasCalculadas,
      item_unit: Number(precoUnitario),
      item_suto: calcularTotal(),
      // Observações mapeadas para campo correto
      item_obse: observacoes.trim() || null,
      item_ambi: 1, // Campo obrigatório
      // Campos específicos para pisos
      produto_tipo: 'PISO',
      desconto_item_disponivel: false,
      percentual_desconto: 0,
      // Dados do cálculo se disponível
      dados_calculo: dadosCalculo,
    }

    onSave(itemData)
    onClose()
  }

  const handleFechar = () => {
    limparCampos()
    onClose()
  }

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={handleFechar}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <View style={styles.header}>
          <TouchableOpacity onPress={handleFechar} style={styles.closeButton}>
            <MaterialIcons name="close" size={24} color="#ff9999" />
          </TouchableOpacity>
          <Text style={styles.title}>
            {item ? 'Editar Item' : 'Adicionar Item'}
          </Text>
          <TouchableOpacity onPress={handleSalvar} style={styles.saveButton}>
            <MaterialIcons name="check" size={24} color="#a8e6cf" />
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Produto</Text>
            <BuscaProdutosInput
              value={produto}
              onSelect={buscarDadosProduto}
              placeholder="Buscar produto..."
              loading={carregandoProduto}
            />
          </View>

          {produto && (
            <>
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Cálculo de Metragem</Text>

                <View style={styles.calculoContainer}>
                  <View style={styles.fieldRow}>
                    <View style={styles.fieldContainer}>
                      <Text style={styles.label}>Área (m²) *</Text>
                      <TextInput
                        style={styles.input}
                        value={areaM2}
                        onChangeText={setAreaM2}
                        placeholder="0,00"
                        placeholderTextColor="#666"
                        keyboardType="numeric"
                      />
                    </View>

                    <View style={styles.fieldContainer}>
                      <Text style={styles.label}>Quebra (%)</Text>
                      <TextInput
                        style={styles.input}
                        value={quebra}
                        onChangeText={setQuebra}
                        placeholder="5"
                        placeholderTextColor="#666"
                        keyboardType="numeric"
                      />
                    </View>
                  </View>

                  <View style={styles.fieldContainer}>
                    <Text style={styles.label}>Condição de Pagamento</Text>
                    <View style={styles.condicaoContainer}>
                      <TouchableOpacity
                        style={[
                          styles.condicaoButton,
                          condicaoPagamento === '0' &&
                            styles.condicaoButtonAtiva,
                        ]}
                        onPress={() => setCondicaoPagamento('0')}>
                        <Text
                          style={[
                            styles.condicaoText,
                            condicaoPagamento === '0' &&
                              styles.condicaoTextAtiva,
                          ]}>
                          À Vista
                        </Text>
                      </TouchableOpacity>

                      <TouchableOpacity
                        style={[
                          styles.condicaoButton,
                          condicaoPagamento === '1' &&
                            styles.condicaoButtonAtiva,
                        ]}
                        onPress={() => setCondicaoPagamento('1')}>
                        <Text
                          style={[
                            styles.condicaoText,
                            condicaoPagamento === '1' &&
                              styles.condicaoTextAtiva,
                          ]}>
                          A Prazo
                        </Text>
                      </TouchableOpacity>
                    </View>
                  </View>

                  <TouchableOpacity
                    style={styles.botaoCalcular}
                    onPress={calcularMetragem}
                    disabled={calculandoMetragem}>
                    {calculandoMetragem ? (
                      <ActivityIndicator size="small" color="#0a0a0a" />
                    ) : (
                      <MaterialIcons
                        name="calculate"
                        size={20}
                        color="#0a0a0a"
                      />
                    )}
                    <Text style={styles.botaoCalcularTexto}>
                      {calculandoMetragem
                        ? 'Calculando...'
                        : 'Calcular Metragem'}
                    </Text>
                  </TouchableOpacity>
                </View>

                {dadosCalculo && (
                  <View style={styles.resultadoCalculo}>
                    <Text style={styles.resultadoTitulo}>
                      Resultado do Cálculo
                    </Text>

                    <View style={styles.resultadoItem}>
                      <Text style={styles.resultadoLabel}>Área real (com perda):</Text>
                      <Text style={styles.resultadoValor}>
                        {dadosCalculo?.metragem_total ?? '—'} m²
                      </Text>
                    </View>

                    <View style={styles.resultadoItem}>
                      <Text style={styles.resultadoLabel}>
                        Caixas necessárias:
                      </Text>
                      <Text style={styles.resultadoValor}>
                        {dadosCalculo?.caixas_necessarias}
                      </Text>
                    </View>

                    <View style={styles.resultadoItem}>
                      <Text style={styles.resultadoLabel}>Total de peças:</Text>
                      <Text style={styles.resultadoValor}>
                        {dadosCalculo?.pecas_necessarias}
                      </Text>
                    </View>

                    <View style={styles.resultadoItem}>
                      <Text style={styles.resultadoLabel}>Valor total:</Text>
                      <Text style={styles.resultadoValor}>
                        {formatarMoeda(dadosCalculo?.valor_total)}
                      </Text>
                    </View>
                  </View>
                )}
              </View>

              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Detalhes do Item</Text>

                <View style={styles.fieldContainer}>
                  <Text style={styles.label}>Quantidade de Caixas*</Text>
                  <TextInput
                    style={styles.input}
                    value={quantidade}
                    onChangeText={setQuantidade}
                    placeholder="0,00"
                    placeholderTextColor="#666"
                    keyboardType="numeric"
                  />
                </View>

                <View style={styles.fieldContainer}>
                  <Text style={styles.label}>Preço Unitário *</Text>
                  <TextInput
                    style={styles.input}
                    value={precoUnitario}
                    onChangeText={setPrecoUnitario}
                    placeholder="0,00"
                    placeholderTextColor="#666"
                    keyboardType="numeric"
                  />
                </View>

                <View style={styles.fieldContainer}>
                  <Text style={styles.label}>Observações</Text>
                  <TextInput
                    style={[styles.input, styles.textArea]}
                    value={observacoes}
                    onChangeText={setObservacoes}
                    placeholder="Observações sobre o item..."
                    placeholderTextColor="#666"
                    multiline
                    numberOfLines={3}
                  />
                </View>
              </View>
            </>
          )}

          {produto && quantidade && precoUnitario && (
            <View style={styles.totalContainer}>
              <Text style={styles.totalLabel}>Total do Item:</Text>
              <Text style={styles.totalValue}>
                {formatarMoeda(calcularTotal())}
              </Text>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </Modal>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  closeButton: {
    padding: 8,
  },
  title: {
    color: '#f5f5f5',
    fontSize: 18,
    fontWeight: '600',
    flex: 1,
    textAlign: 'center',
  },
  saveButton: {
    padding: 8,
  },
  content: {
    flex: 1,
    padding: 16,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    color: '#a8e6cf',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  calculoContainer: {
    backgroundColor: 'rgba(168, 230, 207, 0.05)',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(168, 230, 207, 0.3)',
  },
  fieldRow: {
    flexDirection: 'row',
    gap: 12,
  },
  fieldContainer: {
    flex: 1,
    marginBottom: 16,
  },
  label: {
    color: '#f5f5f5',
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#1a1a1a',
    borderColor: '#333',
    borderWidth: 1,
    borderRadius: 8,
    color: '#f5f5f5',
    fontSize: 16,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  condicaoContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  condicaoButton: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#333',
    backgroundColor: '#1a1a1a',
    alignItems: 'center',
  },
  condicaoButtonAtiva: {
    backgroundColor: 'rgba(168, 230, 207, 0.2)',
    borderColor: '#a8e6cf',
  },
  condicaoText: {
    color: '#f5f5f5',
    fontSize: 14,
    fontWeight: '500',
  },
  condicaoTextAtiva: {
    color: '#a8e6cf',
    fontWeight: '600',
  },
  botaoCalcular: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#a8e6cf',
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 8,
  },
  botaoCalcularTexto: {
    color: '#0a0a0a',
    fontWeight: '600',
    marginLeft: 8,
  },
  resultadoCalculo: {
    backgroundColor: 'rgba(168, 230, 207, 0.1)',
    borderRadius: 8,
    padding: 16,
    marginTop: 16,
    borderWidth: 1,
    borderColor: 'rgba(168, 230, 207, 0.3)',
  },
  resultadoTitulo: {
    color: '#a8e6cf',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  resultadoItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  resultadoLabel: {
    color: '#f5f5f5',
    fontSize: 14,
    fontWeight: '500',
  },
  resultadoValor: {
    color: '#a8e6cf',
    fontSize: 14,
    fontWeight: '600',
  },
  totalContainer: {
    backgroundColor: 'rgba(168, 230, 207, 0.1)',
    borderRadius: 8,
    padding: 16,
    marginTop: 16,
    borderWidth: 1,
    borderColor: '#a8e6cf',
  },
  totalLabel: {
    color: '#f5f5f5',
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 4,
  },
  totalValue: {
    color: '#a8e6cf',
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 30,
  },
})
