# Fluxo de Emissão de Nota Fiscal (NF-e)

Este documento descreve visualmente e tecnicamente o fluxo de emissão de NF-e no sistema, detalhando a responsabilidade de cada arquivo e componente.

## 📊 Grafo do Fluxo de Processamento

```mermaid
graph TD
    %% Definição de Estilos
    classDef model fill:#e1f5fe,stroke:#01579b,color:#01579b
    classDef service fill:#fff3e0,stroke:#e65100,color:#e65100
    classDef dto fill:#f3e5f5,stroke:#4a148c,color:#4a148c
    classDef adapter fill:#e8f5e9,stroke:#1b5e20,color:#1b5e20
    classDef sefaz fill:#263238,stroke:#000,color:#fff

    subgraph Camada_Dados [1. Persistência e Modelos]
        DB[(PostgreSQL)]:::model
        Models[models.py\n(Nota, NotaItem)]:::model
        DB <--> Models
    end

    subgraph Camada_Servico [2. Regras de Negócio]
        CalcService[calculo_impostos_service.py\n(Cálculo de Tributos)]:::service
        NotaService[nota_service.py\n(Orquestrador)]:::service
        
        Models --> NotaService
        NotaService --> CalcService
        CalcService -->|Atualiza Impostos| Models
    end

    subgraph Camada_Dominio [3. Transformação de Dados]
        Builder[dominio/builder.py\n(NotaBuilder)]:::dto
        DTO[dominio/dto.py\n(NotaFiscalDTO)]:::dto
        
        NotaService -->|Aciona| Builder
        Builder -->|Lê| Models
        Builder -->|Gera| DTO
    end

    subgraph Camada_Aplicacao [4. Construção do XML]
        PyNFeBuilder[aplicacao/construir_nfe_pynfe.py\n(Adapter PyNFe)]:::adapter
        PyNFeObj[Objeto PyNFe\n(NotaFiscal)]:::adapter
        
        DTO -->|Input| PyNFeBuilder
        PyNFeBuilder -->|Output| PyNFeObj
        PyNFeBuilder -.->|Armazena IBS/CBS| ExtraData[lista _itens_extra]:::adapter
    end

    subgraph Camada_Infraestrutura [5. Comunicação SEFAZ]
        SefazAdapter[infrastructure/sefaz_adapter.py\n(Assinatura e Envio)]:::adapter
        
        PyNFeObj -->|Serializa| SefazAdapter
        ExtraData -->|Injeção Manual| SefazAdapter
        SefazAdapter -->|Assina XML| SefazAdapter
        SefazAdapter -->|Envia SOAP| SEFAZ((SEFAZ)):::sefaz
    end

    subgraph Retorno [6. Processamento de Resposta]
        SEFAZ -->|XML Retorno| SefazAdapter
        SefazAdapter -->|Parse Status/Motivo| NotaService
        NotaService -->|Salva Chave/Protocolo| Models
    end
```

## 📂 Detalhamento dos Arquivos e Responsabilidades

### 1. Modelos de Dados (`models.py`)
*   **Localização:** `d:\mobile-sps\Notas_Fiscais\models.py`
*   **Função:** Representa as tabelas do banco de dados.
*   **Principais Classes:**
    *   `Nota`: Cabeçalho da nota (emitente, destinatário, valores totais).
    *   `NotaItem`: Itens da nota (produtos, quantidades, valores unitários).
    *   `NotaItemImposto`: Detalhes fiscais de cada item (ICMS, IPI, PIS, COFINS, e agora IBS/CBS).

### 2. Serviço de Cálculo (`calculo_impostos_service.py`)
*   **Localização:** `d:\mobile-sps\Notas_Fiscais\services\calculo_impostos_service.py`
*   **Função:** Realiza todos os cálculos tributários antes da emissão.
*   **Destaque:** É aqui que definimos as alíquotas de IBS/CBS e calculamos os valores baseados na quantidade e valor unitário dos itens. Também aplica regras defensivas para evitar erros de integridade (como `cst_icms` nulo).

### 3. Builder de DTO (`dominio/builder.py`)
*   **Localização:** `d:\mobile-sps\Notas_Fiscais\dominio\builder.py`
*   **Função:** Padrão de projeto *Builder*. Extrai dados complexos dos modelos Django e os converte em um objeto simples e plano (DTO - Data Transfer Object).
*   **Por que existe?** Para desacoplar a lógica de emissão da estrutura do banco de dados. Se o banco mudar, só precisamos ajustar o Builder, sem quebrar a comunicação com a SEFAZ.

### 4. DTO (`dominio/dto.py`)
*   **Localização:** `d:\mobile-sps\Notas_Fiscais\dominio\dto.py`
*   **Função:** Define a estrutura de dados pura que será usada para gerar o XML.
*   **Atributos:** Contém campos para `emitente`, `destinatario`, `itens`, incluindo os novos campos `valor_ibs`, `valor_cbs`, etc.

### 5. Construtor PyNFe (`aplicacao/construir_nfe_pynfe.py`)
*   **Localização:** `d:\mobile-sps\Notas_Fiscais\aplicacao\construir_nfe_pynfe.py`
*   **Função:** Converte nosso `NotaFiscalDTO` para os objetos da biblioteca `PyNFe` (que gera o XML base).
*   **O "Pulo do Gato":** Como a biblioteca `PyNFe` ainda não suporta nativamente os campos da Reforma Tributária (IBS/CBS), nós armazenamos esses dados em uma lista oculta chamada `_itens_extra` dentro do objeto da nota. Isso permite que esses dados "peguem carona" até o momento da assinatura.

### 6. Adaptador SEFAZ (`infrastructure/sefaz_adapter.py`)
*   **Localização:** `d:\mobile-sps\Notas_Fiscais\infrastructure\sefaz_adapter.py`
*   **Função:** É o coração da comunicação com o governo.
*   **Responsabilidades Críticas:**
    1.  **Serialização:** Gera o XML padrão a partir do objeto PyNFe.
    2.  **Injeção Manual (Patch):** Intercepta o XML gerado e injeta manualmente as tags `<IBS>` e `<CBS>` lendo a lista `_itens_extra`. *Importante: Só injeta se os valores forem maiores que zero para evitar Erro 225.*
    3.  **Assinatura:** Assina digitalmente o XML modificado usando o certificado A1.
    4.  **Transmissão:** Envia o XML assinado para os servidores da SEFAZ via SOAP.
    5.  **Debug:** Imprime logs detalhados do retorno (Status HTTP, XML de resposta) para diagnóstico de erros (como o 656 ou 225).

### 7. Orquestrador (`services/nota_service.py`)
*   **Localização:** `d:\mobile-sps\Notas_Fiscais\services\nota_service.py`
*   **Função:** Gerencia o fluxo completo. Chama o cálculo, constrói o DTO, invoca o Adapter da SEFAZ e, dependendo do retorno, atualiza o status da nota no banco de dados (Autorizada, Rejeitada, Cancelada).
