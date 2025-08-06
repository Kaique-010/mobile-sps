CREATE TABLE notificacoes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(usua_codi) ON DELETE CASCADE,
    titulo VARCHAR(100) NOT NULL,
    mensagem TEXT NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    lida BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_notificacao_usuario_data ON notificacoes(usuario_id, data_criacao DESC);
CREATE INDEX idx_notificacao_tipo_data ON notificacoes(tipo, data_criacao DESC);
CREATE INDEX idx_notificacao_lida ON notificacoes(lida, data_criacao DESC);
