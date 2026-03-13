from django.db.utils import OperationalError, ProgrammingError

from sped.models import Contadores, Entidades, Filial, Infvv, Nfevv, NotaFiscal, NotaFiscalItem, Produtos, SaldoProduto, UnidadeMedida


def limpa(valor):
    if valor is None:
        return ""
    return "".join([c for c in str(valor) if c.isdigit()])


class Bloco0Service:
    def __init__(self, *, db_alias, empresa_id, filial_id, data_inicio, data_fim):
        self.db_alias = db_alias
        self.empresa_id = int(empresa_id)
        self.filial_id = int(filial_id)
        self.data_inicio = data_inicio
        self.data_fim = data_fim
    
    def _usar_nfevv(self):
        try:
            if (
                NotaFiscal.objects.using(self.db_alias)
                .filter(
                    empresa=self.empresa_id,
                    filial=self.filial_id,
                    data_emissao__range=(self.data_inicio, self.data_fim),
                )
                .exclude(status=0)
                .exists()
            ):
                return False
        except (ProgrammingError, OperationalError):
            pass

        try:
            return (
                Nfevv.objects.using(self.db_alias)
                .filter(
                    empresa=self.empresa_id,
                    filial=self.filial_id,
                    b09_demi__range=(self.data_inicio, self.data_fim),
                    status_nfe=100,
                )
                .exists()
            )
        except (ProgrammingError, OperationalError):
            return False

    def gerar(self):
        linhas = []

        filial = (
            Filial.objects.using(self.db_alias)
            .filter(empr_empr=self.filial_id)
            .first()
        )
        if not filial:
            return ["|0000|||||||||||||||", "|9999|2|"]

        ind_perfil = (filial.empr_perf_sped or "").strip() or "A"
        ind_ativ = (filial.empr_ativ_sped or "").strip() or "1"

        linhas.append(
            "|0000|019|0|{dt_ini}|{dt_fim}|{nome}|{cnpj}||{uf}|{ie}|{cod_mun}|||{perfil}|{ativ}|".format(
                dt_ini=self.data_inicio.strftime("%d%m%Y"),
                dt_fim=self.data_fim.strftime("%d%m%Y"),
                nome=(filial.empr_nome or "").strip(),
                cnpj=limpa(filial.empr_docu),
                uf=(filial.empr_esta or "").strip(),
                ie=limpa(filial.empr_insc_esta),
                cod_mun=limpa(filial.empr_codi_cida),
                perfil=ind_perfil,
                ativ=ind_ativ,
            )
        )
        linhas.append("|0001|0|")

        linhas.append(
            "|0005|{fant}|{cep}|{end}|{num}|{compl}|{bair}|{fone}|{fax}|{email}|".format(
                fant=(filial.empr_nome or "").strip(),
                cep=limpa(filial.empr_cep),
                end=(filial.empr_ende or "").strip(),
                num=(filial.empr_nume or "").strip(),
                compl=(filial.empr_comp or "").strip(),
                bair=(filial.empr_bair or "").strip(),
                fone=limpa(filial.empr_fone),
                fax="",
                email=(filial.empr_emai or "").strip(),
            )
        )

        if filial.empr_codi_cont:
            contador = (
                Contadores.objects.using(self.db_alias)
                .filter(cont_codi=int(filial.empr_codi_cont))
                .first()
            )
            if contador:
                linhas.append(
                    "|0100|{nome}|{cpf}|{crc}|{cnpj}|{cep}|{end}|{num}|{compl}|{bair}|{fone}|{fax}|{email}|{cod_mun}|".format(
                        nome=(contador.cont_nome or "").strip(),
                        cpf=limpa(contador.cont_cpf),
                        crc=(contador.cont_crc or "").strip(),
                        cnpj=limpa(contador.cont_cnpj),
                        cep=limpa(contador.cont_cep),
                        end=(contador.cont_ende or "").strip(),
                        num=(contador.cont_nume or "").strip(),
                        compl=(contador.cont_comp or "").strip(),
                        bair="",
                        fone=limpa(contador.cont_fone),
                        fax="",
                        email=(contador.cont_emai or "").strip(),
                        cod_mun=limpa(filial.empr_codi_cida),
                    )
                )

        usar_nfevv = self._usar_nfevv()
        if usar_nfevv:
            participantes = {}
            for n in (
                Nfevv.objects.using(self.db_alias)
                .filter(
                    empresa=self.empresa_id,
                    filial=self.filial_id,
                    b09_demi__range=(self.data_inicio, self.data_fim),
                    status_nfe=100,
                )
                .order_by("b09_demi", "b06_mod", "b07_serie", "b08_nnf")
                .iterator()
            ):
                doc = limpa(n.e02_cnpj) if getattr(n, "e02_cnpj", None) else limpa(getattr(n, "e03_cpf", None))
                cod_part = doc or f"NFE{n.b06_mod or ''}{n.b07_serie or ''}{n.b08_nnf or ''}"
                if cod_part in participantes:
                    continue
                participantes[cod_part] = n

            for cod_part, n in sorted(participantes.items(), key=lambda kv: kv[0]):
                doc = cod_part if cod_part.isdigit() else ""
                linhas.append(
                    "|0150|{cod}|{nome}|{cod_pais}|{cnpj}|{ie}|{cod_mun}|{suframa}|{end}|{num}|{compl}|{bair}|".format(
                        cod=cod_part,
                        nome=(getattr(n, "e04_xnome", "") or "").strip(),
                        cod_pais=str(getattr(n, "e14_cpais", "") or "1058").strip(),
                        cnpj=doc,
                        ie=limpa(getattr(n, "e17_ie", None)),
                        cod_mun=limpa(getattr(n, "e10_cmun", None)),
                        suframa="",
                        end=(getattr(n, "e06_xlgr", "") or "").strip(),
                        num=(getattr(n, "e07_nro", "") or "").strip(),
                        compl=(getattr(n, "e08_xcpl", "") or "").strip(),
                        bair=(getattr(n, "e09_xbairro", "") or "").strip(),
                    )
                )
        else:
            participantes_ids = (
                NotaFiscal.objects.using(self.db_alias)
                .filter(
                    empresa=self.empresa_id,
                    filial=self.filial_id,
                    data_emissao__range=(self.data_inicio, self.data_fim),
                )
                .exclude(status=0)
                .values_list("destinatario_id", flat=True)
                .distinct()
            )
            for e in (
                Entidades.objects.using(self.db_alias)
                .filter(enti_empr=self.empresa_id, enti_clie__in=participantes_ids)
                .order_by("enti_clie")
                .iterator()
            ):
                doc = limpa(e.enti_cnpj) if e.enti_cnpj else limpa(e.enti_cpf)
                linhas.append(
                    "|0150|{cod}|{nome}|{cod_pais}|{cnpj}|{ie}|{cod_mun}|{suframa}|{end}|{num}|{compl}|{bair}|".format(
                        cod=e.enti_clie,
                        nome=(e.enti_nome or "").strip(),
                        cod_pais=(e.enti_codi_pais or "1058").strip(),
                        cnpj=doc,
                        ie=limpa(e.enti_insc_esta),
                        cod_mun=limpa(e.enti_codi_cida),
                        suframa="",
                        end=(e.enti_ende or "").strip(),
                        num=(e.enti_nume or "").strip(),
                        compl=(e.enti_comp or "").strip(),
                        bair=(e.enti_bair or "").strip(),
                    )
                )

        xml_prod_map = {}
        unid_ids = set()
        if usar_nfevv:
            notas_qs = (
                Nfevv.objects.using(self.db_alias)
                .filter(
                    empresa=self.empresa_id,
                    filial=self.filial_id,
                    b09_demi__range=(self.data_inicio, self.data_fim),
                    status_nfe=100,
                )
                .values_list("id", flat=True)
            )
            for it in (
                Infvv.objects.using(self.db_alias)
                .filter(id__in=notas_qs)
                .values("i02_cprod", "i04_xprod", "i05_ncm", "i09_ucom")
                .iterator()
            ):
                cod = (it.get("i02_cprod") or "").strip()
                if not cod:
                    continue
                if cod not in xml_prod_map:
                    xml_prod_map[cod] = {
                        "xProd": (it.get("i04_xprod") or "").strip(),
                        "uCom": (it.get("i09_ucom") or "").strip(),
                        "NCM": (it.get("i05_ncm") or "").strip(),
                    }
                if it.get("i09_ucom"):
                    unid_ids.add((it.get("i09_ucom") or "").strip())
        else:
            unid_ids.update(
                NotaFiscalItem.objects.using(self.db_alias)
                .filter(
                    nota__empresa=self.empresa_id,
                    nota__filial=self.filial_id,
                    nota__data_emissao__range=(self.data_inicio, self.data_fim),
                )
                .values_list("produto__prod_unme_id", flat=True)
                .distinct()
            )
        unid_ids.update(
            SaldoProduto.objects.using(self.db_alias)
            .filter(empresa=str(self.empresa_id), filial=str(self.filial_id), saldo_estoque__gt=0)
            .values_list("produto_codigo__prod_unme_id", flat=True)
            .distinct()
        )
        for u in (
            UnidadeMedida.objects.using(self.db_alias)
            .filter(unid_codi__in=unid_ids)
            .order_by("unid_codi")
            .iterator()
        ):
            linhas.append("|0190|{cod}|{desc}|".format(cod=u.unid_codi, desc=(u.unid_desc or "").strip()))

        prod_ids = set()
        if usar_nfevv:
            prod_ids.update(xml_prod_map.keys())
        else:
            prod_ids.update(
                NotaFiscalItem.objects.using(self.db_alias)
                .filter(
                    nota__empresa=self.empresa_id,
                    nota__filial=self.filial_id,
                    nota__data_emissao__range=(self.data_inicio, self.data_fim),
                )
                .values_list("produto_id", flat=True)
                .distinct()
            )
        prod_ids.update(
            SaldoProduto.objects.using(self.db_alias)
            .filter(empresa=str(self.empresa_id), filial=str(self.filial_id), saldo_estoque__gt=0)
            .values_list("produto_codigo_id", flat=True)
            .distinct()
        )
        prod_encontrados = set()
        for p in (
            Produtos.objects.using(self.db_alias)
            .filter(prod_empr=str(self.empresa_id), prod_codi__in=prod_ids)
            .order_by("prod_codi")
            .iterator()
        ):
            prod_encontrados.add(p.prod_codi)
            linhas.append(
                "|0200|{cod}|{desc}|||{unid}|00|{ncm}||||||".format(
                    cod=p.prod_codi,
                    desc=(p.prod_nome or "").strip(),
                    unid=(p.prod_unme_id or "").strip(),
                    ncm=limpa(p.prod_ncm),
                )
            )
        
        if usar_nfevv:
            for cod in sorted(set(xml_prod_map.keys()) - prod_encontrados):
                info = xml_prod_map.get(cod) or {}
                linhas.append(
                    "|0200|{cod}|{desc}|||{unid}|00|{ncm}||||||".format(
                        cod=cod,
                        desc=(info.get("xProd") or "").strip(),
                        unid=(info.get("uCom") or "").strip(),
                        ncm=limpa(info.get("NCM")),
                    )
                )

        linhas.append("|0990|{qtd}|".format(qtd=len(linhas) + 1))
        return linhas
