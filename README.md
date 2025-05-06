# 📦 AI Agents Policy Adherence

Analyze policy document and generate determinstic code (currently, in Python) to enforce operational policies, when invocing AI agent tools.

## 🚀 Features

- Analyze a natural language policy document, assign policy items to specific tools, and provide complience/ violation examples for each tool and policy.
- Generate Python code to protect specific tools from policy violations.

## 🐍 Requirements

- Python 3.12+
- `pip`

## 🛠 Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.ibm.com/MLT/gen_policy_validator.git
   cd gen_policy_validator
   ```

2. **(Optional) Create and activate a virtual environment:**

   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file:**

   Copy the `src/.env.example` to `src/.env` and fill in your environment variables. 
   Replace `AZURE_OPENAI_API_KEY` with your actual API key.

5. **Run the application:**
   Ar
   ```bash
   PYTHONPATH=src python -m policy_adherence
   ```

