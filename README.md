# 📞 AVI Claro - Simulador de Voz para Pós-Venda (POC)

O **AVI (Assistente Virtual Inteligente)** é uma Prova de Conceito (POC) desenvolvida para otimizar o atendimento de pós-venda da **Claro Brasil**. O sistema utiliza Inteligência Artificial e síntese de voz para automatizar dúvidas frequentes, reduzir o tempo de espera e encaminhar o cliente para o autoatendimento.

---

## 🚀 Funcionalidades Principal

- **Interface de Chat Contextual:** Desenvolvida em Streamlit para simular um painel de atendimento.
- **Motor de Respostas Inteligentes:** Simulação de lógica de IA (baseada em Claude 3.5 Sonnet) para intenções de pós-venda.
- **Síntese de Voz (TTS):** Integração com `gTTS` (Google Text-to-Speech) para transformar respostas em áudio em tempo real.
- **Mapeamento de Intenções:**
  - 📱 **Logística:** Status de pedidos e rastreio de aparelhos.
  - 🛠️ **Suporte Técnico:** Reagendamento de visitas técnicas.
  - 🛡️ **Segurança:** Regras de alteração de endereço e protocolos de cancelamento.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.11+
- **Framework Web:** [Streamlit](https://streamlit.io/)
- **Voz:** [gTTS](https://pypi.org/project/gTTS/)
- **IA (Backbone):** Anthropic Claude 3.5 Sonnet (Arquitetura preparada)
- **Deploy:** Streamlit Cloud

---

## 📦 Como Rodar o Projeto Localmente

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/aclaymar/poc-voice-ia-claro.git](https://github.com/aclaymar/poc-voice-ia-claro.git)
   cd poc-voice-ia-claro