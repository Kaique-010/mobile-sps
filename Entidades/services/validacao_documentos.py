import re

from django.core.exceptions import ValidationError


class DocumentoFiscalValidacaoServico:
    @staticmethod
    def somente_digitos(valor) -> str:
        return re.sub(r"\D", "", str(valor or "")).strip()

    @staticmethod
    def cpf_valido(valor) -> bool:
        cpf = DocumentoFiscalValidacaoServico.somente_digitos(valor)
        if len(cpf) != 11 or not cpf.isdigit():
            return False
        if cpf == cpf[0] * 11:
            return False

        soma = 0
        for i, peso in enumerate(range(10, 1, -1)):
            soma += int(cpf[i]) * peso
        dv1 = 11 - (soma % 11)
        dv1 = 0 if dv1 >= 10 else dv1
        if dv1 != int(cpf[9]):
            return False

        soma = 0
        for i, peso in enumerate(range(11, 1, -1)):
            soma += int(cpf[i]) * peso
        dv2 = 11 - (soma % 11)
        dv2 = 0 if dv2 >= 10 else dv2
        return dv2 == int(cpf[10])

    @staticmethod
    def cnpj_valido(valor) -> bool:
        cnpj = DocumentoFiscalValidacaoServico.somente_digitos(valor)
        if len(cnpj) != 14 or not cnpj.isdigit():
            return False
        if cnpj == cnpj[0] * 14:
            return False

        pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(cnpj[i]) * pesos_1[i] for i in range(12))
        dv1 = 11 - (soma % 11)
        dv1 = 0 if dv1 >= 10 else dv1
        if dv1 != int(cnpj[12]):
            return False

        pesos_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(cnpj[i]) * pesos_2[i] for i in range(13))
        dv2 = 11 - (soma % 11)
        dv2 = 0 if dv2 >= 10 else dv2
        return dv2 == int(cnpj[13])

    @staticmethod
    def validar_cpf_ou_cnpj(valor, *, campo: str = "documento") -> str:
        doc = DocumentoFiscalValidacaoServico.somente_digitos(valor)
        if not doc:
            raise ValidationError({campo: "CPF/CNPJ não informado."})
        if len(doc) == 11:
            return DocumentoFiscalValidacaoServico.validar_cpf(doc, campo=campo)
        if len(doc) == 14:
            return DocumentoFiscalValidacaoServico.validar_cnpj(doc, campo=campo)
        raise ValidationError({campo: "Documento inválido: informe CPF (11 dígitos) ou CNPJ (14 dígitos)."})

    @staticmethod
    def validar_cpf(valor, *, campo: str = "cpf") -> str:
        cpf = DocumentoFiscalValidacaoServico.somente_digitos(valor)
        if not cpf:
            raise ValidationError({campo: "CPF não informado."})
        if len(cpf) != 11:
            raise ValidationError({campo: "CPF inválido: informe 11 dígitos."})
        if not DocumentoFiscalValidacaoServico.cpf_valido(cpf):
            raise ValidationError({campo: "CPF inválido."})
        return cpf

    @staticmethod
    def validar_cnpj(valor, *, campo: str = "cnpj") -> str:
        cnpj = DocumentoFiscalValidacaoServico.somente_digitos(valor)
        if not cnpj:
            raise ValidationError({campo: "CNPJ não informado."})
        if len(cnpj) != 14:
            raise ValidationError({campo: "CNPJ inválido: informe 14 dígitos."})
        if not DocumentoFiscalValidacaoServico.cnpj_valido(cnpj):
            raise ValidationError({campo: "CNPJ inválido."})
        return cnpj

    @staticmethod
    def normalizar_opcional(valor) -> str:
        doc = DocumentoFiscalValidacaoServico.somente_digitos(valor)
        return doc
