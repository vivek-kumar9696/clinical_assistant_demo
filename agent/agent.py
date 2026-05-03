import os
import json
import logging
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Annotated, List, Literal
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    TurnHandlingOptions,
    cli,
    inference,
    room_io,
    function_tool
)
from livekit.plugins import ai_coustics, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent-Jenny")
load_dotenv(".env.local")

# --- 1. PYDANTIC SCHEMAS ---

# --- 1. PYDANTIC SCHEMAS ---

# --- ROS LITERAL TYPES (Ensures strict classification) ---
# Source: https://health.uconn.edu/plastic-surgery/wp-content/uploads/sites/132/2017/06/review_of_systems.pdf
ConstitutionalSymptom = Literal["Chills", "Fatigue", "Fever", "Weight gain", "Weight loss"]
HEENTSymptom = Literal["Hearing loss", "Sinus pressure", "Visual changes"]
RespiratorySymptom = Literal["Cough", "Shortness of breath", "Wheezing"]
CardiovascularSymptom = Literal["Chest pain", "Pain while walking (Claudication)", "Edema", "Palpitations"]
GastrointestinalSymptom = Literal["Abdominal pain", "Blood in stool", "Constipation", "Diarrhea", "Heartburn", "Loss of appetite", "Nausea", "Vomiting"]
GenitourinarySymptom = Literal["Painful urination (Dysuria)", "Excessive amount of urine (Polyuria)", "Urinary frequency"]
MetabolicSymptom = Literal["Cold intolerance", "Heat intolerance", "Excessive thirst (Polydipsia)", "Excessive hunger (Polyphagia)"]
NeurologicalSymptom = Literal["Dizziness", "Extremity numbness", "Extremity weakness", "Headaches", "Seizures", "Tremors"]
PsychiatricSymptom = Literal["Anxiety", "Depression"]
IntegumentarySymptom = Literal["Breast discharge", "Breast lump", "Hives", "Mole change(s)", "Rash", "Skin lesion"]
MusculoskeletalSymptom = Literal["Back pain", "Joint pain", "Joint swelling", "Neck pain"]
HematologicSymptom = Literal["Easily bleeds", "Easily bruises", "Lymphedema", "Issues with blood clots"]
ImmunologicSymptom = Literal["Food allergies", "Seasonal allergies"]

class OldCartsAnalysis(BaseModel):
    onset: str
    location: str
    duration: str
    characteristics: str
    aggravating_factors: str = Field(description="MUST explicitly ask the patient what makes the pain worse.")
    alleviating_factors: str = Field(description="MUST explicitly ask the patient what makes the pain better.")
    radiation: str
    treatment_tried: str
    severity: str

class ReviewOfSystems(BaseModel):
    constitutional: List[ConstitutionalSymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    heent: List[HEENTSymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    respiratory: List[RespiratorySymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    cardiovascular: List[CardiovascularSymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    gastrointestinal: List[GastrointestinalSymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    genitourinary: List[GenitourinarySymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    metabolic_endocrine: List[MetabolicSymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    neurological: List[NeurologicalSymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    psychiatric: List[PsychiatricSymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    integumentary: List[IntegumentarySymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    musculoskeletal: List[MusculoskeletalSymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    hematologic: List[HematologicSymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    immunologic: List[ImmunologicSymptom] = Field(description="Pass an empty list [] if none.",default_factory=list)
    pertinent_negatives: List[str] = Field(description="Symptoms explicitly denied by patient.", default_factory=list)

class ClinicalIntake(BaseModel):
    patient_name: str
    patient_age: str
    patient_gender: str
    chief_complaint: str
    oldcarts_analysis: OldCartsAnalysis
    review_of_systems: ReviewOfSystems
    selected_doctor: str = Field(description="The doctor the patient chose.")
    appointment_slot: str = Field(description="The time slot the patient agreed to.")
    transcript_summary: str

    @field_validator('patient_age')
    @classmethod
    def check_age_completeness(cls, v: str) -> str:
        # Detect if the LLM is trying to "shortcut" the requirement
        placeholders = ["not given", "unknown", "none", "n/a", ""]
        if v.lower() in placeholders:
            raise ValueError("Age is mandatory. Please ask the patient specifically for their age before submitting.")
        return v

    @field_validator('patient_name')
    @classmethod
    def check_name_completeness(cls, v: str) -> str:
        # Detect if the LLM is trying to "shortcut" the requirement
        placeholders = ["not given", "unknown", "none", "n/a", ""]
        if v.lower() in placeholders:
            raise ValueError("Name is mandatory. Please ask the patient specifically for their name before submitting.")
        return v
    @field_validator('patient_gender')
    @classmethod
    def check_gender_completeness(cls, v: str) -> str:
        # Detect if the LLM is trying to "shortcut" the requirement
        placeholders = ["not given", "unknown", "none", "n/a", ""]
        if v.lower() in placeholders:
            raise ValueError("Gender is mandatory. Please ask the patient specifically for their gender before submitting.")
        return v


class SymptomStatus(BaseModel):
    symptom_name: str = Field(description="The name of the symptom you asked about.")
    status: Literal["confirmed_yes", "confirmed_no", "unanswered_or_ambiguous"] = Field(
        description="Must be 'unanswered_or_ambiguous' if the patient ignored it, dodged it, or gave a vague answer."
    )

class BatchedSymptomEvaluation(BaseModel):
    symptoms_evaluated: List[SymptomStatus]

# --- 2. TOOL DEFINITION ---

class PatientIntakeTools:
    @function_tool(
        description="CRITICAL: Call this function ONLY when the intake is completely finished AND the user explicitly agrees to submit the data and end the call. Do not call this preemptively."
    )
    async def submit_clinical_intake(
        self,
        intake_data: ClinicalIntake,
    ) -> str:
        os.makedirs("intakes", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intakes/intake_{timestamp}.json"

        try:
            with open(filename, "w") as f:
                json.dump(intake_data.model_dump(), f, indent=2)

            logger.info(f"✅ Intake saved to {filename}")
            return "Intake successfully saved. Please say a polite goodbye to the patient to conclude."

        except Exception as e:
            logger.error(f"❌ Failed to save intake: {e}")
            return "There was an error saving the clinical record."

    @function_tool(description="CRITICAL: Call this silently immediately after the patient answers a question where you asked about multiple symptoms at once.")
    async def evaluate_batched_response(self, evaluation: BatchedSymptomEvaluation):

        # 1. Isolate the "Dropped Packets"
        missed_symptoms = [
            s.symptom_name for s in evaluation.symptoms_evaluated
            if s.status == "unanswered_or_ambiguous"
        ]

        # 2. Deterministic Routing
        if missed_symptoms:
            logger.info(f"⚠️ Incomplete batch. Forcing re-ask for: {missed_symptoms}")
            return (
                f"SYSTEM ERROR: The patient did not clearly confirm or deny the following symptoms: {', '.join(missed_symptoms)}. "
                f"You MUST immediately follow up and ask specifically about these missed symptoms. Do not move forward yet."
            )

        logger.info("✅ Batch fully resolved.")
        return "SYSTEM SUCCESS: All symptoms in that batch were clearly resolved. Proceed."

# --- 3. AGENT DEFINITION ---

class DefaultAgent(Agent):
    def __init__(self, doctor_data: str) -> None:
        intake_tools = PatientIntakeTools()

        super().__init__(
            instructions=f"""# Persona
You are a professional Clinical Intake Assistant for WardlyAI. Your goal is to conduct a focused, empathetic, and structured medical interview.

# Mandatory Workflow sequence
You must follow these steps in order. Do not skip ahead.
1. **Identification**: Ask for the patient's NAME, AGE and GENDER.
2. **Chief Complaint**: Ask what brings them in today.
3. **OLDCARTS**: Investigate the complaint. You MUST explicitly ask about aggravating and alleviating factors.
4. **Targeted ROS**: Do NOT read an exhaustive list of symptoms. Use clinical reasoning based on the Chief Complaint to ask relevant questions.
5. **Doctor Selection**: Present the available doctors and date-time slots SLOWLY, CLEARLY like a HUMAN. Use proper words for date and time. The format of date time is "YYYY-MM-DD HH:mm AM/PM". Ask them to choose one from this list: {doctor_data}.
6. **Final Confirmation**: Summarize the details and ask, "Are you ready for me to submit this to the doctor?"

# Output & Behavior Rules
- Speak like a human: "I'm sorry to hear that," or "That sounds difficult."
- Keep your spoken responses brief (1-3 sentences). Ask ONE question at a time.
- **NEVER** call the 'submit_clinical_intake' tool until Step 6 is complete and the user says YES.
""",
            tools=[intake_tools.submit_clinical_intake],
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions="Greet the user, ask for their name and age, and ask how you can help them today.",
            allow_interruptions=True,
        )

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session(agent_name="Jenny")
async def entrypoint(ctx: JobContext):

    try:
        with open("doctor_availability.json", "r") as f:
            doctor_list = f.read()
    except FileNotFoundError:
        doctor_list = "No doctors currently available in the system."

    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="en"),
        llm=inference.LLM(model="openai/gpt-5.3-chat-latest"),
        tts=inference.TTS(
            model="cartesia/sonic-3",
            voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
            language="en"
        ),
        turn_handling=TurnHandlingOptions(turn_detection=MultilingualModel()),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    await session.start(
        agent=DefaultAgent(doctor_data=doctor_list),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_L,
                ),
            ),
        ),
    )

if __name__ == "__main__":
    cli.run_app(server)
