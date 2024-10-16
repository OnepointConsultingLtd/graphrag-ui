from typing import List
from pydantic import BaseModel, Field
from openai import OpenAI

from graphrag_ui.config import cfg

client = OpenAI(api_key=cfg.openai_api_key)


class Intent(BaseModel):
    intent: str = Field(..., description="The intent of the user's query")
    confidence: float = Field(
        ..., description="The confidence of the intent detection model"
    )


class QueryMetadata(BaseModel):
    intents: List[Intent] = Field(
        ..., description="The list of intents detected in the user's query"
    )
    keywords: List[str] = Field(
        ..., description="The list of keywords extracted from the user's query"
    )
    subqueries: List[str] = Field(
        ...,
        description="The list of subqueries that can the user query can be broken into",
    )


def find_intent(query: str) -> QueryMetadata:
    """
    Find the intent of the user's query.
    """
    search_messages = [
        {
            "role": "system",
            "content": f"""You are an expert at extracting metadata of queries.""",
        },
        {
            "role": "user",
            "content": f"""You have multiple tasks based on a query. Ths first is about detecting the intent of the user's query. 
You need to return the intent and the confidence of the intent detection model.

You also extract keywords from the user's query. 
You need to return the keywords extracted from the user's query.

Finally you also break down the user's query into subqueries.
You need to return the subqueries that can the user query can be broken into.
         
For example:
         
Query: "What is the weather in Tokyo?"
Intents: intent: weather, confidence: 0.9
Keywords: tokyo, weather
Subqueries: What is the temperature in Tokyo?, What is the humidity in Tokyo?, Will it rain in Tokyo?

Here is the query: 
         
{query}
""",
        },
    ]

    completion = client.beta.chat.completions.parse(
        model=cfg.open_ai_model,
        messages=search_messages,
        response_format=QueryMetadata,
    )

    intent_list = completion.choices[0].message.parsed
    return intent_list


def find_intent_as_string(query: str) -> str:
    intent_list = find_intent(query)

    def join_list(l: List[str]) -> str:
        return ", ".join([i for i in l])

    joined_intents = ", ".join([i.intent for i in intent_list.intents])
    joined_keywords = join_list(intent_list.keywords)
    joined_subqueries = join_list(intent_list.subqueries)
    return f"""Intents: {joined_intents} 
Keywords: {joined_keywords}
Subqueries: {joined_subqueries}"""
