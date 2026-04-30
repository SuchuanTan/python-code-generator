import os
import configparser
from openai import OpenAI


def load_llm_config(path="config.ini"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, path)

    parser = configparser.ConfigParser()
    parser.read(full_path, encoding="utf-8")

    if "llm" not in parser:
        raise ValueError("The [llm] configuration section is missing from config.ini.")

    cfg = parser["llm"]

    return {
        "api_key": cfg.get("api_key"),
        "base_url": cfg.get("base_url"),
        "model": cfg.get("model", "gpt-4o-mini"),
        "temperature": float(cfg.get("temperature", '0.7')),
        "max_tokens": int(cfg.get("max_tokens", '1000')),
    }


class Memory:
    def __init__(self, max_turns=5):
        self.max_turns = max_turns
        self.messages = []

    def add_user(self, content):
        self.messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant(self, content):
        self.messages.append({"role": "assistant", "content": content})
        self._trim()

    def get_messages(self, system_prompt=None):
        msgs = self.messages[-self.max_turns * 2:]

        if system_prompt:
            return [{"role": "system", "content": system_prompt}] + msgs

        return msgs

    def _trim(self):
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-self.max_turns * 2:]

class LLM:
    _instance = None

    def __new__(cls, config_path="config.ini"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(config_path)
        return cls._instance

    def _init(self, config_path):
        cfg = load_llm_config(config_path)

        self.model = cfg["model"]
        self.temperature = cfg["temperature"]
        self.max_tokens = cfg["max_tokens"]

        self.client = OpenAI(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"]
        )

    def chat(self, messages):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        return response.choices[0].message.content


class Agent:
    # TODO: 这里的system prompt要改，不要用默认的，一个agent一个system prompt
    def __init__(self, system_prompt="你是一个有帮助的AI助手", memory_window=5):
        self.llm = LLM()
        self.memory = Memory(max_turns=memory_window)
        self.system_prompt = system_prompt

    def run(self, user_input: str):
        self.memory.add_user(user_input)
        messages = self.memory.get_messages(self.system_prompt)
        response = self.llm.chat(messages)
        self.memory.add_assistant(response)
        return response


# TODO: 底下是这个agent对象怎么用
if __name__ == "__main__":
    agent1 = Agent()
    while True:
        user_input = input("You：")
        if user_input.lower() in ["exit", "quit"]:
            break
        print("Agent：", agent1.run(user_input))
