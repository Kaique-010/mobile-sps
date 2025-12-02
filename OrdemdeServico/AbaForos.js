import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  FlatList,
  Image,
  StyleSheet,
} from 'react-native'
import { Modal, Linking, Platform } from 'react-native'
import {
  tirarFotoComGeo,
  enviarFotoEtapa,
  fetchFotos,
} from '../services/fotosApi'
import { BASE_URL, getAuthHeaders } from '../utils/api'
import AsyncStorage from '@react-native-async-storage/async-storage'

const etapas = [
  { key: 'antes', label: 'Antes' },
  { key: 'durante', label: 'Durante' },
  { key: 'depois', label: 'Depois' },
]

export default function AbaForos({ orde_nume, codTecnico }) {
  const [subAba, setSubAba] = useState('antes')
  const [fotos, setFotos] = useState([])
  const [modalVisible, setModalVisible] = useState(false)
  const [imagemSelecionada, setImagemSelecionada] = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [slug, setSlug] = useState('')
  const [authHeaders, setAuthHeaders] = useState(null)
  const [secureSources, setSecureSources] = useState({})

  useEffect(() => {
    const getSlug = async () => {
      const storedSlug = await AsyncStorage.getItem('slug')
      setSlug(storedSlug || '')
    }
    getSlug()
  }, [])

  useEffect(() => {
    const loadAuth = async () => {
      const headers = await getAuthHeaders()
      const token = await AsyncStorage.getItem('access')
      setAuthHeaders({ Authorization: `Bearer ${token}`, ...headers })
    }
    loadAuth()
  }, [])

  useEffect(() => {
    if (orde_nume && slug) {
      loadFotos()
    }
  }, [subAba, orde_nume, slug])

  const loadFotos = async () => {
    try {
      const res = await fetchFotos(subAba, orde_nume)
      if (res && res.length > 0) {
      }

      setFotos(res)
    } catch (error) {
      console.error(`❌ Erro ao carregar fotos da etapa ${subAba}:`, error)
      setFotos([])
    }
  }

  const handleAdd = async () => {
    setIsUploading(true)
    try {
      const data = await tirarFotoComGeo()
      const result = await enviarFotoEtapa({
        etapa: subAba,
        ordemId: orde_nume,
        codTecnico,
        observacao: '',
        data,
      })
      await loadFotos()
    } catch (error) {
      console.error('❌ Erro ao adicionar foto:', error)
      alert(`Erro ao adicionar foto: ${error}`)
    } finally {
      setIsUploading(false)
    }
  }

  const getImageId = (item) => {
    let imageId
    if (subAba === 'antes') {
      imageId = item.iman_id || item.id
    } else if (subAba === 'durante') {
      imageId = item.imdu_id || item.id
    } else if (subAba === 'depois') {
      imageId = item.imde_id || item.id
    } else {
      imageId = item.id
    }
    return imageId
  }

  const openImage = (item) => {
    const imageId = getImageId(item)
    let uri

    if (item.imagem_data_uri) {
      uri = item.imagem_data_uri
    } else if (item.imagem_base64) {
      uri = `data:image/jpeg;base64,${item.imagem_base64}`
    } else {
      const directUri = `${BASE_URL}/api/${slug}/ordemdeservico/imagens-${subAba}/${orde_nume}/${imageId}/bin/`
      if (secureSources[imageId]) {
        uri = secureSources[imageId]
      } else {
        uri = directUri
      }
    }

    if (Platform.OS === 'web' && uri && uri.startsWith('http')) {
      setImagemSelecionada([{ uri: secureSources[imageId] || uri }, item])
    } else if (authHeaders && uri && uri.startsWith('http')) {
      setImagemSelecionada([{ uri, headers: authHeaders }, item])
    } else {
      setImagemSelecionada([{ uri }, item])
    }
    setModalVisible(true)
  }

  const loadSecureImage = async (imageId, imageUri) => {
    try {
      const headers = await getAuthHeaders()
      const token = await AsyncStorage.getItem('access')
      const res = await fetch(imageUri, {
        headers: { Authorization: `Bearer ${token}`, ...headers },
      })
      const blob = await res.blob()
      const reader = new FileReader()
      reader.onloadend = () => {
        setSecureSources((prev) => ({ ...prev, [imageId]: reader.result }))
      }
      reader.readAsDataURL(blob)
    } catch (e) {
      console.error('Erro ao carregar imagem segura:', e)
    }
  }

  const renderItem = ({ item }) => {
    const imageId = getImageId(item)
    let imageSource
    if (item.imagem_data_uri) {
      imageSource = { uri: item.imagem_data_uri }
    } else if (item.imagem_base64) {
      imageSource = { uri: `data:image/jpeg;base64,${item.imagem_base64}` }
    } else {
      const imageUri = `${BASE_URL}/api/${slug}/ordemdeservico/imagens-${subAba}/${orde_nume}/${imageId}/bin/`
      if (secureSources[imageId]) {
        imageSource = { uri: secureSources[imageId] }
      } else if (Platform.OS === 'web') {
        imageSource = { uri: imageUri }
      } else if (authHeaders) {
        imageSource = { uri: imageUri, headers: authHeaders }
      } else {
        imageSource = { uri: imageUri }
      }
    }

    return (
      <TouchableOpacity onPress={() => openImage(item)}>
        <Image
          source={imageSource}
          style={styles.thumb}
          onError={(error) => {
            console.error(`❌ Erro ao carregar imagem ${imageId}:`, error)
            console.error(`❌ Source usado:`, imageSource)
            console.error(`❌ Item completo:`, item)
            const fallbackUri = `${BASE_URL}/api/${slug}/ordemdeservico/imagens-${subAba}/${orde_nume}/${imageId}/bin/`
            loadSecureImage(imageId, fallbackUri)
          }}
          onLoad={() => {}}
          onLoadStart={() => {}}
        />
        <Text style={styles.debugText}>ID: {imageId}</Text>
      </TouchableOpacity>
    )
  }

  return (
    <View style={styles.container}>
      {/* Sub-abas */}
      <View style={styles.tabs}>
        {etapas.map((e) => (
          <TouchableOpacity
            key={e.key}
            style={[styles.tab, subAba === e.key && styles.activeTab]}
            onPress={() => setSubAba(e.key)}>
            <Text style={styles.tabText}>{e.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Lista de miniaturas */}
      {fotos.length > 0 ? (
        <FlatList
          data={fotos}
          keyExtractor={(item) => {
            const imageId = getImageId(item)
            return `${subAba}-${imageId}`
          }}
          renderItem={renderItem}
          numColumns={3}
          nestedScrollEnabled={true}
          contentContainerStyle={{ padding: 8 }}
        />
      ) : (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>
            Nenhuma foto encontrada para a etapa{' '}
            {etapas.find((e) => e.key === subAba)?.label}
          </Text>
        </View>
      )}
      <TouchableOpacity style={styles.addButton} onPress={handleAdd}>
        <Text style={styles.addText}>
          + Foto {etapas.find((e) => e.key === subAba).label}
        </Text>
      </TouchableOpacity>
      <Modal visible={modalVisible} transparent={true} animationType="slide">
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <Image
              source={imagemSelecionada[0]}
              style={styles.modalImage}
              resizeMode="contain"
            />

            <Text style={styles.obsText}>
              📝 {imagemSelecionada[1]?.observacao || 'Sem observação'}
            </Text>

            <Text style={styles.coordText}>
              📍 {imagemSelecionada[1]?.img_latitude || '---'} |{' '}
              {imagemSelecionada[1]?.img_longitude || '---'}
            </Text>

            {imagemSelecionada[1]?.img_latitude &&
              imagemSelecionada[1]?.img_longitude && (
                <TouchableOpacity
                  style={styles.mapButton}
                  onPress={() =>
                    Linking.openURL(
                      `https://www.google.com/maps?q=${imagemSelecionada[1].img_latitude},${imagemSelecionada[1].img_longitude}`
                    )
                  }>
                  <Text style={styles.mapText}>Ver no Mapa</Text>
                </TouchableOpacity>
              )}

            <TouchableOpacity onPress={() => setModalVisible(false)}>
              <Text style={{ color: '#aaa', marginTop: 12 }}>Fechar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  tabs: { flexDirection: 'row', marginVertical: 8 },
  tab: {
    flex: 1,
    padding: 12,
    backgroundColor: '#1a2f3d',
    alignItems: 'center',
    borderRadius: 4,
    marginHorizontal: 2,
  },
  activeTab: { backgroundColor: '#10a2a7' },
  tabText: {
    fontWeight: 'bold',
    color: '#fff',
  },
  thumb: {
    width: 100,
    height: 100,
    margin: 4,
    borderRadius: 8,
    backgroundColor: '#1a2f3d',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  emptyText: {
    color: '#fff',
    fontSize: 16,
    textAlign: 'center',
    opacity: 0.7,
  },
  addButton: {
    padding: 15,
    backgroundColor: '#10a2a7',
    alignItems: 'center',
    margin: 16,
    borderRadius: 8,
    marginBottom: 50,
  },
  addText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
  debugText: {
    color: '#10a2a7',
    fontSize: 10,
    textAlign: 'center',
    marginTop: 2,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
    maxWidth: '90%',
    maxHeight: '90%',
  },
  modalImage: {
    width: 250,
    height: 250,
    marginBottom: 12,
    borderRadius: 8,
  },
  obsText: {
    fontSize: 14,
    marginBottom: 6,
    color: '#222',
  },
  coordText: {
    fontSize: 13,
    color: '#444',
    marginBottom: 10,
  },
  mapButton: {
    padding: 10,
    backgroundColor: '#10a2a7',
    borderRadius: 6,
  },
  mapText: {
    color: '#fff',
    fontWeight: 'bold',
  },
})
