from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from model.factory import chat_model
from utils.prompt_loader import load_system_prompt
from agent.tools.agent_tools import (rag_summarize, get_weather, get_user_location, get_user_id,
                                     get_current_month, fetch_external_data, fill_context_for_report)
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch
from typing import Optional
from utils.logger_handler import logger


def _history_to_langchain_messages(messages: Optional[list[dict]]):
    """
    将 HistoryService 返回的消息列表转换为 LangChain 消息格式
    :param messages: [{"role": "user|assistant|system", "content": "..."}, ...]
    :return: LangChain 消息对象列表
    """
    if not messages:
        return []
    lc_messages = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        elif role == "system":
            lc_messages.append(SystemMessage(content=content))
    return lc_messages


class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompt(),
            tools=[rag_summarize, get_weather, get_user_location, get_user_id,
                   get_current_month, fetch_external_data, fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
        )

    def execute_stream(self, query: str, history_messages: Optional[list[dict]] = None):
        """
        流式执行 Agent
        :param query: 用户当前提问
        :param history_messages: 历史消息列表 [{"role": "...", "content": "..."}, ...]
        :yield: 文本片段
        """
        # 组装消息：历史消息 + 当前提问
        lc_messages = _history_to_langchain_messages(history_messages)
        lc_messages.append(HumanMessage(content=query))

        input_dict = {"messages": lc_messages}

        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            # 只输出 AI 消息，过滤掉 HumanMessage 等非 AI 消息，避免重复输出用户问题
            if isinstance(latest_message, AIMessage) and latest_message.content:
                yield latest_message.content.strip() + "\n"


if __name__ == '__main__':
    agent = ReactAgent()

    for chunk in agent.execute_stream("给我生成我的使用报告"):
        print(chunk, end="", flush=True)
