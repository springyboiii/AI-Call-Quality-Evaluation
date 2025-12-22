from langchain_openai import ChatOpenAI
from src.agents.prompts.prompt_templates import QUALITY_EVAL_PROMPT

import torch
import os 
from src.clients.rabbitmq_client import RabbitMQClient
from src.clients.postgres_client import PostgresClient
import json 

class CallQualityAgent:
    """
    Agentic evaluator: reasoning + judgment only.
    """
    def __init__(self, db: PostgresClient):
        self.llm = ChatOpenAI(
            base_url="http://localhost:1234/v1",
            api_key="lm-studio",
            temperature=0
        )
        self.db = db

    def evaluate(self, transcript: str) -> str:
        prompt = QUALITY_EVAL_PROMPT.format(transcript=transcript)
        response = self.llm.invoke(prompt)
        return response.content

    def process_evaluation_job(self, message: dict):
        try:
            call_id = message.get("call_id")

            call = self.db.get_transcript_by_call_id(call_id)
            
            evaluation = self.evaluate(call["timestamped_text"])
            try:
                evaluation = json.loads(evaluation)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON from LLM: {e}\n{response.content}")
            print("Evaluation:", evaluation)
            transcript_id = self.db.save_evaluation(
                call_id=call_id,
                evaluator_type="agentic",
                evaluator_version="0.1",
                overall_score=evaluation["overall_score"],
                category_scores=evaluation["category_scores"],
                strengths=evaluation["strengths"],
                improvements=evaluation["areas_for_improvement"],
                raw_output=evaluation
            )

            self.db.update_call_status(call_id, "EVALUATED")

        except Exception as e:
            print("Error processing transcription job:", e)
            self.db.update_call_status(call_id, "FAILED")


def main():
    mq = RabbitMQClient()
    db = PostgresClient()
    print("Waiting for evaluation jobs...")


    agent = CallQualityAgent(db=db)
    mq.consume(
        queue_name="evaluation_jobs",
        callback=agent.process_evaluation_job
    )

if __name__ == "__main__":
    main()