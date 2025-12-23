from langchain_openai import ChatOpenAI
from src.agents.prompts.prompt_templates import QUALITY_EVAL_PROMPT
from tenacity import retry, stop_after_attempt, wait_exponential
import torch
import os 
from src.clients.rabbitmq_client import RabbitMQClient
from src.clients.postgres_client import PostgresClient
import json 
from dotenv import load_dotenv
import time
load_dotenv()

class CallQualityAgent:
    def __init__(self, db: PostgresClient, mq: RabbitMQClient):
        self.llm = ChatOpenAI(
            base_url=os.getenv("LLM_BASE_URL"),
            api_key=os.getenv("LLM_API_KEY"),
            temperature=0
        )
        self.db = db
        self.prompt_template = self.db.get_active_prompt("QUALITY_EVAL")
        self.mq = mq

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def evaluate(self, transcript: str) -> str:
        prompt = self.prompt_template["content"].format(transcript=transcript)

        start = time.time()
        response = self.llm.invoke(prompt)
        duration = time.time() - start

        print(f"LLM latency: {duration:.2f}s for call")
        return response.content

    def process_evaluation_job(self, message: dict):
        try:
            call_id = message.get("call_id")
            print("Processing evaluation job for call:", call_id)
            call = self.db.get_transcript_by_call_id(call_id)
            
            evaluation = self.evaluate(call["timestamped_text"])      

            evaluation = json.loads(evaluation)

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
            print("Error processing evaluation job:", e)
            self.db.update_call_status(call_id, "FAILED", f"Evaluation failed: {str(e)}")
            self.mq.publish("failed_jobs", {"file_path": message.get("file_path"), "call_id": message.get("call_id"), "error": f"Evaluation failed: {str(e)}"})


def main():
    mq = RabbitMQClient()
    db = PostgresClient()
    print("Waiting for evaluation jobs...")


    agent = CallQualityAgent(db=db, mq=mq)
    mq.consume(
        queue_name="evaluation_jobs",
        callback=agent.process_evaluation_job
    )

if __name__ == "__main__":
    main()