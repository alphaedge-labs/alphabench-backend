# tests/unit/core/backtesting/test_generator.py
from core.backtesting.generator import ScriptGenerator
from infrastructure.llm.openai_client import OpenAIClient

def test_script_generation():
    llm_client = OpenAIClient()
    generator = ScriptGenerator(llm_client)
    # ... test code