from decimal import Decimal


class ElotechXmlBuilder:
    SOAP_ENV_NS = 'http://schemas.xmlsoap.org/soap/envelope/'

    def montar_envelope_soap(self, xml_interno: str) -> str:
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{self.SOAP_ENV_NS}">
    <soapenv:Header/>
    <soapenv:Body>
        {xml_interno}
    </soapenv:Body>
</soapenv:Envelope>'''

    def montar_xml_emissao(self, data: dict) -> str:
        itens_xml = self._montar_itens_xml(data.get('itens') or [])

        return f'''
<emitirNfseRequest>
    <prestadorDocumento>{self._escape(data.get("prestador_documento"))}</prestadorDocumento>
    <prestadorNome>{self._escape(data.get("prestador_nome"))}</prestadorNome>
    <municipioCodigo>{self._escape(data.get("municipio_codigo"))}</municipioCodigo>

    <rpsNumero>{self._escape(data.get("rps_numero"))}</rpsNumero>
    <rpsSerie>{self._escape(data.get("rps_serie"))}</rpsSerie>

    <tomadorDocumento>{self._escape(data.get("tomador_documento"))}</tomadorDocumento>
    <tomadorNome>{self._escape(data.get("tomador_nome"))}</tomadorNome>
    <tomadorEmail>{self._escape(data.get("tomador_email"))}</tomadorEmail>
    <tomadorTelefone>{self._escape(data.get("tomador_telefone"))}</tomadorTelefone>
    <tomadorEndereco>{self._escape(data.get("tomador_endereco"))}</tomadorEndereco>
    <tomadorNumero>{self._escape(data.get("tomador_numero"))}</tomadorNumero>
    <tomadorBairro>{self._escape(data.get("tomador_bairro"))}</tomadorBairro>
    <tomadorCep>{self._escape(data.get("tomador_cep"))}</tomadorCep>
    <tomadorCidade>{self._escape(data.get("tomador_cidade"))}</tomadorCidade>
    <tomadorUf>{self._escape(data.get("tomador_uf"))}</tomadorUf>
    <tomadorIe>{self._escape(data.get("tomador_ie"))}</tomadorIe>
    <tomadorIm>{self._escape(data.get("tomador_im"))}</tomadorIm>

    <servicoCodigo>{self._escape(data.get("servico_codigo"))}</servicoCodigo>
    <servicoDescricao>{self._escape(data.get("servico_descricao"))}</servicoDescricao>
    <cnaeCodigo>{self._escape(data.get("cnae_codigo"))}</cnaeCodigo>
    <lc116Codigo>{self._escape(data.get("lc116_codigo"))}</lc116Codigo>
    <naturezaOperacao>{self._escape(data.get("natureza_operacao"))}</naturezaOperacao>
    <municipioIncidencia>{self._escape(data.get("municipio_incidencia"))}</municipioIncidencia>
    <municipioServico>{self._escape(data.get("municipio_servico"))}</municipioServico>

    <valorServico>{self._fmt_decimal(data.get("valor_servico"))}</valorServico>
    <valorDeducao>{self._fmt_decimal(data.get("valor_deducao"))}</valorDeducao>
    <valorDesconto>{self._fmt_decimal(data.get("valor_desconto"))}</valorDesconto>
    <valorInss>{self._fmt_decimal(data.get("valor_inss"))}</valorInss>
    <valorIrrf>{self._fmt_decimal(data.get("valor_irrf"))}</valorIrrf>
    <valorCsll>{self._fmt_decimal(data.get("valor_csll"))}</valorCsll>
    <valorCofins>{self._fmt_decimal(data.get("valor_cofins"))}</valorCofins>
    <valorPis>{self._fmt_decimal(data.get("valor_pis"))}</valorPis>
    <valorIss>{self._fmt_decimal(data.get("valor_iss"))}</valorIss>
    <valorLiquido>{self._fmt_decimal(data.get("valor_liquido"))}</valorLiquido>
    <aliquotaIss>{self._fmt_decimal(data.get("aliquota_iss"), places=4)}</aliquotaIss>
    <issRetido>{self._fmt_bool(data.get("iss_retido"))}</issRetido>

    <itens>
        {itens_xml}
    </itens>
</emitirNfseRequest>
'''.strip()

    def montar_xml_consulta(self, data: dict) -> str:
        return f'''
<consultarNfseRequest>
    <numero>{self._escape(data.get("numero"))}</numero>
    <protocolo>{self._escape(data.get("protocolo"))}</protocolo>
    <rpsNumero>{self._escape(data.get("rps_numero"))}</rpsNumero>
    <rpsSerie>{self._escape(data.get("rps_serie"))}</rpsSerie>
</consultarNfseRequest>
'''.strip()

    def montar_xml_cancelamento(self, data: dict) -> str:
        return f'''
<cancelarNfseRequest>
    <numero>{self._escape(data.get("numero"))}</numero>
    <codigoVerificacao>{self._escape(data.get("codigo_verificacao"))}</codigoVerificacao>
    <motivo>{self._escape(data.get("motivo"))}</motivo>
</cancelarNfseRequest>
'''.strip()

    def _montar_itens_xml(self, itens: list[dict]) -> str:
        partes = []

        for item in itens:
            partes.append(f'''
<item>
    <descricao>{self._escape(item.get("descricao"))}</descricao>
    <quantidade>{self._fmt_decimal(item.get("quantidade"), places=4)}</quantidade>
    <valorUnitario>{self._fmt_decimal(item.get("valor_unitario"), places=6)}</valorUnitario>
    <valorTotal>{self._fmt_decimal(item.get("valor_total"))}</valorTotal>
    <servicoCodigo>{self._escape(item.get("servico_codigo"))}</servicoCodigo>
    <cnaeCodigo>{self._escape(item.get("cnae_codigo"))}</cnaeCodigo>
    <lc116Codigo>{self._escape(item.get("lc116_codigo"))}</lc116Codigo>
</item>
'''.strip())

        return '\n'.join(partes)

    def _escape(self, value) -> str:
        if value in [None, '']:
            return ''
        texto = str(value)
        return (
            texto.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;')
        )

    def _fmt_decimal(self, value, places: int = 2) -> str:
        if value in [None, '']:
            value = Decimal('0')
        value = Decimal(str(value))
        return f'{value:.{places}f}'

    def _fmt_bool(self, value) -> str:
        return 'true' if bool(value) else 'false'