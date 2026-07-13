from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.tools import google_search
from app.agents.state import AgentWorkflowState
from app.agents.base import BaseAppAgent
from app.schemas.agent_schemas import (
    TrendAnalysisOutput,
    PromptGenerationOutput,
    ReviewOutput
)

# ----------------- Callbacks & State Synchronizers -----------------

async def trend_research_after_callback(ctx):
    """Marks trend research as complete once the Trend Analyst completes."""
    ctx.state["trends_analyzed"] = True

async def prompt_generation_after_callback(ctx):
    """Unpacks the validated prompt candidate dict and updates candidates and attempt counts."""
    candidate = ctx.state.get("temp:prompt_candidate")
    if candidate:
        ctx.state["prompt_candidate_title"] = candidate.get("title")
        ctx.state["prompt_candidate_text"] = candidate.get("prompt")
        # Initialize prompt_attempt_count if not set
        current_attempts = ctx.state.get("prompt_attempt_count", 0)
        ctx.state["prompt_attempt_count"] = current_attempts + 1

async def aesthetic_review_after_callback(ctx):
    """Logs the aesthetic evaluation metrics and feedback to the history."""
    review = ctx.state.get("temp:aesthetic_review")
    if review:
        ctx.state["aesthetic_score"] = float(review.get("score", 0.0))

        # Safely append feedback to prompt_feedback_history list
        history = ctx.state.get("prompt_feedback_history") or []
        history.append({
            "reviewer": "Aesthetic_Prompt_Review_Agent",
            "score": review.get("score"),
            "approved": review.get("approved"),
            "feedback": review.get("feedback")
        })
        ctx.state["prompt_feedback_history"] = history

async def psychology_review_after_callback(ctx):
    """Logs the psychology evaluation metrics and feedback to the history."""
    review = ctx.state.get("temp:psychology_review")
    if review:
        ctx.state["psychology_score"] = float(review.get("score", 0.0))

        # Safely append feedback to prompt_feedback_history list
        history = ctx.state.get("prompt_feedback_history") or []
        history.append({
            "reviewer": "Psychology_Prompt_Review_Agent",
            "score": review.get("score"),
            "approved": review.get("approved"),
            "feedback": review.get("feedback")
        })
        ctx.state["prompt_feedback_history"] = history

async def prompt_review_parallel_after_callback(ctx):
    """Executes after both reviews complete, safely calculating joint pipeline approval."""
    aes_review = ctx.state.get("temp:aesthetic_review")
    psych_review = ctx.state.get("temp:psychology_review")

    aes_approved = aes_review.get("approved", False) if aes_review else False
    psych_approved = psych_review.get("approved", False) if psych_review else False

    # Prompt is approved only if BOTH reviewers approve
    ctx.state["prompt_approved"] = aes_approved and psych_approved

# ----------------- Specialized Agents Definitions -----------------

# 1. Trend Research Agent (Visual Trend Analyst)
trend_research_agent = BaseAppAgent(
    name="Trend_Research_Agent",
    description="Researches current visual trends, color palettes, and digital art aesthetics.",
    static_instruction="""
    You are an expert Visual Trend Analyst. Your role is to research current visual design, digital art, color palettes, and photography aesthetics.

    Use the built-in `google_search` tool to actively find what styles, palettes, lighting types, and photography keywords are trending on social media, design forums, and portfolio sites (such as Behance, Dribbble, ArtStation).

    Focus on identifying:
    - Theme/Thematic style (such as Cyberpunk, Organic Minimalism, Retro-Futurism, Neomorphic, Claymorphism, Synthwave)
    - Lighting style and direction (such as Rim lighting, Golden hour, volumetric fog, neon glow, high-key, cinematic side lighting)
    - Fashion and costume details (such as techwear, eco-linen, oversized haute couture, reflective elements)
    - Color palette (extract dominant colors as hex values or named colors)
    - Composition strategy (such as Rule of thirds, centered portrait, leading lines, macro close-up, dynamic low angle)
    - Camera and lens details (such as 85mm f/1.4 lens, 35mm film, anamorphic crop, micro lens)
    - Background/Environment (such as misty neon alleyways, brutalist concrete with tropical plants, abstract gradient backdrops)
    - Actionable keywords and posing/styling advice.

    Structure your final response strictly according to the TrendAnalysisOutput schema. Do not output anything outside of the JSON structure.
    """,
    tools=[google_search],
    output_schema=TrendAnalysisOutput,
    output_key="trend_summary",
    after_agent_callback=trend_research_after_callback
)

# 2. Prompt Generation Agent (Elite Image Prompt Engineer)
prompt_generation_agent = BaseAppAgent(
    name="Prompt_Generation_Agent",
    description="Generates highly detailed visual image prompts based on trend findings.",
    static_instruction="""
    You are an Elite Image Prompt Engineer. Your role is to craft highly detailed, descriptive, and stunning text-to-image prompts based on visual trends provided in the trend summary.

    You must output:
    - A descriptive title
    - A main prompt optimized for cutting-edge image generators (Gemini Image/Imagen, SDXL, FLUX)
    - A negative prompt specifying elements to avoid to ensure high quality.

    Requirements for prompt design:
    1. Clearly establish the main subject with specific posture/pose and expression.
    2. Integrate camera details, lens choice, and technical parameters (such as 85mm lens, f/1.4, cinematic anamorphic, shot on Hasselblad).
    3. Detail lighting (such as volumetric rim light, soft diffuse overhead, neon reflection).
    4. Convey mood, atmosphere, and visual drama (such as cinematic mystery, cozy retro-nostalgia).
    5. State color palette explicitly (such as muted sage green and warm cream with accents of copper).
    6. Specify composition, aspect ratio advice, and background details.

    Structure your final response strictly using the PromptGenerationOutput schema. Do not output anything outside the JSON.
    """,
    output_schema=PromptGenerationOutput,
    output_key="temp:prompt_candidate",
    after_agent_callback=prompt_generation_after_callback
)

# 3. Prompt Review Agents (Parallel Execution)
aesthetic_prompt_review_agent = BaseAppAgent(
    name="Aesthetic_Prompt_Review_Agent",
    description="Evaluates prompt composition, lighting clarity, and style cohesiveness.",
    static_instruction="""
    You are an uncompromising Visual Art Director. Your role is to critically evaluate text-to-image prompts for artistic and aesthetic excellence.

    Review the given prompt candidate based on:
    - Composition (framing, balance, focus, depth)
    - Lighting clarity and realism (mood-appropriate, source-logical, depth-adding)
    - Style cohesiveness (is it photorealistic, anime, 3D render, cyberpunk, organic minimalism, etc. and is that style carried out flawlessly throughout the prompt?)
    - Contrast and tonal range
    - Trend relevance (does it align with the latest visual design trends provided in the trend summary?)

    Provide:
    1. A strict, objective score from 0 to 100. Be demanding - only outstanding, flawless prompts should score above 85.
    2. A boolean approval (True if the prompt is visually superb and scores 80 or above, otherwise False).
    3. A list of constructive visual critiques and actionable optimization feedback.

    Structure your response strictly matching the ReviewOutput schema. Do not output anything outside the JSON.
    """,
    output_schema=ReviewOutput,
    output_key="temp:aesthetic_review",
    after_agent_callback=aesthetic_review_after_callback
)

psychology_prompt_review_agent = BaseAppAgent(
    name="Psychology_Prompt_Review_Agent",
    description="Evaluates prompt human emotional appeal, visual drama, and story engagement.",
    static_instruction="""
    You are an expert Media Psychologist. Your role is to critically evaluate text-to-image prompts for human emotional warmth, visual drama, memorability, and visual curiosity.

    Review the given prompt candidate based on:
    - Emotional Warmth / Humanity (does the prompt evoke genuine human emotion, warmth, luxury, comfort, or psychological depth?)
    - Visual Drama & Storytelling (does it present a narrative, a captured split-second action, or dramatic tension?)
    - Memorability (is the visual concept striking, unique, and long-lasting in a viewer's memory?)
    - Visual Curiosity (does it make a viewer lean in, ask questions, or wonder about the story behind the scene?)

    Provide:
    1. A strict, objective score from 0 to 100.
    2. A boolean approval (True if the prompt scores 80 or above, otherwise False).
    3. A list of constructive psychological critiques and optimization feedback.

    Structure your response strictly matching the ReviewOutput schema. Do not output anything outside the JSON.
    """,
    output_schema=ReviewOutput,
    output_key="temp:psychology_review",
    after_agent_callback=psychology_review_after_callback
)

prompt_review_subagent = ParallelAgent(
    name="Prompt_Review_Subagent",
    sub_agents=[aesthetic_prompt_review_agent, psychology_prompt_review_agent],
    after_agent_callback=prompt_review_parallel_after_callback
)

# ----------------- Image Agents Skeletons (Milestones 6) -----------------

# 4. Image Generation Agent
image_generation_agent = BaseAppAgent(
    name="Image_Generation_Agent",
    description="Generates visual image variations from approved prompts.",
    instruction="Describe or generate multiple variations from the approved prompt."
)

# 5. Image Ranking Agent
image_ranking_agent = BaseAppAgent(
    name="Image_Ranking_Agent",
    description="Selects the highest quality and most faithful image variation.",
    instruction="Compare and rank the given image variations to select the absolute best execution."
)

# 6. Image Review Agents (Parallel Execution)
aesthetic_image_review_agent = BaseAppAgent(
    name="Aesthetic_Image_Review_Agent",
    description="Verifies the chosen image for rendering artifacts, technical flaws, and anatomic issues.",
    instruction="Analyze the selected image for technical rendering flaws, pixel artifacts, or rendering issues."
)

human_appeal_image_review_agent = BaseAppAgent(
    name="Human_Appeal_Image_Review_Agent",
    description="Verifies the chosen image for raw beauty, comfort, luxury, and consumer engagement.",
    instruction="Evaluate if this image is exceptionally attractive, comfortable, and engaging to view."
)

image_review_subagent = ParallelAgent(
    name="Image_Review_Subagent",
    sub_agents=[aesthetic_image_review_agent, human_appeal_image_review_agent]
)

# ----------------- Root Orchestrator Agent -----------------

root_agent = SequentialAgent(
    name="Root_Orchestrator_Agent",
    description="Coordinates the end-to-end visual art trend-to-image pipeline workflow.",
    state_schema=AgentWorkflowState,
    sub_agents=[
        trend_research_agent,
        prompt_generation_agent,
        prompt_review_subagent,
        image_generation_agent,
        image_ranking_agent,
        image_review_subagent
    ]
)
