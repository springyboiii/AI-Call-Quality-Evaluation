import whisper
import torch
import json
from src.clients.rabbitmq_client import RabbitMQClient
from src.clients.postgres_client import PostgresClient
import uuid
class TranscriptionWorker:
    """
    Deterministic transcription tool using OpenAI Whisper.
    """
    def __init__(self, model_name="base", MQClient: RabbitMQClient = None, DBClient: PostgresClient = None):
        self.mq = MQClient
        self.db = DBClient
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # self.device = "cpu"
        print(f"Loading Whisper model '{model_name}' on {self.device}...")
        self.model = whisper.load_model(model_name).to(self.device)
        print("Model loaded.")

    def transcribe(self, audio_path: str) -> str:
        result = self.model.transcribe(audio_path)
        # for seg in result["segments"]:
        #     print(f"[{seg['start']:.2f} - {seg['end']:.2f}] {seg['text']}")
        return result

    def segments_to_human_transcript(self, segments: list) -> str:
        lines = []

        for seg in segments:
            ts = seg["start"]
            text = seg["text"].strip()

            if not text:
                continue

            lines.append(f"{ts} {text}")

        return "\n".join(lines)

    def process_transcription_job(self, message: dict):
        """
        Callback executed for every message from RabbitMQ.
        """
        try:
            audio_path = message.get("file_path")
            if not audio_path:
                print("Invalid message received:", message)
                return

            print(f"Transcribing: {audio_path}")
            transcript = self.transcribe(audio_path)
            transcript_id = self.db.save_transcript(
                call_id=message.get("call_id"),
                transcript_id=str(uuid.uuid4()),
                transcript_text=transcript["text"],
                segments=transcript["segments"],
                timestamped_text=self.segments_to_human_transcript(transcript["segments"]),
                model_name="whisper-small",
                language=transcript.get("language", "en")
            )
            self.mq.publish("evaluation_jobs", {"file_path": audio_path, "call_id": message.get("call_id")})
            self.db.update_call_status(message.get("call_id"), "EVALUATION_QUEUE")

        except Exception as e:
            print("Error processing transcription job:", e)
            self.db.update_call_status(message.get("call_id"), "FAILED")


def main():
    mq = RabbitMQClient()
    db = PostgresClient()
    worker = TranscriptionWorker(model_name="base",MQClient=mq, DBClient=db)
    print("Waiting for transcription jobs...")
    mq.consume(
        queue_name="transcription_jobs",
        callback=worker.process_transcription_job
    )


if __name__ == "__main__":
    main()