# Novos parâmetros do sistema
PARAMETROS_SISTEMA = {
    'SISTEMA': {
        'sistema_nome': {'default': 'Sistema SPS', 'tipo': 'string', 'desc': 'Nome do sistema'},
        'versao': {'default': '1.0.0', 'tipo': 'string', 'desc': 'Versão do sistema'},
        'manutencao': {'default': 'false', 'tipo': 'boolean', 'desc': 'Modo manutenção'}
    },
    'BACKUP': {
        'backup_automatico': {'default': 'true', 'tipo': 'boolean', 'desc': 'Backup automático'},
        'dias_backup': {'default': '7', 'tipo': 'integer', 'desc': 'Dias para manter backup'}
    },
    'NOTIFICACOES': {
        'email_ativo': {'default': 'true', 'tipo': 'boolean', 'desc': 'Notificações por email'},
        'sms_ativo': {'default': 'false', 'tipo': 'boolean', 'desc': 'Notificações por SMS'}
    }
}