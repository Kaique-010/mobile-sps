// FilaSync.js
import { Model } from '@nozbe/watermelondb'

class FilaSync extends Model {
  static table = 'fila_sincronizacao'

  get acao() {
    return this._getRaw('acao')
  }
  set acao(value) {
    this._setRaw('acao', value)
  }

  get tabelaAlvo() {
    return this._getRaw('tabela_alvo')
  }
  set tabelaAlvo(value) {
    this._setRaw('tabela_alvo', value)
  }

  get registroIdLocal() {
    return this._getRaw('registro_id_local')
  }
  set registroIdLocal(value) {
    this._setRaw('registro_id_local', value)
  }

  get payloadJson() {
    return this._getRaw('payload_json')
  }
  set payloadJson(value) {
    this._setRaw('payload_json', value)
  }

  get tentativas() {
    return this._getRaw('tentativas')
  }
  set tentativas(value) {
    this._setRaw('tentativas', value)
  }

  get criadoEm() {
    return this._getRaw('criado_em')
  }
  set criadoEm(value) {
    this._setRaw('criado_em', value)
  }

  // Método auxiliar para desserializar o JSON
  get payload() {
    try {
      return JSON.parse(this.payloadJson)
    } catch (e) {
      console.error('Erro ao desserializar payload:', e)
      return null
    }
  }
}
export default FilaSync
