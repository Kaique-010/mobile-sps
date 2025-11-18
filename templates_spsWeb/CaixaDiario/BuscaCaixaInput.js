import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  TextInput,
  FlatList,
  TouchableOpacity,
  Text,
  View,
  Keyboard,
  ActivityIndicator,
} from 'react-native'
import { apiGet } from '../utils/api'
import { getStoredData } from '../services/storageService'
import styles from '../styles/listaStyles'
import debounce from 'lodash/debounce'

export default function BuscaCaixa({
  onSelect,
  placeholder = 'Buscar Caixas...',
  tipo = '',
  value = '',
  isEdit = false,
}) {
  const [termo, setTermo] = useState(typeof value === 'string' ? value : '')
  const [caixa, setCaixa] = useState([])
  const [slug, setSlug] = useState('')
  const [loading, setLoading] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const digitando = useRef(false)

  const buscar = useCallback(
    debounce(async (texto) => {
      if (!slug || !texto || texto.length < 3) {
        setCaixa([])
        setLoading(false)
        return
      }

      setLoading(true)

      try {
        const { results } = await apiGetComContexto('entidades/entidades/', {
          search: texto,
        }, 'enti_')

        let resultadosFiltrados = results
        if (tipo === 'caixa') {
          resultadosFiltrados = resultadosFiltrados.filter(
            (e) => e.enti_tipo_enti === ''
          )
        }

        setCaixa(resultadosFiltrados)
        setShowResults(true)
      } catch (err) {
        console.error('Erro ao buscar entidades:', err.message)
      } finally {
        setLoading(false)
      }
    }, 800),
    [slug, tipo]
  )

  const handleSearch = () => {
    if (termo.length >= 3) {
      buscar(termo)
    }
  }

  useEffect(() => {
    getStoredData()
      .then(({ slug }) => slug && setSlug(slug))
      .catch((err) => console.error('Erro ao carregar slug:', err.message))
  }, [])

  useEffect(() => {
    if (!slug) return

    if (isEdit || (!digitando.current && value)) {
      const deveBuscar =
        typeof value === 'string' && value && !value.includes(' - ')
      if (deveBuscar) buscar(value)
      else if (typeof value === 'string') setTermo(value)
    }

    if (!value) {
      setTermo('')
      setCaixa([])
      setShowResults(false)
    }
  }, [value, isEdit, slug])

  const selecionar = (item) => {
    const texto = `${item.enti_clie} - ${item.enti_nome}`
    setTermo(texto)
    digitando.current = false

    onSelect({
      id: item.enti_clie,
      ...item,
    })

    setCaixa([])
    setShowResults(false)
    Keyboard.dismiss()
  }

  const isSelecionado =
    typeof termo === 'string' && termo.includes(' - ') && caixa.length === 0

  return (
    <View>
      <View style={styles.inputContainer}>
        <TextInput
          style={[
            styles.inputcliente,
            isSelecionado ? styles.inputSelecionado : null,
          ]}
          value={termo}
          editable={!isSelecionado}
          onChangeText={(text) => {
            setTermo(text)
            digitando.current = true
          }}
          onSubmitEditing={handleSearch}
          returnKeyType="search"
          placeholder={placeholder}
          placeholderTextColor="#aaa"
          onFocus={() => setShowResults(true)}
        />
        <TouchableOpacity
          onPress={handleSearch}
          style={styles.searchButton}
          disabled={loading || termo.length < 3}>
          {loading ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.searchButtonText}>Buscar</Text>
          )}
        </TouchableOpacity>
      </View>

      {showResults && caixa.length > 0 && (
        <FlatList
          data={caixa}
          keyExtractor={(item) =>
            `${item.enti_clie}-${item.enti_fili}-${item.enti_empr}`
          }
          keyboardShouldPersistTaps="handled"
          renderItem={({ item }) => (
            <TouchableOpacity
              onPress={() => selecionar(item)}
              style={styles.sugestaoItem}>
              <Text style={styles.sugestaoTexto}>
                {item.enti_clie} - {item.enti_nome}
              </Text>
            </TouchableOpacity>
          )}
          style={styles.sugestaoLista}
        />
      )}
    </View>
  )
}
