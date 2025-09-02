import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
  Switch,
  ActivityIndicator,
  StyleSheet,
} from 'react-native'
import { parametrosStyles } from './styles/parametrosStyle'

import { Feather } from '@expo/vector-icons'

const Parametros = ({ navigation }) => {
  const [parametrosVendas, setParametrosVendas] = useState({})
  const [parametrosCompras, setParametrosCompras] = useState({})
  const [parametrosEstoque, setParametrosEstoque] = useState({})
  const [parametrosFinanceiro, setParametrosFinanceiro] = useState({})
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [empresaId, setEmpresaId] = useState('')
  const [filialId, setFilialId] = useState('')

  const carregarDados = () => {
    // Add your data loading logic here
    setLoading(false)
  }

  useEffect(() => {
    carregarDados()
  }, [])

  return (
    <View style={parametrosStyles.container}>
      <TouchableOpacity
        style={parametrosStyles.button}
        onPress={() => navigation.navigate('ParametrosVendas')}>
        <Feather name="arrow-left" size={24} color="white" />
        <Text style={parametrosStyles.buttonText}>Parâmetros de Vendas</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={parametrosStyles.button}
        onPress={() => navigation.navigate('ParametrosCompras')}>
        <Feather name="arrow-left" size={24} color="white" />
        <Text style={parametrosStyles.buttonText}>Parâmetros de Compras</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={parametrosStyles.button}
        onPress={() => navigation.navigate('ParametrosEstoque')}>
        <Feather name="arrow-left" size={24} color="white" />
        <Text style={parametrosStyles.buttonText}>Parâmetros de Estoque</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={parametrosStyles.button}
        onPress={() => navigation.navigate('ParametrosFinanceiro')}>
        <Feather name="arrow-left" size={24} color="white" />
        <Text style={parametrosStyles.buttonText}>Parâmetros Financeiro</Text>
      </TouchableOpacity>
    </View>
  )
}

export default Parametros
