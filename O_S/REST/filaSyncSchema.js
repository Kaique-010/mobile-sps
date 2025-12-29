// filaSyncSchema.js
import { tableSchema } from '@nozbe/watermelondb'

const filaSyncSchema = tableSchema({
  name: 'fila_sincronizacao',
  columns: [
    // Ação a ser executada no backend (POST, PUT, DELETE)
    { name: 'acao', type: 'string', isIndexed: true },

    // Qual tipo de registro está sendo afetado (Ex: 'os_servico')
    { name: 'tabela_alvo', type: 'string' },

    // O ID LOCAL do registro afetado (para referência, se for uma edição/remoção)
    { name: 'registro_id_local', type: 'string', isIndexed: true },

    // O JSON COMPLETO dos dados a serem enviados para o endpoint do Django
    { name: 'payload_json', type: 'string' },

    // Contagem de tentativas de sincronização (para evitar loops infinitos)
    { name: 'tentativas', type: 'number' },

    // Timestamp para garantir a ordem de processamento (FIFO)
    { name: 'criado_em', type: 'number', isIndexed: true },

    // Colunas de rastreamento WatermelonDB
    { name: 'created_at', type: 'number' },
    { name: 'updated_at', type: 'number' },
  ],
})

export default filaSyncSchema
