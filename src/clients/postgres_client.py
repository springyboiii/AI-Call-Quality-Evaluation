import uuid
import json
import psycopg2
from psycopg2.extras import RealDictCursor


class PostgresClient:
    def __init__(
        self,
        host="localhost",
        port=5432,
        dbname="qa_poc",
        user="postgres",
        password="postgres"
    ):
        self.conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        self.conn.autocommit = False

    def close(self):
        self.conn.close()

    # -----
    # Calls 
    # -----

    def create_call(self, audio_path: str, call_id: str, duration_seconds: float = None):
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO calls (id, audio_path, duration_seconds, status)
                    VALUES (%s, %s, %s, %s)
                """,
                (call_id, audio_path, duration_seconds, "TRANSCRIPTION_QUEUE")
            )

            self.conn.commit()
        except Exception as e:
            print("Error creating call:", e)
            self.conn.rollback()
            return None
        return call_id

    def update_call_status(self, call_id: str, status: str, error_message: str = None):
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE calls
                    SET status = %s,
                    error_message = %s
                WHERE id = %s
                """,
                (status, error_message, call_id)
            )

            if cur.rowcount == 0:
                raise ValueError(f"No call found with id {call_id}")

            self.conn.commit()

        except Exception as e:
            print("Error updating call status:", e)
            self.conn.rollback()
            return False

        return True


    # -------------
    # Transcription 
    # -------------

    def save_transcript(
        self,
        call_id: str,
        transcript_id: str,
        transcript_text: str,
        segments: list,
        timestamped_text: str,
        model_name: str = "whisper-base",
        language: str = "en"
    ):
        try:
            print("Saving transcript to database")
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO transcripts (
                        id,
                        call_id,
                    model_name,
                    language,
                    transcript_text,
                    segments,
                    timestamped_text
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    transcript_id,
                    call_id,
                    model_name,
                    language,
                    transcript_text,
                    json.dumps(segments),
                    timestamped_text
                )
            )

            self.conn.commit()
            print("Transcript saved to database")
        except Exception as e:
            print("Error saving transcript:", e)
            self.conn.rollback()
            return None
        return transcript_id


    def get_transcript_by_call_id(self, call_id: str):
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        call_id,
                        transcript_text,
                        segments,
                        timestamped_text
                    FROM transcripts
                    WHERE call_id = %s
                    """,
                    (call_id,)
                )

                row = cur.fetchone()
                if not row:
                    return None

                return {
                    "id": row[0],
                    "call_id": row[1],
                    "transcript_text": row[2],
                    "segments": row[3],
                    "timestamped_text": row[4]
                }

        except Exception as e:
            print("Error fetching transcript:", e)
            self.conn.rollback()
            return None

    def get_transcripts(self):
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        call_id,
                        transcript_text,
                        segments,
                        timestamped_text,
                        human_transcript
                    FROM transcripts
                    """
                )

                rows = cur.fetchall()
                if not rows:
                    return None

                return [
                    {
                        "id": row[0],
                        "call_id": row[1],
                        "transcript_text": row[2],
                        "segments": row[3],
                        "timestamped_text": row[4],
                        "human_transcript": row[5]
                    }
                for row in rows
                ]

        except Exception as e:
            print("Error fetching transcript:", e)
            self.conn.rollback()
            return None

    # ----------
    # Evaluation 
    # ----------

    def save_evaluation(
        self,
        call_id: str,
        evaluator_type: str,
        evaluator_version: str,
        overall_score: int,
        category_scores: dict,
        strengths: list,
        improvements: list,
        raw_output: dict
    ):
        evaluation_id = str(uuid.uuid4())
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO evaluations (
                        id,
                    call_id,
                    evaluator_type,
                    evaluator_version,
                    overall_score,
                    category_scores,
                    strengths,
                    improvements,
                    raw_output
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    evaluation_id,
                    call_id,
                    evaluator_type,
                    evaluator_version,
                    overall_score,
                    json.dumps(category_scores),
                    json.dumps(strengths),
                    json.dumps(improvements),
                    json.dumps(raw_output)
                )
            )

            self.conn.commit()
        except Exception as e:
            print("Error saving evaluation:", e)
            self.conn.rollback()
            return None
        return evaluation_id

    def get_evaluations(self):
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        call_id,
                        evaluator_type,
                        evaluator_version,
                        overall_score,
                        category_scores,
                        strengths,
                        improvements,
                        raw_output,
                        human_output,
                        created_at
                    FROM evaluations
                    """
                )

                rows = cur.fetchall()
                if not rows:
                    return None

                return [
                        {
                        "id": row[0],
                        "call_id": row[1],
                        "evaluator_type": row[2],
                        "evaluator_version": row[3],
                        "overall_score": row[4],
                        "category_scores": row[5],
                        "strengths": row[6],
                        "improvements": row[7],
                        "raw_output": row[8],
                        "human_output": row[9],
                        "created_at": row[10]
                        }
                    for row in rows
                ]

        except Exception as e:
            print("Error fetching evaluation:", e)
            return None

    # -------
    # Prompts 
    # -------

    def get_active_prompt(self, name: str) -> dict:

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT name, version, content
                    FROM prompts
                    WHERE name = %s AND is_active = TRUE
                    LIMIT 1
                    """,
                    (name,)
                )

                row = cur.fetchone()
                if not row:
                    return None

                return {
                    "name": row[0],
                    "version": row[1],
                    "content": row[2]
                }

        except Exception as e:
            print("Error fetching transcript:", e)
            self.conn.rollback()
            return None