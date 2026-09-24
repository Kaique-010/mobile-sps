from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import models, transaction

from ModeloEtiquetas.models import ModeloEtiqueta


class ModeloEtiquetaService:

    CAMPOS_TEXTO = ("nome", "tipo_papel", "orientacao")

    CAMPOS_DECIMAL = (
        "largura_mm",
        "altura_mm",
        "margem_superior_mm",
        "margem_inferior_mm",
        "margem_esquerda_mm",
        "margem_direita_mm",
        "espacamento_horizontal_mm",
        "espacamento_vertical_mm",
    )

    CAMPOS_INTEIROS = ("colunas", "linhas")

    def __init__(self, banco, empresa_id, filial_id=None):
        self.banco = banco
        self.empresa_id = str(empresa_id)
        self.filial_id = (
            str(filial_id) if filial_id is not None else None
        )

        self.queryset = ModeloEtiqueta.objects.using(
            self.banco
        ).filter(
            empresa_id=self.empresa_id,
            ativo=True,
        )

        if self.filial_id is not None:
            self.queryset = self.queryset.filter(
                models.Q(filial_id=self.filial_id)
                | models.Q(filial_id__isnull=True)
                | models.Q(filial_id="")
            )
        else:
            self.queryset = self.queryset.filter(
                models.Q(filial_id__isnull=True)
                | models.Q(filial_id="")
            )

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def listar_modelos(self):
        return self.queryset.order_by("nome")

    def obter_por_id(self, modelo_id):
        try:
            return self.queryset.get(pk=modelo_id)
        except (ModeloEtiqueta.DoesNotExist, ValueError, TypeError):
            raise ValidationError(
                "Modelo de etiqueta não encontrado."
            )

    def obter_modelo_padrao(self):
        return self.queryset.filter(
            padrao=True
        ).first()

    # ------------------------------------------------------------------
    # Conversão / serialização
    # ------------------------------------------------------------------
    @classmethod
    def converter_dados_formulario(cls, post):
        """Converte o POST do formulário em dados tipados para o service."""
        dados = {}

        for campo in cls.CAMPOS_TEXTO:
            if campo in post:
                dados[campo] = post.get(campo, "").strip()

        try:
            for campo in cls.CAMPOS_DECIMAL:
                if campo in post:
                    valor = Decimal(post[campo])

                    if not valor.is_finite():
                        raise ValueError(campo)

                    dados[campo] = valor

            for campo in cls.CAMPOS_INTEIROS:
                if campo in post:
                    dados[campo] = int(post[campo])

        except (ValueError, TypeError, InvalidOperation):
            raise ValidationError("Informe valores numéricos válidos.")

        if post.get("padrao") in ("on", "true", "True", "1"):
            dados["padrao"] = True

        return dados

    @classmethod
    def para_dict(cls, modelo):
        """Serializa o modelo (decimais com ponto) para o JS da tela."""
        dados = {
            "pk": modelo.pk,
            "padrao": bool(modelo.padrao),
        }

        for campo in cls.CAMPOS_TEXTO:
            dados[campo] = getattr(modelo, campo)

        for campo in cls.CAMPOS_DECIMAL:
            dados[campo] = str(getattr(modelo, campo))

        for campo in cls.CAMPOS_INTEIROS:
            dados[campo] = getattr(modelo, campo)

        return dados

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    def criar_modelo(self, dados):
        dados = dados.copy()

        definir_padrao = bool(dados.pop("padrao", False))

        self._validar_dados(dados, criacao=True)

        # O primeiro modelo do escopo sempre vira o padrão.
        if not self.queryset.exists():
            definir_padrao = True

        dados["empresa_id"] = self.empresa_id
        dados["filial_id"] = self.filial_id

        with transaction.atomic(using=self.banco):
            if definir_padrao:
                self._limpar_padrao()

            modelo = ModeloEtiqueta.objects.using(
                self.banco
            ).create(
                **dados,
                padrao=definir_padrao,
            )

        return modelo

    def atualizar_modelo(self, modelo_id, dados):
        modelo = self.obter_por_id(modelo_id)
        dados = dados.copy()

        # Não permitir alteração do escopo pelo payload.
        dados.pop("empresa_id", None)
        dados.pop("filial_id", None)

        definir_padrao = dados.pop("padrao", None)

        self._validar_dados(dados, instancia=modelo)

        with transaction.atomic(using=self.banco):
            if definir_padrao is True:
                self._limpar_padrao()

            for campo, valor in dados.items():
                if not hasattr(modelo, campo):
                    raise ValidationError(
                        f"Campo inválido: {campo}"
                    )

                setattr(modelo, campo, valor)

            if definir_padrao is not None:
                modelo.padrao = definir_padrao

            modelo.save(using=self.banco)

        return modelo

    def definir_modelo_padrao(self, modelo_id):
        modelo = self.obter_por_id(modelo_id)

        with transaction.atomic(using=self.banco):
            self._limpar_padrao()

            modelo.padrao = True
            modelo.save(
                using=self.banco,
                update_fields=["padrao", "atualizado_em"],
            )

        return modelo

    def excluir_modelo(self, modelo_id):
        modelo = self.obter_por_id(modelo_id)

        modelo.ativo = False
        modelo.padrao = False

        modelo.save(
            using=self.banco,
            update_fields=[
                "ativo",
                "padrao",
                "atualizado_em",
            ],
        )

    def _limpar_padrao(self):
        self.queryset.filter(
            padrao=True
        ).update(padrao=False)

    # ------------------------------------------------------------------
    # Validação
    # ------------------------------------------------------------------
    @staticmethod
    def _validar_dados(dados, instancia=None, criacao=False):
        campos_permitidos = {
            "nome",
            "tipo_papel",
            "orientacao",
            "largura_mm",
            "altura_mm",
            "colunas",
            "linhas",
            "margem_superior_mm",
            "margem_inferior_mm",
            "margem_esquerda_mm",
            "margem_direita_mm",
            "espacamento_horizontal_mm",
            "espacamento_vertical_mm",
            "configuracao",
            "ativo",
        }

        campos_invalidos = set(dados) - campos_permitidos

        if campos_invalidos:
            raise ValidationError(
                f"Campos inválidos: {', '.join(sorted(campos_invalidos))}"
            )

        if (criacao or "nome" in dados) and not dados.get("nome"):
            raise ValidationError("Informe o nome do modelo.")

        if (
            "tipo_papel" in dados
            and dados["tipo_papel"] not in dict(ModeloEtiqueta.Tipo_Papel)
        ):
            raise ValidationError("Tipo de papel inválido.")

        if (
            "orientacao" in dados
            and dados["orientacao"] not in dict(ModeloEtiqueta.Orientacao)
        ):
            raise ValidationError("Orientação inválida.")

        largura = dados.get(
            "largura_mm",
            getattr(instancia, "largura_mm", 40),
        )
        altura = dados.get(
            "altura_mm",
            getattr(instancia, "altura_mm", 60),
        )

        if largura <= 0 or altura <= 0:
            raise ValidationError(
                "Largura e altura devem ser maiores que zero."
            )

        if dados.get("colunas", getattr(instancia, "colunas", 1)) < 1:
            raise ValidationError(
                "A quantidade de colunas deve ser maior que zero."
            )

        if dados.get("linhas", getattr(instancia, "linhas", 1)) < 1:
            raise ValidationError(
                "A quantidade de linhas deve ser maior que zero."
            )

        for campo in (
            "margem_superior_mm",
            "margem_inferior_mm",
            "margem_esquerda_mm",
            "margem_direita_mm",
            "espacamento_horizontal_mm",
            "espacamento_vertical_mm",
        ):
            if campo in dados and dados[campo] < 0:
                raise ValidationError(
                    "Margens e espaçamentos não podem ser negativos."
                )