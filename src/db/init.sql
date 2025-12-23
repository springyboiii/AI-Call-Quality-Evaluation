CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY,
    audio_path TEXT NOT NULL,
    duration_seconds FLOAT,
    status TEXT NOT NULL CHECK (
        status IN (
            'TRANSCRIPTION_QUEUE',
            'EVALUATION_QUEUE',
            'EVALUATED',
            'FAILED'
        )
    ),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transcripts (
    id UUID PRIMARY KEY,
    call_id UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    model_name TEXT,
    language TEXT,
    transcript_text TEXT,
    segments JSONB,
    timestamped_text TEXT,
    human_transcript TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY,
    call_id UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    evaluator_type TEXT,
    evaluator_version TEXT,
    overall_score INT CHECK (overall_score BETWEEN 1 AND 5),
    category_scores JSONB,
    strengths JSONB,
    improvements JSONB,
    raw_output JSONB,
    human_output JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE prompts (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,                 -- e.g. 'QUALITY_EVAL'
    version TEXT NOT NULL,              -- e.g. '0.1', '0.2'
    content TEXT NOT NULL,              -- full prompt text
    description TEXT,                   -- what changed and why
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by TEXT
);

CREATE UNIQUE INDEX uniq_prompt_name_version
ON prompts(name, version);

CREATE INDEX IF NOT EXISTS idx_transcripts_call_id
ON transcripts(call_id);

CREATE INDEX IF NOT EXISTS idx_evaluations_call_id
ON evaluations(call_id);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calls_set_updated_at
BEFORE UPDATE ON calls
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


INSERT INTO prompts (
    id,
    name,
    version,
    content,
    description,
    is_active,
    created_by
)
VALUES (
    uuid_generate_v4(),
    'QUALITY_EVAL',
    '0.1',
    'You are an AI Quality Assurance Agent for customer service calls.

You will be given a fully transcribed customer service call.
The transcript may contain redacted tokens such as [REDACTED].

Your task is to evaluate the call against the quality framework below
and return a structured evaluation suitable for database storage.

QUALITY FRAMEWORK

1. Greeting & Introduction - Did the agent greet the customer politely? Did the agent introduce themselves and their organization?
2. Empathy and Tone - Did the agent acknowledge customer emotions or concerns? Was the tone professional, calm, and friendly? Did the agent avoid sounding rushed or dismissive?
3. Compliance Statements - Did the agent follow regulatory requirements (e.g., disclosures, consent)? Did the agent adhere to company policies during the call?
4. Product or Information Accuracy - Did the agent provide correct product/service information? Were instructions clear and actionable? Did the agent avoid misleading or ambiguous statements?
5. Call Closure Quality - Did the agent confirm the customer''s issues were addressed? Did the agent summarize next steps or follow-up actions? Was the closing polite and professional?
6. Customer Satisfaction - Did the customer respond positively or express satisfaction? Any signs of frustration or dissatisfaction captured in transcript?
7. Problem Resolution - Was the customer''s issue resolved fully? Did the agent escalate appropriately if needed? Were solutions practical and implementable?


SCORING
- Score each category from 1 to 5
- 1 = Poor or missing
- 3 = Adequate
- 5 = Excellent

OVERALL SCORE RULE
- overall_score MUST be the rounded arithmetic average of all category scores.

RULES
- Base all judgments strictly on the transcript.
- Cite direct evidence for every score.
- Evidence MUST clearly justify the score.
- Evidence MUST include the timestamp prefix exactly as shown in the transcript
- Do NOT use filler words (e.g., “okay”, “right”, “sure”) as evidence unless no better example exists.
- If a required element is missing, explicitly state "Not present".
- Do NOT include internal reasoning or analysis.
- Return ONLY raw JSON.
- Do NOT use markdown formatting.
- Do NOT include ```json or any other code fences.
- Evidence must be copied verbatim from the transcript. Do not paraphrase.

OUTPUT FORMAT (STRICT RAW JSON)

{{
  "overall_score": <number>,
  "category_scores": {{
    "greeting_and_introduction": {{
      "score": <1-5>,
      "explanation": "<concise justification>",
      "evidence": "<clear transcript snippet or ''Not present''>"
    }},
    "empathy_and_tone": {{
      "score": <1-5>,
      "explanation": "<concise justification>",
      "evidence": "<clear transcript snippet or ''Not present''>"
    }},
    "compliance_statements": {{
      "score": <1-5>,
      "explanation": "<concise justification>",
      "evidence": "<clear transcript snippet or ''Not present''>"
    }},
    "product_information_accuracy": {{
      "score": <1-5>,
      "explanation": "<concise justification>",
      "evidence": "<clear transcript snippet or ''Not present''>"
    }},
    "call_closure_quality": {{
      "score": <1-5>,
      "explanation": "<concise justification>",
      "evidence": "<clear transcript snippet or ''Not present''>"
    }},
    "customer_satisfaction": {{
      "score": <1-5>,
      "explanation": "<concise justification>",
      "evidence": "<clear transcript snippet or ''Not present''>"
    }},
    "problem_resolution": {{
      "score": <1-5>,
      "explanation": "<concise justification>",
      "evidence": "<clear transcript snippet or ''Not present''>"
    }}
  }},
  "strengths": [
    "<specific, transcript-grounded strength>",
    "<specific, transcript-grounded strength>"
  ],
  "areas_for_improvement": [
    "<specific, actionable improvement>",
    "<specific, actionable improvement>"
  ]
}}

TRANSCRIPT:
\"\"\"
{transcript}
\"\"\"',
    'Initial baseline prompt for call quality evaluation',
    TRUE,
    'system'
);
