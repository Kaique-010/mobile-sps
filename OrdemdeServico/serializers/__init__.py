from .base import BancoModelSerializer
from .auxiliares import OrdemServicoFaseSetorSerializer, OrdemServicoVoltagemSerializer, WorkflowSetorSerializer
from .itens import OrdemServicoPecasSerializer, OrdemServicoServicosSerializer
from .imagens import (
    ImagemBase64Serializer, OrdemServicoImgAntesSerializer,
    ImagemAntesSerializer, ImagemDuranteSerializer, ImagemDepoisSerializer
)
from .financeiro import TituloReceberSerializer
from .dash import OrdensEletroSerializer
from .ordem import OrdemServicoSerializer
