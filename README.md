# 🧪 LLM Evaluation Toolkit

A professional Streamlit application for evaluating answers produced by LLM, RAG, chatbot, and agent systems.

The toolkit evaluates model outputs entered manually or uploaded through CSV files. It does not inspect model architecture, parameters, or weights.

## 🚀 Project Overview

LLM Evaluation Toolkit combines deterministic rule-based checks with local semantic similarity to estimate answer quality.

The application evaluates responses across multiple dimensions, identifies the most likely error type, provides improvement feedback, and supports both individual and batch evaluation workflows.

The default evaluator works without OpenAI, Claude, Gemini, or any external LLM API.

## ✨ Features

- Single-response evaluation
- CSV batch evaluation
- Local sentence-transformer semantic scoring
- Deterministic rule-based quality checks
- Named-entity and factual contradiction detection
- Numeric, date, duration, percentage, and unit normalization
- Equivalent-value detection such as:
  - `two weeks = 14 days`
  - `one quarter = 25%`
  - `1 GB = 1024 MB`
- Question-repetition detection
- Unwanted-refusal detection
- Placeholder and formatting checks
- Adjustable Pass threshold
- Clear Pass and Fail classification
- Primary error-type identification
- Deterministic improvement feedback
- Batch dashboard and filtering
- Invalid-row and duplicate isolation
- Detailed row inspection
- Evaluated CSV export
- Demo Mode and Full Local Mode
- No external API key required

## 🖥️ Application Modes

The application mode is controlled through the `APP_MODE` environment variable.

Supported values:

```env
APP_MODE=local
```

or:

```env
APP_MODE=demo
```

If the variable is missing or invalid, the application defaults to Local Mode.

### Demo Mode

The hosted version is intended for quick testing.

- No API key required
- Single and CSV batch evaluation
- Uses hosted computing resources
- May have speed, memory, or file-size limitations
- Not recommended for private or large datasets

### Full Local Mode

The complete evaluation workflow runs on the user's machine.

- No API key required
- Local sentence-transformer model
- Single and CSV batch evaluation
- Suitable for larger datasets
- Input data remains on the user's machine
- Recommended for private evaluation workflows

## 🧠 How the Evaluator Works

The evaluator combines multiple local techniques.

### Rule-Based Evaluation

The rule layer checks for:

- Empty answers
- Extremely short or incomplete answers
- Question repetition
- Excessive repetition
- Placeholder responses
- Generic refusals
- Formatting problems
- Excessive verbosity

### Semantic Evaluation

The semantic layer uses:

```text
sentence-transformers/all-MiniLM-L6-v2
```

It estimates:

- Answer relevance to the question
- Similarity to the expected answer
- Support from the provided context

### Deterministic Factual Checks

The toolkit also checks for conflicts involving:

- Named entities
- Numbers
- Dates and years
- Percentages
- Durations
- Yes/No answers
- Negation
- Opposite values
- Measurement and storage units
- Abbreviations and expanded terms

Examples:

```text
Riyadh vs Jeddah → Contradiction
14 days vs 30 days → Contradiction
Approved vs Rejected → Contradiction
Two weeks vs 14 days → Equivalent
RAG vs Retrieval-Augmented Generation → Equivalent
```

The evaluator provides a useful quality estimate, but it is not a guaranteed factual judge.

## 📥 Supported Input Format

### Single Evaluation

Required fields:

- `question`
- `answer`

Optional fields:

- `expected_answer`
- `context`

### Batch Evaluation

The CSV file may contain:

| Column | Required | Description |
|---|---:|---|
| `question` | Yes | The original prompt or user question |
| `answer` | Yes | The generated response being evaluated |
| `expected_answer` | No | Reference answer used for correctness |
| `context` | No | Supporting source material used for groundedness |
| `id` | No | Optional row identifier |

Invalid rows, empty required values, missing columns, and duplicate entries are detected and isolated safely.

## 📊 Evaluation Metrics

| Metric | Required Input | Default Weight |
|---|---|---:|
| Relevance | Question and answer | 25% |
| Correctness | Expected answer | 35% |
| Groundedness Estimate | Context | 25% |
| Completeness | Answer and quality rules | 15% |

The final `quality_score` ranges from 0 to 100.

If an optional field is unavailable:

- Correctness is displayed as `N/A` when `expected_answer` is missing.
- Groundedness is displayed as `N/A` when `context` is missing.

The remaining available metric weights are normalized automatically.

The default Pass threshold is:

```text
70
```

A response passes when its quality score reaches the configured threshold and no critical error is detected.

## 🚨 Error Types

The evaluator may classify a result as:

- No Error
- Empty Answer
- Irrelevant Answer
- Incorrect Answer
- Incomplete Answer
- Unsupported Answer
- Contradictory Answer
- Overly Verbose
- Unwanted Refusal
- Formatting Issue
- Insufficient Data

Each failed result includes deterministic improvement feedback explaining the main issue.

## 📈 Batch Evaluation Dashboard

The batch dashboard displays:

- Total evaluated rows
- Passed responses
- Failed responses
- Pass rate
- Average quality score
- Average metric scores
- Error-type distribution
- Lowest-scoring examples
- Filterable results
- Detailed row inspection

The evaluated CSV export preserves the original columns and adds:

```text
relevance_score
correctness_score
groundedness_score
completeness_score
quality_score
status
error_type
improvement_feedback
evaluation_mode
evaluated_at
evaluator_version
```

## 🏗️ Project Architecture

```text
LLM-Evaluation-Toolkit/
├── app.py
├── src/
│   ├── config/
│   │   └── Application settings and scoring weights
│   ├── evaluators/
│   │   └── Semantic, rule, contradiction, and normalization checks
│   ├── ingestion/
│   │   └── CSV loading and validation
│   ├── pipeline/
│   │   └── Single and batch evaluation orchestration
│   ├── reporting/
│   │   └── Feedback, summaries, and CSV export
│   ├── scoring/
│   │   └── Metric aggregation and error classification
│   └── ui/
│       └── Streamlit pages, components, and styling
├── tests/
├── data/
│   └── sample_evaluations.csv
├── assets/
├── .streamlit/
│   └── config.toml
├── .env.example
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

## ⚙️ Installation

Python 3.10 or newer is recommended.

Clone the repository:

```bash
git clone <repository-url>
cd LLM-Evaluation-Toolkit
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

## 🔐 Environment Configuration

Copy the example environment file:

```bash
copy .env.example .env
```

For macOS or Linux:

```bash
cp .env.example .env
```

For local usage, keep:

```env
APP_MODE=local
```

The `.env` file is excluded from Git and should not be committed.

For a hosted demo, set:

```env
APP_MODE=demo
```

through the deployment environment.

## ▶️ Usage

Run the application:

```bash
streamlit run app.py
```

Then open the local URL displayed by Streamlit.

Use:

- **Single Evaluation** for one response
- **Batch Evaluation** for CSV datasets

The embedding model downloads automatically during first use and is loaded from the local cache afterward.

## 📄 CSV Example

```csv
id,question,answer,expected_answer,context
1,What is the capital of Saudi Arabia?,Riyadh is the capital of Saudi Arabia.,The capital of Saudi Arabia is Riyadh.,Riyadh is the capital and largest city of Saudi Arabia.
```

The official downloadable sample is available at:

```text
data/sample_evaluations.csv
```

It contains six representative cases:

- Correct factual answer
- Contradictory answer
- Equivalent duration
- Question repetition
- Unwanted refusal
- Correct answer without context

## 🧪 Testing

Run the automated test suite:

```bash
pytest -q
```

Final project verification:

```text
94 automated tests passed
0 failed
```

A separate 100-case benchmark dataset was also used during development.

Benchmark composition:

```text
38 expected Pass cases
62 expected Fail cases
```

Final benchmark result:

```text
100 of 100 classifications matched the expected labels
False Positives: 0
False Negatives: 0
```

This benchmark was created specifically to test the implemented rules, contradiction checks, equivalent-value normalization, and semantic scoring behavior.

The result should not be interpreted as guaranteed 100% accuracy on unseen datasets or specialized domains.

## ⚠️ Limitations

- Semantic similarity does not guarantee factual correctness.
- Groundedness is an estimate and does not provide citation-level verification.
- Rule-based thresholds may require calibration for specialized domains.
- The first semantic evaluation requires internet access to download the embedding model.
- English is the primary tested language.
- Performance depends on available system memory and dataset size.
- Domain-specific terminology may require additional normalization rules.

## 🔮 Future Improvements

- Optional LLM-as-a-Judge integration
- OpenAI, Claude, Gemini, or local Ollama judge support
- Direct RAG and Agent API evaluation
- Experiment and model-version comparison
- Domain-specific evaluation profiles
- Claim-level groundedness analysis
- Multi-turn conversation evaluation
- Agent tool-call evaluation
- Automated CI/CD quality gates

V1 intentionally remains API-free and locally executable.

## 🛠️ Technologies Used

- Python
- Streamlit
- pandas
- NumPy
- Sentence Transformers
- PyTorch
- python-dotenv
- pytest

## 📜 License

This project is released under the [MIT License](LICENSE).
