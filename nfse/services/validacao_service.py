from decimal import Decimal

from django.core.exceptions import ValidationError


class ValidacaoNfseService:
    @staticmethod
    def validar_payload(data: dict):
        erros = {}

        ValidacaoNfseService._validar_campos_obrigatorios(data, erros)
        ValidacaoNfseService._validar_valores(data, erros)
        ValidacaoNfseService._validar_itens(data, erros)
        ValidacaoNfseService._validar_regra_ponta_grossa(data, erros)

        if erros:
            raise ValidationError(erros)

    @staticmethod
    def _validar_campos_obrigatorios(data: dict, erros: dict):
        obrigatorios = {
            'municipio_codigo': 'Informe o município.',
            'rps_numero': 'Informe o número do RPS.',
            'prestador_documento': 'Informe o documento do prestador.',
            'prestador_nome': 'Informe o nome do prestador.',
            'servico_codigo': 'Informe o código do serviço.',
            'servico_descricao': 'Informe a descrição do serviço.',
        }

        for campo, mensagem in obrigatorios.items():
            valor = data.get(campo)
            if valor in [None, '', []]:
                erros[campo] = mensagem

    @staticmethod
    def _validar_valores(data: dict, erros: dict):
        valor_servico = Decimal(str(data.get('valor_servico') or 0))
        valor_iss = Decimal(str(data.get('valor_iss') or 0))
        valor_liquido = Decimal(str(data.get('valor_liquido') or 0))
        aliquota_iss = Decimal(str(data.get('aliquota_iss') or 0))

        if valor_servico <= 0:
            erros['valor_servico'] = 'O valor do serviço deve ser maior que zero.'

        if valor_iss < 0:
            erros['valor_iss'] = 'O valor do ISS não pode ser negativo.'

        if valor_liquido < 0:
            erros['valor_liquido'] = 'O valor líquido não pode ser negativo.'

        if aliquota_iss < 0:
            erros['aliquota_iss'] = 'A alíquota do ISS não pode ser negativa.'

        if valor_servico and valor_liquido and valor_liquido > valor_servico:
            erros['valor_liquido'] = 'O valor líquido não pode ser maior que o valor do serviço.'

    @staticmethod
    def _validar_itens(data: dict, erros: dict):
        itens = data.get('itens') or []
        if not itens:
            return

        erros_itens = []
        soma_itens = Decimal('0')

        for index, item in enumerate(itens):
            erro_item = {}

            descricao = item.get('descricao')
            quantidade = Decimal(str(item.get('quantidade') or 0))
            valor_unitario = Decimal(str(item.get('valor_unitario') or 0))
            valor_total = Decimal(str(item.get('valor_total') or 0))

            if not descricao:
                erro_item['descricao'] = 'Informe a descrição do item.'

            if quantidade <= 0:
                erro_item['quantidade'] = 'A quantidade deve ser maior que zero.'

            if valor_unitario < 0:
                erro_item['valor_unitario'] = 'O valor unitário não pode ser negativo.'

            if valor_total <= 0:
                erro_item['valor_total'] = 'O valor total do item deve ser maior que zero.'

            total_calculado = quantidade * valor_unitario
            if quantidade > 0 and valor_unitario >= 0 and valor_total > 0:
                if valor_total != total_calculado:
                    erro_item['valor_total'] = (
                        f'Valor total inválido no item {index + 1}. '
                        f'Esperado: {total_calculado}.'
                    )

            if erro_item:
                erros_itens.append({index: erro_item})
            else:
                soma_itens += valor_total

        if erros_itens:
            erros['itens'] = erros_itens
            return

        valor_servico = Decimal(str(data.get('valor_servico') or 0))
        if valor_servico > 0 and soma_itens != valor_servico:
            erros['valor_servico'] = (
                f'O valor do serviço ({valor_servico}) deve ser igual à soma dos itens ({soma_itens}).'
            )

    @staticmethod
    def _validar_regra_ponta_grossa(data: dict, erros: dict):
        municipio_codigo = str(data.get('municipio_codigo') or '')

        if municipio_codigo != '4119905':
            return

        # Regras mínimas para Ponta Grossa no teu primeiro adapter
        if not data.get('cnae_codigo'):
            erros['cnae_codigo'] = 'Informe o CNAE para emissão em Ponta Grossa.'

        if not data.get('lc116_codigo'):
            erros['lc116_codigo'] = 'Informe o código LC116 para emissão em Ponta Grossa.'

        tomador_documento = data.get('tomador_documento')
        tomador_nome = data.get('tomador_nome')

        if not tomador_nome:
            erros['tomador_nome'] = 'Informe o nome do tomador para emissão em Ponta Grossa.'

        if not tomador_documento:
            erros['tomador_documento'] = 'Informe o documento do tomador para emissão em Ponta Grossa.'