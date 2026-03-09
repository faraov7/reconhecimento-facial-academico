# FaceID Academico - TCC

Sistema completo de reconhecimento facial para ambiente academico, com:

- cadastro de usuarios (nome, matricula, fotos)
- captura automatica de fotos via webcam no cadastro
- treinamento de embeddings e salvamento em `models/embeddings.pkl`
- reconhecimento facial em tempo real via webcam
- logs de acesso no SQLite (`RECONHECIDO` e `DESCONHECIDO`)
- controle de presenca por disciplina/turma
- exportacao de relatorios em CSV e PDF
- interface web responsiva com Flask + Bootstrap

## Stack

- Python (core IA e backend)
- Flask (interface web/API)
- OpenCV (detecao facial e camera)
- face_recognition (embeddings faciais)
- SQLite (persistencia de usuarios e acessos)
- HTML/CSS/JS + Bootstrap (frontend)

## Estrutura

```txt
TCC/
├── app.py
├── cadastro.py
├── camera.py
├── config.py
├── database.py
├── detector_face.py
├── reconhecimento.py
├── treinamento.py
├── logs.py
├── requirements.txt
├── dataset/
├── models/
├── templates/
└── static/
```

## Como executar

1. Criar ambiente virtual:

```bash
python -m venv .venv
```

2. Ativar ambiente:

- Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Rodar sistema:

```bash
python app.py
```

5. Abrir no navegador:

`http://127.0.0.1:5000`

## Fluxo operacional

1. Acesse `Cadastro` e registre usuario + fotos.
2. O sistema salva imagens em `dataset/usuario_XXX/`.
3. O treinamento gera embeddings em `models/embeddings.pkl`.
4. Em `Reconhecimento`, a webcam identifica rostos em tempo real.
5. Cada deteccao gera registro na tabela `acessos`.
6. Para controle de presenca, crie turma, vincule alunos e inicie chamada.
7. Exporte relatorios em `/relatorios` (CSV/PDF).

## Banco de dados

### Tabela `usuarios`

- `id` INTEGER PK
- `nome` TEXT
- `matricula` TEXT UNIQUE
- `pasta_dataset` TEXT

### Tabela `acessos`

- `id` INTEGER PK
- `usuario_id` INTEGER (FK usuarios)
- `turma_id` INTEGER (FK turmas)
- `data_hora` DATETIME
- `status` TEXT (`RECONHECIDO` ou `DESCONHECIDO`)

### Tabela `turmas`

- `id` INTEGER PK
- `nome` TEXT
- `disciplina` TEXT
- `periodo` TEXT

### Tabela `usuario_turmas`

- `usuario_id` INTEGER
- `turma_id` INTEGER

### Tabela `presencas`

- `id` INTEGER PK
- `usuario_id` INTEGER
- `turma_id` INTEGER
- `data` DATE
- `status` TEXT (`PRESENTE`/`AUSENTE`)

## Observacoes

- Em ambientes sem webcam, a rota `/video_feed` nao exibira imagem.
- O pacote `face-recognition` depende de `dlib`. Se houver erro de instalacao no Windows,
  recomenda-se instalar o Visual C++ Build Tools ou usar wheel precompilada.
