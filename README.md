📞 AVI Claro - Simulador de Voz com IA Ultra-Realista (POC)
O AVI (Assistente Virtual Inteligente) é uma Prova de Conceito (POC) desenvolvida para otimizar o atendimento de pós-venda da Claro Brasil. O sistema utiliza Inteligência Artificial Generativa e síntese de voz de alta fidelidade para humanizar o autoatendimento e resolver demandas críticas com agilidade.

## 🏗️ Arquitetura da Solução

![Desenho de Arquitetura VoiceIA Claro](./img/arquitetura-voice-ia-claro.png)

O sistema utiliza uma abordagem de IA Generativa Multimodal integrada ao **NICE CXone** para substituir o fluxo de URAs tradicionais.

🧱 Fluxo de Dados (End-to-End)
Captura: Interface Streamlit captura o áudio do microfone do usuário (formato WebM).

Ingestão: O áudio é enviado para o Amazon S3 (Bucket: audio-claro-poc-andy) que atua como zona de pouso segura.

Transcrição (STT): O Amazon Transcribe processa o arquivo no S3 e converte a fala em texto em tempo real (PT-BR).

Cérebro (LLM): O Amazon Bedrock (Claude 3 Haiku) analisa o texto, entende a intenção e gera uma resposta resolutiva de acordo com as regras de negócio da Claro.

Síntese (TTS): A ElevenLabs (Modelo Multilingual v2.5) converte o texto em uma voz ultra-realista que é reproduzida para o cliente.

☁️ Infraestrutura Cloud (AWS)
Segurança: Utilização de IAM Roles com permissões granulares e remoção de Permissions Boundaries restritivas para garantir a fluidez do processo.

Escalabilidade: Arquitetura preparada para lidar com altos volumes de chamadas simultâneas através de serviços serverless da AWS.

🚀 Diferenciais Técnicos
Experiência Premium: Substituição de vozes robóticas por IA de voz ultra-realista, reduzindo o esforço cognitivo do cliente.

Inteligência de Pós-Venda: Mapeamento de intenções para logística (status de pedidos de iPhones), suporte técnico e protocolos de segurança.

Resiliência: Sistema com fallback para entrada de texto caso haja limitações de hardware/navegador no cliente.

🛠️ Tecnologias Utilizadas
Linguagem: Python 3.11+

Framework Web: Streamlit

Infraestrutura: AWS (S3, Transcribe, Bedrock)

Voz (High-Fidelity): ElevenLabs

Deploy: Streamlit Cloud