# AI Call Quality Evaluation POC

This project demonstrates an end-to-end AI system for:
- Transcribing customer service calls
- Evaluating call quality using an LLM-based agent
- Storing structured results for comparison with human annotations

## Tech Stack
- Whisper (local transcription)
- RabbitMQ (job orchestration)
- PostgreSQL (structured storage)
- LangChain + local LLM (quality evaluation)
- Docker Compose (local deployment)

## Architecture
- Ingestion → Transcription → Evaluation → Storage

## Status
Proof-of-concept under active development.

## Setup
