CREATE INDEX idx_ordemservico_empr_fili_orde ON ordemservico (orde_empr, orde_fili, orde_nume);
CREATE INDEX idx_ordemservicopecas_empr_fili_orde ON ordemservicopecas (peca_empr, peca_fili, peca_orde);
CREATE INDEX idx_ordemservicoservicos_empr_fili_orde ON ordemservicoservicos (serv_empr, serv_fili, serv_orde);
CREATE INDEX idx_historico_workflow_empr_fili_orde ON historico_workflow (hist_empr, hist_fili, hist_orde);
